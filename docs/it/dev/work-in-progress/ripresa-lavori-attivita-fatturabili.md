# Ripresa lavori - attivita_fatturabili (22-02-2026)

## 1) Obiettivo

Riprendere il dominio `attivita_fatturabili` allineandolo al livello raggiunto dalla pipeline lotto, partendo prima dai refactor trasversali dei punti 20 e 21 del documento WIP.

Riferimento base:
- `docs/it/dev/work-in-progress/fatturazione-attivita-progetto.md`

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
   - `vendite.attivita_fatturabili_task_runs`
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
4. DTO/UI contract con stato per branch e blocco per scope.

#### E) Mancanze test

1. pgTAP:
   - resolve/list step attivita (fallback)
   - policy branch/global
   - task-runs attivita
2. Django services:
   - run ok
   - errore branch A non blocca branch B (scope BRANCH)
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

## 5.2 Estensioni schema (bozza)

Su `vendite.attivita_fatturabili_pipeline`:
- `branch_code text` (default `DEFAULT`)
- `block_scope text` (`BRANCH|GLOBAL`)
- `depends_on jsonb` (opzionale)

Nuove tabelle speculari a lotto:
- `vendite.attivita_fatturabili_pipeline_task_policy`
- `vendite.attivita_fatturabili_task_runs`

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

## 5.6 Decisioni sorgenti e scope operativo (22-02-2026)

Decisione confermata: avanzare prima sul dominio `attivita_fatturabili` e
gestire l'upstream in fasi successive, con scope sorgenti controllato.

### Sorgenti in scope (fase corrente)

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
   - sorgenti in scope abilitate (`PREVENTIVO`, `CONTRATTO`, `ORDINE_VENDITA`, `ATTIVITA`, `ATTIVITA_CONSUMI`);
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

### 8.1 Fase DB-1 (schema allineamento, priorita immediata)

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

### 8.2 Fase DB-2 (funzioni dominio attivita)

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

### 8.3 Fase DB-3 (test pgtap obbligatori)

1. DDL checks: colonne/default/FK/check.
2. Test funzioni:
   - get/create lotto con emittente.
   - transizioni stato lotto/operativo ammesse e non ammesse.
   - sync `stato_esecuzione` per lotto.
3. Test blocchi:
   - errore tecnico rilevabile da summary.

Uscita fase:
- suite pgtap del dominio verde.

### 8.4 Fase BE-1 (runtime services)

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

### 8.5 Fase BE-2 (API dominio attivita)

1. Endpoint run pipeline attivita.
2. Endpoint status/segnalazioni.
3. Endpoint task-runs.
4. DTO risposta:
   - `stato_lotto`
   - `stato_operativo`
   - riepilogo `stato_esecuzione`.

Uscita fase:
- API consumabile da UI e pronta per debug operativo.

### 8.6 Fase BE-3 (test backend/API)

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

1. in scope abilitate:
   - `ATTIVITA`
   - `PREVENTIVO`
   - `CONTRATTO`
   - `ORDINE_VENDITA`
   - `ATTIVITA_CONSUMI`
2. fuori scope iniziale (`abilitata=false`):
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

1. `POST /attivita-fatturabili/pipeline/run`
   - input: lotto o criteri creazione lotto + filtro sorgenti/branch opzionale;
   - output: id run/lotto + stato iniziale per branch.
2. `GET /attivita-fatturabili/pipeline/{lottoId}/status`
   - output: `stato_lotto`, `stato_operativo`, riepilogo `stato_esecuzione` per branch.
3. `GET /attivita-fatturabili/pipeline/{lottoId}/task-runs`
   - output: lista task run ordinata per sequenza/tentativo con esito e dettagli errore.

Regole API:
- nessun mapping hardcoded sorgente->branch lato Python: usare solo resolver DB;
- error envelope uniforme e tracciabile (code, scope, severity, context).

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

### 9.4 Attivita` esplicitamente fuori scope backend immediato

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
     - gestione esiti `SUCCESS|WARNING|ERROR`.
   - done:
     - supporto `block_scope=BRANCH|GLOBAL` rispettato.

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
     - `POST /attivita-fatturabili/pipeline/run`.
   - done:
     - supporto input con lotto esistente o creazione guidata.

2. `BE-2.2` (TASK, P0) - endpoint status
   - output:
     - `GET /attivita-fatturabili/pipeline/{lottoId}/status`.
   - done:
     - include `stato_lotto`, `stato_operativo`, contatori `stato_esecuzione` per branch.

3. `BE-2.3` (TASK, P0) - endpoint task-runs
   - output:
     - `GET /attivita-fatturabili/pipeline/{lottoId}/task-runs`.
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
   - non aprire `BE-2` senza runner stabile (`BE-1.3` minimo).
   - non chiudere epic senza smoke `BE-3.3`.
