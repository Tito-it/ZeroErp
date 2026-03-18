## 📘 Documentazione Concettuale – Procedura `maintenance.proc_automations_cleanup_job`

> 👀 **Vedi anche**
>
Guide:
> [Automazione DB](/guide/automazione-db)
>
Approfondimento funzioni:
> [dbops.fn_run_automations_cleanup](/dbzero/dbops/funzioni/fn_run_automations_cleanup)
> [maintenance.fn_run_and_log](/dbzero/maintenance/funzioni/fn_run_and_log)

---
### 🎯 Scopo Principale
(latest review 07-02-26)
La procedura **`maintenance.proc_automations_cleanup_job()`** e' un wrapper
per eseguire `dbops.fn_run_automations_cleanup` in modalita' schedulata,
con logging centralizzato e lock applicativo anti-overlap.

---

### Logica operativa

1. Chiama `maintenance.fn_run_and_log` con:
   * `p_jobname = 'automations_cleanup'`
   * `p_stepname = 'run_automations_cleanup'`
   * `p_sql = SELECT dbops.fn_run_automations_cleanup('SCHEDULED', ARRAY['dbops'], false)`
2. Usa `hashtext('automations_cleanup')` come lock per impedire esecuzioni concorrenti.

---

### Esempio di esecuzione

`CALL maintenance.proc_automations_cleanup_job();`

---

{% include-markdown "signature-core.md" %}
