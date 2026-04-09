# JwtAuditMiddleware (Core Django)

## Scopo

Middleware Django per le request `/api/*`. Tre responsabilita':

1. Pre-load della cache permessi Redis L2 sulla request (riusata da `ZeroERPPermission`).
2. Rifiuto early degli utenti `ruolo_sistema = DISABILITATO` con HTTP 403.
3. Reset simmetrico delle GUC PG (`app.jwt_user`, `app.current_user_id`) settate
   da `JwtAuditAuthentication` durante l'autenticazione DRF.

> **Importante — la propagazione delle GUC NON avviene piu' qui.**
> A partire dallo sprint BE-2.0ter (refactor operatore-emittenti), il setting
> delle GUC e' demandato a [`JwtAuditAuthentication`](jwt_audit_authentication.md),
> registrata in `REST_FRAMEWORK.DEFAULT_AUTHENTICATION_CLASSES`. Vedi guida
> [Risorse umane e accessi](/guide/risorse-umane-e-accessi) sezione
> "Propagazione identita utente al database (GUC)".

## Contesto

Classe in `apps/core/middleware/jwt_audit_middleware.py`.
Registrata in `settings.MIDDLEWARE` dopo `AuthenticationMiddleware`.

## Funzionalita'

### 1. Pre-load cache permessi L2 (Redis)

Per le richieste su path `/api/`, se `request._zeroerp_perms_cache` non esiste:

- Chiama `load_user_cache(user.id)` per caricare la cache L2 da Redis
- Crea `request._zeroerp_perms_cache` (dict) e `request._zeroerp_perms_cache_loaded_from_redis` (bool)
- `ZeroERPPermission._get_cache()` riusa questa cache senza query aggiuntive

### 2. Rifiuto anticipato DISABILITATO

Per le richieste su path `/api/`:

- Legge `ruolo_sistema` via `PermissionResolver.get_ruolo_sistema()` con la cache per-request
- Se `DISABILITATO` → logga warning di sicurezza e restituisce 403 JSON con codice `E_USER_DISABILITATO`

### 3. Reset GUC simmetrico

`process_response` resetta le GUC `app.jwt_user` e `app.current_user_id` a stringa
vuota **se e solo se** `JwtAuditAuthentication` ha settato il marker
`request._zeroerp_jwt_guc_set = True`. Una sola `cursor.execute` con
`SELECT set_config('app.jwt_user', '', false), set_config('app.current_user_id', '', false)`.

**Perche' condizionale**: i `SimpleTestCase` API girano con request anonime a livello
middleware (la JWT auth gira nel view dispatch DRF, dopo i middleware), quindi senza
il marker il reset farebbe `cursor.execute` su una connessione vietata da
`DatabaseOperationForbidden`. Il marker garantisce simmetria perfetta: si resetta solo
quando le GUC sono state davvero impostate.

**Defense-in-depth**: oggi `CONN_MAX_AGE = 0` (default Django) chiude la connessione
a fine request, quindi il reset e' superfluo. Resta come blindatura per futuri scenari
con `CONN_MAX_AGE > 0` o pgbouncer transaction-mode dove le GUC potrebbero leak fra
request sulla stessa connessione.

### 4. Utenti anonimi

Per utenti non autenticati o path non-API, il middleware non esegue alcuna operazione
(nessuna cache, nessun check ruolo, nessun reset).

## Formato risposta 403 DISABILITATO

```json
{
  "error": {
    "code": "E_USER_DISABILITATO",
    "message": "Utente disabilitato."
  },
  "meta": {
    "request_id": "<uuid>"
  }
}
```

La sezione `meta` include `request_id` (sempre) e `idempotency_key` (se presente nell'header).

## Security logging

Il rifiuto DISABILITATO genera un log:

```text
security.user_disabilitato user_id=<id> path=<path>
```

## Flusso

```text
process_view(request, ...)
  │
  ├── path non /api/* o user anonimo → None (prosegui)
  │
  ├── Pre-load cache L2 da Redis (load_user_cache)
  ├── ruolo = PermissionResolver.get_ruolo_sistema(user, cache)
  └── ruolo == DISABILITATO? → log warning + JsonResponse 403

process_response(request, response)
  │
  ├── request._zeroerp_jwt_guc_set non settato? → return response
  │
  ├── set_config('app.jwt_user',        '', false)   ┐ una sola
  └── set_config('app.current_user_id', '', false)   ┘ execute
```

## Dipendenze

- `anagrafiche.risorse_umane_auth_user` — lettura `ruolo_sistema` (via `PermissionResolver`)
- `apps.core.services.permissions_cache` — `load_user_cache()` per pre-caricamento L2
- `apps.core.services.permissions_resolver` — `PermissionResolver.get_ruolo_sistema()`
- `apps.core.services.request_context` — `get_request_id()`, `get_idempotency_key()` per meta 403
- `apps.core.api.jwt_audit_authentication.JwtAuditAuthentication` — setta il marker letto
  da `process_response`

## Note

- Il check `DISABILITATO` nel middleware e' **defense-in-depth**: `ZeroERPPermission` effettua
  lo stesso controllo a livello DRF. Il middleware agisce prima, evitando che la request
  raggiunga la view.
- **Storico audit pre-fix**: tutti i record creati prima dello sprint BE-2.0bis (2026-04-XX)
  hanno `user_insert`/`user_update` popolati con il ruolo DB (`zeroerp_app`/`titodb`)
  anziche' lo username JWT, perche' la GUC `app.jwt_user` non veniva propagata correttamente.
  Lo storico non viene riscritto. Dal fix BE-2.0ter in poi, l'audit JWT funziona
  correttamente per tutte le request `/api/*` JWT.

## Test

`apps/core/tests/middleware/test_jwt_audit_middleware.py` — 9 test unitari.
