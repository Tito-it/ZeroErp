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
- `tipo_lotto` (`MASSIVO`/`GIORNALIERO`) per leggere la configurazione corretta
- `rollback` (usa definizione `rollback` invece di `processi`)
- `dry_run`

## Output
- nessun valore di ritorno
- log task/fase su `vendite.fatturazione_lotti_log`
- eventuale errore applicativo (`ServiceError`)

## Regole
- Validazione parametri obbligatori (`lotto_id`, `stato_doc_fiscale_id`, `tipo_lotto`).
- Recupero contesto lotto obbligatorio (`competenza_mese` e campi necessari ai task).
- Lettura configurazione task JSON da `vendite.fatturazione_pipeline` filtrando:
  `stato_doc_fiscale_id + tipo_lotto + utility_id + tipo_doc_fiscale_id` con fallback su `NULL`.
- Ogni task viene loggato prima dell'esecuzione.
- I task per-fattura usano un helper riusabile con gestione errori per singolo documento e routing log `scope=FATTURA`.
- Gli errori di orchestrazione/task non attribuibili a singola fattura usano lo stesso logger con `scope=LOTTO`.
- `dry_run` e task `noop`/`log_only` non eseguono side effect.
- Per `select_attivita`, funzione ammessa solo se in whitelist (`vendite.fn_select_attivita_fatturabili`).
- Per `generate_fatture_righe`, funzione ammessa solo se in whitelist (`vendite.fn_generate_fatture_righe`).
- Per `numera_fatture`, funzione ammessa solo se in whitelist (`vendite.fn_numera_fattura_opz_emessa`).
- `implementation_key` nei task JSON risolve l'handler tramite registry DB (`dbops.fn_get_pipeline_task_implementation`).
- Se `implementation_key` assente usa `default`.
- Il campo `params.fn` resta un token di compatibilita` legacy SQL, non un punto di dispatch dinamico libero.
- Task non riconosciuti -> `E_TASK_NOT_IMPLEMENTED`.

## Dipendenze DB
- Lettura pipeline da `vendite.fatturazione_pipeline`
- `vendite.fn_log_pipeline_fase(...)`
- `vendite.fn_select_attivita_fatturabili(...)`
- `vendite.fn_get_or_create_fattura_header(...)`
- `vendite.fn_numera_fattura_opz_emessa(...)`
- `vendite.fn_sync_lotto_fatture_stato(...)`
- `dbops.fn_get_pipeline_task_implementation(...)`
- Funzioni/trigger di integrita` e coerenza dati restano in DB

## Matrice responsabilita` (Python vs DB)
- Python (step executor): validazione input, dispatch task da JSON, whitelist task/funzioni, controllo `dry_run`/`rollback`.
- DB (funzioni/tabelle): lettura configurazione pipeline, logging persistente, esecuzione logica dati massiva (`fn_select_attivita_fatturabili`), creazione header fattura, enforcement integrita`.

## Note di migrazione
- Stato attuale: migrazione completata lato Python per orchestrazione task.
- Non viene eseguito SQL dinamico da input esterno; il dispatch task e` esplicito nel codice.
- Estensioni future: aggiungere nuovi task mantenendo mapping esplicito in `PipelineStepExecutor`.
