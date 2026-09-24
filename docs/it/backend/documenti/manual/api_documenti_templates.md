# API documenti — Templates e versioni (Django)

## Scopo

Esporre via HTTP il motore documentale parametrico per operatori e
responsabili: lista/dettaglio template, lista/dettaglio versioni, e
mutazioni sulla testata template (create + update).

## Contesto

Endpoint v1 del refactor `sviluppo-documenti.md` (Decisioni 25/30/72-76).
Gli endpoint di lettura interrogano direttamente le tabelle
`documenti.template_documenti` e `documenti.template_documenti_versioni`
con LEFT/INNER JOIN sui lookup (`documenti.tipi_documento_output`,
`config.sorgenti`, `anagrafiche.emittenti_fiscali`,
`documenti.render_engine_documento`). I comandi admin di scrittura passano
dal service applicativo; la pubblicazione di una versione delega al DB la
chiusura atomica della versione pubblicata precedente tramite
`documenti.fn_pubblica_template_documento_versione(...)`.

Gli endpoint template/versioni hanno `area_funzionale = "documenti"`
(id area=11, schema_db=`documenti`). Il livello area si applica con la
catena standard TUTTO/LETTURA/BLOCCATO; lo scope dati e' applicato in
repository tramite `PermissionResolver.get_emittenti_pk_ids` (whitelist
`emittenti_fiscali.id`): admin globale e superuser vedono tutto,
operatori vedono solo i template dei propri emittenti. Le mutazioni admin
usano `post_permission = "documenti_template_manage"` (Decisione 75).

Gli endpoint di generazione/anteprima/download dei documenti generati sono
documentati nelle API delle sorgenti funzionali che li espongono
(es. contratti e preventivi).

---

## Endpoint

### 1. Lista template

#### Input

- Metodo: `GET`
- Path canonico: `/api/v1/documenti/templates/`
- Header sicurezza: `Authorization: Bearer <access_token>`
- `is_search_endpoint = True` -> attiva `SearchBurstRateThrottle`
- Query param (tutti opzionali; assente o vuoto = nessun filtro):
  - `search` (string, min 3 char) — ILIKE su `codice`, `codice_interno`, `descrizione`
  - `attivo` (bool) — `true`/`false` per filtrare solo attivi/disattivati
  - `tipo_documento_output_id` (int)
  - `sorgente_tipo_id` (int)
  - `emittente_fiscale_id` (int) — ulteriore filtro dentro lo scope operatore
  - `page` (int) — default `1`
  - `page_size` (int) — default `50`, max `200`
  - `order_by` (string) — whitelist: `codice`, `codice_interno`, `descrizione`, `data_insert`, `data_update` (default `codice`)
  - `order_dir` (string) — `asc` o `desc` (default `asc`)

#### Output

- `200`:

