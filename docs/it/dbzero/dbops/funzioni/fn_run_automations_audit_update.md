{% include-markdown "it/dbzero/dbops/manual/fn_run_automations_audit_update.md" %}
# ⚙️ Funzione `fn_run_automations_audit_update`

```sql
CREATE FUNCTION fn_run_automations_audit_update(p_exec_mode text, p_schemas text[], p_dry_run boolean)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_run_automations_audit_update(p_exec_mode text, p_schemas text[], p_dry_run boolean)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
    DECLARE
  -- ⭐ Rev 2026-10-16: il contesto dell'errore, costruito una volta e usato
  --   dalle due chiamate del gestore (registro e involucro).
  v_ctx_errore dbops.error_log.context%TYPE;
      -- array: %TYPE non compone con [] (elementi: dbops.automation_scope.schema_name)
      v_schemas text[];
      rtab record;
      rrule record;
      -- la tabella del giro come OID: nessuna colonna la porta
      rel  regclass;
      -- esiti calcolati qui: nessuna colonna ne e' il riflesso
      has_du boolean;
      has_uu boolean;
      tmpl     dbops.automation_rules_tbl.name_template%TYPE;
      trg_name pg_catalog.pg_trigger.tgname%TYPE;
    BEGIN

      /*
        Scopo
        -----
        Esegue l'automazione di provisioning dei trigger "AUDIT_UPDATE" sulle tabelle in scope,
        applicando le regole abilitate in dbops.automation_rules_tbl (rule_type = 'AUDIT_UPDATE').

        Obiettivo del trigger:
        - mantenere aggiornati i campi audit (data_update, user_update, user_insert)
          ad ogni INSERT e UPDATE, secondo la convenzione di audit del database.
        - user_insert/user_update usano la GUC app.jwt_user se disponibile (JWT reale).

        Trigger generato
        ----------------
        BEFORE INSERT OR UPDATE
        EXECUTE FUNCTION script.trgfn_audit_data_user_generic()
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

        FOR rrule IN
          SELECT *
            FROM dbops.automation_rules_tbl r
          WHERE r.enabled
            AND upper(btrim(r.rule_type))='AUDIT_UPDATE'
            AND dbops.fn_schema_match(r.target_schema, rtab.schema_name)
            AND (r.target_table = '*all' OR rtab.table_name = r.target_table)
            AND (upper(btrim(r.exec_mode)) = 'AUTO' OR r.exec_mode = p_exec_mode)
          ORDER BY r.priority, r.id
        LOOP

          -- Le colonne di audit hanno nome fisso per contratto (linee-guida-sql
          -- §7): script.trgfn_audit_data_user_generic le scrive per nome.
          SELECT dbops.fn_col_exists(rtab.schema_name, rtab.table_name, 'data_update')
              , dbops.fn_col_exists(rtab.schema_name, rtab.table_name, 'user_update')
            INTO has_du, has_uu;

          IF has_du AND has_uu THEN
            tmpl     := rrule.name_template;
            trg_name := dbops.fn_name_from_template(tmpl, rtab.schema_name, rtab.table_name, NULL,NULL,NULL,NULL);

            IF NOT dbops.fn_trigger_exists_by_function(rel, 'script', 'trgfn_audit_data_user_generic')
            THEN
              IF p_dry_run THEN

                  PERFORM dbops.fn_audit_log_once(
                  p_function_name => 'dbops.fn_run_automations_audit_update',
                  p_status        => 'DRYRUN',
                  p_rule_type     => 'AUDIT_UPDATE',
                  p_exec_mode     => p_exec_mode,
                  p_parts         => ARRAY['AUDIT_UPDATE'],
                  p_dry_run       => true,
                  p_params        => jsonb_build_object(
                                      'table', rtab.schema_name||'.'||rtab.table_name,
                                      'trigger', trg_name,
                                      'action', 'DRYRUN_CREATE_TRIGGER'
                                    ),
                  p_message       => 'Trigger would be created'
                );

              ELSE
                BEGIN
                  EXECUTE format($f$
                    CREATE TRIGGER %I
                    BEFORE INSERT OR UPDATE ON %I.%I
                    FOR EACH ROW
                    EXECUTE FUNCTION script.trgfn_audit_data_user_generic()
                  $f$, trg_name, rtab.schema_name, rtab.table_name);
                EXCEPTION WHEN others THEN

                    -- ⭐ Rev 2026-10-16 (brief-db-presidio-job-run-a-chi-tocca D8, D10, D11):
                    --   un guasto dell'AMBIENTE (script.fn_sqlstate_di_ambiente: connessione,
                    --   risorse, arresto, sistema, privilegio, lock) si rilancia COM'E', col suo
                    --   SQLSTATE: l'involucro lo faceva diventare P0001, e il presidio dei job lo
                    --   mandava allo sviluppo. Prima si scrive nel registro errori, col contesto.
                    v_ctx_errore := jsonb_build_object(
                        'where','AUDIT_UPDATE',
                        'table', rtab.schema_name||'.'||rtab.table_name,
                        'error', SQLERRM
                      );
                    IF script.fn_sqlstate_di_ambiente(SQLSTATE) THEN
                      PERFORM script.fn_log_error_only(
                          'dbops', 'run_automations', 'E_AUDIT_UPDATE',
                          v_ctx_errore, NULL::uuid, SQLERRM);
                      RAISE;
                    END IF;
                    PERFORM script.fn_log_and_raise_error(
                        'dbops', 'run_automations', 'E_AUDIT_UPDATE',
                        v_ctx_errore, NULL::uuid, SQLERRM);
                END;
              END IF;
            END IF;
          END IF;
        END LOOP;
      END LOOP;
    END;

$function$

COMMENT ON FUNCTION dbops.fn_run_automations_audit_update(p_exec_mode text, p_schemas text[], p_dry_run boolean)
IS 'Automazione AUDIT_UPDATE: monta script.trgfn_audit_data_user_generic (BEFORE INSERT OR UPDATE, utente dalla GUC app.jwt_user) sulle tabelle dell''ambito che hanno data_update e user_update, secondo le regole AUDIT_UPDATE di dbops.automation_rules_tbl. Le colonne di audit hanno nome fisso: il trigger le scrive per nome. Il trigger si riconosce dalla funzione, qualunque nome abbia; il nome di uno nuovo viene dal name_template della regola. In simulazione una riga DRYRUN per trigger in dbops.audit_log, firmata col proprio nome. Un guasto dell''ambiente (script.fn_sqlstate_di_ambiente) si scrive nel registro errori e si rilancia col suo SQLSTATE; i difetti di struttura escono col codice dell''automazione.';
```

</div>

---
{% include-markdown "signature-core.md" %}
