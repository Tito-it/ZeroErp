# Ripresa lavori - attivita_fatturabili (22-02-2026)

> **SUPERATO (26-02-2026):**
> Questo documento e` stato sostituito da `gestione-commesse-v2.md` §25.
> La pipeline legacy `attivita-da-fatturare` e` deprecata (FASE 4 §25.4 completata).
> La modalita` target `COMMESSA_ONLY` (push/pull via `commesse_*`) e` operativa.

> Nota stato (24-02-2026):
> la pipeline legacy `attivita-da-fatturare` e` da considerare deprecata;
> la modalita` target e` `COMMESSA_ONLY` (push/pull via `commesse_*`).

## 1) Obiettivo

Riprendere il dominio `attivita_fatturabili` allineandolo al livello raggiunto dalla pipeline lotto, partendo prima dai refactor trasversali dei punti 20 e 21 del documento WIP.

Riferimento base:
- `docs/it/dev/work-done/fatturazione-attivita-progetto.md`

## 2) Stato reale sintetico (oggi)

### 2.1 Gia` presente

- Pipeline lotto Django matura (runner, step executor, task policy, task runs).
- Registry task DB multi-dominio (`dbops.domini_task`, `dbops.pipeline_task_registry`, `dbops.pipeline_task_registry_impl`).
- Struttura DB pipeline attivita presente:
  - `vendite.attivita_fatturabili_pipeline`
  - funzioni `vendite.fn_resolve_attivita_pipeline_step` e `vendite.fn_list_attivita_pipeline_steps`.
- Refactor lotto/fatture lato DB avanzato:
  - `fatturazione_lotti.emittente_soggetto_ruolo_id`
  - `fatturazione_lotti_fatture.stato_esecuzione`
  - sync automatica `fatture_log -> fatture.critical -> stato_esecuzione` con trigger.

### 2.2 Gap ancora aperti (bloccanti per ripartenza attivita)

- Nessun runner Django dedicato per dominio `ATTIVITA_FATTURABILI`.
- Nessuna API dedicata run/status/task-runs per pipeline attivita.
- Mancano task-runs e policy runtime dedicati al dominio attivita (equivalenti al dominio lotto).
- Routing errori perimetro `ATTIVITA_FATTURABILI` non ancora consolidato come standard unico end-to-end.

### 2.3 Mancanze complete da chiudere (base implementativa unica)

#### A) Disallineamenti documento vs stato reale

1. Sezione note marcata come completata nel WIP storico, ma non risulta un task/handler operativo esplicito di trasferimento note `attivita_fatturabili -> note_fatture_righe`.
2. Nomenclatura trigger nel WIP storico non completamente allineata al naming attuale (`script.trgfn_guard_sorgente_polimorfa`, `vendite.trgfn_attivita_fatturabili_normalize`).
3. Dominio `ATTIVITA_FATTURABILI` creato in `dbops.domini_task`, ma seed task/implementation registry non ancora valorizzato per dominio 2.

#### B) Mancanze DB (dominio attivita pipeline)

1. Policy runtime task dedicate:
   - `vendite.attivita_fatturabili_pipeline_task_policy`
2. Tracing runtime task dedicato:
   - `vendite.attivita_fatturabili_lotti_task_runs`
3. Estensione opzionale pipeline non lineare:
   - `branch_code`
   - `block_scope` (`BRANCH|GLOBAL`)
   - `depends_on` (jsonb)

#### C) Mancanze runtime Django

1. Runner dedicato:
   - `AttivitaPipelineRunner`
2. Step executor dedicato:
   - `AttivitaPipelineStepExecutor`
3. Repository dedicato:
   - `AttivitaPipelineRepository`
4. Mappa runtime registry multi-dominio completata (incluso dominio `ATTIVITA_FATTURABILI`).
5. Routing errori dominio attivita unificato (`scope=ATTIVITA_FATTURABILI`).

#### D) Mancanze API

1. Endpoint run pipeline attivita.
2. Endpoint stato/segnalazioni pipeline attivita.
3. Endpoint task-runs pipeline attivita.
4. DTO/UI contract con stato per branch e blocco per ambito.

#### E) Mancanze test

1. pgTAP:
   - resolve/list step attivita (fallback)
   - policy branch/global
   - task-runs attivita
2. Django services:
   - run ok
   - errore branch A non blocca branch B (ambito BRANCH)
   - errore global blocca run
3. Django API:
   - run/status/task-runs
   - envelope errori coerente

#### F) Mancanze documentazione

1. Allineamento WIP storico alle scelte definitive (trigger/note/ownership runtime).
2. Manuali backend vendite per pipeline attivita (runner/executor/API).
3. Checklist go-live dedicata al dominio attivita.

## 3) Punto 20 - error_log refactor (priorita alta, da chiudere prima)

## 3.1 Esito analisi

Base DB introdotta, ma il completamento non e` ancora uniforme su tutto il dominio attivita:
- lotto/fattura hanno gia` una traiettoria chiara di routing errori;
- attivita_fatturabili non ha ancora un owner runtime dedicato in Django.

## 3.2 Bozza interventi

1. Formalizzare una matrice unica `scope -> owner runtime -> tabella log`:
   - `LOTTO` -> runner lotto + `fatturazione_lotti_log`
   - `FATTURA` -> task documento + `fatture_log`
   - `ATTIVITA_FATTURABILI` -> nuovo runner attivita + log dominio attivita
2. Definire helper comune di payload errore lato Python (shape allineata a DB):
   - `scope`, `severity`, `code`, `lotto_id`, `fattura_id`, `context`
3. Chiudere il perimetro attivita con:
   - codici errore dedicati prefissati (`E_ATTIVITA_*`)
   - test unit per routing (`LOTTO` vs `FATTURA` vs `ATTIVITA_FATTURABILI`)

## 3.3 Deliverable minimi

- Documento mapping errori aggiornato.
- Test Django di routing errori dominio attivita.
- Checklist funzioni SQL attivita con payload coerente.

## 4) Punto 21 - refactor lotto/fatture (priorita alta, completamento operativo)

## 4.1 Esito analisi

La parte DB principale risulta implementata, ma resta da completare il raccordo operativo lato servizio/API per blocchi e visibilita` runtime.

## 4.2 Bozza interventi

1. Rafforzare il blocco avanzamento step includendo anche lo stato ponte:
   - non solo `critical` da log;
   - anche presenza `stato_esecuzione='ERRORE'` su `fatturazione_lotti_fatture`.
2. Unificare query di riepilogo blocchi lotto:
   - estendere `fn_get_lotto_segnalazioni_summary` o aggiungere funzione sorella che includa il ponte.
3. Completare esposizione API dettaglio lotto/fatture:
   - stato documento ponte
   - stato esecuzione
   - critical documento
4. Rendere esplicita la policy "partial failure":
   - quando il lotto puo` proseguire
   - quando deve fermarsi
   - come si comporta il rerun.

## 4.3 Deliverable minimi

- Funzione summary blocchi aggiornata.
- Runner lotto aggiornato con guard unificata.
- Test Django/pgtap su casi:
  - `critical=true` blocca
  - `stato_esecuzione=ERRORE` blocca
  - warning non blocca.

## 5) Ripartenza pipeline attivita_fatturabili (modello non lineare)

