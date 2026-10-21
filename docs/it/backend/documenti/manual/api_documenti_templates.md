# API documenti — Templates e versioni (Django)

## Scopo

Esporre via HTTP il motore documentale parametrico per operatori e
responsabili: lista/dettaglio template, lista/dettaglio versioni, e
mutazioni sulla testata template (create + update).

## Contesto

Endpoint v1 del refactor `sviluppo-documenti.md` (Decisioni 25/30/72-76).
Gli endpoint di lettura interrogano direttamente le tabelle
`documenti.template_documenti` e `documenti.template_documenti_versioni`
con JOIN sui lookup (`documenti.tipi_documento_output`, `config.sorgenti`,
`documenti.render_engine_documento`) e **LEFT JOIN** sull'emittente
(`anagrafiche.emittenti_fiscali`): un modello standard non ne ha. I comandi admin di scrittura passano
dal service applicativo; la pubblicazione di una versione delega al DB la
chiusura atomica della versione pubblicata precedente tramite
`documenti.fn_pubblica_template_documento_versione(...)`.

Gli endpoint template/versioni hanno `area_funzionale = "documenti"`
(id area=11, schema_db=`documenti`). Il livello area si applica con la
catena standard TUTTO/LETTURA/BLOCCATO; lo scope dati e' applicato in
repository tramite `PermissionResolver.get_emittenti_pk_ids` (whitelist
`emittenti_fiscali.id`): admin globale e superuser vedono tutto, gli
operatori vedono i template dei propri emittenti **più i modelli standard**
(condizione `t.standard OR t.emittente_fiscale_id = ANY(whitelist)`); con
whitelist vuota si vedono i soli standard. Le mutazioni admin usano
`post_permission = "documenti_template_manage"` (Decisione 75).

### I modelli standard (dal 2026-10-20)

