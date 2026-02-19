# Fatturazione - attivita di progetto (WIP)

> Documento di lavoro per pianificazione e avanzamento attivita. Contiene appendici e note operative.
> La guida principale resta `docs/it/guide/fatturazione.md`.

---

## ✅ Recap stato (sintesi)

- [x] Pipeline fatturazione su `vendite.fatturazione_pipeline` con fallback `utility_id`/`tipo_doc_fiscale_id`.
- [x] Orchestrazione Django (`pr_run_lotto_pipeline`, `fn_execute_pipeline_step`).
- [x] Registry task multi-dominio in DB (`dbops.domini_task`, `dbops.pipeline_task_registry`, `dbops.pipeline_task_registry_impl`).
- [x] `implementation_key` nei task JSON e dispatch via registry DB.
- [x] Log fatture e flag `critical` (tabella `vendite.fatture_log` + sync).
- [x] Area geografica fatturazione e colonne correlate.
- [x] Chiusura operativa lotto guidata da flag `config.stati_doc_fiscale.chiude_lotto` a fine step.
- [x] Numerazione spostata a step `DEFINITIVA` (pipeline massiva); `EMESSA` resta pre-fiscale/riapribile.
- [x] Reset tecnico modellato in pipeline (`rollback` step `EMESSA`) solo per `MASSIVO`.
- [x] Step `EMESSA` massivo configurato con task minimi/fondi + ricalcolo IVA/totali.
- [x] Step `INVIATA` massivo configurato con preparazione payload SDI su lotto.
- [x] Processo Python per reperire payload SDI da lotto (`fn_prepare_sdi_payload_lotto`).
- [ ] Generazione file invio SDI (builder XML/metadata) da payload lotto.
- [ ] Persistenza esito generazione file su `vendite.fatture_sdi` (`nome_file` + meta output).
- [ ] Registrazione eventi file su `vendite.fatture_sdi_eventi` (es. `FILE_GENERATO`).
- [ ] Processo di invio canale SDI e aggiornamento `data_invio`/esiti ricezione.
- [x] Refactor fondi fattura su contabili/righe (`fn_sync_contabili_fondo_fattura`) con deprecazione wrapper legacy.
- [x] Refactor saldi: `fn_get_saldo_fattura` come residuo documento.
- [x] Introduzione saldo contabile postabile (`fn_get_saldo_fattura_contabili`) per evitare doppie inclusioni.
- [x] Aggiornamento sync/generazione fondi su saldo effettivo (residuo - contabile postabile).
- [x] Modello compensazioni spostato su `pagamenti.vendite_contabili.compensazione_id`.
- [x] Blocco link lotto su testate di compensazione (guard su `vendite_contabili_lotti`).
- [x] Guida tecnica pagamenti creata (`docs/it/guide/pagamenti.md`).
- [x] Pipeline dedicata per `attivita_fatturabili` (tabella + funzioni resolve/list).
- [ ] Pipeline `attivita_fatturabili`: completamento log/runner/handler dominio.
- [ ] Registry runtime multi-dominio completo in Django (mappa per dominio).
- [x] Resume `DEFINITIVA` a livello fattura (ripartenza da errore senza reset globale).
- [x] Policy rerun `MASSIVO` nel runner Django: resume dallo step corrente + rollback step opzionale con `meta.auto_step_rollback=true` (skip rollback distruttivi in auto-run).
- [x] Seed transizioni `config.stati_doc_fiscale_transizioni` allineato agli step lotto (incluso `MASSIVO` 8 -> 3).

## ✅ Recap operativo pipeline fatturazione (DB + Django)

- [x] Runner Django in produzione logica pipeline (`LottoPipelineRunner` + `PipelineStepExecutor`).
- [x] Config pipeline DB allineata agli step `DRAFT` -> `EMESSA` -> `DEFINITIVA`.
- [x] Step `EMESSA` massivo con task fondi/IVA e chiusure operative coerenti.
- [x] Policy rerun `MASSIVO` in errore: resume dallo step corrente.
- [x] Rollback step opzionale (`meta.auto_step_rollback=true`) con guard su rollback distruttivi.
- [x] `DEFINITIVA` in modalita resume (no reset globale lotto).
- [x] Error envelope + idempotency API centralizzati e allineati al flusso.
- [x] Test unit runner aggiornati e verdi (`apps.vendite.tests.services.test_pipeline_runner`).

## 🛣️ Roadmap runtime task/stato_lotto (nuova)

Obiettivo: rendere esplicita la gestione runtime per task, mantenendo `stato_lotto`
come stato tecnico di esecuzione e `stato_operativo` come stato business del lotto.

### Decisioni confermate

- [x] Chiusura lotto solo via flag `config.stati_doc_fiscale.chiude_lotto` a fine step.
- [x] Nessuna chiusura hardcoded su stato specifico.
- [x] In errore step/task: stop del flusso e blocco task successivi nello stesso run.
- [x] Annulla/reset gestiti fuori dal flusso di avanzamento standard.

### Sviluppi DB da introdurre

- [x] `vendite.fatturazione_pipeline_task_policy`
  - policy task per pipeline (`annullabile`, strategia resume/reset, metadati operativi).
- [x] `vendite.fatturazione_lotti_task_runs`
  - traccia runtime per task (start/end, esito, tentativo, errore, contesto step/lotto).

### Sviluppi Django successivi

- [x] runner aggiornato per leggere policy task da DB prima dell'esecuzione.
- [x] gestione resume/reset per task in base alla policy (`annullabile`, `resume_mode`).
- [x] blocco rilancio task quando policy non consente retry automatico.

### Criteri di completamento roadmap

- [x] policy task applicata in runtime su almeno i task DRAFT/EMESSA/DEFINITIVA.
- [x] tracing task consultabile da API/log dominio senza parsing del solo `error_log`.
- [ ] test pgtap + test service Django verdi su flussi: ok, errore task, resume/reset.
  - Django/API verdi; pgtap runtime da rieseguire in ambiente con `internal.env` disponibile.

### Stato SDI (dettaglio operativo)

