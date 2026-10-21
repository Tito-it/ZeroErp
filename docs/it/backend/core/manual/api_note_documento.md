# API — note di documento (building block, sei domini)

## Scopo

Il CRUD delle **note partizionate** appese a un documento: preventivo, offerta,
contratto, ordine, DDT, fattura. **Un solo contratto**, sei montaggi — qui e'
descritto una volta, e le pagine di dominio dicono solo cosa cambia da loro.

⚠️ **Non sono le note di catalogo o di pratica.** `/api/v1/catalogo/…/note/` e
`/api/v1/pratiche/{id}/note/` esistono, ma sono altri endpoint con altre regole:
questa pagina copre **solo** i sei domini montati su
`apps/core/api/partitioned_note_views.make_note_views`.

## Contesto

Le view nascono dalla factory `make_note_views(...)` (core); ogni dominio passa
il proprio repository (`apps/vendite/db/note_repositories.py`) e il proprio
`model_permission`. Il service e' `PartitionedNoteService`, **istanziato per
richiesta** — il repository, che non ha stato, resta condiviso.

A database la tabella e' partizionata per `target_tipo`: una partizione per
dominio, vincoli e trigger ereditati dalla parent.

## 1. La matrice

Sostituire `<dominio>` e `{id}` con la riga giusta:

| dominio | path | `target_tipo` | partizione | righe ancorabili |
|---|---|---|---|---|
| preventivo | `/api/v1/vendite/preventivi/{preventivo_id}/note/` | `PREVENTIVO` | `vendite.note_preventivo` | righe preventivo |
| offerta | `/api/v1/vendite/offerte/{offerta_id}/note/` | `OFFERTA` | `vendite.note_offerte_commerciali` | eccezioni offerta (`vendite.offerte_commerciali_eccezioni`) |
| contratto | `/api/v1/vendite/contratti/{contratto_id}/note/` | `CONTRATTO` | `vendite.note_contratto` | righe contratto |
| ordine | `/api/v1/vendite/ordini/{ordine_id}/note/` | `ORDINE` | `vendite.note_ordini` | righe ordine |
| DDT | `/api/v1/vendite/ddt/{ddt_id}/note/` | `DDT` | `vendite.note_ddt` | righe DDT |
| fattura | `/api/v1/vendite/fatture/{fattura_id}/note/` | `FATTURA` | `vendite.note_fatture` | `vendite.fatture_righe` |

Ogni dominio espone **due** rotte:

* `GET` / `POST` `…/{id}/note/` — lista e creazione;
* `GET` / `PATCH` / `DELETE` `…/{id}/note/{note_id}/` — dettaglio, modifica
  parziale, cancellazione.

## 2. Lista — `GET …/{id}/note/`

| query param | default | note |
|---|---|---|
| `target_riga_id` | — | filtra le note **di una riga**; vuoto = tutte |
| `include_invisible` | `true` | `false` esclude le note con `visibile = false` |
| `limit` | 25 | max 200; fuori da 1..200 → 400 `E_VALIDATION_INPUT` (`limit_fuori_limiti_1_200`) |
| `offset` | 0 | negativo → 400 (`offset_negativo`) |

`limit`/`offset` li legge `pagina_da_query`: un valore non intero è un 400
`E_VALIDATION_INPUT` (`limit_invalid`/`offset_invalid`). ⛔ `page`/`page_size`
in query sono un 400 `E_VALIDATION_INPUT` dal 2026-10-21 (prima erano il
contratto di questa lista).

Risposta: envelope paginato standard `data: {count, page, page_size,
total_pages, results}` (`envelope_da_offset`). `page_size` è il `limit`
chiesto, `page` la pagina ricavata dall'offset.

⭐ **`include_invisible` sta a `true` di default, ed e' la scelta giusta**:
l'endpoint serve il drawer dell'operatore, che le note nascoste **deve** vederle
— «invisibile» qui vuol dire «non esce in stampa», non «segreta». Chi prepara un
documento da stampare passa `false`.

⚠️ La `GET` e' `is_search_endpoint`: vale il throttling di ricerca.

## 3. Creazione — `POST …/{id}/note/`

⛔ **`Idempotency-Key` obbligatoria** (`require_idempotency_key=True`): senza
header la richiesta viene rifiutata. Una nota e' un'operazione che il doppio
click duplicherebbe in silenzio, e una nota doppia non da' errore a nessuno —
per questo il presidio e' in ingresso e non a valle.

Campi accettati (whitelist del service; il repository ne applica una piu'
stretta):

