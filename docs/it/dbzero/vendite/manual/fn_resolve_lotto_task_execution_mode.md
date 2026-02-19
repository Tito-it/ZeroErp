## 📘 Documentazione Concettuale – Funzione `vendite.fn_resolve_lotto_task_execution_mode`

### 🎯 Scopo Principale

Determina in modo deterministico la modalita` di esecuzione del task:
`RUN`, `SKIP`, `RESUME`, `RESET_REQUIRED`.

---

### ✅ Regole principali

* input obbligatori: `lotto_id`, `pipeline_id`, `task_code`
* legge policy task da `vendite.fatturazione_pipeline_task_policy`
* legge ultimo run da `vendite.fatturazione_lotti_task_runs`
* decisione:
  * nessun run precedente -> `RUN`
  * ultimo `COMPLETATO` -> `SKIP`
  * ultimo `IN_ESECUZIONE`/`ERRORE`:
    * `RESUME_TASK` o `RESUME_STEP` -> `RESUME`
    * altrimenti -> `RESET_REQUIRED`
  * ultimo `ANNULLATO` -> `RUN`

---

### ✅ Output

Una riga con:
* `execution_mode`
* policy (`annullabile`, `resume_mode`, `policy_meta`)
* stato ultimo run (`last_task_stato`, `last_tentativo`, `run_meta`)

---

{% include-markdown "signature-core.md" %}
