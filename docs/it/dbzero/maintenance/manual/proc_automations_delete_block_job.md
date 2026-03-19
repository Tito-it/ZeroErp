## 📘 Documentazione Concettuale – Procedura `maintenance.proc_automations_delete_block_job`

> 👀 **Vedi anche**
>
Guide:
> [Automazione DB](/guide/automazione-db)
>
Approfondimento funzioni:
> [dbops.fn_run_automations_delete_block](/dbzero/dbops/funzioni/fn_run_automations_delete_block)

---
### 🎯 Scopo Principale
(latest review 23-01-26)
La procedura **`maintenance.proc_automations_delete_block_job()`** e' un wrapper
per eseguire `dbops.fn_run_automations_delete_block` in modalita' job con logging
centralizzato e lock applicativo.

---

### Logica operativa

1. Chiama `maintenance.fn_run_and_log` con:
   * `p_jobname = 'automations_delete_block'`
   * `p_stepname = 'run_automations_delete_block'`
   * `p_sql = SELECT dbops.fn_run_automations_delete_block('SCHEDULED', NULL, false)`
2. Usa `hashtext('automations_delete_block')` come lock per evitare esecuzioni concorrenti.

---

### Esempio di esecuzione

`CALL maintenance.proc_automations_delete_block_job();`

---

{% include-markdown "signature-core.md" %}
