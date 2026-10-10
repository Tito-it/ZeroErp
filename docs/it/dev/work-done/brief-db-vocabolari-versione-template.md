# Brief DB — I valori ammessi di una versione di template: da CHECK a vocabolario

> **Chi scrive:** sessione BE/FE (`dev/backend-tid`), 2026-10-03. **A chi:** team DB
> (`dev/db-tid`); poi BE/FE (§4).
> **Origine:** revisione del drawer dei modelli di documento (richiesta di Tid, 2026-10-03), che ha
> portato la versione in un drawer suo (`TemplateVersioneDrawer`).
> **Stato:** ✅ **BRIEF CHIUSO il 2026-10-04.** DB applicato il 2026-10-04 (`20261004-20…-22`, §5);
> BE/FE fatto lo stesso giorno (§6): R-FE-V1, R-BE-V1, R-FE-V2, R-BE-V2…V2b. R-BE-V2a deciso da Tid:
> **vincono le colonne**. Resta fuori, dichiarato: `HTML_MARKDOWN_BLOCKS` (§5.6), passato in
> PROJECT_CONTEXT § «Aperto — Media priorità», con la ricaduta sui margini delle versioni
> pubblicate (§6.3).
> **Da leggere per primo:** §5, poi §5.6 e §6.

## 1. Il problema

Tre colonne di `documenti.template_documenti_versioni` hanno un insieme chiuso di valori, scritto
**solo** come CHECK:

| Colonna | CHECK | Valori |
| --- | --- | --- |
| `formato_template` | `chk_template_documenti_versioni_formato` | `HTML`, `HTML_MARKDOWN_BLOCKS` |
| `page_format` | `chk_template_documenti_versioni_page_format` | `A4`, `A3`, `LETTER` |
| `page_orientation` | `chk_template_documenti_versioni_orientation` | `PORTRAIT`, `LANDSCAPE` |

Un CHECK non si legge da una tendina. Così l'insieme vive in **tre** posti:

* il CHECK, a DB;
* tre `frozenset` nel backend (`template_versioni_admin_service.py`, `_FORMATI_VALIDI`,
  `_PAGE_FORMATS_VALIDI`, `_PAGE_ORIENTATIONS_VALIDI`), che anticipano il rifiuto;
* tre array nel frontend (`config/constants/documentiVersioniWhitelists.js`), che riempiono le
  tendine.

## 2. Il controesempio (fatto datato, 2026-10-03)

La copia del frontend era **già divergente**: offriva `MARKDOWN` e `A5`, che il DB rifiuta, e non
offriva `HTML_MARKDOWN_BLOCKS` né `A3`. Scegliendo «A5» la versione non si salvava; «A3» non si
poteva scegliere. Riallineata il 2026-10-03 leggendo il corpo dei CHECK da `pg_constraint`. La doc
API (`api_documenti_templates.md` §7) era giusta, il frontend no: nessun presidio confrontava le
copie.

## 3. Richiesta

| # | Cosa |
| --- | --- |
| **R-DB-1** | Tre vocabolari (`documenti.formati_template`, `documenti.formati_pagina`, `documenti.orientamenti_pagina`, o i nomi della casa), con `codice` + `etichetta_key` sulla forma di `config.esposizioni_componente` (`20261001-41`), e una FK dalle tre colonne al posto dei CHECK. Seed in `80_data` coi valori di §1 |
| **R-DB-2** | Le tre tabelle nella whitelist del lookup (`tabelle_gestibili.csv`, `lookup = true`, `pannello = false`), come R-DB-K1 dell'esposizione dei componenti |
| ❓ | Da decidere col team DB se `attivo` serve: sono la semantica del render (cosa sa stampare il motore), non una configurazione — stesso ragionamento del §9.2 di `brief-db-esposizione-componenti-kit-in-fattura` |

## 4. Dopo, lato BE/FE (si prenota qui)

* BE: le tre voci fra le `_LOOKUP_SPECIALIZZATE` (`etichetta_key`); via i tre `frozenset` del
  service — il rifiuto lo dà la FK, tradotto da `map_integrity_error`.
* FE: le tendine del `TemplateVersioneDrawer` dal lookup (etichette dal DB, ripiego sul codice); si
  ritira `documentiVersioniWhitelists.js`.

## 5. Risposta del team DB (2026-10-04)

