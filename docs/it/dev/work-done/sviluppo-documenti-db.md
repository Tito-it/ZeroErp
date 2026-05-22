# Sviluppo Documenti — Piano DB Corretto

> **Stato**: WIP
> **Data**: 2026-04-29
> **Origine**: estrazione e revisione critica della sezione DB di `sviluppo-documenti.md`
> **Obiettivo**: definire una traccia DB coerente con gli standard reali del repo e con il primo consumatore previsto (`PREVENTIVO`)

---

## 1. Scopo

Questo documento isola la parte **DB** dello sviluppo documenti e la riallinea
alle convenzioni gia' operative in ZeroERP.

Non sostituisce il documento principale
`docs/it/dev/work-in-progress/sviluppo-documenti.md`: lo integra, restringendo
il focus a:

- correzioni strutturali del modello dati;
- punti di attenzione emersi dalla documentazione esistente;
- ordine di atterraggio consigliato per una prima slice reale;
- confine chiaro tra attivita' DB e attivita' backend.

---

## 2. Documentazione letta

Analisi basata prima sulla documentazione, non sulle migrations.

Riferimenti principali:

- `docs/it/dev/work-in-progress/sviluppo-documenti.md`
- `docs/it/linee-guida-sql.md`
- `docs/it/linee-guida-trigger.md`
- `docs/it/liquibase-setup-workflow.md`
- `docs/it/sviluppo-concentrico.md`
- `docs/it/mappa-concentrica.md`
- `docs/it/dbzero/config/manual/sorgenti.md`
- `docs/it/dbzero/config/manual/parameters.md`
- `docs/it/dbzero/anagrafiche/manual/emittenti_fiscali.md`
- `docs/it/dbzero/vendite/manual/listini_versioni.md`
- `docs/it/dbzero/dbops/manual/fn_apply_chiusura_scadenze.md`
- `docs/it/backend/core/manual/api_lookup_codici.md`

---

## 3. Valutazione critica del piano DB originale

Il piano in coda a `sviluppo-documenti.md` e' concettualmente valido, ma troppo
ampio come prima consegna.

Punti principali:

1. Il primo consumatore dichiarato e' `PREVENTIVO`, ma il piano finale modella
   subito un motore documentale quasi completo e cross-domain.
2. Questo contrasta con il principio concentrico del repo: prima una slice
   verticale reale, poi promozione delle astrazioni gia' validate.
3. Le tabelle con `valido_dal` e `valido_al` devono seguire il pattern standard
   del progetto con colonna `validita daterange` calcolata da trigger, non solo
   con le due date input.
4. La whitelist lookup generica non e' solo DB: oggi e' anche una whitelist
   Python nel backend. Quindi non va descritta come deliverable esclusivamente
   DB.
5. Lo schema nuovo `documenti` non entrera' nelle automazioni standard solo per
   il fatto di esistere: va aggiunto esplicitamente all'ambito delle
   automazioni.
6. Le FK verso l'utente Django devono seguire il pattern reale del repo:
   riferimento a `django.auth_user(id)` con creazione condizionale, non
   `auth_user(id)` hardcoded.
7. Alcuni vincoli proposti sono semanticamente corretti ma tecnicamente
   incompleti, per esempio:
   - unique con campi nullable su `documenti_generati`;
   - vincolo "un solo PDF_FINALE" basato su lookup FK senza strategia esplicita;
   - "un solo default" espresso come regola ma non ancora come indice parziale
     concreto.
8. Alcuni pezzi sono utili, ma non indispensabili per validare il primo caso
   d'uso: allegati template multi-PDF, eventi persistenti completi, engine
   multipli.

Conclusione: il lavoro va spezzato in **tranche DB**.

---

## 4. Decisioni DB corrette

### 4.1 Schema dedicato

Confermata la scelta di uno schema dedicato:

- `documenti`

Motivo:

- dominio trasversale;
- non corretto legarlo a `vendite`;
- compatibile con futuri consumatori oltre `PREVENTIVO`.

### 4.2 Pattern temporale standard

Le tabelle documentali con validita' temporale devono adottare il pattern di
progetto completo:

- `valido_dal`
- `valido_al`
- `validita daterange NOT NULL`

Regole:

- `validita` calcolata da `script.trgfn_set_validita()`;
- query operative data-driven su `validita @> CURRENT_DATE`;
- vincoli anti-overlap preferibilmente tramite `EXCLUDE USING gist`.

Questo vale almeno per:

- `documenti.template_documenti_versioni`
- `documenti.template_asset`

### 4.3 Workflow stato + validita'

Se una tabella ha sia stato sia finestra temporale, si applica il pattern
documentato in `linee-guida-sql.md`:

- le date comandano;
- lo stato accompagna;
- eventuali transizioni verso stato terminale devono essere coerenti con
  `valido_al`;
- evitare logiche ridondanti o doppia fonte di verita'.

Per la prima tranche documenti il minimo necessario e':

- guard su versioni `PUBBLICATA`;
- anti-overlap sulle versioni pubblicate;
- nessuna automazione di chiusura generalizzata finche' non esiste un secondo
  consumatore reale che la giustifichi.

### 4.4 Ambito automazioni DB

Se vogliamo audit, tx_id, storicizzazione e lock standard su `documenti`,
servono anche attivita' di predisposizione nucleo:

- aggiungere `documenti,*all` a `dbops.automation_scope`;
- verificare quali regole automatiche sono desiderate davvero sulle tabelle del
  dominio;
- non descrivere i trigger standard come "automatici" senza questa
  registrazione.

### 4.5 Lookup generica

Le nuove tabelle lookup documentali sono corrette come scelta.

Pero' la loro esposizione al lookup generico richiede due livelli:

- DB: tabella con struttura compatibile `id/codice/codice_interno/descrizione`
- Backend: aggiunta della relazione `schema.tabella` alla whitelist Python