La testata ha la colonna `standard` (bool): un modello standard non ha
emittente (`emittente_fiscale_id` NULL, CHECK
`chk_template_documenti_standard_senza_emittente`) e serve a tutti. Lo
standard e le sue versioni si scrivono **solo** da seed/changeSet: ogni
scrittura dall'applicazione (PATCH della testata, crea/aggiorna/elimina/clona/
pubblica versione) la rifiuta il trigger
`documenti.trgfn_template_standard_guard_sola_lettura` con `403`
`E_DOCUMENTI_TEMPLATE_STANDARD_SOLA_LETTURA`. Chi lo vuole diverso lo
**personalizza** (§5-bis): la copia è un modello dell'emittente, la cui prima
versione porta `derivata_da_versione_id` (la versione standard d'origine). Nella
generazione lo standard subentra quando l'emittente non ha modelli suoi che
possono stampare (vedi [api_documenti_per_sorgente](api_documenti_per_sorgente.md) §3.2).

Gli endpoint di generazione/anteprima/download dei documenti generati sono
documentati nelle API delle sorgenti funzionali che li espongono
(es. contratti e preventivi).

### La forma dei dati (dal 2026-09-30)

Ogni versione dichiara la **forma dei dati che legge**
(`versione_contesto`, intero >= 1, NOT NULL senza default). Il builder di
contesto del template dichiara la forma che **produce** (`CONTEXT_VERSION`
nel codice, da cui esce anche `_meta.context_version` del contesto). Una
versione si **pubblica** e si **stampa** solo se le due coincidono: lo decide
`documenti.fn_guard_versione_contesto`, chiamata dal verbo di pubblicazione,
dal backend prima del render (generazione e anteprima) e dal trigger
sull'INSERT della stampa. Il rifiuto è `409
E_DOCUMENTI_VERSIONE_CONTESTO_DIVERSA`, con la frase a catalogo che nomina
versione, template e le due forme. Una BOZZA può dichiarare una forma che il
builder non produce ancora: è così che si prepara la versione successiva.
La ristampa fedele non ricontrolla: la coppia versione/contesto congelata è
stata verificata alla stampa. Brief:
`brief-db-documenti-versione-contesto-template.md`.

---

## Endpoint

### 1. Lista template

#### Input

- Metodo: `GET`
- Path canonico: `/api/v1/documenti/templates/`
- Header sicurezza: `Authorization: Bearer <access_token>`
- `is_search_endpoint = True` -> attiva `SearchBurstRateThrottle`
- Query param (tutti opzionali; assente o vuoto = nessun filtro):
  - `search` (string) — ricerca libera: le colonne le decide il catalogo della lista
    `documenti.template_documenti` (`ricerca_full` nella sua configurazione). Da un
    carattere, senza 400: tabella di configurazione (Tid, 2026-09-24). ⛔ Il `codice_interno` non si cerca (dal
    2026-09-24, decisione di Tid)
  - `attivo` (bool) — `true`/`false` per filtrare solo attivi/disattivati
  - `tipo_documento_output_id` (int)
  - `sorgente_tipo_id` (int)
  - `emittente_fiscale_id` (int) — ulteriore filtro dentro lo scope operatore
  - `limit` (int) — default `25`, max `200`
  - `offset` (int) — default `0`
  - `order_by` (string) — whitelist di 10 colonne: `codice` (default),
    `codice_interno`, `descrizione`, `attivo`, `is_default`,
    `tipo_documento_output_descrizione`, `sorgente_tipo_descrizione`,
    `emittente_ragione_sociale`, `data_insert`, `data_update`. Fuori whitelist:
    `400` `E_DOCUMENTI_VALIDATION`
  - `order_dir` (string) — `asc` o `desc`. Assente: `asc`, salvo
    `data_insert`/`data_update` che partono `desc` (dal 2026-10-20)

  ⚠️ Dal 2026-09-27 la paginazione è `limit`/`offset` con default 25: `page` e
  `page_size` in query sono un 400 `E_VALIDATION_INPUT` (dal 2026-10-20; prima
  non erano letti, e prima ancora `page_size` valeva 50). Lo schema
  OpenAPI della view dichiara ancora `page`/`page_size`.

#### Output

- `200`:

```json
{
  "data": {
    "count": 1,
    "page": 1,
    "page_size": 25,
    "total_pages": 1,
    "results": [
      {
        "id": 1,
        "codice": "TPL-PREV-001",
        "codice_interno": "TPL_PREV_001",
        "descrizione": "Template preventivo standard",
        "is_default": true,
        "attivo": true,
        "tipo_documento_output_id": 1,
        "tipo_documento_output_codice": "PDF_FINALE",
        "tipo_documento_output_descrizione": "PDF finale",
        "sorgente_tipo_id": 10,
        "sorgente_tipo_codice": "PREVENTIVO",
        "sorgente_tipo_descrizione": "Preventivo vendita",
        "context_builder_code": "PREVENTIVO",
        "file_name_pattern": "preventivo-{numero}.pdf",
        "standard": false,
        "emittente_fiscale_id": 5,
        "emittente_fiscale_codice": "EF-001",
        "emittente_ragione_sociale": "Acme SRL",
        "data_insert": "2026-04-29T00:00:00+02:00",
        "data_update": "2026-04-29T00:00:00+02:00"
      }
    ]
  },
  "meta": { "request_id": "..." }
}
```

Su un modello standard `emittente_fiscale_id`, `emittente_fiscale_codice` ed
`emittente_ragione_sociale` sono `null`.

- `400`: parametri non validi (query param int malformato, `order_by` fuori whitelist)
- `401`: JWT mancante o non valido
- `403`: livello area `documenti` = BLOCCATO

### 2. Dettaglio template

#### Input

- Metodo: `GET`
- Path: `/api/v1/documenti/templates/<int:template_id>/`
- Header sicurezza: `Authorization: Bearer <access_token>`

#### Output

- `200`: stessi campi della lista + `meta` (jsonb), `storicizza`,
  `user_insert`, `user_update`, e `versione_contesto_builder` (int|null): la
  forma dei dati che il builder del template (`context_builder_code`) produce
  **oggi**. Non è una colonna: la legge il backend dal registry dei builder.
  `null` = builder non registrato, e il template non genera né pubblica.
  La portano anche le risposte di crea/aggiorna testata.
- `404`: template inesistente o fuori scope emittente — codice
  `E_DOCUMENTI_NOT_FOUND`. La risposta non distingue i due casi (no leak
  di esistenza fuori scope).

### 3. Lista versioni di un template

#### Input

- Metodo: `GET`
- Path: `/api/v1/documenti/templates/<int:template_id>/versioni/`
- Lista a catalogo `documenti.template_versioni` (dal 2026-09-27: paginata).
- Query param (opzionali):
  - `attivo` (bool strict) — assente = nessun filtro (attive e non)
  - `stato` (string) — whitelist: `BOZZA`, `PUBBLICATA`, `OBSOLETA` (case-insensitive)
  - `search` (string) — ricerca libera sulle colonne accese a catalogo (`titolo`)
  - `limit` / `offset` (int) — paginazione (default 25, massimo 200)
  - `order_by` (string) — whitelist `TEMPLATE_VERSIONI_ORDER_COLUMNS`:
    `versione`, `titolo`, `stato`, `valido_dal`, `valido_al` (NULL = senza
    scadenza, in fondo in ASC), `attivo`, `data_update`; senza = `versione DESC`
  - `order_dir` (string) — `asc` / `desc`; assente = DESC sulle date
  - `emittente_fiscale_id` (int, PK) — `lista_emittente_param`: scioglie il
    cancello di perimetro per chi vede più emittenti (il super admin su
    «Tutti»). Vale anche sul **POST** di creazione versione (§7), che sta sulla
    stessa rotta: il FE lo manda con `paramsEmittente()`. Non filtra.

#### Output

- `200`:

```json
{
  "data": {
    "count": 1,
    "page": 1,
    "page_size": 25,
    "total_pages": 1,
    "results": [
      {
        "id": 11,
        "template_documento_id": 1,
        "versione": 1,
        "stato": "PUBBLICATA",
        "titolo": "v1 standard",
        "formato_template": "HTML",
        "render_engine_id": 1,
        "render_engine_codice_interno": "WEASYPRINT",
        "render_engine_codice": "WEASYPRINT",
        "render_engine_descrizione": "WeasyPrint",
        "page_format": "A4",
        "page_orientation": "PORTRAIT",
        "valido_dal": "2026-05-01",
        "valido_al": null,
        "versione_contesto": 2,
        "derivata_da_versione_id": null,
        "attivo": true,
        "data_insert": "2026-04-29T00:00:00+02:00",
        "data_update": "2026-04-29T00:00:00+02:00"
      }
    ]
  },
  "meta": { "request_id": "..." }
}
```

`derivata_da_versione_id` (int|null): sulla prima versione di una copia
personalizzata, l'id della versione standard da cui è partita; `null` altrove.

- `400`: `stato` non in whitelist — codice `E_DOCUMENTI_VALIDATION`; `order_dir` non valido
- `404`: template inesistente o fuori scope — codice `E_DOCUMENTI_NOT_FOUND`
- `422`: `E_UI_LISTA_EMITTENTE_DA_SCEGLIERE` — più emittenti nello scope e nessun `emittente_fiscale_id` in query

> **Campi render engine** — `render_engine_codice_interno` e' la chiave
> **immutabile** (`documenti.render_engine_documento.codice_interno`, es.
> `WEASYPRINT`): e' su questo che il backend valida la whitelist engine. Il
> `render_engine_codice` e' l'etichetta **mutabile** a video (rinominabile
> dall'utente) — usarlo solo per display, mai per logica. La logica FE che deve
> discriminare l'engine usi `render_engine_codice_interno`.

### 4. Dettaglio versione

#### Input

- Metodo: `GET`
- Path: `/api/v1/documenti/templates/<int:template_id>/versioni/<int:versione_id>/`

#### Output

- `200`: campi della lista versione + payload completo:
  - `html_template` (text)
  - `css_template` (text|null)
  - `markdown_template` (text|null)
  - `margin_top_mm`, `margin_right_mm`, `margin_bottom_mm`, `margin_left_mm` (numeric)
  - `context_schema` (jsonb)
  - `meta` (jsonb)
  - `storicizza`, `user_insert`, `user_update`
- `404`: template o versione inesistente / fuori scope — codice
  `E_DOCUMENTI_NOT_FOUND`. Defense-in-depth: la versione e' ritornata solo
  se il binding `versione.template_documento_id` corrisponde al
  `template_id` del path (un id versione orfano di altro template
  servito tramite path di un template diverso ritorna 404).

### 5. Crea testata template (Tranche E)

#### Input

- Metodo: `POST`
- Path: `/api/v1/documenti/templates/`
- Header sicurezza: `Authorization: Bearer <access_token>`
- Permesso azione: `documenti_template_manage` (`post_permission`)
- Body JSON (campi obbligatori marcati con `*`):
  - `tipo_documento_output_id`* (int positivo)
  - `sorgente_tipo_id`* (int positivo)
  - `emittente_fiscale_id`* (int positivo, **deve essere nello scope dell'utente**)
  - `codice`* (string non vuota, max 120 char)
  - `codice_interno`* (string non vuota, max 120 char)
  - `descrizione`* (string non vuota, max 500 char)
  - `context_builder_code`* (string non vuota, max 160 char — la create non lo confronta col registry: vedi Regole)
  - `file_name_pattern` (string nullable, max 200 char)
  - `is_default` (bool, default `false`)
  - `attivo` (bool, default `true`)
  - `meta` (jsonb object)

#### Output

- `200`: dettaglio del template appena creato (stesso shape di "Dettaglio template").
- `400` `E_DOCUMENTI_VALIDATION`:
  - chiave non whitelisted nel payload;
  - campo richiesto mancante o vuoto;
  - `emittente_fiscale_id` fuori dallo scope dell'utente (no `403`/`404` leak);
  - violazione vincolo unique `uq_template_documenti_emittente_sorgente_codice` -> "Esiste gia' un template con questo codice per emittente e sorgente.";
  - violazione `uq_template_documenti_emittente_sorgente_codice_interno` -> idem per codice interno;
  - violazione partial-unique `uq_template_documenti_default_attivo` -> "Esiste gia' un template default attivo per emittente, sorgente e tipo output." (FE deve disabilitare il vecchio default prima di settarne uno nuovo, vedi Regole);
  - FK violation su `tipo_documento_output_id`/`sorgente_tipo_id`/`emittente_fiscale_id` -> messaggio specifico.
- `401`: JWT mancante o non valido.
- `403`: utente senza azione processo `documenti_template_manage` abilitata sul proprio profilo.

### 6. Aggiorna testata template (Tranche E)

#### Input

- Metodo: `PATCH`
- Path: `/api/v1/documenti/templates/<int:template_id>/`
- Header sicurezza: `Authorization: Bearer <access_token>`
- Permesso azione: `documenti_template_manage` (`patch_permission`)
- Body JSON (tutti opzionali; almeno uno obbligatorio):
  - `codice` (string non vuota, max 120)
  - `codice_interno` (string non vuota, max 120)
  - `descrizione` (string non vuota, max 500)
  - `context_builder_code` (string non vuota, max 160)
  - `file_name_pattern` (string nullable, max 200)
  - `is_default` (bool, **non NULL**)
  - `attivo` (bool, **non NULL**)
  - `meta` (jsonb object)

**Campi immutabili dopo create** (rifiutati con `E_DOCUMENTI_VALIDATION`
prima di qualsiasi altra validazione):

- `tipo_documento_output_id`
- `sorgente_tipo_id`
- `emittente_fiscale_id`

Per "spostare" un template ad altro emittente/sorgente/output: creare un
nuovo template e disabilitare il precedente.

#### Output

- `200`: dettaglio del template aggiornato (stesso shape di "Dettaglio
  template"; ricarica via `get_template` per restituire decodifiche
  fresche delle FK).
- `400` `E_DOCUMENTI_VALIDATION`:
  - campo immutabile in payload;
  - chiave extra non whitelisted;
  - `is_default`/`attivo` esplicito a `null`;
  - payload privo di campi aggiornabili dopo validation -> "Nessun campo aggiornabile presente nel payload.";
  - violazione unique/partial-unique come per la create.
- `401`/`403`: come la create.
- `403` `E_DOCUMENTI_TEMPLATE_STANDARD_SOLA_LETTURA`: il template è uno standard
  (lo rifiuta il DB).
- `404` `E_DOCUMENTI_NOT_FOUND`: template inesistente o fuori scope
  emittente. La risposta non distingue i due casi (no leak di esistenza).

### 5-bis. Personalizza un modello standard (dal 2026-10-20)

#### Input

- Metodo: `POST`
- Path: `/api/v1/documenti/templates/<int:template_id>/personalizza/`
- Permesso azione: `documenti_template_manage` (`post_permission`)
- Body JSON:
  - `emittente_fiscale_id`* (int positivo, **nello scope dell'utente**)
  - `is_default` (bool, default `true`: chi personalizza vuole stampare con la copia)
  - `codice`, `codice_interno`, `descrizione` (string; default: quelli dello
    standard — servono quando l'emittente ha già un modello con quel codice)
  - Un valore `null` vale come assente. Altre chiavi: `400`.

#### Output

In una transazione crea la **testata** (copia di tipo output, sorgente,
`context_builder_code`, `file_name_pattern` dello standard; `attivo=true`,
`standard=false`) e la **versione 1 in BOZZA**, copiata dall'ultima versione
`PUBBLICATA` dello standard, con `derivata_da_versione_id` = quella versione.
Finché la bozza non è pubblicata la copia non stampa e l'emittente resta sullo
standard.

- `200`: dettaglio del modello nuovo (shape di "Dettaglio template").
- `400` `E_DOCUMENTI_VALIDATION`: il template non è uno standard; lo standard
  non ha una versione pubblicata; chiave fuori contratto; `emittente_fiscale_id`
  mancante o fuori scope; unique violate come nella create (un predefinito
  attivo già presente → rifare con `is_default=false`; codice già usato → un
  `codice` proprio).
- `404` `E_DOCUMENTI_NOT_FOUND`: template inesistente o fuori scope.

### 7. Crea versione BOZZA (Tranche F)

#### Input

- Metodo: `POST`
- Path: `/api/v1/documenti/templates/<int:template_id>/versioni/`
- Permesso azione: `documenti_template_manage` (`post_permission`)
- Body JSON (campi obbligatori marcati con `*`):
  - `titolo`* (string non vuota, max 500)
  - `html_template`* (string non vuota — payload HTML del template)
  - `render_engine_id`* (int positivo, FK su `documenti.render_engine_documento`)
  - `versione_contesto`* (int positivo) — la forma dei dati che la versione
    legge. **Nessun default**, né qui né a DB: la dichiara chi scrive la
    versione (il frontend propone `versione_contesto_builder` del template)
  - `formato_template` (string, un `codice_interno` di `documenti.formati_template`, default `HTML`)
  - `css_template` (string nullable)
  - `markdown_template` (string nullable)
  - `page_format` (string, un `codice_interno` di `documenti.formati_pagina`, default `A4`)
  - `page_orientation` (string, un `codice_interno` di `documenti.orientamenti_pagina`, default `PORTRAIT`)
  - ⭐ I valori ammessi dei tre campi sono i **vocabolari** a DB (dal 2026-10-04,
    `brief-db-vocabolari-versione-template`), non una lista del backend: il frontend li legge dal
    lookup generico (`rel=documenti.formati_template` / `formati_pagina` / `orientamenti_pagina`,
    con `etichetta_key`) e il rifiuto lo da' la FK, tradotto sul campo.
  - `margin_top_mm` / `margin_right_mm` / `margin_bottom_mm` / `margin_left_mm` (number >= 0, default 10; sono accettate anche stringhe numeriche come `"15.00"`, normalizzate dal service)
  - `valido_dal` (date ISO, nullable in BOZZA — diventa obbligatorio in pubblicazione)
  - `valido_al` (date ISO, nullable)
  - `context_schema` (jsonb object, default `{}`)
  - `meta` (jsonb object, default `{}`)
  - `attivo` (bool, default `true`)
  - ⭐ Un campo **omesso** prende il default della **colonna** (formato, pagina, orientamento,
    margini): il drawer della versione lascia vuoti quei campi in creazione e non li manda, cosi'
    il default resta uno solo, a DB.

#### Output

- `200`: dettaglio della versione creata (stesso shape di "Dettaglio versione").
  - `versione`: numero calcolato come `MAX(versione)+1` per il template.
  - `stato`: sempre `BOZZA` su create.
- `400` `E_DOCUMENTI_VALIDATION`: chiave non whitelisted, campo richiesto
  mancante (anche `versione_contesto`, col campo), `formato_template`/`page_format`/
  `page_orientation` fuori vocabolario (FK, col campo), margine negativo, race su
  `uq_template_documenti_versioni_template_versione` (riprovare).
- `404` `E_DOCUMENTI_NOT_FOUND`: template inesistente o fuori scope.

### 8. Aggiorna versione BOZZA (Tranche F)

#### Input

- Metodo: `PATCH`
- Path: `/api/v1/documenti/templates/<int:template_id>/versioni/<int:versione_id>/`
- Permesso azione: `documenti_template_manage` (`patch_permission`)
- Body JSON (tutti opzionali; almeno uno obbligatorio): stesse chiavi della
  create, esclusi i campi calcolati `template_documento_id`, `versione`,
  `stato`. La transizione di stato passa solo dall'endpoint dedicato
  `pubblica/`. `versione_contesto` si cambia qui, solo in BOZZA (da
  PUBBLICATA lo rifiuta anche il trigger A1, dal `20260930-17`).

#### Output

- `200`: dettaglio della versione aggiornata.
- `400` `E_DOCUMENTI_VALIDATION`: chiave extra, payload vuoto post-validation,
  `formato_template`/`page_format`/`page_orientation` fuori vocabolario (FK, col
  campo), margine negativo o non numerico,
  `attivo`/`is_default` esplicito a `null`. I margini provenienti dal DB come
  stringhe decimali (`"15.00"`) sono validi e vengono convertiti prima del write.
- `404` `E_DOCUMENTI_NOT_FOUND`: template/versione inesistente o fuori scope.
- `403` `E_DOCUMENTI_TEMPLATE_STANDARD_SOLA_LETTURA`: versione di un modello
  standard (vale anche per create, delete, clona e pubblica).
- `409` `E_DOCUMENTI_VERSIONE_PUBBLICATA_IMMUTABILE`: la versione e' in
  stato `PUBBLICATA` (o `OBSOLETA`). Per modificare crea o clona una nuova
  BOZZA. Defense-in-depth: il service applica il check prima del DB; il
  trigger DB A1 (`trgfn_template_documenti_versioni_protect_pubblicata`)
  blocca comunque la mutazione su PUBBLICATA come guardrail finale.

### 9. Elimina versione BOZZA (Tranche F)

#### Input

- Metodo: `DELETE`
- Path: `/api/v1/documenti/templates/<int:template_id>/versioni/<int:versione_id>/`
- Permesso azione: `documenti_template_manage` (`delete_permission`)
- No body.

#### Output

- `200`: `{"data": {"deleted": true, "versione_id": <id>}}`.
- `404` `E_DOCUMENTI_NOT_FOUND`: template/versione inesistente o fuori scope.
- `409` `E_DOCUMENTI_VERSIONE_DELETE_BLOCKED`: la versione e' in stato
  `PUBBLICATA`/`OBSOLETA` oppure e' gia' usata da almeno un documento
  generato. Defense-in-depth: il service applica il check stato; il
  trigger DB A2 (`trgfn_template_documenti_versioni_block_delete`) blocca
  comunque la DELETE come guardrail finale anche per il caso "documenti
  generati collegati" (verifica solo lato DB).

### 10. Clona versione (Tranche F)

#### Input

- Metodo: `POST`
- Path: `/api/v1/documenti/templates/<int:template_id>/versioni/<int:versione_id>/clona/`
- Permesso azione: `documenti_template_manage` (`post_permission`)
- Body JSON (tutti opzionali): override sui campi del source.
  - `titolo` (string non vuota, max 500)
  - `valido_dal` (date ISO)
  - `valido_al` (date ISO)
  - `attivo` (bool, **non NULL**)
  - `meta` (jsonb object)

#### Output

- `200`: dettaglio della nuova versione clone.
  - Source copiato: `formato_template`, `html_template`, `css_template`,
    `markdown_template`, `render_engine_id`, `page_format`,
    `page_orientation`, `margin_*`, `context_schema`, `versione_contesto`
    (il corpo è lo stesso, quindi legge le stesse chiavi; per preparare la
    forma successiva la si cambia sulla bozza). (`meta` se non overrideato.)
  - Default forzati: `stato='BOZZA'`, `versione=MAX+1`, `valido_dal=NULL`,
    `valido_al=NULL` (le date di una nuova bozza si fissano alla
    pubblicazione).
- `400` `E_DOCUMENTI_VALIDATION`: chiave non whitelisted in payload override.
- `404` `E_DOCUMENTI_NOT_FOUND`: source inesistente o fuori scope.

### 11. Pubblica versione (Tranche F)

#### Input

- Metodo: `POST`
- Path: `/api/v1/documenti/templates/<int:template_id>/versioni/<int:versione_id>/pubblica/`
- Permesso azione: `documenti_template_manage` (`post_permission`)
- Body JSON:
  - `valido_dal`* (date ISO) — obbligatorio per la transizione (vincolo
    DB `chk_template_documenti_versioni_valido_dal_pubblicata`).
  - `valido_al` (date ISO, nullable) — se valorizzato deve essere `>= valido_dal`
    (lo giudica il database, non il service: vedi sotto).

#### Output

- `200`: dettaglio della versione pubblicata (`stato='PUBBLICATA'`,
  `valido_dal` valorizzato).
- `400` `E_DATA_AL_MINORE_DAL` (campo `valido_al`): `valido_al < valido_dal`.
  Lo solleva il guard comune `script.trgfn_guard_date_validita` sull'UPDATE
  finale della funzione di pubblicazione, come negli altri scritti delle
  versioni; le chiusure delle versioni precedenti già fatte si annullano con la
  transazione. Dal 2026-09-24 la funzione non ripete più la regola sui
  parametri (brief-db-guard-date-validita §14).
- `400` `E_DOCUMENTI_VALIDATION`:
  - `valido_dal` mancante;
  - versione gia' in `PUBBLICATA` o `OBSOLETA` (idempotenza per design:
    una seconda chiamata dopo la pubblicazione iniziale ritorna 400 con
    "stato_corrente=PUBBLICATA").
- `400` `E_DOCUMENTI_VALIDATION` dal registry: il `context_builder_code` del
  template non è un builder registrato — non c'è una forma con cui
  confrontare, e la pubblicazione non arriva al verbo.
- `409` `E_DOCUMENTI_VERSIONE_CONTESTO_DIVERSA`: la versione legge una forma
  dei dati diversa da quella che il builder del template produce oggi. Il
  service passa al verbo la forma del builder (`p_versione_contesto`,
  obbligatorio dal `20260930-21`); il confronto è del DB, prima di chiudere
  qualunque altra versione. La versione resta BOZZA.
- `409` `E_DOCUMENTI_VERSIONE_OVERLAP`: violazione EXCLUDE gist parziale
  `ex_template_documenti_versioni_no_overlap_pubblicata` (ripristino enforcement
  2026-06-02, migration `20260602-05`) — le date si sovrappongono con un'altra
  versione PUBBLICATA attiva e l'auto-close non risolve (es. nuova decorrenza
  uguale a una versione gia' PUBBLICATA). Codice dedicato 409, armonizzato con
  gli altri overlap (`E_VENDITE_PROMO_OVERLAP` / `E_VENDITE_LISTINO_VERSIONE_OVERLAP`);
  prima ricadeva nel generico `E_DOCUMENTI_VALIDATION` (400).
- `404` `E_DOCUMENTI_NOT_FOUND`: template/versione inesistente o fuori scope.

#### Auto-close versione precedente

La pubblicazione passa dalla funzione DB
`documenti.fn_pubblica_template_documento_versione(...)`. Nella stessa
transazione la funzione:

1. blocca le versioni dello stesso template;
2. individua le versioni `PUBBLICATA + attivo` con `valido_dal < nuovo.valido_dal`
   ancora aperte a `nuovo.valido_dal` (`nuovo.valido_al` non entra nel
   giudizio: con date valide è lo stesso insieme delle «sovrapposte»);
3. le porta a `OBSOLETA`;
4. imposta `valido_al = nuovo.valido_dal - 1`;
5. pubblica la nuova `BOZZA`.

Il vincolo EXCLUDE resta il guardrail finale contro sovrapposizioni non
gestibili automaticamente.

### 12. Builder di contesto registrati (dal 2026-10-03)

- Metodo: `GET`
- Path: `/api/v1/documenti/context-builders/`
- Permesso: livello d'area `documenti` (lettura)
- Output `200`: `{"data": {"results": [{"codice", "versione_contesto"}]}}`, ordinati per codice
  — l'envelope `results` dei lookup.

Il **registro** dei builder (`context_builders.registry.builder_registrati`), cioè cio' che il
processo backend sa davvero costruire, con la forma dei dati di ciascuno. ⭐ E' la tendina
«Context builder» del drawer del template: fino al 2026-10-03 il frontend ne teneva una copia
scritta a mano, con un flag «registrato» anch'esso a mano. Il registro e' di processo
(`VenditeConfig.ready()`), non del DB. L'etichetta la danno i locales
(`documenti.context_builders.<CODICE>`), con ripiego sul codice.

---

## Regole

- **Scope operatore**: tutti gli endpoint applicano lo scope emittente
  via `PermissionResolver.get_emittenti_pk_ids(user)`. Operatore con
  emittenti assegnati vede solo i template dei propri emittenti; admin
  globale/superuser vedono tutto. I modelli standard sono visibili a
  tutti, anche con whitelist vuota (che mostra i soli standard). Utente non
  autenticato (corner case: bypass auth): scope = `[]`, cioè i soli standard.
- **Lookup vs scope**: il filtro query `emittente_fiscale_id` si applica
  *dentro* lo scope. Un operatore che chiede `?emittente_fiscale_id=999`
  fuori dal proprio scope ottiene comunque lista vuota (no
  `forbidden`/`leak`).
- **Search ricerca testuale**: le colonne le decide il catalogo della lista
  (BB `add_ricerca_full_condition`, dal 2026-09-24). Da un carattere, senza
  400 (tabella di configurazione, Tid 2026-09-24); search vuota = nessun filtro.
- **Paginazione**: `limit` in `[1, 200]` (default 25), `offset >= 0`.
  Tiebreaker `t.id` per una paginazione deterministica anche con duplicati
  sulla colonna di sort.
- **Whitelist ORDER BY**: solo le 10 colonne di `TEMPLATES_ORDER_COLUMNS`
  (vedi §1) sono ammesse. Valori fuori whitelist -> `400 E_DOCUMENTI_VALIDATION`
  con elenco delle colonne ammesse (defense-in-depth lato repository,
  fail prima del round-trip DB).
- **Validazione `stato` versione**: il caller passa lowercase o uppercase;
  il service normalizza a UPPER e confronta con `{BOZZA,PUBBLICATA,OBSOLETA}`.
  Set chiuso allineato al CHECK DB.
- **Defense-in-depth versione**: `get_versione` in repository binda
  `template_documento_id`; la view passa il template_id dal path. Un id
  versione di un template diverso non e' mai esposto via path di un
  altro template.
- **Idempotency-Key**: nessun endpoint lo richiede.
- **Versione: ciclo vita di stato e immutabilita'**:
  - `BOZZA` -> editable (PATCH) ed eliminabile (DELETE) finche' non viene
    referenziata da documenti generati;
  - `BOZZA -> PUBBLICATA` solo via endpoint `pubblica/`, mai via PATCH
    diretto. Richiede `valido_dal NOT NULL`.
  - `PUBBLICATA` -> immutabile (trigger DB A1 + service guard). Per
    modificare, `clona` la versione in nuova BOZZA.
  - `OBSOLETA` -> stato terminale. La transizione `PUBBLICATA -> OBSOLETA`
    e' eseguita dalla funzione DB di pubblicazione quando una nuova versione
    successiva sostituisce la precedente.
- **Numero versione calcolato**: `MAX(versione)+1` su `template_documento_id`.
  Race condition rara: due chiamate concorrenti calcolano lo stesso numero
  -> il vincolo unique `uq_template_documenti_versioni_template_versione`
  blocca il secondo INSERT, errore parlante invita al retry.
- **Pubblicazione e overlap**: il comando `pubblica/` delega alla funzione DB
  `documenti.fn_pubblica_template_documento_versione(...)`. La funzione blocca
  le versioni dello stesso template, chiude a `nuovo.valido_dal - 1` le
  `PUBBLICATA` con decorrenza strettamente precedente ancora aperte a quella data,
  le porta a `OBSOLETA` e pubblica la nuova `BOZZA`. Il vincolo GiST EXCLUDE
  `ex_template_documenti_versioni_no_overlap_pubblicata` resta guardrail finale
  contro sovrapposizioni residue o race concorrenti.
- **`is_default` partial-unique senza demote automatico**: setting
  `is_default=true` su create/update/personalizza mentre esiste gia' un altro
  template default attivo per `(tipo_documento_output_id, sorgente_tipo_id,
  emittente_fiscale_id)` ritorna `400 E_DOCUMENTI_VALIDATION`. Il FE
  deve disabilitare il vecchio default (`PATCH is_default=false`) prima
  di settare il nuovo. Decisione di design: nessuna magia in transazione
  2-step lato BE.
- **`context_builder_code` e registry**: create e update controllano solo il
  formato (string non vuota), quindi si può creare un template che punta a un
  builder non registrato. Il registry
  (`apps.documenti.services.context_builders.registry`) lo consultano: il
  dettaglio template (`versione_contesto_builder`, `null` se non registrato),
  la pubblicazione (`400` se non registrato), generazione e anteprima, e
  `GET context-builders/` (§12).
- **Campi immutabili in update** (`tipo_documento_output_id`,
  `sorgente_tipo_id`, `emittente_fiscale_id`): rifiutati prima della
  validazione `validate_allowed_keys` per messaggio parlante. La chiave
  logica del template e' la tripla (output, sorgente, emittente):
  cambiarla equivale a creare un template diverso.
- **Scope emittente in create**: l'`emittente_fiscale_id` del payload
  deve appartenere alla whitelist `PermissionResolver.get_emittenti_pk_ids`
  dell'utente. Admin globale + superuser bypassano (la FK DB blocca id
  inesistenti). Operatore fuori scope -> `400 E_DOCUMENTI_VALIDATION`
  (no `403`/`404`: l'utente conosce gia' il proprio scope dal `/me/`).
- **JWT obbligatorio** su tutte le 12 rotte di `/api/v1/documenti/` (template,
  versioni e comandi, personalizza, context-builders, asset).

---

## Dipendenze DB

- `documenti.template_documenti` — testata template
- `documenti.template_documenti_versioni` — versioni (HTML/CSS/markdown)
- `documenti.tipi_documento_output` (INNER JOIN decodifica)
- `documenti.render_engine_documento` (INNER JOIN decodifica)
- `config.sorgenti` (INNER JOIN decodifica)
- `anagrafiche.emittenti_fiscali` (LEFT JOIN decodifica + scope: lo standard non ha emittente)
- `script.fn_get_emittenti_scope_pk_ids` (via `PermissionResolver.get_emittenti_pk_ids`; fino al 2026-09-12 questa riga nominava una `fn_get_emittenti_for_user` che non esiste)

Nessuna funzione DB applicativa intermedia: query raw SQL parametriche
nel repository.

---

## Permessi

- **Lettura** (endpoint 1-4): livello area `documenti` >= LETTURA. Nessun
  `permission_codename` aggiuntivo richiesto sulla view.
- **Scrittura testata** (endpoint 5-6, Tranche E):
  - `ApiTemplateList.post_permission = "documenti_template_manage"`
  - `ApiTemplateDetail.patch_permission = "documenti_template_manage"`
- **Scrittura versioni** (endpoint 7-11, Tranche F): stesso permesso
  `documenti_template_manage` su:
  - `ApiTemplateVersioniList.post_permission`
  - `ApiTemplateVersioneDetail.patch_permission` + `delete_permission`
  - `ApiTemplateVersioneClona.post_permission`
  - `ApiTemplateVersionePubblica.post_permission`
- **Personalizza** (§5-bis): `ApiTemplatePersonalizza.post_permission = "documenti_template_manage"`.
- **Asset**: upload (`POST asset/`) e PATCH metadati con
  `documenti_asset_manage`; lettura, download e miniatura col livello d'area.
- **Generazione/lista/download PDF**: permessi del dominio sorgente (area
  `vendite` + oggetto della sorgente), vedi
  [api_documenti_per_sorgente](api_documenti_per_sorgente.md).

Vedi Decisione 75 in `sviluppo-documenti.md` §10.

---

## Codici errore

| Codice | HTTP | Quando |
|---|---|---|
| `E_DOCUMENTI_VALIDATION` | 400 | `stato` versione fuori whitelist; `template_id`/`versione_id` non interi positivi; in write: chiave non whitelisted, campo richiesto mancante, campo immutabile, `emittente_fiscale_id` fuori scope, margini non numerici/negativi, violazioni unique/partial-unique/FK del DDL; pubblicazione: `valido_dal` mancante, stato non BOZZA |
| `E_DATA_AL_MINORE_DAL` | 400 | `valido_al < valido_dal` in create/clone/update/pubblicazione di una versione e in upload/PATCH di un asset: guard comune `script.trgfn_guard_date_validita`, campo `valido_al`. Il service non lo anticipa (dal 2026-09-23) |
| `E_DOCUMENTI_VERSIONE_OVERLAP` | 409 | pubblicazione con overlap residuo verso un'altra versione `PUBBLICATA` attiva che l'auto-close non risolve (EXCLUDE `ex_template_documenti_versioni_no_overlap_pubblicata`) |
| `E_DOCUMENTI_NOT_FOUND` | 404 | template/versione inesistente o fuori scope emittente (no leak) |
| `E_DOCUMENTI_TEMPLATE_STANDARD_SOLA_LETTURA` | 403 | scrittura su un modello standard o su una sua versione (trigger `trgfn_template_standard_guard_sola_lettura`) |
| `E_DOCUMENTI_VERSIONE_PUBBLICATA_IMMUTABILE` | 409 | tentativo di modificare versione `PUBBLICATA` (Tranche F). Trigger DB A1 + service guard |
| `E_DOCUMENTI_VERSIONE_DELETE_BLOCKED` | 409 | tentativo di eliminare versione non-BOZZA o gia' usata da documenti generati (Tranche F). Trigger DB A2 + service guard |

Codici Fase A `E_DOCUMENTI_*` registrati in `apps.core.services.error_policies`
(5 codici dominio + 2 guard timeline `E_EVENTO_DOCUMENTO_*`).

**Mapping vincoli DB -> messaggio applicativo** (via
`apps.core.services.payload_helpers.map_integrity_error` su frammento
nome vincolo, case-insensitive):

| Vincolo DDL | Frammento match | Messaggio |
|---|---|---|
| `uq_template_documenti_emittente_sorgente_codice` | `uq_template_documenti_emittente_sorgente_codice` | "Esiste gia' un template con questo codice per emittente e sorgente." |
| `uq_template_documenti_emittente_sorgente_codice_interno` | `uq_template_documenti_emittente_sorgente_codice_interno` | "Esiste gia' un template con questo codice interno per emittente e sorgente." |
| `uq_template_documenti_default_attivo` (partial unique) | `uq_template_documenti_default_attivo` | "Esiste gia' un template default attivo per emittente, sorgente e tipo output." |
| FK `tipo_documento_output_id` | `tipo_documento_output_id_fkey` | "tipo_documento_output_id non valido (FK su documenti.tipi_documento_output)." |
| FK `sorgente_tipo_id` | `sorgente_tipo_id_fkey` | "sorgente_tipo_id non valido (FK su config.sorgenti)." |
| FK `emittente_fiscale_id` | `emittente_fiscale_id_fkey` | "emittente_fiscale_id non valido (FK su anagrafiche.emittenti_fiscali)." |

---

## Note di migrazione

- Endpoint nuovi: nessuna retro-compatibilita' richiesta.
- `tipi_documento_output.area_funzionale_id` previsto in §5.1 originale
  non e' atterrato in Fase A (DDL `20260429-52`): la decodifica per area
  passa via `aree_funzionali.schema_db`. Se in futuro servira', sara'
  una micro-tranche DB additiva.
- Set CHECK chiuso v1 di `template_documenti_versioni.stato`:
  `BOZZA`, `PUBBLICATA`, `OBSOLETA` (DDL `20260429-54`). Estensioni
  Fase B via migration successiva.
- Set CHECK chiuso v1 di `documenti_generati_eventi.evento_tipo`:
  `GENERATO`, `SCARICATO`, `STORAGE_ORPHAN` (DDL `20260503-06`).
  L'INSERT lato BE non passa `tx_id` esplicito: lo popola la regola 4
  dell'automation (Decisione 76 — nota implementativa team DB).
- Tranche E (CRUD admin testata template, 2026-05-03): nessuna `DELETE`
  fisica esposta. Il "delete" in UX e' un PATCH `attivo=false` —
  pattern coerente con `catalogo` / `categorie_clienti`. Il record DB
  resta come storia per le versioni gia' pubblicate e per i documenti
  gia' generati.
- `is_default` partial-unique senza demote automatico: scelta esplicita
  per evitare side-effect non visibili al caller. Comportamento
  multi-template default va orchestrato dal FE (disabilita vecchio,
  abilita nuovo) o, in futuro, da un endpoint comando dedicato
  (`POST .../templates/<id>/set-default/`).
- Tranche F (CRUD versioni + comandi clona/pubblica, 2026-05-03):
  `DELETE` versione e' fisica (hard) ma vincolata dal trigger DB A2 a
  versioni `BOZZA` non ancora referenziate da `documenti.documenti_generati`.
  Le versioni `PUBBLICATA`/`OBSOLETA` restano nel DB per audit dei
  documenti generati che le usano (integrita' referenziale storica).
- Pubblicazione con auto-close DB (2026-05-06): il precedente comportamento
  "no auto-close" e' stato sostituito da una funzione DB atomica dedicata,
  per allineare il ciclo versioni template al pattern di sostituzione delle
  versioni listino. Il FE non orchestra piu' la chiusura della versione
  precedente.

---

## Asset documentali (loghi, firme, immagini)

Gli asset sono i file che i template incorporano: logo dell'emittente, firma,
timbro. Vivono per conto loro perche' hanno **validita' temporale** — un logo
cambia, e le ristampe di ieri devono continuare a mostrare quello di ieri.

| | |
|---|---|
| **Lista** | `GET /api/v1/documenti/asset/` — `search`, `attivo`, `asset_tipo_id`, `emittente_fiscale_id`, `utilizzabili`, `limit` (default 25, max 200), `offset`, `order_by` (whitelist `ASSET_ORDER_COLUMNS`, default `codice`; fuori whitelist `400`), `order_dir` (assente: `asc`, le date `desc`). ⚠️ dal 2026-09-27 `page`/`page_size` non sono letti; lo schema OpenAPI li dichiara ancora |
| **Upload** | `POST /api/v1/documenti/asset/` — **multipart**: campo `file` piu' l'anagrafica (`codice`, `codice_interno`, `descrizione`, `asset_tipo_id`, `emittente_fiscale_id`, `valido_dal`…). I metadati si possono passare come campi form singoli **oppure** come JSON nel campo `metadati`: la view accetta entrambe le forme |
| **Dettaglio / aggiorna** | `GET` `PATCH /api/v1/documenti/asset/{asset_id}/` — la `PATCH` tocca i **metadati**, non il binario |
| **Download** | `GET /api/v1/documenti/asset/{asset_id}/file/` — il file originale, come `attachment` |
| **Miniatura** | `GET /api/v1/documenti/asset/{asset_id}/miniatura/` — vedi sotto |

Upload e PATCH chiedono l'azione `documenti_asset_manage`.

### Miniatura di un asset

`GET /api/v1/documenti/asset/{asset_id}/miniatura/`, nessun parametro; livello
d'area `documenti`. Risposta binaria inline: PNG di lato massimo 128 px per le
immagini raster, il file così com'è per un SVG. Header `ETag`
(`"<sha256>-128"`) e `Cache-Control: private, no-cache`: con `If-None-Match`
uguale risponde `304` senza corpo (lo scope si controlla prima dell'ETag).
Errori: `404` `E_DOCUMENTI_NOT_FOUND` (inesistente o fuori scope), `400`
`E_DOCUMENTI_VALIDATION` (l'asset non è un'immagine), `E_DOCUMENTI_RENDER_FAILED`
(immagine illeggibile).

⛔ **Non esiste la DELETE, ed e' un divieto del database**: il trigger A3 blocca
la cancellazione fisica. Per «togliere» un asset si usa `PATCH attivo=false`
oppure `valido_al=<data passata>`.

⭐ E' la stessa logica della ristampa fedele: un asset cancellato davvero
renderebbe **irriproducibile** ogni documento che lo incorporava — la
riproducibilita' si difende impedendo la cancellazione, non sperando che
nessuno la faccia.

La lista e' `is_search_endpoint` (throttling di ricerca). `search`: le colonne le
decide il catalogo della lista `documenti.template_asset`; da un carattere, senza
400 (tabella di configurazione, Tid 2026-09-24). ⛔ Il `codice_interno` non si cerca (dal 2026-09-24).

### Come un template richiama un asset

Nell'HTML o nel CSS di una versione un asset si richiama per **`codice_interno`**,
con lo schema `asset:`:

```html
<img src="asset:LOGO_INTESTAZIONE">
<link rel="stylesheet" href="asset:STILE_BASE">
```

```css
.firma { background: url(asset:FIRMA_AD); }
```

Il `codice_interno` non si modifica (lock automatico del DB), mentre il `codice`
e' un'etichetta che si puo' cambiare: per questo il riferimento sta sul primo.

**Che cosa il render carica**, ed e' una lista chiusa:

| Riferimento | Esito |
|---|---|
| `asset:<codice_interno>` | l'asset **dello stesso emittente del template**. Nella generazione e nell'anteprima deve essere attivo e valido oggi; nella **ristampa fedele** vale anche se oggi e' scaduto o disattivato, perche' e' il file di allora |
| `data:...` | ammesso: il contenuto e' gia' nella stringa |
| `file:`, `http:`, `https:`, ogni altro schema | **rifiutato** |

Gli asset di un altro emittente non si vedono, e non esiste un livello globale
da usare come ripiego.

⭐ **Il filtro `utilizzabili` della lista** (`true` = solo gli asset attivi e
validi oggi, `false` = solo gli altri, assente = tutti) usa **la stessa
condizione** con cui il render risolve `asset:` (`_ASSET_UTILIZZABILE_OGGI` nel
repository). È quello che usa l'editor dei template per proporre gli asset da
richiamare: un asset proposto lì non viene rifiutato alla stampa per scadenza.
È un **filtro**, non un perimetro: la lista di amministrazione degli asset
continua a mostrarli tutti.

Ogni rifiuto **ferma il render** con `E_DOCUMENTI_RENDER_FAILED` e l'URL nel
`detail`: un asset che l'emittente non ha, uno schema non ammesso, anche dentro
un SVG o un CSS importato. Un PDF senza logo e senza errore non esce mai. Un
render carica al massimo 50 risorse: e' il limite che ferma un CSS che importa
se stesso. Se il file sullo storage non corrisponde allo `sha256` registrato, il
render si ferma con `E_DOCUMENTI_STORAGE_FAILED`.

Decisioni e motivi: `work-done/brief-be-documenti-risorse-esterne-render-pdf.md`.

**La pagina la decidono le colonne della versione** (dal 2026-10-04, D-1 strada A e R-BE-V2a di
`brief-db-vocabolari-versione-template`): formato (`page_format`), orientamento
(`page_orientation`) e i quattro margini (`margin_*_mm`). Il render compone una regola
`@page { size: <formato> <orientamento>; margin: <top> <right> <bottom> <left>mm }` e la applica
**sopra** il CSS del template:

* un `@page` scritto nel template (nel CSS o in uno `<style>` dell'HTML) **non** cambia
  formato, orientamento né margini: le colonne vincono sempre. Restano del template le altre
  dichiarazioni dell'`@page`, cioè i box di margine (`@bottom-left` e simili: piè di pagina,
  numeri di pagina);
* un dato di pagina assente o non valido **ferma il render** con `E_DOCUMENTI_RENDER_FAILED`
  e il campo nel `detail`: niente A4 di ripiego;
* vale anche per la **ristampa fedele**, che usa le colonne della versione di allora.

