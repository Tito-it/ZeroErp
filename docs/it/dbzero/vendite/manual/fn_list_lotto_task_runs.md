## 📘 Documentazione Concettuale – Funzione `vendite.fn_list_lotto_task_runs`

### 🎯 Scopo Principale

Elenca i task run di un lotto, con filtri opzionali per step e task.

---

### ✅ Regole principali

* `p_lotto_id` obbligatorio (`> 0`)
* filtri opzionali:
  * `p_stato_doc_fiscale_id`
  * `p_task_code`
* ordinamento cronologico (`started_at`, `id`)

---

### ✅ Output

Set di righe runtime task con:
* contesto lotto/step/pipeline
* stato task e tentativo
* tempi di esecuzione
* dettagli errore
* metadati

---

{% include-markdown "signature-core.md" %}
