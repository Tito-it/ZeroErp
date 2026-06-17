# ⚙️ Funzione `fn_job_run_end`

```sql
CREATE FUNCTION fn_job_run_end(p_id bigint, p_ok boolean, p_message text, p_rows_affected bigint, p_error_code text, p_error_detail text, p_meta jsonb, p_lock_key text)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_job_run_end(p_id bigint, p_ok boolean, p_message text DEFAULT NULL::text, p_rows_affected bigint DEFAULT NULL::bigint, p_error_code text DEFAULT NULL::text, p_error_detail text DEFAULT NULL::text, p_meta jsonb DEFAULT NULL::jsonb, p_lock_key text DEFAULT NULL::text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'pg_temp'
AS $function$
DECLARE
  c_lock_class constant int := hashtext('zeroerp:job_run_log');
  v_already_ended boolean;
BEGIN
  SELECT (ended_at IS NOT NULL) INTO v_already_ended
  FROM maintenance.job_run_log WHERE id = p_id;

  UPDATE maintenance.job_run_log
     SET ended_at      = clock_timestamp(),
         ok            = p_ok,
         message       = COALESCE(p_message, message),
         rows_affected = COALESCE(p_rows_affected, rows_affected),
         error_code    = p_error_code,
         error_detail  = p_error_detail,
         meta          = COALESCE(p_meta, meta)
   WHERE id = p_id;

  -- Sblocca SOLO se un lock e' realmente posseduto da questo flusso:
  -- end-dopo-skip (riga gia' chiusa) non possiede il lock -> niente unlock/warning.
  IF p_lock_key IS NOT NULL AND NOT COALESCE(v_already_ended, TRUE) THEN
    PERFORM pg_advisory_unlock(c_lock_class, hashtext(p_lock_key));
  END IF;
END;
$function$
```

---
{% include-markdown "signature-core.md" %}
