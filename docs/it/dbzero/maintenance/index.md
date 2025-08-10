# Schema `maintenance`

## 📚 Tabelle
- [job_run_log](tabelle/job_run_log.md) — La tabella `maintenance.job_run_log` memorizza i log di esecuzione dei job schedulati o lanciati manualmente all’interno del sistema Zero ERP. Ogni riga rappresenta una singola esecuzione di un job, includendo informazioni di stato, tempi di inizio/fine, eventuali errori e dettagli di esecuzione.
- [test_pgagent_log](tabelle/test_pgagent_log.md)

## ⚙️ Funzioni
- [fn_run_and_log](funzioni/fn_run_and_log.md) — `maintenance.fn_run_and_log` esegue in modo sicuro uno *statement* SQL arbitrario e ne registra l’esecuzione su `maintenance.job_run_log`, gestendo in modo opzionale un **lock consulente** (advisory lock) per prevenire esecuzioni sovrapposte dello stesso job/step.
- [proc_apply_storicizza_defaults_job](funzioni/proc_apply_storicizza_defaults_job.md) — * **Eseguire in modo schedulato** l’applicazione delle **impostazioni di storicizzazione di default** sull’intero database, incapsulando la chiamata a `dbops.proc_apply_storicizza_defaults()` in un wrapper **robusto** con **lock anti-overlap** e **logging strutturato**.

## 🔍 Views