Quindi il punto "whitelist lookup generica" va marcato come dipendenza DB+BE,
non DB puro.

### 4.6 FK verso utente Django

Le colonne:

- `documenti.documenti_generati.generato_da_user_id`
- `documenti.documenti_generati_eventi.user_id`

devono seguire il pattern gia' in uso nel repo:

- FK a `django.auth_user(id)`
- creata in modo condizionale con `to_regclass('django.auth_user')`

per non rompere ambienti dove lo schema Django non e' presente.

---

## 5. Tranche DB consigliate

## Fase A — Slice minima valida per `PREVENTIVO`

Questa e' la prima consegna raccomandata.

Obiettivo:

- permettere configurazione template;
- permettere versionamento template;
- permettere generazione persistente di un PDF finale storicizzato;
- evitare componenti non ancora esercitati da un consumatore reale.

Include:

1. Schema `documenti`
2. Ambito automazioni DB per `documenti`
3. Lookup standard:
   - `tipi_documento_output`
   - `tipi_asset_documento`
   - `tipi_file_documento`
   - `render_engine_documento`
4. Seed minimi:
   - `PREVENTIVO`
   - `WEASYPRINT`
   - `PDF_FINALE`
   - tipi asset base
5. `documenti.template_documenti`
6. `documenti.template_documenti_versioni`
7. `documenti.template_asset`
8. `documenti.documenti_generati`
9. `documenti.documenti_generati_file`
10. Parametri `config.parameters` per storage e limiti

Scelta deliberata:

- `template_allegati` rinviata;
- `documenti_generati_eventi` rinviata;
- nessun engine secondario operativo oltre `WEASYPRINT`.

## Fase B — Estensioni dopo la prima validazione

Da aprire solo dopo il primo flusso reale `PREVENTIVO -> PDF persistito`.

Include:

1. `documenti.ruoli_template_asset`
2. `documenti.template_allegati`
3. `documenti.documenti_generati_eventi`
4. vincoli/guard specializzati sugli allegati
5. supporto a `PDF_ALLEGATO`, `PDF_FIRMATO`, `HTML_RENDER`
6. eventuale engine addizionale `PLAYWRIGHT_PDF`

## Fase C — Generalizzazione cross-domain

Da affrontare solo dopo almeno un secondo consumatore reale oltre
`PREVENTIVO`.

Possibili estensioni:

- contratti;
- ordini;
- archivio documentale generale;
- policy piu' ricche per allegati condizionali;
- automazioni trasversali ulteriori se emergono pattern ripetuti.

---

## 6. Modello DB della Fase A

### 6.1 Lookup standard

Tabelle:

- `documenti.tipi_documento_output`
- `documenti.tipi_asset_documento`
- `documenti.tipi_file_documento`
- `documenti.render_engine_documento`

Struttura standard:

- `id`
- `codice`
- `codice_interno`
- `descrizione`
- `attivo`
- `meta`
- `storicizza`
- `tx_id`
- audit fields

Guard:

- lock `codice_interno`
- record di sistema protetti anche su `codice` dove opportuno

### 6.2 `documenti.template_documenti`

Responsabilita':

- definire l'identita' logica del template;
- legarlo a tipo output, sorgente e emittente fiscale;
- marcare eventuale template default.

Correzione chiave:

- la unique non deve essere solo `(tipo_documento_output_id, codice)`;
- va modellata in modo compatibile col fatto che il template e' per
  emittente e per sorgente.

Proposta:

- unique su `(emittente_fiscale_id, sorgente_tipo_id, codice)`

Vincolo default:

- indice univoco parziale su
  `(tipo_documento_output_id, sorgente_tipo_id, emittente_fiscale_id)`
  filtrato su `is_default = true AND attivo = true`

### 6.3 `documenti.template_documenti_versioni`

Responsabilita':

- conservare il contenuto renderizzabile;
- gestire il versionamento;
- mantenere finestra temporale e stato pubblicazione.

Correzioni strutturali:

- aggiungere `validita daterange NOT NULL`
- trigger `script.trgfn_set_validita()`
- anti-overlap solo sulle versioni `PUBBLICATA` attive dello stesso template

Stato tecnico iniziale:

- `BOZZA`
- `PUBBLICATA`
- `OBSOLETA`

Regole minime:

- una versione `PUBBLICATA` e' immutabile;
- una `BOZZA` puo' essere cancellata;
- una versione gia' usata da documenti generati non puo' essere cancellata;
- publish e obsolescenza precedente restano orchestrati dal service, ma il DB
  deve bloccare stati incoerenti.

### 6.4 `documenti.template_asset`

Responsabilita':

- registrare asset binari per emittente;
- consentire storico per file distinti;
- impedire sostituzione distruttiva del file.

Campi identitari:

- `codice` per l'uso operativo e leggibile;
- `codice_interno` come identificatore tecnico stabile dell'asset;
- `sha256` come identificatore del contenuto binario caricato.

`sha256` non sostituisce `codice_interno`: i due campi hanno semantica diversa.

Correzioni strutturali:

- aggiungere `validita daterange NOT NULL`
- trigger `script.trgfn_set_validita()`
- unique `(emittente_fiscale_id, codice_interno)`
- unique `(emittente_fiscale_id, sha256)`

Regole minime:

- delete fisico sempre bloccato;
- file/hash/storage immutabili quando l'asset e' gia' usato;
- per cambiare file si crea un nuovo asset.

### 6.5 `documenti.documenti_generati`

Responsabilita':

- rappresentare la generazione persistente del documento;
- mantenere snapshot dati, hash e legame con template/versione.

Correzione chiave:

- la unique su
  `(sorgente_tipo_id, sorgente_uid, sorgente_riga, progressivo_sorgente)`
  va resa robusta anche con `sorgente_riga NULL`

Proposta:

