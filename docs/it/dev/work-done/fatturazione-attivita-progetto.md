# Fatturazione - attivita di progetto (WIP)

> Documento di lavoro per pianificazione e avanzamento attivita. Contiene appendici e note operative.
> La guida principale resta `docs/it/guide/fatturazione.md`.
>
> ⚠️ **Nota operativa (22-02-2026):** per la ripresa implementativa del dominio
> `attivita_fatturabili`, il documento WIP di riferimento unico e`:
> `docs/it/dev/work-done/ripresa-lavori-attivita-fatturabili.md` (superato, vedi `gestione-commesse-v2.md`).
> Questo file resta storico/contestuale.

---

## ✅ Recap stato (sintesi)

- [x] Pipeline fatturazione su `vendite.fatturazione_pipeline` con fallback `utility_id`/`tipo_doc_fiscale_id`.
- [x] Orchestrazione Django (`pr_run_lotto_pipeline` e `fn_execute_pipeline_step` Python; componenti SQL legacy rimosse).
- [x] Registry task multi-dominio in DB (`dbops.domini_task`, `dbops.pipeline_task_registry`, `dbops.pipeline_task_registry_impl`).
- [x] `implementation_key` nei task JSON e dispatch via registry DB.
- [x] Log fatture e flag `critical` (tabella `vendite.fatture_log` + sync).
- [x] Area geografica fatturazione e colonne correlate.
- [x] Chiusura operativa lotto guidata da flag `config.stati_doc_fiscale.chiude_lotto` a fine step.
- [x] Numerazione spostata a step `DEFINITIVA` (pipeline massiva); `EMESSA` resta pre-fiscale/riapribile.
- [x] Stato fattura allineato per-step dal runner (`1→2→8`), sync centralizzato — vedi [§ Allineamento stato fattura ↔ stato step](#-allineamento-stato-fattura--stato-step-sync-per-step).
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
- [ ] Registry runtime multi-dominio completo in Django (mappa per dominio).
- [x] Resume `DEFINITIVA` a livello fattura (ripartenza da errore senza reset globale).
- [x] Policy rerun `MASSIVO` nel runner Django: resume dallo step corrente + rollback step opzionale con `meta.auto_step_rollback=true` (skip rollback distruttivi in auto-run).
- [x] Seed transizioni `config.stati_doc_fiscale_transizioni` allineato agli step lotto (incluso `MASSIVO` 8 -> 3).

## 🧾 Release Notes DB-2 (22-02-2026)

Stato: implementazione DB-2 avanzata e riallineata tra domini `fatturazione_lotti` e `attivita_fatturabili`.

Changeset principali:

1. `20260222-01`  
   `00_schema/vendite/20260222-01-update-attivita-fatturabili-lotti-stati-emittente-mctit.yaml`
   - aggiunti su `attivita_fatturabili_lotti`: `stato_operativo`, `emittente_soggetto_ruolo_id`
   - aggiunto su `attivita_fatturabili`: `stato_esecuzione`
   - indici e vincoli iniziali
2. `20260222-01-02`  
   nello stesso file:
   - `stato_esecuzione` su `attivita_fatturabili` reso nullable (`NULL` fuori pipeline)
   - check aggiornato: `NULL` oppure `PENDING|RUNNING|COMPLETED|ERRORE`
3. `20260222-02`  
   `00_schema/vendite/20260222-02-update-fatturazione-lotti-fatture-stato-esecuzione-v2-mctit.yaml`
   - convergenza `fatturazione_lotti_fatture.stato_esecuzione` a `PENDING|RUNNING|COMPLETED|ERRORE`
   - backfill `OK -> COMPLETED`
4. `20260222-03`  
   `20_code/vendite/20260222-03-update-fn-lotto-stato-esecuzione-v2-mctit.yaml`
   - update funzioni lotto/fatture per nuovi stati runtime (`RUNNING/COMPLETED/ERRORE`)
5. `20260222-04`  
   `20_code/vendite/20260222-04-update-fn-attivita-stato-esecuzione-mctit.yaml`
   - update funzioni attività:
     - lock selezione -> `PENDING`
     - generazione righe -> `RUNNING`/`COMPLETED`
     - cleanup/reset -> `NULL`
6. `20260222-05`  
   `20_code/vendite/20260222-05-create-fn-attivita-lotti-core-mctit.yaml`
   - nuove funzioni core dominio attività:
     - `fn_get_or_create_lotto_attivita`
     - `fn_set_attivita_lotto_stato`
     - `fn_sync_attivita_stato_esecuzione`
7. `20260222-06`  
   `20_code/vendite/20260222-06-refactor-lotti-resolve-emittente-utility-helper-mctit.yaml`
   - refactor anti-duplicazione:
     - nuovo helper condiviso `fn_resolve_lotto_utility_emittente`
     - riuso helper in `fn_get_or_create_lotto` e `fn_get_or_create_lotto_attivita`
8. `20260222-07`  
   `20_code/vendite/20260222-07-refactor-stato-esecuzione-mapping-helper-mctit.yaml`
   - secondo refactor anti-duplicazione:
     - nuovo helper condiviso `fn_resolve_stato_esecuzione`
     - riuso helper in:
       - `fn_set_fatturazione_lotto_stato`
       - `fn_sync_lotto_fatture_stato`
       - `fn_sync_fatture_log_critical_lotto`
       - `fn_sync_attivita_stato_esecuzione`
9. `20260222-08`  
   `20_code/vendite/20260222-08-fix-trgfn-attivita-guard-log-variadic-casts-mctit.yaml`
   - fix trigger function guard attività con cast espliciti su parametri variadici verso `script.fn_log_and_raise_error(...)`
   - riallineate:
     - `trgfn_attivita_fatturabili_guard_ba_coerenza`
     - `trgfn_attivita_fatturabili_guard_fonte`
Nota operativa:
- Prima della conferma finale del pacchetto DB-2, consigliata esecuzione test pgtap dedicati su:
  - coerenza BA/emittente
  - mapping stati esecuzione
  - transizioni stato lotto attività.


## 🛣️ Roadmap runtime task/stato_lotto (nuova)

Obiettivo: rendere esplicita la gestione runtime per task, mantenendo `stato_lotto`
come stato tecnico di esecuzione e `stato_operativo` come stato business del lotto.





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

## 🚦 Test gravita disallineamenti (guida vs WIP)

Riferimento confronto:

* `docs/it/guide/fatturazione.md`
* `docs/it/dev/work-done/fatturazione-attivita-progetto.md`
* `docs/it/dev/work-done/pipeline-domini-engine.md`

Esito sintetico:

* **MEDIA**: 3 aree
* **BASSA**: 2 aree

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



***Fine test gravità***

## ✅ Checklist finale unificata (DB + Django + API)

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

## 🧭 Allineamento stato fattura ↔ stato step (sync per-step)

### Scopo
Garantire che lo **stato documentale delle fatture** segua quello del **lotto**
ad ogni avanzamento di step, in modo **parametrico** (nessuna logica per-stato
cablata). Risolve il difetto per cui la fattura saltava da `DRAFT(1)` a
`DEFINITIVA(8)` violando la matrice transizioni (`config.stati_doc_fiscale_transizioni`,
che per la fattura ammette solo `1→2→8→3→6`).

### Comportamento
* La sincronizzazione e` **centralizzata** in un solo punto:
  `LottoPipelineRunner._execute_pipeline_step` (in `apps/vendite/services/pipeline_runner.py`).
  Dopo l'esecuzione dei task dello step (e prima del log esito / chiusura lotto)
  il runner chiama `repository.sync_lotto_fatture_stato(lotto_id,
  stato_doc_fiscale_id=step.stato_doc_fiscale_id)`.
