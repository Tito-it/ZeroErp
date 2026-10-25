# API — documenti generati per sorgente (la mappa delle rotte)

## Scopo

Dire **quale URL chiamare** per stampare, scaricare e ristampare il documento di
una sorgente — preventivo, offerta, contratto, ordine, DDT, fattura — e cosa
cambia da un dominio all'altro.

⚠️ **Questa pagina e' la mappa, non il manuale del motore.** Il *perche'* dei
percorsi documentali sta in [api_ristampa_fedele](api_ristampa_fedele.md), gli
helper condivisi in [api_documenti_helpers](api_documenti_helpers.md), il lato
amministrativo (template, versioni, asset) in
[api_documenti_templates](api_documenti_templates.md). Qui ci sono i path, che
in quelle pagine non compaiono mai per esteso — ed e' il motivo per cui questa
pagina esiste: **le rotte c'erano, cercabili no.**

> Scritta il 2026-08-19 chiudendo il buco piu' grande dell'analisi di copertura
> ([analisi-copertura-doc-api-vendite-core](../../../dev/work-done/analisi-copertura-doc-api-vendite-core.md)):
> 26 rotte su 6 domini, nessuna nominata da nessun `.md`.

## Contesto

Le view **non sono sei copie**: nascono da una factory,
`build_documenti_sorgente_views(...)` in
`apps/documenti/api/sorgente_documenti_views.py`, che costruisce le otto view di
un dominio; ogni dominio dichiara solo i propri delta in
`apps/vendite/api/<dominio>_documenti_views.py` (repository, service, messaggi,
codice sorgente). Quindi **il comportamento e' lo stesso ovunque**, e questa
pagina lo descrive una volta sola.

Le rotte vivono sotto il path del **dominio** (`/api/v1/vendite/<dominio>/...`),
non sotto `/api/v1/documenti/`: quello e' il motore, questi sono i suoi usi.

## 1. La matrice — chi espone cosa

`{id}` = id della sorgente. Tutte le rotte sono sotto
`/api/v1/vendite/<dominio>/{id}/`.

| dominio | `codice_interno` sorgente | `emetti/` | `documenti/genera/` | `documenti/anteprima/` | `documenti/` | `…/allegati/` | `…/file/` | `…/file/{file_id}/` | `…/ristampa/` |
|---|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| `preventivi` | `PREVENTIVO` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `offerte` | `OFFERTA_COMMERCIALE` | ✅ | ⛔ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `contratti` | `CONTRATTO` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `ordini` | `ORDINE_VENDITA` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `ddt` | `DDT_VENDITA` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `fatture` | `FATTURA` | ⛔ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

**Le due caselle vuote sono volute, e sono asimmetrie di dominio, non buchi:**

* **fatture senza `emetti/`** — una fattura non si «emette» a mano: la produce la
  pipeline di fatturazione. Qui si stampa e si ristampa. Nel codice e' il
  parametro `emetti_call=None`, che *non costruisce* la view;
* **offerte senza `documenti/genera/`** — l'offerta si stampa **una volta**, con
  `emetti/` (transizione + PDF + allegati in un colpo). La view esiste nella
  factory ma non e' cablata: e' dichiarato in `offerte_documenti_views.py`.

## 2. I quattro percorsi, e quale scegliere

E' la distinzione che [api_ristampa_fedele](api_ristampa_fedele.md) spiega per
esteso, qui in forma di tabella decisionale:

| voglio… | endpoint | scrive a DB? | produce |
|---|---|---|---|
| **vedere come verra'** prima di decidere | `POST /api/v1/vendite/<dominio>/{id}/documenti/anteprima/` | **no**, niente record e niente file | PDF `inline`, temporaneo |
| **emettere** il documento avanzando lo stato | `POST /api/v1/vendite/<dominio>/{id}/emetti/` | si', transizione + record + file + allegati | JSON con `{<dominio>, documento}` |
| **generare un documento nuovo** (senza toccare lo stato) | `POST /api/v1/vendite/<dominio>/{id}/documenti/genera/` | si', record + evento `GENERATO` | JSON del documento |
| **riscaricare l'originale** | `GET /api/v1/vendite/<dominio>/{id}/documenti/{doc}/file/` | evento `SCARICATO` | il file di allora, byte per byte |
| **riprodurre l'originale** anche senza file salvato | `GET /api/v1/vendite/<dominio>/{id}/documenti/{doc}/ristampa/` | solo l'evento di audit | PDF ri-renderizzato `inline` |

⚠️ **`genera/` non e' una ristampa** — su un documento del 2025 produce il
modello di oggi con i dati di oggi. Fino al 2026-08-03 il commento nel codice lo
chiamava «ristampa», e il nome faceva credere al chiamante di avere una cosa che
non aveva. La ristampa vera e' `…/ristampa/`.

