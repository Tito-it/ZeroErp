# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Management command — worker DRAINER della coda lavori generica
#        (`dbops.coda_lavori`). Chiamante SOTTILE del core condiviso
#        `draina_coda_lavori` (invariante I-1): qui solo argparse, registrazione
#        run-level (`maintenance.job_run_log`) e output console. Eseguibile come
#        cron/systemd timer. Vive in `apps/core` (la coda è infrastruttura core,
#        non di dominio — il worker è generico, dispatcha per job_type).
#
#        NB anti-overlap: NESSUN `lock_key`. La coda è concorrenza-safe per
#        costruzione (`claim` con `FOR UPDATE SKIP LOCKED` → più worker prendono
#        righe diverse). `registered_job` qui serve solo al TRACCIAMENTO.
#        ⚠️ C'era una seconda ragione — «un lock di sessione verrebbe rilasciato
#        dal canale di sistema per-item, che chiude la connessione» — ed è
#        DECADUTA il 2026-09-05 col ritiro di quel canale. La prima regge da
#        sola, ed è quella vera.
# ------------------------------------------------------------

from __future__ import annotations

from apps.core.management.comando_aziendale import ComandoAziendale

from apps.core.services.coda_lavori.drainer_service import draina_coda_lavori
from apps.core.services.job_run import ORIGINE_CRON, registered_job
from apps.core.services.processi import PROCESSO_DRAINA_CODA_LAVORI


class Command(ComandoAziendale):
    help = (
        "Worker drainer della coda lavori generica (dbops.coda_lavori): claima i "
        "job eleggibili, li dispatcha per tipo (SISTEMA/OPERATORE) e ne aggiorna "
        "l'esito con retry/backoff. Eseguibile come cron/systemd timer."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit", type=int, default=None,
            help="Cap sui job lavorati in questo giro (default del core). Il "
                 "backlog eccedente lo raccoglie il giro successivo.",
        )
        parser.add_argument(
            "--stale-minuti", type=int, default=None,
            help="Job IN_CORSO più vecchi di N minuti (worker morto) riportati a "
                 "PENDING a inizio giro. 0 = disabilita il reaper.",
        )

    def handle(self, *args, **options):
        kwargs = {
            k: options[k]
            for k in ("limit", "stale_minuti")
            if options[k] is not None
        }
        # Tracciamento run-level (senza lock: SKIP LOCKED regge la concorrenza).
        with registered_job(
            PROCESSO_DRAINA_CODA_LAVORI,
            processo_codice=PROCESSO_DRAINA_CODA_LAVORI,
            origine=ORIGINE_CRON,
        ) as job:
            # `job.id` = run job_run_log timbrato sui job claimati (tracciabilità
            # job↔passata, guida Tracciamento processi e job).
            summary = draina_coda_lavori(
                job_run_id=job.id,
                on_item_esito=self._print_item_esito, **kwargs,
            )
            self._print_summary(summary)
            job.set_meta(summary)
            job.set_rows_affected(summary.get("claimate", 0))

    # Scopo: log per-item su stdout/stderr (callback del core).
    def _print_item_esito(self, item, esito) -> None:
        if esito["esito"] == "fatto":
            self.stdout.write(f"  job={item.id} {item.job_type}: FATTO")
            return
        stile = self.style.ERROR if esito["esito"] == "errore" else self.style.WARNING
        etichetta = "ERRORE" if esito["esito"] == "errore" else "RIPROVA"
        self.stderr.write(stile(
            f"  job={item.id} {item.job_type}: {etichetta} code={esito.get('code')}"
        ))

    # Scopo: riepilogo del giro in coda al log.
    def _print_summary(self, summary: dict) -> None:
        if summary["claimate"] == 0:
            recuperate = summary.get("recuperate", 0)
            self.stdout.write(
                "Nessun job in coda da lavorare."
                + (f" (recuperati {recuperate} stantii)" if recuperate else "")
            )
            return
        self.stdout.write(self.style.SUCCESS(
            f"Drenaggio completato: claimati={summary['claimate']} "
            f"fatto={summary['fatto']} errore={summary['errore']} "
            f"riprovabili={summary['riprovabili']} "
            f"(recuperati={summary.get('recuperate', 0)})"
        ))
