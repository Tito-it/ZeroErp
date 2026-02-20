{% include-markdown "it/dbzero/maintenance/manual/proc_automations_cleanup_job.md" %}
# ⚙️ Procedura `proc_automations_cleanup_job`

```sql
CREATE PROCEDURE proc_automations_cleanup_job()
```

**Definizione completa:**

```sql
CREATE OR REPLACE PROCEDURE maintenance.proc_automations_cleanup_job()
 LANGUAGE plpgsql
AS $procedure$
  BEGIN
    PERFORM maintenance.fn_run_and_log(
      p_jobname  := 'automations_cleanup',
      p_stepname := 'run_automations_cleanup',
      p_sql      := 'SELECT dbops.fn_run_automations_cleanup(''SCHEDULED'', ARRAY[''dbops''], false);',
      p_lock_key := hashtext('automations_cleanup')
    );
  END;
$procedure$

COMMENT ON PROCEDURE maintenance.proc_automations_cleanup_job()
IS 'Job wrapper per chiamare fn_run_automations_cleanup con logging e lock.';
```

---
{% include-markdown "signature-core.md" %}
