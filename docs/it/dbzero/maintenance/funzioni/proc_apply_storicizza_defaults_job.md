{% include-markdown "it/dbzero/maintenance/manual/proc_apply_storicizza_defaults_job.md" %}
# ⚙️ Procedura `proc_apply_storicizza_defaults_job`

```sql
CREATE PROCEDURE proc_apply_storicizza_defaults_job()
```

**Definizione completa:**

```sql
CREATE OR REPLACE PROCEDURE maintenance.proc_apply_storicizza_defaults_job()
 LANGUAGE plpgsql
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
```

---
{% include-markdown "signature-core.md" %}