| campo | note |
|---|---|
| `testo`, `testo_md` | il contenuto |
| `anchor_tipo`, `posizione`, `seq` | dove e in che ordine si aggancia |
| `target_riga_id` | ancora la nota a una **riga**; assente = nota di testata |
| `visibile` | `false` = non esce in stampa |
| `solo_stampa` | il complementare: solo per il documento stampato |
| `id_stile`, `id_lingua` | se assenti, li risolve il sistema (§5) |
| `meta` | metadati liberi |

## 4. Dettaglio, modifica, cancellazione

* **GET** `…/note/{note_id}/` — dettaglio. La coppia `(note_id, target_id)` viene
  verificata: chiedere la nota di un altro documento non da' la nota, da' 404.
  E' lo stesso anti-tampering degli endpoint documentali;
* **PATCH** — aggiornamento parziale. ⛔ **`target_riga_id` e' immutabile**: una
  nota non trasloca da una riga a un'altra. Si cancella e si riscrive, cosi'
  l'audit dice cosa e' successo;
* **DELETE** — **hard delete**, risposta `{"deleted": true}`; 404 se non c'e'
  gia' piu'.

## 5. Stile e lingua di default — chiave naturale, non id

Se `id_stile` / `id_lingua` non arrivano, il service li risolve dai parametri di
sistema `NOTE_DEFAULT_STILE` e `NOTE_DEFAULT_LINGUA`.

⭐ **Quei parametri contengono la chiave naturale, non l'id numerico**:
`codice_interno` per `config.note_stili`, `codice_iso` per `config.lingue`.
Motivo: l'id auto-incrementale cambia a ogni re-seed, il codice no — e un
default che punta all'id sbagliato dopo un re-seed e' un difetto che si vede
solo in stampa, tardi.

## 6. Codici errore

| codice | HTTP | quando |
|---|---|---|
| `E_NOTA_VALIDATION` | 400 | payload fuori whitelist o non valido — compresa, in creazione, l'incoerenza `anchor_tipo` / `target_riga_id`, che il service intercetta prima del DB; ripiego per i vincoli non mappati |
| `E_NOTA_PARENT_NOT_FOUND` | 404 | il documento padre non esiste (lista, creazione) |
| `E_NOTA_NOT_FOUND` | 404 | nota inesistente, o appartenente a un altro documento (dettaglio, PATCH, DELETE) |
| `E_NOTA_RIGA_INCOERENTE` | 400 | `target_riga_id` di una riga che non appartiene al documento |
| `E_NOTA_CHECK_VIOLATION` | 400 | vincolo `chk_note_*` o di partizione violato a DB: ripiego per ciò che la validazione del service non ha già fermato |
| `E_NOTA_FK` | 400 | riferimento inesistente (stile, lingua, riga) |

`E_NOTA_CHECK_VIOLATION` ed `E_NOTA_FK` nascono dalla traduzione degli
`IntegrityError` di PostgreSQL. Solo i vincoli **ereditati dalla parent
table** (`chk_note_*`, `fk_vendite_note_id_stile`, `fk_vendite_note_id_lingua`)
valgono identici per tutte le partizioni; i vincoli di coerenza, testo, testata
e riga sono **locali** a ogni partizione, con nomi propri che non seguono un
prefisso solo (`offnote`, `ordini_note`, `ordnote`…). La mappa del service li
copre tutti da una tabella per partizione (`_VINCOLI_PARTIZIONE`): coerenza e
testo → `E_NOTA_CHECK_VIOLATION`, testata → `E_NOTA_PARENT_NOT_FOUND`, riga →
`E_NOTA_FK`. Fino al 2026-10-07 copriva solo preventivo e contratto, e per
offerta, ordine, DDT e fattura i vincoli locali cadevano sul ripiego
`E_NOTA_VALIDATION` (F-7, chiuso). Presidio:
`core/tests/db/test_note_vincoli_mappati_db.py` legge i vincoli veri delle
partizioni da `pg_constraint` e fallisce, nei due versi, su un vincolo non
mappato o su una voce che non nomina niente.

## 7. Permessi

`area_funzionale = "vendite"` piu' `model_permission` **per dominio**
(`("vendite","preventivo")`, `("vendite","contratto")`, …): il permesso e' di
**livello oggetto** (v2), non di sola area. Chi puo' vedere gli ordini ma non i
contratti non legge le note dei contratti.

## 8. Dove guardare nel codice

| cosa | dove |
|---|---|
| factory delle due view | `apps/core/api/partitioned_note_views.py` |
| service (validazione, default, mappa errori) | `apps/core/services/partitioned_note_service.py` |
| repository per dominio | `apps/vendite/db/note_repositories.py` |
| montaggio delle 12 rotte | `apps/vendite/api/note_views.py` + `urls_*.py` |
