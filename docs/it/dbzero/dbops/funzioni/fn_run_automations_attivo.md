{% include-markdown "it/dbzero/dbops/manual/fn_run_automations_attivo.md" %}
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
  -- ⭐ Rev 2026-10-16: il contesto dell'errore, costruito una volta e usato
  --   dalle due chiamate del gestore (registro e involucro).
  v_ctx_errore dbops.error_log.context%TYPE;
  v_schemas text[];
  rrule record;
  rfk   record;

  -- strategia esistenza trigger: BY_NAME / BY_FUNCTION / BOTH (default BY_NAME)
  exist_strat text;

  -- template nome trigger BLOCK/REQUIRE
  nm_block text;
  nm_require text;

  -- colonna attivo sul PADRE (con override)
  col_attivo_parent text;

  -- colonna attivo sul FIGLIO (con override)
  col_attivo_child text;

  parent_has_attivo boolean;
  child_has_attivo  boolean;
  fk_col            text;

  -- colonna del padre realmente referenziata dalla FK del figlio
  -- (non necessariamente la PK del padre)
  v_parent_ref_col  text;

  -- nome trigger calcolato
  tname_parent_block  text;
  tname_child_require text;

  -- verifiche esistenza trigger
  exists_by_name boolean;
  exists_by_args boolean;

  -- helper
  v_reconcile      boolean;
  v_child_upd_cols text;
