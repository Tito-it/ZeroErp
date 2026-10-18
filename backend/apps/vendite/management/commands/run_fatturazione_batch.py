# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Management command — il PRODUTTORE del giro di fatturazione notturno.
#
#        ⭐ Dal 2026-09-05 NON fattura piu' lui: accoda un lavoro
#        `FATTURAZIONE_GIRO` per ogni azienda servita, con l'identita'
#        dell'utente tecnico di quell'azienda, e il worker della coda li esegue.
#        Prima era una corsa sola che attraversava TUTTE le aziende su un ruolo
#        `BYPASSRLS`: un inciampo su una poteva fermarle tutte, e nessuno poteva
#        dire per conto di chi avesse scritto.
#        ⇒ Adesso ogni azienda ha il suo lavoro, il suo perimetro, e i
#        ritentativi con backoff che la coda porta di suo.
#
#        Qui restano le responsabilita' da cron: argparse, registrazione
#        run-level (`job_run_log`) con lock anti-overlap per corsia, console.
#        ⛔ Il DRY-RUN non esiste piu' in questa forma: non c'e' piu' una
#        discovery da mostrare senza eseguire — l'unica cosa che questo comando
#        fa e' accodare, e «accodare per finta» non dice niente di utile. Chi
#        vuole vedere cosa uscirebbe guarda i cruscotti.
#        Gate fiscale D-1: la corsia immediata completa (numera da sola), la
#        differita si ferma a EMESSA (default di corsia nel core;
#        --fino-a-stato per override diagnostico).
# ------------------------------------------------------------

from __future__ import annotations

from datetime import date, datetime

from django.core.management.base import CommandError
from apps.core.services.fuso_aziendale import oggi_aziendale
from apps.core.management.comando_aziendale import ComandoAziendale

from apps.core.services.job_run import (
    ORIGINE_CRON,
    chiudi_se_elementi_non_completati,
    registered_job,
)
from apps.core.services.processi import PROCESSO_RUN_FATTURAZIONE_BATCH
from apps.vendite.services.fatturazione_driver_service import modalita_disponibili
from apps.vendite.services.fatturazione_produttore_service import (
    accoda_giri_fatturazione,
)


# Scopo: il nome della corsia su `maintenance.job_run_log`. Sede unica: lo
#        scrive questo comando e lo dichiara `dovuto.jobname` in sveglie.json
#        (`test_sveglie` prova che coincidano), da cui `e_dovuto` sa se il
#        lavoro del mese e' gia' fatto.
def jobname_corsia(modalita: str) -> str:
    return f"run_fatturazione_batch:{modalita}"


class Command(ComandoAziendale):
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
            "--fino-a-stato", type=str, default=None,
            help="Override diagnostico della fermata (codice config.stati_doc_fiscale, "
                 "es. EMESSA). Default: la fermata di corsia (immediata=fino in fondo, "
                 "differita=EMESSA per D-1).",
        )

    # Scopo: Risolve la competenza (default = primo del mese corrente).
    def _resolve_competenza(self, raw: str | None) -> date:
        if not raw:
            return oggi_aziendale().replace(day=1)
        try:
            return datetime.strptime(raw, "%Y-%m-%d").date().replace(day=1)  # noqa: DTZ007 — si legge una DATA (formato stretto), non un istante: il fuso non c'entra
        except ValueError as exc:
            raise CommandError(f"--competenza non valida (atteso YYYY-MM-DD): {raw}") from exc

    def handle(self, *args, **options):
        modalita = options["modalita"]
        competenza = self._resolve_competenza(options["competenza"])

        # ⚠️ Il jobname porta la CORSIA (`:immediata`/`:differita`), il codice
        # processo no: sono due cose diverse, ed e' il motivo per cui il BB non
        # deriva l'attore dal nome del job.
        job_id = jobname_corsia(modalita)
        with registered_job(
            job_id,
            processo_codice=PROCESSO_RUN_FATTURAZIONE_BATCH,
            origine=ORIGINE_CRON,
            lock_key=job_id,
        ) as job:
            if not job.acquired:
                self.stdout.write(self.style.WARNING(
                    f"skip: un altro run della corsia '{modalita}' è già in corso."
                ))
                return
            summary = accoda_giri_fatturazione(
                modalita=modalita,
                competenza=competenza,
                fino_a_stato=options.get("fino_a_stato"),
                on_emittente=self._print_emittente,
            )
            self._print_summary(summary)
            job.set_meta(summary)
            job.set_rows_affected(summary["accodati"])
            # ⭐ Un'azienda non accodata non lascia una riga in coda: senza
            #    questo il giro chiuderebbe verde avendola persa (D9).
            chiudi_se_elementi_non_completati(
                job, [f["emittente_codice"] for f in summary["falliti"]],
                cosa="aziende non accodate",
            )

    # Scopo: log per azienda: quale lavoro è stato accodato, o perché no.
    def _print_emittente(self, badge, job_id, errore) -> None:
        if errore is not None:
            self.stderr.write(self.style.ERROR(
                f"  {badge['emittente_codice']}: NON accodato — {errore}"
            ))
            return
        self.stdout.write(
            f"  {badge['emittente_codice']} ({badge['username']}): job={job_id}"
        )

    # Scopo: riepilogo del giro di accodamento.
    def _print_summary(self, summary: dict) -> None:
        # ⛔ PRIMA di tutto: le aziende che nessun badge copre. Il loro mese non
        #    verrà fatturato, e un riepilogo che dicesse solo «2 accodati»
        #    sembrerebbe completo.
        scoperti = summary.get("emittenti_non_serviti") or []
        if scoperti:
            self.stderr.write(self.style.WARNING(
                f"{len(scoperti)} azienda/e senza utente tecnico, NON fatturate: "
                f"{', '.join(scoperti)}. Serve creare l'utente del processo "
                "`run_fatturazione_batch` per ognuna."
            ))
        if not summary["accodati"] and not scoperti:
            self.stdout.write(
                "Nessuna azienda servita da questo processo: niente da accodare."
            )
            return
        self.stdout.write(self.style.SUCCESS(
            f"Accodati {summary['accodati']} giri (corsia={summary['modalita']}, "
            f"competenza={summary['competenza']})"
            + (f", {len(summary['falliti'])} falliti" if summary["falliti"] else "")
        ))
