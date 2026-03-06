# RequestLogMiddleware (Core Django)

## Scopo

Registrare ogni request API autenticata nella tabella `dbops.request_log` con metodo, path, status, durata e utente.

## Contesto

Middleware in `apps/core/middleware/request_log_middleware.py`. Registrato in `settings.MIDDLEWARE` dopo `JwtAuditMiddleware`. Intercetta solo le request su path `/api/*`, escludendo path configurabili (health, docs, schema, static).

## Input

Nessun input esplicito. Il middleware opera su ogni `HttpRequest` e `HttpResponse` nel ciclo Django.

## Output

Nessun valore restituito. Effetto: INSERT in `dbops.request_log` con i seguenti campi:

| Campo | Origine |
|-------|---------|
| `auth_user_id` | `request.user.id` (NULL se anonimo) |
| `username` | `str(request.user)` |
| `request_id` | Da `RequestContextMiddleware` |
| `method` | `request.method` (GET, POST, ...) |
| `path` | `request.path` (troncato a 500 char) |
| `query_string` | `request.META["QUERY_STRING"]` (troncato a 1000 char) |
| `status_code` | `response.status_code` |
| `duration_ms` | Calcolato tra `process_request` e `process_response` |
| `ip_address` | `X-Forwarded-For` o `REMOTE_ADDR` |
| `user_agent` | `HTTP_USER_AGENT` (troncato a 500 char) |
| `error_code` | Estratto da `response.content` JSON se status >= 400 |

## Regole

- Logga solo request su path `/api/*`.
- NON logga body request/response (sicurezza + volume).
- Path esclusi di default: `/health`, `/api/docs/`, `/api/schema/`, `/static/`, `/media/`.
- Path esclusi configurabili via `settings.REQUEST_LOG_EXCLUDE_PATHS`.
- Disattivabile via `settings.REQUEST_LOG_ENABLED = False` (env var `DJANGO_REQUEST_LOG_ENABLED`).
- Gestione errori **silent**: se l'INSERT fallisce, l'errore viene loggato ma la response non viene alterata.

## Dipendenze DB

- `dbops.request_log` (INSERT)

## Note di migrazione

- La tabella `dbops.request_log` e' creata via Liquibase (changeset `20260305-02`). Il middleware funziona solo dopo l'applicazione del changeset sul DB.
- Volume alto previsto: valutare partizionamento per mese se necessario.
