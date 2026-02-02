# Error handling API vendite (Django)

## Scopo
Definire un contratto errore uniforme per API, backend Django e logica DB.

## Contesto
Il DB usa `config.messaggi_errore`, `script.fn_log_and_raise_error` e `script.fn_log_error_only`.
Il backend Django traduce le eccezioni applicative/DB in un envelope JSON coerente.
La logica e` centralizzata con:
- `apps/core/services/error_manager.py`
- `apps/core/services/error_policies.py`
- `apps/core/services/service_errors.py`
- `apps/core/services/error_translator.py`

## Input
- Eccezioni applicative Python (es. `PipelineError`)
- Eccezioni DB (`DatabaseError`, incluse `DETAIL` e `HINT`)

## Output
- Payload API uniforme:
  - `error.code`
  - `error.message`
  - `error.detail` (opzionale)
  - `error.hint` (opzionale)
  - `error.tx_id` (opzionale)
  - `error.retryable`

## Regole
- Il frontend gestisce per `error.code`, non per testo libero.
- Mapping centralizzato `code -> HTTP status -> ui_action` in `ErrorPolicyRegistry`.
- Errori di servizio -> codice specifico (`E_PIPELINE_*`, `E_TASK_*`, ecc.) secondo policy.
- Errori database -> `E_DATABASE` / `E_DATABASE_RETRYABLE` secondo SQLSTATE.
- Errori non classificati -> `E_GENERICO`.
- Nei servizi usare `ErrorManager.require(...)` e `ErrorManager.raise_error(...)` per evitare duplicazioni.

### Esempio policy UI/API
- `E_PIPELINE_LOTTO_NOT_FOUND` -> `404` -> `show_empty_state`
- `E_DATABASE_RETRYABLE` -> `409` -> `show_retry_dialog`
- `E_TASK_NOT_IMPLEMENTED` -> `501` -> `show_error_banner`

## Dipendenze DB
- `config.messaggi_errore`
- `script.fn_log_and_raise_error`
- `script.fn_log_error_only`

## Note di migrazione
- Stato attuale: helper unico introdotto e applicato ai servizi pipeline vendite.
- Mapping `codice errore -> HTTP status/UI action` introdotto lato backend in `ErrorPolicyRegistry`.
