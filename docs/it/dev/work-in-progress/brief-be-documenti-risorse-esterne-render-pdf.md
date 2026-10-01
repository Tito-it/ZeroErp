# Brief BE — Documenti: che cosa può caricare un template durante il render PDF

> **Destinatari:** backend (`dev/backend-tid`). Una domanda al team DB (§5.3),
> che può cambiare la forma della soluzione ma non la blocca. **Risposta DB
> scritta il 2026-10-01 in §5.3**: `asset:<codice_interno>`. **§4.3 deciso
> da Tid il 2026-10-01**: asset e template solo per emittente, nessun livello
> globale.
>
> **Tipo:** brief di design. Nasce il 2026-09-26 dall'accensione delle regole
> di sicurezza ruff (`S`), che ha trovato il render documentale con
> l'autoescape Jinja spento. **Quel difetto è chiuso** (§1). Questo brief tratta
> quello che resta aperto dopo, e che non è una riga di configurazione.
>
> **Stato:** ✅ **consegnato a codice BE e FE il 2026-10-01** (§7, §8).
> Tutte le decisioni sono prese da Tid lo stesso giorno. ⏳ Resta il
> **collaudo a video** dell'editor (§8.4), poi si archivia in `work-done/`.
>
> **Da leggere per primo: §2 — perché «i template sono fidati» non basta.**

---

## 1. Da dove viene, e che cosa è già chiuso

`documenti.services.render_service` compone il PDF in due passi: Jinja
interpola il context nell'`html_template` della versione, WeasyPrint trasforma
HTML + `css_template` in PDF.

Fino al 2026-09-26 Jinja girava con `autoescape=False`, e il commento diceva
che l'escape dei dati utente toccava ai builder del context. **Nessuno dei
quattro builder lo faceva** (fattura, DDT, ordine, preventivo). Un campo
anagrafica con dentro `<link rel="attachment" href="file:///...">` diventava
HTML vero, e WeasyPrint avrebbe **allegato al PDF un file del server**.

Chiuso con `autoescape=True` e un test che lo presidia
(`test_render_pdf_jinja_escapa_html_nei_valori_del_context`). I dati degli
utenti non possono più iniettare tag.

**Resta aperto l'altro autore dell'HTML: chi scrive il template.**

## 2. Il punto: chi scrive il template, e che cosa può fargli fare WeasyPrint

`_render_with_weasyprint` chiama `HTML(string=...)` e `CSS(string=...)` **senza
`url_fetcher`**. Il fetcher di default di WeasyPrint risolve:

- `http://` e `https://`: il server che genera il PDF fa richieste in uscita
  verso qualunque indirizzo, compresi quelli interni (SSRF);
- `file://`: legge file del filesystem del backend;
- `data:`: contenuto già dentro la stringa, senza nessun accesso.

Chi scrive un template può quindi mettere in un PDF:

- `<link rel="attachment" href="file:///.../.env.systemd">`: il file delle
  variabili d'ambiente (credenziali DB, chiave Fernet) allegato al PDF;
- `<img src="file:///<DOCUMENTI_STORAGE_ROOT>/...">` o un allegato preso dallo
  storage documentale: **documenti di un altro emittente**;
- `url(http://169.254.../...)` nel CSS: una richiesta verso la rete interna.

Il commento storico dice che i template «sono creati da admin via
Configurazione e sono fidati». Questo non regge per due motivi:

1. **I template sono per emittente fiscale** (`template_documenti`: unicità
   `emittente_fiscale + sorgente + codice`). Chi ha `documenti_template_manage`
   su un emittente non è per forza chi amministra il server. In
   un'installazione con più emittenti, il template di A può leggere lo storage
   di B.
2. **Anche l'admin del sistema** non dovrebbe poter leggere il filesystem del
   backend da un'interfaccia web. Il perimetro dell'admin applicativo è il
   database, non la macchina.

⚠️ Non è un difetto da tamponare con un `url_fetcher` che rifiuta tutto.
Chiudere tutto oggi non rompe niente: l'ho verificato, nessun template seedato
usa `src=`, `href=` o `url(`. Però chiuderebbe anche la strada per cui gli
**asset** esistono.

## 3. Gli asset: il pezzo che manca

`documenti.template_asset` esiste già (Tranche G). È caricabile con upload e
whitelist MIME per tipo (`LOGO`, `FIRMA`, `IMMAGINE`, `PDF`, `CSS`), va nello
storage con `storage_key` e sha256, è immutabile (Decisione 66) e non si
cancella.