* Il task `numera_fatture` (`PipelineStepExecutor._handle_numera_fatture_task`)
  **NON** sincronizza piu` lo stato: esegue **solo** la numerazione fiscale
  (`fn_numera_fattura_opz_emessa`). Unico punto di sync ⇒ nessuna duplicazione.
* **Dopo** i task: l'allineamento a `EMESSA(2)` avviene a valle del ricalcolo
  IVA/totali (semantica *"EMESSA = IVA certificata"*), prima della numerazione
  in `DEFINITIVA`.
* **Solo forward**: `_execute_pipeline_step` non e` il path di rollback (il
  rollback ha una chiamata `execute_step(rollback=True)` separata che non passa
  da qui), quindi il sync non scatta mai in rollback.
* **Mai in dry-run**: la chiamata e` sotto guard `if not dry_run`.
* **Idempotente**: `fn_sync_lotto_fatture_stato` aggiorna solo le fatture con
  `stato_doc_fiscale_id IS DISTINCT FROM` il target (lo step `DRAFT` ⇒ `1→1`
  no-op, dato che le fatture nascono gia` `DRAFT`), preserva `critical`/`esclusa`.

### Catena risultante
* **MASSIVO**: `1 (DRAFT) → 2 (EMESSA) → 8 (DEFINITIVA)` automatico per fattura,
  un hop per step; la chiusura lotto avviene su `DEFINITIVA` (`chiude_lotto=t`).