- usare indice unique con `NULLS NOT DISTINCT` se disponibile nel pattern
  adottato dal progetto;
- in alternativa indice unique su espressione con `COALESCE`.

FK utente:

- riferimento condizionale a `django.auth_user(id)`

Stati minimi:

- `GENERATO`
- `ARCHIVIATO`
- `ANNULLATO`

Nota:

- `CORRENTE` e `SOSTITUITO` possono anche essere rinviati alla Fase B se nella
  prima consegna il "corrente" e' determinato solo da ordinamento e non da
  stato persistito.

### 6.6 `documenti.documenti_generati_file`

Responsabilita':

- collegare il file fisico persistito al record funzionale di generazione.

Per la Fase A basta supportare:

- `PDF_FINALE`

Regola:

- un solo `PDF_FINALE` per `documento_generato_id`

Scelta tecnica da fissare nel DDL:

- o guard trigger esplicito;
- o indice univoco parziale se si decide una modellazione che non dipenda da
  join su lookup.

---

## 7. Oggetti rinviati

Questi oggetti sono legittimi, ma non sono necessari nella prima slice:

- `documenti.ruoli_template_asset`
- `documenti.template_allegati`
- `documenti.documenti_generati_eventi`
- `PLAYWRIGHT_PDF`
- allegati PDF fusi nel `PDF_FINALE`
- archivio generale cross-sorgente

Motivo del rinvio:

- alzano molto il costo del modello;
- introducono piu' stati/guard/lookup;
- non servono per validare il flusso base del preventivo.

---

## 8. Parametri `config.parameters`

Confermata la scelta di usare `config.parameters` per la configurazione non
segreta.

Seed consigliati Fase A:

- `documenti_storage_provider`
- `documenti_storage_endpoint`
- `documenti_storage_base_url`
- `documenti_storage_bucket`
- `documenti_storage_prefix`
- `documenti_storage_secret_ref`
- `documenti_asset_upload_max_mb`
- `documenti_pdf_generato_max_mb`

Regole:

- nessuna credenziale in chiaro;
- `secret_ref` solo riferimento logico;
- valori portabili come stringhe, non ID numerici.

Nota:

- la validazione semantica di questi parametri resta lato backend/service.

---

## 9. Deliverable DB della Fase A

Deliverable attesi:

1. Changeset Liquibase ordinati in `migrations_v2`
2. Registrazione dello schema `documenti` nell'ambito automazioni DB
3. Tabelle e vincoli della Fase A
4. Seed idempotenti lookup e parametri
5. Guard minime su immutabilita' e delete block
6. Test pgTAP della Fase A
7. Commenti su tabelle e colonne principali

Esplicitamente fuori scope della Fase A:

- API
- service di render
- upload reale storage
- gestione allegati template
- eventi di download persistenti

---

## 10. Piano di esecuzione

Il piano seguente traduce la Fase A in step operativi ordinati.

### Step 0 — Preparazione tecnica

Obiettivo:

- predisporre il contesto DB per il nuovo schema.

Attivita':

1. creare il file `00_schema/documenti/<data>-01-create-schema-documenti-*.yaml`
2. creare lo schema `documenti`
3. aggiungere commento schema
4. aggiungere `documenti,*all` a `dbops.automation_scope`
5. verificare che lo schema rientri nelle automazioni standard del progetto

Output atteso:

- schema esistente e riconosciuto dal framework automazioni

### Step 1 — Lookup di base

Obiettivo:

- creare il vocabolario minimo del modulo.

Attivita':

1. creare:
   - `documenti.tipi_documento_output`
   - `documenti.tipi_asset_documento`
   - `documenti.tipi_file_documento`
   - `documenti.render_engine_documento`
2. applicare i campi standard:
   - `id`
   - `codice`
   - `codice_interno`
   - `descrizione`
   - `attivo`
   - `meta`
   - `storicizza`
   - `tx_id`
   - audit fields
3. applicare i vincoli:
   - unique `codice`
   - unique `codice_interno`
   - check non vuoto
4. predisporre lock `codice_interno`

Output atteso:

- lookup tecnici disponibili e coerenti con lo standard config-like

### Step 2 — Seed minimi

Obiettivo:

- rendere subito utilizzabile il modulo nel primo caso `PREVENTIVO`.

Attivita':

1. seed `documenti.tipi_documento_output`:
   - `PREVENTIVO`
2. seed `documenti.tipi_asset_documento`:
   - `LOGO`
   - `FIRMA`
   - `IMMAGINE`
   - `PDF`
   - `CSS`
   - `ALTRO`
3. seed `documenti.tipi_file_documento`:
   - `PDF_FINALE`
4. seed `documenti.render_engine_documento`:
   - `WEASYPRINT`
5. garantire idempotenza su `codice_interno`

Output atteso:

- lookup valorizzati senza dipendenza da ID numerici

### Step 3 — `template_documenti`

Obiettivo:

- creare il contenitore logico dei template.

Attivita':

1. creare `documenti.template_documenti`
2. aggiungere FK verso:
   - `documenti.tipi_documento_output`
   - `config.sorgenti`
   - `anagrafiche.emittenti_fiscali`
3. applicare unique coerente con emittente e sorgente
4. applicare indice univoco parziale per `is_default = true AND attivo = true`
5. applicare lock su `codice`

Output atteso:

- template logici registrabili per tipo output, sorgente ed emittente

### Step 4 — `template_documenti_versioni`

Obiettivo:

- creare il versionamento reale del template renderizzabile.

Attivita':

1. creare `documenti.template_documenti_versioni`
2. aggiungere:
   - `valido_dal`
   - `valido_al`
   - `validita`
3. installare trigger `script.trgfn_set_validita()`
4. aggiungere FK verso:
   - `documenti.template_documenti`
   - `documenti.render_engine_documento`
