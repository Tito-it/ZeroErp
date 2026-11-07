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
#        ⭐ Dal 2026-11-07 (BE10) il giro è per azienda, con l'utente tecnico
#        di ciascuna (`draina_coda_lavori_per_roster`). Un'azienda il cui giro
#        non parte chiude la corsa rossa (D9), dopo le altre.
# ------------------------------------------------------------

from __future__ import annotations

from apps.core.management.comando_aziendale import ComandoAziendale

from apps.core.services.coda_lavori.drainer_service import (
    draina_coda_lavori_per_roster,
)
from apps.core.services.job_run import (
    ORIGINE_CRON,
    chiudi_se_elementi_non_completati,
    registered_job,
)
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
            summary = draina_coda_lavori_per_roster(
                job_run_id=job.id,
                on_item_esito=self._print_item_esito,
                on_emittente_esito=self._print_emittente_esito,
                **kwargs,
            )
            self._print_summary(summary)
            job.set_meta(summary)
            job.set_rows_affected(summary.get("claimate", 0))
            # ⭐ Un'azienda il cui giro non e' partito lascia i suoi lavori in
            #    coda senza che nessuno li abbia guardati: la corsa non chiude
            #    verde (D9). Il meta e' gia' scritto.
            chiudi_se_elementi_non_completati(
                job,
                [f["emittente_codice"] for f in summary["emittenti_falliti"]],
                cosa="aziende con la coda lavori non drenata",
            )

    # Scopo: log di fine giro per una singola azienda (callback del core).
    def _print_emittente_esito(self, badge, esito, errore) -> None:
        if errore is not None:
            self.stderr.write(self.style.ERROR(
                f"  emittente={badge['emittente_codice']}: ERRORE {errore}"
            ))
            return
        self.stdout.write(
            f"  emittente={badge['emittente_codice']} "
            f"({badge['username']}): claimati={esito['claimate']} "
            f"fatto={esito['fatto']} errore={esito['errore']}"
        )

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
        # ⛔ PRIMA di tutto il resto: chi non e' stato guardato. Un riepilogo
        #    che dicesse solo «nessun job in coda» sarebbe una bugia per
        #    omissione.
        if summary.get("roster_vuoto"):
            self.stderr.write(self.style.WARNING(
                "⚠️  Nessun utente tecnico per draina_coda_lavori: la coda NON "
                "e' stata drenata, nemmeno i lavori SISTEMA. Crearne uno per "
                "azienda con script.fn_crea_utente_tecnico."
            ))
        scoperti = summary.get("emittenti_non_serviti") or []
        if scoperti:
            self.stderr.write(self.style.WARNING(
                f"{len(scoperti)} emittente/i senza utente tecnico, NON serviti: "
                f"{', '.join(scoperti)}. I loro lavori restano in coda finché "
                "qualcuno non crea l'utente."
            ))
        for fallito in summary.get("emittenti_falliti") or []:
            self.stderr.write(self.style.ERROR(
                f"emittente {fallito['emittente_codice']}: giro fallito — "
                f"{fallito['errore']}"
            ))
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
