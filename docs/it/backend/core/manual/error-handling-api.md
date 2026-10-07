# Error handling API (Core Django)

## Scopo

Definire un contratto errore uniforme per tutte le API backend Django.

## Contesto

La logica condivisa e` centralizzata in:

- `apps/core/services/error_manager.py`
- `apps/core/services/error_policies.py` — `ErrorPolicyRegistry`, mappe classe → HTTP e classe → `ui_action`
- `apps/core/services/error_policies_generated.py` — `CLASSE_PER_CODICE` (codice → classe, generato dal catalogo)
- `apps/core/services/service_errors.py`
- `apps/core/services/error_translator.py`
- `apps/core/api/error_responses.py` — envelope errori + DRF exception handler
- `apps/core/middleware/api_exception_middleware.py`

## Input

- Eccezioni applicative (`ServiceError`)
- Eccezioni DB (`DatabaseError`, SQLSTATE)
- Eccezioni non classificate

## Output

- Envelope JSON coerente (le chiavi con valore `None` vengono omesse):
  - `error.code`
  - `error.message`
  - `error.detail` (opzionale)
  - `error.technical_message` (solo con `DJANGO_API_EXPOSE_TECHNICAL_DETAILS=1` e codice tecnico)
  - `error.hint` (opzionale; mai sui codici tecnici)
  - `error.tx_id` (opzionale)
  - `error.retryable`
  - `error.ui_action` (dalla classe del codice)
  - `error.fields` (opzionale: campi del form da correggere, dal `context={"field": ...}` del `ServiceError`)
  - `error.targets` (opzionale: bersaglio dell'errore; mai sui codici tecnici ne' su HTTP >= 500)
- `meta.request_id` / `meta.idempotency_key`, ciascuno solo se disponibile

## Regole

- Mapping centralizzato in `ErrorPolicyRegistry`: codice → classe (`CLASSE_PER_CODICE` in `error_policies_generated.py`), classe → HTTP status e `ui_action` (`error_policies.py`).
- Traduzione delle eccezioni (`ErrorTranslator.to_api_error`): `ServiceError` → suo codice; `ValueError`/`TypeError` → `E_VALIDATION_INPUT`; `DatabaseError` → codice applicativo estratto dal DB, altrimenti `E_DATABASE` (`E_DATABASE_RETRYABLE` se ritentabile); altro → `E_GENERICO`.
- Nessuna eccezione per `handle_post_json` (dal 2026-10-07, E-6): un `ValueError` dell'handler passa dal translator come altrove, e un corpo illeggibile o non oggetto esce 400 `E_VALIDATION_INPUT` col `context.motivo` (BB `errore_corpo`).
- I domini devono usare `ErrorManager.require(...)` / `ErrorManager.raise_error(...)`.
- Le view API dominio **non devono** usare `try/except Exception` generici: il middleware globale gestisce il fallback.
- Middleware globale intercetta eccezioni non gestite solo su path `/api/*`, lasciando invariato il comportamento Django su pagine non API e su eccezioni `Http404`/`PermissionDenied`/`SuspiciousOperation`.
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
Converte le eccezioni DRF auth/permessi nell'envelope standard del progetto.
Il codice si sceglie cosi':

1. se l'eccezione ha un `default_code` che inizia per `E_` (es. `VesteNonAttivaError` →
   `E_VESTE_NON_ATTIVA`, `JwtSenzaIdentitaError` → `E_JWT_SENZA_IDENTITA`), vince quello;
2. altrimenti si usa la mappa per **classe** (`isinstance`): una sottoclasse prende il codice della madre, per esempio `InvalidToken` di SimpleJWT (token scaduto o invalido) → `E_AUTHENTICATION_FAILED` (E-3, 2026-09-27):

| Eccezione DRF          | Codice errore              |
| ---------------------- | -------------------------- |
| `NotAuthenticated`     | `E_NOT_AUTHENTICATED`      |
| `AuthenticationFailed` | `E_AUTHENTICATION_FAILED`  |
| `PermissionDenied`     | `E_PERMISSION_DENIED`      |

L'envelope porta `code`, il `message` della policy del codice (non il testo
dell'eccezione) e `ui_action`; lo status HTTP resta quello dell'eccezione DRF.
`meta.request_id` / `meta.idempotency_key` compaiono solo se disponibili.
Le eccezioni che non producono un codice passano invariate nel formato default DRF.

> ⚠️ Difetto noto (E-5): i messaggi mirati impostati da `ZeroERPPermission` vengono
> sostituiti dalla frase di `E_PERMISSION_DENIED`. Vedi [analisi difetti](../../../dev/work-in-progress/analisi-be-difetti-emersi-verifica-doc-api-core.md).

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
- `error.message` resta il messaggio business/safe della policy
- `error.detail` resta sanitizzato con `request_id`
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
