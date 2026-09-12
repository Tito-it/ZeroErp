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
Senza override usa il template `is_default = true` per (sorgente, emittente).
Risposta **201** con il documento; scrive il record e l'evento `GENERATO`.

### 3.3 `POST /api/v1/vendite/<dominio>/{id}/documenti/anteprima/`

Stesso body di `genera/`. Risposta **binaria**: `application/pdf`,
`Content-Disposition: inline`, `Content-Length` valorizzato. **Non scrive
niente** — nessun record, nessun file, nessun evento.

### 3.4 `GET /api/v1/vendite/<dominio>/{id}/documenti/`

Lista paginata dei documenti della sorgente (`generato_at DESC`).

| query param | default | limite |
|---|---|---|
| `page` | 1 | — |
| `page_size` | 50 | **max 200** (cap lato view) |

Risposta: envelope standard con i campi del service piu' `page` e `page_size`.

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
| render fallito | `E_DOCUMENTI_RENDER_FAILED` | — |
| storage non disponibile | `E_DOCUMENTI_STORAGE_FAILED` | — |

⚠️ **Perche' il controllo c'e' anche dove sembra inutile.** Su `file/`,
`allegati/` e `ristampa/` lo scope vero e' sul `documento_id`; la verifica sulla
sorgente e' **defense-in-depth** contro il tampering dell'URL — chiedere il
documento di un'altra sorgente da' 404, non un file. Toglierla perche' «tanto
c'e' lo scope sul documento» e' esattamente il passo che apre il buco.

## 5. Permessi

Tutte le view dichiarano `area_funzionale = "vendite"`: valgono i permessi di
area (lettura/scrittura) del profilo operatore.

⚠️ **Un'asimmetria da decidere, non un difetto accertato.** Fra i cinque domini
che espongono `emetti/`, **solo `preventivi` dichiara anche un permesso di
processo** (`emetti_post_permission="cambia_stato_preventivi"`). Offerte,
contratti, ordini e DDT delegano la transizione al service di dominio senza
dichiarare un'azione di processo sulla view. Se emettere un DDT deve pesare
quanto cambiare stato a un preventivo, mancano quattro dichiarazioni; se non
deve, allora e' il preventivo l'eccezione e va scritto perche'. **Segnalato il
2026-08-19, non modificato.**

## 6. Dove guardare nel codice

| cosa | dove |
|---|---|
| le otto view (flusso condiviso) | `apps/documenti/api/sorgente_documenti_views.py` |
| i delta di dominio | `apps/vendite/api/<dominio>_documenti_views.py` |
| guard di contesto e allegati | `apps/documenti/api/contesto_helpers.py`, `multipart_helpers.py` |
| generazione, download, ristampa | `apps/documenti/services/document_generation_service.py` |
| rotte | `apps/vendite/api/urls_<dominio>.py` (e `urls_v1.py` per preventivi/offerte/contratti) |
