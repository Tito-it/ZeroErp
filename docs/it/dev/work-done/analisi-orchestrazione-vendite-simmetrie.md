# Analisi — Simmetrie di orchestrazione del ciclo vendite (commesse → AF → fatturazione)

> **Tipo**: doc di analisi / promemoria di disegno. **NON è un brief DB né un piano
> esecutivo**: serve a fissare conclusioni e candidati emersi in sessione, per non
> perderli. Nessuna azione DB/BE parte da qui senza un brief/piano dedicato e l'ok di Tid.
>
> **Data**: 2026-06-18 · **Stato**: 🔵 ANALISI (solo conclusioni, niente codice)
>
> **Origine**: discussione a valle del gap `tipo_doc_fiscale` nel batch fatturazione
> (vedi [brief-db-emittibili-lane-tipo-doc-fiscale.md](brief-db-emittibili-lane-tipo-doc-fiscale.md)).
> Tre temi: (A) quanto è generico il motore pipeline, (B) candidato BB "fan-out isolato"
> da non perdere, (C) avanzamento stati lotto AF→fatturazione innescato da UI.

---

## A. Stato del motore pipeline: già generico, e una lezione storica

**Il motore è già generico e multi-dominio per disegno:**

- Registry a DB pensato per N domini: `dbops.domini_task` (seedati **due** domini:
  `FATTURAZIONE` e `ATTIVITA_FATTURABILI`), `dbops.pipeline_task_registry`,
  `dbops.pipeline_task_registry_impl` (dispatch via `implementation_key`, niente eval
  dinamico). Funzioni `dbops.fn_check_pipeline_task_registered` /
  `fn_get_pipeline_task_implementation` + pgTAP.
- Runner/executor applicativi (`LottoPipelineRunner`, `PipelineStepExecutor`) con **logica
  di dominio ~zero**: risolvono gli step da tabella, fallback (utility/tipo_doc), tracing
  task-run, rollback. Unico accoppiamento: `VenditePipelineRepository.DOMINIO_CODE =
  "FATTURAZIONE"` come default + la `handler_registry` (10 handler di fatturazione).
- Visione documentata in [pipeline-domini-engine.md](pipeline-domini-engine.md):
  "pipeline DB separate per dominio, engine applicativo unico".

**Lezione storica decisiva** (`db/changelog/.../20260227-16-drop-attivita-pipeline-deprecated`):
fu costruito un **intero sottosistema pipeline stateful per le attività** (15 funzioni:
`fn_get_or_create_lotto_attivita`, `fn_set_attivita_lotto_stato`,
`fn_*_attivita_lotto_task_run`, branch policy…, + tabelle task-run dedicate) e poi
**droppato**. In parallelo `fn_emit_attivita_fatturabili_da_commessa` ha **perso**
`p_lotto_attivita_id`. Il processo **commessa→AF** è stato **collassato** in un singolo
task idempotente (`pull_attivita_da_commessa`), step 0 della pipeline FATTURAZIONE.

**Conclusione A**: i due processi *non sono simmetrici nell'essenza*:

| Processo | Natura | Ha bisogno del motore pipeline? |
|---|---|---|
| AF → fatturazione | ciclo di vita **fiscale stateful** (stati DRAFT→EMESSA→DEFINITIVA→INVIATA, numerazione, rollback) | **Sì** — giustamente è un dominio pipeline pieno |
| commessa → AF | **promozione idempotente stateless** (scopri → emetti → marca EMESSA) | **No** — è un fan-out; la macchina pesante fu provata e ritirata |

→ **Non** ricostruire commessa→AF come dominio pipeline: re-litiga la deprecazione
`20260227-16`. Decisione confermata con Tid (2026-06-18).

---

## B. Candidato BB da NON perdere — "fan-out con isolamento + run log"

La simmetria *reale e utile* è più in basso. Due processi condividono la stessa forma:

| Fase | `sorgenti → commessa` (`CommessaPushOrchestrator._run_locked`) | `commessa → AF` (`PipelineStepExecutor._handle_pull_attivita_da_commessa_task`) |
|---|---|---|
| discovery | `_resolve_handlers(source_types)` | `commesse_repository.list_commesse_emittibili(...)` |
| fan-out isolato | `for handler: try/except → HandlerResult` | `for commessa: transaction.atomic (savepoint) + try/except → errors[]` |
| aggregazione esito | `_compute_stato(results)` | "se tutte falliscono → raise; altrimenti prosegui" |
| log del run | `PUSH_STARTED` / `log_push_run` + `event_log` | `event_log` + `PipelineErrorLogger` |

Entrambi reimplementano a mano: **"scopri item → per ognuno isola l'errore (savepoint) →
aggrega esiti → logga il run"**.

**Candidato** ([feedback_regola_del_2_estrai_bb]): estrarre un BB generico di fan-out, es.
`apps/core/services/` — concettualmente:

```
risultato = run_fan_out(
    items=<iterabile discovery>,
    process=<callable per-item>,        # eseguito in savepoint
    on_error=<policy: skip+log | abort>,
    aggregate=<callable esiti → stato>, # es. ALL_OK / PARTIAL / ALL_FAIL
    run_logger=<start/end run + event_log>,
)
```

