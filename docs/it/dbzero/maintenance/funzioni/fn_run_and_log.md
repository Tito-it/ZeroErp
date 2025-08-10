{% include-markdown "it/dbzero/maintenance/manual/fn_run_and_log.md" %}
# ⚙️ Funzione `fn_run_and_log`

```sql
CREATE FUNCTION fn_run_and_log(p_jobname text, p_stepname text, p_sql text, p_lock_key bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION maintenance.fn_run_and_log(p_jobname text, p_stepname text, p_sql text, p_lock_key bigint DEFAULT NULL::bigint)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
  DECLARE
    v_id         bigint;
    v_rows       bigint := 0;
    v_locked     boolean := false;

    -- diagnosi errori
    v_errmsg     text;
    v_errdetail  text;
    v_errhint    text;
    v_errcontext text;
    v_sqlstate   text;
  BEGIN
    -- lock opzionale per evitare overlap
    IF p_lock_key IS NOT NULL THEN
      v_locked := pg_try_advisory_lock(p_lock_key);
      IF NOT v_locked THEN
        INSERT INTO maintenance.job_run_log(jobname, stepname, ok, message)
        VALUES (p_jobname, p_stepname, TRUE, 'skip: another run in progress');
        RETURN;
      END IF;
    END IF;

    INSERT INTO maintenance.job_run_log(jobname, stepname)
    VALUES (p_jobname, p_stepname)
    RETURNING id INTO v_id;

    BEGIN
      EXECUTE p_sql;
      GET DIAGNOSTICS v_rows = ROW_COUNT;

      UPDATE maintenance.job_run_log
        SET ended_at      = clock_timestamp(),
            ok            = TRUE,
            rows_affected = v_rows,
            message       = 'done'
      WHERE id = v_id;

      IF v_locked THEN
        PERFORM pg_advisory_unlock(p_lock_key);
      END IF;

    EXCEPTION WHEN OTHERS THEN
      -- cattura dettagli dal frame eccezione
      GET STACKED DIAGNOSTICS
        v_errmsg     = MESSAGE_TEXT,
        v_errdetail  = PG_EXCEPTION_DETAIL,
        v_errhint    = PG_EXCEPTION_HINT,
        v_errcontext = PG_EXCEPTION_CONTEXT,
        v_sqlstate   = RETURNED_SQLSTATE;

      UPDATE maintenance.job_run_log
        SET ended_at     = clock_timestamp(),
            ok           = FALSE,
            message      = v_errmsg,
            error_code   = v_sqlstate,
            error_detail = coalesce(v_errdetail,'') ||
                            CASE WHEN v_errhint IS NOT NULL THEN E'\nHINT: '||v_errhint ELSE '' END ||
                            CASE WHEN v_errcontext IS NOT NULL THEN E'\nCONTEXT: '||v_errcontext ELSE '' END
      WHERE id = v_id;

      IF v_locked THEN
        PERFORM pg_advisory_unlock(p_lock_key);
      END IF;

      RAISE;  -- lascio propagare (togli se vuoi "ingoiare")
    END;
  END;
  $function$
```
---
{% include-markdown "signature-core.md" %}
