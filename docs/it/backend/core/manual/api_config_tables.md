# API — CRUD generico sulle tabelle di configurazione

## Scopo

Un solo gruppo di endpoint per **leggere e manutenere le tabelle di
configurazione** (`config.*` e le altre della lista), senza scrivere una view
per ognuna. E' il lato server del pannello di configurazione generico: il FE
costruisce lista, form e colonne **dai metadati**, non da un layout cablato.

⚠️ **Il perimetro e' la lista a DB, non lo schema.** `rel` (`<schema>.<tabella>`)
deve essere una riga di [`config.tabelle_gestibili`](/dbzero/config/tabelle/tabelle_gestibili)
con `pannello = true`. Una tabella non elencata non e' raggiungibile — nessun
accesso «per nome» a tabelle arbitrarie, che e' il rischio ovvio di un CRUD
generico. Il nome che entra negli SQL e' quello della riga di lista, non quello
mandato dal client. Fino al 2026-09-25 la lista era la costante `REL_CONSENTITE`
del backend. Le tabelle con RLS (`magazzino.magazzini`, `magazzino.ubicazioni`,
`pagamenti.enti_incasso`, `vendite.listini`) stanno nelle tendine
(`lookup = true`) ma **non** nel pannello: hanno endpoint propri.

## Contesto

⭐ **Il permesso si chiede sull'oggetto della tabella, non sull'area del
pannello** (dal 2026-09-25, brief-db-pannello-config-verbo-generico). Ogni riga
della lista nomina l'oggetto (`app_label`, `model_name`); le rotte con `{rel}`
chiedono il livello su quell'oggetto, nell'area che ne ricava
`script.fn_area_di_oggetto`. Chi ha `TUTTO` solo su Configurazione legge e
modifica le tabelle di `config`, ma non le causali di magazzino. L'elenco delle
tabelle (`GET /tables/`) resta sull'area `config`.

⭐ **Si scrive solo col verbo** [`config.fn_pannello_scrivi`](/dbzero/config/manual/fn_pannello_scrivi):
fa lo stesso controllo del livello (il 403 del backend arriva prima, senza
aprire la transazione), rifiuta i campi che non si scrivono e scrive con i
privilegi del proprietario. Alcune tabelle sono chiuse all'app in scrittura
(oggi `magazzino.causali`): dal pannello si scrivono solo cosi'.

La lista record **riusa** il lookup generico (`fn_list_lookup_codici`) invece
di avere una query propria: stessa paginazione, stessa ricerca, stesso
ordinamento validato contro whitelist.

## Endpoint

### 1. `GET /api/v1/core/config/tables/`

Le tabelle manutenibili. Risposta: `results` con `{schema, table, rel}` per ogni
riga della lista con `pannello = true`, ordinate per `rel`. ⭐ Dal 2026-09-28 e'
l'**unica** lista del pannello: il FE la legge per la colonna di sinistra, e il
suo registro `config-tables.js` e' ritirato. Una tabella nuova nel pannello =
una riga nel CSV del DB piu' l'etichetta `config_panel.tabelle.<schema>.<tabella>`
nei locales del FE (il presidio `test_config_panel_registro_db` la chiede).

### 2. `GET /api/v1/core/config/tables/{rel}/metadata/`

Le **colonne** della tabella (tipo, nullabilita', default…), lette
dall'introspezione, nella risposta `{"columns": [...]}`. E' quello che permette al FE di generare il form senza
sapere in anticipo che tabella sia.

⭐ **Dal 2026-09-21 il metadata legge anche le chiavi esterne**: ogni colonna
porta `references` (`<schema>.<tabella>` nominata dalla FK a una colonna, o
`null`), `references_column` (la colonna referenziata — **non e' sempre `id`**:
`config.stati_doc_*.esito` punta a `esiti_flussi_pratiche(codice_interno)`, e
il FE la usa come `valueField` della `LookupSelect`) e `references_lookup`
(`true` se quella tabella e' nella lista con `lookup = true` **e** la colonna referenziata
e' fra quelle che il lookup restituisce, `LOOKUP_COLONNE_VALORE` =
`id`/`codice`/`codice_interno`; `false` = resta un valore a mano, e il drawer
lo dichiara). Chi possiede whitelist e contratto del lookup decide: il FE non
li conosce. Ogni colonna porta anche `has_default` (c'era gia') (il DB la riempie da solo,
anche quando `default` e' `null` perche' non e' un literal — `now()`,
`nextval`): il FE marca obbligatoria una colonna solo se NOT NULL **senza**
default.
⭐ **Quali colonne lo dice il DB**: `id` piu' quelle di
[`config.fn_pannello_colonne_scrivibili`](/dbzero/config/manual/fn_pannello_colonne_scrivibili),
la stessa funzione con cui il verbo decide quali campi accettare (sede unica
dal 2026-09-27). Restano fuori le colonne che il DB scrive per ogni riga
(audit, `tx_id`, `storicizza`, `uid`), le generate e le identity `ALWAYS`.
Fino ad allora il metadata aveva una sua copia di quell'elenco: se le due
divergevano, il form offriva un campo che il salvataggio rifiuta.

### 3. `GET /api/v1/core/config/tables/{rel}/`

Lista paginata dei record.

| query param | default | note |
|---|---|---|
| `search` | — | ricerca testo (ILIKE) su codice/descrizione |
| `order_col` | `descrizione` | validato contro whitelist |
| `order_dir` | `asc` | `asc` / `desc` |
| `attivo_only` | `false` | `true` filtra `attivo IS TRUE` (solo se la colonna esiste) |
| `page` | 1 | |
| `page_size` | 25 | max 200 |

⚠️ Endpoint dichiarato `is_search_endpoint = True`: vale il throttling di
ricerca. Un client che cicla su piu' tabelle prende 429 se non respira.

### 4. `POST /api/v1/core/config/tables/{rel}/`

Crea un record col verbo e risponde con la riga scritta: `id` e i campi del
form, cioe' le colonne del metadata (dal 2026-09-27; prima «tutto tranne le
colonne di audit»). Body JSON con le sole colonne **scrivibili** della tabella — quelle del
metadata tranne `id`. ⛔ Dal 2026-09-25 una chiave che non e' una colonna
scrivibile si **rifiuta** (`E_PANNELLO_CAMPO_NON_AMMESSO`, col campo nel
contesto) invece di essere scartata in silenzio, e un body vuoto e'
`E_PANNELLO_DATI_VUOTI`. I valori li converte PostgreSQL sul tipo di ogni
colonna. La validazione vera e' **del database** — vincoli, CHECK e trigger
restano l'autorita', e l'API si limita a tradurne il rifiuto.