## 3. Gli endpoint

### 3.1 `POST /api/v1/vendite/<dominio>/{id}/emetti/` — multipart

Transizione di stato del dominio **+** generazione del documento **+** allegati,
in **una** transazione.

| | |
|---|---|
| **Content-Type** | `multipart/form-data` (l'unico endpoint che non e' JSON in ingresso) |
| **Campi** | `template_documento_id` (int, opz.) · `tipo_documento_output_id` (int, opz.) · `allegati` (file multipli, opz.) |
| **Risposta 200** | `{"data": {"<chiave dominio>": {...}, "documento": {...}}}` — la chiave e' `preventivo`, `offerta`, `contratto`, `ordine`, `ddt` |

⭐ **L'ordine dentro l'atomic non e' un dettaglio**: prima la transizione, poi la
generazione (savepoint annidato). Cosi' lo snapshot del contesto vede lo stato
gia' avanzato — **numero e stato assegnati dai trigger DB finiscono nel PDF** — e
se il render fallisce il rollback annulla anche la transizione: niente documento
orfano, niente stato avanzato senza stampa.

### 3.2 `POST /api/v1/vendite/<dominio>/{id}/documenti/genera/`

Body JSON: `template_documento_id` (opz.), `tipo_documento_output_id` (opz.).
Senza `template_documento_id` il modello lo sceglie il DB
(`documenti.fn_risolvi_template_applicabile`), a **due livelli**: il
predefinito dell'emittente, se l'emittente ha modelli suoi che possono stampare
per (tipo, sorgente); altrimenti il predefinito **standard**. Con l'override il
modello deve essere della stessa sorgente e dello stesso emittente, oppure uno
standard. Rifiuti della risoluzione: `409` `E_DOCUMENTI_TEMPLATE_SENZA_PREDEFINITO`
(l'emittente ha modelli ma nessuno predefinito: lo standard non subentra), `404`
`E_DOCUMENTI_TEMPLATE_NON_RISOLTO` (né modello dell'emittente né standard
utilizzabile), `500` `E_DOCUMENTI_TEMPLATE_AMBIGUO` (senza
`tipo_documento_output_id` su una sorgente con più tipi).
Risposta **200** con il documento (lo schema OpenAPI dichiara ancora 201); scrive
il record e l'evento `GENERATO`. Stessa risoluzione per `emetti/` e `anteprima/`.

### 3.3 `POST /api/v1/vendite/<dominio>/{id}/documenti/anteprima/`

Stesso body di `genera/`. Risposta **binaria**: `application/pdf`,
`Content-Disposition: inline`, `Content-Length` valorizzato. **Non scrive
niente** — nessun record, nessun file, nessun evento.

### 3.4 `GET /api/v1/vendite/<dominio>/{id}/documenti/`

Lista a catalogo `documenti.documenti_sorgente` (dal 2026-09-27: contratto di
lista standard; fino ad allora `page`/`page_size` con default 50, che il FE non
passava — la lista troncava in silenzio).

| query param | effetto |
|---|---|
| `search` | ricerca libera sulle colonne accese a catalogo (`titolo`, `nome_file`) |
| `limit` / `offset` | paginazione (default 25, **max 200**) |
| `order_by` | whitelist `DOCUMENTI_SORGENTE_ORDER_COLUMNS` (`progressivo_sorgente`, `generato_at`, `titolo`, `nome_file`, `stato`); senza = `generato_at DESC` |
| `order_dir` | `asc` / `desc`; assente = DESC sulle date |
| `emittente_fiscale_id` | PK dell'emittente del documento — `lista_emittente_param`: scioglie il cancello di perimetro per chi vede più emittenti (il dialog lo passa dal documento aperto). Non filtra |

Risposta: envelope paginato standard (`count`, `page`, `page_size`,
`total_pages`, `results`). `422 E_UI_LISTA_EMITTENTE_DA_SCEGLIERE` con più
emittenti nello scope e nessun `emittente_fiscale_id`.

### 3.5 `GET/POST /api/v1/vendite/<dominio>/{id}/documenti/{documento_id}/allegati/`

* **GET** — elenco di **tutti** i file del documento: principale **e** allegati.
  E' quello che alimenta la row-expand del dialog documenti nel FE;
* **POST** — multipart, campo `allegati`: aggiunge file a un documento gia'
  generato (append). MIME e dimensione li valida il service.

### 3.6 `GET /api/v1/vendite/<dominio>/{id}/documenti/{documento_id}/file/`

### 3.6-bis `GET /api/v1/vendite/<dominio>/{id}/documenti/{documento_id}/file/{file_id}/`

Download del **documento principale** persistito: `Content-Disposition:
attachment`, evento `SCARICATO`.

Stessa cosa per **uno specifico file per id** — principale o allegato: e' la
variante che cabla la row-expand del dialog documenti nel FE (`downloadFile`).

### 3.7 `GET /api/v1/vendite/<dominio>/{id}/documenti/{documento_id}/ristampa/`

Ri-renderizza l'originale dalla **versione di template con cui nacque** e dal
**contesto congelato** di allora. Non persiste nulla oltre all'evento di audit.
Stream `inline`, come l'anteprima: e' una consultazione.

⭐ **Header di risposta `X-Ristampa-Pdf-Hash-Match`**: `1` se il PDF ricostruito
coincide **byte per byte** con l'originale, `0` se e' fedele nel contenuto ma
non nei byte (renderer non deterministico). La fedelta' viaggia in **header** e
non nel corpo perche' il corpo e' il PDF — dichiarata, non nascosta.

## 4. I guard comuni, e cosa rispondono

Ogni endpoint nidificato risolve il contesto **prima** di fare qualsiasi cosa
(`resolve_contesto_documentale`), anche quando l'id della sorgente non gli
servirebbe:

| condizione | codice | esito |
|---|---|---|
| sorgente inesistente o fuori perimetro | `E_DOCUMENTI_NOT_FOUND` | 404 |
| sorgente senza emittente fiscale risolto | `E_DOCUMENTI_VALIDATION` | 400 |
| tipo sorgente non configurato o non attivo | `E_DOCUMENTI_VALIDATION` | 400 |
| render fallito | `E_DOCUMENTI_RENDER_FAILED` | 500 (`TECNICO`) |
| storage non disponibile | `E_DOCUMENTI_STORAGE_FAILED` | 500 (`TECNICO`) |

⚠️ **Perche' il controllo c'e' anche dove sembra inutile.** Su `file/`,
`allegati/` e `ristampa/` lo scope vero e' sul `documento_id`; la verifica sulla
sorgente e' **defense-in-depth** contro il tampering dell'URL — chiedere il
documento di un'altra sorgente da' 404, non un file. Toglierla perche' «tanto
c'e' lo scope sul documento» e' esattamente il passo che apre il buco.

## 5. Permessi

Tutte le view dichiarano `area_funzionale = "vendite"` **e** l'oggetto del
catalogo permessi della sorgente (`model_permission`, applicato dalla factory a
tutte le otto view): i documenti sono una parte dell'oggetto e ne chiedono il
livello.

| dominio | `model_permission` |
|---|---|
| `preventivi` | `("vendite", "preventivo")` |
| `offerte` | `("vendite", "offerta_commerciale")` |
| `contratti` | `("vendite", "contratto")` |
| `ordini` | `("vendite", "ordine")` |
| `ddt` | `("vendite", "ddt")` |
| `fatture` | `("vendite", "fattura")` |

Il livello segue il metodo: i `GET` (lista, `file/`, `ristampa/`, elenco
allegati) bastano con **LETTURA**; i `POST` chiedono **TUTTO**, anche quelli che
non scrivono — `anteprima/` compresa — perché solo la lista ha
`is_search_endpoint`. Chi ha la sola lettura vede e scarica i documenti, ma non
genera né l'anteprima né un documento nuovo.

⭐ **Il permesso dell'emissione dalla riga del passaggio.** Un documento portato
al modello (guida `modello-documento-di-vendita` §6) passa
`emetti_passaggio=(testata, stato di emissione)`: la factory dichiara
`post_passaggio` e la catena dei permessi legge l'azione dalla riga della matrice,
la stessa del verbo. Oggi lo fa il **DDT** (`("vendite.ddt", "EMESSO")`, 2026-10-25).
Il **preventivo** dichiara ancora `emetti_post_permission="cambia_stato_preventivi"`
finché il suo giro del cantiere non lo porta al modello; offerte, contratti e
ordini non dichiarano un'azione. Le due forme si escludono (errore all'import).

## 6. Dove guardare nel codice

| cosa | dove |
|---|---|
| le otto view (flusso condiviso) | `apps/documenti/api/sorgente_documenti_views.py` |
| i delta di dominio | `apps/vendite/api/<dominio>_documenti_views.py` |
| guard di contesto e allegati | `apps/documenti/api/contesto_helpers.py`, `multipart_helpers.py` |
| generazione, download, ristampa | `apps/documenti/services/document_generation_service.py` |
| rotte | `apps/vendite/api/urls_<dominio>.py` (e `urls_v1.py` per preventivi/offerte/contratti) |
