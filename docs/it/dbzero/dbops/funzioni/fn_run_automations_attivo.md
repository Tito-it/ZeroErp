# ⚙️ Funzione `fn_run_automations_attivo`

```sql
CREATE FUNCTION fn_run_automations_attivo(p_exec_mode text, p_schemas text[], p_dry_run boolean)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION dbops.fn_run_automations_attivo(p_exec_mode text, p_schemas text[], p_dry_run boolean)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE
  rrule record;
  rfk   record;

  exist_strat text;

  -- template (JSON con 3 nomi)
  nm_cascade text;
  nm_require text;
  nm_block   text;

  -- colonne attivo
  col_attivo_parent text;
  col_attivo_child  text;

  parent_has_attivo boolean;
  child_has_attivo  boolean;

  fk_col text;

  tname_parent_cascade text;
  tname_child_require  text;
  tname_parent_block   text;
BEGIN

  -- ======================================================================
  -- dbops.run_automations_attivo(p_exec_mode, p_schemas, p_dry_run)
  -- Applica regole ATTIVO/soft-delete su FK con ON DELETE RESTRICT:
  --   - CASO A (padre&figlio con attivo): 
  --       * padre AFTER UPDATE OF attivo → dbops.trgfn_soft_delete_cascade()
  --       * figlio CONSTRAINT DEFERRABLE → dbops.trgfn_child_requires_active_parent()
  --   - CASO B (solo padre con attivo):
  --       * padre BEFORE UPDATE OF attivo → dbops.trgfn_prevent_deactivate_if_children()
  -- Usa naming parametrico (3 template JSON: cascade/require/block).
  -- ======================================================================


  FOR rrule IN
    SELECT *
      FROM dbops.automation_rules_tbl
    WHERE enabled
      AND rule_type='ATTIVO'
      AND (exec_mode='AUTO' OR exec_mode=p_exec_mode)
      AND (target_schema IS NULL OR target_schema = ANY(p_schemas))
    ORDER BY priority, id
  LOOP
    exist_strat := COALESCE(rrule.existence_strategy,'BY_NAME');

    nm_cascade := COALESCE((rrule.name_template::jsonb)->>'cascade','trg_soft_del_{parent}__{child}__{fk}');
    nm_require := COALESCE((rrule.name_template::jsonb)->>'require','trg_chk_{child}_parent_{fk}');
    nm_block   := COALESCE((rrule.name_template::jsonb)->>'block','trg_block_deact_{parent}__{child}');

    FOR rfk IN
      SELECT
        c.oid AS conoid,
        np.nspname AS parent_schema,
        cp.relname AS parent_table,
        nc.nspname AS child_schema,
        cc.relname AS child_table,
        c.conrelid::regclass AS child_rel,
        c.confrelid::regclass AS parent_rel,
        c.conname,
        c.confdeltype
      FROM pg_constraint c
      JOIN pg_class cc ON cc.oid = c.conrelid
      JOIN pg_namespace nc ON nc.oid = cc.relnamespace
      JOIN pg_class cp ON cp.oid = c.confrelid
      JOIN pg_namespace np ON np.oid = cp.relnamespace
      WHERE c.contype='f'
        AND c.confdeltype IN ('r','a')  -- RESTRICT o NO ACTION
        AND (rrule.target_schema IS NULL OR nc.nspname = rrule.target_schema)
        -- target_table applicata a child OPPURE parent
        AND (rrule.target_table IS NULL OR cc.relname LIKE rrule.target_table OR cp.relname LIKE rrule.target_table)
        AND NOT EXISTS (
          SELECT 1 FROM dbops.automation_fk_exclusions e
          WHERE e.parent_schema=np.nspname AND e.parent_table=cp.relname
            AND e.child_schema=nc.nspname  AND e.child_table=cc.relname
        )
    LOOP
      col_attivo_parent := dbops.fn_get_override_col(rfk.parent_schema, rfk.parent_table, 'ATTIVO_COL', 'attivo');
      col_attivo_child  := dbops.fn_get_override_col(rfk.child_schema,  rfk.child_table,  'ATTIVO_COL', 'attivo');

      SELECT dbops.fn_col_exists(rfk.parent_schema, rfk.parent_table, col_attivo_parent)
          , dbops.fn_col_exists(rfk.child_schema,  rfk.child_table,  col_attivo_child)
        INTO parent_has_attivo, child_has_attivo;

      fk_col := dbops.fn_get_child_fk_col(rfk.conoid);

      tname_parent_cascade := dbops.fn_name_from_template(nm_cascade, rfk.parent_schema, rfk.parent_table, rfk.parent_table, rfk.child_table, rfk.conname, NULL);
      tname_child_require  := dbops.fn_name_from_template(nm_require, rfk.child_schema, rfk.child_table, rfk.parent_table, rfk.child_table, rfk.conname, NULL);
      tname_parent_block   := dbops.fn_name_from_template(nm_block, rfk.parent_schema, rfk.parent_table, rfk.parent_table, rfk.child_table, rfk.conname, NULL);

      -- CASO A: entrambi hanno attivo → cascade + require
      IF parent_has_attivo AND child_has_attivo THEN
        -- padre: cascade
        IF (exist_strat='BY_NAME'     AND NOT dbops.fn_trigger_exists_by_name(rfk.parent_rel, tname_parent_cascade))
        OR (exist_strat='BY_FUNCTION' AND NOT dbops.fn_trigger_exists_by_function(rfk.parent_rel,'dbops','trgfn_soft_delete_cascade'))
        OR (exist_strat='BOTH'        AND NOT (dbops.fn_trigger_exists_by_name(rfk.parent_rel, tname_parent_cascade)
                                          OR dbops.fn_trigger_exists_by_function(rfk.parent_rel,'dbops','trgfn_soft_delete_cascade')))
        THEN
          IF p_dry_run THEN
            PERFORM dbops.fn_log_error_only(jsonb_build_object('action','DRYRUN_CREATE_TRIGGER','rule','ATTIVO_cascade','table',rfk.parent_schema||'.'||rfk.parent_table,'name',tname_parent_cascade,'fk',fk_col));
          ELSE
            BEGIN
              EXECUTE format($f$
                CREATE TRIGGER %I
                AFTER UPDATE OF %I ON %I.%I
                FOR EACH ROW
                EXECUTE FUNCTION dbops.trgfn_soft_delete_cascade(%L,%L,%L)
              $f$, tname_parent_cascade, col_attivo_parent, rfk.parent_schema, rfk.parent_table, rfk.child_schema, rfk.child_table, fk_col);
            EXCEPTION WHEN others THEN
              PERFORM dbops.fn_log_error_only(jsonb_build_object('where','ATTIVO_cascade','table',rfk.parent_schema||'.'||rfk.parent_table,'error',SQLERRM));
            END;
          END IF;
        END IF;

        -- figlio: require (constraint, deferrable)
        IF (exist_strat='BY_NAME'     AND NOT dbops.fn_trigger_exists_by_name(rfk.child_rel, tname_child_require))
        OR (exist_strat='BY_FUNCTION' AND NOT dbops.fn_trigger_exists_by_function(rfk.child_rel,'dbops','trgfn_child_requires_active_parent'))
        OR (exist_strat='BOTH'        AND NOT (dbops.fn_trigger_exists_by_name(rfk.child_rel, tname_child_require)
                                          OR dbops.fn_trigger_exists_by_function(rfk.child_rel,'dbops','trgfn_child_requires_active_parent')))
        THEN
          IF p_dry_run THEN
            PERFORM dbops.fn_log_error_only(jsonb_build_object('action','DRYRUN_CREATE_TRIGGER','rule','ATTIVO_require','table',rfk.child_schema||'.'||rfk.child_table,'name',tname_child_require,'fk',fk_col));
          ELSE
            BEGIN
              EXECUTE format($f$
                CREATE CONSTRAINT TRIGGER %I
                AFTER INSERT OR UPDATE OF %I, %I ON %I.%I
                DEFERRABLE INITIALLY DEFERRED
                FOR EACH ROW
                EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent(%L,%L,%L,%L)
              $f$, tname_child_require, col_attivo_child, fk_col, rfk.child_schema, rfk.child_table,
                  rfk.parent_schema, rfk.parent_table, col_attivo_parent, fk_col);
            EXCEPTION WHEN others THEN
              PERFORM dbops.fn_log_error_only(jsonb_build_object('where','ATTIVO_require','table',rfk.child_schema||'.'||rfk.child_table,'error',SQLERRM));
            END;
          END IF;
        END IF;

      -- CASO B: solo padre ha attivo → blocco
      ELSIF parent_has_attivo AND NOT child_has_attivo THEN
        IF (exist_strat='BY_NAME'     AND NOT dbops.fn_trigger_exists_by_name(rfk.parent_rel, tname_parent_block))
        OR (exist_strat='BY_FUNCTION' AND NOT dbops.fn_trigger_exists_by_function(rfk.parent_rel,'dbops','trgfn_prevent_deactivate_if_children'))
        OR (exist_strat='BOTH'        AND NOT (dbops.fn_trigger_exists_by_name(rfk.parent_rel, tname_parent_block)
                                          OR dbops.fn_trigger_exists_by_function(rfk.parent_rel,'dbops','trgfn_prevent_deactivate_if_children')))
        THEN
          IF p_dry_run THEN
            PERFORM dbops.fn_log_error_only(jsonb_build_object('action','DRYRUN_CREATE_TRIGGER','rule','ATTIVO_block','table',rfk.parent_schema||'.'||rfk.parent_table,'name',tname_parent_block,'fk',fk_col));
          ELSE
            BEGIN
              EXECUTE format($f$
                CREATE TRIGGER %I
                BEFORE UPDATE OF %I ON %I.%I
                FOR EACH ROW
                EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children(%L,%L,%L)
              $f$, tname_parent_block, col_attivo_parent, rfk.parent_schema, rfk.parent_table, rfk.child_schema, rfk.child_table, fk_col);
            EXCEPTION WHEN others THEN
              PERFORM dbops.fn_log_error_only(jsonb_build_object('where','ATTIVO_block','table',rfk.parent_schema||'.'||rfk.parent_table,'error',SQLERRM));
            END;
          END IF;
        END IF;
      END IF;

    END LOOP; -- fk
  END LOOP; -- regole ATTIVO
END;
$function$
```

---
{% include-markdown "signature-core.md" %}
