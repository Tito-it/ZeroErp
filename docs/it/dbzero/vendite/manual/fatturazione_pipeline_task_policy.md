## 📘 Documentazione Concettuale – Tabella `vendite.fatturazione_pipeline_task_policy`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [vendite.fatturazione_pipeline](/dbzero/vendite/tabelle/fatturazione_pipeline)  
> • [vendite.fatturazione_lotti_task_runs](/dbzero/vendite/tabelle/fatturazione_lotti_task_runs)  
>
---

### 🎯 Scopo Principale

La tabella `vendite.fatturazione_pipeline_task_policy` definisce le regole operative
per ciascun task della pipeline fatturazione.

Serve a governare in modo configurabile:

* se un task e` annullabile,
* come gestire la ripartenza (`resume_mode`),
* eventuali metadati runtime.

---

### ✅ Regole principali

* Chiave logica unica: `pipeline_id + task_code`.
* `resume_mode` ammessi:
  * `RESET_STEP`
  * `RESUME_STEP`
  * `RESUME_TASK`
* `attivo=true` abilita l'applicazione della policy nel runner.

---

### 🧩 Utilizzo previsto

* consultata dal runner Django prima dell'esecuzione task,
* usata per decidere percorso in errore/rilancio/reset,
* separa policy di runtime dalla configurazione “sequenza task” della pipeline.

---

{% include-markdown "signature-core.md" %}
