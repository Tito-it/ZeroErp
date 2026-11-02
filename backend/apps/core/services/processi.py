# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
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
#        Brief: work-done/piano-be-fe-processi-automatici-identita-e-perimetro.md §1.2
# ------------------------------------------------------------

from __future__ import annotations

# ── Processi su canale COMMAND (management command / cron / systemd) ──────
# Il valore e' il `dbops.processi.codice`, non il nome del command: coincidono
# oggi per tutti e sei, ma e' una coincidenza di nomi, non un contratto.
PROCESSO_RUN_FATTURAZIONE_BATCH = "run_fatturazione_batch"
PROCESSO_DRAINA_CODA_STAMPA = "draina_coda_stampa"
PROCESSO_DRAINA_CODA_LAVORI = "draina_coda_lavori"
PROCESSO_SEND_PENDING_EMAILS = "send_pending_emails"
# ⭐ 2026-10-05: era `listen_cambio_reparto`. Il listener ascolta anche il
#    canale del catalogo dei permessi, e il nome vecchio non lo diceva piu'. A
#    catalogo e' una riga NUOVA (46), non un rinomino: la 24 resta ritirata
#    perche' il giornale ha righe col codice vecchio, legate dalla FK
#    `fk_job_run_log_processi` (brief-db-permessi-catalogo-notify-cache.md §6.2).
PROCESSO_LISTEN_PERMESSI = "listen_permessi"
# ⭐ 2026-09-10: il DESTINATARIO che alle viste di presidio mancava. Classe
#    `MANUTENZIONE` e canale `COMMAND` (riga 26 di `dbops.processi`): legge
#    `dbops` e non i dati di un'azienda, quindi non vuole ne' identita' ne'
#    emittente — e' una lettura periodica che nel dominio non scrive niente.
# ⚠️ Ha DUE corsie, come `run_fatturazione_batch`: si registra sul giornale come
#    `digest_presidi:<cadenza>`, e la chiave del battito resta il codice del
#    processo. Brief: work-done/brief-db-un-destinatario-per-i-presidi.md.
PROCESSO_DIGEST_PRESIDI = "digest_presidi"
# ⭐ 2026-10-13: il giro NOTTURNO degli smoke (`scripts/smoke-baseline.sh`), riga
#    47 di `dbops.processi`: classe `MANUTENZIONE`, canale `COMMAND`, tolleranza
#    NULL (spento di default: non risulta mai «mai partito»). Solo sviluppo: gli
#    smoke scrivono dati di prova. Una corsa con regressioni chiude `ok=false` e
#    la vede `maintenance.vw_job_run_da_guardare`, quindi il digest delle 7.
PROCESSO_SMOKE_NOTTURNO = "smoke_notturno"

# ⛔ `sync_auth_user_active` NON sta piu' qui: la riga 23 di `dbops.processi` e'
#    RITIRATA (`obsoleto_dal = 2026-09-07`) a favore del gemello pgAgent
#    `sync_auth_user_expired_daily` (id 11), che fa lo stesso lavoro da dentro
#    il database ed e' l'unico dei due che il confronto a due fonti riesca a
#    vedere. Il management command sopravvive come attrezzo a mano, e proprio
#    per questo NON si registra piu' sul giornale: un run sotto un processo
#    ritirato e' un attore che il panorama non elenca.
#    ⭐ E non e' solo igiene di catalogo. La LATERAL di
#    `dbops.vw_processi_programmazione` legge il giornale con
#    `processo_codice = codice OR jobname = codice`, SENZA filtrare `origine`:
#    una corsa a mano registrata sotto il gemello sposterebbe avanti
#    `giornale_ultima_corsa` e SPEGNEREBBE il confronto GIRA_E_NON_REGISTRA su
#    quel job — cioe' il rilevatore di R-12, che su `apply_storicizza_weekly` ha
#    lavorato indisturbato per sei mesi e mezzo.
#    Decisione di Tid, 2026-09-07.
#    Brief: work-in-progress/brief-db-sveglia-dei-processi.md §8.5 e §9.5-bis.

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
