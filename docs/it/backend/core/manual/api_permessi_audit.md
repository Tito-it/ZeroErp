# ApiPermessiAudit (Core Django)

## Scopo

Endpoint che restituisce la timeline audit delle modifiche ai permessi di un utente.
Interroga le 8 tabelle storico del sistema permessi (5 per utente + 3 per reparto) con filtri opzionali e paginazione.

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

## Tabelle storico interrogate (8)

L'elenco vive in `PermissionsAuditRepository._USER_TABLES` / `_DEPT_TABLES`
(`backend/apps/core/db/permissions_audit_repository.py`). Il valore del filtro
`tabella` e' il **label** (seconda colonna), non il nome fisico.

### Filtro per `auth_user_id` (snapshot)

| Tabella storico                  | Label                    | Contenuto                                                    |
| -------------------------------- | ------------------------ | ------------------------------------------------------------ |
| `storico.user_override_aree`     | `user_override_aree`     | Override livello area                                        |
| `storico.user_override_oggetti`  | `user_override_oggetti`  | Override livello oggetto                                     |
| `storico.user_override_azioni`   | `user_override_azioni`   | Override azione processo                                     |
| `storico.user_emittenti_fiscali` | `user_emittenti_fiscali` | Whitelist emittenti                                          |
| `storico.identita_digitali`      | `identita_digitali`      | Identita' dell'utente: `ruolo_applicativo`, attivo, validita', blocco |

⛔ **Dal 2026-09-12 il bridge legacy `risorse_umane_auth_user` non e' piu' una
sorgente** (decisione Tid): dismesso dal multi-face auth, `attivo = f` in
`dbops.audit_sources`, shadow vecchia droppata. La storia dell'identita' e' in
`identita_digitali`. Chi filtrava con `?tabella=risorse_umane_auth_user`
riceve ora `400 E_CORE_VALIDATION` (contratto rotto di proposito: non in
produzione, e il label morto non deve sembrare vivo).

### Filtro per `unita_organizzativa_id` (reparto)

| Tabella storico                      | Label                      | Filtro nello snapshot                                        |
| ------------------------------------ | -------------------------- | ------------------------------------------------------------ |
| `storico.profili_accesso_aree`       | `profili_accesso_aree`     | indiretto: `profilo_accesso_id` risolto via binding REPARTO corrente |
| `storico.profili_accesso_azioni`     | `profili_accesso_azioni`   | idem                                                         |
| `storico.profili_accesso_bindings`   | `profili_accesso_bindings` | diretto: `unita_organizzativa_id`                            |

## Dipendenze DB

- `storico.*` (8 tabelle) -- generate da `script.trgfn_storico_generic()`
- `script.fn_get_uo_id_for_user` -- risoluzione `unita_organizzativa_id`
  (catena `identita_digitali -> soggetti_ruoli -> risorse_umane`, via
  `PermissionResolver.get_unita_organizzativa_id`)
- `config.profili_accesso` + `config.profili_accesso_bindings` -- per il filtro
  indiretto delle tabelle profilo

## Test

`apps/core/tests/api/test_permissions_audit.py` -- 11 test unitari.
