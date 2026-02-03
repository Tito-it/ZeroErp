# fn_execute_pipeline_step (Django)

## Scopo
Eseguire un singolo step di pipeline, applicando i task definiti nello step corrente.

## Contesto
La funzione SQL `vendite.fn_execute_pipeline_step()` e` stata migrata lato backend Django.
La logica applicativa ora vive in:
- `apps/vendite/services/pipeline_service.py` (`fn_execute_pipeline_step`)
- `apps/vendite/services/pipeline_step_executor.py` (`PipelineStepExecutor.execute_step`)

## Input
- `lotto_id`
- `stato_doc_fiscale_id` (step corrente)
- `rollback` (usa definizione `rollback` invece di `processi`)
- `dry_run`

## Output
- nessun valore di ritorno
- log task/fase su `vendite.fatturazione_lotti_log`
- eventuale errore applicativo (`ServiceError`)

## Regole
- Validazione parametri obbligatori (`lotto_id`, `stato_doc_fiscale_id`).
- Recupero contesto lotto obbligatorio (`competenza_mese` e campi necessari ai task).
- Lettura configurazione task JSON da `vendite.fatturazione_pipeline`.
- Ogni task viene loggato prima dell'esecuzione.
- `dry_run` e task `noop`/`log_only` non eseguono side effect.
- Per `select_attivita`, funzione ammessa solo se in whitelist (`vendite.fn_select_attivita_fatturabili`).
- Per `generate_fatture_righe`, funzione ammessa solo se in whitelist (`vendite.fn_generate_fatture_righe`).
- Task non riconosciuti -> `E_TASK_NOT_IMPLEMENTED`.

## Dipendenze DB
- Lettura pipeline da `vendite.fatturazione_pipeline`
- `vendite.fn_log_pipeline_fase(...)`
- `vendite.fn_select_attivita_fatturabili(...)`
- `vendite.fn_get_or_create_fattura_header(...)`
- Funzioni/trigger di integrita` e coerenza dati restano in DB

## Matrice responsabilita` (Python vs DB)
- Python (step executor): validazione input, dispatch task da JSON, whitelist task/funzioni, controllo `dry_run`/`rollback`.
- DB (funzioni/tabelle): lettura configurazione pipeline, logging persistente, esecuzione logica dati massiva (`fn_select_attivita_fatturabili`), creazione header fattura, enforcement integrita`.

## Note di migrazione
- Stato attuale: migrazione completata lato Python per orchestrazione task.
- Non viene eseguito SQL dinamico da input esterno; il dispatch task e` esplicito nel codice.
- Estensioni future: aggiungere nuovi task mantenendo mapping esplicito in `PipelineStepExecutor`.
