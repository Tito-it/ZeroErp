# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: I CODICI dei processi automatici che il backend esegue — il nome con cui
#        un command headless si dichiara sul giornale dei run
#        (`maintenance.job_run_log.processo_codice`).
# Note: ⛔ NON e' un secondo catalogo. La verita' sta in `dbops.processi`
#        (classe, canale, descrizione, stato); qui c'e' solo il NOME, perche' il
#        Python deve poterlo scrivere. Copiare qui la classe o il canale
#        creerebbe la seconda sorgente che poi diverge in silenzio.
#        ⭐ Il presidio non e' un test: e' la FK `fk_job_run_log_processi`. Un
#        refuso in questo modulo non passa inosservato — la prima corsa del job
#        fallisce all'INSERT, invece di scrivere una riga con l'attore sbagliato.
#        ⚠️ Solo i processi che il BACKEND avvia. I dodici job pgAgent si
#        dichiarano da soli: `maintenance.fn_run_and_log` deriva il codice dal
#        jobname, e li' la derivazione e' COMPLETA (il jobname *e'* il codice).
#        Brief: work-in-progress/piano-be-fe-processi-automatici-identita-e-perimetro.md §1.2
# ------------------------------------------------------------

from __future__ import annotations

# ── Processi su canale COMMAND (management command / cron / systemd) ──────
# Il valore e' il `dbops.processi.codice`, non il nome del command: coincidono
# oggi per tutti e sei, ma e' una coincidenza di nomi, non un contratto.
PROCESSO_RUN_FATTURAZIONE_BATCH = "run_fatturazione_batch"
PROCESSO_DRAINA_CODA_STAMPA = "draina_coda_stampa"
PROCESSO_DRAINA_CODA_LAVORI = "draina_coda_lavori"
PROCESSO_SEND_PENDING_EMAILS = "send_pending_emails"
PROCESSO_SYNC_AUTH_USER_ACTIVE = "sync_auth_user_active"
PROCESSO_LISTEN_CAMBIO_REPARTO = "listen_cambio_reparto"

# ⚠️ `chiusura_scadenze_daily` (canale CODA_AUTOMATICA) NON sta qui, di
#    proposito: il backend non lo avvia e non lo accoda — lo sveglia pgAgent con
#    `dbops.fn_accoda_chiusura_scadenze`. Il legame fra il tipo di coda
#    `CHIUSURA_SCADENZE` e quel processo lo tiene il database
#    (`coda_lavori_tipi.processo_codice`), e l'handler non ha bisogno di
#    nominarlo. Una costante che nessuno legge e' un nome in piu' da tenere
#    allineato.

# ⚠️ I due processi su canale CODA (`FATTURAZIONE_GIRO`, `FATTURAZIONE_NUMERA`)
#    NON stanno qui: le loro costanti esistono gia' in
#    `apps/vendite/services/_fatturazione_job_helpers.py` come `JOB_TYPE_*`,
#    perche' li' quel valore serve come **tipo di coda**, non come attore di un
#    run. Il fatto che i due vocabolari coincidano e' un legame che il database
#    tiene (`coda_lavori_tipi.processo_codice` → `processi.codice`), non una
#    ragione per scrivere il letterale una terza volta.
