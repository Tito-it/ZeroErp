{% include-markdown "it/dbzero/dbops/manual/fn_run_automations_cleanup.md" %}
# ⚙️ Funzione `fn_run_automations_cleanup`

```sql
CREATE FUNCTION fn_run_automations_cleanup(p_exec_mode text, p_schemas text[], p_dry_run boolean)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION dbops.fn_run_automations_cleanup(p_exec_mode text, p_schemas text[], p_dry_run boolean)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_schemas text[];
  rtab record;
  rrule record;
  v_is_excluded boolean;
  v_cleanup_col text;
  v_base_col text;
  v_ttl_days integer;
  v_apply_on_update boolean;
  v_batch_limit integer;
  v_rows integer;
  v_params jsonb;
  v_rule_type text;
BEGIN

/*
  Scopo
  -----
  Orchestratore per il framework di cleanup basato su cleanup_at.
  Applica due tipi di regola su tabelle in scope:
  - CLEANUP_AT   : calcola cleanup_at con TTL fisso
  - CLEANUP_PURGE: elimina record scaduti in batch

  Logica
  ------
  1) risolve lo scope (dbops.fn_resolve_scope)
  2) itera le tabelle fisiche nello scope (dbops.fn_table_in_scope)
  3) salta tabelle in dbops.automation_cleanup_exclusions (enabled=true)
  4) applica regole compatibili con exec_mode e target schema/table
  5) logga sempre su dbops.audit_log tramite fn_audit_log_once
*/

  v_schemas := dbops.fn_resolve_scope(p_schemas);

  FOR rtab IN
    SELECT n.nspname AS schema_name,
           c.relname AS table_name
      FROM pg_class c
      JOIN pg_namespace n ON n.oid=c.relnamespace
     WHERE c.relkind='r'
       AND n.nspname = ANY(v_schemas)
       AND dbops.fn_table_in_scope(n.nspname, c.relname)
  LOOP
    SELECT EXISTS(
      SELECT 1
        FROM dbops.automation_cleanup_exclusions e
       WHERE e.enabled
         AND e.schema_name = rtab.schema_name
         AND e.table_name  = rtab.table_name
    ) INTO v_is_excluded;

    IF v_is_excluded THEN
      PERFORM dbops.fn_audit_log_once(
        p_function_name => 'dbops.fn_run_automations_cleanup',
        p_status        => 'SKIP_EXCLUDED',
        p_rule_type     => 'CLEANUP',
        p_exec_mode     => p_exec_mode,
        p_parts         => ARRAY['CLEANUP'],
        p_dry_run       => p_dry_run,
        p_params        => jsonb_build_object('table', rtab.schema_name||'.'||rtab.table_name),
        p_message       => 'Tabella esclusa da automation_cleanup_exclusions'
      );
      CONTINUE;
    END IF;

    FOR rrule IN
      SELECT *
        FROM dbops.automation_rules_tbl r
       WHERE r.enabled
         AND upper(btrim(r.rule_type)) IN ('CLEANUP_AT','CLEANUP_PURGE')
         AND (upper(btrim(r.exec_mode)) = 'AUTO' OR r.exec_mode = p_exec_mode)
         AND dbops.fn_schema_match(r.target_schema, rtab.schema_name)
         AND (UPPER(r.target_table) = '*ALL' OR rtab.table_name ILIKE r.target_table)
       ORDER BY r.priority, r.id
    LOOP
      v_rule_type := upper(btrim(rrule.rule_type));
      v_params := COALESCE(rrule.params, '{}'::jsonb);
      v_cleanup_col := COALESCE(NULLIF(btrim(v_params->>'cleanup_column'), ''), 'cleanup_at');

      IF NOT dbops.fn_col_exists(rtab.schema_name, rtab.table_name, v_cleanup_col) THEN
        PERFORM dbops.fn_audit_log_once(
          p_function_name => 'dbops.fn_run_automations_cleanup',
          p_status        => 'SKIP_NO_COLUMN',
          p_rule_type     => v_rule_type,
          p_exec_mode     => p_exec_mode,
          p_parts         => ARRAY[v_rule_type],
          p_dry_run       => p_dry_run,
          p_params        => jsonb_build_object(
                              'table', rtab.schema_name||'.'||rtab.table_name,
                              'cleanup_column', v_cleanup_col
                            ),
          p_message       => 'Colonna cleanup non presente'
        );
        CONTINUE;
      END IF;

      IF v_rule_type = 'CLEANUP_AT' THEN
        v_ttl_days := (v_params->>'ttl_days')::integer;
        v_apply_on_update := COALESCE((v_params->>'apply_on_update')::boolean, false);
        v_base_col := NULLIF(btrim(v_params->>'base_ts_column'), '');

        IF v_base_col IS NULL THEN
          IF dbops.fn_col_exists(rtab.schema_name, rtab.table_name, 'data_insert') THEN
            v_base_col := 'data_insert';
          ELSIF dbops.fn_col_exists(rtab.schema_name, rtab.table_name, 'executed_at') THEN
            v_base_col := 'executed_at';
          ELSIF dbops.fn_col_exists(rtab.schema_name, rtab.table_name, 'occurred_at') THEN
            v_base_col := 'occurred_at';
          ELSIF dbops.fn_col_exists(rtab.schema_name, rtab.table_name, 'created_at') THEN
            v_base_col := 'created_at';
          END IF;
        END IF;

        IF v_ttl_days IS NULL THEN
          PERFORM dbops.fn_audit_log_once(
            p_function_name => 'dbops.fn_run_automations_cleanup',
            p_status        => 'SKIP_RULE',
            p_rule_type     => v_rule_type,
            p_exec_mode     => p_exec_mode,
            p_parts         => ARRAY[v_rule_type],
            p_dry_run       => p_dry_run,
            p_params        => jsonb_build_object(
                                'table', rtab.schema_name||'.'||rtab.table_name,
                                'cleanup_column', v_cleanup_col
                              ),
            p_message       => 'Parametro ttl_days mancante'
          );
          CONTINUE;
        END IF;

        IF v_base_col IS NULL OR NOT dbops.fn_col_exists(rtab.schema_name, rtab.table_name, v_base_col) THEN
          PERFORM dbops.fn_audit_log_once(
            p_function_name => 'dbops.fn_run_automations_cleanup',
            p_status        => 'SKIP_RULE',
            p_rule_type     => v_rule_type,
            p_exec_mode     => p_exec_mode,
            p_parts         => ARRAY[v_rule_type],
            p_dry_run       => p_dry_run,
            p_params        => jsonb_build_object(
                                'table', rtab.schema_name||'.'||rtab.table_name,
                                'cleanup_column', v_cleanup_col,
                                'base_ts_column', v_base_col
                              ),
            p_message       => 'Colonna base_ts non presente'
          );
          CONTINUE;
        END IF;

        v_rows := dbops.fn_apply_cleanup_at(
          rtab.schema_name,
          rtab.table_name,
          v_cleanup_col,
          v_base_col,
          v_ttl_days,
          v_apply_on_update,
          p_dry_run
        );

        PERFORM dbops.fn_audit_log_once(
          p_function_name => 'dbops.fn_run_automations_cleanup',
          p_status        => CASE WHEN p_dry_run THEN 'DRYRUN' ELSE 'OK' END,
          p_rule_type     => v_rule_type,
          p_exec_mode     => p_exec_mode,
          p_parts         => ARRAY[v_rule_type],
          p_dry_run       => p_dry_run,
          p_rows_affected => v_rows,
          p_params        => jsonb_build_object(
                              'table', rtab.schema_name||'.'||rtab.table_name,
                              'cleanup_column', v_cleanup_col,
                              'base_ts_column', v_base_col,
                              'ttl_days', v_ttl_days,
                              'apply_on_update', v_apply_on_update
                            ),
          p_message       => 'cleanup_at calcolato'
        );

      ELSIF v_rule_type = 'CLEANUP_PURGE' THEN
        v_batch_limit := COALESCE((v_params->>'batch_limit')::integer, 5000);

        v_rows := dbops.fn_purge_cleanup_expired(
          rtab.schema_name,
          rtab.table_name,
          v_cleanup_col,
          v_batch_limit,
          p_dry_run
        );

        PERFORM dbops.fn_audit_log_once(
          p_function_name => 'dbops.fn_run_automations_cleanup',
          p_status        => CASE WHEN p_dry_run THEN 'DRYRUN' ELSE 'OK' END,
          p_rule_type     => v_rule_type,
          p_exec_mode     => p_exec_mode,
          p_parts         => ARRAY[v_rule_type],
          p_dry_run       => p_dry_run,
          p_rows_affected => v_rows,
          p_params        => jsonb_build_object(
                              'table', rtab.schema_name||'.'||rtab.table_name,
                              'cleanup_column', v_cleanup_col,
                              'batch_limit', v_batch_limit
                            ),
          p_message       => 'cleanup eseguito'
        );
      END IF;
    END LOOP;
  END LOOP;
END;
$function$
```

---
{% include-markdown "signature-core.md" %}
