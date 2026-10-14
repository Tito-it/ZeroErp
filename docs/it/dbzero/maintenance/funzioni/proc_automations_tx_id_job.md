{% include-markdown "it/dbzero/maintenance/manual/proc_automations_tx_id_job.md" %}
# ⚙️ Procedura `proc_automations_tx_id_job`

```sql
CREATE PROCEDURE proc_automations_tx_id_job()
```

**Definizione completa:**

```sql
CREATE OR REPLACE PROCEDURE maintenance.proc_automations_tx_id_job()
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'topology', 'pg_temp'
AS $procedure$
BEGIN
  PERFORM maintenance.fn_run_and_log(
    p_jobname  := 'automations_tx_id',
    p_stepname := 'run_automations_tx_id',
    p_sql      := 'SELECT dbops.fn_run_automations_tx_id(''SCHEDULED'', NULL, false);',
    p_lock_key := hashtext('automations_tx_id')
  );
END;
$procedure$
```

---
{% include-markdown "signature-core.md" %}