Gia` implementato:

* `vendite.fn_prepare_sdi_payload(...)` (DB): prepara/riusa tentativi SDI per fatture del lotto.
* task pipeline `prepare_sdi_payload_lotto` (Django): invoca funzione DB e reperisce dataset strutturato.
* facade applicativa `fn_prepare_sdi_payload_lotto` (Django): riuso anche fuori pipeline.

Da implementare (step successivi):

* builder file SDI (XML/metadata) a partire dal payload.
* persistenza nome/percorso file su `vendite.fatture_sdi`.
* evento applicativo su `vendite.fatture_sdi_eventi` (`FILE_GENERATO` e successivi).
* step invio canale SDI con gestione esiti (accettazione/scarto/consegna).

## ✅ Go-live checklist tecnica (stato)

- [x] Seed transizioni lotto coerente con step pipeline (evitati duplicati logici su `8 -> 3`).
- [x] Seed registry task/implementation coerente con task JSON pipeline.
- [x] Documentazione guida + WIP riallineata al comportamento reale runner.
- [x] Consolidare checklist test finale unica (pgtap + Django + smoke API end-to-end).
- [ ] Estendere stesso pattern a pipeline `attivita_fatturabili` (runner/handler/test).

## 🚦 Test gravita disallineamenti (guida vs WIP)

Riferimento confronto:

* `docs/it/guide/fatturazione.md`
* `docs/it/dev/work-in-progress/fatturazione-attivita-progetto.md`
* `docs/it/dev/work-in-progress/pipeline-domini-engine.md`

Esito sintetico:

* **ALTA**: 1 area
* **MEDIA**: 3 aree
* **BASSA**: 2 aree

### Alta gravita

* **Pipeline `attivita_fatturabili` non ancora attiva**
  * Impatto: blocca la chiusura completa del disegno end-to-end (alimentazione -> fatturazione) in modalita pipeline uniforme.
  * Azione: introdurre tabella/funzioni pipeline dominio attivita e relativo pacchetto test.
  * Stato: **aperta**.

### Media gravita

* **Registry runtime Python multi-dominio non completato**
  * Impatto: il modello e` pronto lato DB ma non ancora esteso a tutti i domini futuri.
  * Azione: completare mappa runtime per dominio e validazione pre-run unificata.
  * Stato: **aperta**.

* **Checklist test finale non unificata**
  * Impatto: bassa visibilita` di regressione globale tra pgtap e test Django.
  * Azione: creare una sezione unica “go-live checklist” con test minimi obbligatori.
  * Stato: **chiusa** (sezione unica introdotta in questo documento).

* **Contenuti guida/WIP parzialmente duplicati**
  * Impatto: rischio drift documentale su sezioni operative lunghe replicate.
  * Azione: mantenere in WIP solo stato lavori/checklist e lasciare i dettagli di processo nella guida.
  * Stato: **in rifinitura**.

### Bassa gravita

* **Terminologia mista in alcune sezioni WIP**
  * Impatto: solo leggibilita`.
  * Azione: uniformare lessico su “lotto massivo/giornaliero”, “contabile”, “source fondi”.
  * Stato: **pianificata**.

* **Promemoria tecnici sparsi**
  * Impatto: nessun blocco funzionale, ma minore tracciabilita`.
  * Azione: concentrare i TODO residui in checklist finale.
  * Stato: **pianificata**.

## ✅ Attivita chiuse (formalizzazione)

Le seguenti attivita sono considerate **chiuse** e allineate con la guida principale:

* [x] Pipeline fatturazione configurabile (`vendite.fatturazione_pipeline`) con fallback.
* [x] Orchestrazione spostata in Django (runner/step executor).
* [x] Registry task DB multi-dominio introdotto (`dbops.*`).
* [x] Dispatch con `implementation_key` e binding controllato.
* [x] Gestione log fatture e allineamento flag `critical`.
* [x] Chiusura operativa lotto a fine step guidata da `chiude_lotto` (senza task dedicato).
* [x] Refactor fondi fattura verso contabili/righe.
* [x] Refactor saldo fattura (residuo documento) + saldo contabile postabile.
* [x] Compensazioni agganciate a testata contabile.
* [x] Guida pagamenti pubblicata e coerente col modello contabile.

Nota:
le chiusure sopra restano valide salvo refactor strutturali successivi.


***Fine test gravità***


### Stato documenti WIP (allineamento)

* [x] `pipeline-domini-engine.md` riallineato su scelta: pipeline DB per dominio + registry condiviso
* [x] `fatturazione-attivita-progetto.md` aggiornato con avanzamento su fondi/contabili/saldi
* [x] Guida `fatturazione.md` integrata con sezione minimi/fondi fattura
* [x] Guida `pagamenti.md` introdotta con dashboard (WIP) e vincoli architetturali
* [x] Consolidare checklist test finali (pgtap + Django) in sezione unica di chiusura

### ✅ Checklist finale unificata (DB + Django + API)

#### 1) Test DB / pgtap (SQL)

* [x] Eseguiti test pgtap SQL principali del dominio fatturazione/pagamenti.
* [x] Nessun errore bloccante su migrazioni/funzioni SQL coinvolte nel flusso.

Comando base:

```bash
scripts/testpgtap.sh db/pgtap/<schema>/<test-file>.sql
```

#### 2) Test Django services

* [x] Eseguire suite servizi pipeline:
  * [x] `apps.vendite.tests.services.test_pipeline_runner`
  * [x] `apps.vendite.tests.services.test_pipeline_step_executor`
* [x] Eseguire suite servizi reset/lotto/fattura.

Comando base:

```bash
./manage-test.sh apps.vendite.tests.services -v 2
```

#### 3) Test API

* [x] Eseguire test API pipeline/reset:
  * [x] `apps.vendite.tests.api.test_pipeline_api`
  * [x] `apps.vendite.tests.api.test_reset_lotto_draft_api`
  * [x] `apps.vendite.tests.api.test_reset_lotto_fattura_draft_api`
* [x] Verificare idempotency + envelope errori.

Comando base:

```bash
./manage-test.sh apps.vendite.tests.api -v 2
```

#### 4) Smoke end-to-end (manuale)

* [ ] Avvio pipeline lotto (`MASSIVO`/`GIORNALIERO`) da API.
* [ ] Verifica avanzamento step/fase nei log lotto.
* [ ] Verifica routing errori su `error_log` + log dominio (`fatture_log`/`fatturazione_lotti_log`).

#### 5) Criteri di chiusura

* [ ] Tutti i test DB + Django + API verdi.
* [ ] Nessun errore tecnico non sanitizzato in response pubblica.
* [ ] Tracciabilita` completa request/log (request_id, scope, severity, code).
* [ ] Chiusura checklist con data e commit SHA.

## 📌 Promemoria saldi (da formalizzare)

- Saldo **contabile ufficiale** fattura: calcolato solo da `pagamenti.vendite_movimenti` (postati).
- `pagamenti.vendite_contabili` / `pagamenti.vendite_contabili_righe` restano area pre-posting (working).
- Mapping stati contabili concordato:
  - `VALIDATA` = pronta al posting
  - `CHIUSA` = postata
- Reset fatturazione ammesso finche` la contabile collegata non e` `CHIUSA`.
- Valutare una vista/endpoint separato per saldo previsionale (include contabili non postate), distinto dal saldo ufficiale.

## 🔁 Note migrazione DB -> Django (parti trasferite)

Queste logiche sono state trasferite da funzioni SQL a servizi Django:

* orchestrazione pipeline lotto (ex `vendite.pr_run_lotto_pipeline`)
  * ora in `apps/vendite/services/pipeline_runner.py`