Premessa funzionale confermata:
- la pipeline attivita deve essere piu` libera della pipeline lotto;
- rami indipendenti per sorgente (es. PREVENTIVI, ORDINI) non devono bloccarsi automaticamente tra loro.

## 5.1 Modello proposto

1. Esecuzione per branch indipendente (`branch_code`).
2. Dipendenze esplicite opzionali (`depends_on` in `meta`).
3. Politica blocco configurabile:
   - `block_scope = BRANCH` (default)
   - `block_scope = GLOBAL`.
4. Resume/rerun per branch, non per intera pipeline.

Nota implementativa — precedenza `block_scope`:
`block_scope` compare in entrambe le tabelle: `attivita_fatturabili_pipeline_task_policy` (livello task)
e `attivita_fatturabili_sorgenti_branch_policy` (livello sorgente/branch).
Regola adottata: il valore nella **task policy ha precedenza** (piu` specifico);
se la task policy non definisce un override esplicito, si usa il valore della sorgente branch policy.
Questa logica va implementata nell'executor (BE-1.2) e non nel runner.

## 5.2 Estensioni schema (bozza)

Su `vendite.attivita_fatturabili_pipeline`:
- `branch_code text` (default `DEFAULT`)
- `block_scope text` (`BRANCH|GLOBAL`)
- `depends_on jsonb` (opzionale)

Nuove tabelle speculari a lotto:
- `vendite.attivita_fatturabili_pipeline_task_policy`
- `vendite.attivita_fatturabili_lotti_task_runs`

## 5.3 Runtime Django (bozza)

Nuovi componenti:
- `AttivitaPipelineRunner`
- `AttivitaPipelineStepExecutor`
- repository dedicato `AttivitaPipelineRepository`

Regole minime:
- dispatch via registry DB dominio `ATTIVITA_FATTURABILI`
- tracing task run per branch
- blocco solo nel branch salvo policy `GLOBAL`.

## 5.4 Allineamento strutturale con fatturazione_lotti (nuovo delta richiesto)

Obiettivo: ridurre divergenze semantiche tra pipeline `fatturazione_lotti` e `attivita_fatturabili_lotti`, cosi` da riusare pattern runtime, test e API.

### Delta schema proposto

1. `vendite.attivita_fatturabili_lotti`
   - aggiungere `stato_operativo text not null default 'APERTO'`
   - aggiungere `emittente_soggetto_ruolo_id bigint null references anagrafica.soggetti_ruoli(id)`
   - mantenere `stato_lotto` come stato tecnico pipeline; usare `stato_operativo` come stato business.
2. `vendite.attivita_fatturabili`
   - aggiungere `stato_esecuzione text not null default 'PENDING'`
   - vincolo check su set coerente con fatturazione (`PENDING|RUNNING|COMPLETED|ERRORE`).

Nota progettuale:
- `stato_lotto` e` il runtime della pipeline.
- `stato_operativo` e` la visione funzionale del lotto (aperto/chiuso/annullato).
- `stato_esecuzione` su riga attivita e` lo stato tecnico puntuale, analogo a `fatturazione_lotti_fatture.stato_esecuzione`.
- Allineamento trasversale confermato: anche `fatturazione_lotti_fatture.stato_esecuzione` converge su `PENDING|RUNNING|COMPLETED|ERRORE` (superato legacy `OK|ERRORE`).

### Impatti funzione/facade da introdurre o adeguare

1. `fn_get_or_create_lotto_attivita(...)`
   - valorizzare anche `emittente_soggetto_ruolo_id` (fallback coerente al dominio vendite).
   - impostare default `stato_operativo='APERTO'`.
2. `fn_set_attivita_lotto_stato(...)` (nuova o estensione della funzione stato esistente)
   - separare aggiornamento `stato_lotto` (tecnico) da `stato_operativo` (business).
3. `fn_sync_attivita_stato_esecuzione(...)` (nuova)
   - sincronizzazione batch per `lotto_attivita_id`.
   - mapping esito task/pipeline -> `stato_esecuzione` righe attivita.
4. Funzioni di summary/segnalazioni lotto attivita
   - includere conteggi per `stato_esecuzione` e condizioni bloccanti.

### Policy runtime da rendere esplicita

1. Errore su task di branch A:
   - blocca solo branch A se `block_scope='BRANCH'`.
   - blocca tutto se `block_scope='GLOBAL'`.
2. `stato_operativo` lotto:
   - transizioni autorizzate solo da punti di controllo espliciti (no update casuali da task interni).
3. `stato_esecuzione` righe attivita:
   - aggiornato dal runner/executor, non da API CRUD standard.

### Migrazioni e retrofit dati

1. Migrazione schema:
   - add colonne + default + check + FK.
2. Backfill iniziale:
   - `attivita_fatturabili_lotti.stato_operativo='APERTO'` dove null.
   - `attivita_fatturabili.stato_esecuzione='PENDING'` dove null.
3. Hardening:
   - indice su `attivita_fatturabili(lotto_attivita_id, stato_esecuzione)`.
   - indice opzionale su `attivita_fatturabili_lotti(stato_operativo)`.

### Test minimi da aggiungere

1. pgTAP
   - DDL: colonne, default, vincoli, FK.
   - funzione get/create lotto con emittente.
   - sync stato esecuzione su righe attivita.
2. Django services
   - errore branch A non blocca branch B con `BRANCH`.
   - errore global blocca run con `GLOBAL`.
   - transizioni valide `stato_operativo`.
3. API
   - risposta status lotto attivita con `stato_lotto`, `stato_operativo`, conteggi `stato_esecuzione`.

### Decisione architetturale raccomandata

Le where testuali su `codice/descrizione` restano fuori dalle funzioni core di pipeline (gestione in API/repository), per non mescolare logica runtime con logica di ricerca UI/autocomplete.

## 5.5 Avanzamento implementato (22-02-2026)

### DB completato su lotti/stati

1. `attivita_fatturabili_lotti`
   - aggiunti `stato_operativo` e `emittente_soggetto_ruolo_id`.
2. `attivita_fatturabili`
   - aggiunto `stato_esecuzione` con vincolo che ammette `NULL` fuori pipeline.
3. `fatturazione_lotti_fatture`
   - `stato_esecuzione` unificato a `PENDING|RUNNING|COMPLETED|ERRORE`.

### Funzioni introdotte/aggiornate

1. Nuove funzioni dominio attivita:
   - `vendite.fn_get_or_create_lotto_attivita(...)`
   - `vendite.fn_set_attivita_lotto_stato(...)`
   - `vendite.fn_sync_attivita_stato_esecuzione(...)`
2. Refactor funzioni esistenti:
   - `vendite.fn_select_attivita_fatturabili(...)` -> lock imposta `PENDING`.
   - `vendite.fn_generate_fatture_righe(...)` -> `RUNNING`/`COMPLETED`.
   - `vendite.fn_cleanup_fatture_by_ids(...)` -> reset `stato_esecuzione = NULL`.
3. Allineamento fatturazione:
   - aggiornate funzioni lotto/fatture a nuovi stati esecuzione (`RUNNING/COMPLETED/ERRORE`).

### Refactor deduplicazione (prima conferma)

1. Introdotto helper condiviso:
   - `vendite.fn_resolve_lotto_utility_emittente(...)`
2. Riutilizzo helper in:
   - `vendite.fn_get_or_create_lotto(...)`
   - `vendite.fn_get_or_create_lotto_attivita(...)`
3. Effetto:
   - una sola logica centralizzata per coerenza `billing_account`/`utility`/`emittente` e fallback emittente default.

