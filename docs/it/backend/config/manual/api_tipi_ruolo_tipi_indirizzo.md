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

Tutti gli endpoint richiedono ruolo ADMIN (`AdminAPIView`).

### Query params lista

- `search` (str, opzionale, min 3 char) — ILIKE su codice/descrizione di
  tipo ruolo e tipo indirizzo
- `attivo` (bool, opzionale) — filtro per stato
- `tipo_ruolo_id` (int, opzionale) — filtro per tipo ruolo
- `tipo_indirizzo_id` (int, opzionale) — filtro per tipo indirizzo
- `limit` (int, default 25, max 200)
- `offset` (int, default 0)
- `order_by` (str, default `tipo_ruolo_descrizione`) — whitelist:
  `tipo_ruolo_codice`, `tipo_ruolo_descrizione`, `tipo_indirizzo_codice`,
  `tipo_indirizzo_descrizione`, `obbligatorio`, `attivo`, `data_insert`,
  `data_update`
- `order_dir` (`asc`/`desc`, default `asc`)

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
        "data_insert": "2026-04-10T10:00:00Z",
        "data_update": "2026-04-10T10:00:00Z",
        "user_insert": "admin",
        "user_update": "admin"
      }
    ]
  }
}
```

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
- Validita' temporale (`valido_dal/al`): presente nella tabella ma non gestita
  da questo CRUD (default DB applicato).
- Permessi: tutti gli endpoint richiedono ruolo `ADMIN` di sistema.

## Codici errore

| Codice | HTTP | Descrizione |
|---|---|---|
| `E_CONFIG_VALIDATION` | 400 | Payload non valido (chiavi sconosciute, FK negative, bool non valido, tentativo modifica FK) |
| `E_CONFIG_MATRICE_NOT_FOUND` | 404 | Riga matrice inesistente (get/patch) |
| `E_CONFIG_MATRICE_DUPLICATA` | 409 | Coppia gia' presente (UNIQUE) |
| `E_CONFIG_MATRICE_FK` | 400 | `tipo_ruolo_id`, `tipo_indirizzo_id` o `fallback_tipo_indirizzo_id` non esistente |

Codici registrati in `apps.core.services.error_policies.ErrorPolicyRegistry`.

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
  nella whitelist `_REL_CONSENTITE` di `dbops_repository.py`, quindi i Select
  del drawer riusano `LookupSelect` (BB esistente).