* esecuzione step pipeline (ex `vendite.fn_execute_pipeline_step`)
  * ora in `apps/vendite/services/pipeline_step_executor.py`
* grouping e generazione righe fattura (ex `vendite.fn_group_attivita_fatturabili`, `vendite.fn_generate_fatture_righe`)
  * ora in `apps/vendite/services/fatture_righe_service.py`

Regole chiave:

* il DB resta fonte di verita` per configurazione pipeline e fallback.
* il dispatch e` controllato da registry DB + mapping statico in Django.
* vincoli, trigger e funzioni di consistenza restano in DB.

## 📌 Generazione fatture puntuali (lotti giornalieri)

### Scopo
Gestire emissioni immediate (front-office) senza attendere il ciclo massivo,
ma mantenendo la tracciabilita` tramite lotto giornaliero.

### Modello operativo

* Il **lotto giornaliero** e` un contenitore operativo, non il driver di emissione.
* Le fatture vengono **create/emesse per documento** (processo puntuale).
* Il lotto resta **APERTO** e raccoglie le fatture emesse nella giornata.
* La chiusura operativa lotto e` **parametrica**: avviene a fine step solo se
  `config.stati_doc_fiscale.chiude_lotto = true`.

### Impatti su pipeline e guard

* La pipeline `GIORNALIERO` non deve includere step di creazione/emissione.
* Il trigger `trgfn_fatturazione_lotti_guard_stato` non viene sollecitato
  per la fase EMESSA, perche` il lotto non transita in EMESSA.
* Nessuna chiusura hardcoded su stato specifico (es. `INVIATA`):
  vale solo la regola `chiude_lotto`.

### Processo puntuale (fuori pipeline)

* Deve riusare **gli stessi servizi/primitive** del massivo:
  `select_attivita` (lock), `get_or_create_fattura_header`,
  `generate_fatture_righe`, `fn_numera_fattura_opz_emessa`.
* Deve garantire **idempotenza** e **lock** sul lotto giornaliero.
* Deve loggare su `fatturazione_lotti_log` per tracciabilita`.
* Deve agganciare sempre la fattura al lotto giornaliero aperto.

### Nota di coerenza

Il flusso puntuale non duplica logica: usa le stesse funzioni/servizi,
ma senza passare dalla pipeline lotto.

### Sviluppi necessari (minimo)

* Servizio Django “emissione immediata”:
  * risolve/crea lotto giornaliero APERTO
  * seleziona/locka attivita fatturabili
  * genera righe e numerazione documento
  * collega fattura al lotto
  * logga su `fatturazione_lotti_log`
* Pipeline giornaliera ridotta ai soli task batch (chiusura/invio)
* Chiusura batch guidata da `config.stati_doc_fiscale.chiude_lotto` a fine step
* Endpoint API dedicato (o estensione dell’endpoint esistente)

---

## 1) Processo di alimentazione `attivita_fatturabili`

### 🎯 Scopo
Creare le righe pre‑documentali che rappresentano **tutto cio` che potra` essere fatturato**.

### 🔌 Sorgenti (macro‑tipi)
Le sorgenti sono definite in `config.sorgenti` e rappresentano **origini dati** eterogenee. Esempio:

1. ATTIVITA (RIGA)  
2. PREVENTIVO (DOCUMENTO)  
3. PREVENTIVO_RIGA (RIGA)  
4. CONTRATTO (DOCUMENTO)  
5. CONTRATTO_RIGA (RIGA)  
6. ORDINE_VENDITA (DOCUMENTO)  
7. ORDINE_VENDITA_RIGA (RIGA)  
8. DDT_VENDITA (DOCUMENTO)  
9. DDT_VENDITA_RIGA (RIGA)  
10. FATTURA (DOCUMENTO)  
11. FATTURA_RIGA (RIGA)

### 🧩 Logica di alimentazione
* Ogni sorgente genera righe in `vendite.attivita_fatturabili` con:
  `sorgente_tipo_id`, `sorgente_uid`/`sorgente_riga`, `articolo_id`, `istanza_utility_id`, `quantita`, `competenza_*`.
* L’idempotenza e` garantita dalla coppia `(sorgente_tipo_id, sorgente_uid)` con indice unico parziale.
* Le righe nascono **in bozza** (`approvato = false`) e vengono validate/approvate nel passaggio successivo.

### 🖥️ Dashboard “Input Fatturazione”
* Selezione sorgenti e intervalli (periodo, BA, istanza, utility).
* Visualizzazione righe candidate e preview dei conteggi.
* Avvio del processo di alimentazione (batch o manuale).

**Integrazione utilities (gas/energia/acqua)**  
Non tutte le sorgenti possono alimentare direttamente `attivita_fatturabili`:
nei casi utilities serve un **processo di calcolo preliminare** dei consumi.
La dashboard “Input” deve quindi gestire due flussi:

1) **Alimentazione diretta** → inserimento righe `attivita_fatturabili` da sorgenti semplici.  
2) **Alimentazione con calcolo** → generazione di `attivita_consumi` (testata consumi),
   log dedicato e successiva produzione di righe `attivita_fatturabili`.

Il processo di alimentazione avviene **prima** del lotto fatture e mantiene tracciabilita`
tramite `attivita_fatturabili_lotti`.

---

## 2) Processo operativo di calcolo (pre‑emissione)

### 🎯 Scopo
Trasformare attivita` approvate e fatturabili in **righe economiche** di fattura.

### 🔎 Selezione
* `approvato = true`
* `fatturato = false`
* `sospesa = false`
* `posticipa_al` in regola con la data fatturazione
* competenza mensile/puntuale in regola

### 🔒 Isolamento batch
* `lock_in_fatturazione` e `lock_batch_id` garantiscono coerenza di selezione.
* Evita doppie estrazioni concorrenti.

### 🧮 Output
* Generazione `vendite.fatture_righe` con snapshot economici (prezzo, IVA, UoM, importi).
* Aggancio a `vendite.attivita_fatturabili` (`fattura_riga_id`, `fatturato = true`).

### 🖥️ Dashboard “Pre‑Calcolo”
* Visualizzazione delle righe eleggibili e motivi di esclusione.
* Azioni: approva/sospendi/posticipa.
* Lancio calcolo batch con log esiti e anomalie.

---

## 3) Processo di emissione documento (output)

### 🎯 Scopo
Convertire il risultato del calcolo in **documento fiscale numerato**.

### ✅ Separazione dal calcolo
Il **calcolo** produce righe; l’**emissione** produce la testata, la numerazione e gli output fiscali.

### 🔢 Numerazione
* Assegnata **solo** in fase di emissione (cambio di stato).
* Regole gestite da `vendite.registri_fatturazione`.

### 📦 Output correlati
* `vendite.fatture_riepiloghi_iva`
* `vendite.fatture_scadenze`
* `vendite.note` (e partizioni dedicate)
* `vendite.fatture_indirizzi` (se previsto)