5. definire gli stati tecnici:
   - `BOZZA`
   - `PUBBLICATA`
   - `OBSOLETA`
6. creare guard di immutabilita' per versioni `PUBBLICATA`
7. creare vincolo anti-overlap per versioni `PUBBLICATA` dello stesso template
8. bloccare la cancellazione di versioni pubblicate o gia' usate

Output atteso:

- versioni pubblicabili con regole temporali e di immutabilita' solide

### Step 5 — `template_asset`

Obiettivo:

- registrare asset binari riusabili per emittente.

Attivita':

1. creare `documenti.template_asset`
2. aggiungere:
   - `valido_dal`
   - `valido_al`
   - `validita`
3. installare trigger `script.trgfn_set_validita()`
4. aggiungere FK verso:
   - `documenti.tipi_asset_documento`
   - `anagrafiche.emittenti_fiscali`
5. creare unique su:
   - `(emittente_fiscale_id, codice)`
   - `(emittente_fiscale_id, sha256)`
6. bloccare delete fisico
7. bloccare modifica colonne file/hash quando l'asset e' usato

Output atteso:

- catalogo asset storicizzabile e non distruttivo

### Step 6 — `documenti_generati`

Obiettivo:

- persistere la generazione storica del PDF.

Attivita':

1. creare `documenti.documenti_generati`
2. aggiungere FK verso:
   - `documenti.tipi_documento_output`
   - `documenti.template_documenti`
   - `documenti.template_documenti_versioni`
   - `config.sorgenti`
   - `anagrafiche.emittenti_fiscali`
3. aggiungere FK condizionale a `django.auth_user(id)` per `generato_da_user_id`
4. applicare unique su `uid`
5. applicare unique robusta per progressivo sorgente anche con `sorgente_riga NULL`
6. definire gli stati minimi della Fase A
7. bloccare delete fisico

Output atteso:

- registro storico delle generazioni persistite

### Step 7 — `documenti_generati_file`

Obiettivo:

- collegare il file PDF finale alla generazione.

Attivita':

1. creare `documenti.documenti_generati_file`
2. aggiungere FK verso:
   - `documenti.documenti_generati`
   - `documenti.tipi_file_documento`
3. applicare i check su:
   - `file_size_bytes`
   - `sha256`
   - `ordinamento`
4. implementare la regola:
   - un solo `PDF_FINALE` per `documento_generato_id`

Output atteso:

- persistenza del PDF finale coerente con il record funzionale

### Step 8 — Parametri storage

Obiettivo:

- predisporre la configurazione non segreta del backend documentale.

Attivita':

1. seed parametri in `config.parameters`:
   - `documenti_storage_provider`
   - `documenti_storage_endpoint`
   - `documenti_storage_base_url`
   - `documenti_storage_bucket`
   - `documenti_storage_prefix`
   - `documenti_storage_secret_ref`
   - `documenti_asset_upload_max_mb`
   - `documenti_pdf_generato_max_mb`
2. rendere gli insert idempotenti su `code`
3. evitare qualsiasi credenziale in chiaro

Output atteso:

- configurazione base pronta per essere letta dal backend

### Step 9 — Test pgTAP

Obiettivo:

- verificare che il modello sia sicuro prima del layer applicativo.

Attivita':

1. test lookup e seed
2. test default unico template
3. test anti-overlap versioni pubblicate
4. test immutabilita' versione `PUBBLICATA`
5. test delete block asset
6. test lock colonne file asset usato
7. test unique progressivo sorgente
8. test un solo `PDF_FINALE`
9. test seed parametri idempotenti

Output atteso:

- base DB validata e pronta per il lavoro BE

### Step 10 — Step successivi fuori Fase A

Da non eseguire nella prima consegna:

1. `documenti.ruoli_template_asset`
2. `documenti.template_allegati`
3. `documenti.documenti_generati_eventi`
4. engine secondari
5. allegati PDF fusi nel file finale
6. archivio generale cross-sorgente

---

## 11. Test DB minimi consigliati

Per la Fase A:

- creazione schema `documenti`
- scope automazioni registrato
- unique `codice` e `codice_interno` sulle lookup
- lock `codice_interno`
- unique default template per emittente/sorgente/tipo
- anti-overlap versioni `PUBBLICATA`
- immutabilita' versione `PUBBLICATA`
- deduplica asset per `(emittente_fiscale_id, sha256)`
- delete block asset
- immutabilita' file asset usato
- unique progressivo sorgente anche con `sorgente_riga NULL`
- un solo `PDF_FINALE` per documento generato
- seed parametri idempotenti

---

## 12. Sintesi operativa

La direzione architetturale del modulo `documenti` e' corretta.

La correzione necessaria non e' cambiare idea, ma cambiare **ordine di
atterraggio**:

- prima una base DB essenziale ma solida per `PREVENTIVO`;
- poi allegati, eventi e generalizzazioni;
- poi eventuale promozione delle astrazioni cross-domain solo dopo uso reale.

Questo mantiene coerenza con:

- sviluppo concentrico;
- standard SQL del repo;
- pattern gia' usati per validita', stato, lookup e configurazione.

---

## 13. Analisi critica stato attuale (2026-04-30)

> Scopo della sezione: confrontare cio' che e' gia' atterrato in
> `db/changelog/migrations_v2/` con il piano della Fase A, e fissare un elenco
> chiuso di cosa rimane da fare lato DB **prima** di considerare la Fase A
> davvero conclusa.

### 13.1 Cosa e' gia' atterrato