**Nel render però nessuno li collega.** `render_service` non li risolve, e il
commento su `_render_with_weasyprint` dice solo che «il template dovrebbe usare
URL assolute per risorse esterne (asset documentali via storage_uri
risolvibile)». Oggi quindi un template non ha un modo previsto per mostrare il
logo dell'emittente. L'unica strada che funziona è quella da chiudere: l'URL
esterna o il `file://`.

La decisione sul fetcher e quella su come un template richiama un asset sono
**la stessa decisione**. Per questo stanno in un brief solo.

## 4. Decisioni da prendere

### 4.1 Come un template richiama un asset — ✅ deciso

**Approvato da Tid il 2026-10-01**, con la sintassi data dal DB in §5.3:
`asset:<codice_interno>`. Proposta originale: uno **schema dedicato** risolto dal nostro `url_fetcher`, per
esempio `asset:LOGO` o `asset:<codice>`. Il fetcher lo traduce nella lettura
dallo storage, **dentro il perimetro dell'emittente del template**.

Alternative considerate:
- *Il builder mette l'asset nel context come `data:` URI.* Funziona, ma il
  context deve sapere quali asset servono a ogni template (accoppiamento), e
  un PDF con dieci immagini gonfia la stringa HTML.
- *URL HTTP del backend (`/api/.../asset/<id>`).* Il render farebbe una
  richiesta HTTP a sé stesso, con autenticazione da inventare. È la strada
  più fragile.

### 4.2 Che cosa il fetcher ammette — ✅ deciso

**Approvato da Tid il 2026-10-01.** Con una precisazione per la ristampa
fedele, decisa lo stesso giorno (§4.6). Lista chiusa:
- `asset:<codice_interno>` → storage, solo asset **attivi e validi**
  (`validita @> current_date`) con lo **stesso** `emittente_fiscale_id` del
  template (§4.3);
- `data:` → ammesso, perché non accede a niente;
- **tutto il resto rifiutato**: `file:`, `http(s):`, schemi ignoti.

