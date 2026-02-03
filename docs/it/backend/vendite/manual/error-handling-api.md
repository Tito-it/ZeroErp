# Error handling API vendite (Django)

## Scopo
Documentare come l'area vendite applica il contratto errori condiviso.

## Contesto
La policy errori cross-domain e` definita in:
- `docs/it/backend/core/manual/error-handling-api.md`

Vendite usa i componenti core senza ridefinire policy locali:
- `apps/core/services/error_manager.py`
- `apps/core/api/error_responses.py`

## Input
- Eccezioni applicative vendite (`ServiceError` con codici `E_PIPELINE_*`, `E_TASK_*`, ...)
- Eccezioni DB propagate dai repository

## Output
- Payload API uniforme (definito in area core).

## Regole
- Il frontend gestisce per `error.code`, non per testo libero.
- Mapping centralizzato `code -> HTTP status -> ui_action` in `ErrorPolicyRegistry` (core).
- Nei servizi vendite usare `ErrorManager.require(...)` e `ErrorManager.raise_error(...)`.
- Nelle view vendite usare helper core `exception_to_error_response(...)`.

### Esempio policy UI/API
- `E_PIPELINE_LOTTO_NOT_FOUND` -> `404` -> `show_empty_state`
- `E_DATABASE_RETRYABLE` -> `409` -> `show_retry_dialog`
- `E_TASK_NOT_IMPLEMENTED` -> `501` -> `show_error_banner`

## Dipendenze DB
- `config.messaggi_errore`
- `script.fn_log_and_raise_error`
- `script.fn_log_error_only`

## Note di migrazione
- Stato attuale: vendite allineata al layer errori core condiviso.
- Le evoluzioni policy devono essere fatte in area core e poi riusate da vendite.
