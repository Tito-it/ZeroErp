# session_audit_service (Core Django)

## Scopo

Registrare eventi di sessione JWT (login, refresh) nella tabella `dbops.sessioni_utente`.

## Contesto

Service in `apps/core/services/session_audit_service.py`. Chiamato dalle auth views override (`AuditTokenObtainPairView`, `AuditTokenRefreshView`) dopo emissione/refresh token con successo. Utilizza il repository `SessionAuditRepository` per INSERT diretto.

## Input

### `record_login(user_id, request, *, jti=None, dettaglio=None)`

- `user_id` (int) — ID auth_user autenticato
- `request` (HttpRequest) — request Django (per IP, User-Agent)
- `jti` (str, opzionale) — JWT ID del token emesso
- `dettaglio` (dict, opzionale) — dati aggiuntivi serializzati in JSONB

### `record_refresh(user_id, request, *, jti=None, dettaglio=None)`

Stessa firma di `record_login`.

## Output

Nessun valore restituito. Effetto: INSERT in `dbops.sessioni_utente`.

## Regole

- Gestione errori **silent**: se l'INSERT fallisce (DB down, schema mancante), l'errore viene loggato ma non propagato. Il flusso di login/refresh non viene interrotto.
- IP client estratto da `X-Forwarded-For` (primo IP) con fallback su `REMOTE_ADDR`.
- User-Agent troncato a 500 caratteri per evitare inserimenti anomali.
- `request_id` recuperato dal `RequestContextMiddleware` via `get_request_id()`.

## Dipendenze DB

- `dbops.sessioni_utente` (INSERT)

## Note di migrazione

- La tabella `dbops.sessioni_utente` e' creata via Liquibase (changeset `20260305-01`). Il service funziona solo dopo l'applicazione del changeset sul DB.
