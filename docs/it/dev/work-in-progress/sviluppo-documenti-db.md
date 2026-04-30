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
