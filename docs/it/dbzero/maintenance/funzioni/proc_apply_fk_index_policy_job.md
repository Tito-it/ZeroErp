{% include-markdown "it/dbzero/maintenance/manual/proc_apply_fk_index_policy_job.md" %}
# ⚙️ Procedura `proc_apply_fk_index_policy_job`

```sql
CREATE PROCEDURE proc_apply_fk_index_policy_job(IN p_populate boolean)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE PROCEDURE maintenance.proc_apply_fk_index_policy_job(IN p_populate boolean DEFAULT false)
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'topology', 'pg_temp'
AS $procedure$
  BEGIN
    PERFORM maintenance.fn_run_and_log(
      p_jobname  := 'apply_fk_index_policy',
      p_stepname := 'run_apply_fk_index_policy',
      p_sql      := CASE
                      WHEN p_populate THEN
                        'SELECT dbops.fn_populate_fk_index_policy(); CALL dbops.apply_fk_index_policy();'
                      ELSE
                        'CALL dbops.apply_fk_index_policy();'
                    END,
      p_lock_key := hashtext('apply_fk_index_policy')
    );
  END;
$procedure$

COMMENT ON PROCEDURE maintenance.proc_apply_fk_index_policy_job(IN p_populate boolean)
IS 'Job wrapper per chiamare apply_fk_index_policy con logging e lock.';
```

</div>

---
{% include-markdown "signature-core.md" %}