### 5. `GET` e `PATCH` `/api/v1/core/config/tables/{rel}/{id}/`

Dettaglio e aggiornamento parziale di un record. Il `GET` restituisce il
record; il `PATCH` (col verbo, stesse regole del `POST` sui campi: solo quelli
mandati si scrivono) risponde `{"updated": true}`, **non** il record
aggiornato: chi deve mostrare i valori scritti li rilegge col `GET`.

## Codici errore

| codice | quando |
|---|---|
| `E_CORE_VALIDATION` | `rel` fuori dalla lista del pannello; oppure il DB rifiuta il record per un **CHECK**, una **FK** o un **NOT NULL** — con `fields` che nomina la colonna (dal vincolo, se e' a una colonna; su un NOT NULL dal `column_name` di PostgreSQL) |
| `E_PERMESSO_NEGATO` (403) | il livello sull'**oggetto** della tabella non basta (dal backend prima, dal verbo come ultima difesa) |
| `E_PANNELLO_CAMPO_NON_AMMESSO` | una chiave del body non e' una colonna scrivibile (`campo` nel contesto) |
| `E_PANNELLO_DATI_VUOTI` | body vuoto in `POST`/`PATCH` |
| `E_PANNELLO_RIGA_NON_TROVATA` | record inesistente, in `GET` di dettaglio come in `PATCH` (fino al 2026-09-25 era `E_ANAG_NOT_FOUND`) |
| `E_PANNELLO_TABELLA_NON_AMMESSA` | il verbo rifiuta la tabella (fuori lista o con RLS): con il controllo del backend davanti non dovrebbe mai arrivare, e se arriva e' un difetto |
| `E_ANAG_DUPLICATO` | violazione di **unicita'**, con `fields` = la colonna se il vincolo e' a una colonna |
| il codice del **trigger** (`E_CODICE_NON_MODIFICABILE`, `E_ATTIVO_BLOCK_CHILDREN_EXIST`, …) | un `P0001` del DB passa **com'e'**: il codice lo dichiara il DB (`translate_db_errors`) |

⚠️ **Fino al 2026-09-21 OGNI `IntegrityError` era «Record gia' esistente»**: un
`CHECK` violato, una FK sbagliata, un NOT NULL — tutti «duplicato», senza
campo. Ora il service passa dal BB `translate_db_errors`, e le mappe per nome
di vincolo le legge dal **catalogo della tabella** (`pg_constraint`, via
`ConfigMetadataRepository.get_table_constraints`) invece di scriverle a mano
per ~90 tabelle. Il campo si dichiara solo sui vincoli a una colonna: un campo
inventato accende l'input sbagliato.

⚠️ **`E_ANAG_DUPLICATO` su endpoint `core` non e' un refuso**: il service
riusa il codice della famiglia anagrafiche (`config_crud_service.py`). E' un
disallineamento di nomi noto — chi scrive un client lo deve gestire cosi' come
e', non come ci si aspetterebbe.

## Dipendenze

* `apps/core/api/views_config_crud.py` — le quattro view; `_PermessoSullOggettoMixin` (dichiara l'oggetto della tabella, `oggetto_permesso_da_richiesta`; lo applica la catena di `ZeroERPPermission`, D-P7)
* `apps/core/services/config_crud_service.py` — `rel` sulla lista del pannello, mapping errori
* `apps/core/db/config_crud_repository.py` (il verbo), `config_metadata_repository.py`
* `apps/core/db/tabelle_gestibili_repository.py` — la lista a DB (`config.tabelle_gestibili`)
* [api_lookup_codici](api_lookup_codici.md) — il lookup generico che serve la lista (colonna `lookup` della stessa tabella)

## Test

* `apps/core/tests/db/test_pannello_verbo_db.py` — sul DB vero: la porta chiusa
  su `magazzino.causali`, il verbo che crea e modifica, i rifiuti coi loro codici
* `apps/core/tests/api/test_views_config_crud.py` — il permesso sull'oggetto
* `apps/core/tests/services/test_config_crud_service.py` — lista, verbo, errori tradotti
* `apps/core/tests/db/test_config_panel_registro_db.py` — il registro FE contro la lista a DB