| Step Fase A | File migration | Stato |
| --- | --- | --- |
| Step 0 schema | `00_schema/documenti/20260429-51-create-schema-documenti-mctit.yaml` | ok |
| Step 0 scope automazioni | `80_data/sql/dbops/automation_scope.csv` riga `documenti,*all` | ok |
| Step 1+2 lookup + seed | `00_schema/documenti/20260429-52-create-lookup-documenti-base-mctit.yaml` + `80_data/changelog/20260429-58-upsert-documenti-seed-base-mctit.yaml` + 4 CSV in `80_data/sql/documenti/` | ok |
| Step 3 `template_documenti` | `00_schema/documenti/20260429-53-create-template-documenti-mctit.yaml` | ok |
| Step 4 `template_documenti_versioni` | `00_schema/documenti/20260429-54-create-template-documenti-versioni-mctit.yaml` | ok |
| Step 5 `template_asset` | `00_schema/documenti/20260429-55-create-template-asset-mctit.yaml` | ok |
| Step 6 `documenti_generati` | `00_schema/documenti/20260429-56-create-documenti-generati-mctit.yaml` (con FK condizionale `django.auth_user`) | ok |
| Step 7 `documenti_generati_file` | `00_schema/documenti/20260429-57-create-documenti-generati-file-mctit.yaml` | ok |
| Step 8 parametri storage | `80_data/changelog/20260429-59-upsert-parameters-documenti-storage-mctit.yaml` + `80_data/sql/config/parameters_documenti_storage.csv` | ok |
| Step 9 test pgTAP | `db/pgtap/documenti/` non esiste | **mancante** |

Quindi struttura tabelle e seed sono completi. Le **guard funzionali**, i
**collanti applicativi** e i **test pgTAP** restano da scrivere.

### 13.2 Punti dove il DDL gia' atterrato e' coerente con il piano

- `documenti.template_documenti` espone sia `codice` sia `codice_interno`,
  entrambi unici per `(emittente_fiscale_id, sorgente_tipo_id, *)`. Coerente
  con lo standard "codice operativo + codice tecnico stabile". Il piano §6.2 e
  §11.5 menzionava solo `codice`: la presenza di `codice_interno` e' una
  estensione corretta, va solo allineata la documentazione concettuale.
- `documenti.documenti_generati.uid` usa `uuidv7()` come default, in linea con
  PostgreSQL 18 e con lo standard `uid` pubblico stabile.
- L'unique progressivo sorgente usa `UNIQUE NULLS NOT DISTINCT` (PG 15+), che
  e' la soluzione robusta richiesta dal §6.5.
- La FK `generato_da_user_id -> django.auth_user(id)` e' creata in changeSet
  separato con `preConditions/tableExists`, secondo il pattern del repo
  (memoria progetto `feedback_django_refs_in_liquibase`).
- `template_documenti_versioni` e `template_asset` hanno `valido_dal`,
  `valido_al`, `validita daterange`, trigger `script.trgfn_set_validita`,
  e — per le versioni — `EXCLUDE USING gist` solo su `(attivo, stato='PUBBLICATA')`.
  Questo e' esattamente il pattern temporale standard previsto dal §4.2.
- Lo scope automazioni `documenti,*all` e' gia' registrato: l'automazione
  standard del repo (regole 1, 2, 4, 6, 7, 8 di `automation_rules_tbl.csv`)
  applichera' in modo automatico `tx_id`, audit `data_update/user_update`,
  `ATTIVO` parent/child, provisioning storico, trigger storico
  UPDATE/DELETE e `LOCK_COLUMNS` su `codice_interno`. Quindi la grande
  maggioranza dei trigger generici **non va scritta a mano**.

### 13.3 Cosa manca o e' incompleto lato DB

Le voci sotto sono ordinate per criticita' decrescente. Tutto il blocco va
chiuso prima di considerare la Fase A finita.

#### A. Guard funzionali specifiche (20_code/documenti/)

Le automazioni `*all` non coprono regole semantiche di dominio. Servono trigger
dedicati in `20_code/documenti/` (non in `00_schema/`):

A1. **Immutabilita' versione `PUBBLICATA`** — manca trigger
`trg_template_documenti_versioni_a10_protect_pubblicata_upd` che blocchi
`UPDATE OF html_template, css_template, markdown_template, render_engine_id,
formato_template, page_format, page_orientation, margin_top_mm,
margin_right_mm, margin_bottom_mm, margin_left_mm, valido_dal, valido_al,
context_schema, template_documento_id, versione` quando `OLD.stato = 'PUBBLICATA'`.
Errore via `script.fn_log_and_raise_error`.
Requisito esplicito §6.3, §11.6 e Decisione 8.

A2. **Delete block versioni protette/usate** — manca trigger
`trg_template_documenti_versioni_a10_block_delete_protected_dlt`:

- bloccare DELETE quando `stato IN ('PUBBLICATA','OBSOLETA')`;
- bloccare DELETE quando esiste almeno una riga in `documenti.documenti_generati`
  con `template_versione_id = OLD.id`.

Requisito §6.3 e §11.6.

A3. **Delete block fisico `template_asset`** — manca trigger
`trg_template_asset_a10_block_delete_dlt` che bloccia sempre il DELETE
fisico (regola "no delete fisico asset", §5.8 e §11.7).

