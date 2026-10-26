{% include-markdown "it/dbzero/dbops/manual/fn_audit_begin.md" %}
# ⚙️ Funzione `fn_audit_begin`

```sql
CREATE FUNCTION fn_audit_begin(p_function_name text, p_params jsonb, p_exec_mode text, p_parts text[], p_rule_type text, p_dry_run boolean, p_host text, p_app_version text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_audit_begin(p_function_name text, p_params jsonb DEFAULT '{}'::jsonb, p_exec_mode text DEFAULT NULL::text, p_parts text[] DEFAULT NULL::text[], p_rule_type text DEFAULT NULL::text, p_dry_run boolean DEFAULT NULL::boolean, p_host text DEFAULT NULL::text, p_app_version text DEFAULT NULL::text)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_id        bigint;
  v_use_dbk   boolean := COALESCE(current_setting('myapp.log_with_dblink', true)='on', false);
  v_has_dbk   boolean := EXISTS (SELECT 1 FROM pg_extension WHERE extname='dblink');
  v_can_use   boolean := false;
  v_sql       text;
BEGIN
  -- BEGIN: inserisce START (usa dblink/logconn se attivo), ritorna id
  IF v_use_dbk AND v_has_dbk THEN
    -- prova ad aprire/riusare 'logconn' (tua funzione)
    BEGIN
      EXECUTE 'SELECT script.fn_ensure_logconn()';
    EXCEPTION WHEN undefined_function THEN
      v_use_dbk := false;  -- funzione non presente → fallback
    WHEN others THEN
      v_use_dbk := false;  -- qualsiasi errore → fallback
    END;
  END IF;

  IF v_use_dbk AND v_has_dbk THEN
    v_can_use := 'logconn' = ANY (COALESCE(public.dblink_get_connections(), ARRAY[]::text[]));
  END IF;

  IF v_can_use THEN
    -- out-of-tx
    v_sql := format(
      'INSERT INTO dbops.audit_log(function_name, params, status, exec_mode, parts, rule_type, dry_run, host, app_version)
       VALUES (%L, %L::jsonb, %L, %L, %L::text[], %L, %s, %L, %L)
       RETURNING id',
       p_function_name,
       COALESCE((p_params)::text,'null'),
       'START',
       p_exec_mode,
       COALESCE((p_parts)::text,'null'),
       p_rule_type,
       CASE WHEN p_dry_run IS NULL THEN 'NULL' ELSE (p_dry_run::text) END,
       p_host,
       p_app_version
    );
    EXECUTE format($q$
      SELECT id FROM dblink('logconn', %L) AS t(id bigint)
    $q$, v_sql) INTO v_id;
  ELSE
    -- locale (in transazione)
    INSERT INTO dbops.audit_log(function_name, params, status, exec_mode, parts, rule_type, dry_run, host, app_version)
    VALUES (p_function_name, p_params, 'START', p_exec_mode, p_parts, p_rule_type, p_dry_run, p_host, p_app_version)
    RETURNING id INTO v_id;
  END IF;

  RETURN v_id;
END;
$function$
```

</div>

---
{% include-markdown "signature-core.md" %}
