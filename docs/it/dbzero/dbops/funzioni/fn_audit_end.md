{% include-markdown "it/dbzero/dbops/manual/fn_audit_end.md" %}
# ⚙️ Funzione `fn_audit_end`

```sql
CREATE FUNCTION fn_audit_end(p_id bigint, p_status text, p_message text, p_sqlstate text, p_error_context text, p_rows_affected integer, p_result jsonb)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_audit_end(p_id bigint, p_status text DEFAULT 'OK'::text, p_message text DEFAULT NULL::text, p_sqlstate text DEFAULT NULL::text, p_error_context text DEFAULT NULL::text, p_rows_affected integer DEFAULT NULL::integer, p_result jsonb DEFAULT NULL::jsonb)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_use_dbk   boolean := COALESCE(current_setting('myapp.log_with_dblink', true)='on', false);
  v_has_dbk   boolean := EXISTS (SELECT 1 FROM pg_extension WHERE extname='dblink');
  v_can_use   boolean := false;
  v_sql       text;
  v_dummy     text;
BEGIN
  -- END: aggiorna esito e durata (out-of-tx se possibile) 
  IF v_use_dbk AND v_has_dbk THEN
    BEGIN
      EXECUTE 'SELECT script.fn_ensure_logconn()';
    EXCEPTION WHEN others THEN
      v_use_dbk := false;
    END;
  END IF;

  IF v_use_dbk AND v_has_dbk THEN
    v_can_use := 'logconn' = ANY (COALESCE(public.dblink_get_connections(), ARRAY[]::text[]));
  END IF;

  IF v_can_use THEN
    v_sql := format(
      'UPDATE dbops.audit_log
         SET status=%L,
             message=%L,
             sqlstate=%L,
             error_context=%L,
             rows_affected=%s,
             result=%s,
             duration_ms = COALESCE(duration_ms, ROUND(EXTRACT(EPOCH FROM (clock_timestamp() - executed_at))*1000)::int)
       WHERE id=%s',
       p_status,
       p_message,
       p_sqlstate,
       p_error_context,
       COALESCE(p_rows_affected::text,'NULL'),
       CASE WHEN p_result IS NULL THEN 'NULL' ELSE format('%L::jsonb', (p_result)::text) END,
       p_id::text
    );
    SELECT dblink_exec('logconn', v_sql) INTO v_dummy;
  ELSE
    UPDATE dbops.audit_log
       SET status        = COALESCE(p_status, status),
           message       = p_message,
           sqlstate      = COALESCE(p_sqlstate, sqlstate),
           error_context = COALESCE(p_error_context, error_context),
           rows_affected = COALESCE(p_rows_affected, rows_affected),
           result        = COALESCE(p_result, result),
           duration_ms   = COALESCE(duration_ms, ROUND(EXTRACT(EPOCH FROM (clock_timestamp() - executed_at))*1000)::int)
     WHERE id=p_id;
  END IF;
END;
$function$
```

</div>

---
{% include-markdown "signature-core.md" %}
