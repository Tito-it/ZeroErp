## 📘 Documentazione Concettuale – Funzione `vendite.fn_fail_attivita_lotto_task_run`

### 🎯 Scopo Principale

Marca in errore un task-run runtime attività.

---

### ✅ Regole principali

* `p_task_run_id` obbligatorio (`> 0`)
* imposta `task_stato = ERRORE`
* valorizza `ended_at = now()`
* salva `error_code` (fallback `E_TASK_RUNTIME`) e `error_message`
* fonde `p_meta` nei metadati runtime

---

{% include-markdown "signature-core.md" %}
