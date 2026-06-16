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

from apps.core.services.service_errors import ServiceError
from apps.vendite.db.commesse_repository import CommesseRepository
from apps.vendite.db.pipeline_repository import LOTTO_META_KEY_FATTURAZIONE_IMMEDIATA
from apps.vendite.services.pipeline_service import run_lotto_pipeline_until_done

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
            return

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
            return

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