### 🖥️ Dashboard “Emissione”
* Preview del documento, controlli finali e numerazione.
* Conferma emissione con log degli esiti.

---

## 4) Dashboard e varianti operative

### ✅ Dashboard standard
* **Input Fatturazione** → alimenta `attivita_fatturabili`
* **Pre‑Calcolo** → selezione, approvazione, calcolo righe
* **Emissione** → numerazione e creazione documento

### 🔁 Variante: invio SDI (Italia)
* **Estrazione** del documento in formato fiscale (es. XML FatturaPA).
* **Invio** a canali SDI e registrazione esiti (accettato/scartato).
* **Nota di variante**: in altri paesi si sostituisce il canale SDI con sistemi locali o e‑invoicing alternativi.

### 📊 Variante: controlli e statistiche
* **Pre‑emissione**: controlli di anomalia (importi negativi, IVA mancante, competenze fuori periodo, mismatch BA/istanza).
* **Post‑emissione**: riepiloghi fiscali e gestionali:
  * per gruppi voce / articoli
  * per utility / BA / periodo
  * per stato documento (bozza, emessa, annullata)

---

## 🧠 Linee guida di progettazione

1. **Separare sempre calcolo vs emissione**  
   Il calcolo e` idempotente e ripetibile; l’emissione e` un’azione fiscale “finale”.

2. **Dashboard come orchestratore**  
   Il motore batch deve essere avviato da contesto visibile e controllato (input + pre‑calcolo + emissione).

3. **Idempotenza garantita dalle sorgenti**  
   Le sorgenti alimentano `attivita_fatturabili` evitando duplicazioni con chiavi uniche parziali.

4. **Audit e log sempre presenti**  
   Ogni fase deve loggare esiti, scarti, errori e motivi di esclusione.

---

## ✅ Risultato atteso

Un processo fatturazione **modulare**, verificabile e scalabile:

* sorgenti ingegnerizzate → `attivita_fatturabili`
* calcolo controllato → `fatture_righe`
* emissione separata → `fatture` numerate
* dashboard e output fiscali governati

---

## 🧩 Collegamenti tabellari (visione sintetica)

```mermaid
flowchart TD
  subgraph INPUT["Sorgenti (input)"]
    PREV["vendite.preventivi"]
    PREVR["vendite.preventivi_righe"]
    CONT["vendite.contratti"]
    CONTR["vendite.contratti_righe"]
    ORD["vendite.ordini"]
    ORDR["vendite.ordini_righe"]
    DDT["vendite.ddt"]
    DDTR["vendite.ddt_righe"]
  end

  AF["vendite.attivita_fatturabili"]

  subgraph OUTPUT["Output (documenti)"]
    FR["vendite.fatture_righe"]
    F["vendite.fatture"]
  end

  PREV --> AF
  PREVR --> AF
  CONT --> AF
  CONTR --> AF
  ORD --> AF
  ORDR --> AF
  DDT --> AF
  DDTR --> AF

  AF --> FR
  FR --> F
```

---

## 📌 Attivita` da introdurre – Fondi fattura (WIP)

### Scopo
Separare i **fondi fattura** dalle righe standard per garantire semantica corretta,
tracciabilita` verso documenti precedenti e calcolo deterministico del totale a pagare.

### Modello proposto

**Nuove tabelle:**

* `vendite.tipi_fondi_fattura`
  * `id`, `codice`, `codice_interno`, `descrizione`, `meta`, audit
* `vendite.fatture_fondi_fattura`
  * `id`, `fattura_id`, `riferimento_fattura_id`, `tipo_fondo_fattura_id`, `importo`, `meta`, audit

**Modifiche a `vendite.fatture`:**

* `totale_doc` resta: `imponibile_tot + imposta_tot`
* introdurre `totale_a_pagare` (totale fiscale + arrotondamenti + fondi)
* rimuovere `totale_escluso_imponibile` (sostituito dalla somma fondi)

**Modifiche a `catalogo.articoli`:**

* rimuovere `fondo_fattura` (non piu` coerente come flag articolo)

### Impatti su logica Django

* Il processo di generazione righe **non** deve creare fondi fattura.
* I fondi fattura vanno gestiti da **servizio dedicato** (API o batch).
* Il ricalcolo totali deve includere `SUM(fatture_fondi_fattura.importo)`.

### Note operative

* Nessuna migrazione dati (al momento non esistono righe fondo fattura).
* Aggiornare `fn_ricalcola_totali_fattura` e test pgtap relativi.

---

## 📌 Analisi fondi fattura – processo e regole (WIP)

### Problema da risolvere

I fondi fattura non sono righe di vendita. Sono addebiti/accrediti extra
(minimi fatturati, canone RAI, recuperi precedenti) e richiedono:

* tracciabilita` verso fattura origine
* idempotenza (niente riaddebiti)
* gestione storni/riaperture

### Separazione necessaria

1) **Sorgente fondo**: credito/debito originario da fattura precedente.  
2) **Fondo applicato**: addebito collegato alla fattura corrente.

### Tabella sorgente (core logico)

`vendite.fatture_fondi_fattura_source`:

* `fattura_sorgente_id`
* `tipo_fondo_fattura_id`
* `importo`
* `stato`: `DISPONIBILE` | `ASSEGNATO` | `ANNULLATO`
* `fattura_figlia_id`, `data_assegnazione`, `user_assegnazione`
* denormalizzazioni: `billing_account_id`, `utility_id`, `tipo_doc_fiscale_id`,
  `emittente_soggetto_ruolo_id`, `valuta_id`

### Processo 1: Generazione source

* seleziona fatture con `minimo = true`
* esclude fatture gia` presenti in `source`
* esclude fatture pagate (regola a definire su pagamenti)
* inserisce record `DISPONIBILE`

### Processo 2: Applicazione su fattura

* seleziona record `DISPONIBILE` per chiave BA+utility+tipo_doc+emittente+valuta
* crea record in `fatture_fondi_fattura`
* aggiorna source `ASSEGNATO` e collega la `fattura_figlia_id`

### Storni / note credito

Policy per tipologia fondo:

* default `riapribile = false`
* se `riapribile = true` e arriva storno, lo source torna `DISPONIBILE`

### Pagamenti

Serve tabella movimenti:

* `pagamenti.vendite_movimenti`
* `SUM(importo) >= totale_a_pagare` come regola base di “pagata”

### Totali fattura

* `totale_doc = imponibile + imposta`
* `totale_a_pagare = totale_doc + arrotondamenti + SUM(fondi)`


## 📎 Appendice – Lotto, raggruppamenti e stati (design operativo)

