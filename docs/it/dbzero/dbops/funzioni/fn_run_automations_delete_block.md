{% include-markdown "it/dbzero/dbops/manual/fn_run_automations_delete_block.md" %}
# ⚙️ Funzione `fn_run_automations_delete_block`

```sql
CREATE FUNCTION fn_run_automations_delete_block(p_exec_mode text, p_schemas text[], p_dry_run boolean)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_run_automations_delete_block(p_exec_mode text, p_schemas text[], p_dry_run boolean)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE
  -- Il contesto dell'errore, costruito una volta e usato dalle due
  -- chiamate del gestore (registro e involucro).
  v_ctx_errore dbops.error_log.context%TYPE;
  -- text[]: %TYPE non fa array
  v_schemas text[];
  rconf record;
  -- regclass: tipo del valore, nessuna colonna lo porta
  rel regclass;
  v_trigger_name dbops.automation_delete_block.trigger_name%TYPE;
BEGIN
  v_schemas := dbops.fn_resolve_scope(p_schemas);

  FOR rconf IN
    SELECT d.*
      FROM dbops.automation_delete_block d
     WHERE d.enabled
       AND d.schema_name = ANY(v_schemas)
       AND dbops.fn_table_in_scope(d.schema_name, d.table_name)
     ORDER BY d.id
  LOOP
    rel := to_regclass(format('%I.%I', rconf.schema_name, rconf.table_name));
    IF rel IS NULL THEN
      -- ⭐ Un salto, in tutti e due i giri: la configurazione punta a
      --   una tabella che non c'e'. dry_run dice quale giro.
      PERFORM dbops.fn_audit_log_once(
        p_function_name => 'dbops.fn_run_automations_delete_block',
        p_status        => 'WARN',
        p_rule_type     => 'DELETE_BLOCK',
        p_exec_mode     => p_exec_mode,
        p_parts         => ARRAY['DELETE_BLOCK'],
        p_dry_run       => p_dry_run,
        p_params        => jsonb_build_object(
                            'action','SKIP',
                            'reason','TABLE_NOT_FOUND',
                            'table', rconf.schema_name||'.'||rconf.table_name
                          ),
        p_message       => 'Skip: table not found'
      );
      CONTINUE;
    END IF;

    -- Lo stesso nome che calcola fn_apply_delete_block_trigger.
    v_trigger_name := COALESCE(
      NULLIF(rconf.trigger_name, ''),
      format('trg_%s_a10_delete_block_dlt', rconf.table_name)
    );

    IF dbops.fn_trigger_exists_by_name(rel, v_trigger_name) THEN
      CONTINUE;
    END IF;

    IF p_dry_run THEN
      PERFORM dbops.fn_audit_log_once(
        p_function_name => 'dbops.fn_run_automations_delete_block',
        p_status        => 'DRYRUN',
        p_rule_type     => 'DELETE_BLOCK',
        p_exec_mode     => p_exec_mode,
        p_parts         => ARRAY['DELETE_BLOCK'],
        p_dry_run       => true,
        p_params        => jsonb_build_object(
                            'table', rconf.schema_name||'.'||rconf.table_name,
                            'trigger', v_trigger_name,
                            'guc_key', rconf.guc_key,
                            'action','DRYRUN_CREATE_TRIGGER'
                          ),
        p_message       => 'Trigger would be created'
      );
    ELSE
      BEGIN
        PERFORM dbops.fn_apply_delete_block_trigger(
          rconf.schema_name,
          rconf.table_name,
          rconf.guc_key,
          rconf.trigger_name
        );
      EXCEPTION WHEN others THEN
        -- ⭐ Un guasto dell'AMBIENTE (script.fn_sqlstate_di_ambiente:
        --   connessione, risorse, arresto, sistema, privilegio, lock) si
        --   rilancia COM'E', col suo SQLSTATE: l'involucro lo faceva
        --   diventare P0001, e il presidio dei job lo mandava allo
        --   sviluppo. Prima si scrive nel registro errori, col contesto.
        --   Brief: brief-db-presidio-job-run-a-chi-tocca D8, D10, D11.
        v_ctx_errore := jsonb_build_object(
            'where','DELETE_BLOCK',
            'table', rconf.schema_name||'.'||rconf.table_name,
            'error', SQLERRM
          );
        IF script.fn_sqlstate_di_ambiente(SQLSTATE) THEN
          PERFORM script.fn_log_error_only(
              'dbops', 'run_automations', 'E_DELETE_BLOCK',
              v_ctx_errore, NULL::uuid, SQLERRM);
          RAISE;
        END IF;
        PERFORM script.fn_log_and_raise_error(
            'dbops', 'run_automations', 'E_DELETE_BLOCK',
            v_ctx_errore, NULL::uuid, SQLERRM);
      END;

      -- ⭐ Il giro vero lascia traccia: qui il trigger c'e' (se la
      --   creazione fosse fallita, il blocco avrebbe sollevato).
      PERFORM dbops.fn_audit_log_once(
        p_function_name => 'dbops.fn_run_automations_delete_block',
        p_status        => 'OK',
        p_rule_type     => 'DELETE_BLOCK',
        p_exec_mode     => p_exec_mode,
        p_parts         => ARRAY['DELETE_BLOCK'],
        p_dry_run       => false,
        p_params        => jsonb_build_object(
                            'table', rconf.schema_name||'.'||rconf.table_name,
                            'trigger', v_trigger_name,
                            'guc_key', rconf.guc_key,
                            'action','CREATE_TRIGGER'
                          ),
        p_message       => 'Trigger created'
      );
    END IF;
  END LOOP;
END;
$function$

COMMENT ON FUNCTION dbops.fn_run_automations_delete_block(p_exec_mode text, p_schemas text[], p_dry_run boolean)
IS 'Applica i trigger DELETE_BLOCK configurati in dbops.automation_delete_block, sulle tabelle in ambito. Ogni azione lascia una riga in dbops.audit_log: OK quando il giro vero crea il trigger, DRYRUN quando il dry run lo creerebbe, WARN TABLE_NOT_FOUND in tutti e due i giri quando la tabella configurata non esiste. Un trigger gia'' presente non e'' un''azione e non si registra. Il nome del trigger si calcola come in dbops.fn_apply_delete_block_trigger. Nel gestore WHEN others un guasto dell''AMBIENTE (script.fn_sqlstate_di_ambiente: 08, 53, 57, 58, 42501, 55P03) si rilancia com''e'', col suo SQLSTATE, dopo averlo scritto nel registro errori (fn_log_error_only); gli altri errori escono da fn_log_and_raise_error con E_DELETE_BLOCK.';
```

</div>

---
{% include-markdown "signature-core.md" %}
