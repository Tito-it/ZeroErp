## 📘 Documentazione Concettuale – Tabella `vendite.fatturazione_pipeline_task_policy`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.fatturazione_pipeline](/dbzero/vendite/tabelle/fatturazione_pipeline)  
> • [vendite.fatturazione_lotti_task_runs](/dbzero/vendite/tabelle/fatturazione_lotti_task_runs)  
>
### 🎯 Scopo Principale
La tabella `vendite.fatturazione_pipeline_task_policy` definisce le regole operative
per ciascun task della pipeline fatturazione.

Serve a governare in modo configurabile:

* se un task e` annullabile,
* come gestire la ripartenza (`resume_mode`),
* eventuali metadati runtime.

---

### Regole principali

* Chiave logica unica: `pipeline_id + task_code`.
* `resume_mode` ammessi:
  * `RESET_STEP` — la corsa ferma non riprende: serve un reset (`RESET_REQUIRED`)
  * `RESUME_TASK` — la corsa `IN_ESECUZIONE`/`ERRORE` riprende (`RESUME`)
  * ⛔ `RESUME_STEP` è stato **ritirato il 12-09-2026** (`00_schema/20260912-32`):
    il resolver lo trattava come `RESUME_TASK` e nessuno lo implementava — una
    distinzione senza differenza. La «ripresa a livello di step» (a valle di un
    task eseguito in questo giro nessun task si salta) è una regola
    dell'**orchestratore** (`PipelineStepExecutor`), non una policy per task: la
    domanda «qualcosa a monte è stato eseguito?» la sa solo lui. Il CHECK respinge
    il valore (pgTAP `test-fatturazione-pipeline-task-runtime` 19). Brief:
    `brief-db-rilancio-step-non-rivede-le-proprie-commesse` §10.3
* `attivo=true` abilita l'applicazione della policy nel runner.

---

### Utilizzo previsto

* consultata dal runner Django prima dell'esecuzione task,
* usata per decidere percorso in errore/rilancio/reset,
* separa policy di runtime dalla configurazione “sequenza task” della pipeline.

---

{% include-markdown "signature-core.md" %}