> **Nota importante (evidenza):**
> `area_geografica_id` restera` **solo** un filtro geografico.
> In futuro i raggruppamenti multi‑criterio (comuni + tipologia utenza + contratti, ecc.)
> saranno gestiti con un **nuovo livello** (`gruppo_fatturazione_id`), per evitare
> ambiguita` semantiche e mantenere la compatibilita` con l’attuale modello.

### 1) Lotto di fatturazione

Il **lotto** diventa l’elemento centrale per:

* ricalcolo controllato,
* tracciabilita` dei job,
* orchestrazione dei processi successivi (emissione, invio, statistiche).

**Campi proposti (minimi)**:

* `id` (bigint, PK)
* `uuid` (lock_batch_id)
* `codice` (es. LOT-YYYYMM-NN)
* `competenza_mese` (date, YYYY-MM-01)
* `utility_id` (opzionale, derivabile da BA)
* `tipo_doc_fiscale_id` (**obbligatorio**)
* `billing_account_id` (opzionale)
* `stato_lotto` (IN_ESECUZIONE | COMPLETATO | ERRORE)
* `stato_doc_fiscale_id` (FK -> `config.stati_doc_fiscale`)
* audit + `meta`

> Nota: `tipo_doc_fiscale_id` e` obbligatorio; `utility_id` puo` essere derivato da `billing_account_id`.
> Lo stato del lotto segue un **ordine** e supporta `stato_precedente_ammesso` per eventuali rollback.

**Rollback DRAFT (lotto MASSIVO)**  
Consentito solo per lotti **MASSIVO** in **DRAFT**.  
Rollback tecnico: elimina fatture/righe/riepiloghi/log e ripristina le
`attivita_fatturabili` (unlock + reset flag).  
Il lotto viene marcato: `stato_doc_fiscale = ANNULLATA`, `stato_operativo = CHIUSO`, `stato_lotto = COMPLETATO`.

---

### 1.1) Processo di alimentazione attivita_fatturabili (necessita`)

In ambito utilities (gas/energia/acqua) la **generazione** di `attivita_fatturabili`
non e` un semplice import ma un **calcolo complesso** (consumi, conguagli, minimi, fasce).
Questo richiede:

* **tracciabilita` batch** (quando e` stato eseguito il calcolo, con quali parametri);
* **log dedicato** (warning/critical specifici del calcolo consumi);
* **testata di calcolo** con totali e periodi per BA/competenza;
* separazione chiara tra **alimentazione** e **fatturazione**.

Per questo si introduce un **processo di alimentazione** separato dal lotto fatture,
ma collegabile in dashboard.

> Nota: le validazioni/normalizzazioni su `attivita_fatturabili` sono gestite da
> trigger dedicati (es. `trgfn_attivita_fatturabili_guard_ba_coerenza`,
> `trgfn_attivita_fatturabili_guard_fonte`, `trgfn_attivita_norm_competenza_mese`).

---

### 1.2) Lotto alimentazione + attivita_consumi (design)

**Lotto alimentazione** (`vendite.attivita_fatturabili_lotti`):
* batch di generazione `attivita_fatturabili` con parametri di calcolo (competenza, utility, BA);
* stato lotto (IN_ESECUZIONE | COMPLETATO | ERRORE);
* riferimento per dashboard e audit.

**Testata consumi** (`vendite.attivita_consumi`):
* totalizzatori per BA/periodo (consumo_totale, uom, periodo);
* punto di aggregazione per i dettagli futuri (fasce, minimi, ecc.);
* collegabile a `fattura_id` quando il documento e` emesso.

**Log dedicato** (`vendite.attivita_fatturabili_log`):
* messaggi W/C riferiti al lotto o alla testata consumi.

---

### 1.3) Area geografica (analisi)

Per esigenze di fatturazione (es. raggruppamenti per **comuni**), e` necessario
introdurre una **area geografica** dedicata.  
Questa area e` un filtro **specifico** e non va confusa con i futuri gruppi
multi‑criterio (che useranno un livello distinto).

> Nota: i BA senza area restano **fatturabili**. L’area geografica puo` essere
> NULL e le attivita vengono comunque generate, per non penalizzare chi non
> usa questa funzionalita`.

Le righe `attivita_fatturabili` generate da processi automatici
mantengono un riferimento al **lotto alimentazione** e, se disponibile,
alla **testata consumi**.

---

## 📌 Appendice – Modifiche richieste (giornaliero)

### A) Schema
* `vendite.fatturazione_lotti`
  * aggiungere `tipo_lotto` (`MASSIVO` | `GIORNALIERO`)
  * aggiungere `stato_operativo` (`APERTO` | `CHIUSO` | `ERRORE`)

### B) Regole operative
* **Giornaliero**:
  * fatture emesse subito (numerazione immediata)
  * **no retrocessione** a BOZZA
  * lotto `APERTO` finché lo step corrente non ha `chiude_lotto = true`
* **Massivo**:
  * retrocessione ammessa (se previsto dalle transizioni)
  * `stato_operativo` può riaprire

### C) Pipeline
* pipeline dedicata **GIORNALIERO** (step ridotti fino a numerazione)
* pipeline MASSIVA invariata

### 2) Parametri funzione di calcolo (proposta)

* `p_competenza_mese` (obbligatorio, YYYY-MM-01)
* `p_billing_account_id` (opzionale)
* `p_utility_id` (opzionale)
* `p_tipo_doc_fiscale_id` (obbligatorio)
* `p_reseller_soggetto_ruolo_id` (opzionale)
* `p_lotto_id` (opzionale; se NULL/0 -> crea lotto)
* `p_preview` (opzionale)

**Regole**:

* se `p_lotto_id` e` valorizzato, il ricalcolo si aggancia al lotto (e ai suoi parametri).
* il lotto contiene **tutti i parametri** necessari per ricalcoli futuri.
* il `reseller` e` un filtro commerciale, **non** modifica il destinatario fattura.

---

### 3) Raggruppamento fatture

Chiavi di raggruppamento:

* `billing_account_id`
* `competenza_mese`
* `utility_id` (se valorizzato)
* `tipo_doc_fiscale_id`
* `valuta_id`
* `emittente_soggetto_ruolo_id` (se valorizzato)

La funzione **aggrega** su fattura bozza esistente con stessa chiave.

---

### 3.1) Multi‑emittente e fatturazione su parent billing account

**Multi‑emittente**:
* L’emittente fiscale e` un ruolo e puo` variare per utility/cliente.
* Il lotto puo` includere piu` emittenti (societa` diverse) e il raggruppamento
  deve mantenere separati i documenti per emittente.

**Parent billing account**:
* Un `billing_account` puo` avere un **parent**.
* La **testata fattura** viene emessa al parent.
* Le **righe** mantengono il dettaglio per **child** (es. `dest_billing_account_id`),
  cosi` il parent riceve una fattura aggregata ma con dettaglio per account figlio.

**Implicazioni di calcolo**:
* Il raggruppamento usa il parent per la testata.
* I calcoli di riga restano legati al child, per ripartizioni e riepiloghi separati.

---

### 3.2) Reseller (ruolo commerciale, non cliente)

* **Cliente unico**: il destinatario fattura resta sempre il **billing account** (o il suo parent).
* **Reseller opzionale**: non aggrega BA diversi in un’unica fattura; serve come filtro e
  metadato commerciale (report, provvigioni, selezioni batch).
* **Distribuzione esclusa**: il caso in cui il reseller diventa destinatario fattura
  e` fuori dallo standard e verra` trattato come processo dedicato.

---

### 4) Stati documento e stati SDI (separati)

Lo **stato SDI** deve essere **per documento**, non per lotto.
Si propone quindi lo **sdoppiamento** dello stato:

**A) Stato documento** (ciclo fiscale interno):

* DRAFT (Bozza)
* EMESSA
* INVIATA
* REGISTRATA
* ANNULLATA

**B) Stato SDI** (Italia, esito canale):

* NON_INVIATA
* INVIATA
* CONSEGNATA
* SCARTATA

Questa separazione evita sovrapposizioni tra **stato fiscale** e **stato di invio**.

**Operativamente**:

* `INVIATA` resta stato documento in `config.stati_doc_fiscale`
* si crea `config.stati_sdi` e si collega a `vendite.fatturazione_lotti_fatture.stato_sdi_id`
* `config.stati_doc_fiscale` resta unica, con flag di applicabilita`:
  * `applica_fattura` (stato valido per `vendite.fatture`)
  * `applica_lotto` (stato valido per `vendite.fatturazione_lotti`)

---

### 5) Regole di rollback (da definire in policy)

Proposta di base:

* da **EMESSA** → **DRAFT** ammesso per consentire ricalcolo (prima dell’invio)
* **REGISTRATA** e **ANNULLATA** non sono rollbackabili (salvo processo amministrativo dedicato)

Regola operativa confermata:
* `MASSIVO`
  * `DRAFT` e `EMESSA`: rieseguibili con reset tecnico di step.
  * `DEFINITIVA`: niente reset globale; resume dalle sole fatture non numerate/in errore.
* `GIORNALIERO`
  * nessun reset lotto per `EMESSA`; emissione gestita fuori pipeline lotto.

Nota implementativa corrente:
* Il runner Django esegue gli step con `rollback=false` fisso; il rollback automatico su errore step e` ancora da introdurre.

**Regola proposta (config)**:

* ✅ in `config.stati_doc_fiscale` aggiungere `stato_precedente_ammesso boolean`
* la retrocessione e` consentita **solo** verso lo stato immediatamente precedente (per ordine), se il flag e` `true`

---

### 6) Tipo documento fiscale (regola proposta)

* `vendite.attivita_fatturabili` **deve** avere `tipo_doc_fiscale_id`.
* Se l’attivita` deriva da una sorgente **RIGA** (`config.sorgenti`), il `tipo_doc_fiscale_id` viene ereditato dalla sorgente.
* Per attivita` inserite manualmente (auto‑sorgente), il `tipo_doc_fiscale_id` deve essere valorizzato direttamente.
* **Fallback**: non previsto. Il tipo documento e` di sistema.
* **Ordine di risoluzione** per l’alimentazione di `attivita_fatturabili`:
  1) `config.sorgenti.tipo_doc_fiscale_id` (se sorgente RIGA e valorizzato)
  2) errore se ancora NULL