> **Chi scrive:** sessione DB (`dev/db-tid`), 2026-10-04. Valutata e scritta R-DB-1 e R-DB-2;
> il ❓ di §3 è sciolto in §5.2. ✅ **Applicato il 2026-10-04** (§5.7).

### 5.1 Che cosa è stato scritto

| changeSet | Fase | Cosa |
| --- | --- | --- |
| `20261004-20-create-vocabolari-versione-template` | `00_schema/documenti` | `documenti.formati_template`, `documenti.formati_pagina`, `documenti.orientamenti_pagina`, forma di `config.esposizioni_componente` (`codice_interno`, `codice`, `descrizione`, `etichetta_key`, `ordine`, audit, `tx_id`) |
| `20261004-21-seed-vocabolari-versione-template` | `80_data` | mirror `loadUpdateData` dei tre CSV (`80_data/sql/documenti/*.csv`), coi valori dei tre CHECK — né uno di più né uno di meno |
| `20261004-22-fk-vocabolari-versione-template` | `80_data` | tre FK da `template_documenti_versioni` su `codice_interno`, `RESTRICT`; poi il `DROP` dei tre CHECK, nello stesso changeSet |
| `tabelle_gestibili.csv` (righe 90-92) | `80_data` | R-DB-2: `lookup = true`, `pannello = false` |
| `db/pgtap/documenti/test-documenti-vocabolari-versione-v1.sql` | pgTAP | 14 test, casi costruiti (sotto) |

Nomi: quelli proposti in §3 — plurali, nello schema `documenti`, accanto a `tipi_file_documento` e
compagni. Doc manuale aggiornata: `dbzero/documenti/manual/template_documenti_versioni.md`
(regole principali).

⚠️ Numerazione da `-20`: `-15` e `-16` sono di un'altra sessione DB aperta lo stesso giorno, non
ancora committati.

### 5.2 Le scelte, e perché

* **Niente `attivo`** (il ❓ di §3). Il ragionamento di §9.2 del brief dei kit vale identico: i
  valori sono ciò che il motore di stampa deve saper onorare, non una preferenza
  dell'installazione. Spegnerne uno non è una cosa che il modello sappia onorare — le versioni
  `PUBBLICATA` che lo usano sono immutabili (guard A1) — e con `attivo` a `ci_apply` nascerebbe la
  coppia ATTIVO su `template_documenti_versioni`. Un valore si aggiunge o si ritira con un
  cantiere (seed + motore), non con un flag.
* **FK su `codice_interno`, non su `id`.** Le tre colonne restano `varchar` e portano il codice,
  com'erano: nessuna conversione di tipo su righe pubblicate e immutabili, nessun cambio di
  contratto per il BE (manda e riceve gli stessi codici), e i tre seed di `80_data` già mergiati
  che copiano le versioni (`20260804-61`, `20260805-09`, `20260816-01`) restano validi. Precedente:
  `20261001-57`.
* **Non contraddice le decisioni 62-63 del 2026-04-29** (`work-done/sviluppo-documenti.md`):
  quelle dicono «tecnici, non lookup **configurabili**», e restano vere — i vocabolari si leggono e
  non si scrivono (`pannello = false`). Cambia la sede dell'insieme, non chi lo decide.
* **Le FK in `80_data`, dopo il seed**: in `00_schema` il catalogo è vuoto. Il `DROP` dei CHECK sta
  nello stesso changeSet, dopo le FK, così la colonna non resta mai senza cancello. Nessun
  changeSet di `80_data`/`90_end` nomina i tre CHECK (censito il 2026-10-04), quindi il `DROP` non
  ne rompe nessuno a valle.
* **Che cosa nasce da solo a `ci_apply`**: audit, `tx_id` e il lock su `codice_interno` (per la
  sola presenza della colonna). Niente `storicizza`, quindi niente storico e nessuna riga in
  `dbops.storico_scope_policy` — come il precedente. Nessuna FK verso tabelle in RLS, quindi il
  presidio del perimetro non è toccato.

### 5.3 La prova (2026-10-04)

Su `zeroerp_ci`, da owner, in una transazione annullata: l'SQL **estratto** dai due YAML con
`ON_ERROR_STOP`, i seed simulati riga per riga dai CSV, poi il pgTAP.

* `test-documenti-vocabolari-versione-v1`: **13/14**; il 14 (lock su `codice_interno`) è rosso per
  costruzione senza `ci_apply`. Con `dbops.fn_run_automations_lock_columns('CI', ARRAY['documenti'], false)`
  nella stessa transazione: **14/14**.