**Stato**: 🟡 **DICHIARATO, NON ESEGUITO**. Mini-protocollo regola del 2 rispettato:
candidato dichiarato a chat, **in attesa ok di Tid**. Caveat anti-astrazione-prematura:
**estrarre toccando ENTRAMBI i call-site insieme** (push + pull), non da un solo sito
vivo. Da fare come task a sé, **NON** innestato nel fix del gap `tipo_doc_fiscale` (che
tocca solo il lato pull/driver).

**Quando**: dopo la chiusura del gap `tipo_doc_fiscale`. Vedi conclusione condivisa
"punto 2" della sessione 2026-06-18.

---

## C. Avanzamento stati lotto AF→fatturazione da UI — cosa esiste e cosa predisporre

**Contesto (Tid)**: l'avanzamento degli stati del lotto (DRAFT→EMESSA→DEFINITIVA→…)
sarà **quasi sempre innescato da UI** (operatore), non da schedulazione. Serve capire il
collegamento con quanto fatto sul driver commesse.

### C.1 Cosa esiste GIÀ (più di quanto sembri)

L'orchestrazione di avanzamento è già a due velocità, **entrambe già esposte**:

- **Single-step** — `LottoPipelineRunner.run_pipeline()` esegue **UN solo step per
  chiamata** (avanzamento incrementale; resume/rollback gestiti). Endpoint UI:
  `POST /api/v1/vendite/pipeline/run/` (`ApiRunLottoPipeline`).
- **Run-until-done** — `run_lotto_until_done()` cicla `run_pipeline` finché la catena si
  esaurisce o lo stato `chiude_lotto`. Endpoint UI:
  `POST /api/v1/vendite/pipeline/run-until-done/`.
- **Reset/rollback** — endpoint reset lotto (DRAFT) + rollback step già presenti.

Lo **stesso orchestratore** serve due trigger diversi: il **cron**
(`run_fatturazione_batch`) è solo un *wrapper sottile* attorno a `run_until_done`, sotto
**contesto SISTEMA** (RLS Path A, `system_process_context`) + registrazione in
`job_run_log`. La UI usa gli stessi entrypoint sotto **scope OPERATORE** (JWT normale).

> **Link forte con le commesse**: la logica di avanzamento è **context-agnostica**; è il
> *trigger* a scegliere il regime DB. Cron → contesto sistema + job_run_log; UI → scope
> operatore + event_log. Nessun ramo di codice duplicato per i due mondi.

### C.2 Il vero GAP da predisporre — "azioni disponibili del lotto" data-driven

Oggi **non esiste** un `fn_available_actions_lotto` (esistono i gemelli per
`commessa`/`offerta`/`contratto`). Per una UI pulita, l'operatore deve sapere **quale
transizione è ammessa ORA** su QUESTO lotto, senza che il FE conosca la macchina di stati.

Pattern da replicare (simmetria con `fn_available_actions_commessa` +
`POST /commesse/<id>/stato/`):

- **`fn_available_actions_lotto(lotto_id)`** (DB, data-driven): legge stato lotto +
  `config.stati_doc_fiscale_transizioni` + eventuali segnalazioni bloccanti
  (`LottoSegnalazioniService`) e ritorna le azioni ammesse: `avanza` (→ prossimo stato),
  `avanza_fino_a_fine`, `reset_a_draft`, `rollback_step`, ciascuna con capability/abilitato
  + motivo se disabilitata.
- **FE**: bottoni guidati dalle capability (niente stato cablato lato client), come già
  fatto per commesse/offerte/contratti.
- **Endpoint**: riusare gli esistenti `pipeline/run/` (= "avanza"), `run-until-done/`,
  reset. Eventuale endpoint unico `POST /lotti/<id>/azione/` solo se serve uniformare.

### C.3 Cosa NON serve

- **Niente nuovo motore**: l'avanzamento c'è già (single-step + until-done).
- **Niente schedulazione obbligatoria**: per AF→fatturazione il path primario è UI; il
  cron/sistema resta opzionale (corsia immediata/differita). Il `job_run_log` è per i run
  *headless*; un avanzamento da UI **non** va in `job_run_log` (è tracciato da `event_log`:
  `PIPELINE_STARTED`/`STEP_COMPLETED`/`PIPELINE_COMPLETED`).

### C.4 Conclusione C

Il "processo gemello" che serve **non è un nuovo orchestratore**: l'avanzamento stati è
già pronto e UI-esposto. Ciò che va **predisposto** è il layer **data-driven di azioni
disponibili del lotto** (`fn_available_actions_lotto` + capability FE), per dare
all'operatore la stessa esperienza guidata già presente su commesse. È un incremento
**piccolo e simmetrico**, non un nuovo sottosistema.

---

## Sintesi operativa (ordine consigliato)

1. **Gap `tipo_doc_fiscale`** (in corso): brief DB → BE driver. Priorità.
2. **`fn_available_actions_lotto` + capability FE** (conclusione C): incremento simmetrico
   quando si affronta la UI di fatturazione. Brief DB dedicato + FE.
3. **BB fan-out isolato** (conclusione B): refactor a sé, toccando push + pull insieme,
   solo dopo il punto 1 e con ok esplicito di Tid.
