{% include-markdown "it/dbzero/dbops/manual/fn_run_automations_cleanup.md" %}
# ⚙️ Funzione `fn_run_automations_cleanup`

```sql
CREATE FUNCTION fn_run_automations_cleanup(p_exec_mode text, p_schemas text[], p_dry_run boolean)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

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
  -- ⭐ Le tre variabili del rifiuto: una tabella che si oppone non ferma il
  --   giro, ma non sparisce nemmeno — il suo SQLSTATE e il suo messaggio
  --   finiscono nell'audit.
  v_sqlstate text;
  v_errmsg text;
  v_errctx text;
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
        p_status        => 'WARN',
        p_rule_type     => 'CLEANUP',
        p_exec_mode     => p_exec_mode,
        p_parts         => ARRAY['CLEANUP'],
        p_dry_run       => p_dry_run,
        p_params        => jsonb_build_object(
                            'table', rtab.schema_name||'.'||rtab.table_name,
                            'skip_reason', 'EXCLUDED'
                          ),
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
          p_status        => 'WARN',
          p_rule_type     => v_rule_type,
          p_exec_mode     => p_exec_mode,
          p_parts         => ARRAY[v_rule_type],
          p_dry_run       => p_dry_run,
          p_params        => jsonb_build_object(
                              'table', rtab.schema_name||'.'||rtab.table_name,
                              'cleanup_column', v_cleanup_col,
                              'skip_reason', 'NO_CLEANUP_COLUMN'
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
            p_status        => 'WARN',
            p_rule_type     => v_rule_type,
            p_exec_mode     => p_exec_mode,
            p_parts         => ARRAY[v_rule_type],
            p_dry_run       => p_dry_run,
            p_params        => jsonb_build_object(
                                'table', rtab.schema_name||'.'||rtab.table_name,
                                'cleanup_column', v_cleanup_col,
                                'skip_reason', 'MISSING_TTL_DAYS'
                              ),
            p_message       => 'Parametro ttl_days mancante'
          );
          CONTINUE;
        END IF;

        IF v_base_col IS NULL OR NOT dbops.fn_col_exists(rtab.schema_name, rtab.table_name, v_base_col) THEN
          PERFORM dbops.fn_audit_log_once(
            p_function_name => 'dbops.fn_run_automations_cleanup',
            p_status        => 'WARN',
            p_rule_type     => v_rule_type,
            p_exec_mode     => p_exec_mode,
            p_parts         => ARRAY[v_rule_type],
            p_dry_run       => p_dry_run,
            p_params        => jsonb_build_object(
                                'table', rtab.schema_name||'.'||rtab.table_name,
                                'cleanup_column', v_cleanup_col,
                                'base_ts_column', v_base_col,
                                'skip_reason', 'MISSING_BASE_TS_COLUMN'
                              ),
            p_message       => 'Colonna base_ts non presente'
          );
          CONTINUE;
        END IF;

        BEGIN
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
        EXCEPTION
          -- ⛔ Un annullamento resta un annullamento: se qualcuno ferma il job,
          --    il job si ferma. Non e' una tabella che rifiuta.
          WHEN query_canceled THEN
            RAISE;
          -- ⭐ Tutto il resto: la tabella viene SALTATA, non subita. Prima di
          --    questa rete un solo veto (un trigger append-only, un guard sul
          --    DELETE dei log) faceva morire l'INTERO giro: le tabelle che
          --    venivano dopo non venivano piu' pulite, e nessuno lo sapeva.
          --    ⚠️ Lo status e' ERROR e non WARN di proposito: i WARN di questa
          --    funzione sono salti DICHIARATI (esclusa, senza colonna, senza
          --    ttl). Questo non e' dichiarato — e' una tabella che si e'
          --    opposta, e va distinta a colpo d'occhio.
          WHEN OTHERS THEN
            GET STACKED DIAGNOSTICS
              v_sqlstate = RETURNED_SQLSTATE,
              v_errmsg   = MESSAGE_TEXT,
              v_errctx   = PG_EXCEPTION_CONTEXT;
            PERFORM dbops.fn_audit_log_once(
              p_function_name => 'dbops.fn_run_automations_cleanup',
              p_status        => 'ERROR',
              p_rule_type     => v_rule_type,
              p_exec_mode     => p_exec_mode,
              p_parts         => ARRAY[v_rule_type],
              p_dry_run       => p_dry_run,
              p_sqlstate      => v_sqlstate,
              p_error_context => v_errctx,
              p_params        => jsonb_build_object(
                                  'table', rtab.schema_name||'.'||rtab.table_name,
                                  'cleanup_column', v_cleanup_col,
                                  'skip_reason', 'BLOCKED_BY_TABLE'
                                ),
              p_message       => v_errmsg
            );
        END;

      ELSIF v_rule_type = 'CLEANUP_PURGE' THEN
        v_batch_limit := COALESCE((v_params->>'batch_limit')::integer, 5000);

        BEGIN
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
        EXCEPTION
          -- ⛔ Un annullamento resta un annullamento: se qualcuno ferma il job,
          --    il job si ferma. Non e' una tabella che rifiuta.
          WHEN query_canceled THEN
            RAISE;
          -- ⭐ Tutto il resto: la tabella viene SALTATA, non subita. Prima di
          --    questa rete un solo veto (un trigger append-only, un guard sul
          --    DELETE dei log) faceva morire l'INTERO giro: le tabelle che
          --    venivano dopo non venivano piu' pulite, e nessuno lo sapeva.
          --    ⚠️ Lo status e' ERROR e non WARN di proposito: i WARN di questa
          --    funzione sono salti DICHIARATI (esclusa, senza colonna, senza
          --    ttl). Questo non e' dichiarato — e' una tabella che si e'
          --    opposta, e va distinta a colpo d'occhio.
          WHEN OTHERS THEN
            GET STACKED DIAGNOSTICS
              v_sqlstate = RETURNED_SQLSTATE,
              v_errmsg   = MESSAGE_TEXT,
              v_errctx   = PG_EXCEPTION_CONTEXT;
            PERFORM dbops.fn_audit_log_once(
              p_function_name => 'dbops.fn_run_automations_cleanup',
              p_status        => 'ERROR',
              p_rule_type     => v_rule_type,
              p_exec_mode     => p_exec_mode,
              p_parts         => ARRAY[v_rule_type],
              p_dry_run       => p_dry_run,
              p_sqlstate      => v_sqlstate,
              p_error_context => v_errctx,
              p_params        => jsonb_build_object(
                                  'table', rtab.schema_name||'.'||rtab.table_name,
                                  'cleanup_column', v_cleanup_col,
                                  'skip_reason', 'BLOCKED_BY_TABLE'
                                ),
              p_message       => v_errmsg
            );
        END;
      END IF;
    END LOOP;
  END LOOP;
END;
$function$

COMMENT ON FUNCTION dbops.fn_run_automations_cleanup(p_exec_mode text, p_schemas text[], p_dry_run boolean)
IS 'Orchestratore cleanup_at con regole in dbops.automation_rules_tbl. Regole supportate: CLEANUP_AT (calcola cleanup_at con TTL fisso) e CLEANUP_PURGE (elimina i record scaduti, a batch). Parametri: p_exec_mode (AUTO/CI/SCHEDULED), p_schemas (scope schemi, NULL -> resolve da automation_scope), p_dry_run. ⭐ rev 2026-08-23: una tabella che RIFIUTA di essere pulita non fa piu'' morire il giro. Prima non c''era nessun EXCEPTION nel doppio ciclo, quindi un solo veto — un trigger append-only, il guard sul DELETE dei log — fermava l''intera passata e le tabelle successive non venivano piu'' pulite, senza che nessuno lo sapesse. Adesso la tabella viene saltata e il rifiuto lascia una riga ERROR in dbops.audit_log con SQLSTATE e contesto (skip_reason = BLOCKED_BY_TABLE): e'' il quarto membro della famiglia di salti che la funzione aveva gia'' (EXCLUDED, NO_CLEANUP_COLUMN, MISSING_TTL_DAYS, MISSING_BASE_TS_COLUMN). ⚠️ status ERROR e non WARN di proposito: i WARN sono salti DICHIARATI, questo e'' una tabella che si e'' opposta. ⛔ query_canceled si ri-solleva: un annullamento resta un annullamento. ⚠️ Ogni regola gira ora in una sottotransazione, che e'' cio'' che un blocco EXCEPTION implica.';
```

</div>

---
{% include-markdown "signature-core.md" %}