* Gli altri 13 pgTAP di `db/pgtap/documenti/`, ciascuno con l'SQL nuovo in testa: tutti verdi
  tranne `test-documenti-generati-eventi` 16, che è rosso **anche senza** l'SQL nuovo — è un test
  di RLS, rosso da owner per costruzione.
* 8 e 9 usano `A5` e `MARKDOWN` apposta: sono i due valori che la copia del FE offriva e il DB
  rifiutava (§2).

Non provati qui: l'apply vero (il loader `loadUpdateData`, `ci_apply`), la corsa come app, i
presidi trasversali. Restano a Tid.

### 5.4 Ricadute sul BE/FE — conferma e aggiunte a §4

| # | Cosa | Quando |
| --- | --- | --- |
| **R-FE-V1** | Le sette chiavi i18n nei locale: `documenti.formati_template.html`, `.html_markdown_blocks`; `documenti.formati_pagina.a4`, `.a3`, `.letter`; `documenti.orientamenti_pagina.portrait`, `.landscape`. ⛔ `scripts/check_i18n_keys.py` legge la colonna `etichetta_key` dei CSV: senza le chiavi **la CI è rossa** | **stesso giro** del DB, prima del merge su `Tito-dev` |
| **R-BE-V1** | §4 confermato: le tre voci fra le `_LOOKUP_SPECIALIZZATE` (`etichetta_key`), via i tre `frozenset`. ⚠️ `map_integrity_error` del service delle versioni mappa oggi i nomi dei tre CHECK, che non esistono più: un valore fuori catalogo esce **23503** con il nome della FK (`fk_template_documenti_versioni_formati_template`, `_formati_pagina`, `_orientamenti_pagina`). Finché i `frozenset` restano, il rifiuto arriva prima: nessuna regressione nel frattempo | dopo l'apply |
| **R-FE-V2** | §4 confermato: tendine dal lookup, si ritira `documentiVersioniWhitelists.js` | dopo R-BE-V1 |

### 5.5 ⚠️ Emerso nella valutazione — il motore di stampa non legge le tre colonne (D-1: ✅ strada A, §5.6)

Leggendo chi consuma i valori (fatto di struttura, letto nel codice il 2026-10-04):
`apps/documenti/services/render_service.render_pdf` passa a WeasyPrint **solo** `html_template` e
`css_template`. Non legge `page_format`, `page_orientation`, i quattro margini, né
`formato_template`; `markdown_template` «in v1 non viene processato». Nessun template di seed
dichiara una regola `@page` nel CSS. Quindi:

* una versione con `page_format = A3` e `page_orientation = LANDSCAPE` esce **A4 verticale** (il
  default di WeasyPrint), senza errore;
* `HTML_MARKDOWN_BLOCKS` si salva e si comporta come `HTML`.

Le colonne sono una **promessa che nessuno onora**: il drawer fa scegliere un valore che non ha
effetto. Il vocabolario non crea il problema e non lo risolve: sposta in una sede sola un insieme
che oggi, a stampa, non conta. Le strade:

| | Strada | Effetto |
| --- | --- | --- |
| **A** (raccomandata) | Il render onora le colonne: il BE compone un `@page { size: <formato> <orientamento>; margin: … }` dai campi della versione e lo passa a WeasyPrint. Da decidere chi vince se il CSS del template dichiara anche lui `@page` | le colonne fanno quello che il modello dichiara («Layout PDF», manuale della tabella). I codici del vocabolario sono già parole CSS valide (`A4`, `A3`, `letter`, `portrait`, `landscape`), quindi non serve una colonna in più |
| **B** | Si ritirano `page_format`, `page_orientation` e i margini: la pagina la decide il CSS del template | un cantiere DB a parte (colonne, vocabolari appena nati, drawer). Perde la scelta guidata |

Su `formato_template` la domanda è diversa: `HTML_MARKDOWN_BLOCKS` era la Decisione 4 («markdown
solo per blocchi controllati pre-convertiti»), mai implementata. Resta a catalogo perché lo era
nel CHECK — il cantiere sposta l'insieme, non lo restringe — ma oggi è una scelta senza effetto.
Da decidere se implementarla o ritirarla, insieme a D-1.

