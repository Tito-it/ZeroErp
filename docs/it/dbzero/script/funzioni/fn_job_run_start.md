{% include-markdown "it/dbzero/script/manual/fn_job_run_start.md" %}
# ⚙️ Funzione `fn_job_run_start`

```sql
CREATE FUNCTION fn_job_run_start(p_jobname text, p_origine character varying, p_stepname text, p_lock_key text, p_agent_host text, p_processo_codice text, p_auth_user_id integer)
```

**Definizione completa:**

<div data-search-exclude markdown>

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
      -- ⭐ Rev 2026-10-10: la riga si dichiara SALTATA, chiusa e
      --   senza esito (ok NULL). Con ok = TRUE ogni lettore la
      --   contava come una corsa riuscita: brief-db-corsa-saltata-
      --   non-e-una-corsa. Il message resta, ma e' solo testo.
      INSERT INTO maintenance.job_run_log
          (jobname, stepname, origine, saltata, ended_at, message, agent_host,
           processo_codice, auth_user_id, ruolo_sessione)
      VALUES (p_jobname, p_stepname, p_origine, TRUE, clock_timestamp(),
              'skip: another run in progress',
              COALESCE(p_agent_host, inet_client_addr()::text),
              p_processo_codice, p_auth_user_id, session_user)
      RETURNING job_run_log.id, job_run_log.run_uuid INTO v_id, v_uuid;
      RETURN QUERY SELECT v_id, v_uuid, FALSE;
      RETURN;
    END IF;
  END IF;

  INSERT INTO maintenance.job_run_log
      (jobname, stepname, origine, agent_host,
       processo_codice, auth_user_id, ruolo_sessione)
  VALUES (p_jobname, p_stepname, p_origine,
          COALESCE(p_agent_host, inet_client_addr()::text),
          p_processo_codice, p_auth_user_id,
          -- ⭐ Rev 2026-10-15: chi si e' collegato (D-5).
          session_user)
  RETURNING job_run_log.id, job_run_log.run_uuid INTO v_id, v_uuid;
  RETURN QUERY SELECT v_id, v_uuid, TRUE;
END;
$function$

COMMENT ON FUNCTION script.fn_job_run_start(p_jobname text, p_origine character varying, p_stepname text, p_lock_key text, p_agent_host text, p_processo_codice text, p_auth_user_id integer)
IS 'Apre una riga su maintenance.job_run_log per un processo HEADLESS (management command / cron / systemd), con advisory lock anti-overlap opzionale. Rev 2026-09-04: prende p_processo_codice (l''ATTORE, hard FK verso dbops.processi) e p_auth_user_id (utente tecnico dei soli processi DOMINIO), e li scrive su ENTRAMBI i rami — anche sulla riga di «skip», altrimenti ogni sovrapposizione lascerebbe un run senza attore. Brief: brief-db-processi-automatici-identita-e-perimetro §3.2. ⭐ Rev 2026-10-10: col lock occupato la riga nasce SALTATA (saltata = TRUE), chiusa e con ok NULL, e la funzione torna acquired = false. Prima nasceva con ok = TRUE, e ogni lettore la contava come una corsa riuscita: una sveglia calendariale saltava il periodo, una corsa appesa spariva dal presidio. Il chiamante che riceve acquired = false salta il lavoro e NON chiude la corsa (script.fn_job_run_end la rifiuta). Brief: brief-db-corsa-saltata-non-e-una-corsa §8. ⭐ Rev 2026-10-15: entrambe le righe scrivono ruolo_sessione = session_user (chi si e'' collegato; session_user perche'' la funzione e'' DEFINER). Brief: brief-db-ruoli-di-sistema D-5.';
```

</div>

---
{% include-markdown "signature-core.md" %}