BEGIN
  /*
    Scopo
    -----
    Automazione ATTIVO (BLOCK + REQUIRE).
    Per ogni FK eleggibile nello scope:
    - sul PADRE: trigger BEFORE UPDATE OF attivo che impedisce la
      disattivazione se esistono righe figlie attive;
    - sul FIGLIO: constraint trigger DEFERRABLE che richiede padre attivo.

    Chiave del fix
    --------------
    Il cursor rfk include parent_ref_col (colonna del padre referenziata
    dalla FK del figlio) ricavata da pg_constraint.confkey[1]. Questa
    colonna viene passata alle trgfn al posto della PK del padre, per
    supportare correttamente FK che puntano a colonne UNIQUE non-PK.
  */

  v_schemas := dbops.fn_resolve_scope(p_schemas);

  -- ⭐ Rev 20260925-48: chi genera ritira. Le FK dichiarate eccezione in
  --   dbops.automazione_attivo_eccezioni non si legano sull'attivo: se i
  --   trigger ci sono gia' (generati prima che la coppia diventasse
  --   un'eccezione) si tolgono qui, a ogni giro. Non in dry run.
  IF NOT p_dry_run THEN
    PERFORM dbops.fn_ritira_attivo_eccezioni();
  END IF;

  FOR rrule IN
    SELECT r.*
    FROM dbops.automation_rules_tbl r
    WHERE r.enabled
      AND upper(btrim(r.rule_type)) = 'ATTIVO'
      AND (upper(btrim(r.exec_mode)) = 'AUTO' OR r.exec_mode = p_exec_mode)
      AND dbops.fn_schema_in_scope(r.target_schema, v_schemas)
    ORDER BY r.priority, r.id
  LOOP
    exist_strat := COALESCE(rrule.existence_strategy, 'BY_NAME');
    nm_block    := COALESCE((rrule.name_template::jsonb)->>'block',
                            'trg_{parent}_a10_{child}_block_deact_upd');
    nm_require  := COALESCE((rrule.name_template::jsonb)->>'require',
                            'trg_{child}_a10_{parent}_require_attivo_ins_upd');
    v_reconcile := COALESCE((rrule.params->>'reconcile_on_change')::boolean, true);

    -- Cursor FK: per ogni vincolo FK monocolonna in scope, ricava
    -- la colonna del padre realmente referenziata (confkey[1] -> attname)
    -- e la colonna FK del figlio (conkey[1] -> attname) in un'unica
    -- query, eliminando chiamate a dbops.fn_get_child_fk_col.
    -- Le FK multicolonna sono escluse: la trgfn non le supporta.
    FOR rfk IN
      SELECT
        c.oid                 AS conoid,
        np.nspname            AS parent_schema,
        cp.relname            AS parent_table,
        nc.nspname            AS child_schema,
        cc.relname            AS child_table,
        c.conrelid::regclass  AS child_rel,
        c.confrelid::regclass AS parent_rel,
        c.conname,
        a_p.attname           AS parent_ref_col,  -- colonna del padre referenziata
        a_c.attname           AS child_fk_col     -- colonna FK del figlio
      FROM pg_constraint c
      JOIN pg_class cc        ON cc.oid = c.conrelid
      JOIN pg_namespace nc    ON nc.oid = cc.relnamespace
      JOIN pg_class cp        ON cp.oid = c.confrelid
      JOIN pg_namespace np    ON np.oid = cp.relnamespace
      -- confkey e' int2[]; [1] e' la colonna referenziata sul padre
      JOIN pg_attribute a_p
        ON a_p.attrelid    = cp.oid
       AND a_p.attnum      = c.confkey[1]
       AND a_p.attnum > 0
       AND NOT a_p.attisdropped
      -- conkey e' int2[]; [1] e' la colonna FK sul figlio
      JOIN pg_attribute a_c
        ON a_c.attrelid    = cc.oid
       AND a_c.attnum      = c.conkey[1]
       AND a_c.attnum > 0
       AND NOT a_c.attisdropped
      WHERE c.contype = 'f'
        -- Solo FK monocolonna: la trgfn non supporta FK composite
        AND array_length(c.confkey, 1) = 1
        AND array_length(c.conkey, 1)  = 1
        AND nc.nspname = ANY(v_schemas)
        AND np.nspname = ANY(v_schemas)
        AND dbops.fn_table_in_scope(nc.nspname, cc.relname)
        AND dbops.fn_table_in_scope(np.nspname, cp.relname)
        AND (
          dbops.fn_schema_match(rrule.target_schema, np.nspname)
          OR dbops.fn_schema_match(rrule.target_schema, nc.nspname)
        )
        AND (
          UPPER(btrim(rrule.target_table)) = '*ALL'
          OR cc.relname ILIKE rrule.target_table
          OR cp.relname ILIKE rrule.target_table
        )
    LOOP
      -- 1) serve attivo sul PADRE
      col_attivo_parent := dbops.fn_get_override_col(rfk.parent_schema, rfk.parent_table, 'ATTIVO_COL', 'attivo');
      parent_has_attivo := dbops.fn_col_exists(rfk.parent_schema, rfk.parent_table, col_attivo_parent);

      IF NOT parent_has_attivo THEN
        IF p_dry_run THEN
          PERFORM dbops.fn_audit_log_once(
            p_function_name => 'fn_run_automations_attivo',
            p_status        => 'DRYRUN',
            p_rule_type     => 'ATTIVO_SKIP_PARENT_NO_ATTIVO',
            p_exec_mode     => p_exec_mode,
            p_parts         => ARRAY['ATTIVO_BLOCK','ATTIVO_REQUIRE'],
            p_dry_run       => true,
            p_params        => jsonb_build_object(
                                'action','SKIP',
                                'reason','PARENT_NO_ATTIVO',
                                'parent', rfk.parent_schema||'.'||rfk.parent_table,
                                'child',  rfk.child_schema||'.'||rfk.child_table
                              ),
            p_message       => 'Skip: parent table has no attivo column'
          );
        END IF;
        CONTINUE;
      END IF;

      -- 2) fk_col gia' calcolata dal cursor (no chiamata a fn_get_child_fk_col)
      fk_col := rfk.child_fk_col;

      -- 2.0) ⭐ Rev 20260925-48: FK dichiarata eccezione -> niente block,
      --   niente require (dbops.automazione_attivo_eccezioni, col suo motivo).
      IF EXISTS (SELECT 1 FROM dbops.automazione_attivo_eccezioni e
                  WHERE e.schema_figlia  = rfk.child_schema
                    AND e.tabella_figlia = rfk.child_table
                    AND e.colonna_fk     = fk_col) THEN
        IF p_dry_run THEN
          PERFORM dbops.fn_audit_log_once(
            p_function_name => 'fn_run_automations_attivo',
            p_status        => 'DRYRUN',
            p_rule_type     => 'ATTIVO_SKIP_ECCEZIONE',
            p_exec_mode     => p_exec_mode,
            p_parts         => ARRAY['ATTIVO_BLOCK','ATTIVO_REQUIRE'],
            p_dry_run       => true,
            p_params        => jsonb_build_object(
                                'action','SKIP',
                                'reason','ECCEZIONE_DICHIARATA',
                                'parent', rfk.parent_schema||'.'||rfk.parent_table,
                                'child',  rfk.child_schema||'.'||rfk.child_table,
                                'fk',     fk_col
                              ),
            p_message       => 'Skip: FK dichiarata in dbops.automazione_attivo_eccezioni'
          );
        END IF;
        CONTINUE;
      END IF;

      -- 2.1) applica automations solo su FK con suffisso _id
      IF lower(fk_col) NOT LIKE '%_id' THEN
        IF p_dry_run THEN
          PERFORM dbops.fn_audit_log_once(
            p_function_name => 'fn_run_automations_attivo',
            p_status        => 'DRYRUN',
            p_rule_type     => 'ATTIVO_SKIP_FK_NO_ID',
            p_exec_mode     => p_exec_mode,
            p_parts         => ARRAY['ATTIVO_BLOCK','ATTIVO_REQUIRE'],
            p_dry_run       => true,
            p_params        => jsonb_build_object(
                                'action','SKIP',
                                'reason','FK_NO_ID_SUFFIX',
                                'parent', rfk.parent_schema||'.'||rfk.parent_table,
                                'child',  rfk.child_schema||'.'||rfk.child_table,
                                'fk',     fk_col
                              ),
            p_message       => 'Skip: FK column has no _id suffix'
          );
        END IF;
        CONTINUE;
      END IF;

      -- 3) Colonna del padre referenziata dalla FK (dal cursor, no fallback su PK)
      v_parent_ref_col := rfk.parent_ref_col;

      -- 4) Colonna attivo sul figlio (opzionale)
      col_attivo_child := dbops.fn_get_override_col(rfk.child_schema, rfk.child_table, 'ATTIVO_COL', 'attivo');
      child_has_attivo := dbops.fn_col_exists(rfk.child_schema, rfk.child_table, col_attivo_child);

      -- 5) Nome trigger REQUIRE (figlio)
      tname_child_require :=
        dbops.fn_name_from_template(
          nm_require,
          rfk.child_schema, rfk.child_table,
          rfk.parent_table, rfk.child_table, rfk.conname, NULL
        );

      -- 6) REQUIRE: esistenza trigger (helper aggiornata a 5 args)
      exists_by_name := dbops.fn_trigger_exists_by_name(rfk.child_rel, tname_child_require);
      exists_by_args := dbops.fn_trigger_exists_require_by_args(
                          rfk.child_rel,
                          rfk.parent_schema, rfk.parent_table,
                          col_attivo_parent, fk_col, v_parent_ref_col
                        );

      IF (exist_strat='BY_NAME'      AND NOT exists_by_name)
      OR (exist_strat='BY_FUNCTION'  AND NOT exists_by_args)
      OR (exist_strat='BOTH'         AND NOT (exists_by_name OR exists_by_args))
      THEN
        IF p_dry_run THEN
          PERFORM dbops.fn_audit_log_once(
            p_function_name => 'fn_run_automations_attivo',
            p_status        => 'DRYRUN',
            p_rule_type     => 'ATTIVO_REQUIRE',
            p_exec_mode     => p_exec_mode,
            p_parts         => ARRAY['ATTIVO_REQUIRE'],
            p_dry_run       => true,
            p_params        => jsonb_build_object(
                                'action','DRYRUN_CREATE_TRIGGER',
                                'name',       tname_child_require,
                                'parent',     rfk.parent_schema||'.'||rfk.parent_table,
                                'child',      rfk.child_schema||'.'||rfk.child_table,
                                'attivo_col', col_attivo_parent,
                                'fk',         fk_col,
                                'ref_col',    v_parent_ref_col,
                                'exist_strategy', exist_strat
                              ),
            p_message       => 'REQUIRE trigger would be created'
          );
        ELSE
          BEGIN
            IF v_reconcile THEN
              -- drop dei trigger con la nuova firma a 5 args
              PERFORM dbops.fn_drop_triggers_by_function_args(
                rfk.child_rel,
                'dbops', 'trgfn_child_requires_active_parent',
                rfk.parent_schema, rfk.parent_table,
                col_attivo_parent, fk_col, v_parent_ref_col
              );
            END IF;

            IF child_has_attivo THEN
              v_child_upd_cols := format('%I, %I', col_attivo_child, fk_col);
            ELSE
              v_child_upd_cols := format('%I', fk_col);
            END IF;

            -- Crea il trigger REQUIRE passando 5 args alla trgfn
            EXECUTE format($f$
              CREATE CONSTRAINT TRIGGER %I
              AFTER INSERT OR UPDATE OF %s ON %I.%I
              DEFERRABLE INITIALLY DEFERRED
              FOR EACH ROW
              EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent(%L,%L,%L,%L,%L)
            $f$,
              tname_child_require,
              v_child_upd_cols,
              rfk.child_schema, rfk.child_table,
              rfk.parent_schema, rfk.parent_table,
              col_attivo_parent, fk_col, v_parent_ref_col
            );

          EXCEPTION WHEN others THEN
            -- ⭐ Rev 2026-10-16 (brief-db-presidio-job-run-a-chi-tocca D8, D10, D11):
            --   un guasto dell'AMBIENTE (script.fn_sqlstate_di_ambiente: connessione,
            --   risorse, arresto, sistema, privilegio, lock) si rilancia COM'E', col suo
            --   SQLSTATE: l'involucro lo faceva diventare P0001, e il presidio dei job lo
            --   mandava allo sviluppo. Prima si scrive nel registro errori, col contesto.
            v_ctx_errore := jsonb_build_object(
                'where',      'ATTIVO_REQUIRE_CREATE',
                'parent',     rfk.parent_schema||'.'||rfk.parent_table,
                'child',      rfk.child_schema||'.'||rfk.child_table,
                'attivo_col', col_attivo_parent,
                'fk',         fk_col,
                'ref_col',    v_parent_ref_col,
                'trigger',    tname_child_require,
                'error',      SQLERRM
              );
            IF script.fn_sqlstate_di_ambiente(SQLSTATE) THEN
              PERFORM script.fn_log_error_only(
                  'dbops', 'run_automations', 'E_ATTIVO_REQUIRE',
                  v_ctx_errore, NULL::uuid, SQLERRM);
              RAISE;
            END IF;
            PERFORM script.fn_log_and_raise_error(
                'dbops', 'run_automations', 'E_ATTIVO_REQUIRE',
                v_ctx_errore, NULL::uuid, SQLERRM);
          END;
        END IF;
      ELSE
        IF p_dry_run THEN
          PERFORM dbops.fn_audit_log_once(
            p_function_name => 'fn_run_automations_attivo',
            p_status        => 'DRYRUN',
            p_rule_type     => 'ATTIVO_REQUIRE_OK_EXISTS',
            p_exec_mode     => p_exec_mode,
            p_parts         => ARRAY['ATTIVO_REQUIRE'],
            p_dry_run       => true,
            p_params        => jsonb_build_object(
                                'action','NOOP',
                                'reason','TRIGGER_EXISTS',
                                'name',    tname_child_require,
                                'parent',  rfk.parent_schema||'.'||rfk.parent_table,
                                'child',   rfk.child_schema||'.'||rfk.child_table,
                                'fk',      fk_col,
                                'ref_col', v_parent_ref_col,
                                'exist_strategy', exist_strat,
                                'exists_by_name', exists_by_name,
                                'exists_by_args', exists_by_args
                              ),
            p_message       => 'No action: REQUIRE trigger already exists'
          );
        END IF;
      END IF;

      -- 7) Nome trigger BLOCK (padre)
      tname_parent_block :=
        dbops.fn_name_from_template(
          nm_block,
          rfk.parent_schema, rfk.parent_table,
          rfk.parent_table, rfk.child_table, rfk.conname, NULL
        );

      -- 8) BLOCK: esistenza trigger (helper aggiornata a 5 args utili)
      exists_by_name := dbops.fn_trigger_exists_by_name(rfk.parent_rel, tname_parent_block);
      exists_by_args := dbops.fn_trigger_exists_block_by_args(
                          rfk.parent_rel,
                          rfk.child_schema, rfk.child_table,
                          fk_col, v_parent_ref_col, col_attivo_parent
                        );

      IF (exist_strat='BY_NAME'      AND NOT exists_by_name)
      OR (exist_strat='BY_FUNCTION'  AND NOT exists_by_args)
      OR (exist_strat='BOTH'         AND NOT (exists_by_name OR exists_by_args))
      THEN
        IF p_dry_run THEN
          PERFORM dbops.fn_audit_log_once(
            p_function_name => 'fn_run_automations_attivo',
            p_status        => 'DRYRUN',
            p_rule_type     => 'ATTIVO_BLOCK',
            p_exec_mode     => p_exec_mode,
            p_parts         => ARRAY['ATTIVO_BLOCK'],
            p_dry_run       => true,
            p_params        => jsonb_build_object(
                                'action','DRYRUN_CREATE_TRIGGER',
                                'name',       tname_parent_block,
                                'parent',     rfk.parent_schema||'.'||rfk.parent_table,
                                'child',      rfk.child_schema||'.'||rfk.child_table,
                                'attivo_col', col_attivo_parent,
                                'fk',         fk_col,
                                'ref_col',    v_parent_ref_col,
                                'exist_strategy', exist_strat
                              ),
            p_message       => 'BLOCK trigger would be created'
          );
        ELSE
          BEGIN
            IF v_reconcile THEN
              PERFORM dbops.fn_drop_triggers_by_function_args(
                rfk.parent_rel,
                'dbops', 'trgfn_prevent_deactivate_if_children',
                rfk.child_schema, rfk.child_table,
                fk_col, v_parent_ref_col, col_attivo_parent
              );
            END IF;

            -- Crea il trigger BLOCK passando 5 args alla trgfn:
            -- child_schema, child_table, fk_col, parent_ref_col, parent_attivo_col
            -- Il 5° arg (parent_attivo_col) consente alla trgfn di
            -- leggere OLD/NEW.<col_attivo> dinamicamente, rispettando
            -- l'override gestito da dbops.automation_overrides_cols.
            EXECUTE format($f$
              CREATE TRIGGER %I
              BEFORE UPDATE OF %I ON %I.%I
              FOR EACH ROW
              EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children(%L,%L,%L,%L,%L)
            $f$,
              tname_parent_block,
              col_attivo_parent,
              rfk.parent_schema, rfk.parent_table,
              rfk.child_schema, rfk.child_table,
              fk_col, v_parent_ref_col, col_attivo_parent
            );

          EXCEPTION WHEN others THEN
            -- ⭐ Rev 2026-10-16 (brief-db-presidio-job-run-a-chi-tocca D8, D10, D11):
            --   un guasto dell'AMBIENTE (script.fn_sqlstate_di_ambiente: connessione,
            --   risorse, arresto, sistema, privilegio, lock) si rilancia COM'E', col suo
            --   SQLSTATE: l'involucro lo faceva diventare P0001, e il presidio dei job lo
            --   mandava allo sviluppo. Prima si scrive nel registro errori, col contesto.
            v_ctx_errore := jsonb_build_object(
                'where',      'ATTIVO_BLOCK_CREATE',
                'parent',     rfk.parent_schema||'.'||rfk.parent_table,
                'child',      rfk.child_schema||'.'||rfk.child_table,
                'attivo_col', col_attivo_parent,
                'fk',         fk_col,
                'ref_col',    v_parent_ref_col,
                'trigger',    tname_parent_block,
                'error',      SQLERRM
              );
            IF script.fn_sqlstate_di_ambiente(SQLSTATE) THEN
              PERFORM script.fn_log_error_only(
                  'dbops', 'run_automations', 'E_ATTIVO_BLOCK',
                  v_ctx_errore, NULL::uuid, SQLERRM);
              RAISE;
            END IF;
            PERFORM script.fn_log_and_raise_error(
                'dbops', 'run_automations', 'E_ATTIVO_BLOCK',
                v_ctx_errore, NULL::uuid, SQLERRM);
          END;
        END IF;
      ELSE
        IF p_dry_run THEN
          PERFORM dbops.fn_audit_log_once(
            p_function_name => 'fn_run_automations_attivo',
            p_status        => 'DRYRUN',
            p_rule_type     => 'ATTIVO_OK_EXISTS',
            p_exec_mode     => p_exec_mode,
            p_parts         => ARRAY['ATTIVO_BLOCK'],
            p_dry_run       => true,
            p_params        => jsonb_build_object(
                                'action','NOOP',
                                'reason','TRIGGER_EXISTS',
                                'name',    tname_parent_block,
                                'parent',  rfk.parent_schema||'.'||rfk.parent_table,
                                'child',   rfk.child_schema||'.'||rfk.child_table,
                                'fk',      fk_col,
                                'ref_col', v_parent_ref_col,
                                'exist_strategy', exist_strat,
                                'exists_by_name', exists_by_name,
                                'exists_by_args', exists_by_args
                              ),
            p_message       => 'No action: BLOCK trigger already exists'
          );
        END IF;
      END IF;

    END LOOP; -- rfk
  END LOOP; -- rrule