⚠️ Il rifiuto deve essere un errore parlante (`E_DOCUMENTI_RENDER_FAILED` con
l'URL rifiutata nel `detail`), non un'immagine mancante in silenzio.
WeasyPrint, se il fetcher fallisce, di default logga e va avanti: il PDF esce
senza logo e nessuno sa perché. È lo stesso tipo di difetto che non dà errore.

### 4.3 Asset di sistema e asset dell'emittente — ✅ deciso

**Deciso da Tid il 2026-10-01: solo per emittente.** Il modello non ha un
livello globale, né per gli asset né per i template (`emittente_fiscale_id`
`NOT NULL` su entrambi, §5.3), e per ora non se ne aggiunge uno. Non c'è
quindi nessuna regola di risoluzione e nessun ripiego. Un template vede
soltanto gli asset del suo emittente. Se il template chiede un `asset:` che
non esiste, il fetcher alza l'errore parlante di §4.2: un logo generico al
suo posto sarebbe un PDF sbagliato senza nessun errore.

Un livello globale dei template (per esempio un'impaginazione di base per un
emittente nuovo) resta fuori da questo brief. Se tornerà a servire, sarà una
domanda di modello con un brief DB apposito.

### 4.4 Il CSS — ✅ deciso

`css_template` e gli asset di tipo `CSS` passano dallo stesso fetcher (`url()`,
`@import`), quindi sono coperti da §4.2. Restava da decidere se un asset `CSS`
può fare `@import` di un altro asset. È ricorsione: il fetcher la gestisce, ma
serve un limite.

**Deciso da Tid il 2026-10-01: un tetto di risorse per render.** L'`@import`
resta ammesso; oltre 50 risorse caricate in un render, il render si ferma con
`E_DOCUMENTI_RENDER_FAILED`. Perché un tetto e non un limite di profondità:
WeasyPrint 70 non ha nessuna guardia sui cicli (un CSS che importa se stesso
ricorre senza fine), e il fetcher vede le singole URL, non la catena degli
import. Il tetto copre in un colpo solo cicli, import annidati e SVG che
richiamano altre risorse. Le immagini WeasyPrint le tiene in cache per URL:
lo stesso logo su ogni pagina conta una volta.

**Precisato da Tid il 2026-10-01: il tetto conta solo gli `asset:`.** Un
`data:` porta il suo contenuto scritto nell'URL: non può richiamare se stesso,
e ogni catena che si allunga passa per forza da un `asset:`. Contarlo fermava
un template con molte icone inline senza nessun ciclo (test 24 di
`test_render_service`).

### 4.5 SVG

`image/svg+xml` è ammesso per `LOGO`, `FIRMA` e `IMMAGINE`. Un SVG può a sua
volta referenziare risorse esterne (`<image href="...">`). WeasyPrint le
risolve con lo stesso fetcher, quindi §4.2 le copre. Va comunque scritto un
test con un SVG che punta a `file://`.

⚠️ **Il test l'ha smentito a metà** (2026-10-01, §7.2): il fetcher rifiuta,
ma WeasyPrint **inghiotte** il rifiuto dentro un SVG e il PDF esce lo stesso,
con l'immagine monca e nessun errore.

### 4.6 La ristampa fedele — ✅ deciso

Punto emerso leggendo il codice, non previsto dal brief. La ristampa
(`ristampa_fedele`) rilegge la versione **di allora** con il contesto **di
allora**. Con la regola di §4.2 «solo attivi e validi», un documento il cui
logo oggi è scaduto o disattivato non si ristamperebbe più.

**Deciso da Tid il 2026-10-01: la ristampa ignora la validità.** Generazione
e anteprima vedono solo gli asset attivi e validi oggi; la ristampa vede
l'asset dell'emittente del documento con quel `codice_interno`, qualunque sia
il suo stato. Regge sul modello: l'asset è immutabile nelle colonne del file
(guard A4), non si cancella (A3), e `(emittente, codice_interno)` è unico.
Lo stesso `codice_interno` indica quindi sempre gli stessi byte, cioè il file
di allora.

## 5. Ricadute

### 5.1 Backend
- `url_fetcher` in `render_service`: BB unico, testato caso per caso (`asset:`
  valido, fuori perimetro, non attivo, `data:`, `file:`, `http:`, SVG annidato,
  CSS `@import`).
- Risoluzione `asset:` → lettura storage con il BB `percorso_allegato`, che già
  impedisce di uscire dalla radice. ⚠️ **Correzione (2026-10-01):** il
  brief sbagliava BB. `percorso_allegato` serve gli allegati **email**
  (`core/services/email_allegati_storage.py`). Lo storage documentale ha il
  suo guard: `DocumentStorage.build_storage_uri` + `read`, con
  `_normalize_key`/`_resolve_path` contro il path traversal. È quello che usa
  già `download_asset`, ed è quello usato.
- Il context del render deve portare l'emittente del template, per il
  perimetro.

### 5.2 Frontend — ✅ consegnato (§8)
- L'editor dei template dovrebbe mostrare come si richiama un asset (elenco
  dei codici disponibili). È fuori da questo brief: si decide dopo §4.1.
  Deciso e fatto il 2026-10-01: vedi §8.

### 5.3 Domanda al team DB
- Il `codice` dell'asset è unico per emittente e quindi può reggere
  `asset:<codice>`, oppure serve un `codice_interno` immutabile, come per i
  template? Se l'asset si rinomina, i template che lo citano si rompono. La
  risposta decide la sintassi di §4.1.

**Risposta DB (2026-10-01, verificata sui changeSet, non sul DB vivo):**

- **Il `codice_interno` c'è già, e non serve nessun lavoro DB.**
  `documenti.template_asset` (changeSet `20260429-55`) ha `codice_interno
  varchar(120) NOT NULL`, unico per emittente
  (`uq_template_asset_emittente_codice_interno`) e non vuoto. È immutabile
  grazie al lock automatico (linee-guida-sql §6b/§6c): la regola
  `LOCK_COLUMNS` di `dbops.automation_rules_tbl` vale per tutte le tabelle
  (`*all`), lo schema `documenti` è in `dbops.automation_scope`, e la sola
  presenza della colonna fa nascere il lock. Una modifica dà
  `E_CODICE_NON_MODIFICABILE`.
- **Il `codice` invece si può modificare.** È unico per emittente, ma non
  c'è nessun lock: il guard A4 (`trgfn_template_asset_protect_file`) blocca
  solo le colonne del file (`storage_key`, `sha256`, `file_size_bytes`,
  `mime_type`, `file_name`). È un'etichetta da mostrare (§6c).
