# ⚙️ Funzione `fn_job_run_start`

```sql
CREATE FUNCTION fn_job_run_start(p_jobname text, p_origine text, p_stepname text, p_lock_key text, p_agent_host text)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_job_run_start(p_jobname text, p_origine text DEFAULT 'CRON'::text, p_stepname text DEFAULT NULL::text, p_lock_key text DEFAULT NULL::text, p_agent_host text DEFAULT NULL::text)
 RETURNS TABLE(id bigint, run_uuid uuid, acquired boolean)
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'pg_temp'
AS $function$
DECLARE
  c_lock_class constant int := hashtext('zeroerp:job_run_log');  -- namespace lock headless
  v_acquired boolean := true;
  v_id   maintenance.job_run_log.id%TYPE;
  v_uuid maintenance.job_run_log.run_uuid%TYPE;
BEGIN
  -- origine e' validata dal CHECK colonna (chk_job_run_log_origine) all'INSERT.
  IF p_lock_key IS NOT NULL THEN
    v_acquired := pg_try_advisory_lock(c_lock_class, hashtext(p_lock_key));
    IF NOT v_acquired THEN
      INSERT INTO maintenance.job_run_log
          (jobname, stepname, origine, ok, ended_at, message, agent_host)
      VALUES (p_jobname, p_stepname, p_origine, TRUE, clock_timestamp(),
              'skip: another run in progress',
              COALESCE(p_agent_host, inet_client_addr()::text))
      RETURNING job_run_log.id, job_run_log.run_uuid INTO v_id, v_uuid;
      RETURN QUERY SELECT v_id, v_uuid, FALSE;
      RETURN;
    END IF;
  END IF;

  INSERT INTO maintenance.job_run_log
      (jobname, stepname, origine, agent_host)
  VALUES (p_jobname, p_stepname, p_origine,
          COALESCE(p_agent_host, inet_client_addr()::text))
  RETURNING job_run_log.id, job_run_log.run_uuid INTO v_id, v_uuid;
  RETURN QUERY SELECT v_id, v_uuid, TRUE;
END;
$function$
```

---
{% include-markdown "signature-core.md" %}
