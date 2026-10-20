{% include-markdown "it/dbzero/maintenance/manual/proc_sync_storico_set_storicizza_job.md" %}
# ⚙️ Procedura `proc_sync_storico_set_storicizza_job`

```sql
CREATE PROCEDURE proc_sync_storico_set_storicizza_job()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE PROCEDURE maintenance.proc_sync_storico_set_storicizza_job()
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'topology', 'pg_temp'
AS $procedure$
  BEGIN
    PERFORM maintenance.fn_run_and_log(
      p_jobname  := 'sync_storico_set_storicizza',
      p_stepname := 'run_sync_storico_set_storicizza',
      p_sql      := 'call maintenance.proc_sync_storico_set_storicizza();',
      p_lock_key := hashtext('proc_sync_storico_set_storicizza')  -- evita overlap
    );
  END;
  
$procedure$

COMMENT ON PROCEDURE maintenance.proc_sync_storico_set_storicizza_job()
IS 'Job wrapper per chiamare proc_sync_storico_set_storicizza con logging e lock.';
```

</div>

---
{% include-markdown "signature-core.md" %}
