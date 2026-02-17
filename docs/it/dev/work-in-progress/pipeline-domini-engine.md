# Progettazione Pipeline Vendite + Registry Multi-Dominio (WIP)

## 1) Scopo e origine

Questo documento nasce per chiarire una decisione architetturale:

* **non** costruire una pipeline DB universale per domini diversi;
* mantenere pipeline **separate per dominio funzionale**;
* introdurre invece un **registry multi-dominio** lato engine Django per il dispatch task parametrico e sicuro.

Motivazione:
in fatturazione, alimentazione attivita`, pratiche o utility verticali (idrico/gas/elettrico) gli stati e le regole sono diversi. Un'unica pipeline DB rischia di mescolare semantiche incompatibili.

---

## 2) Decisione architetturale

## 2.1 Cosa facciamo

1. Pipeline DB separate per dominio:
* `vendite.fatturazione_pipeline` (gia` presente)
* `vendite.attivita_fatturabili_pipeline` (introdotta - step base)
* eventuali pipeline verticali future (se necessarie)

2. Engine applicativo unico condiviso:
* runner/dispatcher comuni
* repository specifici per dominio
* logging e gestione errori con policy comuni

3. Registry multi-dominio (Python):
* `task_code + implementation_key` con whitelist controllata
* `default` obbligatorio
* `params.fn` mantenuto solo come compatibilita` legacy (deprecabile)

## 2.2 Cosa non facciamo

* Nessuna tabella pipeline DB unica cross-dominio.
* Nessun modello stati "universale" che accorpa domini diversi.

---

## 3) Stato attuale confermato

### Fatturazione

* pipeline configurata su `vendite.fatturazione_pipeline`
* fallback `utility_id` / `tipo_doc_fiscale_id` gia` implementato e testato
* orchestrazione in Django gia` avviata

### Attivita fatturabili

* pipeline dedicata non ancora creata
* verra` progettata separatamente, con propri step/stati e propri lotti

---

## 4) Cosa serve fare adesso (backlog)

## 4.1 Registry multi-dominio (Python)

### Scopo
Rendere parametrico il dispatch task senza esecuzione dinamica libera.

### Struttura

* `registry[dominio][task_code][implementation_key] = handler`
* `implementation_key='default'` obbligatorio per ogni task

### Regole

* se task non registrato -> errore dominio
* se implementation_key non valida -> errore dominio
* niente eval/import dinamico da stringhe config

### Stato
* [x] Integrazione `implementation_key` in `PipelineStepExecutor` (dominio fatturazione)
* [x] Risoluzione handler via DB in `VenditePipelineRepository`
* [ ] Registry runtime multi-dominio completo (mappa per dominio)
  * Nota: posticipabile finche` esiste solo il dominio fatturazione.
  * Vincolo: mantenere dispatch basato su `handler_code` e mapping in un solo punto
    per ridurre il refactor futuro.

---

## 4.1-bis Registry multi-dominio (DB - schema `dbops`)

### Tabella `dbops.domini_task`

**Scopo:** catalogo domini task riusabili (registry generale).

**Struttura proposta:**

* `id` bigint PK
* `codice` text NOT NULL UNIQUE (es. `FATTURAZIONE`, `ATTIVITA_FATTURABILI`, `PRATICHE`)
* `descrizione` text NULL
* `attivo` boolean NOT NULL default `true`
* `meta` jsonb NOT NULL default `'{}'::jsonb`
* audit standard

---

### Tabella `dbops.pipeline_task_registry`

**Scopo:** catalogo task ammessi per dominio.

**Struttura proposta:**

* `id` bigint PK
* `dominio_id` bigint NOT NULL FK -> `dbops.domini_task.id`
* `task_code` text NOT NULL (es. `select_attivita`, `generate_fatture_righe`)
* `descrizione` text NULL
* `attivo` boolean NOT NULL default `true`
* `meta` jsonb NOT NULL default `'{}'::jsonb`
* audit standard

**Vincoli:**

* unique (`dominio_id`, `task_code`)

---

### Tabella `dbops.pipeline_task_registry_impl`

**Scopo:** implementazioni abilitate per ciascun task.

**Struttura proposta:**

* `id` bigint PK
* `task_registry_id` bigint NOT NULL FK -> `dbops.pipeline_task_registry.id`
* `implementation_key` text NOT NULL (es. `default`, `v2`, `gas_v1`)
* `handler_code` text NOT NULL
* `is_default` boolean NOT NULL default `false`
* `attivo` boolean NOT NULL default `true`
* `meta` jsonb NOT NULL default `'{}'::jsonb`
* audit standard

**Vincoli:**

* unique (`task_registry_id`, `implementation_key`)
* unique parziale su `task_registry_id` con `is_default=true` (un solo default per task)

**Nota sicurezza:**

* `handler_code` e` solo identificativo logico.
* l'esecuzione resta demandata a un registry Python statico (no dynamic import da input).