* **GIORNALIERO**: stesso meccanismo; lo step `EMESSA` (`processi=[]`) porta
  comunque la fattura a `2` prima della numerazione — **senza nuovi seed**.

### Invariante (contratto)
> **Ogni stato della pipeline deve essere `applica_fattura=TRUE`**, perche` la
> fattura segue il lotto step-by-step. Gli step provengono da
> `fn_list_fatturazione_pipeline_steps` (filtra `applica_lotto=TRUE`,
> `ORDER BY stati_doc_fiscale.ordine`): l'ordine logico determina la sequenza
> degli hop, che deve essere coperta dalla matrice transizioni fattura
> (`solo_lotto=FALSE`). Se un futuro stato fosse lotto-only, il guard
> `trgfn_fatture_guard_stato` fallirebbe in modo esplicito (fail-fast voluto,
> nessun skip silenzioso lato applicativo).

### Dipendenze DB
* `vendite.fn_sync_lotto_fatture_stato(p_lotto_id, p_target_stato_doc_fiscale_id)`
* `config.stati_doc_fiscale_transizioni` (matrice; ramo fattura = `solo_lotto=FALSE`)
* `vendite.fn_list_fatturazione_pipeline_steps` (`ORDER BY ordine`)
* `vendite.trgfn_fatture_guard_stato` (guard transizioni fattura)

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

## 📌 ~~Analisi fondi fattura (WIP)~~ — 🔴 SUPERATA (2026-08-15)

> 🔴 **Questa sezione è un design del 2026-02 mai eseguito, e tre delle sue righe
> sono state decise diversamente.** Resta scritta perché è la storia del
> ragionamento, non perché sia ancora valida. **La versione viva è
> [brief-db-fondo-fattura-ricalcolo-e-governo.md](../work-in-progress/brief-db-fondo-fattura-ricalcolo-e-governo.md) §8.**
>
> | Qui si diceva | Decisione presa |
> |---|---|
> | *«Storni / note credito: policy `riapribile` per tipologia fondo; se arriva uno storno la source torna `DISPONIBILE`»* | 🔴 **Cade due volte.** Lo **storno non esiste più come concetto** (una correzione è una contabile con importi negativi — cantiere incassi D3-d), e soprattutto sarebbe **un automatismo che riscrive uno stato in reazione a un pagamento**: sono stati esclusi tutti. Un fondo esistente **resta com'è**; la decisione la prende una persona |
> | *«esclude fatture pagate (regola a definire su pagamenti)»* | La regola ora c'è, ed è una **lettura al momento dell'atto**, non un filtro anticipato: si verifica che la sorgente sia ancora capiente **quando** il fondo muove denaro |
> | *«seleziona per chiave BA+utility+tipo_doc+emittente+valuta»* | La chiave è quella con cui si **accorpano le attività in fattura** (`fn_build_fattura_key`): **nove** elementi, non cinque. Ne mancavano reseller, registro, termine e modalità di pagamento |
> | *«`SUM(importo) >= totale_a_pagare` come regola base di *pagata*»* | ⚠️ Su un documento a **credito** il confronto si inverte e la regola risponde sempre «pagata». Ogni soglia su `totale_a_pagare` va definita **sapendo che può essere negativo** |
>
> ⭐ Non tutto è caduto: la **banda** delle soglie, i tre stati e la struttura dei
> due processi (genera → applica) sono rimasti quelli.

### Processo 1: Generazione source

* seleziona fatture con `minimo = true`
* esclude fatture gia` presenti in `source`
* ~~esclude fatture pagate (regola a definire su pagamenti)~~
* inserisce record `DISPONIBILE`