### Refactor deduplicazione (seconda conferma)

1. Introdotto helper condiviso:
   - `vendite.fn_resolve_stato_esecuzione(...)`
2. Riutilizzo helper in:
   - `vendite.fn_set_fatturazione_lotto_stato(...)`
   - `vendite.fn_sync_lotto_fatture_stato(...)`
   - `vendite.fn_sync_fatture_log_critical_lotto(...)`
   - `vendite.fn_sync_attivita_stato_esecuzione(...)`
3. Effetto:
   - mapping runtime centralizzato (`PENDING|RUNNING|COMPLETED|ERRORE`) e riduzione drift tra dominio lotti e dominio attivita.

## 5.6 Decisioni sorgenti e ambito operativo (22-02-2026)

Decisione confermata: avanzare prima sul dominio `attivita_fatturabili` e
gestire l'upstream in fasi successive, con ambito sorgenti controllato.

### Sorgenti nell'ambito (fase corrente)

1. `PREVENTIVO`
2. `CONTRATTO`
3. `ORDINE_VENDITA`
4. `ATTIVITA`
5. `ATTIVITA_CONSUMI`

Regola lotto attivita:
- convergenza nello stesso lotto solo se coerente con perimetro fiscale/operativo
  (competenza, utility, tipo_doc, emittente; opzionale BA);
- la pipeline/policy decide quali branch possono convivere nello stesso lotto.

### Sorgenti temporaneamente escluse (posticipate)

1. Tutte le sorgenti `*_RIGA`
   - motivo: fase iniziale orientata a livello testata/documento;
   - rischio: duplicazioni e deduplica prematura complessa.
2. `FATTURA` e `FATTURA_RIGA`
   - motivo: nel flusso target le fatture sono output, non input di alimentazione standard;
   - possibile riuso futuro su canali dedicati (rettifiche/import esterni/reconciliation).
3. `DDT_VENDITA` e `DDT_VENDITA_RIGA`
   - motivo: sovrapposizione frequente con `ORDINE_VENDITA` e rischio doppio conteggio;
   - riattivazione solo con policy esplicita di precedenza/deduplica.

### Backlog esplicito da riprendere

