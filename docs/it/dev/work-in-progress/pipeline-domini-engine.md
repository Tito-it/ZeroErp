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
* `vendite.attivita_fatturabili_pipeline` (da introdurre)
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

### Nuova tabella `vendite.attivita_fatturabili_pipeline` (da creare)

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
* [ ] Tabella `vendite.attivita_fatturabili_pipeline`
* [ ] Funzioni `fn_resolve_attivita_pipeline_step` e `fn_list_attivita_pipeline_steps`

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
