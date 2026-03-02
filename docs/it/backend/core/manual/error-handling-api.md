# Error handling API (Core Django)

## Scopo

Definire un contratto errore uniforme per tutte le API backend Django.

## Contesto

La logica condivisa e` centralizzata in:

- `apps/core/services/error_manager.py`
- `apps/core/services/error_policies.py`
- `apps/core/services/service_errors.py`
- `apps/core/services/error_translator.py`
- `apps/core/api/error_responses.py` — envelope errori + DRF exception handler
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
- Le view API dominio **non devono** usare `try/except Exception` generici: il middleware globale gestisce il fallback.
- Middleware globale intercetta eccezioni non gestite solo su path `/api/*`, lasciando invariato il comportamento Django su pagine non API e su eccezioni `Http404`/`PermissionDenied`.
- Flag attivazione middleware: `DJANGO_API_EXCEPTION_MIDDLEWARE_ENABLED` (`1` default, `0` disabilita).
- Errori `retryable` includono header `Retry-After` (default 3s, configurabile via `DJANGO_API_RETRY_AFTER_SECONDS`).
- Sanitizzazione detail tecnico verso client:
  - default `DJANGO_API_EXPOSE_TECHNICAL_DETAILS=0` (non espone stack SQL/PLpgSQL)
  - opzionale in debug mirato: `DJANGO_API_EXPOSE_TECHNICAL_DETAILS=1`
  - i dettagli completi restano nei log interni e sono correlabili via `request_id`.
- Contratto messaggi tecnici:
  - `message`: sempre business/safe in produzione per codici tecnici.
  - `technical_message`: presente solo con `DJANGO_API_EXPOSE_TECHNICAL_DETAILS=1`.

## DRF exception handler

Un custom exception handler (`drf_exception_handler`) e` registrato in `settings.REST_FRAMEWORK["EXCEPTION_HANDLER"]`.
Converte le eccezioni DRF auth/permessi nell'envelope standard del progetto:

| Eccezione DRF          | Codice errore              |
| ---------------------- | -------------------------- |
| `NotAuthenticated`     | `E_NOT_AUTHENTICATED`      |
| `AuthenticationFailed` | `E_AUTHENTICATION_FAILED`  |
| `PermissionDenied`     | `E_PERMISSION_DENIED`      |

La risposta include sempre `meta.request_id` (e `meta.idempotency_key` se presente).
Le eccezioni DRF non mappate passano invariate al handler default DRF.

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

## Modalita` debug dettaglio tecnico

Questa sezione regola cosa vede il client API in caso di errore tecnico (`E_DATABASE`, `E_PIPELINE`, `E_GENERICO`).

### Modalita` standard (consigliata)

- `DJANGO_API_EXPOSE_TECHNICAL_DETAILS=0` (default)
- `error.message` = messaggio business/safe
- `error.detail` = testo sanitizzato con `request_id`
- `error.technical_message` = assente

Esempio:

```json
{
  "error": {
    "code": "E_DATABASE",
    "message": "Errore durante l'operazione database.",
    "detail": "Dettaglio tecnico non esposto. Usa request_id=<uuid> per supporto."
  }
}
```

### Modalita` debug tecnico (solo temporanea)

- `DJANGO_API_EXPOSE_TECHNICAL_DETAILS=1`
- `error.message` puo` contenere testo tecnico
- `error.technical_message` presente con dettaglio tecnico completo

Uso consigliato:

- attivare solo durante analisi incidente
- disattivare a fine analisi
- usare sempre `request_id` per correlare i log server/DB

### Come attivare/disattivare

In `backend/env.sh`:

```bash
export DJANGO_API_EXPOSE_TECHNICAL_DETAILS=1
```

In `backend/.env.systemd`:

```bash
DJANGO_API_EXPOSE_TECHNICAL_DETAILS=1
```

Applicazione:

```bash
sudo systemctl restart zeroerp-gunicorn
```

Ritorno alla modalita` standard:

```bash
# valore consigliato produzione
export DJANGO_API_EXPOSE_TECHNICAL_DETAILS=0
sudo systemctl restart zeroerp-gunicorn
```
