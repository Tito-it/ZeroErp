# ApiPermessiAudit (Core Django)

## Scopo

Endpoint che restituisce la timeline audit delle modifiche ai permessi di un utente.
Interroga le 8 tabelle storico del sistema permessi (5 per utente + 3 per reparto) con filtri opzionali e paginazione.

## Contesto

Classe in `apps/core/api/views.py` (`ApiPermessiAudit`).
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
| `data_da`   | date   | --      | Filtro data inizio (dal giorno indicato), formato `YYYY-MM-DD` |
| `data_a`    | date   | --      | Filtro data fine (fino al giorno indicato **incluso**), formato `YYYY-MM-DD` |
| `tabella`   | string | --      | Filtro singola tabella sorgente (es. `user_override_aree`)     |
| `page`      | int    | 1       | Numero pagina                                                  |
| `page_size` | int    | 25      | Dimensione pagina; oltre 200 viene ridotta a 200 in silenzio   |

`page` e `page_size` accettano solo cifre (altrimenti `E_VALIDATION_INPUT`, 400).

`page` e `page_size` partono da 1 (sotto: 400 `E_VALIDATION_INPUT`, `page_size`
tagliato a 200). `data_a` **include** il giorno indicato: intervallo
`[data_da, data_a + 1 giorno)` (F-4, 2026-09-27), e i giorni sono giorni **dell'azienda** (fuso `SYSTEM_FUSO_ORARIO`, confini calcolati dal DB col BB `predicato_giorno_operativo`, dal 2026-10-09).

## Output

```json
{
  "data": {
    "user_id": 5,
    "count": 42,
    "page": 1,
    "page_size": 25,
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

- JWT obbligatorio (via `JwtAuditAuthentication` + `ZeroERPPermission`, con
  `skip_area_check = True`).
- Stessa policy di `permessi-effettivi`: superuser Django o utenti con binding
  SUPER_ADMIN (`script.fn_is_super_admin`) possono consultare qualsiasi utente; tutti
  gli altri solo se stessi, altrimenti `E_PERMESSO_NEGATO` (403).
- Per utenti senza unita' organizzativa, le tabelle reparto vengono escluse dalla query.
- La view non usa `try/except Exception`: il middleware globale gestisce il fallback.
- Ordinamento: `valid_from DESC` (eventi piu' recenti prima).
- Paginazione con `COUNT(*) OVER()` + `LIMIT/OFFSET`.

## Codici errore

| Codice               | HTTP | Causa                                                        |
| -------------------- | ---- | ------------------------------------------------------------ |
| `E_PERMESSO_NEGATO`  | 403  | Consultazione di un altro utente senza superuser/SUPER_ADMIN |
| `E_AMM_UTENTE_NOT_FOUND` | 404 | `user_id` inesistente (dal 2026-10-08; prima 400 `E_CORE_VALIDATION`) |
| `E_CORE_VALIDATION`  | 400  | `tabella` non ammessa                                        |
| `E_VALIDATION_INPUT` | 400  | Data non ISO, `page`/`page_size` non numerici o < 1          |


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

`apps/core/tests/api/test_permissions_audit.py` -- test unitari.
