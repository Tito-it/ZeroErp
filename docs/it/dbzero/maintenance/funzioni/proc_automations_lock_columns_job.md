{% include-markdown "it/dbzero/maintenance/manual/proc_automations_lock_columns_job.md" %}
# ⚙️ Procedura `proc_automations_lock_columns_job`

```sql
CREATE PROCEDURE proc_automations_lock_columns_job()
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE PROCEDURE maintenance.proc_automations_lock_columns_job()
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'topology', 'pg_temp'
AS $procedure$
  BEGIN
    -- rev 20260923-46: anche il guard delle date di validita'
    --   (automazione DATE_VALIDITA), stessa famiglia del lock.
    -- rev 20260926-05: niente piu' fn_run_automations_drop_lock_trg;
    --   togliere un lock e' un'azione del runner che converge.
    PERFORM maintenance.fn_run_and_log(
      p_jobname  := 'automations_lock_columns',
      p_stepname := 'run_automations_lock_columns',
      p_sql      := 'SELECT dbops.fn_run_automations_lock_columns(''SCHEDULED'', NULL, false); ' ||
                   'SELECT dbops.fn_run_automations_date_validita(''SCHEDULED'', NULL, false);',
      p_lock_key := hashtext('automations_lock_columns')
    );
  END;
$procedure$

COMMENT ON PROCEDURE maintenance.proc_automations_lock_columns_job()
IS 'Wrapper del processo automations_lock_columns: in una sola corsa esegue in modo SCHEDULED dbops.fn_run_automations_lock_columns e poi dbops.fn_run_automations_date_validita su tutto l''ambito, passando da maintenance.fn_run_and_log, che registra la corsa in maintenance.job_run_log sotto il codice del processo e tiene un advisory lock contro due corse sovrapposte. Non aggiunge logica. Il primo runner porta i trigger di lock di colonna al registro dichiarato: li crea, li rigenera, li toglie; se un lock vivo blocca una colonna che il registro non nomina, si ferma con E_LOCK_COLUMNS prima di ogni DDL. Il secondo monta, sulle tabelle con valido_dal e valido_al, il guard che rifiuta una fine precedente all''inizio. Le due istruzioni stanno nella stessa transazione e lasciano una riga sola nel giornale: se il lock si ferma, il guard delle date quella volta non gira. Lo chiamano il job pgAgent automations_lock_columns e la convergenza del rilascio (dbops.processi.ci_ordine). SECURITY DEFINER: gira come il proprietario, non come il ruolo con cui si collega pgAgent.';
```

</div>

---
{% include-markdown "signature-core.md" %}
