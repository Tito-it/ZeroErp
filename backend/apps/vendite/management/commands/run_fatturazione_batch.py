# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Management command — driver batch della fatturazione (Fase 3).
#        Scopre le commesse emittibili di una corsia (immediata/differita) e
#        porta a termine la pipeline lotto PER EMITTENTE (un lotto per emittente,
#        la numerazione fattura è per emittente). Best-effort: una corsia/emittente
#        in errore non blocca gli altri. Eseguibile come cron job (systemd/crontab),
#        NON pgAgent (riservato a manutenzione DB).
# ------------------------------------------------------------

from __future__ import annotations

from datetime import date, datetime

from django.core.management.base import BaseCommand, CommandError

from apps.core.services.auth_constants import AUDIT_ACTOR_BATCH_FATTURAZIONE
from apps.core.services.job_run import ORIGINE_CRON, registered_job
from apps.core.services.service_errors import ServiceError
from apps.core.services.system_context import system_process_context
from apps.vendite.db.commesse_repository import CommesseRepository
from apps.vendite.db.pipeline_repository import LOTTO_META_KEY_FATTURAZIONE_IMMEDIATA
from apps.vendite.services.pipeline_service import run_lotto_pipeline_until_done

# Alias DB del canale di sistema per la fatturazione (settings.DATABASES) — Path A.
SYSTEM_FATTURAZIONE_DB_ALIAS = "system_fatturazione"

# Mappatura corsia → (tipo_lotto pipeline, filtro fatturazione_immediata).
# Convenzione del modello a due corsie (vedi brief-db-emittibili-filtro-...).
_MODALITA = {
    "immediata": ("GIORNALIERO", True),
    "differita": ("MASSIVO", False),
}


