{% include-markdown "it/dbzero/maintenance/manual/proc_automations_audit_update_job.md" %}
# ⚙️ Procedura `proc_automations_audit_update_job`

```sql
CREATE PROCEDURE proc_automations_audit_update_job()
```

**Definizione completa:**

```sql
CREATE OR REPLACE PROCEDURE maintenance.proc_automations_audit_update_job()
 LANGUAGE plpgsql
AS $procedure$
BEGIN
  PERFORM maintenance.fn_run_and_log(
    p_jobname  := 'automations_audit_update',
    p_stepname := 'run_automations_audit_update',
    p_sql      := 'SELECT dbops.fn_run_automations_audit_update(''SCHEDULED'', NULL, false);',
    p_lock_key := hashtext('automations_audit_update')
  );
END;
$procedure$
```

---
{% include-markdown "signature-core.md" %}