Questa regola rende il raggruppamento deterministico e permette casi semplificati con **un solo tipo documento per utility**.

---

### 7) Ricalcolo e note (policy)

**Ricalcolo:**

* Consentito solo per fatture **BOZZA**.
* Strategia: **delete & regen** delle righe fattura per lotto/BA/competenza.
* Le righe manuali **non sono ammesse** in fattura: eventuali inserimenti manuali devono passare da `attivita_fatturabili`.

**Note:**

* ✅ Le note associate a `attivita_fatturabili` confluiscono in `note_fatture_righe`.
* ✅ Il trasferimento avviene **in fase di emissione/numerazione**, tramite **processo dedicato** richiamabile.
* ✅ La lettura note usa `vendite.fn_get_vendite_note` (wrapper su tabella partizionata `vendite.note`).

**IVA (processo dedicato):**

* ✅ La generazione `fatture_riepiloghi_iva` e` un processo separato.
* ✅ Deve **prima** rimuovere i riepiloghi esistenti della fattura/lotto
  e **poi** ricalcolare.
* ✅ Il processo puo` essere inserito in qualsiasi step della pipeline (o servizio dedicato),
  senza vincolo a stato specifico.
*  Il processo di generazione righe (Django) deve valorizzare `iva_id`
  in modo corretto e coerente con le regole applicative.

---

### 7.1) Arrotondamenti per scope

Per garantire arrotondamenti **deterministici** e coerenti tra fattura e storni,
introduciamo uno **scope tecnico** separato dalla testata.

**Tabella:** `vendite.fatture_arrotondamenti_scope`

**Chiave scope (univoca):**

* `billing_account_id`
* `utility_id`
* `tipo_doc_fiscale_id`
* `emittente_soggetto_ruolo_id`
* `valuta_id`

**Campo principale:**

* `saldo_arrotondamento` (saldo tecnico da usare per `arrotondamento_precedente/attuale`).

**Note operative:**

* Il saldo e` tecnico, non fiscale.
* L’aggiornamento deve avvenire tramite funzioni dedicate (get/set), non a mano.

---

### 8) Regole kit/BOM (flag componenti)

Quando `calcolo_qta_padre = somma_componenti_flaggate`, serve un flag **esplicito** sulle componenti
per definire quali righe contribuiscono alla quantita` del padre.

**Proposta**:

* ✅ aggiungere in `catalogo.articoli_componenti` il campo `determina_qta_padre boolean`
* ✅ la somma delle componenti con `determina_qta_padre = true` determina `qta_padre`

---

### 9) Emittente e valuta (regole di risoluzione)

Se in `attivita_fatturabili` non sono espliciti:

* ✅ **Emittente**: derivare da configurazione legata a `utility_id` (o a `billing_account`), con fallback su emittente di default.
* ✅ **Valuta**: derivare da `billing_account` o da default di utility; fallback su valuta di sistema.

Queste regole devono essere **deterministiche** e centralizzate (tabella/config dedicata),
per evitare fatture miste o ambiguita`.

---

### 10) Audit/Log di processo (modello job)

I processi di fatturazione vanno tracciati con il modello **job** previsto in guide:

* `dbops.jobs` (definizione)
* `dbops.job_runs` (esecuzione)
* `dbops.job_steps` (step)
* integrazione con `dbops.audit_log` ed `dbops.error_log`

In questo modo ogni esecuzione e` **monitorabile** e correlata al `lotto_id`.