### Stato
* [x] Tabelle `dbops.domini_task`, `dbops.pipeline_task_registry`, `dbops.pipeline_task_registry_impl`
* [x] Funzioni `dbops.fn_check_pipeline_task_registered` e `dbops.fn_get_pipeline_task_implementation`
* [x] Seed CSV iniziali per dominio FATTURAZIONE e task base
* [x] Task `close_lotto` registrato con handler `close_lotto_default`

---

## 4.2 Pipeline fatturazione (DB) - integrazioni

### Tabella `vendite.fatturazione_pipeline`

* mantenere struttura specifica fatturazione
* mantenere fallback gia` implementato (`utility_id`, `tipo_doc_fiscale_id`)
* introdurre/rafforzare uso di `implementation_key` nei task JSON

**Formato JSON target (task):**

```json
[
  {
    "task": "select_attivita",
    "fase": "Caricamento lista attivita",
    "params": {
      "implementation_key": "default",
      "lock": true
    }
  }
]
```

**Regole:**

* `implementation_key` assente -> fallback automatico a `default`.
* `params.fn` resta legacy/transitorio e non pilota il dispatch.
* `implementation_key` assente significa: usare l'implementazione `is_default=true`
  definita in `dbops.pipeline_task_registry_impl`.

### Stato
* [x] Seed `fatturazione_pipeline.csv` aggiornato con `implementation_key: default`
* [x] Python usa `implementation_key` e registry DB per dispatch
* [x] Pipeline massiva (EMESSA) include task `close_lotto`
* [x] Runner Django: policy rerun su lotto `MASSIVO` in errore (resume dallo step corrente + rollback step opzionale via `meta.auto_step_rollback=true`, con skip automatico dei rollback distruttivi)
* [x] Resume `DEFINITIVA` per fattura (senza reset globale lotto)
* [x] Seed transizioni `config.stati_doc_fiscale_transizioni` coerente con avanzamento step lotto

Vincolo operativo:
* Le transizioni in `config.stati_doc_fiscale_transizioni` devono essere seedate in modo coerente con gli step pipeline lotto (`DRAFT -> EMESSA`, ecc.), altrimenti il trigger stato lotto blocca l'avanzamento.
* Se una transizione lotto e` comune a piu` tipi lotto, usare riga unica (`meta = {}`) per evitare duplicazioni logiche.

### Funzioni SQL fatturazione

* mantenere:
  * `vendite.fn_resolve_fatturazione_pipeline_step(...)`
  * `vendite.fn_list_fatturazione_pipeline_steps(...)`
* usare queste funzioni come source of truth per la risoluzione configurazione

### Funzioni SQL/DBOPS da aggiungere (registry)

* `dbops.fn_check_pipeline_task_registered(p_dominio_id bigint, p_task_code text)`  
  Scopo: validare che task esista e sia attivo.

* `dbops.fn_get_pipeline_task_implementation(p_dominio_id bigint, p_task_code text, p_implementation_key text)`  
  Scopo: risolvere implementation effettiva (`requested` o `default`) e restituire `handler_code`.

---

## 4.2-bis Integrazione Python con modello attuale

### `PipelineStepExecutor`

* leggere `implementation_key` da `processi.params`
* se assente usare `default`
* risolvere implementation via repository (lookup su `dbops`)
* validare coerenza task/implementation prima del dispatch

### `VenditePipelineRepository`

* helper SQL verso `dbops.fn_get_pipeline_task_implementation(...)`
* nessuna logica di dispatch dinamico basata su stringa esterna

### Registry runtime Python

* mappa interna:
  * `registry[dominio][task_code][implementation_key] = callable`
* controllo finale:
  * `handler_code` risolto da DB deve esistere nella mappa locale
  * se manca -> errore dominio bloccante

---

## 4.3 Nuova pipeline attivita fatturabili (DB)

### Tabella `vendite.attivita_fatturabili_pipeline` (introdotta)

Scopo:
configurare step/task del processo di alimentazione e preparazione attivita` fatturabili.

Struttura base (analoga alla pipeline fatturazione, ma dominio-specifica):

* id
* descrizione
* stato_step_attivita (codice o FK dominio attivita)
* processi jsonb
* rollback jsonb
* attivo
* meta
* audit
* opzionali di filtro (valutare): utility_id, tipologia processo, ecc.

### Funzioni attese (dominio attivita)

