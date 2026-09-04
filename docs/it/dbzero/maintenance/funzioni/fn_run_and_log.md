{% include-markdown "it/dbzero/maintenance/manual/fn_run_and_log.md" %}
# ⚙️ Funzione `fn_run_and_log`

```sql
CREATE FUNCTION fn_run_and_log(p_jobname text, p_stepname text, p_sql text, p_lock_key bigint, p_processo_codice text, p_auth_user_id integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION maintenance.fn_run_and_log(p_jobname text, p_stepname text, p_sql text, p_lock_key bigint DEFAULT NULL::bigint, p_processo_codice text DEFAULT NULL::text, p_auth_user_id integer DEFAULT NULL::integer)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
  DECLARE
    v_id         maintenance.job_run_log.id%TYPE;
    v_rows       maintenance.job_run_log.rows_affected%TYPE := 0;
    v_locked     boolean := false;
    -- Attore risolto: passato dal chiamante, oppure derivato dal
    -- jobname (vedi intestazione: qui la derivazione e' completa).
    v_processo   maintenance.job_run_log.processo_codice%TYPE;

    -- diagnosi errori
    v_errmsg     maintenance.job_run_log.message%TYPE;
    v_errdetail  text;
    v_errhint    text;
    v_errcontext text;
    v_sqlstate   maintenance.job_run_log.error_code%TYPE;
  BEGIN
    -- Sotto-select scalare, non SELECT INTO: senza righe ritorna
    -- NULL senza azzerare nulla di gia' calcolato.
    v_processo := COALESCE(
        p_processo_codice,
        (SELECT pr.codice
           FROM dbops.processi pr
          WHERE pr.codice = p_jobname)
    );

    -- lock opzionale per evitare overlap
    -- ⚠️ Forma a UN argomento, invariata di proposito: e' uno
    --   spazio di lock distinto da quello di
    --   script.fn_job_run_start, e i due canali restano
    --   indipendenti (vedi intestazione).
    IF p_lock_key IS NOT NULL THEN
      v_locked := pg_try_advisory_lock(p_lock_key);
      IF NOT v_locked THEN
        -- L'attore va scritto anche sulla riga di skip: senza,
        -- ogni sovrapposizione lascerebbe un run senza attore.
        INSERT INTO maintenance.job_run_log
            (jobname, stepname, ok, message, processo_codice, auth_user_id)
        VALUES (p_jobname, p_stepname, TRUE, 'skip: another run in progress',
                v_processo, p_auth_user_id);
        RETURN;
      END IF;
    END IF;

    INSERT INTO maintenance.job_run_log
        (jobname, stepname, processo_codice, auth_user_id)
    VALUES (p_jobname, p_stepname, v_processo, p_auth_user_id)
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

      RAISE;  -- lascio propagare
    END;
  END;
$function$

COMMENT ON FUNCTION maintenance.fn_run_and_log(p_jobname text, p_stepname text, p_sql text, p_lock_key bigint, p_processo_codice text, p_auth_user_id integer)
IS 'Esegue p_sql registrandone l''esito su maintenance.job_run_log, con advisory lock anti-overlap opzionale. Canale PGAGENT (origine default). Rev 2026-09-04: prende p_processo_codice (l''ATTORE, hard FK verso dbops.processi) e p_auth_user_id, scritti su entrambi i rami — anche sulla riga di «skip». ⭐ Se il codice non e'' passato lo DERIVA dal jobname: per i job pgAgent il jobname E'' il processo (i wrapper proc_*_job passano gia'' esattamente il codice seedato), quindi i 12 job diventano conformi senza toccare 85_pgagent. Un jobname che non corrisponde a nessun processo resta NULL e finisce in dbops.vw_run_senza_attore: niente e'' mascherato. ⛔ L''advisory lock resta alla forma a UN argomento: e'' uno spazio di lock distinto da quello di script.fn_job_run_start, e i due canali restano indipendenti. Brief: brief-db-processi-automatici-identita-e-perimetro §3.2.';
```

---
{% include-markdown "signature-core.md" %}
