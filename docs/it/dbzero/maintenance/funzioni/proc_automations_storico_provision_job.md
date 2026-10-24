{% include-markdown "it/dbzero/maintenance/manual/proc_automations_storico_provision_job.md" %}
# ⚙️ Procedura `proc_automations_storico_provision_job`

```sql
CREATE PROCEDURE proc_automations_storico_provision_job()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE PROCEDURE maintenance.proc_automations_storico_provision_job()
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'topology', 'pg_temp'
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

</div>

---
{% include-markdown "signature-core.md" %}