* `fn_resolve_attivita_pipeline_step(...)`
* `fn_list_attivita_pipeline_steps(...)`

Scopo:
stessa logica di risoluzione configurazione, ma limitata al dominio attivita.

### Stato
* [x] Tabella `vendite.attivita_fatturabili_pipeline`
* [x] Funzioni `fn_resolve_attivita_pipeline_step` e `fn_list_attivita_pipeline_steps`
* [ ] Log dedicato dominio attivita (tabella/funzioni)

---

## 5) Logging e lotti

## 5.1 Lotti separati

* `fatturazione_lotti` per pipeline fatture
* `attivita_fatturabili_lotti` per pipeline attivita

Non vanno fusi.

## 5.2 Logging

* mantenere logging per dominio (gia` presente per fatturazione)
* se in futuro serve osservabilita` cross-dominio, introdurre vista/report aggregato, non forzare subito tabella unica.

---

## 6) Impatti su artefatti esistenti

### Da aggiornare subito

* documentazione backend pipeline:
  * chiarire registry multi-dominio
  * chiarire che la pipeline DB resta dominio-specifica

* `PipelineStepExecutor`:
  * supportare `implementation_key` (con default)
  * mantenere `params.fn` solo come token legacy

### Da introdurre dopo

* tabella/funzioni pipeline attivita fatturabili
* test pgtap e test Python dedicati al nuovo dominio

---

## 7) Riepilogo decisionale

1. Pipeline DB universale: **NO**
2. Pipeline DB separate per dominio: **SI**
3. Engine/registry applicativo condiviso: **SI**
4. Dispatch dinamico libero: **NO**
5. Dispatch parametrico controllato (task + implementation_key): **SI**

---

## 8) Checklist operativa

### Stato aggiornato (recap operativo)

* [x] Registry DB multi-dominio creato (`dbops.domini_task`, `dbops.pipeline_task_registry`, `dbops.pipeline_task_registry_impl`)
* [x] Funzioni DB registry operative (`fn_check_pipeline_task_registered`, `fn_get_pipeline_task_implementation`)
* [x] Seed pipeline fatturazione con `implementation_key: default`
* [x] Dispatch Django su registry DB + `implementation_key`
* [x] Task `close_lotto` integrato nella pipeline massiva
* [ ] Registry runtime Python completo multi-dominio (mappa per dominio)
* [ ] Pipeline dedicata `attivita_fatturabili` (log + runner/handler dominio)
* [ ] Pacchetto test completo dominio attivita (pgtap + python)
* [ ] Validazione pre-run unificata per tutti i domini pipeline

## 9) Test gravita (stato corrente)

### Alta

* [ ] Pipeline dominio `attivita_fatturabili` non ancora implementata.
  Impatto: non e` completata la convergenza su modello pipeline per l'intero flusso vendite.

### Media

* [ ] Registry runtime Python multi-dominio non completato.
  Impatto: il modello DB e` pronto, ma la generalizzazione runtime non e` ancora chiusa.

* [ ] Validazione pre-run unificata non ancora consolidata.
  Impatto: rischio eterogeneita` nei controlli tra domini quando verra` introdotto il secondo dominio attivo.

### Bassa

* [x] Seed e funzioni DB per dominio `FATTURAZIONE` completati.
* [x] Dispatch `implementation_key` operativo sul dominio fatturazione.
* [x] Documentazione strategica allineata alla scelta: pipeline per dominio + registry condiviso.

1. **Dominio runtime**
   * Seed `dbops.domini_task` con codici standard (`FATTURAZIONE`, `ATTIVITA_FATTURABILI`).
   * Esporre mapping stabile `dominio_id` lato Python.
   * Passare `dominio_id` nei lookup registry.

2. **Registry DB completo**
   * Creare tabelle:
     * `dbops.domini_task`
     * `dbops.pipeline_task_registry`
     * `dbops.pipeline_task_registry_impl`
   * Seed iniziale per fatturazione:
     * task `select_attivita`, `generate_fatture_righe`
     * implementation `default` (is_default = true)

3. **Funzioni DB registry**
   * `dbops.fn_check_pipeline_task_registered(p_dominio_id, p_task_code)`
   * `dbops.fn_get_pipeline_task_implementation(p_dominio_id, p_task_code, p_implementation_key)`
   * opzionale: `dbops.fn_check_pipeline_tasks_json(p_dominio_id, p_processi jsonb)`

4. **Parametrizzazione JSON**
   * Aggiornare seed `fatturazione_pipeline.csv` con `implementation_key: "default"`.
   * Regola: se assente -> `default`.

5. **Python dispatch**
   * `PipelineStepExecutor`: leggere `implementation_key`, risolvere `handler_code` via DB, dispatch su registry locale.
   * Errore se task/implementation/handler non validi.

6. **Validazione prima run**
   * In `PipelineRunner` aggiungere validazione task (DB function o check per step).
   * Errore bloccante se task/implementation non valida.

7. **Pipeline attivita (fase 1)**
   * Tabella `vendite.attivita_fatturabili_pipeline`.
   * Tabella stati/step attivita (es. `vendite.attivita_pipeline_stati`).
   * Log dedicato (es. `vendite.attivita_pipeline_log`).

8. **Test pgtap**
   * Registry DB: task registrato, fallback default, errori su task assente.
   * Pipeline JSON: `implementation_key` assente -> default.
   * Attivita pipeline: resolve/list per dominio attivita.

9. **Test Python**
   * Dispatch `default`.
   * `implementation_key` non valido -> errore.
   * task non registrato -> errore.
   * `handler_code` non mappato -> errore.

10. **Documentazione**
    * Aggiornare manuali pipeline con `implementation_key` e registry DB.
    * Aggiornare WIP con stati/step attivita e log.

---

## 9) Checklist di coerenza (da eseguire)

* Verificare che ogni `task_code` abbia **esattamente un** `is_default=true`.
* Verificare che ogni `handler_code` abbia **mappatura Python** unica e stabile.
* Verificare che `params.fn` non alteri il dispatch (solo legacy).
* Verificare che il mapping `dominio_id` sia centralizzato (no hardcode sparso).
* Verificare validazione JSON pipeline (task/implementation) prima dell'esecuzione.
* Verificare che il fallback `implementation_key -> default` sia sempre loggato.
* Verificare coerenza fra seed DB e registry Python (task registrati e attivi).

---

## 10) Note critiche aperte (da chiudere)

## 10.1 Baseline runtime Python non allineata (CI/dev vs Docker)

### Problema

Ad oggi la baseline runtime non e` unica:

* linee guida e toolchain backend puntano a Python `3.14`
* CI usa Python `3.14`
* `Dockerfile` usa ancora base image Python `3.13`

Questa divergenza puo` introdurre bug non riproducibili tra locale, CI e container runtime.

### Rischio tecnico

* differenze di risoluzione dipendenze e wheel
* differenze di comportamento runtime (stdlib/interprete)
* falsi verdi in CI o regressioni solo in produzione

### Soluzioni possibili

1. **Allineamento completo a 3.14 (consigliato)**
   * aggiornare `Dockerfile` a base `python:3.14-slim`
   * mantenere `backend/.python-version` e CI su 3.14
   * verificare lock/compile requirements con 3.14

2. **Rollback coordinato a 3.13**
   * portare CI, `.python-version` e linee guida a 3.13
   * rigenerare requirements su 3.13
   * documentare motivazione e data target per ritorno a 3.14

### Decisione proposta

Adottare opzione 1: una sola baseline `3.14` su tutti gli ambienti.

---

## 10.2 Pipeline giornaliera: doppio canale di chiusura lotto

### Problema

Nell'implementazione attuale convivono due meccanismi di chiusura:

1. chiusura implicita in runner (`fn_close_giornaliero_lotto` quando step = `INVIATA`)
2. task pipeline `close_lotto` che chiude operativamente con update diretto

Se la configurazione pipeline non e` rigorosa, i due canali possono concorrere sullo stesso stato operativo/documentale.

### Rischio tecnico

* transizioni duplicate o non deterministiche
* log step meno leggibili (chiusura avvenuta fuori task esplicito)
* maggior rischio regressioni quando si estende a nuovi domini pipeline

### Soluzioni possibili

1. **Canale unico via task pipeline (consigliato)**
   * il runner non chiude automaticamente allo step `INVIATA`
   * la chiusura avviene solo tramite task esplicito (`close_lotto`) risolto da registry
   * il task deve delegare a funzione DB canonica (no update diretto duplicato)

2. **Canale unico via runner**
   * mantenere chiusura automatica nel runner
   * rimuovere `close_lotto` dagli step giornalieri
   * vietare da validazione pre-run l'uso del task `close_lotto` per `GIORNALIERO`

3. **Hardening ibrido transitorio**
   * mantenere assetto attuale ma con guard espliciti:
     * validazione pre-run: errore se in pipeline `GIORNALIERO` coesistono auto-close e task `close_lotto`
     * idempotenza forte lato DB: seconda chiusura no-op con log warning
   * pianificare convergenza a canale unico

### Decisione proposta

Convergere a canale unico (opzione 1) per avere comportamento esplicito, testabile e coerente con il modello registry/task.