A4. **Immutabilita' file/hash asset** — `template_asset` deve bloccare
`UPDATE OF storage_key, sha256, file_size_bytes, mime_type, file_name`. Il
piano in §6.4 dice "quando l'asset e' gia' usato"; la decisione 48
estende il vincolo anche agli asset non ancora usati ("il file non si
sostituisce: si carica un nuovo asset"). Quindi in Fase A il trigger puo'
essere semplice e bloccare l'UPDATE su quelle colonne **sempre**, senza
verificare riferimenti. Trigger:
`trg_template_asset_a10_protect_file_cols_upd`.

A5. **Delete block `documenti_generati`** — manca trigger
`trg_documenti_generati_a10_block_delete_dlt`. Tabella append-only sulla
generazione: lo stato cambia tramite `ARCHIVIATO`/`ANNULLATO`, il record non
si cancella. Requisito §6.5, §11.9 e Decisione 13.

A6. **Coerenza referenziale `documenti_generati`** — manca guard
`trg_documenti_generati_a10_check_coerenza_ins_upd`. Senza questo guard,
nulla impedisce di salvare un record con:

- `template_versione_id` che non appartiene al `template_documento_id` indicato;
- `template_documento_id.tipo_documento_output_id` diverso da
  `tipo_documento_output_id`;
- `template_documento_id.sorgente_tipo_id` diverso da `sorgente_tipo_id`;
- `template_documento_id.emittente_fiscale_id` diverso da
  `emittente_fiscale_id`.

Il `context_json` snapshot perde valore di audit se queste coerenze non
sono garantite a livello DB. Il service le rispetta, ma il DB e' la guard
finale (filosofia DB-first del repo).

A7. **Immutabilita' snapshot `documenti_generati`** — manca trigger
`trg_documenti_generati_a10_protect_snapshot_upd` che blocchi
`UPDATE OF` sui campi che rappresentano lo snapshot funzionale del
documento prodotto:

- `tipo_documento_output_id`, `template_documento_id`, `template_versione_id`;
- `sorgente_tipo_id`, `sorgente_uid`, `sorgente_riga`, `progressivo_sorgente`;
- `emittente_fiscale_id`, `generato_da_user_id`, `generato_at`;
- `context_json`, `context_hash`, `template_hash`, `pdf_hash`;
- `titolo`, `nome_file`, `uid`.

Solo `stato` e `meta` restano modificabili. Questa guard e' il
prerequisito tecnico della scelta B (disabilitazione storico): senza A7
non possiamo affidare l'immutabilita' al solo "patto col service".

A7-bis. **Immutabilita' `documenti_generati_file`** — analogo trigger
`trg_documenti_generati_file_a10_protect_file_upd` che blocchi
`UPDATE OF documento_generato_id, file_tipo_id, mime_type, file_name,
file_size_bytes, storage_key, sha256, is_principale` (per `is_principale`
si veda C). Resta modificabile solo `meta` e, in scenari Fase B,
`ordinamento` se necessario.

#### B. Storico per `documenti_generati` / `documenti_generati_file` — DECISIONE

**Decisione 2026-04-30**: disabilitare lo storico standard per
`documenti.documenti_generati` e `documenti.documenti_generati_file`.

Motivazione:

- `documenti_generati` e' di per se' una **tabella di versionamento storico**:
  ogni rigenerazione produce un nuovo record con `progressivo_sorgente` che
  cresce monotonamente (Decisione 13 e Decisione 14). La storia delle
  generazioni e' gia' codificata in piu' righe per la stessa sorgente.
- La tabella e' append-only per disegno: la guard A5 blocca DELETE e la
  guard A7 blocca UPDATE su tutti i campi snapshot. Quindi la tabella di
  storico standard registrerebbe **solo** i cambi di `stato`
  (`GENERATO`→`ARCHIVIATO`/`ANNULLATO`) e di `meta`. Valore informativo
  basso, replicando pero' un `context_json` che puo' pesare decine di KB
  per riga.
- Lo storico standard del repo replica **l'intera riga** (con tutto il
  `context_json`) ad ogni UPDATE. Per generazione = duplicazione
  garantita appena lo stato cambia. Costo elevato, beneficio nullo
  rispetto a una colonna `audit_log` minimale o a un evento applicativo.
- L'audit dei cambi di `stato` (chi ha archiviato/annullato e quando) e'
  meglio coperto dalla tabella `documenti.documenti_generati_eventi` di
  Fase B, che e' progettata proprio per questo e che salva solo i campi
  utili (`evento_tipo`, `evento_at`, `user_id`, `esito`, `messaggio`,
  `detail`) — non un duplicato dello snapshot.

Cosa serve fare:

B1. Disabilitare le regole `STORICO_PROVISION` (6) e `STORICO` (7) per
`documenti.documenti_generati` e `documenti.documenti_generati_file`.
Verificare il pattern concreto del repo per disabilitare regole `*all *all`
su tabelle specifiche: l'opzione piu' pulita e' aggiungere righe
override in `automation_rules_tbl.csv` con `target_schema='documenti'`,
`target_table='documenti_generati'` (e idem `documenti_generati_file`),
`rule_type='STORICO_PROVISION'`/`STORICO`, `enabled='f'`. Se il pattern
del repo non supporta override per disabilitazione, valutare seed in una
tabella `automation_rules_overrides` o equivalente; se non esiste,
aprire prima la convenzione DB con un changelog dedicato.

B2. **Prerequisito non negoziabile**: A7 e A7-bis devono atterrare nello
stesso commit di B1. Senza guard di immutabilita' lo "spegnimento storico"
diventa un buco di audit, non una scelta tecnica.

B3. Conferma: per `template_documenti`, `template_documenti_versioni`,
`template_asset` e per le 4 lookup, lo **storico resta attivo**. Questo
copre BOZZA modificate, asset disattivati, lookup riconfigurate, dove la
sequenza di modifiche e' realmente significativa.

B4. Per gli stati `documenti_generati.stato` valutare se serve un piccolo
log applicativo gia' in Fase A (chi e quando ha archiviato/annullato).
Opzioni:

- rinviare a Fase B con `documenti_generati_eventi` (preferito, evita
  proliferazione di soluzioni temporanee);
- aggiungere ora due colonne minimali `archiviato_at`/`archiviato_da_user_id`
  e analoghe per `ANNULLATO`. Sconsigliato: introduce duplicati che andranno
  rimossi in Fase B quando arriveranno gli eventi reali.

Raccomandazione: **rinviare a Fase B**. In Fase A si vive col solo `stato`
attuale + `data_update`/`user_update` standard.

#### C. Vincolo "un solo `PDF_FINALE`" — DECISIONE

