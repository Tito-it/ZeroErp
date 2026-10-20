{% include-markdown "it/dbzero/dbops/manual/fn_audit_log_once.md" %}
# ⚙️ Funzione `fn_audit_log_once`

```sql
CREATE FUNCTION fn_audit_log_once(p_function_name text, p_status text, p_params jsonb, p_message text, p_exec_mode text, p_parts text[], p_rule_type text, p_dry_run boolean, p_sqlstate text, p_error_context text, p_rows_affected integer, p_result jsonb, p_host text, p_app_version text)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_audit_log_once(p_function_name text, p_status text, p_params jsonb DEFAULT '{}'::jsonb, p_message text DEFAULT NULL::text, p_exec_mode text DEFAULT NULL::text, p_parts text[] DEFAULT NULL::text[], p_rule_type text DEFAULT NULL::text, p_dry_run boolean DEFAULT NULL::boolean, p_sqlstate text DEFAULT NULL::text, p_error_context text DEFAULT NULL::text, p_rows_affected integer DEFAULT NULL::integer, p_result jsonb DEFAULT NULL::jsonb, p_host text DEFAULT NULL::text, p_app_version text DEFAULT NULL::text)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_id      bigint;
  v_use_dbk boolean := COALESCE(current_setting('myapp.log_with_dblink', true)='on', false);
  v_has_dbk boolean := EXISTS (SELECT 1 FROM pg_extension WHERE extname='dblink');
  v_can_use boolean := false;
  v_sql     text;
BEGIN
  -- ONE-SHOT: inserisce direttamente una riga completa (es. DRYRUN)

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
      'INSERT INTO dbops.audit_log(function_name, status, params, message, exec_mode, parts, rule_type, dry_run, sqlstate, error_context, rows_affected, result, host, app_version)
       VALUES (%L, %L, %L::jsonb, %L, %L, %L::text[], %L, %s, %L, %L, %s, %s, %L, %L)
       RETURNING id',
       p_function_name,
       p_status,
       COALESCE((p_params)::text,'null'),
       p_message,
       p_exec_mode,
       COALESCE((p_parts)::text,'null'),
       p_rule_type,
       CASE WHEN p_dry_run IS NULL THEN 'NULL' ELSE (p_dry_run::text) END,
       p_sqlstate,
       p_error_context,
       COALESCE(p_rows_affected::text,'NULL'),
       CASE WHEN p_result IS NULL THEN 'NULL' ELSE format('%L::jsonb', (p_result)::text) END,
       p_host,
       p_app_version
    );
    EXECUTE format($q$
      SELECT id FROM dblink('logconn', %L) AS t(id bigint)
    $q$, v_sql) INTO v_id;
  ELSE
    INSERT INTO dbops.audit_log(function_name, status, params, message, exec_mode, parts, rule_type, dry_run, sqlstate, error_context, rows_affected, result, host, app_version)
    VALUES (p_function_name, p_status, p_params, p_message, p_exec_mode, p_parts, p_rule_type, p_dry_run, p_sqlstate, p_error_context, p_rows_affected, p_result, p_host, p_app_version)
    RETURNING id INTO v_id;
  END IF;

  RETURN v_id;
END;
$function$
```

</div>

---
{% include-markdown "signature-core.md" %}
