{% include-markdown "it/dbzero/maintenance/manual/proc_apply_storicizza_defaults_job.md" %}
# ⚙️ Procedura `proc_apply_storicizza_defaults_job`

```sql
CREATE PROCEDURE proc_apply_storicizza_defaults_job()
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE PROCEDURE maintenance.proc_apply_storicizza_defaults_job()
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'topology', 'pg_temp'
AS $procedure$
     BEGIN
       PERFORM maintenance.fn_run_and_log(
         p_jobname  := 'apply_storicizza_weekly',
         p_stepname := 'run_proc_apply_storicizza',
         p_sql      := 'call maintenance.proc_apply_storicizza_defaults();',
         p_lock_key := hashtext('proc_apply_storicizza_defaults')  -- evita overlap
       );
     END;
     
   $procedure$

COMMENT ON PROCEDURE maintenance.proc_apply_storicizza_defaults_job()
IS 'Job wrapper per chiamare proc_apply_storicizza_defaults con logging e lock.';
```

</div>

---
{% include-markdown "signature-core.md" %}