⭐ Il lavoro DB di §5.1 è giusto con A e con il sì a `HTML_MARKDOWN_BLOCKS`; con B le
`formati_pagina`/`orientamenti_pagina` andrebbero ritirate prima del commit, e costa poco perché
non è ancora applicato niente.

### 5.6 ✅ D-1 decisa da Tid (2026-10-04): strada A

**Il render onora le colonne della versione.** Il lavoro DB di §5.1 resta com'è: i vocabolari
servono anche alla strada A, e i loro codici sono già parole CSS. Al DB non serve altro.

| # | Cosa | A chi |
| --- | --- | --- |
| **R-BE-V2** | `render_pdf` compone dai campi della versione una regola `@page { size: <page_format> <page_orientation>; margin: <top> <right> <bottom> <left>mm }` e la passa a WeasyPrint insieme al CSS del template. I valori si leggono dalla versione già caricata (`_VERSIONI_PROJECTION_DETAIL` porta le colonne); nessuna tabella di traduzione nel codice, perché `A4`, `A3`, `LETTER`, `PORTRAIT`, `LANDSCAPE` sono parole CSS valide (in CSS non conta maiuscolo o minuscolo) | BE |
| **R-BE-V2a** | Da decidere nel giro BE, e da scrivere nella doc API: chi vince se anche il CSS del template dichiara `@page`. ⭐ La lettura coerente col modello: vincono le colonne, perché sono ciò che il drawer fa scegliere; quindi la regola composta va passata **dopo** il CSS del template. Se invece si vuole lasciare al template l'ultima parola, il drawer deve dirlo | BE (+ Tid se serve) |
| **R-BE-V2b** | Un test che stampa una versione A3 orizzontale e legge la dimensione della pagina del PDF: il caso di §5.5 che oggi esce A4 senza errore | BE |

⚠️ **Resta aperto, e non era dentro D-1**: `HTML_MARKDOWN_BLOCKS` (Decisione 4, mai
implementata). Resta a catalogo; implementarlo o ritirarlo è una domanda a sé per Tid, da
aprire quando si tocca il trattamento del markdown.

### 5.7 ✅ Applicato (2026-10-04)

Tid ha applicato `20261004-20…-22` su dbdev il 2026-10-04: **nessuna regressione** nella corsa
pgTAP. Letto dal catalogo di sistema lo stesso giorno: esistono le tre tabelle
`documenti.formati_template`, `formati_pagina`, `orientamenti_pagina` e le tre FK
`fk_template_documenti_versioni_*`; i tre CHECK non ci sono più.

Lato DB chiuso. Il brief resta aperto per:

* **R-FE-V1**: le sette chiavi i18n — fino ad allora `check_i18n_keys.py` è rosso;
* **R-BE-V1 / R-FE-V2** (§5.4): tendine dal lookup, via i `frozenset` e
  `documentiVersioniWhitelists.js`, `map_integrity_error` sui nomi delle FK;
* **R-BE-V2…V2b** (§5.6): il render onora formato, orientamento e margini.

Quando i tre punti sono chiusi, il brief va in `work-done/`.

## 6. Lato BE/FE (2026-10-04)

> **Chi scrive:** sessione BE/FE (`dev/backend-tid`), 2026-10-04. **A chi:** Tid (commit).
> **Decisioni di Tid nella sessione:** R-BE-V2a → **vincono le colonne**; il file
> `documentiVersioniWhitelists.js` si cancella.
> **Stato:** fatto, non committato.

### 6.1 Le richieste

| # | Stato | Dove |
| --- | --- | --- |
| R-FE-V1 | ✅ le sette chiavi in it ed en, sotto `documenti.formati_template` / `formati_pagina` / `orientamenti_pagina`. Ritirate le due `config.modelli_documenti.versioni.orientation_*`, che il drawer usava al loro posto. `check_i18n_keys` torna pulito | `it.json`, `en.json` |
| R-BE-V1 | ✅ le tre voci fra le `_LOOKUP_SPECIALIZZATE` (`etichetta_key`, senza `attivo` né `obsoleto_dal`). Tolti i tre `frozenset` e `_validate_in_set`: il valore arriva al DB com'è e la FK decide. `_CHECK_CONSTRAINTS` perde i tre CHECK ritirati; nasce `_FK_CONSTRAINTS` coi nomi delle tre FK e il **campo** di ciascuna, passato a ogni `map_integrity_error` del service | `dbops_repository.py`, `template_versioni_admin_service.py` |
| R-FE-V2 | ✅ le tre tendine del drawer da `useLookupEtichettato` sul `codice_interno`; `documentiVersioniWhitelists.js` cancellato | `TemplateVersioneDrawer.vue` |
| R-BE-V2 | ✅ `render_pdf` compone `@page { size: <formato> <orientamento> !important; margin: … !important }` dalle colonne e lo passa a WeasyPrint **dopo** il CSS del template (`_regola_pagina`) | `render_service.py` |
| R-BE-V2a | ✅ **vincono le colonne** (Tid). Restano del template le altre dichiarazioni dell'`@page` (i box di margine). Scritto nella doc API | `api_documenti_templates.md` |
| R-BE-V2b | ✅ test 28 sulla libreria vera: una versione A3 orizzontale con `@page { size: A4 }` nel CSS **e** in uno `<style>` dell'HTML esce 420 × 297 mm (letto dal `/MediaBox` del PDF); la A4 verticale resta 210 × 297 | `test_render_service.py` |

