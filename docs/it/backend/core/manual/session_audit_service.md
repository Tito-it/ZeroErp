# session_audit_service (Core Django)

## Scopo

Registrare eventi di sessione JWT (login, refresh, logout, revoca) nella tabella `dbops.sessioni_utente`.

## Contesto

Service in `apps/core/services/session_audit_service.py`. Chiamato dalle auth views override
(`AuditTokenObtainPairView`, `AuditTokenRefreshView`) per login/refresh, da `ChangePasswordView`
(LOGIN della nuova coppia di token emessa dopo il cambio password), da `LogoutView` per il
logout, e da `SessioneRevocaView` / `SessioniRevocaTutteView` per la revoca di sessioni.
Utilizza il repository `SessionAuditRepository` per INSERT diretto.

## Input

### `record_login(user_id, request, *, jti=None, dettaglio=None)`

- `user_id` (int) — ID auth_user autenticato
- `request` (HttpRequest) — request Django (per IP, User-Agent)
- `jti` (str, opzionale) — JWT ID del token emesso
- `dettaglio` (dict, opzionale) — dati aggiuntivi serializzati in JSONB

### `record_refresh(user_id, request, *, jti=None, dettaglio=None)`

Stessa firma di `record_login`. Registra evento REFRESH.

### `record_logout(user_id, request, *, jti=None, dettaglio=None)`

Stessa firma di `record_login`. Registra evento LOGOUT.
Chiamato da `LogoutView` dopo il blacklist del refresh token.
L'evento LOGOUT chiude logicamente la sessione: la CTE `list_sessioni_attive`
esclude sessioni il cui ultimo evento non e' LOGIN o REFRESH, e quelle il cui ultimo
evento e' piu' vecchio di 1 giorno (finestra cablata nella query, oggi pari a
`REFRESH_TOKEN_LIFETIME`).

### `record_revoca(user_id, request, *, jti=None, dettaglio=None)`

Stessa firma di `record_login`. Registra evento REVOCA.
Chiamato da `SessioneRevocaView` dopo il blacklist del token outstanding, e da
`SessioniRevocaTutteView` con un evento per ciascuna sessione attiva revocata.
Permette all'utente di chiudere sessioni remote sospette.

## Output

Nessun valore restituito. Effetto: INSERT in `dbops.sessioni_utente`.

## Regole

- Gestione errori **silent**: se l'INSERT fallisce (DB down, schema mancante), l'errore viene loggato ma non propagato. Il flusso di login/refresh/logout non viene interrotto.
- IP client estratto da `X-Forwarded-For` (primo IP) con fallback su `REMOTE_ADDR`.
- User-Agent troncato a 500 caratteri per evitare inserimenti anomali.
- `request_id` recuperato dal `RequestContextMiddleware` via `get_request_id()`.
  ⚠️ Difetto noto ([S-1](../../../dev/work-in-progress/analisi-be-difetti-emersi-verifica-doc-api-core.md)): un `X-Request-ID` del client che non e' un UUID fa fallire
  l'INSERT (colonna `uuid`), e l'evento si perde con il solo log dell'errore.
- Tutti e 4 i metodi delegano a `_log_event()` interno, che compone i parametri e chiama `SessionAuditRepository.log_session_event()`.

## Dipendenze DB

- `dbops.sessioni_utente` (INSERT)

## File backend

| File | Ruolo |
|---|---|
| `apps/core/services/session_audit_service.py` | Funzioni `record_login`, `record_refresh`, `record_logout`, `record_revoca` |
| `apps/core/db/session_audit_repository.py` | `log_session_event()` — INSERT + `list_sessioni_attive()` — CTE query |
| `apps/core/tests/services/test_session_audit_service.py` | Test unitari (mock repository) |

## Note di migrazione

- La tabella `dbops.sessioni_utente` e' creata via Liquibase (changeset `20260305-01`). Il service funziona solo dopo l'applicazione del changeset sul DB.
