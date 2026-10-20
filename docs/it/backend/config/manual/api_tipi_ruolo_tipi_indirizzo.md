# API Matrice `config.tipi_ruolo_tipi_indirizzo` (Django)

## Scopo
CRUD admin per la matrice `config.tipi_ruolo_tipi_indirizzo`, che definisce
quali tipi di indirizzo sono ammessi (e obbligatori) per ciascun tipo ruolo.
La matrice governa la validazione indirizzi nella creazione soggetti, clienti
e fornitori, e supporta il fallback automatico per tipi indirizzo mancanti.

## Contesto
- Schema DB: `config`
- Tabella: `config.tipi_ruolo_tipi_indirizzo`
- App Django: `apps.config`
- Consumer principali:
  - `LookupRepository.list_matrice_indirizzi_ruolo` (combo indirizzo)
  - `FornitoriService._create_indirizzi_ruolo` (auto-clone obbligatori)
  - Guard DB: `trgfn_indirizzi_soggetti_guard_tipo_indirizzo`
- Pattern: amministrazione admin-only, CRUD modellato su
  `utilities_tipi_ruolo` (stessa app config).

## Input

### Endpoint

| Metodo | Path | Descrizione |
|---|---|---|
| GET | `/api/v1/config/tipi-ruolo-tipi-indirizzo/` | Lista paginata |
| POST | `/api/v1/config/tipi-ruolo-tipi-indirizzo/` | Crea nuova riga |
| GET | `/api/v1/config/tipi-ruolo-tipi-indirizzo/<id>/` | Dettaglio |
| PATCH | `/api/v1/config/tipi-ruolo-tipi-indirizzo/<id>/` | Aggiorna campi modificabili |

Tutti gli endpoint sono riservati agli amministratori (`AdminAPIView` → `IsAdminZeroERP`): binding `SUPER_ADMIN` o superuser Django. Altrimenti `403` `E_ACCESSO_RISERVATO_ADMIN`.

### Query params lista

- `search` (str, opzionale) — ricerca libera su codice/descrizione di
  tipo ruolo e tipo indirizzo (colonne e soglia dal catalogo della lista; sotto
  soglia il termine non filtra, nessun `400`)
- `attivo` (bool, opzionale) — filtro per stato
- `tipo_ruolo_id` (int, opzionale) — filtro per tipo ruolo
- `tipo_indirizzo_id` (int, opzionale) — filtro per tipo indirizzo
- `limit` (int, default 25, max 200)
- `offset` (int, default 0)
- `order_by` (str, default `tipo_ruolo_descrizione`) — whitelist:
  `tipo_ruolo_codice`, `tipo_ruolo_descrizione`, `tipo_indirizzo_codice`,
  `tipo_indirizzo_descrizione`, `obbligatorio`, `attivo`, `valido_dal`
  (vuoto = `-infinity`), `valido_al` (vuoto = `infinity`), `data_insert`,
  `data_update`
- `order_dir` (`asc`/`desc`). Assente: il default della lista — `asc` sulle colonne testo, `desc` sulle colonne data (`valido_dal`, `valido_al`, `data_insert`, `data_update`; dal 2026-10-20, prima `asc`)

### Body POST

```json
{
  "tipo_ruolo_id": 5,
  "tipo_indirizzo_id": 8,
  "obbligatorio": true,
  "fallback_tipo_indirizzo_id": 3,
  "attivo": true
}
```

- `tipo_ruolo_id` (int, obbligatorio)
- `tipo_indirizzo_id` (int, obbligatorio)
- `obbligatorio` (bool, opzionale, default DB `false`)
- `fallback_tipo_indirizzo_id` (int, opzionale, nullable) — FK a
  `config.tipi_indirizzi`, tipo indirizzo da usare come fallback.
  CHECK: non puo' essere uguale a `tipo_indirizzo_id` stesso.
- `attivo` (bool, opzionale, default DB `true`)

### Body PATCH

```json
{
  "attivo": false,
  "obbligatorio": true,
  "fallback_tipo_indirizzo_id": null
}
```

Campi modificabili: `attivo`, `obbligatorio`, `fallback_tipo_indirizzo_id`.
Le FK `(tipo_ruolo_id, tipo_indirizzo_id)` sono **immutabili**: tentativi di
modifica rifiutati con `E_CONFIG_VALIDATION`.

## Output

### Envelope standard

```json
{
  "data": {
    "count": 15,
    "page": 1,
    "page_size": 25,
    "total_pages": 1,
    "results": [
      {
        "id": 1,
        "tipo_ruolo_id": 5,
        "tipo_ruolo_codice": "CL",
        "tipo_ruolo_descrizione": "Cliente",
        "tipo_indirizzo_id": 8,
        "tipo_indirizzo_codice": "RES",
        "tipo_indirizzo_descrizione": "Residenza",
        "obbligatorio": true,
        "fallback_tipo_indirizzo_id": 3,
        "fallback_codice": "SEDEOP",
        "fallback_descrizione": "Sede operativa",
        "attivo": true,
        "valido_dal": "2026-04-10",
        "valido_al": null,
        "data_insert": "2026-04-10T10:00:00Z",
        "data_update": "2026-04-10T10:00:00Z",
        "user_insert": "admin",
        "user_update": "admin"
      }
    ]
  }
}
```

**Fase 4 — `non_editable_fields` a livello envelope**: l'envelope GET lista
include `data.non_editable_fields: ["tipo_indirizzo_id", "tipo_ruolo_id"]`
(le 2 dimensioni della matrice sono semanticamente immutabili: cambiarle =
rimpiazzare la riga). Il FE consuma questo campo per gating dei Select
dimensionali nel drawer di edit.