### 6.2 Scelte fatte scrivendo

* **`!important` è necessario, non un vezzo.** WeasyPrint tratta i fogli passati con `stylesheets=`
  come origine **user**, e un `@page` scritto in uno `<style>` dell'HTML è origine **author**: nella
  cascata l'author batte lo user **qualunque sia l'ordine**. Provato il 2026-10-04: senza
  `!important` un A3 orizzontale usciva A4 verticale, con margini 18/16. Solo un `!important` di
  origine user batte l'author. Il test 28 mette l'`@page` concorrente proprio nello `<style>`.
* **Niente ripiego.** I sei campi di pagina sono NOT NULL a DB: uno assente è una proiezione rotta,
  e il render si ferma con `E_DOCUMENTI_RENDER_FAILED` e il campo nel `detail`, invece di stampare
  un A4. Il formato e l'orientamento finiscono in un foglio CSS, quindi devono essere
  identificatori (`[A-Za-z0-9_]+`), e un margine dev'essere un numero finito e non negativo.
* **Il nome della FK provato sul DB vero.** Con un nome sbagliato nella mappa il rifiuto cadrebbe
  nel ripiego senza campo, e nessun mock se ne accorgerebbe: test 3 di
  `test_versione_contesto_db` (sulla bozza che quel file già costruisce) salva
  `HTML_MARKDOWN_BLOCKS` / `A3` / `LANDSCAPE` e rifiuta `MARKDOWN`, `A5`, `OBLIQUO` con 400 e campo.

### 6.3 ⚠️ Un fatto che smentisce il §5.5, e cosa ne segue

Il §5.5 dice che nessun template di seed dichiara un `@page`. Letto su dbdev il 2026-10-04 (fatto
datato): **tutte** le versioni pubblicate e in bozza (preventivo, contratto, offerta, ordine, DDT, fattura
v7) hanno nel CSS `@page { size: A4; margin: 18mm 16mm 18mm 16mm; @bottom-left { … } }`, e alcune lo
ripetono in uno `<style>` dell'HTML. Le loro colonne dicono A4 verticale e margini **15 mm**.

Era la stessa cosa scritta in due sedi, già divergenti. Con la regola di Tid, dal 2026-10-04:

* tutte stampano coi **15 mm** delle colonne, piè di pagina invariato;
* la **ristampa fedele** dei documenti già emessi esce coi 15 mm, diversa dal PDF di allora (usa la
  versione di allora, e le versioni pubblicate non si modificano);
* per tornare ai 18/16 mm servono versioni **nuove** coi margini nelle colonne. Nel loro CSS
  l'`@page` di formato e margini non ha più effetto, e conviene toglierlo, per non lasciare una
  seconda sede che non conta.

### 6.4 Come è stato provato

* `apps.documenti`, `apps.core`, `apps.config`, `apps.vendite`, `apps.anagrafiche`: **4654 verdi**
  (131 skip). Sul DB provvisto (`ZEROERP_TEST_DB_E2E=1`) `apps.documenti.tests.db` e
  `test_lookup_specializzate` (il test 4 attraversa sul DB **ogni** specializzata, quindi anche le
  tre nuove): **16 verdi**.
* FE: vitest **662 verdi**, eslint pulito su `src/config`, `check_i18n_keys` pulito. Ruff pulito.
* ⚠️ **Non provato**: il drawer a video (le tendine dal lookup) e un PDF vero generato da una
  versione pubblicata dopo il cambio dei margini.

