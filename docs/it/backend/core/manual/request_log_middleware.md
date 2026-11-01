# RequestLogMiddleware (Core Django)

## Scopo

Registrare ogni request API (`/api/*`, anonime comprese) nella tabella `dbops.request_log` con metodo, path, status, durata e utente.

## Contesto

Middleware in `apps/core/middleware/request_log_middleware.py`. Registrato in `settings.MIDDLEWARE` dopo `JwtAuditMiddleware`. Intercetta solo le request su path `/api/*`, escludendo path configurabili (health, docs, schema, static).

## Input

Nessun input esplicito. Il middleware opera su ogni `HttpRequest` e `HttpResponse` nel ciclo Django.

## Output

Nessun valore restituito. Effetto: INSERT in `dbops.request_log` con i seguenti campi:

| Campo | Origine |
|-------|---------|
| `auth_user_id` | `request.user.id` (NULL se anonimo) |
| `username` | `str(request.user)` se autenticato, altrimenti NULL |
| `request_id` | Da `RequestContextMiddleware` (sempre un UUID: quello del client solo se valido, S-1) |
| `method` | `request.method` (GET, POST, ...) |
| `path` | `request.path` (troncato a 500 char) |
| `query_string` | `request.META["QUERY_STRING"]` (troncato a 1000 char) |
| `status_code` | `response.status_code` |
| `duration_ms` | Calcolato tra `process_request` e `process_response` |
| `ip_address` | `X-Forwarded-For` o `REMOTE_ADDR` |
| `user_agent` | `HTTP_USER_AGENT` (troncato a 500 char) |
| `error_code` | Estratto da `response.content` JSON (`error.code`) se status >= 400 |
| `idempotency_key` | Da `RequestContextMiddleware` (chiave idempotenza della request, se valida) |
| `emittente_attivo_id` | GUC di sessione `app.current_emittente_id`, scritta da `JwtAuditAuthentication` (NULL se assente) |

## Regole

- Logga solo request su path `/api/*`, autenticate o anonime.
- NON logga body request/response (sicurezza + volume).
- Non logga i **percorsi tecnici** (BB `apps/core/services/percorsi_tecnici.py`, `e_percorso_tecnico`): sotto `/api/` contano `/api/docs/` e `/api/schema/`. L'elenco ha una sede sola, condivisa col middleware del fuso: non si configura da settings (fino al 2026-11-01 la doc citava un `REQUEST_LOG_EXCLUDE_PATHS` che nessun settings leggeva).
- Disattivabile via `settings.REQUEST_LOG_ENABLED = False` (env var `DJANGO_REQUEST_LOG_ENABLED`).
- Gestione errori **silent**: se l'INSERT fallisce, l'errore viene loggato ma la response non viene alterata.

## Dipendenze DB

- `dbops.request_log` (INSERT)

## Note di migrazione

- La tabella `dbops.request_log` e' creata via Liquibase (changeset `20260305-02`). Il middleware funziona solo dopo l'applicazione del changeset sul DB.
- Volume alto previsto: valutare partizionamento per mese se necessario.