**Decisione 2026-04-30**: aggiungere subito `is_principale boolean` su
`documenti.documenti_generati_file` + indice unico parziale, e rilassare
il vincolo unique attuale.

Stato attuale ([20260429-57](../../../../db/changelog/migrations_v2/00_schema/documenti/20260429-57-create-documenti-generati-file-mctit.yaml)):

```sql
CONSTRAINT uq_documenti_generati_file_doc_tipo
  UNIQUE (documento_generato_id, file_tipo_id)
```

In Fase A esiste solo `PDF_FINALE`, quindi e' equivalente a "un solo file per
documento". In Fase B compariranno `PDF_ALLEGATO` (multiplo per documento),
`PDF_FIRMATO`, `HTML_RENDER`: lo unique attuale si rompera'.

Modellazione scelta:

C1. Aggiungere colonna `is_principale boolean NOT NULL DEFAULT false` su
`documenti.documenti_generati_file`.

C2. Sostituire il vincolo `uq_documenti_generati_file_doc_tipo` con uno
piu' permissivo:

```sql
CONSTRAINT uq_documenti_generati_file_doc_tipo_ord
  UNIQUE (documento_generato_id, file_tipo_id, ordinamento)
```

C3. Aggiungere indice unico parziale "un solo principale per documento":

```sql
CREATE UNIQUE INDEX uq_documenti_generati_file_principale
  ON documenti.documenti_generati_file (documento_generato_id)
  WHERE is_principale IS TRUE;
```

C4. In Fase A il service marca a `true` il `PDF_FINALE` (unico file
prodotto). In Fase B la stessa colonna distinguera' il file principale dai
file accessori. Nessuna migrazione dati dolorosa quando si aggiungera'
`PDF_ALLEGATO`/`PDF_FIRMATO`.

