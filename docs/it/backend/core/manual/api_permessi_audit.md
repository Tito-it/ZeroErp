# ApiPermessiAudit (Core Django)

## Scopo

Endpoint che restituisce la timeline audit delle modifiche ai permessi di un utente.
Interroga le 7 tabelle storico del sistema permessi con filtri opzionali e paginazione.

## Contesto

Classi in `apps/core/api/views.py` (`ApiPermessiAudit`, `ApiPermessiAudit`).
Repository SQL in `apps/core/db/permissions_audit_repository.py`.
URL: `GET /api/v1/core/users/{user_id}/permessi-audit/`

## Input

### Path parameter

| Param     | Tipo | Descrizione       |
| --------- | ---- | ----------------- |
| `user_id` | int  | ID utente target  |

### Query params (opzionali)

| Param       | Tipo   | Default | Descrizione                                                    |
| ----------- | ------ | ------- | -------------------------------------------------------------- |
| `data_da`   | date   | --      | Filtro data inizio (`valid_from >=`), formato `YYYY-MM-DD`     |
| `data_a`    | date   | --      | Filtro data fine (`valid_from <=`), formato `YYYY-MM-DD`       |
| `tabella`   | string | --      | Filtro singola tabella sorgente (es. `user_override_aree`)     |
| `page`      | int    | 1       | Numero pagina                                                  |
| `page_size` | int    | 50      | Dimensione pagina (max 200)                                    |

## Output

```json
{
  "data": {
    "user_id": 5,
    "count": 42,
    "page": 1,
    "page_size": 50,
    "total_pages": 1,
    "events": [
      {
        "tabella": "user_override_aree",
        "timestamp": "2026-02-28T10:30:00+00:00",
        "tipo_operazione": "MODIFICA",
        "user_modifica": "admin_user",
        "snapshot": { "livello": "TUTTO", "area_id": 3 },
        "tx_id": "uuid"
      }
    ]
  },
  "meta": { "request_id": "..." }
}
```

### Valori `tipo_operazione`

| Codice DB | Label         |
| --------- | ------------- |
| 1         | `INIZIALE`    |
| 2         | `MODIFICA`    |
| 3         | `ELIMINAZIONE`|

## Regole

- JWT obbligatorio (via `JWTAuthentication` + `ZeroERPPermission`).
- Stessa policy di `permessi-effettivi`: ADMIN/superuser possono consultare qualsiasi utente,
  OPERATIVO solo se stesso.
- Per utenti senza unita' organizzativa, le tabelle reparto vengono escluse dalla query.
- La view non usa `try/except Exception`: il middleware globale gestisce il fallback.
- Ordinamento: `valid_from DESC` (eventi piu' recenti prima).
- Paginazione con `COUNT(*) OVER()` + `LIMIT/OFFSET`.

## Tabelle storico interrogate (7)

### Filtro per `auth_user_id` (snapshot)

| Tabella storico                   | Contenuto                |
| --------------------------------- | ------------------------ |
| `storico.user_override_aree`      | Override livello area    |
| `storico.user_override_oggetti`   | Override livello oggetto |
| `storico.user_override_azioni`    | Override azione processo |
| `storico.user_emittenti_fiscali`  | Whitelist emittenti      |
| `storico.risorse_umane_auth_user` | Cambio ruolo_sistema     |

### Filtro per `unita_organizzativa_id` (snapshot)

| Tabella storico                    | Contenuto              |
| ---------------------------------- | ---------------------- |
| `storico.profili_reparto_aree`     | Profilo area reparto   |
| `storico.profili_reparto_azioni`   | Profilo azione reparto |

## Dipendenze DB

- `storico.*` (7 tabelle) -- generate da `script.trgfn_storico_generic()`
- `anagrafiche.risorse_umane_auth_user` -- per risoluzione `unita_organizzativa_id`

## Test

`apps/core/tests/api/test_permissions_audit.py` -- 11 test unitari.