### `GET` dettaglio — proiezioni Fase 4

Il `GET /{record_id}/` arricchisce il dict di response con:

- `non_editable_fields: list[str]` — stessa lista dell'envelope.
- `fallback_options: list[{tipo_indirizzo_id, codice, descrizione}]` — lista
  pre-filtrata dei tipi indirizzo candidati come fallback per la riga corrente.
  Il filtraggio applica:
  - **No self-reference**: il tipo della riga e' escluso (un tipo non puo'
    essere fallback di se stesso).
  - **No cicli**: candidati la cui catena di fallback porta al tipo corrente
    sono esclusi (DFS con `visited` set, gestisce anche cicli pre-esistenti
    nel DB senza loop infinito).

**Esempio response detail**:

```json
{
  "data": {
    "id": 1, "tipo_ruolo_id": 5, "tipo_indirizzo_id": 8,
    "fallback_tipo_indirizzo_id": 3,
    "non_editable_fields": ["tipo_indirizzo_id", "tipo_ruolo_id"],
    "fallback_options": [
      {"tipo_indirizzo_id": 3, "codice": "SEDEOP", "descrizione": "Sede operativa"},
      {"tipo_indirizzo_id": 7, "codice": "CORR",   "descrizione": "Corrispondenza"}
    ]
  }
}
```

In `GET` lista i campi `non_editable_fields` e `fallback_options` sono
solo a livello envelope/dettaglio: la lista non li espone per riga (il
calcolo `fallback_options` per N righe e' costoso e serve solo nel drawer
di edit di una singola riga).

## Regole

- Le coppie `(tipo_ruolo_id, tipo_indirizzo_id)` sono **immutabili** in update.
  Per modificarle disattivare la riga e crearne una nuova.
- Il `fallback_tipo_indirizzo_id` non puo' essere uguale a `tipo_indirizzo_id`
  (CHECK DB `chk_tipi_ruolo_tipi_indirizzo_fallback_not_self`).
- Il flag `obbligatorio` controlla l'auto-clone indirizzi in creazione
  cliente/fornitore: se un tipo obbligatorio manca nel payload, il primo
  indirizzo viene clonato su quel tipo.
- Il flag `attivo` influenza la lettura via
  `LookupRepository.list_matrice_indirizzi_ruolo` (filtro `attivo = true`).
- Validita' temporale: `valido_dal`/`valido_al` sono esposti in lista e
  dettaglio ma non si scrivono nel corpo (chiave fuori contratto → `400`). La
  `POST` imposta `valido_dal = script.fn_data_operativa()` (l'oggi aziendale);
  in `PATCH`, `attivo` trascina `valido_al`: `false` lo chiude a
  `fn_data_operativa()`, `true` lo azzera.
- Permessi: binding `SUPER_ADMIN` o superuser (`403` `E_ACCESSO_RISERVATO_ADMIN`).

## Codici errore

| Codice | HTTP | Descrizione |
|---|---|---|
| `E_CONFIG_VALIDATION` | 400 | Payload non valido (chiavi sconosciute, FK negative, bool non valido, tentativo modifica FK) |
| `E_CONFIG_MATRICE_NOT_FOUND` | 404 | Riga matrice inesistente (get/patch) |
| `E_CONFIG_MATRICE_DUPLICATA` | 409 | Coppia gia' presente (UNIQUE) |
| `E_CONFIG_MATRICE_FK` | 400 | `tipo_ruolo_id`, `tipo_indirizzo_id` o `fallback_tipo_indirizzo_id` non esistente. Messaggio distingue la FK violata (mapping per nome vincolo DB via `map_integrity_error`). |

Codici registrati in `apps.core.services.error_policies.ErrorPolicyRegistry`.

Validazione payload e traduzione vincoli DB delegate al building block
`apps.core.services.payload_helpers` (`PayloadValidator`,
`map_integrity_error`). Vedi
[catalogo-building-block-backend.md](/dev/backend/catalogo-building-block-backend).

## Dipendenze DB

- `config.tipi_ruolo_tipi_indirizzo` (PK `id`,
  UNIQUE `(tipo_ruolo_id, tipo_indirizzo_id)`,
  CHECK `chk_ruoli_tipi_indirizzo_validita`,
  CHECK `chk_tipi_ruolo_tipi_indirizzo_fallback_not_self`)
- `config.tipi_ruoli` (FK `tipo_ruolo_id`, lookup join `codice_interno`/`codice`)
- `config.tipi_indirizzi` (FK `tipo_indirizzo_id` e `fallback_tipo_indirizzo_id`,
  lookup join `codice_interno`/`codice`)
- Trigger audit: `script.trgfn_audit_data_user_generic`
- Trigger storico: `script.trgfn_storico_generic`

## Note di migrazione

- Nessuna migrazione DB necessaria: la tabella e i vincoli esistono gia'.
- Backend: repository + service + views in `apps.config`, route in
  `apps.config.api.urls` sotto `/api/v1/config/tipi-ruolo-tipi-indirizzo/`.
- Frontend admin: lista + drawer in `frontend/src/amministrazione/`.
  Route: `/amm-software/matrice-indirizzi-ruoli`.
  Voce navigazione: "Matrice Indirizzi/Ruoli" con icona `pi pi-map`.
- I lookup `config.tipi_ruoli` e `config.tipi_indirizzi` sono gia' presenti
  nella lista del lookup generico (`config.tabelle_gestibili`), quindi i Select
  del drawer riusano `LookupSelect` (BB esistente).
