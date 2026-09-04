{% include-markdown "it/dbzero/script/manual/fn_job_run_start.md" %}
# ⚙️ Funzione `fn_job_run_start`

```sql
CREATE FUNCTION fn_job_run_start(p_jobname text, p_origine character varying, p_stepname text, p_lock_key text, p_agent_host text, p_processo_codice text, p_auth_user_id integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_job_run_start(p_jobname text, p_origine character varying DEFAULT 'CRON'::character varying, p_stepname text DEFAULT NULL::text, p_lock_key text DEFAULT NULL::text, p_agent_host text DEFAULT NULL::text, p_processo_codice text DEFAULT NULL::text, p_auth_user_id integer DEFAULT NULL::integer)
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
  -- p_processo_codice e' validato dalla FK fk_job_run_log_processi: un
  -- codice non registrato in dbops.processi fa fallire l'INSERT (fail-loud
  -- voluto). ⚠️ NULL resta ammesso finche' dura la transizione dei chiamanti.
  IF p_lock_key IS NOT NULL THEN
    v_acquired := pg_try_advisory_lock(c_lock_class, hashtext(p_lock_key));
    IF NOT v_acquired THEN
      -- ⚠️ L'attore va scritto ANCHE sulla riga di skip: senza, ogni
      --   sovrapposizione lascerebbe un run senza attore e terrebbe
      --   accesa la vista di presidio per un caso che non e' un difetto.
      INSERT INTO maintenance.job_run_log
          (jobname, stepname, origine, ok, ended_at, message, agent_host,
           processo_codice, auth_user_id)
      VALUES (p_jobname, p_stepname, p_origine, TRUE, clock_timestamp(),
              'skip: another run in progress',
              COALESCE(p_agent_host, inet_client_addr()::text),
              p_processo_codice, p_auth_user_id)
      RETURNING job_run_log.id, job_run_log.run_uuid INTO v_id, v_uuid;
      RETURN QUERY SELECT v_id, v_uuid, FALSE;
      RETURN;
    END IF;
  END IF;

  INSERT INTO maintenance.job_run_log
      (jobname, stepname, origine, agent_host,
       processo_codice, auth_user_id)
  VALUES (p_jobname, p_stepname, p_origine,
          COALESCE(p_agent_host, inet_client_addr()::text),
          p_processo_codice, p_auth_user_id)
  RETURNING job_run_log.id, job_run_log.run_uuid INTO v_id, v_uuid;
  RETURN QUERY SELECT v_id, v_uuid, TRUE;
END;
$function$

COMMENT ON FUNCTION script.fn_job_run_start(p_jobname text, p_origine character varying, p_stepname text, p_lock_key text, p_agent_host text, p_processo_codice text, p_auth_user_id integer)
IS 'Apre una riga su maintenance.job_run_log per un processo HEADLESS (management command / cron / systemd), con advisory lock anti-overlap opzionale. Rev 2026-09-04: prende p_processo_codice (l''ATTORE, hard FK verso dbops.processi) e p_auth_user_id (utente tecnico dei soli processi DOMINIO), e li scrive su ENTRAMBI i rami — anche sulla riga di «skip», altrimenti ogni sovrapposizione lascerebbe un run senza attore. Brief: brief-db-processi-automatici-identita-e-perimetro §3.2.';
```

---
{% include-markdown "signature-core.md" %}
