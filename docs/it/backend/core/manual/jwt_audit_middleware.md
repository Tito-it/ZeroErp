# JwtAuditMiddleware (Core Django)

## Scopo

Middleware Django che propaga l'identita' dell'utente autenticato nella sessione PostgreSQL
tramite GUC (`SET LOCAL`) e rifiuta anticipatamente gli utenti disabilitati sugli endpoint API.

## Contesto

Classe in `apps/core/middleware/jwt_audit_middleware.py`.
Registrata in `settings.MIDDLEWARE` dopo `AuthenticationMiddleware`.

## Funzionalita'

### 1. Propagazione GUC PostgreSQL

Per ogni richiesta di un utente autenticato, imposta due variabili di sessione PG:

| GUC                    | Valore              | Uso                                            |
|------------------------|---------------------|-------------------------------------------------|
| `app.jwt_user`         | `str(user)`         | Audit trail nei trigger DB                     |
| `app.current_user_id`  | `str(user.id)`      | Trigger guard defense-in-depth (ambito emittente)|

Entrambe usano `SET LOCAL` (valide solo per la transazione corrente).

### 2. Pre-caricamento cache permessi L2 (Redis)

Per le richieste su path `/api/`, se `request._zeroerp_perms_cache` non esiste:

- Chiama `load_user_cache(user.id)` per caricare la cache L2 da Redis
- Crea `request._zeroerp_perms_cache` (dict) e `request._zeroerp_perms_cache_loaded_from_redis` (bool)
- `ZeroERPPermission._get_cache()` riusa questa cache senza query aggiuntive

### 3. Rifiuto anticipato DISABILITATO

Per le richieste su path `/api/`:

- Legge `ruolo_sistema` via `PermissionResolver.get_ruolo_sistema()` con la cache per-request
- Se `DISABILITATO` → logga warning di sicurezza e restituisce 403 JSON con codice `E_USER_DISABILITATO`

### 4. Utenti anonimi

Per utenti non autenticati, il middleware non esegue alcuna operazione (nessun `SET LOCAL`,
nessun check ruolo).

## Formato risposta 403

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
  ├── user non autenticato? → None (prosegui)
  │
  ├── SET LOCAL app.jwt_user = str(user)
  ├── SET LOCAL app.current_user_id = str(user.id)
  │
  ├── path inizia con /api/?
  │     ├── Pre-carica cache L2 da Redis (load_user_cache)
  │     ├── ruolo = PermissionResolver.get_ruolo_sistema(user, cache)
  │     └── ruolo == DISABILITATO? → log warning + JsonResponse 403
  │
  └── None (prosegui)
```

## Dipendenze

- `anagrafiche.risorse_umane_auth_user` — lettura `ruolo_sistema` (via `PermissionResolver`)
- `apps.core.services.permissions_cache` — `load_user_cache()` per pre-caricamento L2
- `apps.core.services.permissions_resolver` — `PermissionResolver.get_ruolo_sistema()`
- `apps.core.services.request_context` — `get_request_id()`, `get_idempotency_key()` per meta 403

## Note

- Il check `DISABILITATO` nel middleware e' **defense-in-depth**: `ZeroERPPermission` effettua
  lo stesso controllo a livello DRF. Il middleware agisce prima, evitando che la request
  raggiunga la view.
- `app.current_user_id` e' pensato per essere usato dai trigger guard DB
  (`config.fn_check_user_emittente_scope`) che verificano l'ambito emittente a livello di riga.

## Test

`apps/core/tests/middleware/test_jwt_audit_middleware.py` — 7 test unitari.