END;
$function$

COMMENT ON FUNCTION dbops.fn_run_automations_attivo(p_exec_mode text, p_schemas text[], p_dry_run boolean)
IS 'Automazione ATTIVO (BLOCK + REQUIRE): crea trigger BLOCK sul padre e REQUIRE sul figlio quando il padre ha colonna attivo. Usa la colonna del padre realmente referenziata dalla FK (confkey[1]), non la PK, per supportare FK su colonne UNIQUE non-PK. ⭐ Rev 20260925-48: salta le FK dichiarate in dbops.automazione_attivo_eccezioni (ognuna col suo motivo) e, fuori dal dry run, in testa a ogni giro chiama dbops.fn_ritira_attivo_eccezioni, che toglie i trigger gia'' generati per quelle coppie: chi genera ritira. Prima eccezione: config.profili_accesso_bindings.identita_digitale_id (porta e profili si sganciano, brief-db-blocco-login-per-credenziale §12.3). ⭐ Rev 2026-10-16: nel gestore WHEN others, un guasto dell''AMBIENTE (script.fn_sqlstate_di_ambiente: 08, 53, 57, 58, 42501, 55P03) si rilancia COM''E'', col suo SQLSTATE, dopo averlo scritto nel registro errori con lo stesso codice e contesto (fn_log_error_only). Prima diventava P0001 col codice dell''involucro, e il presidio dei job (maintenance.vw_job_run_da_guardare) lo mandava allo sviluppo. I difetti di struttura escono come prima. Brief: brief-db-presidio-job-run-a-chi-tocca D8, D11.';
```

---
{% include-markdown "signature-core.md" %}
