---
search:
  exclude: true
---

# Schema `maintenance`

## 📚 Tabelle (manuale)
- [job_run_log](manual/job_run_log.md) — (latest review 18-06-2026) La tabella `maintenance.job_run_log` memorizza i log di esecuzione dei job schedulati o lanciati manualmente all’interno del sistema Zero ERP. Ogni riga rappresenta una singola esecuzione di un job, includendo informazioni di stato, tempi di inizio/fine, eventuali errori e dettagli di esecuzione.

## ⚙️ Funzioni (manuale)
- [fn_analyze_statistiche](manual/fn_analyze_statistiche.md) — (latest review 14-10-2026)
- [fn_job_run_log_failure](manual/fn_job_run_log_failure.md) — (latest review 05-09-2026)
- [fn_run_and_log](manual/fn_run_and_log.md) — (latest review 07-01-26) `maintenance.fn_run_and_log` esegue in modo sicuro uno *statement* SQL arbitrario e ne registra l’esecuzione su `maintenance.job_run_log`, gestendo in modo opzionale un **lock consulente** (advisory lock) per prevenire esecuzioni sovrapposte dello stesso job/step.
- [fn_sveglia_accesa](manual/fn_sveglia_accesa.md)
- [proc_analyze_statistiche_job](manual/proc_analyze_statistiche_job.md) — (latest review 14-10-2026)
- [proc_apply_fk_index_policy_job](manual/proc_apply_fk_index_policy_job.md) — (latest review 16-01-26) * **Eseguire in modo schedulato** l’applicazione della **policy indici FK** incapsulando la chiamata a `dbops.apply_fk_index_policy()` in un wrapper **robusto** con **lock anti-overlap** e **logging strutturato**.
- [proc_apply_storicizza_defaults](manual/proc_apply_storicizza_defaults.md) — (latest review 05-09-2026)
- [proc_apply_storicizza_defaults_job](manual/proc_apply_storicizza_defaults_job.md) — (latest review 07-01-26) * **Eseguire in modo schedulato** l’applicazione delle **impostazioni di storicizzazione di default** sull’intero database, incapsulando la chiamata a `maintenance.proc_apply_storicizza_defaults()` in un wrapper **robusto** con **lock anti-overlap** e **logging strutturato**.
- [proc_automations_attivo_job](manual/proc_automations_attivo_job.md) — (latest review 07-01-26) * **Eseguire in modo schedulato** l’orchestrazione delle **automazioni ATTIVO** (soft-delete / vincoli di coerenza “attivo”) incapsulando la chiamata a `dbops.fn_run_automations_attivo(...)` in un wrapper **robusto** con **lock anti-overlap** e **logging strutturato**.
- [proc_automations_audit_update_job](manual/proc_automations_audit_update_job.md) — (latest review 07-01-26) * **Eseguire in modo schedulato** l’orchestrazione delle **automazioni AUDIT_UPDATE** (trigger di audit su UPDATE) incapsulando la chiamata a `dbops.fn_run_automations_audit_update(...)` in un wrapper **robusto** con **lock anti-overlap** e **logging strutturato**.
- [proc_automations_cleanup_job](manual/proc_automations_cleanup_job.md) — (latest review 07-02-26) La procedura **`maintenance.proc_automations_cleanup_job()`** e' un wrapper per eseguire `dbops.fn_run_automations_cleanup` in modalita' schedulata, con logging centralizzato e lock applicativo anti-overlap.
- [proc_automations_delete_block_job](manual/proc_automations_delete_block_job.md) — (latest review 23-01-26) La procedura **`maintenance.proc_automations_delete_block_job()`** e' un wrapper per eseguire `dbops.fn_run_automations_delete_block` in modalita' job con logging centralizzato e lock applicativo.
- [proc_automations_lock_columns_job](manual/proc_automations_lock_columns_job.md) — (latest review 11-01-26) * **Eseguire in modo schedulato** l’orchestrazione delle **automazioni LOCK_COLUMNS** (trigger di blocco colonne) incapsulando la chiamata a `dbops.fn_run_automations_lock_columns(...)` e il cleanup dei trigger obsoleti in un wrapper **robusto** con **lock anti-overlap** e **logging strutturato**.
- [proc_automations_overlap_job](manual/proc_automations_overlap_job.md) — (latest review 02-06-26) La procedura **`maintenance.proc_automations_overlap_job()`** e' un wrapper per eseguire `dbops.fn_apply_automazione_overlap` in modalita' schedulata, con logging centralizzato e lock applicativo anti-concorrenza.
- [proc_automations_storico_job](manual/proc_automations_storico_job.md) — (latest review 07-01-26) * **Eseguire in modo schedulato** l’orchestrazione delle **automazioni STORICO** (trigger di storicizzazione su UPDATE/DELETE) incapsulando la chiamata a `dbops.fn_run_automations_storico(...)` in un wrapper **robusto** con **lock anti-overlap** e **logging strutturato**.
- [proc_automations_storico_provision_job](manual/proc_automations_storico_provision_job.md) — (latest review 07-01-26) * **Eseguire in modo schedulato** il **provisioning delle automazioni STORICO** (setup/adeguamento dei trigger di storicizzazione) incapsulando la chiamata a `dbops.fn_run_automations_storico_provision(...)` in un wrapper **robusto** con **lock anti-overlap** e **logging strutturato**.
- [proc_automations_tx_id_job](manual/proc_automations_tx_id_job.md) — (latest review 07-01-26) * **Eseguire in modo schedulato** l’orchestrazione delle **automazioni TX_ID** (policy di transazione su tabelle nell'ambito) incapsulando la chiamata a `dbops.fn_run_automations_tx_id(...)` in un wrapper **robusto** con **lock anti-overlap** e **logging strutturato**.
- [proc_bump_indirizzi_dettaglio](manual/proc_bump_indirizzi_dettaglio.md) — (latest review 02-01-26) Riallineare la normalizzazione degli indirizzi di dettaglio quando cambia la via (stradario) in modo controllato e tracciato.
- [proc_bump_toponomastica](manual/proc_bump_toponomastica.md) — (latest review 02-01-26) Consentire la correzione controllata di un toponimo **in uso**, forzando la rinormalizzazione di `config.stradario_generale` tramite i trigger esistenti.
- [proc_sync_storico_set_storicizza](manual/proc_sync_storico_set_storicizza.md) — (latest review 05-09-2026)
- [proc_sync_storico_set_storicizza_job](manual/proc_sync_storico_set_storicizza_job.md) — (last review 07-01-26) Wrapper di job che **esegue e traccia** la sincronizzazione della tabella `config.storico_set_storicizza`, delegando l’esecuzione alla procedura core `maintenance.proc_sync_storico_set_storicizza()` e centralizzando **logging** e **advisory lock** tramite `maintenance.fn_run_and_log`.

## 🔍 Views (manuale)
- [vw_job_run_da_guardare](manual/vw_job_run_da_guardare.md) — (latest review 18-10-2026)
- [vw_statistiche_mancanti](manual/vw_statistiche_mancanti.md) — (latest review 14-10-2026)

## ⏰ Job pgAgent
- [I job pgAgent](job_pgagent.md) — quali lavori a orario esistono, quando partono e che cosa chiamano
