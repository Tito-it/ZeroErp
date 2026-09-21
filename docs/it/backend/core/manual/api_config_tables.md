# API — CRUD generico sulle tabelle di configurazione

## Scopo

Un solo gruppo di endpoint per **leggere e manutenere le tabelle di
configurazione** (`config.*` e le altre in whitelist), senza scrivere una view
per ognuna. E' il lato server del pannello di configurazione generico: il FE
costruisce lista, form e colonne **dai metadati**, non da un layout cablato.

⚠️ **Il perimetro e' la whitelist, non lo schema.** `rel` (`<schema>.<tabella>`)
deve stare in `_REL_CONSENTITE`: e' la stessa whitelist del lookup generico. Una
tabella non elencata non e' raggiungibile — nessun accesso «per nome» a tabelle
arbitrarie, che e' il rischio ovvio di un CRUD generico.

## Contesto

Area funzionale `config`: valgono i permessi di area del profilo. La lista
record **riusa** il lookup generico (`fn_list_lookup_codici`) invece di avere
una query propria: stessa paginazione, stessa ricerca, stesso ordinamento
validato contro whitelist.

## Endpoint

### 1. `GET /api/v1/core/config/tables/`

Le tabelle manutenibili. Risposta: `results` con `{schema, table, rel}` per ogni
voce della whitelist, ordinate per `rel`.

### 2. `GET /api/v1/core/config/tables/{rel}/metadata/`

Le **colonne** della tabella (tipo, nullabilita', default…), lette
dall'introspezione. E' quello che permette al FE di generare il form senza
sapere in anticipo che tabella sia.

⭐ **Dal 2026-09-21 il metadata legge anche le chiavi esterne**: ogni colonna
porta `references` (`<schema>.<tabella>` nominata dalla FK a una colonna, o
`null`), `references_column` (la colonna referenziata — **non e' sempre `id`**:
`config.stati_doc_*.esito` punta a `esiti_flussi_pratiche(codice_interno)`, e
il FE la usa come `valueField` della `LookupSelect`) e `references_lookup`
(`true` se quella tabella e' in `_REL_CONSENTITE` **e** la colonna referenziata
e' fra quelle che il lookup restituisce, `LOOKUP_COLONNE_VALORE` =
`id`/`codice`/`codice_interno`; `false` = resta un valore a mano, e il drawer
lo dichiara). Chi possiede whitelist e contratto del lookup decide: il FE non
li conosce.
⚠️ Escluse, oltre alle colonne di audit e `tx_id`/`storicizza`, le **identita'
tecniche** che scrive il DB (`uid` con default `uuidv7()`): un campo che
l'operatore non deve compilare non si mostra come obbligatorio.

### 3. `GET /api/v1/core/config/tables/{rel}/`

Lista paginata dei record.

| query param | default | note |
|---|---|---|
| `search` | — | ricerca testo (ILIKE) su codice/descrizione |
| `order_col` | `descrizione` | validato contro whitelist |
| `order_dir` | `asc` | `asc` / `desc` |
| `attivo_only` | `false` | `true` filtra `attivo IS TRUE` (solo se la colonna esiste) |
| `page` | 1 | |
| `page_size` | 50 | |

⚠️ Endpoint dichiarato `is_search_endpoint = True`: vale il throttling di
ricerca. Un client che cicla su piu' tabelle prende 429 se non respira.

### 4. `POST /api/v1/core/config/tables/{rel}/`

Crea un record. Body JSON con le colonne della tabella; la validazione vera e'
**del database** — vincoli, CHECK e trigger restano l'autorita', e l'API si
limita a tradurne il rifiuto.

### 5. `GET` e `PATCH` `/api/v1/core/config/tables/{rel}/{id}/`

Dettaglio e aggiornamento parziale di un record.

## Codici errore

| codice | quando |
|---|---|
| `E_CORE_VALIDATION` | `rel` fuori whitelist; oppure il DB rifiuta il record per un **CHECK**, una **FK** o un **NOT NULL** — con `fields` che nomina la colonna (dal vincolo, se e' a una colonna; su un NOT NULL dal `column_name` di PostgreSQL) |
| `E_ANAG_NOT_FOUND` | record inesistente |
| `E_ANAG_DUPLICATO` | violazione di **unicita'**, con `fields` = la colonna se il vincolo e' a una colonna |
| il codice del **trigger** (`CODICE_NON_MODIFICABILE`, `E_ATTIVO_BLOCK_CHILDREN_EXIST`, …) | un `P0001` del DB passa **com'e'**: il codice lo dichiara il DB (`translate_db_errors`) |

⚠️ **Fino al 2026-09-21 OGNI `IntegrityError` era «Record gia' esistente»**: un
`CHECK` violato, una FK sbagliata, un NOT NULL — tutti «duplicato», senza
campo. Ora il service passa dal BB `translate_db_errors`, e le mappe per nome
di vincolo le legge dal **catalogo della tabella** (`pg_constraint`, via
`ConfigMetadataRepository.get_table_constraints`) invece di scriverle a mano
per ~90 tabelle. Il campo si dichiara solo sui vincoli a una colonna: un campo
inventato accende l'input sbagliato.

⚠️ **I due codici `E_ANAG_*` su endpoint `core` non sono un refuso**: il service
riusa i codici della famiglia anagrafiche (`config_crud_service.py`). E' un
disallineamento di nomi noto — chi scrive un client li deve gestire cosi' come
sono, non come ci si aspetterebbe.

## Dipendenze

* `apps/core/api/views_config_crud.py` — le quattro view
* `apps/core/services/config_crud_service.py` — whitelist `rel`, mapping errori
* `apps/core/db/config_crud_repository.py`, `config_metadata_repository.py`
* [api_lookup_codici](api_lookup_codici.md) — il lookup generico che serve la lista, e la stessa whitelist
