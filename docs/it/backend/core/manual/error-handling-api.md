# Error handling API (Core Django)

## Scopo
Definire un contratto errore uniforme per tutte le API backend Django.

## Contesto
La logica condivisa e` centralizzata in:
- `apps/core/services/error_manager.py`
- `apps/core/services/error_policies.py`
- `apps/core/services/service_errors.py`
- `apps/core/services/error_translator.py`
- `apps/core/api/error_responses.py`
- `apps/core/middleware/api_exception_middleware.py`

## Input
- Eccezioni applicative (`ServiceError`)
- Eccezioni DB (`DatabaseError`, SQLSTATE)
- Eccezioni non classificate

## Output
- Envelope JSON coerente:
  - `error.code`
  - `error.message`
  - `error.detail` (opzionale)
  - `error.hint` (opzionale)
  - `error.tx_id` (opzionale)
  - `error.retryable`

## Regole
- Mapping centralizzato `code -> HTTP status -> ui_action` in `ErrorPolicyRegistry`.
- I domini devono usare `ErrorManager.require(...)` / `ErrorManager.raise_error(...)`.
- Le API devono convertire eccezioni in risposta usando helper core (`exception_to_error_response`).
- Middleware globale intercetta eccezioni non gestite solo su path `/api/*`, lasciando invariato il comportamento Django su pagine non API e su eccezioni `Http404`/`PermissionDenied`.
- Flag attivazione middleware: `DJANGO_API_EXCEPTION_MIDDLEWARE_ENABLED` (`1` default, `0` disabilita).
- Errori `retryable` includono header `Retry-After` (default 3s, configurabile via `DJANGO_API_RETRY_AFTER_SECONDS`).

## Dipendenze DB
- `config.messaggi_errore`
- `script.fn_log_and_raise_error`
- `script.fn_log_error_only`

## Note di migrazione
- Questo documento e` la fonte condivisa cross-domain.
- Le aree dominio (es. vendite) devono solo documentare l'uso locale della policy.
- Endpoint diagnostico (canonico versionato) disponibile per test rapido envelope:
  - `GET /api/v1/core/diagnostics/error-envelope/`
  - varianti: `?kind=generic|retryable|not_found`
- Compatibilita` temporanea mantenuta anche su `/api/core/diagnostics/error-envelope/`.
