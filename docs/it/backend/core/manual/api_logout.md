# Endpoint POST /api/v1/auth/logout/ — Logout utente

## Scopo

Invalida il refresh token corrente (blacklist) e registra l'evento LOGOUT
nella tabella `dbops.sessioni_utente`, chiudendo la sessione associata al suo
identificativo di sessione (claim `sid` del token).

## Contesto

Chiamato dal frontend quando l'utente esegue il logout. L'endpoint blacklista
il refresh token via SimpleJWT e registra l'evento LOGOUT tramite
`session_audit_service.record_logout()`. La CTE in `list_sessioni_attive()`
esclude automaticamente le sessioni il cui ultimo evento e' LOGOUT.

Il logout e' **idempotente**: se il token e' gia' blacklistato, scaduto o
malformato, l'endpoint restituisce comunque 204 senza errore.

## Input

- **Autenticazione**: JWT Bearer token (header `Authorization: Bearer <access_token>`)
- **Body** (JSON):

| Campo | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `refresh` | string | si | Refresh token JWT da invalidare |

### Esempio request

```json
{
  "refresh": "eyJhbGciOiJIUzI1NiIs..."
}
```

## Output

- **204 No Content** — logout eseguito (o token gia' invalido)
- Nessun body nella risposta

## Regole

- Se il campo `refresh` e' assente, vuoto o non stringa, l'endpoint solleva `E_LOGOUT_NO_TOKEN` (400)
- Se il token e' malformato, scaduto o gia' blacklistato (`TokenError`), l'endpoint restituisce 204 senza propagare errore — logout idempotente
- Il claim `sid` viene letto dal token **senza** verificarne firma e scadenza, cosi' il logout si registra anche con un token scaduto
- Dopo il blacklist, viene registrato l'evento LOGOUT in `dbops.sessioni_utente` con quel `sid` (nella colonna `jti`). Se il `sid` non si legge (token malformato o senza claim) **nessun evento** viene registrato: la risposta resta 204
- Un body JSON che non e' un oggetto (es. una lista) e' un 400 `E_VALIDATION_INPUT` (BB `corpo_oggetto`, F-9, 2026-09-27)
- L'evento LOGOUT chiude logicamente la sessione: la CTE `list_sessioni_attive` filtra sessioni il cui ultimo evento e' LOGIN o REFRESH

## Dipendenze DB

| Funzione/Tabella | Schema | Ruolo |
|---|---|---|
| `sessioni_utente` | `dbops` | INSERT evento LOGOUT |

## File backend

| File | Ruolo |
|---|---|
| `apps/core/api/logout_view.py` | `LogoutView(DomainAPIView)`, `skip_area_check = True` — POST con JWT + blacklist + audit |
| `apps/core/services/session_audit_service.py` | `record_logout()` — delega INSERT al repository |
| `apps/core/db/session_audit_repository.py` | `log_session_event()` — INSERT in `dbops.sessioni_utente` |
| `zeroerp_backend/urls.py` | Rotta `api/v1/auth/logout/` registrata |
| `apps/core/services/error_policies_generated.py` | `E_LOGOUT_NO_TOKEN` a catalogo, classe `DATO_ERRATO` (HTTP 400) |
| `apps/core/tests/api/test_sessioni_view.py` | `LogoutViewTests`: success, no_token, token invalido idempotente, token scaduto, chiude_sessione |

## Errori

| Codice | HTTP | Quando |
|---|---|---|
| `E_LOGOUT_NO_TOKEN` | 400 | Campo `refresh` assente o vuoto nel body |

## Note di migrazione

- La tabella `dbops.sessioni_utente` deve essere presente (changeset Liquibase `20260305-01`)
- L'app `token_blacklist` di SimpleJWT deve essere nelle `INSTALLED_APPS` e le relative tabelle migrate
