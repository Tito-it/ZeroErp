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
| `E_CORE_VALIDATION` | `rel` fuori whitelist, oppure payload rifiutato |
| `E_ANAG_NOT_FOUND` | record inesistente |
| `E_ANAG_DUPLICATO` | violazione di unicita' tradotta da `IntegrityError` |

⚠️ **I due codici `E_ANAG_*` su endpoint `core` non sono un refuso**: il service
riusa i codici della famiglia anagrafiche (`config_crud_service.py`). E' un
disallineamento di nomi noto — chi scrive un client li deve gestire cosi' come
sono, non come ci si aspetterebbe.

## Dipendenze

* `apps/core/api/views_config_crud.py` — le quattro view
* `apps/core/services/config_crud_service.py` — whitelist `rel`, mapping errori
* `apps/core/db/config_crud_repository.py`, `config_metadata_repository.py`
* [api_lookup_codici](api_lookup_codici.md) — il lookup generico che serve la lista, e la stessa whitelist
