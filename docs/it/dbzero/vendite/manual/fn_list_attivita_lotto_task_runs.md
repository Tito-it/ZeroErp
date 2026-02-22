## 📘 Documentazione Concettuale – Funzione `vendite.fn_list_attivita_lotto_task_runs`

### 🎯 Scopo Principale

Elenca i task-run di un lotto attività, con filtri opzionali per branch e task.

---

### ✅ Regole principali

* `p_lotto_attivita_id` obbligatorio (`> 0`)
* filtri opzionali:
  * `p_branch_code`
  * `p_task_code`
* ordinamento cronologico decrescente (`started_at DESC, id DESC`)

---

### ✅ Output

Set di righe runtime task con:
* contesto lotto/pipeline/sorgente/branch
* stato task e tentativo
* policy applicata (`block_scope`, `depends_on`)
* tempi di esecuzione
* dettagli errore
* metadati

---

{% include-markdown "signature-core.md" %}
