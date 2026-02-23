# pr_run_attivita_pipeline (Django)

## Scopo

Orchestrare l'esecuzione della pipeline attivita fatturabili per un lotto, gestendo:

- risoluzione/creazione lotto attivita
- esecuzione branch indipendenti (una sorgente = un branch)
- aggiornamento stato lotto (`IN_ESECUZIONE` → `COMPLETATO`/`ERRORE`)
- tracing task run per branch
- routing errori dominio `ATTIVITA_FATTURABILI`

## Contesto

L'orchestrazione vive in:

- `apps/vendite/services/attivita_pipeline_service.py` (`pr_run_attivita_pipeline`) — facade
- `apps/vendite/services/attivita_pipeline_runner.py` (`AttivitaPipelineRunner.run_pipeline`) — orchestratore
- `apps/vendite/services/attivita_pipeline_step_executor.py` (`AttivitaPipelineStepExecutor.execute_step`) — esecutore step/task
- `apps/vendite/db/attivita_pipeline_repository.py` (`AttivitaPipelineRepository`) — accesso DB
- `apps/vendite/services/attivita_pipeline_error_logger.py` (`AttivitaPipelineErrorLogger`) — log errori

I vincoli di coerenza dati restano delegati al database.

## Input

- `lotto_id` (opzionale; `0`/`None` → crea/risolvi lotto)
- `competenza_mese`
- `utility_id`
- `billing_account_id`
- `sorgente_tipo_id` — filtro opzionale: esegue solo il branch della sorgente specificata
- `emittente_soggetto_ruolo_id`
- `lock_batch_id`
- `meta`
- `dry_run`

## Output

- `lotto_id` elaborato (int)
- stato lotto aggiornato su `vendite.attivita_fatturabili_lotti`
- task run persistiti su `vendite.attivita_fatturabili_lotti_task_runs`

## Regole

### Risoluzione lotto

- Se `lotto_id` e` omesso o `0`, il lotto viene creato/risolto via `vendite.fn_get_or_create_lotto_attivita`.
- Se il lotto esiste ed e` `IN_ESECUZIONE`, il rilancio e` bloccato con `E_ATTIVITA_PIPELINE`.

### Sorgenti e branch

- Le sorgenti abilitate vengono lette tramite `vendite.fn_list_attivita_sorgenti_abilitate(utility_id)` — filtro e ordinamento delegati al DB.
- Ogni sorgente corrisponde a un branch indipendente; il `branch_code` e` attributo della sorgente (es. `DEFAULT`, `PREVENTIVI`).
- Se non ci sono sorgenti abilitate, la pipeline e` bloccata con `E_ATTIVITA_PIPELINE`.
- `sorgente_tipo_id` nel payload filtra i branch: solo il branch corrispondente viene eseguito.

### Semantica block_scope

- Ogni task run persiste il proprio `block_scope` (`BRANCH` o `GLOBAL`).
- **Precedenza**: il `block_scope` della task policy (specifica per task+branch) sovrascrive quello della sorgente branch policy (valore di default).
- `BRANCH` — errore blocca solo il branch corrente; gli altri branch proseguono.
- `GLOBAL` — errore blocca tutti i branch rimanenti; stato finale `ERRORE`.

### Stato lotto

- Transizioni gestite via `vendite.fn_set_attivita_lotto_stato`.
- `stato_lotto` — stato tecnico pipeline: `DRAFT` | `IN_ESECUZIONE` | `COMPLETATO` | `ERRORE`.
- `stato_operativo` — stato business del lotto: `APERTO` | `CHIUSO` | `ANNULLATO`. Non modificato dalla pipeline.

### Task handler

- Handler registrati in `AttivitaPipelineStepExecutor.handler_registry` (7 stub attivi):
  - `acquisisci_preventivi_default`
  - `acquisisci_contratti_default`
  - `acquisisci_ordini_default`
  - `acquisisci_attivita_consumi_default`
  - `normalizza_attivita_default`
  - `valida_attivita_default`
  - `deduplica_attivita_default`
- Task `noop` / `log_only` → saltati senza aprire task run.
- Handler non trovato in registry → `ServiceError(E_ATTIVITA_PIPELINE)`.

### dry_run

- `dry_run=true`: step e task risolti ma handler non chiamati, nessun task run aperto.

## Logging e routing errori

- Log tecnico: `dbops.error_log` (via `ErrorManager`).
- Log dominio attivita: `AttivitaPipelineErrorLogger.log_error` con `scope=ATTIVITA_FATTURABILI`, `severity` I/W/C.
- Nota: tabella log specifica per il dominio attivita non ancora definita; il logger usa `ErrorManager.log_error_only` (log applicativo Django).

## Dipendenze DB

- `vendite.fn_get_or_create_lotto_attivita` — creazione/risoluzione lotto
- `vendite.fn_set_attivita_lotto_stato` — aggiornamento `stato_lotto`
- `vendite.fn_sync_attivita_stato_esecuzione` — sync `stato_esecuzione` su righe attivita
- `vendite.fn_list_attivita_sorgenti_abilitate` — sorgenti abilitate (funzione DB con filtro/ordinamento)
- `vendite.fn_list_attivita_pipeline_steps` — step pipeline per branch
- `vendite.fn_resolve_attivita_pipeline_step` — processi e `pipeline_id` per step
- `vendite.fn_get_attivita_pipeline_task_policy` — policy task (block_scope, depends_on, resume_mode)
- `vendite.fn_start_attivita_lotto_task_run` — apertura task run
- `vendite.fn_complete_attivita_lotto_task_run` — chiusura task run (COMPLETATO)
- `vendite.fn_fail_attivita_lotto_task_run` — chiusura task run (ERRORE)
- `dbops.fn_get_pipeline_task_implementation` — risoluzione handler code da registry DB

## Matrice responsabilita` (Python vs DB)

- **Python** (runner/executor): orchestrazione branch, sequencing step, semantica block_scope, policy dry_run, gestione errori applicativi.
- **DB** (funzioni/tabelle): creazione/risoluzione lotto, persistenza stati e task run, risoluzione step/processi, registry handler, vincoli di integrita`.

## Differenze rispetto a `pr_run_lotto_pipeline`

| Aspetto                  | Lotto                                  | Attivita                                              |
|--------------------------|----------------------------------------|-------------------------------------------------------|
| Step key                 | `stato_doc_fiscale_id` (int)           | `codice_step` (varchar)                               |
| Task runs table          | `fatturazione_lotti_task_runs`         | `attivita_fatturabili_lotti_task_runs`                |
| FK task runs             | `lotto_id`                             | `lotto_attivita_id`                                   |
| Execution mode           | `fn_resolve_lotto_task_execution_mode` | policy raw via `fn_get_attivita_pipeline_task_policy` |
| Block scope persistito   | no                                     | si — `block_scope` su ogni task run                   |
| Orchestrazione           | step sequenziali su lotto singolo      | branch indipendenti (sorgente = branch)               |
| Sorgente→branch resolver | hardcoded in Python                    | DB (`fn_list_attivita_sorgenti_abilitate`)            |