1. Definire policy di precedenza tra `ORDINE_VENDITA` e `DDT_VENDITA`.
2. Valutare reintroduzione selettiva delle sorgenti `*_RIGA` per casi a granularita` articolo.
3. Definire se e come usare `FATTURA*` come sorgente eccezionale fuori pipeline standard.

### Implementazione DB matrice sorgenti (22-02-2026)

Introdotta matrice esplicita `sorgente -> branch/policy` per evitare mapping hardcoded lato backend:

1. Tabella:
   - `vendite.attivita_fatturabili_sorgenti_branch_policy`
   - campi principali: `sorgente_tipo_id`, `branch_code`, `abilitata`, `acquisizione_mode`, `block_scope`, `priorita`, `meta`.
2. Funzione di risoluzione:
   - `vendite.fn_resolve_attivita_sorgente_branch_policy(p_sorgente_tipo_id, p_require_abilitata)`
3. Seed iniziale:
   - sorgenti nell'ambito abilitate (`PREVENTIVO`, `CONTRATTO`, `ORDINE_VENDITA`, `ATTIVITA`, `ATTIVITA_CONSUMI`);
   - sorgenti posticipate marcate `abilitata=false` (`*_RIGA`, `DDT*`, `FATTURA*`).
4. Registry task dominio `ATTIVITA_FATTURABILI` seedato in `dbops`:
   - `acquisisci_preventivi`
   - `acquisisci_contratti`
   - `acquisisci_ordini`
   - `acquisisci_attivita_consumi`
   - `normalizza_attivita`
   - `valida_attivita`
   - `deduplica_attivita`
   con relative implementazioni `*_default` in `dbops.pipeline_task_registry_impl`.

## 6) Ordine di esecuzione consigliato

1. Chiudere punto 20 (routing errori e ownership dominio attivita).
2. Chiudere punto 21 lato servizio/API (blocchi su `critical` + `stato_esecuzione`).
3. Applicare delta schema allineamento (`stato_operativo`, `emittente_soggetto_ruolo_id`, `stato_esecuzione`).
4. Introdurre runtime attivita (runner/executor/task-runs/policy).
5. Esporre API attivita (run, status, task-runs).
6. Aggiungere test pgtap + Django + smoke API.

## 7) Definition of done (ripresa attivita)

- Punto 20 e 21 chiusi con test.
- Delta schema allineamento lotto/attivita applicato e coperto da test.
- Pipeline attivita eseguibile almeno su due branch:
  - import da preventivi
  - import da ordini
- Fallimento branch A non blocca branch B (se `block_scope=BRANCH`).
- API e log permettono diagnosi completa per branch/task.

## 8) Piano operativo esecutivo (DB -> Backend -> Go-live)

Obiettivo operativo: completare il dominio `attivita_fatturabili` con logiche omogenee a `fatturazione_lotti`, riducendo refactor futuri e rischi di regressione.

### 8.1 Fase DB-1 (schema allineamento) — ✓ COMPLETATA

1. Changelog: aggiungere colonne e vincoli
   - `vendite.attivita_fatturabili_lotti.stato_operativo` (`not null`, default `APERTO`)
   - `vendite.attivita_fatturabili_lotti.emittente_soggetto_ruolo_id` (`bigint`, FK)
   - `vendite.attivita_fatturabili.stato_esecuzione` (`not null`, default `PENDING`)
   - check `stato_esecuzione in ('PENDING','RUNNING','COMPLETED','ERRORE')`
2. Backfill dati esistenti
   - valorizzazione default su righe storiche.
3. Hardening
   - indice `attivita_fatturabili(lotto_attivita_id, stato_esecuzione)`
   - indice opzionale `attivita_fatturabili_lotti(stato_operativo)`

Uscita fase:
- migrazione applicabile in ambiente pulito e su snapshot reale.
- nessun null residuo su nuove colonne obbligatorie.

### 8.2 Fase DB-2 (funzioni dominio attivita) — ✓ COMPLETATA

1. Adeguare `fn_get_or_create_lotto_attivita(...)`
   - supporto pieno `emittente_soggetto_ruolo_id`
   - default coerente `stato_operativo='APERTO'`.
2. Introdurre/adeguare funzione stato lotto
   - separazione `stato_lotto` (tecnico) vs `stato_operativo` (business).
3. Introdurre `fn_sync_attivita_stato_esecuzione(...)`
   - sync batch per lotto.
   - mapping esiti pipeline/task.
4. Adeguare funzioni di summary
   - conteggi `stato_esecuzione` e blocchi.

Uscita fase:
- SQL installabile senza dipendenze circolari.
- funzioni idempotenti sui rerun.
- avanzamento 22-02-2026:
  - `20260222-10` creata `vendite.attivita_fatturabili_pipeline_task_policy` (policy branch/global).
  - `20260222-11` creata `vendite.attivita_fatturabili_lotti_task_runs` (tracing runtime task per branch).
  - `20260222-12` introdotte funzioni runtime task-runs/policy dedicate al dominio attivita.

### 8.3 Fase DB-3 (test pgtap obbligatori) — ✓ COMPLETATA

1. DDL checks: colonne/default/FK/check.
2. Test funzioni:
   - get/create lotto con emittente.
   - transizioni stato lotto/operativo ammesse e non ammesse.
   - sync `stato_esecuzione` per lotto.
3. Test blocchi:
   - errore tecnico rilevabile da summary.

Uscita fase:
- suite pgtap del dominio verde.

### 8.4 Fase BE-1 (runtime services) — ✓ COMPLETATA

1. Implementare/chiudere:
   - `AttivitaPipelineRunner`
   - `AttivitaPipelineStepExecutor`
   - `AttivitaPipelineRepository`
2. Routing errori:
   - envelope standard con `scope=ATTIVITA_FATTURABILI`.
3. Policy branch/global:
   - `BRANCH` non blocca gli altri branch.
   - `GLOBAL` blocca run.
4. Sync stato:
   - aggiornamento `stato_esecuzione` da runtime (non da CRUD).

Uscita fase:
- esecuzione pipeline su branch indipendenti con tracing task.
- avanzamento 22-02-2026:
  - `backend/apps/vendite/db/attivita_pipeline_repository.py` creato (BE-1.1).
  - `backend/apps/vendite/services/attivita_pipeline_step_executor.py` creato (BE-1.2); 7 handler stub registrati.
  - `backend/apps/vendite/services/attivita_pipeline_runner.py` creato (BE-1.3); branch-first con `_AttivitaBranchBlockError`/`_AttivitaGlobalBlockError`.
  - `backend/apps/vendite/services/attivita_pipeline_error_logger.py` creato (BE-1.5).
  - `backend/apps/vendite/types.py` esteso con `AttivitaTaskRunRow`.
  - 26 test unitari aggiunti (repository 12, executor 8, runner 6); suite verde (98 test ok).

### 8.5 Fase BE-2 (API dominio attivita) — ✓ COMPLETATA

1. Endpoint run pipeline attivita.
2. Endpoint status/segnalazioni.
3. Endpoint task-runs.
4. DTO risposta:
   - `stato_lotto`
   - `stato_operativo`
   - riepilogo `stato_esecuzione`.

Uscita fase:
- API consumabile da UI e pronta per debug operativo.
- avanzamento 23-02-2026:
  - `backend/apps/vendite/db/attivita_pipeline_repository.py` esteso con `get_lotto_attivita_full_stato`.
  - `backend/apps/vendite/services/attivita_pipeline_service.py` creato (BE-2.1/2.2/2.3); facade `pr_run_attivita_pipeline`, `fn_get_attivita_pipeline_status`, `fn_get_attivita_task_runs`.
  - `backend/apps/vendite/api/views.py` esteso con 6 view classes (3 base + 3 V1).
  - `backend/apps/vendite/api/urls_v1.py` esteso con 3 path `attivita_fatturabili/pipeline/*`.
  - 6 test unitari aggiunti (service); suite verde (104 test ok).

### 8.6 Fase BE-3 (test backend/API) — ✓ COMPLETATA

1. Test service:
   - run ok
   - errore branch non blocca altri branch (`BRANCH`)
   - errore global blocca (`GLOBAL`)
2. Test API:
   - run/status/task-runs
   - envelope errori coerente
3. Smoke:
   - branch PREVENTIVI + ORDINI nello stesso lotto.

Uscita fase:
- suite backend verde e smoke senza blocchi inattesi.

Avanzamento 23-02-2026 (BE-3):

- Creati `backend/apps/vendite/tests/api/test_attivita_pipeline_api.py` (14 test HTTP contract).
- Creato `backend/apps/vendite/tests/api/test_attivita_pipeline_smoke.py` (3 smoke multi-branch).
- Suite verde: 174 test ok (tutti i test `apps.vendite.tests` incluse regressioni lotto).

### 8.7 Sequenza di avvio sviluppo (operativa)

1. Aprire changelog DB-1 (nuovo changeset).
2. Implementare DB-2.
3. Eseguire e chiudere DB-3.
4. Passare a backend BE-1.
5. Esporre BE-2.
6. Chiudere BE-3 e checklist DoD.

Nota:
- Le ricerche testuali (`codice/descrizione`, autocomplete, `ilike`) restano in API/repository, non nelle funzioni core pipeline.

### Seed operativo iniziale (go-live)

Definito profilo idempotente `GO_LIVE_INITIAL` su matrice sorgenti:

1. nell'ambito abilitate:
   - `ATTIVITA`
   - `PREVENTIVO`
   - `CONTRATTO`
   - `ORDINE_VENDITA`
   - `ATTIVITA_CONSUMI`
2. fuori ambito iniziale (`abilitata=false`):
   - tutte le `*_RIGA`
   - `DDT_VENDITA` / `DDT_VENDITA_RIGA`
   - `FATTURA` / `FATTURA_RIGA`
3. seed applicato via upsert per codice sorgente (non dipende da id hardcoded) in:
   - `migrations_v2/80_data/changelog/20260222-18-set-attivita-sorgenti-go-live-profile-mctit.yaml`.

Obiettivo:
- eliminare ambiguita` in avvio BE-1/BE-2, delegando al DB la policy sorgente/branch.

## 9) Sviluppi Backend Da Implementare (handover)

Stato prerequisiti DB per backend:
- completati (schema, funzioni core, policy/task-runs runtime, matrice sorgenti->branch/policy, seed go-live, pgtap verde).

### 9.1 BE-1 Runner/Orchestrazione (obbligatorio)

Implementare il runtime dominio `ATTIVITA_FATTURABILI` con semantica branch-first:

1. Componenti applicativi:
   - `AttivitaPipelineRunner`
   - `AttivitaPipelineStepExecutor`
   - `AttivitaPipelineRepository`
2. Regole orchestrazione:
   - risoluzione policy sorgente tramite `vendite.fn_resolve_attivita_sorgente_branch_policy(...)`;
   - esecuzione indipendente per `branch_code`;
   - blocco perimetrale su `block_scope`:
     - `BRANCH`: blocca solo il branch corrente;
     - `GLOBAL`: interrompe l'intero run.
3. Stato runtime:
   - aggiornare `attivita_fatturabili.stato_esecuzione` solo da runner/executor;
   - sincronizzare stati lotto con funzioni DB dedicate (`fn_set_attivita_lotto_stato`, `fn_sync_attivita_stato_esecuzione`).
4. Error handling:
   - envelope standard con `scope=ATTIVITA_FATTURABILI`;
   - distinzione errori tecnici bloccanti vs non bloccanti coerente con policy.

Acceptance BE-1:
- run multi-branch nello stesso lotto senza blocchi incrociati in modalita` `BRANCH`;
- tracing task persistito su `attivita_fatturabili_lotti_task_runs`;
- rerun/resume branch isolato funzionante.

### 9.2 BE-2 API Operative (obbligatorio)

Esporre API minime per uso UI/ops:

1. `POST /api/v1/vendite/attivita_fatturabili/pipeline/run`
   - input: lotto o criteri creazione lotto + filtro sorgenti/branch opzionale;
   - output: id run/lotto + stato iniziale per branch.
2. `GET /api/v1/vendite/attivita_fatturabili/pipeline/{lotto_id}/status`
   - output: `stato_lotto`, `stato_operativo`, riepilogo `stato_esecuzione` per branch.
3. `GET /api/v1/vendite/attivita_fatturabili/pipeline/{lotto_id}/task-runs`
   - output: lista task run ordinata per sequenza/tentativo con esito e dettagli errore.

Nota convenzioni URL: snake_case e prefisso `/api/v1/vendite/` coerenti con gli endpoint esistenti
(es. `/api/v1/vendite/lotti/{id}/fatture/`). Non usare kebab-case.

Regole API:
- nessun mapping hardcoded sorgente->branch lato Python: usare solo resolver DB;
- error envelope uniforme e tracciabile (code, ambito, severity, context).

Acceptance BE-2:
- endpoint run/status/task-runs disponibili e coerenti con dati DB runtime;
- contratti DTO stabili per UI (branch-level visibility).

### 9.3 BE-3 Test Backend/API (obbligatorio prima del go-live)

1. Test service:
   - success path multi-branch;
   - errore in branch A non blocca B con `BRANCH`;
   - errore `GLOBAL` interrompe run.
2. Test API:
   - run/status/task-runs;
   - envelope errori coerente con standard dominio.
3. Smoke end-to-end:
   - sorgenti abilitate `PREVENTIVO` + `ORDINE_VENDITA` nello stesso lotto;
   - verifica `task_runs`, stati e riepiloghi finali.

Acceptance BE-3:
- suite backend verde;
- nessuna regressione su pipeline lotto esistente.

### 9.4 Attivita` esplicitamente fuori ambito backend immediato

1. Reintroduzione `DDT_VENDITA*`.
2. Reintroduzione `FATTURA*` come input standard.
3. Supporto sorgenti `*_RIGA`.

Nota:
- queste sorgenti restano governate da policy DB (`abilitata=false`) fino a decisione successiva.

### 9.5 Sequenza operativa consigliata per team backend

1. Implementare BE-1 (runner/repository/executor).
2. Implementare BE-2 (API run/status/task-runs).
3. Chiudere BE-3 (test + smoke).
4. Eseguire handover UI con contratti endpoint consolidati.

## 10) Checklist Ticket-Ready Backend (Jira/GitHub)

Legenda:
- tipo: `EPIC`, `STORY`, `TASK`, `TEST`
- priorita`: `P0` blocca go-live, `P1` necessario, `P2` migliorativo

### 10.0 Prerequisiti backend — ✓ COMPLETATI

I deliverable Django dei punti 20 e 21 (§3.3 e §4.3) non sono coperti dai ticket BE-1/BE-2/BE-3
e devono essere completati prima di aprire BE-1, pena regressioni sul runner lotto esistente.

1. `PRE-1` (TASK, P0) ✓ - aggiornare guard runner lotto (§4.3)
   - output:
     - `pipeline_repository.py`: nuovo metodo `count_fatture_stato_esecuzione_errore(lotto_id)`.
     - `lotto_segnalazioni_service.py`: `LottoSignalStatus` con campo `fatture_stato_esecuzione_errore_count`;
       `evaluate_lotto_status` blocca se `critical_count > 0 OR stato_esecuzione_errore_count > 0`.
     - `pipeline_runner.py`: detail e context arricchiti con `stato_esecuzione_errore_count`.
   - done:
     - test 14/15 in `test_pipeline_runner.py`: `stato_esecuzione=ERRORE` blocca; warning non blocca.
     - test 3 in `test_lotto_segnalazioni_service.py`: guard su ponte verificata a livello service.

2. `PRE-2` (TASK, P0) ✓ - codici errore dominio attivita (§3.3)
   - output:
     - `error_policies.py`: aggiunti `E_ATTIVITA_PIPELINE` (HTTP 400), `E_ATTIVITA_VALIDATION` (HTTP 400),
       `E_ATTIVITA_LOTTO_NOT_FOUND` (HTTP 404).
   - done:
     - codici errore `E_ATTIVITA_*` disponibili nel registry; il runner attivita (BE-1) li usera`.
   - nota: helper payload `build_pipeline_error_context` rimandato a BE-1.5 (contesto piu` ricco).

### 10.1 EPIC BE-ATT-PIPELINE

1. `BE-ATT-PIPELINE` (EPIC, P0)
   - obiettivo: completare runtime/API/test dominio `ATTIVITA_FATTURABILI`.
   - done: tutte le story 10.2-10.4 chiuse e smoke verdi.

### 10.2 Story BE-1 (runtime)

1. `BE-1.1` (TASK, P0) - creare `AttivitaPipelineRepository`
   - output:
     - metodi lettura step/policy/task registry;
     - integrazione resolver `vendite.fn_resolve_attivita_sorgente_branch_policy(...)`.
   - done:
     - nessun mapping hardcoded sorgente->branch in codice.

2. `BE-1.2` (TASK, P0) - creare `AttivitaPipelineStepExecutor`
   - output:
     - dispatch task via registry dominio `ATTIVITA_FATTURABILI`;
     - gestione esiti `SUCCESS|WARNING|ERROR`;
     - `handler_registry` Python (dict statico `handler_code -> callable`) per tutti i task
       seedati in `dbops.pipeline_task_registry_impl` del dominio:
       `acquisisci_preventivi_default`, `acquisisci_contratti_default`,
       `acquisisci_ordini_default`, `acquisisci_attivita_consumi_default`,
       `normalizza_attivita_default`, `valida_attivita_default`, `deduplica_attivita_default`.
   - done:
     - supporto `block_scope=BRANCH|GLOBAL` rispettato (task policy ha precedenza su sorgente policy);
     - nessun import dinamico: mapping statico come in `PipelineStepExecutor` del dominio lotto;
     - stub funzionanti per tutti e 7 gli handler (anche se non implementati nel dettaglio).

3. `BE-1.3` (TASK, P0) - creare `AttivitaPipelineRunner`
   - output:
     - orchestrazione per branch indipendente;
     - resume/rerun branch-level;
     - stato run finale aggregato.
   - done:
     - errore branch non blocca altri branch con policy `BRANCH`.

4. `BE-1.4` (TASK, P0) - integrazione stato DB runtime
   - output:
     - sync `attivita_fatturabili.stato_esecuzione`;
     - sync stati lotto via funzioni DB esistenti.
   - done:
     - nessun update stati runtime da endpoint CRUD generici.

5. `BE-1.5` (TASK, P1) - envelope errori unificato
   - output:
     - payload standard (`scope`, `severity`, `code`, `context`).
   - done:
     - `scope=ATTIVITA_FATTURABILI` in tutte le eccezioni dominio.

### 10.3 Story BE-2 (API)

1. `BE-2.1` (TASK, P0) - endpoint run
   - output:
     - `POST /api/v1/vendite/attivita_fatturabili/pipeline/run`.
   - done:
     - supporto input con lotto esistente o creazione guidata.

2. `BE-2.2` (TASK, P0) - endpoint status
   - output:
     - `GET /api/v1/vendite/attivita_fatturabili/pipeline/{lotto_id}/status`.
   - done:
     - include `stato_lotto`, `stato_operativo`, contatori `stato_esecuzione` per branch.

3. `BE-2.3` (TASK, P0) - endpoint task-runs
   - output:
     - `GET /api/v1/vendite/attivita_fatturabili/pipeline/{lotto_id}/task-runs`.
   - done:
     - ordinamento coerente (step, sequenza, tentativo, timestamp).

4. `BE-2.4` (TASK, P1) - DTO/API contract
   - output:
     - schema response versionato e documentato.
   - done:
     - contract stabile condivisibile a UI/ops.

### 10.4 Story BE-3 (test e hardening)

1. `BE-3.1` (TEST, P0) - unit test runner/executor
   - casi:
     - success multi-branch;
     - errore branch isolato (`BRANCH`);
     - errore globale (`GLOBAL`).
   - done:
     - coverage minima target su servizi runtime (definita dal team BE).

2. `BE-3.2` (TEST, P0) - API test run/status/task-runs
   - casi:
     - HTTP code;
     - payload successo;
     - payload errore standard.
   - done:
     - tutti i casi verdi in CI.

3. `BE-3.3` (TEST, P0) - smoke E2E dominio attivita
   - casi:
     - run con `PREVENTIVO` + `ORDINE_VENDITA`;
     - verifica esiti su task-runs e stati finali.
   - done:
     - nessuna regressione funzionale su pipeline lotto esistente.

### 10.5 Dipendenze e ordine di esecuzione

1. Sequenza:
   - `BE-1.1` -> `BE-1.2` -> `BE-1.3` -> `BE-1.4` -> `BE-1.5`
   - `BE-2.1`/`BE-2.2`/`BE-2.3` -> `BE-2.4`
   - `BE-3.1` -> `BE-3.2` -> `BE-3.3`
2. Gate:
   - non aprire `BE-1` senza `PRE-1` e `PRE-2` chiusi.
   - non aprire `BE-2` senza runner stabile (`BE-1.3` minimo).
   - non chiudere epic senza smoke `BE-3.3`.

---

## §11) Migliorie DB future (riduzione logica backend)

Raccolta di interventi DB che semplificherebbero o eliminerebbero logica duplicata
nel layer Python. Da pianificare dopo il completamento di BE-1/BE-2/BE-3.
Non bloccano nessun ticket corrente.

### §11.1 Unificare query blocco lotto in `fn_get_lotto_segnalazioni_summary`

**Contesto**: `evaluate_lotto_status` in `lotto_segnalazioni_service.py` esegue
attualmente due query DB separate per valutare se il lotto e` bloccato:

1. `get_lotto_segnalazioni_summary()` — chiama `vendite.fn_get_lotto_segnalazioni_summary`
   e restituisce i contatori segnalazioni per severita`.
2. `count_fatture_stato_esecuzione_errore()` — query diretta su
   `vendite.fatturazione_lotti_fatture` per contare le fatture con
   `stato_esecuzione = 'ERRORE'`.

**Miglioramento**: estendere `vendite.fn_get_lotto_segnalazioni_summary` per
restituire anche la colonna `fatture_stato_esecuzione_errore_count`
(COUNT su `fatturazione_lotti_fatture.stato_esecuzione = 'ERRORE'`).
Questo eliminerebbe la seconda query e ridurrebbe i round-trip DB per ogni
valutazione blocco lotto.

**Impatto backend**:

- rimuovere il metodo `count_fatture_stato_esecuzione_errore` dal repository;
- leggere `fatture_stato_esecuzione_errore_count` direttamente dal summary
  restituito dalla funzione DB;
- aggiornare `evaluate_lotto_status` di conseguenza (nessun cambio all'interfaccia
  pubblica di `LottoSignalStatus`).

**Stato avanzamento (23-02-2026, DB): COMPLETATO**

Implementato lato DB:

1. Estesa funzione SQL:
   - `vendite.fn_get_lotto_segnalazioni_summary(p_lotto_id bigint)`
   - nuova colonna output in coda: `fatture_stato_esecuzione_errore_count`.
2. Nuova aggregazione:
   - `COUNT(*) FILTER (WHERE stato_esecuzione='ERRORE')` su
     `vendite.fatturazione_lotti_fatture` per il lotto richiesto.
3. Compatibilita`:
   - nessuna funzione SQL dipendente da aggiornare (uso DB interno: assente);
   - estensione non breaking lato SQL per consumer che selezionano esplicitamente colonne.
4. Test DB:
   - aggiunto pgTAP `db/pgtap/vendite/test-lotto-segnalazioni-summary-v2.sql`;
   - aggiunto alla suite `scripts/testpgtap-fatturazione-logs.sh`.

**Azione richiesta al team backend (integrazione)**

1. Repository:
   - includere la nuova colonna nel mapping `get_lotto_segnalazioni_summary`.
2. Service:
   - rimuovere query separata `count_fatture_stato_esecuzione_errore`;
   - usare solo il summary funzione DB per il blocco lotto.

**Integrazione backend (23-02-2026): COMPLETATA**

- `types.py`: aggiunto `fatture_stato_esecuzione_errore_count` a `LottoSegnalazioniSummary`.
- `pipeline_repository.py`: SELECT esteso a 6 colonne; rimosso metodo `count_fatture_stato_esecuzione_errore`.
- `lotto_segnalazioni_service.py`: `evaluate_lotto_status` legge `summary["fatture_stato_esecuzione_errore_count"]`.
- Test aggiornati: `test_pipeline_repository.py`, `test_lotto_segnalazioni_service.py`, `test_pipeline_runner.py`.

### §11.2 Spostare `_compute_branch_summary` nel DB

**Contesto**: `fn_get_attivita_pipeline_status` in `attivita_pipeline_service.py`
recupera fino a 500 task run dal DB (`list_attivita_task_runs(limit=500)`)
solo per aggregarli in Python via `_compute_branch_summary`:

```python
{"DEFAULT": {"COMPLETATO": 3}, "PREVENTIVI": {"COMPLETATO": 2, "ERRORE": 1}}
```

Il trasferimento di 500 righe complete per estrarre solo i contatori e` inefficiente.

**Miglioramento**: creare `vendite.fn_get_attivita_branch_summary(lotto_id)`:

```sql
SELECT branch_code, task_stato, COUNT(*) AS cnt
FROM vendite.attivita_fatturabili_lotti_task_runs
WHERE lotto_attivita_id = lotto_id
GROUP BY branch_code, task_stato
```

**Impatto backend**:

- sostituire `repo.list_attivita_task_runs(limit=500)` + `_compute_branch_summary`
  con `repo.get_attivita_branch_summary(lotto_id)`;
- eliminare `_compute_branch_summary` dal service;
- riduce i dati trasmessi DB→Python per ogni richiesta status da N righe a M bucket.

**Stato avanzamento (23-02-2026, DB): COMPLETATO**

Implementato lato DB:

1. Nuova funzione SQL:
   - `vendite.fn_get_attivita_branch_summary(p_lotto_attivita_id bigint)`
   - output: `branch_code`, `task_stato`, `cnt`.
2. Validazione parametro:
   - errore se `lotto_attivita_id` nullo o `<= 0`.
3. Aggregazione:
   - `GROUP BY branch_code, task_stato` su `vendite.attivita_fatturabili_lotti_task_runs`.
4. Test DB:
   - aggiunto pgTAP `db/pgtap/vendite/test-attivita-branch-summary-v1.sql`.
   - aggiunto alla suite `scripts/testpgtap-fatturazione-logs.sh`.

**Azione richiesta al team backend (integrazione)**

1. Repository:
   - introdurre metodo `get_attivita_branch_summary(lotto_id)` che legge la nuova funzione DB.
2. Service status:
   - sostituire la logica attuale (`list_attivita_task_runs(limit=500)` + `_compute_branch_summary`).
3. Pulizia codice:
   - rimuovere `_compute_branch_summary` dal service una volta agganciato il repository.

**Integrazione backend (23-02-2026): COMPLETATA**

- `attivita_pipeline_repository.py`: aggiunto `get_attivita_branch_summary` che chiama `fn_get_attivita_branch_summary`.
- `attivita_pipeline_service.py`: `fn_get_attivita_pipeline_status` usa `repo.get_attivita_branch_summary`; rimossa `_compute_branch_summary`.
- Test: aggiunto `test_get_attivita_branch_summary_returns_dict` in `test_attivita_pipeline_repository.py`; aggiornato `test_attivita_pipeline_service.py`.

### §11.3 Sostituire query dirette su `attivita_fatturabili_lotti` con funzione DB

**Contesto**: `AttivitaPipelineRepository` contiene tre metodi con SELECT separati
sulla stessa tabella `vendite.attivita_fatturabili_lotti`:

- `get_lotto_attivita_stato` — solo `stato_lotto`
- `get_lotto_attivita_full_stato` — `stato_lotto` + `stato_operativo`
- `is_lotto_attivita_in_esecuzione` — `stato_lotto = 'IN_ESECUZIONE'`

Ogni metodo apre un cursore separato per leggere lo stesso record.

**Miglioramento**: creare `vendite.fn_get_attivita_lotto_info(lotto_id)`
che restituisce `(stato_lotto, stato_operativo, is_in_esecuzione)` in un
unico round-trip. I tre metodi Python diventerebbero delegati dello stesso metodo
repository `get_lotto_attivita_info(lotto_id)`.

**Impatto backend**: riduce i round-trip DB nel flusso runner (che chiama
`is_lotto_attivita_in_esecuzione` all'avvio e poi eventualmente `get_lotto_attivita_stato`).

**Stato avanzamento (23-02-2026, DB): COMPLETATO**

Implementato lato DB:

1. Nuova funzione SQL:
   - `vendite.fn_get_attivita_lotto_info(p_lotto_id bigint)`
   - output: `stato_lotto`, `stato_operativo`, `is_in_esecuzione`.
2. Regole:
   - validazione `lotto_id` obbligatorio e `> 0`;
   - lotto inesistente -> 0 righe.
3. Test DB:
   - aggiunto pgTAP `db/pgtap/vendite/test-attivita-lotto-info-v1.sql`;
   - aggiunto alla suite `scripts/testpgtap-fatturazione-logs.sh`.

   > ⚠️ **Nota del 2026-08-18 — quel file non esiste piu'.** E' stato cancellato
   > perche' testava solo `vendite.fn_get_attivita_lotto_info` e
   > `vendite.fn_get_or_create_lotto_attivita`, entrambe rimosse dal
   > `20260227-16`, che ha ritirato **l'intero sotto-sistema pipeline
   > `attivita_fatturabili`** (15 funzioni) sostituendolo con commesse v2. Il
   > test non toccava nessuna tabella sopravvissuta: era copertura di un
   > sotto-sistema che non c'e' piu', e restava in `baseline-rossi.tsv` come
   > `ERRORE_FIXTURE` senza eseguire nessuna asserzione.
   > La riga qui sopra resta perche' racconta cosa fu fatto allora — e' cronaca,
   > non un puntatore.

**Azione richiesta al team backend (integrazione)**

1. Repository:
   - introdurre `get_lotto_attivita_info(lotto_id)` su funzione DB.
2. Refactor metodi:
   - `get_lotto_attivita_stato`, `get_lotto_attivita_full_stato`,
     `is_lotto_attivita_in_esecuzione` devono delegare al nuovo metodo unico
     oppure essere deprecati/rimossi.

**Integrazione backend (23-02-2026): COMPLETATA**

- `attivita_pipeline_repository.py`: aggiunto `get_lotto_attivita_info` che chiama `fn_get_attivita_lotto_info`; i tre metodi esistenti delegano a questo.
- Test: aggiunto `test_get_lotto_attivita_info_returns_dict` con verifica SQL e delega metodi.

### §11.4 Helper interno `_decode_jsonb` nel repository attivita

**Contesto**: `AttivitaPipelineRepository` ripete il pattern di decodifica JSONB
in quattro metodi (`list_sorgenti_abilitate`, `get_attivita_step_processes`,
`get_attivita_task_policy`, `list_attivita_task_runs`):

```python
if isinstance(value, str):
    try:
        value = json.loads(value)
    except json.JSONDecodeError:
        value = default
```

**Miglioramento**: helper statico privato da estrarre nel repository:

```python
@staticmethod
def _decode_jsonb(value, default):
    if isinstance(value, (list, dict)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            pass
    return default
```

**Impatto backend**: intervento puramente interno al repository (nessun cambio
interfaccia pubblica). Riduce il rischio di evoluzione inconsistente tra i blocchi.

**Stato avanzamento (23-02-2026, DB): NON APPLICABILE**

1. Nessuna modifica schema/funzioni SQL necessaria.
2. Nessun changeset DB previsto per questo punto.
3. Nessun pgTAP DB richiesto (refactor solo applicativo Python).

**Azione richiesta al team backend (integrazione)**

1. Estrarre helper `_decode_jsonb(value, default)` nel repository attivita.
2. Riutilizzare helper in:
   - `list_sorgenti_abilitate`
   - `get_attivita_step_processes`
   - `get_attivita_task_policy`
   - `list_attivita_task_runs`
3. Mantenere invariata interfaccia pubblica repository/service.

**Integrazione backend (23-02-2026): COMPLETATA**

- `attivita_pipeline_repository.py`: aggiunto `_decode_jsonb` statico; applicato in tutti e 4 i metodi elencati.

> ⚠️ **Aggiornamento 2026-10-28** (brief-modello-documento-vendita §15.17.3): `_decode_jsonb` è ritirato. Le letture per posizione usano il BB `jsonb_out` di `apps/core/db/_helpers.py`; le letture a dizionari (`row_to_dict`, `rows_to_list`, `fetch_paged_with_total`) decodificano i jsonb da sole.


### §11.5 Wrappare `list_sorgenti_abilitate` in funzione DB

**Contesto**: `list_sorgenti_abilitate` esegue SELECT diretto su
`vendite.attivita_fatturabili_sorgenti_branch_policy`
con filtro e ordinamento embedded nel codice Python.

**Miglioramento**: creare `vendite.fn_list_attivita_sorgenti_abilitate(utility_id)`
per allineare il pattern con le altre funzioni DB del dominio
(`fn_list_attivita_pipeline_steps`, `fn_resolve_attivita_pipeline_step`).

**Impatto backend**:

- query inline sostituita con `SELECT * FROM vendite.fn_list_attivita_sorgenti_abilitate(%s)`;
- logica di filtro modificabile solo lato DB senza deploy backend.

**Stato avanzamento (23-02-2026, DB): COMPLETATO**

Implementato lato DB:

1. Nuova funzione SQL:
   - `vendite.fn_list_attivita_sorgenti_abilitate(p_utility_id integer DEFAULT NULL)`
   - output: `sorgente_tipo_id`, `branch_code`, `abilitata`, `acquisizione_mode`,
     `block_scope`, `priorita`, `meta`.
2. Regole:
   - filtra solo policy `attivo=true` e `abilitata=true`;
   - ordinamento `priorita, id`;
   - parametro `utility_id` mantenuto per compatibilita` (oggi non filtrante).
3. Test DB:
   - aggiunto pgTAP `db/pgtap/vendite/test-attivita-list-sorgenti-abilitate-v1.sql`;
   - aggiunto alla suite `scripts/testpgtap-fatturazione-logs.sh`.

**Azione richiesta al team backend (integrazione)**

1. Repository:
   - sostituire query diretta in `list_sorgenti_abilitate` con chiamata a
     `vendite.fn_list_attivita_sorgenti_abilitate(%s)`.
2. Refactor:
   - mantenere la firma del metodo invariata;
   - lasciare al DB l'ordinamento/filtro sorgenti abilitate.

**Integrazione backend (23-02-2026): COMPLETATA**

- `attivita_pipeline_repository.py`: `list_sorgenti_abilitate` usa `fn_list_attivita_sorgenti_abilitate`; mapping righe invariato.
- Test: `test_list_sorgenti_abilitate_returns_list` aggiornato con assert SQL su `fn_list_attivita_sorgenti_abilitate`.

## 12) Acquisizione reale da PREVENTIVI/ORDINI via COMMESSA (obbligatoria)

### 12.1 Decisione architetturale vincolante

Regola confermata:

1. percorso diretto `preventivo/ordine -> attivita_fatturabili` vietato;
2. tutte le attivita` fatturabili devono essere emesse da layer commessa;
3. il layer commessa puo` essere:
   - `REALE` (commessa operativa richiesta dal processo),
   - `AUTO` (commessa tecnica/fittizia per casi senza gestione operativa commessa).

Obiettivo:
- un unico modello di controllo, deduplica e partializzazione prima della fatturazione.

### 12.2 Stato reale (oggi)

1. Pipeline attivita e policy branch/global sono pronte.
2. Registry task e task-runs runtime sono pronti.
3. Manca l'acquisizione reale da sorgenti commerciali verso commessa.
4. Di conseguenza manca anche l'emissione finale commessa -> `attivita_fatturabili` su dati reali.

Conclusione:
- infrastruttura pronta, ma ingestione operativa ancora da completare con flusso commessa-centrico.

### 12.3 Modello dati operativo (senza lineage root)

In `attivita_fatturabili` restano fondamentali:

1. chiavi sorgente primarie:
   - `sorgente_tipo_id`
   - `sorgente_uid`
   - `sorgente_riga` (coerente con `key_selector` e trigger polimorfo)
2. collegamenti commessa:
   - `commessa_id` (nullable in transizione, target: valorizzata sempre),
   - `commessa_attivita_id` (nullable in transizione, target: valorizzata sempre).

Nota:
- non serve `lineage_root_source` dedicata; la root e` gia` ricostruibile da `sorgente_*` + relazione commessa.

### 12.4 Implementazioni previste (DB)

#### DB-A1) Ingestione sorgenti verso commessa

Funzioni previste:

1. risoluzione/creazione commessa (`REALE` o `AUTO`) per documento sorgente;
2. upsert relazione documento -> commessa;
3. upsert attivita` di commessa per righe/segmenti eleggibili.

Regole minime:

1. stati eleggibili per `PREVENTIVO` e `ORDINE_VENDITA` definiti a policy;
2. esclusione record annullati/non fatturabili;
3. idempotenza su chiave sorgente + segmentazione commessa;
4. coerenza chiavi `sorgente_riga`/`sorgente_uid` per compatibilita` trigger/funzioni.

#### DB-A2) Emissione commessa -> attivita_fatturabili

Funzione/facade prevista:

1. estrazione attivita` commessa eleggibili;
2. upsert in `vendite.attivita_fatturabili` con link commessa;
3. metriche standard `inserted/updated/skipped/error`.

#### DB-A3) Pipeline task reali

Sostituire i placeholder `noop` con task concreti:

1. `RACCOLTA_INPUT`:
   - ingestione da sorgenti commerciali verso commessa;
2. `GENERAZIONE_OPERATIVA`:
   - emissione da commessa verso `attivita_fatturabili`;
3. `NORMALIZZAZIONE`:
   - normalizza/valida/deduplica.

#### DB-A4) Guardrail anti-bypass

Aggiungere controlli espliciti per impedire inserimenti diretti non autorizzati:

1. vincolo o trigger di coerenza sul path di creazione;
2. logging tecnico se intercettato tentativo di bypass del layer commessa.

### 12.5 Implementazioni previste (Backend)

1. handler branch `PREVENTIVI` e `ORDINI` devono chiamare funzioni DB commessa-centriche;
2. nessun handler deve scrivere direttamente `attivita_fatturabili` da documento sorgente;
3. supporto run `FULL` e `INCREMENTAL` con watermark;
4. tracciamento metriche e errori su `attivita_fatturabili_lotti_task_runs`.

### 12.6 Test obbligatori

#### pgTAP

1. ingestione `PREVENTIVO/ORDINE` crea/aggiorna commessa in modo idempotente;
2. emissione commessa -> `attivita_fatturabili` idempotente;
3. tentativo percorso diretto documento -> `attivita_fatturabili` bloccato;
4. coerenza `sorgente_riga`/`sorgente_uid` e trigger polimorfo valida.

#### Backend

1. mapping branch -> funzioni commessa-centriche corretto;
2. run multi-branch con isolamento `BRANCH` e stop `GLOBAL` invariati;
3. run incrementale non duplica record.

### 12.7 Definition of done (acquisizione reale via commessa)

1. nessun percorso diretto `preventivo/ordine -> attivita_fatturabili` attivo;
2. pipeline `PREVENTIVI` e `ORDINI` popola commessa e poi `attivita_fatturabili`;
3. idempotenza verificata su rerun;
4. test pgTAP + backend verdi;
5. documentazione aggiornata su funzioni e policy commessa-centriche.

### 12.8 Roadmap operativa (dopo chiusura punto 11)

Fase 1 - Regole sorgente:

1. fissare eleggibilita` stati `PREVENTIVO`/`ORDINE_VENDITA`;
2. fissare policy commessa `REALE` vs `AUTO`;
3. validare chiavi sorgente obbligatorie per idempotenza.

Fase 2 - DB ingestione:

1. implementare funzioni ingestione sorgente -> commessa;
2. implementare funzione emissione commessa -> `attivita_fatturabili`;
3. aggiornare processi pipeline eliminando i `noop`.

Fase 3 - Backend handlers:

1. collegare handler a funzioni DB nuove;
2. integrare metriche standard nei task-runs;
3. abilitare modalita` `FULL`/`INCREMENTAL`.

Fase 4 - Hardening:

1. aggiungere guardrail anti-bypass layer commessa;

### 12.9 Aggiornamento stato (24-02-2026) - canali documento

Completato allineamento DB del registro canali su conversioni documento:

1. funzione `vendite.fn_set_documento_canale_stato` introdotta (upsert/transizioni `APERTO|CONSUMATO|BLOCCATO`);
2. trigger function `vendite.trgfn_documenti_sync_canali` introdotta;
3. trigger su `vendite.ordini`, `vendite.ddt`, `vendite.contratti` attivati;
4. gestione conversioni coperta:
   - `PREVENTIVO -> ORDINE_VENDITA`
   - `ORDINE_VENDITA -> DDT_VENDITA`
   - `CONTRATTO -> DIRETTO`
5. pgTAP dedicati predisposti:
   - `db/pgtap/vendite/test-documenti-fatturazione-canali-v1.sql`
   - `db/pgtap/vendite/test-documenti-canali-sync-v1.sql`
2. verificare consistency stati lotto/attivita;
3. validare resume branch-level su scenari reali.

Fase 5 - Validazione finale:

1. chiudere suite pgTAP e backend;
2. smoke multi-branch con sorgenti reali;
3. handover finale al team backend su contratto stabile.
