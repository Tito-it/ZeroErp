## 📘 Documentazione Concettuale – Funzione `vendite.fn_cancel_attivita_lotto_task_run`

### 🎯 Scopo Principale

Marca come annullato un task-run runtime attività.

---

### ✅ Regole principali

* `p_task_run_id` obbligatorio (`> 0`)
* imposta `task_stato = ANNULLATO`
* valorizza `ended_at = now()`
* fonde `p_meta` nei metadati runtime

---

{% include-markdown "signature-core.md" %}