class Command(BaseCommand):
    help = (
        "Driver batch fatturazione: per la corsia scelta scopre le commesse "
        "emittibili e completa la pipeline lotto per ogni emittente. "
        "Eseguibile come cron job (systemd/crontab)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--modalita", required=True, choices=sorted(_MODALITA.keys()),
            help="Corsia: 'immediata' (GIORNALIERO) o 'differita' (MASSIVO).",
        )
        parser.add_argument(
            "--competenza", type=str, default=None,
            help="Mese di competenza ISO (YYYY-MM-DD, normalizzato al 1°). "
                 "Default: primo giorno del mese corrente.",
        )
        parser.add_argument(
            "--emittente-id", type=int, default=None,
            help="Limita a un singolo emittente (soggetto_ruolo_id). "
                 "Default: tutti gli emittenti con commesse emittibili.",
        )
        parser.add_argument(
            "--utility-id", type=int, default=None,
            help="Filtro perimetro opzionale per utility.",
        )
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Solo scoperta e conteggio, senza creare lotti né fatturare.",
        )
        parser.add_argument(
            "--limit", type=int, default=10000,
            help="Cap discovery commesse emittibili (default 10000).",
        )

    # Scopo: Risolve la competenza (default = primo del mese corrente).
    def _resolve_competenza(self, raw: str | None) -> date:
        if not raw:
            return date.today().replace(day=1)
        try:
            return datetime.strptime(raw, "%Y-%m-%d").date().replace(day=1)
        except ValueError as exc:
            raise CommandError(f"--competenza non valida (atteso YYYY-MM-DD): {raw}") from exc

    def handle(self, *args, **options):
        modalita = options["modalita"]
        tipo_lotto, fatturazione_immediata = _MODALITA[modalita]
        competenza = self._resolve_competenza(options["competenza"])
        emittente_id = options["emittente_id"]
        utility_id = options["utility_id"]
        dry_run = options["dry_run"]
        limit = options["limit"]

        run_kwargs = dict(
            modalita=modalita,
            tipo_lotto=tipo_lotto,
            fatturazione_immediata=fatturazione_immediata,
            competenza=competenza,
            emittente_id=emittente_id,
            utility_id=utility_id,
            limit=limit,
        )

        # Canale di SISTEMA per il batch headless (RLS Path A): instrada la catena DB
        # sul ruolo BYPASSRLS `zeroerp_batch_fatturazione` (alias `system_fatturazione`)
        # — il cron non è un operatore e deve vedere/scrivere TUTTI gli emittenti.
        # L'endpoint on-demand resta invece nello scope OPERATORE del chiamante.
        with system_process_context(
            alias=SYSTEM_FATTURAZIONE_DB_ALIAS,
            actor=AUDIT_ACTOR_BATCH_FATTURAZIONE,
        ):
            # DRY-RUN: solo discovery/conteggio → NON è un'esecuzione operativa, niente
            # registrazione del run (design §6.2).
            if dry_run:
                self._run_batch(dry_run=True, **run_kwargs)
                return

            # Registrazione run-level (job_run_log) DENTRO il canale di sistema (stessa
            # connessione del ruolo batch → advisory-lock di sessione valido per tutto il
            # run). Chiave logica per-corsia: immediata e differita non si bloccano a
            # vicenda. Lock occupato → skip senza attendere (riga "skip" già loggata).
            job_id = f"run_fatturazione_batch:{modalita}"
            with registered_job(job_id, origine=ORIGINE_CRON, lock_key=job_id) as job:
                if not job.acquired:
                    self.stdout.write(self.style.WARNING(
                        f"skip: un altro run della corsia '{modalita}' è già in corso."
                    ))
                    return
                summary = self._run_batch(dry_run=False, **run_kwargs)
                job.set_meta(summary)
                job.set_rows_affected(summary.get("emittenti", 0))

    # Scopo: corpo del batch (discovery + esecuzione per emittente) eseguito DENTRO il
    #        canale di sistema. Estratto da handle per isolare il setup del gateway.
    #        Ritorna un riepilogo GENERICO del run (emittenti/falliti/per_motivo) usato
    #        come `meta` di job_run_log; `{}` per dry-run (non registrato).
    def _run_batch(
        self,
        *,
        modalita: str,
        tipo_lotto: str,
        fatturazione_immediata: bool,
        competenza: date,
        emittente_id: int | None,
        utility_id: int | None,
        dry_run: bool,
        limit: int,
    ) -> dict:
        repo = CommesseRepository()

        # Perimetri emittente: esplicito (--emittente-id) o scoperti tra gli emittibili.
        if emittente_id is not None:
            scoperti: list[int | None] = [emittente_id]
        else:
            scoperti = repo.list_emittibili_emittenti(
                competenza_mese=competenza,
                utility_id=utility_id,
                fatturazione_immediata=fatturazione_immediata,
                limit=limit,
            )

        # Un lotto richiede un emittente (emittente_soggetto_ruolo_id NOT NULL): le
        # commesse emittibili senza emittente non sono fatturabili da qui → saltate.
        emittenti = [e for e in scoperti if e is not None]
        senza_emittente = len(scoperti) - len(emittenti)
        if senza_emittente:
            self.stderr.write(self.style.WARNING(
                f"{senza_emittente} gruppo/i di commesse emittibili SENZA emittente: "
                "non fatturabili (il lotto richiede emittente), saltati."
            ))

        self.stdout.write(
            f"Corsia={modalita} (tipo_lotto={tipo_lotto}, immediata={fatturazione_immediata}) "
            f"competenza={competenza.isoformat()} emittenti={len(emittenti)}"
            + (" [DRY-RUN]" if dry_run else "")
        )

        if not emittenti:
            self.stdout.write("Nessuna commessa emittibile (con emittente) per la corsia/competenza.")
            return {"emittenti": 0, "falliti": 0, "per_motivo": {}}

        # DRY-RUN: solo discovery/conteggio, nessun lotto creato.
        if dry_run:
            for em in emittenti:
                count = len(repo.list_commesse_emittibili(
                    competenza_mese=competenza,
                    utility_id=utility_id,
                    emittente_soggetto_ruolo_id=em,
                    fatturazione_immediata=fatturazione_immediata,
                    limit=limit,
                ))
                self.stdout.write(f"  emittente={em}: {count} commesse emittibili")
            return {}

        # Esecuzione: un lotto per emittente, best-effort.
        esiti_per_motivo: dict[str, int] = {}
        falliti = 0
        for em in emittenti:
            try:
                esito = run_lotto_pipeline_until_done(
                    competenza_mese=competenza,
                    emittente_soggetto_ruolo_id=em,
                    utility_id=utility_id,
                    tipo_lotto=tipo_lotto,
                    meta={LOTTO_META_KEY_FATTURAZIONE_IMMEDIATA: fatturazione_immediata},
                    dry_run=False,
                )
            except ServiceError as exc:
                falliti += 1
                self.stderr.write(self.style.ERROR(
                    f"  emittente={em}: ERRORE {exc.code} - {exc.detail or exc}"
                ))
                continue
            motivo = str(esito.get("motivo_stop"))
            esiti_per_motivo[motivo] = esiti_per_motivo.get(motivo, 0) + 1
            self.stdout.write(
                f"  emittente={em}: lotto={esito.get('lotto_id')} "
                f"motivo={motivo} step_eseguiti={esito.get('step_eseguiti')}"
            )

        riepilogo = ", ".join(f"{k}={v}" for k, v in sorted(esiti_per_motivo.items()))
        self.stdout.write(self.style.SUCCESS(
            f"Completato: {len(emittenti)} emittenti — {riepilogo or 'nessun esito'}"
            + (f", falliti={falliti}" if falliti else "")
        ))
        return {
            "emittenti": len(emittenti),
            "falliti": falliti,
            "per_motivo": esiti_per_motivo,
        }
