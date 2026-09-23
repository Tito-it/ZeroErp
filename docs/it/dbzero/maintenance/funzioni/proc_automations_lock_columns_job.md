{% include-markdown "it/dbzero/maintenance/manual/proc_automations_lock_columns_job.md" %}
# ⚙️ Procedura `proc_automations_lock_columns_job`

```sql
CREATE PROCEDURE proc_automations_lock_columns_job()
```

**Definizione completa:**

```sql
CREATE OR REPLACE PROCEDURE maintenance.proc_automations_lock_columns_job()
 LANGUAGE plpgsql
AS $procedure$
  BEGIN
    -- rev 20260923-46: anche il guard delle date di validita'
    --   (automazione DATE_VALIDITA), stessa famiglia del lock.
    PERFORM maintenance.fn_run_and_log(
      p_jobname  := 'automations_lock_columns',
      p_stepname := 'run_automations_lock_columns',
      p_sql      := 'SELECT dbops.fn_run_automations_lock_columns(''SCHEDULED'', NULL, false); ' ||
                   'SELECT dbops.fn_run_automations_drop_lock_trg(''SCHEDULED'', NULL, false); ' ||
                   'SELECT dbops.fn_run_automations_date_validita(''SCHEDULED'', NULL, false);',
      p_lock_key := hashtext('automations_lock_columns')
    );
  END;
$procedure$

COMMENT ON PROCEDURE maintenance.proc_automations_lock_columns_job()
IS 'Job wrapper per chiamare fn_run_automations_lock_columns e cleanup trigger LOCK_COLUMNS obsoleti. Rev 20260923-46: monta anche il guard delle date di validita'' (dbops.fn_run_automations_date_validita, automazione DATE_VALIDITA), stessa famiglia del lock.';
```

---
{% include-markdown "signature-core.md" %}
