# Auth Views Audit (Core Django)

## Scopo

Override delle view SimpleJWT per registrare eventi di login e refresh nella tabella `dbops.sessioni_utente`.

## Contesto

File `apps/core/api/auth_views.py`. Contiene due classi che estendono le view standard di SimpleJWT agganciando il logging delle sessioni dopo ogni operazione con successo.

### `AuditTokenObtainPairView`

Estende `TokenObtainPairView`. Dopo login con successo (HTTP 200), chiama `session_audit_service.record_login()` con lo `user_id` dell'utente autenticato.

### `AuditTokenRefreshView`

Estende `TokenRefreshView`. Dopo refresh con successo (HTTP 200), chiama `session_audit_service.record_refresh()` decodificando lo `user_id` dal refresh token nel body.

## Input

- `POST /api/v1/auth/token/` — credenziali `username` + `password` (login)
- `POST /api/v1/auth/token/refresh/` — `refresh` token (refresh)

## Output

Stessi output delle view SimpleJWT standard:
- Login: `{"access": "...", "refresh": "..."}`
- Refresh: `{"access": "..."}`

Effetto aggiuntivo: INSERT in `dbops.sessioni_utente`.

## Regole

- Il logging avviene **solo** dopo risposta con successo (status 200). Login/refresh falliti non generano record.
- Se il logging fallisce, l'errore e' gestito silenziosamente dal service (non interrompe la response).
- Le view sono registrate in `zeroerp_backend/urls.py` con `permission_classes=[AllowAny]` (endpoint pubblici di autenticazione).
- Estrazione `user_id` nel refresh: decodifica del refresh token via `RefreshToken(refresh_str)` per ottenere il claim `user_id`.

## Dipendenze DB

- `dbops.sessioni_utente` (INSERT via `session_audit_service`)

## Note di migrazione

- Le view sostituiscono `TokenObtainPairView` e `TokenRefreshView` nel routing. Il contratto HTTP resta identico: nessun impatto sui client.