> Nota: al momento queste tabelle **non risultano presenti** nelle migrazioni; vanno introdotte prima di adottare il modello.

---

### 11) Emittente fiscale e valuta in `attivita_fatturabili` (proposta)

**Emittente fiscale (ruolo):**

* ✅ introdurre una tabella di mapping **billing_account → emittente fiscale** (ruolo).
* ✅ l’emittente fiscale va **sempre valorizzato** per coerenza, anche quando coincide con il gestore.
* ✅ se un **billing_account** non e` associato, usare un **emittente di default** (per evitare configurazioni manuali in presenza di un solo emittente).

**Valuta + prezzo in attivita_fatturabili:**

* ✅ aggiungere `valuta_id` su `vendite.attivita_fatturabili`.
* ✅ aggiungere `prezzo_unitario numeric(20,8)`.
* ✅ la valuta di default resta derivabile da configurazione (utility/azienda), ma la riga deve avere il valore **esplicito** per calcoli deterministici.

---

### 12) Sottoprocessi richiamabili (scomposizione)

Per evitare monoliti, la pipeline deve essere composta da procedure richiamabili:

* `cleanup_righe_fattura(fattura_id)` → elimina righe e dipendenze in bozza
* `calcolo_righe_fattura(lotto_id, ...)` → genera righe da `attivita_fatturabili`
* `trasferisci_note(lotto_id | fattura_id)` → note da attivita` a righe fattura
* `emetti_fatture(lotto_id)` → numerazione + stato documento
* `invio_sdi(lotto_id)` → processo canale (solo Italia)

---

### 13) Tabelle da introdurre o modificare (prima della logica)

**Nuove tabelle (proposte):**

* ✅ `vendite.fatturazione_lotti` (lotto + stato job/documenti + lock uuid)
* ✅ `vendite.fatturazione_lotti_fatture` (relazione lotto ↔ fattura + stato SDI + esclusione)
  
* ✅ -`config.stati_sdi` (stati canale SDI)
* ✅ `config.stati_doc_fiscale` (stati documento con flag `applica_lotto` / `applica_fattura`)
  
* ✅ `vendite.tipi_doc_fiscale_registri` (mapping **tipo documento → registro**)

* ✅ `anagrafiche.emittenti_fiscali_billing_account` (mapping **billing_account → emittente fiscale**)
  * aggiungere `default boolean` con **unicita`** del valore `true`
 `dbops.jobs`, `dbops.job_runs`, `dbops.job_steps` (modello job)
  
* ✅ `vendite.fatture_log` (log anomalie documento)

* ✅  `anagrafiche.resellers_billing_account` (mapping **billing_account → reseller** senza default)
  * campi minimi: `id`, `billing_account_id`, `reseller_soggetto_ruolo_id`, `meta`, audit

**Tabelle da modificare (proposte):**

* ✅ `vendite.attivita_fatturabili` → aggiungere `tipo_doc_fiscale_id`, `valuta_id`, `prezzo_unitario`
* ✅ `config.sorgenti` → aggiungere `tipo_doc_fiscale_id` (per sorgenti RIGA)
* ✅ `config.utilities` → aggiungere `tipo_doc_fiscale_id` default
* ✅ `vendite.fatture` → aggiungere `registro_id` e `critical`

* ✅ `config.stati_doc_fiscale` → rimuovere stati SDI e aggiungere `stato_precedente_ammesso`
 
* ✅  `catalogo.articoli_componenti` → aggiungere `determina_qta_padre`

* ✅ `anagrafiche.resellers` → bloccare `attivo = false` se esistono mapping su `resellers_billing_account`

---

### 14) Collegamento lotto ↔ fatture e esclusioni

La relazione tra lotto e fatture deve essere esplicita:

* ✅ tabella `vendite.fatturazione_lotti_fatture` con `lotto_id`, `fattura_id`, `stato_sdi_id`
* ✅ flag `esclusa boolean` per escludere una fattura dal lotto
  * ✅ `esclusa = true` ammesso **solo** se `stato_doc_fiscale = DRAFT`

Questa tabella e` il punto estensibile per metadati futuri legati a lotto/fatture.

---

### 15) Log anomalie fattura e blocco numerazione/invio

* ✅ tabella `vendite.fatture_log` con:
  * `id`, `fattura_id`, `data_ora`, `messaggio`, `status` (W=warning, C=critical), `disabilitato`
  * audit + `meta`
* ✅ piu` messaggi per documento.
* ✅ un operatore autorizzato puo` **disabilitare** un errore ritenuto accettabile.
* ✅ se esiste almeno un log **critical** attivo, `fatture.critical = true` e la numerazione/invio devono essere bloccati.
* ✅ `disabilitato = true` esclude il log dal calcolo del flag `critical` sulla fattura.

---

### 16) Sviluppi funzioni (backlog)

**Preparazione lotto**

* ✅ `vendite.fn_create_fatturazione_lotto(...)` → crea lotto da parametri (competenza, utility, tipo documento, BA/reseller opzionali).
* ✅ `vendite.fn_get_or_create_lotto(...)` → valida lotto esistente o lo crea se assente (supporto ricalcolo).

**Selezione e lock attivita_fatturabili**

* ✅`vendite.fn_select_attivita_fatturabili(...)` → seleziona righe eleggibili e, se richiesto, esegue il lock in modo atomico.

**Aggregazione e chiavi documento**

* ✅`vendite.fn_group_attivita_fatturabili(...)` → applica regole di aggregazione (BA, utility, tipo documento, valuta, parent BA).
* ✅`vendite.fn_build_fattura_key(...)` → genera chiave logica di aggregazione per documento.

**Generazione documenti**

* ✅`vendite.fn_get_or_create_fattura_header(...)` → crea/recupera testata fattura in bozza (riuso per lotto/chiave).
* ✅`vendite.fn_generate_fatture_righe(...)` → genera righe da `attivita_fatturabili` secondo regole.

**Ricalcolo**

* `vendite.fn_reset_fattura_righe(...)` → elimina righe e dipendenze se lo stato lo consente.
* `vendite.fn_ricalcolo_lotto(...)` → reset + rigenerazione per lotto (eventuale filtro BA).

**Stato e validazioni**

* `vendite.fn_guard_lotto_stato(...)` → verifica transizioni ammesse per lotto.
* `vendite.fn_guard_fattura_stato(...)` → verifica transizioni ammesse per fattura.
* `vendite.fn_check_fattura_errors(...)` → aggiorna `critical` e log in base agli errori.

**Post-process**

* `vendite.fn_numera_fatture_lotto(...)` → assegna progressivi documento (registri).
* `vendite.fn_prepare_sdi_payload(...)` → prepara invio SDI (placeholder).

**Pipeline (orchestrazione lotto)**

