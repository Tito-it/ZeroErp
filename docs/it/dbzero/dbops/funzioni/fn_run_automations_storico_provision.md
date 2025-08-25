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
  v_schemas text[] := p_schemas;
  has_flag boolean;
  storicizza_col text;
  fk_col text;
  create_gin boolean;
BEGIN
  -- Runner: scansiona regole STORICO con auto_provision, crea solo le tabelle storico mancanti
  -- scope fallback se p_schemas è NULL
  IF v_schemas IS NULL THEN
    IF EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
              WHERE n.nspname='dbops' AND c.relname='automation_scope' AND c.relkind='r') THEN
      SELECT array_agg(DISTINCT schema_name) INTO v_schemas FROM dbops.automation_scope;
    ELSE
      SELECT array_agg(nspname) INTO v_schemas
      FROM pg_namespace
      WHERE nspname NOT LIKE 'pg_%'
        AND nspname <> 'information_schema'
        AND nspname <> 'storico';
    END IF;
  END IF;

  -- loop tabelle degli schemi target
  FOR rtab IN
    SELECT n.nspname AS schema_name, c.relname AS table_name
    FROM pg_class c
    JOIN pg_namespace n ON n.oid=c.relnamespace
    WHERE c.relkind='r' AND n.nspname = ANY(v_schemas)
  LOOP
    -- regole STORICO pertinenti
    FOR rrule IN
      SELECT *
      FROM dbops.automation_rules_tbl r
      WHERE r.enabled
        AND r.rule_type='STORICO'
        AND (r.exec_mode='AUTO' OR r.exec_mode=p_exec_mode)
        AND r.target_schema = rtab.schema_name
        AND (r.target_table IS NULL OR rtab.table_name LIKE r.target_table)
    LOOP
      -- parametri
      create_gin := COALESCE((rrule.params->>'create_gin_index')::boolean, false);
      IF COALESCE((rrule.params->>'auto_provision')::boolean, false) IS NOT TRUE THEN
        CONTINUE;
      END IF;

      -- colonna storicizza (override: STORICIZZA_COL)
      storicizza_col := dbops.fn_get_override_col(rtab.schema_name, rtab.table_name, 'STORICIZZA_COL', 'storicizza');
      has_flag := dbops.fn_col_exists(rtab.schema_name, rtab.table_name, storicizza_col);
      IF NOT has_flag THEN
        CONTINUE;
      END IF;

      -- fk storico (override: STORICO_FK)
      fk_col := dbops.fn_get_override_col(rtab.schema_name, rtab.table_name, 'STORICO_FK', rtab.table_name||'_id');

      -- crea tabella storico se manca
      PERFORM dbops.fn_ensure_storico_table(rtab.schema_name, rtab.table_name, fk_col, create_gin, p_dry_run);
    END LOOP;
  END LOOP;
END;
$function$
```

---
{% include-markdown "signature-core.md" %}