```json
{
  "data": {
    "count": 1,
    "page": 1,
    "page_size": 50,
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

- `400`: parametri non validi (`search` < 3 char con `E_API_VALIDATION`; query param int malformato)
- `401`: JWT mancante o non valido
- `403`: livello area `documenti` = BLOCCATO

### 2. Dettaglio template

#### Input

- Metodo: `GET`
- Path: `/api/v1/documenti/templates/<int:template_id>/`
- Header sicurezza: `Authorization: Bearer <access_token>`

#### Output

- `200`: stessi campi della lista + `meta` (jsonb), `storicizza`,
  `user_insert`, `user_update`.
- `404`: template inesistente o fuori scope emittente — codice
  `E_DOCUMENTI_NOT_FOUND`. La risposta non distingue i due casi (no leak
  di esistenza fuori scope).

### 3. Lista versioni di un template

#### Input

- Metodo: `GET`
- Path: `/api/v1/documenti/templates/<int:template_id>/versioni/`
- Query param (opzionali):
  - `attivo` (bool) — default `true`
  - `stato` (string) — whitelist: `BOZZA`, `PUBBLICATA`, `OBSOLETA` (case-insensitive)

#### Output

- `200`:

```json
{
  "data": {
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
        "attivo": true,
        "data_insert": "2026-04-29T00:00:00+02:00",
        "data_update": "2026-04-29T00:00:00+02:00"
      }
    ]
  },
  "meta": { "request_id": "..." }
}
```

- `400`: `stato` non in whitelist — codice `E_DOCUMENTI_VALIDATION`
- `404`: template inesistente o fuori scope — codice `E_DOCUMENTI_NOT_FOUND`

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
  - `context_builder_code`* (string non vuota, max 160 char — formato libero in v1, check whitelist registry rinviato a Tranche H)
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
- `404` `E_DOCUMENTI_NOT_FOUND`: template inesistente o fuori scope
  emittente. La risposta non distingue i due casi (no leak di esistenza).

### 7. Crea versione BOZZA (Tranche F)

#### Input

- Metodo: `POST`
- Path: `/api/v1/documenti/templates/<int:template_id>/versioni/`
- Permesso azione: `documenti_template_manage` (`post_permission`)
- Body JSON (campi obbligatori marcati con `*`):
  - `titolo`* (string non vuota, max 500)
  - `html_template`* (string non vuota — payload HTML del template)
  - `render_engine_id`* (int positivo, FK su `documenti.render_engine_documento`)
  - `formato_template` (string in `{HTML, HTML_MARKDOWN_BLOCKS}`, default `HTML`)
  - `css_template` (string nullable)
  - `markdown_template` (string nullable)
  - `page_format` (string in `{A4, A3, LETTER}`, default `A4`)
  - `page_orientation` (string in `{PORTRAIT, LANDSCAPE}`, default `PORTRAIT`)
  - `margin_top_mm` / `margin_right_mm` / `margin_bottom_mm` / `margin_left_mm` (number >= 0, default 10; sono accettate anche stringhe numeriche come `"15.00"`, normalizzate dal service)
  - `valido_dal` (date ISO, nullable in BOZZA — diventa obbligatorio in pubblicazione)
  - `valido_al` (date ISO, nullable)
  - `context_schema` (jsonb object, default `{}`)
  - `meta` (jsonb object, default `{}`)
  - `attivo` (bool, default `true`)

#### Output

- `200`: dettaglio della versione creata (stesso shape di "Dettaglio versione").
  - `versione`: numero calcolato come `MAX(versione)+1` per il template.
  - `stato`: sempre `BOZZA` su create.
- `400` `E_DOCUMENTI_VALIDATION`: chiave non whitelisted, campo richiesto
  mancante, formato/page_format/orientation fuori whitelist, margine
  negativo, race su `uq_template_documenti_versioni_template_versione`
  (riprovare).
- `404` `E_DOCUMENTI_NOT_FOUND`: template inesistente o fuori scope.

### 8. Aggiorna versione BOZZA (Tranche F)

#### Input

- Metodo: `PATCH`
- Path: `/api/v1/documenti/templates/<int:template_id>/versioni/<int:versione_id>/`
- Permesso azione: `documenti_template_manage` (`patch_permission`)
- Body JSON (tutti opzionali; almeno uno obbligatorio): stesse chiavi della
  create, esclusi i campi calcolati `template_documento_id`, `versione`,
  `stato`. La transizione di stato passa solo dall'endpoint dedicato
  `pubblica/`.

#### Output

- `200`: dettaglio della versione aggiornata.
- `400` `E_DOCUMENTI_VALIDATION`: chiave extra, payload vuoto post-validation,
  formato/orientation fuori whitelist, margine negativo o non numerico,
  `attivo`/`is_default` esplicito a `null`. I margini provenienti dal DB come
  stringhe decimali (`"15.00"`) sono validi e vengono convertiti prima del write.
- `404` `E_DOCUMENTI_NOT_FOUND`: template/versione inesistente o fuori scope.
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
    `page_orientation`, `margin_*`, `context_schema`. (`meta` se non
    overrideato.)
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

---

## Regole

- **Scope operatore**: tutti gli endpoint applicano lo scope emittente
  via `PermissionResolver.get_emittenti_pk_ids(user)`. Operatore con
  emittenti assegnati vede solo i template dei propri emittenti; admin
  globale/superuser vedono tutto. Utente non autenticato (corner case:
  bypass auth) riceve lista vuota: `is_authenticated=False` -> scope = `[]`.
- **Lookup vs scope**: il filtro query `emittente_fiscale_id` si applica
  *dentro* lo scope. Un operatore che chiede `?emittente_fiscale_id=999`
  fuori dal proprio scope ottiene comunque lista vuota (no
  `forbidden`/`leak`).
- **Search ricerca testuale**: minimo 3 caratteri (regola
  `require_min_search_length`). Search vuota o `< 3` -> `400`
  `E_API_VALIDATION`.
- **Paginazione**: `page>=1`, `page_size` in `[1, 200]`. Ordinamento
  `id ASC` come tiebreaker garantisce paginazione deterministica anche
  con duplicati sulla colonna di sort.
- **Whitelist ORDER BY**: solo le 5 colonne mappate nel repository
  (`codice`, `codice_interno`, `descrizione`, `data_insert`, `data_update`)
  sono ammesse. Valori fuori whitelist -> `400 E_DOCUMENTI_VALIDATION`
  con elenco delle colonne ammesse (defense-in-depth lato repository,
  fail prima del round-trip DB).
- **Validazione `stato` versione**: il caller passa lowercase o uppercase;
  il service normalizza a UPPER e confronta con `{BOZZA,PUBBLICATA,OBSOLETA}`.
  Set chiuso allineato al CHECK DB.
- **Defense-in-depth versione**: `get_versione` in repository binda
  `template_documento_id`; la view passa il template_id dal path. Un id
  versione di un template diverso non e' mai esposto via path di un
  altro template.
- **Endpoint read-only** (1-4): nessun `Idempotency-Key` richiesto.
- **Endpoint write** (5-11): nessun `Idempotency-Key` richiesto in v1
  (allineato al pattern `categorie_clienti`); valutabile in PR successive
  se il pattern di replay diventa critico per UX.
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
  `is_default=true` su create/update mentre esiste gia' un altro template
  default attivo per `(tipo_documento_output_id, sorgente_tipo_id,
  emittente_fiscale_id)` ritorna `400 E_DOCUMENTI_VALIDATION`. Il FE
  deve disabilitare il vecchio default (`PATCH is_default=false`) prima
  di settare il nuovo. Decisione di design: nessuna magia in transazione
  2-step lato BE.
- **`context_builder_code` validation v1**: solo formato (string non
  vuota). Il check whitelist contro
  `apps.documenti.services.context_builders.registry` arriva con il
  render service (Tranche H). In v1 e' lecito creare un template che
  punta a un builder ancora non registrato; la validazione esplode al
  momento della generazione.
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
- **JWT obbligatorio** su tutti i 6 endpoint.

---

## Dipendenze DB

- `documenti.template_documenti` — testata template
- `documenti.template_documenti_versioni` — versioni (HTML/CSS/markdown)
- `documenti.tipi_documento_output` (INNER JOIN decodifica)
- `documenti.render_engine_documento` (INNER JOIN decodifica)
- `config.sorgenti` (INNER JOIN decodifica)
- `anagrafiche.emittenti_fiscali` (INNER JOIN decodifica + scope)
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
- **Asset upload** (Tranche G, in arrivo): `post_permission = "documenti_asset_manage"`.
- **Generazione/lista/download PDF** (Tranche J, in arrivo): permessi del
  dominio sorgente (es. `vendite` per preventivi).

Vedi Decisione 75 in `sviluppo-documenti.md` §10.

---

## Codici errore

| Codice | HTTP | Quando |
|---|---|---|
| `E_DOCUMENTI_VALIDATION` | 400 | `stato` versione fuori whitelist; `template_id`/`versione_id` non interi positivi; in write: chiave non whitelisted, campo richiesto mancante, campo immutabile, `emittente_fiscale_id` fuori scope, margini non numerici/negativi, violazioni unique/partial-unique/FK del DDL; pubblicazione: `valido_dal` mancante, stato non BOZZA |
| `E_DATA_AL_MINORE_DAL` | 400 | `valido_al < valido_dal` in create/clone/update/pubblicazione di una versione e in upload/PATCH di un asset: guard comune `script.trgfn_guard_date_validita`, campo `valido_al`. Il service non lo anticipa (dal 2026-09-23) |
| `E_DOCUMENTI_VERSIONE_OVERLAP` | 409 | pubblicazione con overlap residuo verso un'altra versione `PUBBLICATA` attiva che l'auto-close non risolve (EXCLUDE `ex_template_documenti_versioni_no_overlap_pubblicata`) |
| `E_DOCUMENTI_NOT_FOUND` | 404 | template/versione inesistente o fuori scope emittente (no leak) |
| `E_DOCUMENTI_VERSIONE_PUBBLICATA_IMMUTABILE` | 409 | tentativo di modificare versione `PUBBLICATA` (Tranche F). Trigger DB A1 + service guard |
| `E_DOCUMENTI_VERSIONE_DELETE_BLOCKED` | 409 | tentativo di eliminare versione non-BOZZA o gia' usata da documenti generati (Tranche F). Trigger DB A2 + service guard |
| `E_API_VALIDATION` | 400 | search < 3 char (helper core) |

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
| **Lista** | `GET /api/v1/documenti/asset/` — `search`, `attivo`, `asset_tipo_id`, `emittente_fiscale_id`, `page`, `page_size`, `order_by`, `order_dir` |
| **Upload** | `POST /api/v1/documenti/asset/` — **multipart**: campo `file` piu' l'anagrafica (`codice`, `codice_interno`, `descrizione`, `asset_tipo_id`, `emittente_fiscale_id`, `valido_dal`…). I metadati si possono passare come campi form singoli **oppure** come JSON nel campo `metadati`: la view accetta entrambe le forme |
| **Dettaglio / aggiorna** | `GET` `PATCH /api/v1/documenti/asset/{asset_id}/` — la `PATCH` tocca i **metadati**, non il binario |
| **Download** | `GET /api/v1/documenti/asset/{asset_id}/file/` — il file originale, come `attachment` |

⛔ **Non esiste la DELETE, ed e' un divieto del database**: il trigger A3 blocca
la cancellazione fisica. Per «togliere» un asset si usa `PATCH attivo=false`
oppure `valido_al=<data passata>`.

⭐ E' la stessa logica della ristampa fedele: un asset cancellato davvero
renderebbe **irriproducibile** ogni documento che lo incorporava — la
riproducibilita' si difende impedendo la cancellazione, non sperando che
nessuno la faccia.

La lista e' `is_search_endpoint` (throttling di ricerca).

