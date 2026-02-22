## 📘 Documentazione Concettuale – Tabella `vendite.attivita_fatturabili_pipeline_task_policy`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [vendite.attivita_fatturabili_pipeline](/dbzero/vendite/tabelle/attivita_fatturabili_pipeline)  
> • [vendite.attivita_fatturabili_lotti_task_runs](/dbzero/vendite/tabelle/attivita_fatturabili_lotti_task_runs)  
>
---

### 🎯 Scopo Principale

La tabella `vendite.attivita_fatturabili_pipeline_task_policy` definisce le regole
runtime dei task della pipeline attività, con supporto a branch indipendenti.

Serve a governare in modo configurabile:

* se un task e` annullabile,
* come gestire la ripartenza (`resume_mode`),
* quale scope di blocco applicare in errore (`block_scope`),
* dipendenze opzionali (`depends_on`) tra task/step.

---

### ✅ Regole principali

* Chiave logica unica: `pipeline_id + branch_code + task_code`.
* `resume_mode` ammessi:
  * `RESET_STEP`
  * `RESUME_STEP`
  * `RESUME_TASK`
  * `RESUME_BRANCH`
* `block_scope` ammessi:
  * `BRANCH`
  * `GLOBAL`
* `attivo=true` abilita l'applicazione della policy nel runner.

---

### 🧩 Utilizzo previsto

* consultata dal runner attività prima dell'esecuzione task,
* usata per isolare il blocco su singolo branch o su run globale,
* base per resume/rerun branch-oriented.

---

{% include-markdown "signature-core.md" %}
