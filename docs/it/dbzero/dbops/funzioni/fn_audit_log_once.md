{% include-markdown "it/dbzero/dbops/manual/fn_audit_log_once.md" %}
# ⚙️ Funzione `fn_audit_log_once`

```sql
CREATE FUNCTION fn_audit_log_once(p_function_name text, p_status text, p_params jsonb, p_message text, p_exec_mode text, p_parts text[], p_rule_type text, p_dry_run boolean, p_sqlstate text, p_error_context text, p_rows_affected integer, p_result jsonb, p_host text, p_app_version text, p_duration_ms integer)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_audit_log_once(p_function_name text, p_status text, p_params jsonb DEFAULT '{}'::jsonb, p_message text DEFAULT NULL::text, p_exec_mode text DEFAULT NULL::text, p_parts text[] DEFAULT NULL::text[], p_rule_type text DEFAULT NULL::text, p_dry_run boolean DEFAULT NULL::boolean, p_sqlstate text DEFAULT NULL::text, p_error_context text DEFAULT NULL::text, p_rows_affected integer DEFAULT NULL::integer, p_result jsonb DEFAULT NULL::jsonb, p_host text DEFAULT NULL::text, p_app_version text DEFAULT NULL::text, p_duration_ms integer DEFAULT NULL::integer)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
-- Scopo: la porta unica di scrittura di dbops.audit_log. Una riga
--   intera, una volta, nella transazione del chiamante: se la
--   transazione si annulla, si annulla anche la riga.
DECLARE
    v_id dbops.audit_log.id%TYPE;
BEGIN
    INSERT INTO dbops.audit_log(
        function_name, status, params, message, exec_mode, parts,
        rule_type, dry_run, sqlstate, error_context, rows_affected,
        result, host, app_version, duration_ms)
    VALUES (
        p_function_name, p_status, p_params, p_message, p_exec_mode, p_parts,
        p_rule_type, p_dry_run, p_sqlstate, p_error_context, p_rows_affected,
        p_result, p_host, p_app_version, p_duration_ms)
    RETURNING id INTO v_id;

    RETURN v_id;
END;
$function$

COMMENT ON FUNCTION dbops.fn_audit_log_once(p_function_name text, p_status text, p_params jsonb, p_message text, p_exec_mode text, p_parts text[], p_rule_type text, p_dry_run boolean, p_sqlstate text, p_error_context text, p_rows_affected integer, p_result jsonb, p_host text, p_app_version text, p_duration_ms integer)
IS 'La porta unica di scrittura del registro delle automazioni (dbops.audit_log): scrive una riga intera, una volta, e ne restituisce l''id. La riga nasce nella transazione del chiamante e si annulla con lei: un esito che deve sopravvivere a un errore non sta qui ma in dbops.error_log. p_duration_ms e'' la durata del lavoro in millisecondi, misurata da chi chiama; la durata ha una sede sola, la colonna duration_ms. Tutti i parametri tranne nome e stato sono facoltativi.';
```

</div>

---
{% include-markdown "signature-core.md" %}
