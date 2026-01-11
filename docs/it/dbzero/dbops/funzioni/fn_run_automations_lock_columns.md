{% include-markdown "it/dbzero/dbops/manual/fn_run_automations_lock_columns.md" %}
# ⚙️ Funzione `fn_run_automations_lock_columns`

```sql
CREATE FUNCTION fn_run_automations_lock_columns(p_exec_mode text, p_schemas text[], p_dry_run boolean)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION dbops.fn_run_automations_lock_columns(p_exec_mode text, p_schemas text[], p_dry_run boolean)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_schemas text[];
  rtab record;
  rrule record;
  rcol record;
  rel  regclass;
  col_list text[];
  arg_list text[];
  trg_name text;
  tmpl     text;
  exist_strat text;
  update_cols text;
  arg_text text;
  created boolean;
BEGIN

/*
  Scopo
  -----
  Esegue l'automazione di provisioning dei trigger "LOCK_COLUMNS" sulle tabelle in scope,
  applicando il blocco su:
  - codice_interno (se presente in tabella),
  - colonne extra definite in dbops.automation_lock_columns.

  Regole di selezione colonne
  ---------------------------
  1) codice_interno e' implicito: non si configura nella tabella di setup.
  2) Le colonne extra sono lette da dbops.automation_lock_columns con:
     - enabled = true
     - exec_mode = 'AUTO' oppure exec_mode = p_exec_mode
  3) Una colonna e' aggiunta solo se esiste fisicamente nella tabella target.

  Trigger generato
  ----------------
  Unico trigger per tabella:
    BEFORE UPDATE OF <colonne>
    EXECUTE FUNCTION script.trgfn_lock_columns(<col,msgcode...>)
  Nome trigger:
    trg_{table}_a10_lock_columns_upd (via dbops.fn_name_from_template)

  Modalita' DRY RUN
  ----------------
  Se p_dry_run=true non esegue DDL (CREATE TRIGGER) e registra audit con dbops.fn_audit_log_once.

  Error handling
  --------------
  In caso di errore nella creazione del trigger, log strutturato e rilancio tramite
  script.fn_log_and_raise_error con contesto 'LOCK_COLUMNS'.
*/

  v_schemas := dbops.fn_resolve_scope(p_schemas);
  FOR rtab IN
    SELECT n.nspname AS schema_name,
          c.relname AS table_name,
          (quote_ident(n.nspname)||'.'||quote_ident(c.relname))::regclass AS rel
    FROM pg_class c
    JOIN pg_namespace n ON n.oid=c.relnamespace
    WHERE c.relkind='r'
      AND n.nspname = ANY(v_schemas)
      AND dbops.fn_table_in_scope(n.nspname, c.relname)
  LOOP
    rel := rtab.rel;
    col_list := ARRAY[]::text[];
    arg_list := ARRAY[]::text[];
    created := false;

    IF dbops.fn_col_exists(rtab.schema_name, rtab.table_name, 'codice_interno') THEN
      col_list := array_append(col_list, 'codice_interno');
      arg_list := array_append(arg_list, quote_literal('codice_interno'));
      arg_list := array_append(arg_list, quote_literal('CODICE_NON_MODIFICABILE'));
    END IF;

    FOR rcol IN
      SELECT column_name,
             COALESCE(error_code, 'CODICE_NON_MODIFICABILE') AS error_code
        FROM dbops.automation_lock_columns
       WHERE enabled
         AND target_schema = rtab.schema_name
         AND target_table = rtab.table_name
         AND (upper(btrim(exec_mode)) = 'AUTO' OR exec_mode = p_exec_mode)
       ORDER BY column_name
    LOOP
      IF dbops.fn_col_exists(rtab.schema_name, rtab.table_name, rcol.column_name) THEN
        IF NOT (rcol.column_name = ANY(col_list)) THEN
          col_list := array_append(col_list, rcol.column_name);
          arg_list := array_append(arg_list, quote_literal(rcol.column_name));
          arg_list := array_append(arg_list, quote_literal(rcol.error_code));
        END IF;
      END IF;
    END LOOP;

    IF array_length(col_list, 1) IS NOT NULL THEN
      FOR rrule IN
        SELECT *
          FROM dbops.automation_rules_tbl r
        WHERE r.enabled
          AND upper(btrim(r.rule_type))='LOCK_COLUMNS'
          AND dbops.fn_schema_match(r.target_schema, rtab.schema_name)
          AND (UPPER(r.target_table) = '*ALL' OR rtab.table_name ILIKE r.target_table)
          AND (upper(btrim(r.exec_mode)) = 'AUTO' OR r.exec_mode = p_exec_mode)
        ORDER BY r.priority, r.id
      LOOP
        EXIT WHEN created;
        exist_strat := COALESCE(rrule.existence_strategy,'BY_NAME');
        tmpl := COALESCE(rrule.name_template, 'trg_{table}_a10_lock_columns_upd');
        trg_name := dbops.fn_name_from_template(tmpl, rtab.schema_name, rtab.table_name, NULL, NULL, NULL, NULL);

        IF (exist_strat='BY_NAME'     AND NOT dbops.fn_trigger_exists_by_name(rel, trg_name))
        OR (exist_strat='BY_FUNCTION' AND NOT dbops.fn_trigger_exists_by_function(rel, 'script', 'trgfn_lock_columns'))
        OR (exist_strat='BOTH'        AND NOT (dbops.fn_trigger_exists_by_name(rel, trg_name)
                                          OR dbops.fn_trigger_exists_by_function(rel, 'script', 'trgfn_lock_columns')))
        THEN
          update_cols := (
            SELECT string_agg(quote_ident(c), ', ')
              FROM unnest(col_list) AS c
          );
          arg_text := array_to_string(arg_list, ', ');

          IF p_dry_run THEN
            PERFORM dbops.fn_audit_log_once(
              p_function_name => 'dbops.fn_run_automations',
              p_status        => 'DRYRUN',
              p_rule_type     => 'LOCK_COLUMNS',
              p_exec_mode     => p_exec_mode,
              p_parts         => ARRAY['LOCK_COLUMNS'],
              p_dry_run       => true,
              p_params        => jsonb_build_object(
                                  'table', rtab.schema_name||'.'||rtab.table_name,
                                  'trigger', trg_name,
                                  'columns', col_list,
                                  'action', 'DRYRUN_CREATE_TRIGGER'
                                ),
              p_message       => 'Trigger would be created'
            );
            created := true;
          ELSE
            BEGIN
              EXECUTE format($f$
                CREATE TRIGGER %I
                BEFORE UPDATE OF %s ON %I.%I
                FOR EACH ROW
                EXECUTE FUNCTION script.trgfn_lock_columns(%s)
              $f$, trg_name, update_cols, rtab.schema_name, rtab.table_name, arg_text);
              created := true;
            EXCEPTION WHEN others THEN
              PERFORM script.fn_log_and_raise_error(
                'dbops',
                'run_automations',
                'E_LOCK_COLUMNS',
                jsonb_build_object(
                  'where','LOCK_COLUMNS',
                  'table', rtab.schema_name||'.'||rtab.table_name,
                  'error', SQLERRM
                ),
                NULL::uuid,
                SQLERRM
              );
            END;
          END IF;
        END IF;
      END LOOP;
    END IF;
  END LOOP;
END;
$function$
```

---
{% include-markdown "signature-core.md" %}