- **Quindi la sintassi è `asset:<codice_interno>`.** Lo dice la regola d'oro
  di §6c: la logica si aggancia solo a `codice_interno`. La chiave del fetcher
  è `(emittente del template, codice_interno)`, e corrisponde esattamente al
  vincolo unico.

⚠️ **Una premessa di §4.2 e §4.3 non regge sul modello: gli asset di sistema
non esistono.** In `template_asset` la colonna `emittente_fiscale_id` è `NOT
NULL`, e lo è anche in `template_documenti` (changeSet `20260429-53`).
Inoltre il trigger `a10_default_emittente_ins` (changeSet `20260915-45`,
modo `SOLLEVA`) solleva `E_EMITTENTE_NON_RISOLTO` invece di lasciare NULL.
Non c'è quindi né un «template di sistema» né un «asset di sistema», e in
`template_documenti.md` non esiste la sezione «risoluzione» a cui rimanda
§4.3. Per il BE, oggi:

- in §4.2 il perimetro è uno solo: gli asset con lo **stesso**
  `emittente_fiscale_id` del template. La parentesi su `emittente` NULL va
  tolta;
- §4.3 non era una regola di risoluzione da scegliere, ma una **domanda di
  modello**. Tid l'ha chiusa il 2026-10-01: solo per emittente (vedi §4.3).

Nota per §4.2 («attivi e validi»): la validità si legge da `validita @>
current_date`, colonna `GENERATED ALWAYS … STORED` (changeSet `20260514-27`).
Va letta così, senza ricalcolarla da `valido_dal`/`valido_al`.

## 6. Fuori perimetro

- L'autoescape Jinja: chiuso (§1).
- Il motore di render alternativo: `_ENGINE_WHITELIST` resta `WEASYPRINT`.
- La sanitizzazione dell'HTML del template in fase di salvataggio. Il fetcher
  chiude l'accesso alle risorse, che è il rischio concreto. Filtrare i tag al
  salvataggio sarebbe un secondo cancello, da valutare solo se emerge un caso
  che il fetcher non copre.

## 7. Consegna BE — 2026-10-01

### 7.1 Che cosa è stato fatto

| Pezzo | Dove |
| --- | --- |
| Fetcher a lista chiusa (`asset:`, `data:`), tetto di 50 risorse, `fail_on_errors=True`, registro del primo rifiuto | `documenti/services/render_service.py` — `_crea_fetcher`, `_render_with_weasyprint`, `_solleva_rifiuto` |
| `render_pdf(..., risolvi_asset)` **obbligatorio**: ogni chiamante dichiara il perimetro, e il modulo resta senza DB | `render_service.RisolviAsset` |
| Risolutore per render: `(emittente, codice_interno)` → storage, cache per render, confronto con lo `sha256` della riga | `DocumentGenerationService._risolutore_asset` |
| Perimetro: genera e anteprima → emittente del template, `solo_validi=True`; ristampa → emittente del documento, `solo_validi=False` (§4.6) | i tre punti di render in `document_generation_service.py` |
| Query: `validita @> CURRENT_DATE` dalla colonna generata, chiave del vincolo unico | `DocumentiRepository.get_asset_per_render` |
| Doc: come un template richiama un asset | `backend/documenti/manual/api_documenti_templates.md` § «Come un template richiama un asset» |
| Catalogo BB | voce `render_service.render_pdf` |

Nessun lavoro DB, nessun codice errore nuovo: si usano
`E_DOCUMENTI_RENDER_FAILED` e `E_DOCUMENTI_STORAGE_FAILED`, già registrati.

### 7.2 Che cosa ha mostrato la libreria vera (WeasyPrint 70.0)

Tre cose che il brief non poteva sapere, e che un test con WeasyPrint finto
non avrebbe visto:

1. **`FatalURLFetchingError` deriva da `BaseException`.** È ciò che
   `fail_on_errors=True` solleva. L'`except Exception` che c'era non lo
   cattura: senza un `except` dedicato il rifiuto usciva come errore senza
   codice applicativo.
2. **WeasyPrint inghiotte il rifiuto in almeno un punto anche con
   `fail_on_errors`.** `SVGImage.draw` cattura `BaseException` e logga. Il
   file non viene letto (la sicurezza regge), ma il PDF esce con l'SVG monco
   e nessun errore: il difetto che §4.2 voleva evitare. Chiuso in modo
   generale: il fetcher registra il primo rifiuto e il render lo rilegge
   **anche dopo un `write_pdf` riuscito**. Così vale per qualunque punto
   della libreria che inghiotte, non solo per l'SVG.
