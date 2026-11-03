{% include-markdown "it/dbzero/dbops/manual/fn_run_automations_date_validita.md" %}
# ⚙️ Funzione `fn_run_automations_date_validita`

```sql
CREATE FUNCTION fn_run_automations_date_validita(p_exec_mode text, p_schemas text[], p_dry_run boolean)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_run_automations_date_validita(p_exec_mode text, p_schemas text[], p_dry_run boolean)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
/*
  Scopo
  -----
  Automazione DATE_VALIDITA: su ogni tabella dello scope che porta
  le colonne `valido_dal` e `valido_al` monta il guard della regola
  del periodo:
    BEFORE INSERT OR UPDATE OF valido_dal, valido_al
    FOR EACH ROW EXECUTE FUNCTION script.trgfn_guard_date_validita()

  Regole di selezione
  -------------------
  - la sola presenza delle due colonne (niente registro per tabella:
    la regola e' della coppia, non della tabella);
  - lo schema `storico` e' escluso: le tabelle ombra ricordano, non
    si giudicano.

  Idempotenza
  -----------
  Esistenza secondo la regola (BY_NAME / BY_FUNCTION / BOTH). Il nome
  oltre i 63 caratteri PostgreSQL lo tronca: con BOTH il trigger si
  riconosce comunque dalla funzione.

  Dry run
  -------
  p_dry_run = true: nessuna DDL, una riga di audit per tabella.
*/
DECLARE
  -- ⭐ Rev 2026-10-16: il contesto dell'errore, costruito una volta e usato
  --   dalle due chiamate del gestore (registro e involucro).
  v_ctx_errore dbops.error_log.context%TYPE;
    v_schemas   text[];
    rtab        record;
    rrule       record;
    trg_name    text;
    exist_strat text;
    created     boolean;
BEGIN
    v_schemas := dbops.fn_resolve_scope(p_schemas);

    FOR rtab IN
        SELECT n.nspname AS schema_name,
               c.relname AS table_name,
               c.oid::regclass AS rel
          FROM pg_class c
          JOIN pg_namespace n ON n.oid = c.relnamespace
         WHERE c.relkind = 'r'
           AND n.nspname = ANY(v_schemas)
           AND n.nspname <> 'storico'
           AND dbops.fn_table_in_scope(n.nspname, c.relname)
           AND dbops.fn_col_exists(n.nspname, c.relname, 'valido_dal')
           AND dbops.fn_col_exists(n.nspname, c.relname, 'valido_al')
         ORDER BY n.nspname, c.relname
    LOOP
        created := false;

        FOR rrule IN
            SELECT *
              FROM dbops.automation_rules_tbl r
             WHERE r.enabled
               AND upper(btrim(r.rule_type)) = 'DATE_VALIDITA'
               AND dbops.fn_schema_match(r.target_schema, rtab.schema_name)
               AND (upper(r.target_table) = '*ALL' OR rtab.table_name ILIKE r.target_table)
               AND (upper(btrim(r.exec_mode)) = 'AUTO' OR r.exec_mode = p_exec_mode)
             ORDER BY r.priority, r.id
        LOOP
            EXIT WHEN created;
            exist_strat := COALESCE(rrule.existence_strategy, 'BOTH');
            trg_name := dbops.fn_name_from_template(
                            COALESCE(rrule.name_template, 'trg_{table}_a10_date_validita_ins_upd'),
                            rtab.schema_name, rtab.table_name,
                            NULL, NULL, NULL, NULL);

            IF (exist_strat = 'BY_NAME'     AND NOT dbops.fn_trigger_exists_by_name(rtab.rel, trg_name))
            OR (exist_strat = 'BY_FUNCTION' AND NOT dbops.fn_trigger_exists_by_function(rtab.rel, 'script', 'trgfn_guard_date_validita'))
            OR (exist_strat = 'BOTH'        AND NOT (dbops.fn_trigger_exists_by_name(rtab.rel, trg_name)
                                              OR dbops.fn_trigger_exists_by_function(rtab.rel, 'script', 'trgfn_guard_date_validita')))
            THEN
                IF p_dry_run THEN
                    PERFORM dbops.fn_audit_log_once(
                        p_function_name => 'dbops.fn_run_automations',
                        p_status        => 'DRYRUN',
                        p_rule_type     => 'DATE_VALIDITA',
                        p_exec_mode     => p_exec_mode,
                        p_parts         => ARRAY['DATE_VALIDITA'],
                        p_dry_run       => true,
                        p_params        => jsonb_build_object(
                                             'table',   rtab.schema_name || '.' || rtab.table_name,
                                             'trigger', trg_name,
                                             'action',  'DRYRUN_CREATE_TRIGGER'),
                        p_message       => 'Trigger would be created'
                    );
                ELSE
                    BEGIN
                        EXECUTE format($f$
                            CREATE TRIGGER %I
                            BEFORE INSERT OR UPDATE OF valido_dal, valido_al ON %I.%I
                            FOR EACH ROW
                            EXECUTE FUNCTION script.trgfn_guard_date_validita()
                        $f$, trg_name, rtab.schema_name, rtab.table_name);
                    EXCEPTION WHEN others THEN
                        -- ⭐ Rev 2026-10-16 (brief-db-presidio-job-run-a-chi-tocca D8, D10, D11):
                        --   un guasto dell'AMBIENTE (script.fn_sqlstate_di_ambiente: connessione,
                        --   risorse, arresto, sistema, privilegio, lock) si rilancia COM'E', col suo
                        --   SQLSTATE: l'involucro lo faceva diventare P0001, e il presidio dei job lo
                        --   mandava allo sviluppo. Prima si scrive nel registro errori, col contesto.
                        v_ctx_errore := jsonb_build_object(
                                'where', 'DATE_VALIDITA',
                                'table', rtab.schema_name || '.' || rtab.table_name,
                                'error', SQLERRM);
                        IF script.fn_sqlstate_di_ambiente(SQLSTATE) THEN
                          PERFORM script.fn_log_error_only(
                              'dbops', 'run_automations', 'E_DATE_VALIDITA',
                              v_ctx_errore, NULL::uuid, rtab.schema_name || '.' || rtab.table_name, SQLERRM);
                          RAISE;
                        END IF;
                        PERFORM script.fn_log_and_raise_error(
                            'dbops', 'run_automations', 'E_DATE_VALIDITA',
                            v_ctx_errore, NULL::uuid, rtab.schema_name || '.' || rtab.table_name, SQLERRM);
                    END;
                END IF;
            END IF;
            -- Una regola applicata basta, anche se il trigger c'era gia'.
            created := true;
        END LOOP;
    END LOOP;
END;
$function$

COMMENT ON FUNCTION dbops.fn_run_automations_date_validita(p_exec_mode text, p_schemas text[], p_dry_run boolean)
IS 'Automazione DATE_VALIDITA: su ogni tabella dello scope che porta valido_dal e valido_al monta script.trgfn_guard_date_validita (BEFORE INSERT OR UPDATE OF valido_dal, valido_al), secondo la regola DATE_VALIDITA di dbops.automation_rules_tbl. ⭐ La regola e'' della COPPIA di colonne, non della tabella: la sola presenza basta, come il lock di codice_interno, e una tabella nuova nasce presidiata. ⚠️ Esclude lo schema storico (le tabelle ombra ricordano, non si giudicano). Esistenza BY_NAME / BY_FUNCTION / BOTH: con BOTH un nome troncato oltre i 63 caratteri si riconosce dalla funzione. Dry run con audit; errore strutturato E_DATE_VALIDITA. Chiamata a ogni migrate (90_end, runAlways) e dal job notturno automations_lock_columns. Brief: brief-db-guard-date-validita.md ⭐ Rev 2026-10-16: nel gestore WHEN others, un guasto dell''AMBIENTE (script.fn_sqlstate_di_ambiente: 08, 53, 57, 58, 42501, 55P03) si rilancia COM''E'', col suo SQLSTATE, dopo averlo scritto nel registro errori con lo stesso codice e contesto (fn_log_error_only). Prima diventava P0001 col codice dell''involucro, e il presidio dei job (maintenance.vw_job_run_da_guardare) lo mandava allo sviluppo. I difetti di struttura escono come prima. Brief: brief-db-presidio-job-run-a-chi-tocca D8, D11.';
```

</div>

---
{% include-markdown "signature-core.md" %}