### Processo 2: Applicazione su fattura

* ~~seleziona record `DISPONIBILE` per chiave BA+utility+tipo_doc+emittente+valuta~~
* crea record in `fatture_fondi_fattura`
* aggiorna source `ASSEGNATO` e collega la `fattura_figlia_id`

### ~~Storni / note credito~~ — 🔴 concetto ritirato

~~Policy per tipologia fondo:~~

* ~~default `riapribile = false`~~
* ~~se `riapribile = true` e arriva storno, lo source torna `DISPONIBILE`~~

### Pagamenti

Serve tabella movimenti:

* `pagamenti.vendite_movimenti`
* ~~`SUM(importo) >= totale_a_pagare` come regola base di “pagata”~~

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

### 7.1) Arrotondamenti per ambito

Per garantire arrotondamenti **deterministici** e coerenti tra fattura e storni,
introduciamo un **ambito tecnico** separato dalla testata.

**Tabella:** `vendite.fatture_arrotondamenti_scope`

**Chiave ambito (univoca):**

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

### 11) Sottoprocessi richiamabili (scomposizione)

Per evitare monoliti, la pipeline deve essere composta da procedure richiamabili:

* `cleanup_righe_fattura(fattura_id)` → elimina righe e dipendenze in bozza
* `calcolo_righe_fattura(lotto_id, ...)` → genera righe da `attivita_fatturabili`
* `trasferisci_note(lotto_id | fattura_id)` → note da attivita` a righe fattura
* `emetti_fatture(lotto_id)` → numerazione + stato documento
* `invio_sdi(lotto_id)` → processo canale (solo Italia)

---

### 12) Log anomalie fattura e blocco numerazione/invio

* ✅ tabella `vendite.fatture_log` con:
  * `id`, `fattura_id`, `data_ora`, `messaggio`, `status` (W=warning, C=critical), `disabilitato`
  * audit + `meta`
* ✅ piu` messaggi per documento.
* ✅ un operatore autorizzato puo` **disabilitare** un errore ritenuto accettabile.
* ✅ se esiste almeno un log **critical** attivo, `fatture.critical = true` e la numerazione/invio devono essere bloccati.
* ✅ `disabilitato = true` esclude il log dal calcolo del flag `critical` sulla fattura.

---

### 13) Sviluppi funzioni (backlog)

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

* ✅ Servizio Python `pr_run_lotto_pipeline(...)` → esegue la pipeline configurabile leggendo `vendite.fatturazione_pipeline`.
  * imposta `stato_lotto = IN_ESECUZIONE` all’avvio e `COMPLETATO` a fine job.
  * per ogni step:
    * aggiorna `stato_doc_fiscale_id` del lotto,
    * scrive un log `status=I` con `fase` su `fatturazione_lotti_log`,
    * esegue i task definiti in `processi`.
  * in caso di errore: `stato_lotto = ERRORE` + log errore.
* ✅ Servizio Python `fn_execute_pipeline_step(...)` → esegue i task di uno step (lettura `processi`/`rollback`).
* ✅ `vendite.fn_log_pipeline_fase(...)` → inserisce log `I/W/C` con fase e stato lotto.
* Pipeline configurabile anche per `utility_id` e `tipo_doc_fiscale_id`, con fallback su `NULL`
  per mantenere una configurazione base riusabile.

---

### 14) Sviluppi – Area geografica (backlog)

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

### 15) Nota su Fatturazione Elettronica (FE)

* Il mapping **FE** (es. TD01, TD04) non e` gestito nel tipo documento attuale.
* La classificazione FE verra` introdotta in una fase successiva con un dominio dedicato
  per l’emissione elettronica e l’invio SDI.

---

### 16) error_log refactor

Obiettivo: classificare le funzioni perimetro `LOTTO` vs `FATTURA` vs `ATTIVITA_FATTURABILI` per applicare in modo coerente il routing errori applicativi (`scope`, `severity`, `code`, `lotto_id`, `fattura_id`, `context`) su `dbops.error_log` e log dominio.

**Owner runtime per blocco**

| Blocco                   | Owner runtime principale         | Note operative                                                                                             |
| ------------------------ | -------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| LOTTO                    | Django orchestration + SQL guard | Python gestisce sequencing/retry/logica step; DB applica vincoli e guardrail di stato/integrità.           |
| FATTURA                  | Ibrido                           | Python orchestration per processo; SQL per calcoli atomici, consistenza dati e operazioni batch/sincronia. |
| ATTIVITA_FATTURABILI     | Ibrido                           | SQL forte su selezione/lock/normalize; Python usa le funzioni DB dentro flussi pipeline/applicativi.       |
| Legacy orchestration SQL | Rimosso                          | Entry point runtime SQL eliminati; orchestrazione attiva solo Django/Python.                               |

Legenda owner:

* `SQL guard`: enforcement dati/stati/integrità direttamente nel DB.
* `Django orchestration`: controllo del flusso di processo (pipeline/task/error handling).
* `Ibrido`: orchestration in Python con task calcolati/validati da funzioni SQL.

---

### 17) Refactor lotto/fatture (analisi consolidata)

#### Descrizione funzionale

Si conferma la separazione dei ruoli:

* `vendite.fatturazione_lotti`: stato del processo lotto (driver pipeline).
* `vendite.fatture`: stato reale del documento fiscale.
* `vendite.fatturazione_lotti_fatture`: stato tecnico per-fattura nel contesto lotto.

Inoltre, su testata lotto e` necessario aggiungere l'emittente fiscale
(`emittente_soggetto_ruolo_id`) come attributo di processo; `billing_account_id`
resta opzionale solo come filtro operativo di creazione lotto.

