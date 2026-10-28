{% include-markdown "it/dbzero/maintenance/manual/proc_automations_delete_block_job.md" %}
# ⚙️ Procedura `proc_automations_delete_block_job`

```sql
CREATE PROCEDURE proc_automations_delete_block_job()
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE PROCEDURE maintenance.proc_automations_delete_block_job()
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'topology', 'pg_temp'
AS $procedure$
  BEGIN
    PERFORM maintenance.fn_run_and_log(
      p_jobname  := 'automations_delete_block',
      p_stepname := 'run_automations_delete_block',
      p_sql      := 'SELECT dbops.fn_run_automations_delete_block(''SCHEDULED'', NULL, false);',
      p_lock_key := hashtext('automations_delete_block')
    );
  END;
$procedure$

COMMENT ON PROCEDURE maintenance.proc_automations_delete_block_job()
IS 'Job wrapper per chiamare fn_run_automations_delete_block con logging e lock.';
```

</div>

---
{% include-markdown "signature-core.md" %}
