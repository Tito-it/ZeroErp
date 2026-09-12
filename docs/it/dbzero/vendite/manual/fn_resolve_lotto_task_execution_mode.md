## 📘 Documentazione Concettuale – Funzione `vendite.fn_resolve_lotto_task_execution_mode`
### 🎯 Scopo Principale
Determina in modo deterministico la modalita` di esecuzione del task:
`RUN`, `SKIP`, `RESUME`, `RESET_REQUIRED`.

---

### Regole principali

* input obbligatori: `lotto_id`, `pipeline_id`, `task_code`
* legge policy task da `vendite.fatturazione_pipeline_task_policy`
* legge ultimo run da `vendite.fatturazione_lotti_task_runs`
* decisione:
  * nessun run precedente -> `RUN`
  * ultimo `COMPLETATO` -> `SKIP`
  * ultimo `IN_ESECUZIONE`/`ERRORE`:
    * `RESUME_TASK` -> `RESUME`
    * altrimenti (`RESET_STEP`) -> `RESET_REQUIRED`
  * ultimo `ANNULLATO` -> `RUN`

⚠️ **Risponde alla domanda che gli si fa, per task**, guardando la sola ultima
corsa di *quel* task. Un `COMPLETATO → SKIP` è corretto per il task, ma al
rilancio di uno step **a valle di un task rieseguito** quel `SKIP` va ignorato:
l'input è appena cambiato. La domanda «qualcosa a monte è stato eseguito in
questo giro?» la sa solo l'**orchestratore**, ed è lì che vive la regola di
catena (`PipelineStepExecutor`, 12-09-2026). ⛔ Non cercarla qui, e non
aggiungerla qui: duplicherebbe o contraddirebbe quella. Per questo
`RESUME_STEP` — che prometteva nel nome una ripresa «a livello di step» e non la
faceva — è stato ritirato (`20260912-32`, `-33`). Brief:
`brief-db-rilancio-step-non-rivede-le-proprie-commesse` §10.2-10.3.

---

### Output

Una riga con:
* `execution_mode`
* policy (`annullabile`, `resume_mode`, `policy_meta`)
* stato ultimo run (`last_task_stato`, `last_tentativo`, `run_meta`)

---

{% include-markdown "signature-core.md" %}