C5. La guard A7-bis (immutabilita' file) include `is_principale` tra le
colonne bloccate in UPDATE: il "file principale" e' definito al momento
della generazione e non cambia in seguito.

Implementazione:

- se 20260429-57 non e' ancora pushato sul remoto pubblico, modificare
  direttamente quel file aggiungendo la colonna, sostituendo il vincolo e
  aggiungendo l'indice;
- se 20260429-57 e' gia' pushato, creare un changeset additivo
  `20260430-NN-add-is-principale-documenti-generati-file-mctit.yaml` con:
  `ADD COLUMN is_principale ... NOT NULL DEFAULT false`,
  `DROP CONSTRAINT uq_documenti_generati_file_doc_tipo`,
  `ADD CONSTRAINT uq_documenti_generati_file_doc_tipo_ord ...`,
  `CREATE UNIQUE INDEX uq_documenti_generati_file_principale ...`.

Verificare lo stato del remoto prima di scegliere.

#### D. Whitelist lookup generica (Python)

`apps/core/db/dbops_repository.py` espone `_REL_CONSENTITE` come whitelist
delle tabelle accessibili tramite `fn_get_lookup_codici`. Le 4 lookup
documenti **non** sono presenti.

Va aggiunto:

- `documenti.tipi_documento_output`
- `documenti.tipi_asset_documento`
- `documenti.tipi_file_documento`
- `documenti.render_engine_documento`

Tecnicamente e' lavoro backend (PR2), ma e' una dipendenza del DB perche'
senza questa modifica le lookup atterrate non sono raggiungibili dall'API
generica. Va segnalato esplicitamente come blocker della prima slice end-to-end.

#### E. Check minori sul DDL gia' atterrato

E1. `template_documenti.file_name_pattern text NULL` — manca `CHECK
(file_name_pattern IS NULL OR btrim(file_name_pattern) <> '')`. Coerenza con
gli altri non-vuoti.

E2. `template_documenti_versioni.context_schema jsonb` — manca
`CHECK (jsonb_typeof(context_schema) = 'object')` per evitare scalari/array.
Stessa cosa potrebbe valere per `meta` e `detail` ovunque presenti, da
verificare se e' applicato dall'automazione standard del repo.

E3. `template_documenti_versioni.html_template text NOT NULL` — manca
`CHECK (btrim(html_template) <> '')`. Una versione con HTML vuoto non e'
mai una versione utile.

E4. `documenti_generati.context_json` — manca
`CHECK (jsonb_typeof(context_json) = 'object')`. Lo snapshot funzionale e'
sempre un oggetto.

E5. `documenti_generati_file.ordinamento integer NOT NULL DEFAULT 1` —
ottimo, ma per la Fase A col solo `PDF_FINALE` il `DEFAULT 1` e' di fatto
forzato. In Fase B con piu' file diventa significativo. Niente da
cambiare ora, e' un "ricordare in Fase B".

#### F. Test pgTAP (Step 9 della Fase A)

Tutto da scrivere, in `db/pgtap/documenti/`:

- creazione schema e tabelle base;
- unique `codice` e `codice_interno` sulle 4 lookup + lock `codice_interno`
  (verifica che l'automazione `LOCK_COLUMNS` abbia generato il trigger);
- default unico template attivo per `(tipo_documento_output_id,
  sorgente_tipo_id, emittente_fiscale_id)` — testare che due `is_default=true`
  attivi sulla stessa tripla siano rifiutati;
- anti-overlap versioni `PUBBLICATA` (EXCLUDE gist);
- immutabilita' versione `PUBBLICATA` (richiede A1 prima);
- delete block versione protetta (richiede A2 prima);
- deduplica asset per `(emittente_fiscale_id, sha256)`;
- delete block asset (richiede A3 prima);
- lock colonne file asset (richiede A4 prima);
- delete block documenti generati (richiede A5 prima);
- coerenza referenziale documenti generati (richiede A6 prima);
- immutabilita' snapshot `documenti_generati` (richiede A7 prima):
  tentativo di UPDATE su `context_json`, `*_hash`, riferimenti template
  o sorgente deve fallire;
- immutabilita' file `documenti_generati_file` (richiede A7-bis prima):
  tentativo di UPDATE su `storage_key`, `sha256`, `is_principale`,
  `file_size_bytes`, `mime_type`, `file_name` deve fallire;
- assenza tabella storico per `documenti_generati` e
  `documenti_generati_file` (verifica B1: il provisioning standard non ha
  creato `storico.documenti_generati_*`);
- unique progressivo sorgente con `sorgente_riga NULL` (NULLS NOT DISTINCT);
- un solo file `is_principale = true` per `documento_generato_id` (C3);
- unique `(documento_generato_id, file_tipo_id, ordinamento)` permette
  piu' righe stesso `file_tipo_id` con `ordinamento` distinto (C2);
- seed lookup idempotenti (`runOnChange: true` rilanciato non duplica);
- seed parametri `config.parameters` idempotenti.

I test seguono il pattern del repo
(memoria progetto `feedback_pgtap_patterns`):
`BEGIN; ... ROLLBACK;`, codici fiscali validi fissi per fixture soggetti, no
collisioni UNIQUE con seed/migrazioni.

#### G. Documentazione concettuale manuale

In `docs/it/dbzero/documenti/manual/` esistono gia' i file md per le 9
tabelle previste in Fase A: stato sconosciuto (probabilmente vuoti o stub).
Vanno popolati con almeno scopo, contesto, regole DB, dipendenze. Le doc
auto-generate `tabelle/`, `viste/`, `funzioni/` arriveranno con il
prossimo run del generatore, non vanno toccate a mano.

### 13.4 Ordine consigliato per chiudere la Fase A

Ordine pensato per minimizzare i conflitti tra DDL, guard e test, e per non
lasciare la base in stati intermedi pericolosi (es. "no storico" senza
ancora la guard di immutabilita').

1. **C — `is_principale` su `documenti_generati_file`**. Prima i dati,
   prima del nullable e dei vincoli. Modifica in-place del 20260429-57 se
   non pushato, altrimenti nuovo changeset additivo `20260430-NN-...`.
   Operazioni SQL elencate in §13.3 punto C.

2. **E — check minori sul DDL** in un singolo changeset
   `20260430-NN-add-checks-documenti-mctit.yaml` in
   `00_schema/documenti/`. Include E1..E4: non-vuoto su
   `file_name_pattern` e `html_template`, `jsonb_typeof = 'object'` su
   `context_schema`, `context_json`, e dove serve su `meta` (verificare se
   il pattern del repo lo applica gia' via automazione).

3. **A1..A7 + A7-bis — guard** in `20_code/documenti/`, una funzione
   `trgfn_*` + un `CREATE TRIGGER` per ciascuna regola. Naming
   `trg_<tabella>_a10_<descrizione>_<eventi>` per guard fail-fast (vedi
   `linee-guida-trigger.md`). Errori via `script.fn_log_and_raise_error`
   con codici stabili (es. `E_DOCUMENTI_VERSIONE_PUBBLICATA_IMMUTABILE`,
   `E_DOCUMENTI_ASSET_DELETE_BLOCKED`,
   `E_DOCUMENTI_GENERATO_SNAPSHOT_IMMUTABILE`,
   `E_DOCUMENTI_GENERATO_COERENZA`).

4. **B — disabilitazione storico** per `documenti_generati` e
   `documenti_generati_file`. Va rilasciata **dopo** A7/A7-bis nello
   stesso PR, mai prima: senza A7 lo "spegnimento storico" e' un buco di
   audit. Verificare il pattern repo per override regole `*all *all` su
   tabelle specifiche.

5. **F — test pgTAP** in `db/pgtap/documenti/`, scritti nello stesso
   commit della guard relativa
   (memoria progetto `feedback_guard_breaks_existing_tests`).
   Ordine pratico: prima i test che non dipendono dalle guard
   (deduplica sha256, default unico, anti-overlap, NULLS NOT DISTINCT,
   indice principale), poi i test delle guard man mano che atterrano.

6. **D — whitelist `_REL_CONSENTITE`** in
   `apps/core/db/dbops_repository.py` (PR2 backend). Senza questo step la
   lookup generica non vede le 4 lookup di `documenti`. Lo segnaliamo come
   dipendenza esplicita PR1 DB → PR2 BE.

7. **G — popolare i manual md** in `docs/it/dbzero/documenti/manual/`,
   secondo lo standard scopo/contesto/regole/dipendenze. Puo' avvenire in
   parallelo al resto.

Punto critico cross-step: ogni nuovo changelog file aggiunto **dopo** un
push pubblico va numerato successivo all'ultimo (`20260430-NN-...`), mai
modificare i 51-59 se gia' su remoto. Vedi la memoria progetto
`feedback_liquibase_phase_ordering_preconditions`.

### 13.5 Note di metodo

- Le guard A1..A6 vanno in `20_code/documenti/`, **non** in `00_schema/`:
  contengono codice (funzioni e trigger), e l'autogen del master changelog
  separa fasi DDL e fasi codice.
- Il `logicalFilePath` dei nuovi changeset deve combaciare col path reale
  (vedi `liquibase-setup-workflow.md`).
- Niente modifiche ai changeset 51-59 se sono gia' stati pushati su
  `dev/db-tid` o oltre: aggiungere sempre un nuovo file con numerazione
  successiva (regola memoria progetto
  `feedback_pg_returns_table_drop_required`
  per i drop-and-recreate vale solo per cambi di firma; qui parliamo di
  immutabilita' del file gia' pushato).
- Le guard dovrebbero usare `script.fn_log_and_raise_error` con codice
  errore stabile (es. `E_DOCUMENTI_VERSIONE_PUBBLICATA_IMMUTABILE`,
  `E_DOCUMENTI_ASSET_DELETE_BLOCKED`) cosi' da poter mappare a
  `error_policies.py` lato backend.