#### Modifiche DB da fare

**`vendite.fatturazione_lotti`**

* completare checklist campi/stati effettivamente necessari al run corrente;
* verificare che i vincoli supportino il perimetro `MASSIVO` e `GIORNALIERO` senza casi edge.

#### API / Django (refactor richiesto)

Runner/Service:

* leggere e aggiornare `stato_esecuzione` per ogni fattura task-by-task.
* usare `emittente_soggetto_ruolo_id` da lotto come riferimento primario.
* bloccare avanzamento su fatture `critical` o `stato_esecuzione='ERRORE'` secondo policy step.

Endpoint/DTO:

* estendere dettaglio lotto con stato per-fattura (`stato_doc_fiscale_id`, `stato_esecuzione`, `critical`).
* mantenere `billing_account_id` come filtro input opzionale (non attributo centrale di stato).

Test:

* ✅pgtap: coerenza `critical` <-> `stato_esecuzione`.
* Django service/API: gestione errore parziale per-fattura dentro lotto.

#### Promemoria `attivita_fatturabili` (prima di riprendere sviluppo)

Prima di riprendere implementazioni pipeline `attivita_fatturabili` verificare:

* coerenza del legame lotto `attivita_fatturabili_lotti` con nuovo modello emittente su lotto.
* regole di transizione/errore per-fattura allineate al nuovo `stato_esecuzione`.
* allineamento filtri pipeline (utility/tipo_doc/emittente) tra alimentazione e fatturazione.
* evitare di reintrodurre logiche su `billing_account_id` come chiave di testata lotto.

---


#### Problema operativo rilevato

Nel runtime attuale `fn_sync_lotto_fatture_stato` legge `vendite.fatture.critical`, ma la sincronizzazione di `critical` dipende da chiamate esplicite (`fn_sync_fattura_critical`) e non da un automatismo unico su ogni modifica log.

Azioni suggerite:

* introdurre un punto unico di sync `critical` richiamato a fine step pipeline e su eventi log `C/W`;
* aggiungere test DB + Django che validino la coerenza `fatture_log` -> `fatture.critical` -> avanzamento stato lotto.