3. **Nessuna guardia sui cicli di `@import`** (§4.4).

### 7.3 Il file sullo storage e la fedeltà

La riga dell'asset è immutabile a DB, il file sul disco no. Il risolutore
confronta lo `sha256` dei byte letti con quello registrato, e se divergono
ferma il render con `E_DOCUMENTI_STORAGE_FAILED`. È quello che rende vera la
premessa di §4.6 («stesso `codice_interno`, stessi byte»). Il `template_hash`
del documento non copre i byte degli asset, e non serve che li copra: il
riferimento per `codice_interno` li inchioda.

### 7.4 Test

- `tests/services/test_render_service.py` (13 → 24): i test esistenti
  dichiarano il risolutore; due test con WeasyPrint finto (rifiuto
  inghiottito, `ServiceError` del risolutore conservato); **un test per ramo
  sulla libreria vera** (`asset:` ammesso e letto una volta, `data:`, asset
  assente, `<img>` `file:`, `<link rel=attachment>` `file:`, `http:` verso
  169.254…, `url(file:)` nel CSS, `@import` ciclico, SVG annidato con
  `file:`). Senza Pango la classe si salta **dichiarandolo** (`skipUnless`
  col motivo). ⚠️ `ci-validate.yaml` gira su `ubuntu-latest` e **non
  installa Pango** esplicitamente: i nove test girano in CI solo se
  l'immagine del runner lo porta già, altrimenti risultano saltati col
  motivo. **Da verificare sul log della prima CI**. Se risultano saltati,
  si aggiunge Pango all'`apt-get` del job: è una decisione di Tid, perché
  tocca il workflow.
- `tests/services/test_risolutore_asset.py` (nuovo, 6): perimetro, cache per
  render (non condivisa fra render), asset assente, impronta diversa.
- Perimetro dei tre percorsi: asserzioni aggiunte negli happy path di
  genera, anteprima e ristampa.
- `tests/db/test_asset_per_render_db.py` (nuovo, 3, su DB provvisto): chiave
  `(emittente, codice_interno)` (non `codice`, non un altro emittente),
  asset disattivato e asset scaduto **fabbricati** sulla riga, visti solo
  dalla ristampa.

Esito il 2026-10-01: `apps.documenti` 299 test OK; DB provvisto
(`ZEROERP_TEST_DB_E2E=1`) 11 OK; suite backend 5948 OK; ruff pulito.

### 7.5 Che cosa resta

- **§5.2 (FE)**: consegnato lo stesso giorno, §8.
- Nessun template seedato usa `src=`, `href=` o `url(` (verificato il
  2026-09-26, fatto datato): la chiusura non rompe nessuna stampa esistente.
  Non è il motivo della scelta, che regge sul modello (§2).

## 8. Consegna §5.2 — l'editor mostra gli asset (2026-10-01)

### 8.1 Decisioni di Tid (2026-10-01)

| # | Domanda | Decisione |
| --- | --- | --- |
| 1 | Quali asset mostrare | **Solo quelli che il render accetta oggi**, con un parametro del backend che applica la **stessa** regola del render. Scartata la strada «tutti, coi non validi spenti»: sarebbe stata la seconda copia della regola, nel frontend |
| 2 | Inserire o copiare | **Inserire al cursore** nella textarea giusta (HTML o CSS) |
| 3 | Sola lettura | Pannello **visibile per consultare**, inserimento spento |

### 8.2 Backend

- `GET /api/v1/documenti/asset/?utilizzabili=true|false`: **filtro**, non
  perimetro (api.md §«Un PERIMETRO non è un filtro»). La lista di
  amministrazione degli asset continua a mostrarli tutti, e l'assenza del
  parametro vuol dire «nessun filtro». View strict (`qp_bool_optional`:
  `?utilizzabili=banana` è un 400).
- ⭐ **Una condizione sola**: `_ASSET_UTILIZZABILE_OGGI` in
  `documenti_repository`, letta da `get_asset_per_render` (il render) **e** da
  `list_asset` (il filtro). È la regola del 2 applicata prima che la seconda
  copia nascesse. Se le due letture divergessero, l'editor proporrebbe un
  asset che la stampa rifiuta.
