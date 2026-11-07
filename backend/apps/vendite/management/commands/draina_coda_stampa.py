# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Management command — worker DRAINER della coda stampa documentale
#        (Fase C, step C-2b). È un CHIAMANTE SOTTILE del core condiviso
#        `stampa_coda_drainer_service.draina_coda_stampa_per_roster`
#        (invariante I-1): qui restano solo le responsabilità da cron/systemd —
#        argparse, registrazione run-level (job_run_log) con lock anti-overlap,
#        output console.
#        ⭐ Dal 2026-09-05 NIENTE canale di sistema: il worker gira un emittente
#        alla volta con l'identità del rispettivo utente tecnico. Eseguibile come cron/systemd timer accanto a
#        `run_fatturazione_batch`; drena in background le stampe accodate alla
#        DEFINITIVA e le ristampe on-demand.
#        ⭐ Dal 2026-11-07 un emittente il cui giro non parte chiude la corsa
#        rossa (D9), dopo gli altri: la stessa regola della coda lavori.
# ------------------------------------------------------------

from __future__ import annotations

from apps.core.management.comando_aziendale import ComandoAziendale

from apps.core.services.job_run import (
    ORIGINE_CRON,
    chiudi_se_elementi_non_completati,
    registered_job,
)
from apps.core.services.processi import PROCESSO_DRAINA_CODA_STAMPA
from apps.vendite.services.stampa_coda_drainer_service import (
    draina_coda_stampa_per_roster,
)


class Command(ComandoAziendale):
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

        # ⭐ NIENTE canale di sistema (2026-09-05). Il worker gira un emittente
        # alla volta con l'identita' del rispettivo UTENTE TECNICO: la RLS su
        # `vendite.fatture_stampa_coda` seleziona le righe giuste da se', e
        # l'audit dice chi ha stampato invece di un attore generico.
        # ⚠️ Il lock anti-overlap resta UNO per tutto il giro, non uno per
        #    emittente: due corse ravvicinate del cron devono escludersi a
        #    vicenda per intero — un lock per emittente lascerebbe la seconda
        #    corsa entrare sugli emittenti che la prima non ha ancora raggiunto.
        job_id = PROCESSO_DRAINA_CODA_STAMPA
        with registered_job(
            job_id,
            processo_codice=PROCESSO_DRAINA_CODA_STAMPA,
            origine=ORIGINE_CRON,
            lock_key=job_id,
        ) as job:
            if not job.acquired:
                self.stdout.write(self.style.WARNING(
                    "skip: un altro worker di drenaggio è già in corso."
                ))
                return
            summary = draina_coda_stampa_per_roster(
                on_item_esito=self._print_item_esito,
                on_emittente_esito=self._print_emittente_esito,
                **kwargs,
            )
            self._print_summary(summary)
            job.set_meta(summary)
            job.set_rows_affected(summary.get("claimate", 0))
            # ⭐ Un emittente il cui giro non e' partito lascia le sue stampe in
            #    coda senza che nessuno le abbia guardate: la corsa non chiude
            #    verde (D9), come quella della coda lavori. Il meta e' gia'
            #    scritto. Le righe fallite una per una no: quelle le dice la
            #    coda stessa, con il loro errore.
            chiudi_se_elementi_non_completati(
                job,
                [f["emittente_codice"] for f in summary["emittenti_falliti"]],
                cosa="emittenti con la coda stampa non drenata",
            )

    # Scopo: log di fine giro per un singolo emittente (callback del core).
    def _print_emittente_esito(self, badge, esito, errore) -> None:
        if errore is not None:
            self.stderr.write(self.style.ERROR(
                f"  emittente={badge['emittente_codice']}: ERRORE {errore}"
            ))
            return
        self.stdout.write(
            f"  emittente={badge['emittente_codice']} "
            f"({badge['username']}): claimate={esito['claimate']} "
            f"fatto={esito['fatto']} errore={esito['errore']}"
        )

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
        # ⛔ PRIMA di tutto il resto: gli emittenti che nessun badge copre. Il
        #    loro lavoro non e' stato fatto, e un riepilogo che dicesse solo
        #    «nessuna stampa in coda» sarebbe una bugia per omissione.
        scoperti = summary.get("emittenti_non_serviti") or []
        if scoperti:
            self.stderr.write(self.style.WARNING(
                f"{len(scoperti)} emittente/i senza utente tecnico, NON serviti: "
                f"{', '.join(scoperti)}. Le loro stampe restano in coda finché "
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
                f"Nessuna stampa in coda da lavorare "
                f"({summary.get('emittenti_serviti', 0)} emittente/i guardati)."
                + (f" (recuperate {recuperate} righe stantie)" if recuperate else "")
            )
            return
        self.stdout.write(self.style.SUCCESS(
            f"Drenaggio completato: claimate={summary['claimate']} "
            f"fatto={summary['fatto']} errore={summary['errore']} "
            f"riprovabili={summary['riprovabili']} "
            f"(recuperate={summary.get('recuperate', 0)}, "
            f"emittenti={summary.get('emittenti_serviti', 0)})"
        ))
