{% include-markdown "it/dbzero/maintenance/manual/proc_apply_fk_index_policy_job.md" %}
# ⚙️ Procedura `proc_apply_fk_index_policy_job`

```sql
CREATE PROCEDURE proc_apply_fk_index_policy_job()
```

**Definizione completa:**

```sql
CREATE OR REPLACE PROCEDURE maintenance.proc_apply_fk_index_policy_job()
 LANGUAGE plpgsql
AS $procedure$
  BEGIN
    PERFORM maintenance.fn_run_and_log(
      p_jobname  := 'apply_fk_index_policy',
      p_stepname := 'run_apply_fk_index_policy',
      p_sql      := 'CALL dbops.apply_fk_index_policy();',
      p_lock_key := hashtext('apply_fk_index_policy')
    );
  END;
$procedure$

COMMENT ON PROCEDURE maintenance.proc_apply_fk_index_policy_job()
IS 'Job wrapper per chiamare apply_fk_index_policy con logging e lock.';
```

---
{% include-markdown "signature-core.md" %}
