{% include-markdown "it/dbzero/dbops/manual/fn_run_automations_tx_id.md" %}
# ⚙️ Funzione `fn_run_automations_tx_id`

```sql
CREATE FUNCTION fn_run_automations_tx_id(p_exec_mode text, p_schemas text[], p_dry_run boolean)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_run_automations_tx_id(p_exec_mode text, p_schemas text[], p_dry_run boolean)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE
  -- ⭐ Rev 2026-10-16: il contesto dell'errore, costruito una volta e usato
  --   dalle due chiamate del gestore (registro e involucro).
  v_ctx_errore dbops.error_log.context%TYPE;
  v_schemas text[];
  rtab record;
  rrule record;
  rel  regclass;
  has_txid boolean;
  tmpl     text;
  trg_name text;
  exist_strat text;
BEGIN


/*
  Scopo
  -----
  Esegue l'automazione di provisioning dei trigger "TX_ID managed" sulle tabelle in scope,
  applicando le regole abilitate in dbops.automation_rules_tbl di tipo 'TX_ID'.

  La funzione:
  1) risolve lo scope degli schemi (dbops.fn_resolve_scope),
  2) scorre tutte le tabelle fisiche (pg_class.relkind='r') degli schemi target
    filtrate da dbops.fn_table_in_scope(schema, table),
  3) per ogni tabella applica le regole TX_ID compatibili con:
    - enabled = true
    - rule_type = 'TX_ID'
    - exec_mode = 'AUTO' oppure exec_mode = p_exec_mode
    - match su schema (dbops.fn_schema_match)
    - match su tabella: '*ALL' oppure pattern ILIKE su r.target_table
  4) verifica la pre-condizione tecnica: la tabella deve avere una colonna tx_id di tipo uuid
    (information_schema.columns).
    Se la colonna non esiste, la tabella viene ignorata (non crea colonne, crea solo trigger).

  Trigger generato
  ----------------
  Per le tabelle idonee, la funzione assicura l'esistenza del trigger:
    BEFORE INSERT OR UPDATE
    EXECUTE FUNCTION dbops.trgfn_tx_id_managed()
  Il nome del trigger è derivato da un template:
    - rrule.name_template (default: 'trg_{table}_gen_tx_id_ins_upd')
    - dbops.fn_name_from_template per generare un nome coerente e standardizzato.

  Esistenza trigger / strategie
  -----------------------------
  La creazione del trigger è condizionata da rrule.existence_strategy (default 'BY_NAME'):
  - BY_NAME     : verifica esistenza per nome trigger
  - BY_FUNCTION : verifica esistenza per funzione trigger (dbops.trgfn_tx_id_managed)
  - BOTH        : considera presente se esiste per nome OR per funzione
  Questo consente migrazioni controllate e previene duplicazioni.

  Modalità DRY RUN
  ---------------
  Se p_dry_run=true non esegue DDL (CREATE TRIGGER) e registra invece un audit
  con dbops.fn_audit_log_once indicando cosa verrebbe creato.

  Error handling
  --------------
  In caso di errore nella creazione del trigger, log strutturato e rilancio tramite
  script.fn_log_and_raise_error includendo tabella, contesto ('TX_ID') e SQLERRM.
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
        AND upper(btrim(r.rule_type))='TX_ID'
        AND dbops.fn_schema_match(r.target_schema, rtab.schema_name)
        AND (UPPER(r.target_table) = '*ALL' OR rtab.table_name ILIKE r.target_table)
        --AND (r.exec_mode='AUTO' OR r.exec_mode=p_exec_mode)
        AND (upper(btrim(r.exec_mode)) = 'AUTO' OR r.exec_mode = p_exec_mode)
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
        tmpl     := COALESCE(rrule.name_template,'trg_{table}_gen_tx_id_ins_upd');
        trg_name := dbops.fn_name_from_template(tmpl, rtab.schema_name, rtab.table_name, NULL,NULL,NULL,NULL);

        IF (exist_strat='BY_NAME'     AND NOT dbops.fn_trigger_exists_by_name(rel, trg_name))
        OR (exist_strat='BY_FUNCTION' AND NOT dbops.fn_trigger_exists_by_function(rel,'dbops','trgfn_tx_id_managed'))
        OR (exist_strat='BOTH'        AND NOT (dbops.fn_trigger_exists_by_name(rel, trg_name)
                                          OR dbops.fn_trigger_exists_by_function(rel,'dbops','trgfn_tx_id_managed')))
        THEN
          IF p_dry_run THEN

            PERFORM dbops.fn_audit_log_once(
                  p_function_name => 'dbops.fn_run_automations',
                  p_status        => 'DRYRUN',
                  p_rule_type     => 'E_TX_ID',
                  p_exec_mode     => p_exec_mode,
                  p_parts         => ARRAY['TX_ID'],
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
                EXECUTE FUNCTION dbops.trgfn_tx_id_managed()
              $f$, trg_name, rtab.schema_name, rtab.table_name);
            EXCEPTION WHEN others THEN
                -- ⭐ Rev 2026-10-16 (brief-db-presidio-job-run-a-chi-tocca D8, D10, D11):
                --   un guasto dell'AMBIENTE (script.fn_sqlstate_di_ambiente: connessione,
                --   risorse, arresto, sistema, privilegio, lock) si rilancia COM'E', col suo
                --   SQLSTATE: l'involucro lo faceva diventare P0001, e il presidio dei job lo
                --   mandava allo sviluppo. Prima si scrive nel registro errori, col contesto.
                v_ctx_errore := jsonb_build_object(
                    'where','TX_ID',
                    'table', rtab.schema_name||'.'||rtab.table_name,
                    'error', SQLERRM
                  );
                IF script.fn_sqlstate_di_ambiente(SQLSTATE) THEN
                  PERFORM script.fn_log_error_only(
                      'dbops', 'run_automations', 'E_TX_ID',
                      v_ctx_errore, NULL::uuid, SQLERRM);
                  RAISE;
                END IF;
                PERFORM script.fn_log_and_raise_error(
                    'dbops', 'run_automations', 'E_TX_ID',
                    v_ctx_errore, NULL::uuid, SQLERRM);

            END;
          END IF;
        END IF;
      END IF;
    END LOOP;
  END LOOP;
END;
$function$

COMMENT ON FUNCTION dbops.fn_run_automations_tx_id(p_exec_mode text, p_schemas text[], p_dry_run boolean)
IS 'Crea i trigger TX_ID dove esiste tx_id UUID. ⭐ Rev 2026-10-16: nel gestore WHEN others, un guasto dell''AMBIENTE (script.fn_sqlstate_di_ambiente: 08, 53, 57, 58, 42501, 55P03) si rilancia COM''E'', col suo SQLSTATE, dopo averlo scritto nel registro errori con lo stesso codice e contesto (fn_log_error_only). Prima diventava P0001 col codice dell''involucro, e il presidio dei job (maintenance.vw_job_run_da_guardare) lo mandava allo sviluppo. I difetti di struttura escono come prima. Brief: brief-db-presidio-job-run-a-chi-tocca D8, D11.';
```

</div>

---
{% include-markdown "signature-core.md" %}
