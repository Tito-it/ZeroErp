{% include-markdown "it/dbzero/script/manual/fn_job_run_end.md" %}
# ⚙️ Funzione `fn_job_run_end`

```sql
CREATE FUNCTION fn_job_run_end(p_id bigint, p_ok boolean, p_message text, p_rows_affected bigint, p_error_code text, p_error_detail text, p_meta jsonb, p_lock_key text, p_sqlstate text)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_job_run_end(p_id bigint, p_ok boolean, p_message text DEFAULT NULL::text, p_rows_affected bigint DEFAULT NULL::bigint, p_error_code text DEFAULT NULL::text, p_error_detail text DEFAULT NULL::text, p_meta jsonb DEFAULT NULL::jsonb, p_lock_key text DEFAULT NULL::text, p_sqlstate text DEFAULT NULL::text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'pg_temp'
AS $function$
DECLARE
  c_lock_class constant int := hashtext('zeroerp:job_run_log');
  -- `boolean` esplicito: e' derivato (ended_at IS NOT NULL), non
  -- il riflesso di una colonna.
  v_already_ended boolean;
  v_saltata       maintenance.job_run_log.saltata%TYPE;
  v_jobname       maintenance.job_run_log.jobname%TYPE;
BEGIN
  SELECT (l.ended_at IS NOT NULL), l.saltata, l.jobname
    INTO v_already_ended, v_saltata, v_jobname
    FROM maintenance.job_run_log l
   WHERE l.id = p_id;

  -- ⛔ Rev 2026-10-10: una corsa SALTATA non si chiude. Non ha
  --   fatto lavoro e nasce gia' chiusa, senza esito (CHECK
  --   chk_job_run_log_saltata): chiuderla le scriverebbe un esito
  --   e la farebbe passare per una corsa vera. Chi riceve
  --   acquired = false da fn_job_run_start salta il lavoro e non
  --   chiama questa funzione. brief-db-corsa-saltata-non-e-una-corsa.
  -- ⚠️ TECNICO: lo produce solo un chiamante rotto. Niente
  --   `campo` ne' bersaglio: su un 500 non c'e' gesto da offrire.
  IF v_saltata THEN
    PERFORM script.fn_log_and_raise_error(
        'database',
        'script.fn_job_run_end',
        'E_JOB_RUN_SALTATA_NON_CHIUDIBILE',
        jsonb_build_object('job_run_id', p_id, 'jobname', v_jobname),
        NULL::uuid,
        p_id::text,
        v_jobname);
  END IF;

  UPDATE maintenance.job_run_log
     SET ended_at      = clock_timestamp(),
         ok            = p_ok,
         message       = COALESCE(p_message, message),
         rows_affected = COALESCE(p_rows_affected, rows_affected),
         error_code    = p_error_code,
         error_detail  = p_error_detail,
         -- ⭐ Rev 2026-10-16: lo SQLSTATE, quando l'errore e' passato dal
         --   database; error_code resta il codice del backend (D5).
         --   brief-db-presidio-job-run-a-chi-tocca §4.2.
         sqlstate      = p_sqlstate,
         meta          = COALESCE(p_meta, meta)
   WHERE id = p_id;

  -- Sblocca SOLO se un lock e' realmente posseduto da questo flusso:
  -- una riga gia' chiusa (doppia chiusura, o una skip scritta prima
  -- del 2026-10-10 con saltata = false) non possiede il lock ->
  -- niente unlock/warning.
  IF p_lock_key IS NOT NULL AND NOT COALESCE(v_already_ended, TRUE) THEN
    PERFORM pg_advisory_unlock(c_lock_class, hashtext(p_lock_key));
  END IF;
END;
$function$

COMMENT ON FUNCTION script.fn_job_run_end(p_id bigint, p_ok boolean, p_message text, p_rows_affected bigint, p_error_code text, p_error_detail text, p_meta jsonb, p_lock_key text, p_sqlstate text)
IS 'Chiude una corsa aperta da script.fn_job_run_start: esito, messaggio, righe toccate, errore e meta; rilascia l''advisory lock della corsia solo se questo flusso lo possiede (la riga era ancora aperta). SECURITY DEFINER con search_path fisso: e'' la porta di scrittura del giornale per chi non ha UPDATE su maintenance.job_run_log. ⛔ Rev 2026-10-10: rifiuta una corsa SALTATA (E_JOB_RUN_SALTATA_NON_CHIUDIBILE, TECNICO). Non ha fatto lavoro e nasce chiusa senza esito: chiuderla le scriverebbe un esito e la farebbe passare per una corsa vera. Chi riceve acquired = false salta il lavoro e non chiama questa funzione. Brief: brief-db-corsa-saltata-non-e-una-corsa §8. ⭐ Rev 2026-10-16: parametro p_sqlstate in coda (DEFAULT NULL), scritto in job_run_log.sqlstate: lo SQLSTATE di un errore passato dal database, che il backend prima perdeva. error_code resta il codice del backend. Brief: brief-db-presidio-job-run-a-chi-tocca §4.2.';
```

</div>

---
{% include-markdown "signature-core.md" %}
