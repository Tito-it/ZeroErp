# ⚙️ Funzione `fn_run_automations_tx_id`

```sql
CREATE FUNCTION fn_run_automations_tx_id(p_exec_mode text, p_schemas text[], p_dry_run boolean)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION dbops.fn_run_automations_tx_id(p_exec_mode text, p_schemas text[], p_dry_run boolean)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE
  rtab record;
  rrule record;
  rel  regclass;
  has_txid boolean;
  tmpl     text;
  trg_name text;
  exist_strat text;
BEGIN
  FOR rtab IN
    SELECT n.nspname AS schema_name,
          c.relname AS table_name,
          (quote_ident(n.nspname)||'.'||quote_ident(c.relname))::regclass AS rel
    FROM pg_class c
    JOIN pg_namespace n ON n.oid=c.relnamespace
    WHERE c.relkind='r'
      AND n.nspname = ANY(p_schemas)
  LOOP
    rel := rtab.rel;

    FOR rrule IN
      SELECT *
        FROM dbops.automation_rules_tbl r
      WHERE r.enabled
        AND r.rule_type='TX_ID'
        AND r.target_schema = rtab.schema_name
        AND (r.target_table IS NULL OR rtab.table_name LIKE r.target_table)
        AND (r.exec_mode='AUTO' OR r.exec_mode=p_exec_mode)
      ORDER BY r.priority, r.id
    LOOP
      exist_strat := COALESCE(rrule.existence_strategy,'BY_NAME');

      SELECT EXISTS(
        SELECT 1 FROM information_schema.columns
        WHERE table_schema=rtab.schema_name
          AND table_name =rtab.table_name
          AND column_name='tx_id' AND udt_name='uuid'
      ) INTO has_txid;

      IF has_txid THEN
        tmpl     := COALESCE(rrule.name_template,'trg_{table}_ins_upd_gen_tx_id');
        trg_name := dbops.fn_name_from_template(tmpl, rtab.schema_name, rtab.table_name, NULL,NULL,NULL,NULL);

        IF (exist_strat='BY_NAME'     AND NOT dbops.fn_trigger_exists_by_name(rel, trg_name))
        OR (exist_strat='BY_FUNCTION' AND NOT dbops.fn_trigger_exists_by_function(rel,'dbops','trgfn_tx_id_managed'))
        OR (exist_strat='BOTH'        AND NOT (dbops.fn_trigger_exists_by_name(rel, trg_name)
                                          OR dbops.fn_trigger_exists_by_function(rel,'dbops','trgfn_tx_id_managed')))
        THEN
          IF p_dry_run THEN
            PERFORM dbops.fn_log_error_only(jsonb_build_object('action','DRYRUN_CREATE_TRIGGER','rule','TX_ID','table',rtab.schema_name||'.'||rtab.table_name,'name',trg_name));
          ELSE
            BEGIN
              EXECUTE format($f$
                CREATE TRIGGER %I
                BEFORE INSERT OR UPDATE ON %I.%I
                FOR EACH ROW
                EXECUTE FUNCTION dbops.trgfn_tx_id_managed()
              $f$, trg_name, rtab.schema_name, rtab.table_name);
            EXCEPTION WHEN others THEN
              PERFORM dbops.fn_log_error_only(jsonb_build_object('where','TX_ID','table',rtab.schema_name||'.'||rtab.table_name,'error',SQLERRM));
            END;
          END IF;
        END IF;
      END IF;
    END LOOP;
  END LOOP;
END;
$function$
```

---
{% include-markdown "signature-core.md" %}
