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
| `app.current_user_id`  | `str(user.id)`      | Trigger guard defense-in-depth (scope emittente)|

Entrambe usano `SET LOCAL` (valide solo per la transazione corrente).

### 2. Rifiuto anticipato DISABILITATO

Per le richieste su path `/api/`:
- Legge `ruolo_sistema` dalla tabella ponte `anagrafiche.risorse_umane_auth_user`
- Se `DISABILITATO` → restituisce 403 JSON con codice `E_USER_DISABILITATO`
- Cache del ruolo su `request._zeroerp_ruolo_sistema` per evitare query duplicata nel resolver

### 3. Utenti anonimi

Per utenti non autenticati, il middleware non esegue alcuna operazione (nessun `SET LOCAL`,
nessun check ruolo).

## Formato risposta 403

```json
{
  "error": {
    "code": "E_USER_DISABILITATO",
    "message": "Utente disabilitato. Contattare l'amministratore."
  }
}
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
  │     ├── ruolo = _get_ruolo_sistema_cached(request)
  │     └── ruolo == DISABILITATO? → JsonResponse 403
  │
  └── None (prosegui)
```

## Dipendenze DB

- `anagrafiche.risorse_umane_auth_user` — lettura `ruolo_sistema`

## Note

- Il check `DISABILITATO` nel middleware e' **defense-in-depth**: `ZeroERPPermission` effettua
  lo stesso controllo a livello DRF. Il middleware agisce prima, evitando che la request
  raggiunga la view.
- `app.current_user_id` e' pensato per essere usato dai trigger guard DB
  (`config.fn_check_user_emittente_scope`) che verificano lo scope emittente a livello di riga.

## Test

`apps/core/tests/middleware/test_jwt_audit_middleware.py` — 5 test unitari.
