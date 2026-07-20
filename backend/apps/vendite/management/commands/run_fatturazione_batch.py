# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Management command — driver batch della fatturazione. Dal 2026-07-20
#        (Fase C cockpit, step C-1) e' un CHIAMANTE SOTTILE del core condiviso
#        `fatturazione_driver_service.esegui_giro_fatturazione` (stesso core
#        dell'endpoint POST /vendite/fatturazione/run/ — invariante I-1: mai
#        due implementazioni). Qui restano solo le responsabilita' da cron:
#        argparse, canale di SISTEMA (RLS Path A), registrazione run-level
#        (job_run_log) con lock anti-overlap per corsia, output console.
#        Gate fiscale D-1: la corsia immediata completa (numera da sola), la
#        differita si ferma a EMESSA (default di corsia nel core;
#        --fino-a-stato per override diagnostico).
# ------------------------------------------------------------

from __future__ import annotations

from datetime import date, datetime

from django.core.management.base import BaseCommand, CommandError

from apps.core.services.auth_constants import AUDIT_ACTOR_BATCH_FATTURAZIONE
from apps.core.services.job_run import ORIGINE_CRON, registered_job
from apps.core.services.system_context import (
    SYSTEM_FATTURAZIONE_DB_ALIAS,
    system_process_context,
)
from apps.vendite.services.fatturazione_driver_service import (
    esegui_giro_fatturazione,
    modalita_disponibili,
)


class Command(BaseCommand):
    help = (
        "Driver batch fatturazione: per la corsia scelta scopre le commesse "
        "emittibili e completa la pipeline lotto per ogni emittente. "
        "Eseguibile come cron job (systemd/crontab)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--modalita", required=True, choices=modalita_disponibili(),
            help="Corsia: 'immediata' (GIORNALIERO) o 'differita' (MASSIVO).",
        )
        parser.add_argument(
            "--competenza", type=str, default=None,
            help="Competenza massima ISO (YYYY-MM-DD, normalizzata al 1°). È un BOUND "
                 "SUPERIORE cumulativo (<=): include anche gli arretrati dei mesi "
                 "precedenti. Default: primo giorno del mese corrente.",
        )
        parser.add_argument(
            "--emittente-id", type=int, default=None,
            help="Restringe la discovery a un singolo emittente (soggetto_ruolo_id); "
                 "le coppie (emittente, tipo_doc) di quell'emittente vengono comunque "
                 "scoperte. Default: tutti gli emittenti emittibili.",
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
            help="Cap sulle COPPIE (emittente, tipo_doc) scoperte (default 10000).",
        )
        parser.add_argument(
            "--fino-a-stato", type=str, default=None,
            help="Override diagnostico della fermata (codice config.stati_doc_fiscale, "
                 "es. EMESSA). Default: la fermata di corsia (immediata=fino in fondo, "
                 "differita=EMESSA per D-1).",
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
        competenza = self._resolve_competenza(options["competenza"])
        dry_run = options["dry_run"]

        giro_kwargs = dict(
            modalita=modalita,
            competenza=competenza,
            emittente_soggetto_ruolo_id=options["emittente_id"],
            utility_id=options["utility_id"],
            limit=options["limit"],
            dry_run=dry_run,
        )
        if options["fino_a_stato"] is not None:
            giro_kwargs["fino_a_stato"] = options["fino_a_stato"]

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
                summary = esegui_giro_fatturazione(
                    on_discovery=self._print_header, **giro_kwargs,
                )
                self._print_summary(summary)
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
                summary = esegui_giro_fatturazione(
                    on_discovery=self._print_header,
                    on_lane_esito=self._print_lane_esito,
                    **giro_kwargs,
                )
                self._print_summary(summary)
                # Meta COMPATTA per job_run_log: niente lista esiti per-terna
                # (con centinaia di lane gonfierebbe il jsonb di monitoraggio;
                # il dettaglio vive nei log e nell'esito API).
                job.set_meta(self._compact_meta(summary))
                job.set_rows_affected(summary.get("lane", 0))

    # Scopo: log progressivo per-terna su stdout/stderr (callback del core):
    #        esito su successo, riga ERRORE best-effort su fallimento.
    def _print_lane_esito(self, lane, esito, errore) -> None:
        em = lane["emittente_soggetto_ruolo_id"]
        tipo_doc = lane["tipo_doc_fiscale_id"]
        utility = lane["utility_id"]
        if errore is not None:
            self.stderr.write(self.style.ERROR(
                f"  emittente={em} tipo_doc={tipo_doc} utility={utility}: "
                f"ERRORE {errore.code} - {errore.detail or errore}"
            ))
            return
        self.stdout.write(
            f"  emittente={em} tipo_doc={tipo_doc} utility={utility}: "
            f"lotto={esito.get('lotto_id')} "
            f"motivo={esito.get('motivo_stop')} step_eseguiti={esito.get('step_eseguiti')}"
        )

    # Scopo: header del giro in TESTA al log (callback on_discovery del core:
    #        stampato dopo la discovery, prima dell'esecuzione delle terne).
    def _print_header(self, summary: dict) -> None:
        if summary["senza_emittente"]:
            self.stderr.write(self.style.WARNING(
                f"{summary['senza_emittente']} terna/e emittibili SENZA emittente: "
                "non fatturabili (il lotto richiede emittente), saltate."
            ))
        self.stdout.write(
            f"Corsia={summary['modalita']} (tipo_lotto={summary['tipo_lotto']}, "
            f"immediata={summary['fatturazione_immediata']}) "
            f"competenza<={summary['competenza']} terne={summary['lane']}"
            + (" [DRY-RUN]" if summary["dry_run"] else "")
        )

    # Scopo: meta compatta del run per job_run_log (senza la lista esiti).
    def _compact_meta(self, summary: dict) -> dict:
        return {k: v for k, v in summary.items() if k != "esiti"}

    # Scopo: stampa la coda del riepilogo (dry-run lanes / nessuna terna / chiusura).
    def _print_summary(self, summary: dict) -> None:
        if not summary["lane"]:
            self.stdout.write(
                "Nessuna terna (emittente, tipo_doc, utility) emittibile per la corsia/competenza."
            )
            return
        if summary["dry_run"]:
            for lane in summary["esiti"]:
                self.stdout.write(
                    f"  emittente={lane['emittente_soggetto_ruolo_id']} "
                    f"tipo_doc={lane['tipo_doc_fiscale_id']} "
                    f"utility={lane['utility_id']} "
                    f"competenza={lane['competenza_mese']}: "
                    f"{lane['total_candidate']} righe candidate"
                )
            return
        riepilogo = ", ".join(
            f"{k}={v}" for k, v in sorted(summary["per_motivo"].items())
        )
        falliti = summary["falliti"]
        self.stdout.write(self.style.SUCCESS(
            f"Completato: {summary['lane']} terne — {riepilogo or 'nessun esito'}"
            + (f", falliti={falliti}" if falliti else "")
        ))
