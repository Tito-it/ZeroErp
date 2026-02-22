## 📘 Documentazione Concettuale – Funzione `vendite.fn_complete_attivita_lotto_task_run`

### 🎯 Scopo Principale

Chiude con successo un task-run runtime attività.

---

### ✅ Regole principali

* `p_task_run_id` obbligatorio (`> 0`)
* imposta `task_stato = COMPLETATO`
* valorizza `ended_at = now()`
* azzera `error_code` e `error_message`
* fonde `p_meta` nei metadati runtime

---

{% include-markdown "signature-core.md" %}
