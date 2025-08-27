# Schema `maintenance`

## 📚 Tabelle
- [job_run_log](tabelle/job_run_log.md) — La tabella `maintenance.job_run_log` memorizza i log di esecuzione dei job schedulati o lanciati manualmente all’interno del sistema Zero ERP. Ogni riga rappresenta una singola esecuzione di un job, includendo informazioni di stato, tempi di inizio/fine, eventuali errori e dettagli di esecuzione.
- [test_pgagent_log](tabelle/test_pgagent_log.md)

## ⚙️ Funzioni
- [fn_run_and_log](funzioni/fn_run_and_log.md) — `maintenance.fn_run_and_log` esegue in modo sicuro uno *statement* SQL arbitrario e ne registra l’esecuzione su `maintenance.job_run_log`, gestendo in modo opzionale un **lock consulente** (advisory lock) per prevenire esecuzioni sovrapposte dello stesso job/step.
- [proc_apply_storicizza_defaults_job](funzioni/proc_apply_storicizza_defaults_job.md) — * **Eseguire in modo schedulato** l’applicazione delle **impostazioni di storicizzazione di default** sull’intero database, incapsulando la chiamata a `dbops.proc_apply_storicizza_defaults()` in un wrapper **robusto** con **lock anti-overlap** e **logging strutturato**.
- [proc_automations_attivo_job](funzioni/proc_automations_attivo_job.md)
- [proc_automations_audit_update_job](funzioni/proc_automations_audit_update_job.md)
- [proc_automations_storico_job](funzioni/proc_automations_storico_job.md)
- [proc_automations_storico_provision_job](funzioni/proc_automations_storico_provision_job.md)
- [proc_automations_tx_id_job](funzioni/proc_automations_tx_id_job.md)
- [proc_sync_storico_set_storicizza_job](funzioni/proc_sync_storico_set_storicizza_job.md) — Wrapper di job che **esegue e traccia** la sincronizzazione della tabella `config.storico_set_storicizza`, delegando l’esecuzione alla procedura core `dbops.proc_sync_storico_set_storicizza()` e centralizzando **logging** e **advisory lock** tramite `maintenance.fn_run_and_log`.

## 🔍 Views
