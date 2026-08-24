# Progettazione Pipeline Vendite + Registry Multi-Dominio (WIP)

> 🟢 **ARCHIVIATO — 2026-08-22.** Documento di **febbraio 2026** (ultima
> revisione 19-02), verificato riga per riga contro il **codice e il DB vivi**.
> Esito: **la decisione architetturale ha retto**, il backlog è per metà fatto e
> per metà **superato da una decisione presa dopo**, e resta aperto un solo
> capitolo (SDI), già censito altrove.
>
> ### Cosa ha retto
>
> | Concetto (§) | Verifica del 22-08 |
> | --- | --- |
> | **No a una pipeline DB universale, sì a pipeline per dominio** (§2, §7) | ✅ **retto, e confermato due volte**: dalla deprecazione `20260227-16` e dalla decisione presa con Tid il 2026-06-18 ([analisi-orchestrazione-vendite-simmetrie.md](../work-done/analisi-orchestrazione-vendite-simmetrie.md) §A) |
> | **Engine applicativo unico + registry a DB** (§4.1-bis) | ✅ **in esercizio**: `dbops.domini_task` (2 domini), `pipeline_task_registry` (21 task), `pipeline_task_registry_impl` (21 impl), più `fn_check_pipeline_task_registered` e `fn_get_pipeline_task_implementation`. Il registry è letto sia dal dispatch sia dall'**API di tracciamento** (`views_tracciamento.py`) |
> | **Dispatch parametrico, mai `eval`; `params.fn` solo legacy** (§2.1, §4.2) | ✅ **retto alla lettera**: `params.fn` è ancora nel codice ma **non pilota il dispatch** — è una validazione che solleva `E_TASK_NOT_ALLOWED` se contraddice la funzione ammessa |
> | **Governance runtime task/stato lotto** (§8, ultimo punto) | ✅ **fatta**: `fatturazione_pipeline_task_policy` (25 righe) e `fatturazione_lotti_task_runs` (194 corse) |
> | **Canale unico di chiusura lotto via `chiude_lotto`** (§10.1) | ✅ **adottato e vivo** (`is_stato_doc_chiude_lotto` nel runner). Il task dedicato `close_lotto` è a registro con `attivo = false`, come voleva la decisione. ⚠️ Residuo minimo: l'handler Python `close_lotto_default` esiste ancora |
>
> ### Cosa è superato dai fatti
>
> ⛔ **§4.3 e §5.1 — la pipeline del dominio «attività fatturabili» non esiste
> più, ed è una decisione, non un debito.** Il changeSet
> `20260227-16-drop-attivita-pipeline-deprecated` — applicato il **2026-02-27**,
> otto giorni dopo l'ultima revisione di questo documento — ha rimosso
> **l'intero sottosistema**: 15 funzioni, 5 tabelle
> (`attivita_fatturabili_pipeline`, `..._lotti`, `..._lotti_task_runs`,
> `..._pipeline_task_policy`, `..._sorgenti_branch_policy`), 4 trigger e la
> colonna `lotto_attivita_id` da tre tabelle. Motivo scritto nel changeSet:
> *«sostituito da commesse v2»*. Il processo **commessa → AF** è stato
> **collassato** in un unico task idempotente, `pull_attivita_da_commessa`, che
> oggi è lo step 0 della pipeline FATTURAZIONE.
> ⚠️ Quindi le spunte `[x]` del §4.3 («tabella introdotta», «funzioni
> `fn_resolve_attivita_pipeline_step` / `fn_list_attivita_pipeline_steps`»)
> descrivono oggetti **che non esistono**: erano vere quando scritte.
>
> ⛔ **§9 «gravità Alta: pipeline dominio attività non implementata»** — non è
> più un rischio aperto: è la risposta. I due processi non sono simmetrici — AF
> → fatturazione è un ciclo di vita **fiscale stateful** (che il motore lo
> merita), commessa → AF è una **promozione idempotente** (che non lo merita).
> *La macchina pesante era stata costruita davvero, ed è stata ritirata.*
>
> 🟡 **§4.1 «registry runtime Python multi-dominio (mappa per dominio)»** — non
> fatto, e **non serve**: il dominio attivo è uno solo. Oggi c'è
> `VenditePipelineRepository.DOMINIO_CODE = "FATTURAZIONE"` più una
> `handler_registry` piatta di **14 handler**. Il presidio che quel punto voleva
> dare è nato altrove e in forma migliore: il cancello DB↔Python
> `backend/apps/vendite/tests/db/test_pipeline_task_handler_guardrail.py`
> (2026-08-18), che confronta i task delle pipeline **vive** col dizionario
> Python **vivo** — nato dopo un caso reale (`popola_fatture_rettifiche` in
> pipeline con l'handler ancora da scrivere, e l'errore sarebbe arrivato *dopo*
> la numerazione).
> ℹ️ È lo stesso cancello che tiene il **registro del debito dormiente**: i 7
> task `ATTIVITA_FATTURABILI` (`acquisisci_*`, `normalizza_`, `valida_`,
> `deduplica_attivita`) sono a registro **senza handler** e sono i resti di
> questo §4.3. Non fanno danno finché nessuno li mette in un JSON `processi`.
>
> ### Cosa resta aperto (e dove vive)
>
> 🟠 **Solo il capitolo SDI del §4.2**: builder del file XML, persistenza di
> `nome_file`/esito, invio e registrazione eventi. Verificato: `vendite.fatture_sdi`
> e `fatture_sdi_eventi` **esistono e sono vuote**, il task
> `prepare_sdi_payload_lotto` è attivo in pipeline. È già censito in
> `.codex/PROJECT_CONTEXT.md` («Builder XML SDI», «Persistenza esito SDI»), che
> resta la sede: **non serve tenere aperto questo documento per quelle tre righe**.
>
> ### Dove è finita la materia viva
>
> * [analisi-orchestrazione-vendite-simmetrie.md](../work-done/analisi-orchestrazione-vendite-simmetrie.md) §A — perché commessa→AF **non** doveva diventare un dominio pipeline (è il seguito diretto di questo documento)
> * [guide/fatturazione.md](../../guide/fatturazione.md) — la pipeline come è oggi, step per step
> * [guide/analisi-tracciamento-processi-e-job.md](../../guide/analisi-tracciamento-processi-e-job.md) — l'osservabilità che legge il registry
> * `docs/it/backend/vendite/manual/api_pipeline_task.md` — i cinque pezzi di cui è fatto un task
>
> ---

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
* [x] Chiusura lotto standardizzata via flag `config.stati_doc_fiscale.chiude_lotto` a fine step (runner)

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
* [x] Chiusura operativa lotto gestita a fine step via `chiude_lotto` (nessun task dedicato richiesto in pipeline)
* [x] Runner Django: policy rerun su lotto `MASSIVO` in errore (resume dallo step corrente + rollback step opzionale via `meta.auto_step_rollback=true`, con skip automatico dei rollback distruttivi)
* [x] Resume `DEFINITIVA` per fattura (senza reset globale lotto)
* [x] Seed transizioni `config.stati_doc_fiscale_transizioni` coerente con avanzamento step lotto
* [x] Task `prepare_sdi_payload_lotto` attivo (preparazione payload/ tentativi SDI da lotto)
* [ ] Builder file invio SDI (XML/metadata) agganciato al task successivo
* [ ] Persistenza `nome_file`/esito generazione su `vendite.fatture_sdi`
* [ ] Invio canale SDI + registrazione eventi in `vendite.fatture_sdi_eventi`

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