*✅ `vendite.pr_run_lotto_pipeline(...)` → esegue la pipeline configurabile leggendo `vendite.fatturazione_pipeline`.
  * imposta `stato_lotto = IN_ESECUZIONE` all’avvio e `COMPLETATO` a fine job.
  * per ogni step:
    * aggiorna `stato_doc_fiscale_id` del lotto,
    * scrive un log `status=I` con `fase` su `fatturazione_lotti_log`,
    * esegue i task definiti in `processi`.
  * in caso di errore: `stato_lotto = ERRORE` + log errore.
* ✅`vendite.fn_execute_pipeline_step(...)` → esegue i task di uno step (lettura `processi`/`rollback`).
* ✅ `vendite.fn_log_pipeline_fase(...)` → inserisce log `I/W/C` con fase e stato lotto.
* Pipeline configurabile anche per `utility_id` e `tipo_doc_fiscale_id`, con fallback su `NULL`
  per mantenere una configurazione base riusabile.

---

### 18) Sviluppi – Area geografica (backlog)

**Tabelle**

* ✅`vendite.area_geografica_fatturazione`
  * id, codice, descrizione, attivo, meta, audit
* ✅`vendite.area_geografica_fatturazione_comuni`
  * id, area_id, comune_id, attivo, meta, audit

**Colonne da aggiungere**

* ✅`vendite.attivita_fatturabili.area_geografica_id` (FK, opzionale)
* ✅`vendite.fatturazione_lotti.area_geografica_id` (FK, opzionale)

**Funzioni / regole previste**

* risoluzione area da comune (BA/indirizzo/utenza) in normalize
* filtro area in `fn_select_attivita_fatturabili`

---

### 17) Nota su Fatturazione Elettronica (FE)

* Il mapping **FE** (es. TD01, TD04) non e` gestito nel tipo documento attuale.
* La classificazione FE verra` introdotta in una fase successiva con un dominio dedicato
  per l’emissione elettronica e l’invio SDI.

---

### 19) Promemoria refactor

* Rinominare `vendite.fatturazione_lotti_attivita` in `vendite.attivita_fatturabili_lotti`.

---

### 20) error_log refactor

Obiettivo: classificare le funzioni perimetro `LOTTO` vs `FATTURA` vs `ATTIVITA_FATTURABILI` per applicare in modo coerente il routing errori applicativi (`scope`, `severity`, `code`, `lotto_id`, `fattura_id`, `context`) su `dbops.error_log` e log dominio.

**Perimetro LOTTO**

* ✅X`vendite.fn_create_fatturazione_lotto`
* ✅X `vendite.fn_get_or_create_lotto`
* ✅X `vendite.fn_set_fatturazione_lotto_stato`
* ✅X `vendite.fn_sync_lotto_fatture_stato`
* ✅X `vendite.fn_log_pipeline_fase`
* ✅X `vendite.fn_log_lotto_esito_fatture`
* ✅X `vendite.fn_list_fatturazione_pipeline_steps`
* ✅X `vendite.fn_resolve_fatturazione_pipeline_step`
* ✅X `vendite.fn_prepare_sdi_payload`
* ✅X `vendite.fn_close_giornaliero_lotto` (legacy/fallback, non usata nel canale principale runner)
* ✅X `vendite.fn_reset_lotto_draft`
* ✅X `vendite.fn_reset_lotto_fattura_draft`
* ✅ Trigger: `vendite.trgfn_fatturazione_lotti_guard_stato`, `vendite.trgfn_fatturazione_lotti_gen_codice`

**Perimetro FATTURA**

* ✅ X`vendite.fn_build_fattura_key`
* ✅ X`vendite.fn_get_or_create_fattura_header`
* ✅ X`vendite.fn_group_attivita_fatturabili`
* ✅ X`vendite.fn_generate_fatture_righe`
* ✅ X`vendite.fn_assign_numero_fattura`
* ✅ X`vendite.fn_numera_fattura_opz_emessa`
* ✅ X`vendite.fn_ricalcola_riepilogo_iva_fattura`
* ✅ X`vendite.fn_ricalcola_totali_fattura`
* ✅ X`vendite.fn_ricalcola_fattura`
* ✅ X`vendite.fn_ricalcola_riepiloghi_iva_lotto`
* ✅ X`vendite.fn_get_totale_fondi_fattura`
* ✅ X`vendite.fn_genera_fondi_fattura_source`
* ✅ X`vendite.fn_applica_fondi_fattura`
* ✅ X`vendite.fn_reset_fondi_fattura`
* ✅ X`vendite.fn_sync_contabili_fondo_fattura`
* ✅ X`vendite.fn_sync_pagamento_fondo_fattura` (wrapper, da tenere solo come compatibilità)
* ✅ X`vendite.fn_sync_fattura_critical`
* ✅ X`vendite.fn_resolve_termini_pagamento`
* ✅ Trigger: `vendite.trgfn_fatture_*`, `vendite.trgfn_fatture_righe_guard_normalize`

**Perimetro ATTIVITA_FATTURABILI (pre-fattura)**

* ✅ `vendite.fn_select_attivita_fatturabili`
* ✅ `vendite.fn_get_registro_id`
* ✅ `vendite.fn_get_tipo_doc_fiscale_id`
* ✅ `vendite.fn_get_valuta_id`
* ✅ `vendite.fn_get_vendite_note`
* ✅ `vendite.fn_list_attivita_pipeline_steps`
* ✅ `vendite.fn_resolve_attivita_pipeline_step`
* ✅ Trigger: `vendite.trgfn_attivita_fatturabili_*`, `vendite.trgfn_attivita_norm_competenza_mese`

**Legacy orchestration SQL (deprecata lato runtime)**

* ✅ `vendite.pr_run_lotto_pipeline`
* ✅ `vendite.fn_execute_pipeline_step`
* Nota: runtime corrente orchestrato in Django/Python; mantenere SQL solo come compatibilità tecnica/documentale finché non rimosso.

**Owner runtime per blocco**

| Blocco                   | Owner runtime principale         | Note operative                                                                                             |
| ------------------------ | -------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| LOTTO                    | Django orchestration + SQL guard | Python gestisce sequencing/retry/logica step; DB applica vincoli e guardrail di stato/integrità.           |
| FATTURA                  | Ibrido                           | Python orchestration per processo; SQL per calcoli atomici, consistenza dati e operazioni batch/sincronia. |
| ATTIVITA_FATTURABILI     | Ibrido                           | SQL forte su selezione/lock/normalize; Python usa le funzioni DB dentro flussi pipeline/applicativi.       |
| Legacy orchestration SQL | Deprecato                        | Da non usare come entrypoint runtime; mantenuto solo per compatibilità tecnica temporanea.                 |

Legenda owner:

* `SQL guard`: enforcement dati/stati/integrità direttamente nel DB.
* `Django orchestration`: controllo del flusso di processo (pipeline/task/error handling).
* `Ibrido`: orchestration in Python con task calcolati/validati da funzioni SQL.
