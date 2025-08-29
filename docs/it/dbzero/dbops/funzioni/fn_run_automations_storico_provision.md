{% include-markdown "it/dbzero/dbops/manual/fn_run_automations_storico_provision.md" %}
# ⚙️ Funzione `fn_run_automations_storico_provision`

```sql
CREATE FUNCTION fn_run_automations_storico_provision(p_exec_mode text, p_schemas text[], p_dry_run boolean)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION dbops.fn_run_automations_storico_provision(p_exec_mode text, p_schemas text[], p_dry_run boolean)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
      DECLARE
        rtab record;
        rrule record;
        v_schemas text[] ;
        has_flag boolean;
        storicizza_col text;
        fk_col text;
        create_gin boolean;
      BEGIN
        v_schemas := dbops.fn_resolve_scope(p_schemas);

      

        -- loop tabelle degli schemi target
        FOR rtab IN
          SELECT n.nspname AS schema_name, c.relname AS table_name
          FROM pg_class c
          JOIN pg_namespace n ON n.oid=c.relnamespace
          WHERE c.relkind='r' AND n.nspname = ANY(v_schemas)
          AND n.nspname <> 'storico'   
          AND dbops.fn_table_in_scope(n.nspname, c.relname)
        LOOP
          -- regole 'STORICO_PROVISION' pertinenti (schema match con wildcard *all + target_table)
          FOR rrule IN
            SELECT *
            FROM dbops.automation_rules_tbl r
            WHERE r.enabled
              AND r.rule_type='STORICO_PROVISION'
              AND (r.exec_mode='AUTO' OR r.exec_mode=p_exec_mode)
              AND dbops.fn_schema_match(r.target_schema, rtab.schema_name)
              AND (r.target_table IS NULL OR rtab.table_name LIKE r.target_table)
          LOOP
            --  parametri regola
            create_gin := COALESCE((rrule.params->>'create_gin_index')::boolean, false);

            /*IF COALESCE((rrule.params->>'auto_provision')::boolean, false) IS NOT TRUE THEN
              CONTINUE;
            END IF; */

            -- colonna storicizza (override: STORICIZZA_COL)
            storicizza_col := dbops.fn_get_override_col(rtab.schema_name, rtab.table_name, 'STORICIZZA_COL', 'storicizza');
            has_flag := dbops.fn_col_exists(rtab.schema_name, rtab.table_name, storicizza_col);
            IF NOT has_flag THEN
              CONTINUE;
            END IF;

            -- calcolo FK colonna storico (override: STORICO_FK)
            fk_col := dbops.fn_get_override_col(rtab.schema_name, rtab.table_name, 'STORICO_FK', rtab.table_name||'_id');

            -- crea tabella storico se manca (dry-run / ok / error handling già dentro helper)
            PERFORM dbops.fn_ensure_storico_table(rtab.schema_name, rtab.table_name, fk_col, create_gin, p_dry_run);
          END LOOP;
        END LOOP;
      END;
      $function$
```

---
{% include-markdown "signature-core.md" %}
