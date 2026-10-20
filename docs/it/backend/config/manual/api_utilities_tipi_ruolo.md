# API Matrice `config.utilities_tipi_ruolo` (Django)

## Scopo
CRUD admin per la matrice `config.utilities_tipi_ruolo`, che definisce la
whitelist delle utility ammesse per ciascun tipo ruolo. La matrice e' la base
del pattern slot/override usato dagli emittenti fiscali (e in futuro da
fornitori/clienti) per i parametri di fatturazione utility-specifici.

## Contesto
- Schema DB: `config`
- Tabella: `config.utilities_tipi_ruolo`
- App Django: `apps.config` (precedentemente scaffold vuoto, attivata con questa
  funzionalita')
- Riferimento BB cross-dominio:
  - Repository slot/override: `apps.core.db.lookup_repository.LookupRepository.list_entity_utility_matrix`
  - Trigger guard DB: `script.fn_guard_utility_tipo_ruolo`
- Pattern: amministrazione admin-only, CRUD modellato su `unita_misura`
  (catalogo) — vedi `docs/it/dev/api.md` e
  `docs/it/dev/backend/catalogo-building-block-backend.md`.

## Input

### Endpoint

| Metodo | Path | Descrizione |
|---|---|---|
| GET | `/api/v1/config/utilities-tipi-ruolo/` | Lista paginata |
| POST | `/api/v1/config/utilities-tipi-ruolo/` | Crea nuova riga |
| GET | `/api/v1/config/utilities-tipi-ruolo/<id>/` | Dettaglio |
| PATCH | `/api/v1/config/utilities-tipi-ruolo/<id>/` | Aggiorna `attivo` |
| GET | `/api/v1/config/utilities-tipi-ruolo/<id>/usage/` | Emittenti che usano la matrice |

Tutti gli endpoint sono riservati agli amministratori (`AdminAPIView` → `IsAdminZeroERP`): binding `SUPER_ADMIN` o superuser Django. Altrimenti `403` `E_ACCESSO_RISERVATO_ADMIN`.

### Query params lista

- `search` (str, opzionale) — ricerca libera su codice/descrizione di
  utility e tipo_ruolo (colonne e soglia dal catalogo della lista; sotto
  soglia il termine non filtra, nessun `400`)
- `attivo` (bool, opzionale) — filtro per stato
- `utility_id` (int, opzionale) — filtro per utility
- `tipo_ruolo_id` (int, opzionale) — filtro per tipo ruolo
- `limit` (int, default 25, max 200)
- `offset` (int, default 0)
- `order_by` (str, default `utility_descrizione`) — whitelist:
  `utility_codice`, `utility_descrizione`, `tipo_ruolo_codice`,
  `tipo_ruolo_descrizione`, `attivo`, `data_insert`, `data_update`
- `order_dir` (`asc`/`desc`). Assente: il default della lista — `asc` sulle colonne testo, `desc` sulle colonne data (`data_insert`, `data_update`; dal 2026-10-20, prima `asc`)

### Body POST

```json
{
  "utility_id": 10,
  "tipo_ruolo_id": 5,
  "attivo": true
}
```

- `utility_id` (int, obbligatorio)
- `tipo_ruolo_id` (int, obbligatorio)
- `attivo` (bool, opzionale, default DB `true`)

### Body PATCH

```json
{ "attivo": false }
```

Solo `attivo` e' modificabile. Tentativi di modifica delle FK sono rifiutati
con `E_CONFIG_VALIDATION` (le coppie `(utility_id, tipo_ruolo_id)` sono
immutabili per scelta di progetto).

## Output

### Envelope standard

```json
{
  "data": {
    "count": 12,
    "page": 1,
    "page_size": 25,
    "total_pages": 1,
    "results": [
      {
        "id": 1,
        "utility_id": 10,
        "utility_codice": "GAS",
        "utility_descrizione": "Gas",
        "tipo_ruolo_id": 5,
        "tipo_ruolo_codice": "EF",
        "tipo_ruolo_descrizione": "Emittente fiscale",
        "attivo": true,
        "data_insert": "2026-04-08T10:00:00Z",
        "data_update": "2026-04-08T10:00:00Z",
        "user_insert": "admin",
        "user_update": "admin"
      }
    ]
  }
}
```

### Envelope usage

Lista a catalogo `config.utilities_tipi_ruolo_usage` (dal 2026-09-27), in una
query sola (pagina + totale). Parametri di query:

| Parametro | Tipo | Descrizione |
|---|---|---|
| `search` | string | Ricerca libera sulle colonne accese a catalogo (codice e ragione sociale dell'emittente) |
| `limit` / `offset` | integer | Paginazione (default 25, massimo 200) |
| `order_by` | string | Whitelist `USAGE_ORDER_COLS`: `emittente_codice`, `emittente_descrizione`, `emittente_attivo`, `override_attivo`; fuori whitelist = ordine di partenza |
| `order_dir` | string | `asc` / `desc` (`400` su un valore diverso) |

Senza ordinamento: ragione sociale, poi codice dell'emittente (ASC),
spareggio sull'id dell'emittente. Nessun cancello di perimetro emittente: la
lista è `multi_emittente` (ogni riga è un emittente) e la vista è admin.

```json
{
  "data": {
    "count": 2,
    "page": 1,
    "page_size": 25,
    "total_pages": 1,
    "results": [
      {
        "emittente_id": 1,
        "emittente_codice": "EF-001",
        "emittente_descrizione": "Sede principale",
        "emittente_attivo": true,
        "override_id": 99,
        "override_attivo": true
      }
    ]
  }
}
```

`usage` ritorna risultati significativi solo per matrici con
`tipo_ruolo` = `EF`. Per altri ruoli ritorna sempre 0 (non ci sono override
emittenti per ruoli diversi da Emittente Fiscale).

## Regole

- Le coppie `(utility_id, tipo_ruolo_id)` sono **immutabili** in update. Per
  modificarle disattivare la riga e crearne una nuova.
- Il flag `attivo` non e' soggetto a guard DB sulla coppia: e' un disable
  logico che influenza la lettura via
  `LookupRepository.list_entity_utility_matrix` e
  `LookupRepository.list_utilities_per_ruolo` (filtro `utr.attivo = true`).
- Validita' temporale (`valido_dal/al`): non gestita da questo CRUD (fuori
  scope per la prima iterazione, default DB applicato).
- Permessi: binding `SUPER_ADMIN` o superuser (`403` `E_ACCESSO_RISERVATO_ADMIN`).

## Codici errore

| Codice | HTTP | Descrizione |
|---|---|---|
| `E_CONFIG_VALIDATION` | 400 | Payload non valido (chiavi sconosciute, FK negative, attivo non bool, tentativo modifica FK) |
| `E_CONFIG_MATRICE_NOT_FOUND` | 404 | Riga matrice inesistente (get/patch/usage) |
| `E_CONFIG_MATRICE_DUPLICATA` | 409 | Coppia gia' presente (UNIQUE) |
| `E_CONFIG_MATRICE_FK` | 400 | `utility_id` o `tipo_ruolo_id` non esistente. Messaggio distingue la FK violata (mapping per nome vincolo DB via `map_integrity_error`). |

Codici registrati in `apps.core.services.error_policies.ErrorPolicyRegistry`.

Validazione payload e traduzione vincoli DB delegate al building block
`apps.core.services.payload_helpers` (`PayloadValidator`,
`map_integrity_error`). Vedi
[catalogo-building-block-backend.md](/dev/backend/catalogo-building-block-backend).

## Dipendenze DB

- `config.utilities_tipi_ruolo` (PK `id`, UNIQUE `(utility_id, tipo_ruolo_id)`,
  CHECK `chk_utilities_tipi_ruolo_validita`)
- `config.utilities` (FK `utility_id`)
- `config.tipi_ruoli` (FK `tipo_ruolo_id`, lookup join `codice_interno`/`codice`)
- `anagrafiche.emittenti_fiscali_utilities` (per query `usage`)
- `anagrafiche.emittenti_fiscali` (per query `usage`)
- Trigger guard correlato (lettura dalla matrice):
  `script.fn_guard_utility_tipo_ruolo`

## Note di migrazione

- Prima implementazione di un CRUD nella app `apps.config` (scaffold attivato).
- Wiring main urls: `path("api/v1/config/", include("apps.config.api.urls"))`.
- Frontend admin: lista + drawer in `frontend/src/amministrazione/`
  (coerente con altri admin tools come emittenti fiscali). Route:
  `/amm-software/matrice-utilities-ruoli`.
- I lookup `config.utilities` e `config.tipi_ruoli` sono gia' presenti nella
  lista del lookup generico (`config.tabelle_gestibili`), quindi i Select del
  drawer riusano `LookupSelect` (BB esistente).