- Test: unitario sulla condizione
  (`test_list_asset_utilizzabili_usa_la_condizione_del_render`) e,
  soprattutto, **concordanza sul DB vero**: nei tre casi fabbricati di
  `test_asset_per_render_db` (valido, disattivato, scaduto) la lista con
  `utilizzabili` vede l'asset esattamente quando lo vede il render.

### 8.3 Frontend

- `config/components/TemplateAssetRiferimenti.vue`, montato nel form della
  versione (`TemplateVersioniSection`) sotto l'editor CSS. Per ogni asset:
  miniatura (solo immagini), `asset:<codice_interno>`, descrizione e MIME,
  e i pulsanti «In HTML» / «In CSS».
- **La forma del riferimento la decide il `mime_type`** (immutabile a DB), non
  il tipo di asset: `image/*` → `<img src>` / `url()`, `text/css` →
  `<link rel=stylesheet>` / `@import`, `application/pdf` → `<link
  rel=attachment>` (nessun pulsante CSS).
- L'inserimento sostituisce la selezione, o va al cursore, e rimette il
  cursore dopo il testo inserito (`inserisciRiferimento` nell'editor, che
  possiede le textarea).
- Sola lettura: il drawer è `app-readonly`, i pulsanti non si mostrano, il
  codice resta selezionabile.
- Oltre i 200 asset (il `MAX_LIMIT` del backend) il riquadro **lo dice**
  invece di troncare in silenzio. Si rilegge quando un'altra scheda modifica
  un asset (`useTabEvents`).
- Non ha voce nel catalogo BB FE: un solo consumatore (regola del 2).
- **Miniature (2026-10-01, Tid: «facciamo direttamente l'endpoint»).** Prima
  il riquadro scaricava il file **intero** di ogni immagine, una alla volta, a
  ogni apertura. Ora chiede `GET /api/v1/documenti/asset/<id>/miniatura/`
  (`ApiAssetMiniatura` → `TemplateService.miniatura_asset`), tutte insieme:
  - raster → PNG di lato al massimo `LATO_MINIATURA` = 128 px, proporzioni e
    trasparenza conservate, orientamento EXIF applicato, primo fotogramma di
    una GIF; SVG → il file com'è (vettoriale, Pillow non lo legge);
  - un asset non immagine → 400 `E_DOCUMENTI_VALIDATION`; un file illeggibile
    → `E_DOCUMENTI_RENDER_FAILED` con `asset_id`;
  - `ETag` = impronta del file + lato, `Cache-Control: private, no-cache`: il
    browser la tiene e la **rivalida** (304, senza leggere il file né
    ridimensionarlo). ⚠️ `no-cache` e non `max-age`: la cache del browser non
    distingue l'utente, e lo scope va ricontrollato a ogni richiesta — il
    service lo controlla **prima** dell'ETag;
  - Pillow dichiarata in `requirements.in` (ok Tid): era già installata come
    dipendenza di WeasyPrint, il lock cambia solo nel «via».
- Test: `TemplateAssetRiferimenti.spec.js` (8): cosa chiede al backend,
  `codice_interno` e non `codice`, la forma per MIME, sola lettura,
  troncamento, miniatura e mai file intero. Backend:
  `test_miniatura_asset` (8, Pillow vero) e `test_documenti_api` 22-bis/ter
  (200 inline con ETag, 304).

Esito il 2026-10-01: `apps.documenti` 305 OK, DB provvisto 11 OK; vitest
66 file / 521 test OK; `npm run guards`, `check_i18n_keys.py`, eslint e
build puliti.

### 8.4 Collaudo a video (da fare)

L'inserimento al cursore non ha un test automatico: monta
`TemplateVersioniSection` intero, con store e drawer, ed è più onesto
guardarlo. Configurazione › Documenti › un modello → una versione in BOZZA:

1. il riquadro «Asset richiamabili» mostra solo asset attivi e validi
   dell'emittente del modello (prova: disattivane uno nella scheda «Asset
   documentali», torna al modello, sparisce);
2. cursore a metà dell'HTML, «In HTML» su un logo: il testo entra lì, non in
   coda, e il cursore resta dopo;
3. «In CSS» va nella textarea del CSS;
4. versione PUBBLICATA o utente in sola lettura: niente pulsanti, codice
   selezionabile;
5. salva, genera l'anteprima del documento: il logo compare. Con un
   `asset:REFUSO` scritto a mano l'anteprima risponde
   `E_DOCUMENTI_RENDER_FAILED` con `asset:REFUSO` nel dettaglio.