## 4.3 ~~Nuova pipeline attivita fatturabili (DB)~~ — ⛔ **RITIRATA il 2026-02-27**

> ⛔ **Tutto questo paragrafo è superato**, e non «da fare»: il sottosistema fu
> **costruito e poi droppato** (`20260227-16-drop-attivita-pipeline-deprecated`,
> applicato il 2026-02-27) perché sostituito da **commesse v2**. Le spunte `[x]`
> qui sotto erano vere quando scritte e oggi nominano oggetti inesistenti.
> Il processo commessa → AF vive ora in un solo task idempotente,
> `pull_attivita_da_commessa`, step 0 della pipeline FATTURAZIONE.
> Perché non va ricostruito: [analisi-orchestrazione-vendite-simmetrie.md](../work-done/analisi-orchestrazione-vendite-simmetrie.md) §A.

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

## 5.1 ~~Lotti separati~~ — ⛔ **caduta con la 4.3**

> ⛔ `vendite.attivita_fatturabili_lotti` **non esiste piu'** (droppata dal
> `20260227-16`). Il principio «non vanno fusi» resta corretto in astratto, ma
> oggi il lotto e' uno solo perche' il dominio pipeline e' uno solo.

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
* [x] Chiusura lotto centralizzata nel runner (`_process_close_lotto_by_flag`)
* [ ] Registry runtime Python completo multi-dominio (mappa per dominio)
* [ ] Pipeline dedicata `attivita_fatturabili` (log + runner/handler dominio)
* [ ] Pacchetto test completo dominio attivita (pgtap + python)
* [ ] Validazione pre-run unificata per tutti i domini pipeline
* [ ] Governance runtime task/stato_lotto:
  * introdurre policy task per pipeline (`vendite.fatturazione_pipeline_task_policy`)
  * introdurre tracing runtime task per lotto (`vendite.fatturazione_lotti_task_runs`)

## 9) Test gravita (stato corrente)

### Alta

> ⛔ **Non e' piu' un rischio: e' la risposta.** Il dominio pipeline attivita' fu
> costruito e **ritirato** il 2026-02-27, e la scelta e' stata riconfermata con
> Tid il 2026-06-18. I due processi non sono simmetrici: AF -> fatturazione e' un
> ciclo di vita **fiscale stateful** (il motore lo merita), commessa -> AF e' una
> **promozione idempotente** (non lo merita).

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

## 10.1 Pipeline giornaliera: convergenza canale unico chiusura lotto

### Esito adottato

La chiusura operativa lotto avviene con un solo meccanismo:

1. a fine step, il runner verifica `config.stati_doc_fiscale.chiude_lotto`
2. se `true`, chiude il lotto operativamente
3. se lo step fallisce, non avviene chiusura

### Rischio tecnico

* transizioni duplicate o non deterministiche
* log step meno leggibili (chiusura non centralizzata)
* maggior rischio regressioni quando si estende a nuovi domini pipeline

### Regole operative

* Niente chiusure implicite per stato specifico (`INVIATA`) hardcoded nel runner.
* Niente task pipeline dedicati `close_lotto`.
* Parametrizzazione solo su stato configurato (`chiude_lotto=true`).

### Decisione proposta

Convergere a canale unico (opzione 1) per avere comportamento esplicito, testabile e coerente con il modello registry/task.
