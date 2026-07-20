# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Management command — worker DRAINER della coda stampa documentale
#        (Fase C, step C-2b). È un CHIAMANTE SOTTILE del core condiviso
#        `stampa_coda_drainer_service.draina_coda_stampa` (invariante I-1): qui
#        restano solo le responsabilità da cron/systemd — argparse, canale di
#        SISTEMA (RLS Path A, stesso ruolo BYPASSRLS del batch fatturazione),
#        registrazione run-level (job_run_log) con lock anti-overlap, output
#        console. Eseguibile come cron/systemd timer accanto a
#        `run_fatturazione_batch`; drena in background le stampe accodate alla
#        DEFINITIVA e le ristampe on-demand.
# ------------------------------------------------------------

from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.core.services.auth_constants import AUDIT_ACTOR_WORKER_STAMPA
from apps.core.services.job_run import ORIGINE_CRON, registered_job
from apps.core.services.system_context import system_process_context
# Alias DB del canale di sistema: owner unico è il command batch (stesso ruolo
# BYPASSRLS `zeroerp_batch_fatturazione`) — niente 2ª copia del letterale.
from apps.vendite.management.commands.run_fatturazione_batch import (
    SYSTEM_FATTURAZIONE_DB_ALIAS,
)
from apps.vendite.services.stampa_coda_drainer_service import draina_coda_stampa


class Command(BaseCommand):
    help = (
        "Worker drainer della coda stampa documentale: numera (backstop) e "
        "genera i PDF delle fatture accodate, aggiornando l'esito per riga. "
        "Eseguibile come cron/systemd timer."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit", type=int, default=None,
            help="Cap sulle righe di coda lavorate in questo giro (default del "
                 "core). Il backlog eccedente lo raccoglie il giro successivo.",
        )
        parser.add_argument(
            "--soglia-tentativi", type=int, default=None,
            help="Tentativi oltre cui una riga passa a ERRORE terminale "
                 "(default del core).",
        )
        parser.add_argument(
            "--stale-minuti", type=int, default=None,
            help="Righe IN_CORSO più vecchie di N minuti (worker morto) "
                 "riportate a PENDING a inizio giro. 0 = disabilita il reaper.",
        )

    def handle(self, *args, **options):
        # Solo i parametri esplicitamente passati sovrascrivono i default del core.
        kwargs = {
            k: options[k]
            for k in ("limit", "soglia_tentativi", "stale_minuti")
            if options[k] is not None
        }

        # Canale di SISTEMA per il worker headless (RLS Path A): ruolo BYPASSRLS
        # `zeroerp_batch_fatturazione` (alias `system_fatturazione`). Necessario
        # perché `genera_documento` in contesto sistema (emittente_scope=None)
        # ha un guard fail-loud che pretende una connessione BYPASSRLS.
        with system_process_context(
            alias=SYSTEM_FATTURAZIONE_DB_ALIAS,
            actor=AUDIT_ACTOR_WORKER_STAMPA,
        ):
            # Registrazione run-level DENTRO il canale di sistema (stessa
            # connessione → advisory-lock di sessione valido per tutto il run).
            # Lock anti-overlap: un secondo cron mentre il primo è in corso fa
            # skip senza attendere. La parallelizzazione vera (P-5) è comunque
            # sicura a livello DB (claim `FOR UPDATE SKIP LOCKED`): all'occorrenza
            # basta sharding/lock distinti, non un cambio di modello.
            job_id = "draina_coda_stampa"
            with registered_job(job_id, origine=ORIGINE_CRON, lock_key=job_id) as job:
                if not job.acquired:
                    self.stdout.write(self.style.WARNING(
                        "skip: un altro worker di drenaggio è già in corso."
                    ))
                    return
                summary = draina_coda_stampa(
                    on_item_esito=self._print_item_esito, **kwargs,
                )
                self._print_summary(summary)
                job.set_meta(summary)
                job.set_rows_affected(summary.get("claimate", 0))

    # Scopo: log per-riga su stdout/stderr (callback del core): esito del render.
    def _print_item_esito(self, item, esito) -> None:
        coda_id = item["id"]
        fattura_id = item["sorgente_id"]
        if esito["esito"] == "fatto":
            self.stdout.write(
                f"  coda={coda_id} fattura={fattura_id}: FATTO "
                f"documento={esito.get('documento_id')}"
            )
            return
        stile = self.style.ERROR if esito["esito"] == "errore" else self.style.WARNING
        etichetta = "ERRORE" if esito["esito"] == "errore" else "RIPROVA"
        self.stderr.write(stile(
            f"  coda={coda_id} fattura={fattura_id}: {etichetta} "
            f"code={esito.get('code')}"
        ))

    # Scopo: riepilogo del giro di drenaggio in coda al log.
    def _print_summary(self, summary: dict) -> None:
        if summary["claimate"] == 0:
            recuperate = summary.get("recuperate", 0)
            self.stdout.write(
                "Nessuna stampa in coda da lavorare."
                + (f" (recuperate {recuperate} righe stantie)" if recuperate else "")
            )
            return
        self.stdout.write(self.style.SUCCESS(
            f"Drenaggio completato: claimate={summary['claimate']} "
            f"fatto={summary['fatto']} errore={summary['errore']} "
            f"riprovabili={summary['riprovabili']} "
            f"(recuperate={summary.get('recuperate', 0)})"
        ))
