# Endpoint POST /api/v1/auth/logout/ — Logout utente

## Scopo

Revoca la sessione del refresh token corrente (blacklist di tutti i token col
suo `sid`), registra l'evento LOGOUT nella tabella `dbops.sessioni_utente` e
cancella il cookie di refresh dal browser.

## Contesto

Chiamato dal frontend quando l'utente esegue il logout. Il refresh token non
arriva nel corpo ma dal cookie HttpOnly `zeroerp_refresh` (dal 2026-09-28, BB
`apps/core/api/refresh_cookie.py`; attributi del cookie in
[api_multi_veste_token.md](api_multi_veste_token.md#cookie-di-refresh)).

L'endpoint revoca la **sessione**, non il solo token presentato: blocca tutti
i token dell'utente con lo stesso `sid` (BB `blocca_token_sessioni`), cosi' un
successore gia' emesso da una rotazione in volo non resta valido. Poi registra
l'evento LOGOUT tramite `session_audit_service.record_logout()`. La CTE in
`list_sessioni_attive()` esclude automaticamente le sessioni il cui ultimo
evento e' LOGOUT.

Il logout e' **idempotente**: se il token e' illeggibile, di un altro utente o
senza sessione, l'endpoint restituisce comunque 204 senza revocare nulla (il
caso anomalo va nel log `security`).

## Input

- **Autenticazione**: JWT Bearer token (header `Authorization: Bearer <access_token>`)
- **Cookie**: `zeroerp_refresh` — il refresh token della sessione da chiudere,
  mandato dal browser da solo (`Path=/api/v1/`)
- **Body**: vuoto

### Esempio request

```http
POST /api/v1/auth/logout/
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
Cookie: zeroerp_refresh=eyJhbGciOiJIUzI1NiIs...
```

Non serve l'header anti-CSRF `X-Requested-With`: l'endpoint pretende gia' il
Bearer, che un altro sito non ha.

## Output

- **204 No Content** — logout eseguito (o niente da revocare)
- Nessun body nella risposta
- Ogni risposta, tranne l'errore per cookie assente, **cancella il cookie**:

```http
HTTP/1.1 204 No Content
Set-Cookie: zeroerp_refresh=""; expires=Thu, 01 Jan 1970 00:00:00 GMT; Max-Age=0; Path=/api/v1/; SameSite=Strict
```

## Regole

- Se il cookie `zeroerp_refresh` e' assente o vuoto, l'endpoint solleva `E_LOGOUT_NO_TOKEN` (400)
- La **firma** del refresh si verifica (il `sid` decide quale sessione si revoca), la **scadenza** no: il logout con un refresh scaduto chiude lo stesso la sessione. Un token gia' in blacklist e' accettato (e' il caso del refresh ruotato da una richiesta in volo)
- Token con firma estranea, malformato o che non e' un refresh (es. un access token) → 204 senza revoca, log `security.logout_token_non_valido`
- Refresh di un utente diverso da quello autenticato dal Bearer → 204 senza revoca, log `security.logout_token_altrui`
- Refresh senza claim `sid` → 204 senza revoca, log `security.logout_token_senza_sid`
- Altrimenti: blacklist di tutti i token dell'utente col `sid` del refresh, poi evento LOGOUT in `dbops.sessioni_utente` con quel `sid` (nella colonna `jti`)
- Il cookie si cancella con lo stesso `Path` e `SameSite` con cui e' stato scritto (`cancella_refresh_cookie`), in ogni risposta 204: dopo il logout il browser non deve piu' portarlo
- L'evento LOGOUT chiude logicamente la sessione: la CTE `list_sessioni_attive` filtra sessioni il cui ultimo evento e' LOGIN o REFRESH

## Dipendenze DB

| Funzione/Tabella | Schema | Ruolo |
|---|---|---|
| `sessioni_utente` | `dbops` | INSERT evento LOGOUT |

## File backend

| File | Ruolo |
|---|---|
| `apps/core/api/logout_view.py` | `LogoutView(DomainAPIView)`, `skip_area_check = True` — POST con JWT + revoca della sessione + audit + cancellazione del cookie |
| `apps/core/api/refresh_cookie.py` | BB del cookie di refresh: `leggi_refresh_cookie`, `cancella_refresh_cookie` |
| `apps/core/services/revoca_token.py` | `blocca_token_sessioni()` — blacklist dei token della sessione |
| `apps/core/services/session_audit_service.py` | `record_logout()` — delega INSERT al repository |
| `apps/core/db/session_audit_repository.py` | `log_session_event()` — INSERT in `dbops.sessioni_utente` |
| `zeroerp_backend/urls.py` | Rotta `api/v1/auth/logout/` registrata |
| `apps/core/services/error_policies_generated.py` | `E_LOGOUT_NO_TOKEN` a catalogo, classe `DATO_ERRATO` (HTTP 400) |
| `apps/core/tests/api/test_sessioni_view.py` | `LogoutViewTests`: success, no_token, chiude_sessione, token invalido idempotente, token scaduto, firma estranea, token altrui, access token, senza sid |

## Errori

| Codice | HTTP | Quando |
|---|---|---|
| `E_LOGOUT_NO_TOKEN` | 400 | Cookie `zeroerp_refresh` assente o vuoto |

## Note di migrazione

- La tabella `dbops.sessioni_utente` deve essere presente (changeset Liquibase `20260305-01`)
- L'app `token_blacklist` di SimpleJWT deve essere nelle `INSTALLED_APPS` e le relative tabelle migrate
