# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Management command del GIRO NOTTURNO DEGLI SMOKE: lancia
#        `scripts/smoke-baseline.sh` (tutti gli smoke, Python e bash) e ne
#        registra l'esito sul giornale dei processi, cosi' una regressione arriva
#        da sola nel digest delle 7.
# Note: ⭐ NASCE DA UN FATTO. Il 2026-10-12 meta' degli smoke bash erano rossi da
#        settimane: non li lanciava nessuno, perche' un giro dura minuti e va
#        ricordato. Un presidio che dipende dalla memoria di qualcuno non presidia.
#
#        ⭐ COME ARRIVA ALLA PERSONA. La corsa si apre e si chiude sempre con
#        `registered_job` (processo `smoke_notturno`, riga 47 di
#        `dbops.processi`). Con regressioni si chiude `ok=false` — sollevando
#        `GiroSmokeFallito`, perche' e' cosi' che il BB segna un esito negativo —
#        e `maintenance.vw_job_run_da_guardare`, presidio del digest giornaliero,
#        la mostra per 7 giorni. Nel `meta` della corsa: non-verdi, regressioni,
#        rientrati, tempi e la cartella con l'output dei rossi.
#
#        ⛔ SOLO SVILUPPO. Gli smoke scrivono documenti di prova sul database.
#        Tre difese, indipendenti: la sveglia e' spenta di default
#        (`sveglie.json`, `abilita: false`), non ha «Esegui ora»
#        (`avvio_manuale: false`), e questo comando rifiuta di partire senza
#        `SMOKE_NOTTURNO_CONSENTITO=1` nell'ambiente — PRIMA di aprire la corsa,
#        cosi' un rifiuto non sporca il giornale.
#
#        ⚠️ Il giro deve chiudere entro l'ora: una corsa aperta da piu' di un'ora
#        esce come «presa e mai chiusa». Il timeout e' sotto quel limite.
# ------------------------------------------------------------

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.management.base import CommandError

from apps.core.management.comando_aziendale import ComandoAziendale
from apps.core.services.job_run import ORIGINE_CRON, registered_job
from apps.core.services.processi import PROCESSO_SMOKE_NOTTURNO
from apps.core.services.sottoprocesso import lancia_con_tetto

ENV_CONSENTITO = "SMOKE_NOTTURNO_CONSENTITO"
# Sotto l'ora dopo la quale la corsa risulta «presa e mai chiusa» (2026-10-13:
# un giro completo durava 13 minuti, con meta' del tempo in attesa sui freni).
TIMEOUT_GIRO_S = 50 * 60
SCRIPT = Path(settings.BASE_DIR).parent / "scripts" / "smoke-baseline.sh"
# La corsia sul giornale: la forma `<processo>:<corsia>` che il `dovuto` della
# sveglia legge (sveglie.json). Una sola corsia oggi, il giro completo.
CORSIA = "completo"
BASH = shutil.which("bash") or "/bin/bash"   # percorso assoluto, non «bash» dal PATH
JOB_NAME = f"{PROCESSO_SMOKE_NOTTURNO}:{CORSIA}"


class GiroSmokeFallito(Exception):
    """Esito negativo del giro: il `code` finisce su `job_run_log.error_code`."""

    def __init__(self, code: str, messaggio: str) -> None:
        super().__init__(messaggio)
        self.code = code


# Scopo: Riassume l'output di `smoke-baseline.sh` in un dizionario per il `meta`
#        della corsa. Legge le righe che lo script stampa per le persone: se un
#        giorno cambiano forma, i campi restano vuoti, e l'esito lo dice comunque
#        il codice d'uscita (0 nessuna regressione, 1 regressioni, 2 errore).
def riassumi(output: str, codice_uscita: int) -> dict[str, Any]:
    testo = output.replace("\r", "\n")
    righe = testo.splitlines()
    esito: dict[str, Any] = {"codice_uscita": codice_uscita}

    m = re.search(r"Non-verdi ora: (\d+) su (\d+)", testo)
    if m:
        esito["non_verdi"], esito["totale"] = int(m.group(1)), int(m.group(2))
    m = re.search(r"giro (\d+)s, di cui attesa sul freno (\d+)s", testo)
    if m:
        esito["durata_s"], esito["attesa_freno_s"] = int(m.group(1)), int(m.group(2))
    m = re.search(r"Output dei non-verdi: (\S+)", testo)
    if m:
        esito["log_dir"] = m.group(1)

    # I nomi sotto le intestazioni delle due sezioni, fino alla riga vuota.
    def _sezione(intestazione: str) -> list[str]:
        nomi: list[str] = []
        dentro = False
        for riga in righe:
            if intestazione in riga:
                dentro = True
                continue
            if dentro:
                if not riga.strip() or riga.strip().startswith("→"):
                    break
                nomi.append(riga.split()[0])
        return nomi

    esito["regressioni"] = _sezione("REGRESSIONI")
    esito["rientrati"] = _sezione("RIENTRATI")
    return esito


class Command(ComandoAziendale):
    help = (
        "Giro notturno degli smoke (solo sviluppo): lancia scripts/smoke-baseline.sh "
        "e registra l'esito sul giornale dei processi."
    )

    def handle(self, *args: Any, **options: Any) -> None:
        if os.environ.get(ENV_CONSENTITO) != "1":
            raise CommandError(
                f"{ENV_CONSENTITO}=1 mancante: il giro degli smoke scrive dati di "
                "prova e gira solo in sviluppo. Nessuna corsa aperta."
            )
        if not SCRIPT.is_file():
            raise CommandError(f"script degli smoke non trovato: {SCRIPT}")

        with registered_job(
            JOB_NAME, processo_codice=PROCESSO_SMOKE_NOTTURNO,
            origine=ORIGINE_CRON, stepname=CORSIA, lock_key=JOB_NAME,
        ) as job:
            if not job.acquired:   # un giro gia' in corso: questa corsa salta
                return
            try:
                # BB `lancia_con_tetto`: sul tetto muore il GRUPPO, cioe' anche gli
                # smoke che lo script ha avviato, non solo lo script.
                fatto = lancia_con_tetto(
                    [BASH, str(SCRIPT)], TIMEOUT_GIRO_S, cwd=SCRIPT.parent.parent,
                )
            except subprocess.TimeoutExpired as exc:
                raise GiroSmokeFallito(
                    "SMOKE_GIRO_FALLITO", f"giro oltre {TIMEOUT_GIRO_S}s: interrotto",
                ) from exc

            esito = riassumi(fatto.stdout + fatto.stderr, fatto.returncode)
            job.set_meta(esito)
            job.set_rows_affected(int(esito.get("non_verdi") or 0))
            job.set_message(
                f"{esito.get('non_verdi', '?')} non verdi su {esito.get('totale', '?')}, "
                f"regressioni {len(esito['regressioni'])}, "
                f"durata {esito.get('durata_s', '?')}s (freno {esito.get('attesa_freno_s', '?')}s)"
            )
            self.stdout.write(job.message or "")

            if fatto.returncode == 1:
                raise GiroSmokeFallito(
                    "SMOKE_REGRESSIONI",
                    "regressioni: " + ", ".join(esito["regressioni"]),
                )
            if fatto.returncode != 0:
                raise GiroSmokeFallito(
                    "SMOKE_GIRO_FALLITO",
                    f"smoke-baseline.sh uscito con {fatto.returncode}: "
                    + (fatto.stderr or fatto.stdout)[-500:],
                )
