# ⚙️ Procedura `proc_automations_storico_provision_job`

```sql
CREATE PROCEDURE proc_automations_storico_provision_job()
```

**Definizione completa:**

```sql
CREATE OR REPLACE PROCEDURE maintenance.proc_automations_storico_provision_job()
 LANGUAGE plpgsql
AS $procedure$
BEGIN
  PERFORM maintenance.fn_run_and_log(
    p_jobname  := 'automations_storico_provision',
    p_stepname := 'run_automations_storico_provision',
    p_sql      := 'SELECT dbops.fn_run_automations_storico_provision(''SCHEDULED'', NULL, false);',
    p_lock_key := hashtext('automations_storico_provision')
  );
END;
$procedure$
```

---
{% include-markdown "signature-core.md" %}
