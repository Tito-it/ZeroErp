## 📘 Documentazione Concettuale – Funzione `vendite.fn_set_runtime_task_run_esito`

### 🎯 Scopo Principale

Helper condiviso per applicare l'esito runtime di un task-run
nei domini `LOTTO` e `ATTIVITA_FATTURABILI`.

---

### Regole principali

* `p_scope` obbligatorio (`LOTTO|ATTIVITA_FATTURABILI`)
* `p_task_run_id` obbligatorio (`> 0`)
* `p_task_stato` obbligatorio (`COMPLETATO|ERRORE|ANNULLATO`)
* aggiorna sempre:
  * `task_stato`
  * `ended_at`
  * merge `meta`
* su `ERRORE` valorizza `error_code/error_message` con fallback dominio

---

### Utilizzo previsto

* usata dalle funzioni wrapper:
  * `fn_complete_lotto_task_run`
  * `fn_fail_lotto_task_run`
  * `fn_cancel_lotto_task_run`
  * `fn_complete_attivita_lotto_task_run`
  * `fn_fail_attivita_lotto_task_run`
  * `fn_cancel_attivita_lotto_task_run`

---

{% include-markdown "signature-core.md" %}
