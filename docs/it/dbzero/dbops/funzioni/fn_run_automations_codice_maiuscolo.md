{% include-markdown "it/dbzero/dbops/manual/fn_run_automations_codice_maiuscolo.md" %}
# ⚙️ Funzione `fn_run_automations_codice_maiuscolo`

```sql
CREATE FUNCTION fn_run_automations_codice_maiuscolo(p_exec_mode text, p_schemas text[], p_dry_run boolean)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_run_automations_codice_maiuscolo(p_exec_mode text, p_schemas text[], p_dry_run boolean)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
/*
  Scopo
  -----
  Automazione CODICE_MAIUSCOLO: porta i trigger
    BEFORE INSERT OR UPDATE FOR EACH ROW
    EXECUTE FUNCTION script.trgfn_codice_maiuscolo()
  allo stato che dbops.fn_codice_maiuscolo_perimetro dichiara.

  Azioni
  ------
  CREA      il trigger col nome dal template della regola
  RIGENERA  toglie tutti i trigger vivi sulla funzione, crea quello atteso
  TOGLIE    toglie tutti i trigger vivi (eccezione, colonna tolta,
            tabella fuori ambito)

  Regola
  ------
  CREA e RIGENERA chiedono una regola CODICE_MAIUSCOLO accesa in
  dbops.automation_rules_tbl che copra schema e tabella: da li' il
  template del nome. Senza, la tabella non si tocca (audit WARN
  NO_RULE). TOGLIE non chiede regola.

  DRY RUN
  -------
  p_dry_run = true: nessuna DDL, una riga di audit DRYRUN per azione.
*/
DECLARE
    v_ctx_errore dbops.error_log.context%TYPE;
    r            record;
    v_template   dbops.automation_rules_tbl.name_template%TYPE;
    v_nome       pg_catalog.pg_trigger.tgname%TYPE;
    v_trg        pg_catalog.pg_trigger.tgname%TYPE;
BEGIN
    FOR r IN
        SELECT d.*
          FROM dbops.fn_codice_maiuscolo_perimetro(p_schemas) AS d
         WHERE d.azione IS NOT NULL
         ORDER BY d.schema_name, d.table_name
    LOOP
        v_nome := NULL;

        IF r.azione IN ('CREA', 'RIGENERA') THEN
            SELECT rr.name_template
              INTO v_template
              FROM dbops.automation_rules_tbl rr
             WHERE rr.enabled
               AND upper(btrim(rr.rule_type)) = 'CODICE_MAIUSCOLO'
               AND dbops.fn_schema_match(rr.target_schema, r.schema_name)
               AND (upper(rr.target_table) = '*ALL' OR r.table_name ILIKE rr.target_table)
               AND (upper(btrim(rr.exec_mode)) = 'AUTO' OR rr.exec_mode = p_exec_mode)
             ORDER BY rr.priority, rr.id
             LIMIT 1;

            IF NOT FOUND THEN
                PERFORM dbops.fn_audit_log_once(
                    p_function_name => 'dbops.fn_run_automations_codice_maiuscolo',
                    p_status        => 'WARN',
                    p_rule_type     => 'CODICE_MAIUSCOLO',
                    p_exec_mode     => p_exec_mode,
                    p_parts         => ARRAY['CODICE_MAIUSCOLO'],
                    p_dry_run       => p_dry_run,
                    p_params        => jsonb_build_object(
                                         'table',  r.schema_name || '.' || r.table_name,
                                         'action', 'NO_RULE'),
                    p_message       => 'Nessuna regola CODICE_MAIUSCOLO accesa: tabella non toccata'
                );
                CONTINUE;
            END IF;

            v_nome := dbops.fn_name_from_template(
                          COALESCE(NULLIF(btrim(v_template), ''),
                                   'trg_{table}_a15_codice_maiuscolo_ins_upd'),
                          r.schema_name, r.table_name,
                          NULL, NULL, NULL, NULL);
        END IF;

        IF p_dry_run THEN
            PERFORM dbops.fn_audit_log_once(
                p_function_name => 'dbops.fn_run_automations_codice_maiuscolo',
                p_status        => 'DRYRUN',
                p_rule_type     => 'CODICE_MAIUSCOLO',
                p_exec_mode     => p_exec_mode,
                p_parts         => ARRAY['CODICE_MAIUSCOLO'],
                p_dry_run       => true,
                p_params        => jsonb_build_object(
                                     'table',        r.schema_name || '.' || r.table_name,
                                     'trigger',      v_nome,
                                     'trigger_vivi', r.trigger_vivi,
                                     'action',       'DRYRUN_' || r.azione),
                p_message       => 'Codice maiuscolo: ' || r.azione
            );
            CONTINUE;
        END IF;

        BEGIN
            FOREACH v_trg IN ARRAY r.trigger_vivi LOOP
                EXECUTE format('DROP TRIGGER IF EXISTS %I ON %I.%I',
                               v_trg, r.schema_name, r.table_name);
            END LOOP;

            IF r.azione IN ('CREA', 'RIGENERA') THEN
                EXECUTE format($f$
                    CREATE TRIGGER %I
                    BEFORE INSERT OR UPDATE ON %I.%I
                    FOR EACH ROW
                    EXECUTE FUNCTION script.trgfn_codice_maiuscolo()
                $f$, v_nome, r.schema_name, r.table_name);
            END IF;
        EXCEPTION WHEN others THEN
            -- Un guasto dell'AMBIENTE (script.fn_sqlstate_di_ambiente:
            -- connessione, risorse, arresto, sistema, privilegio, lock) si
            -- rilancia COM'E', col suo SQLSTATE, dopo averlo scritto nel
            -- registro errori; un difetto di struttura esce col codice
            -- dell'automazione (stessa forma dei runner gemelli).
            v_ctx_errore := jsonb_build_object(
                    'where',  'CODICE_MAIUSCOLO',
                    'table',  r.schema_name || '.' || r.table_name,
                    'azione', r.azione,
                    'error',  SQLERRM);
            IF script.fn_sqlstate_di_ambiente(SQLSTATE) THEN
                PERFORM script.fn_log_error_only(
                    'dbops', 'fn_run_automations_codice_maiuscolo', 'E_CODICE_MAIUSCOLO',
                    v_ctx_errore, NULL::uuid,
                    r.schema_name || '.' || r.table_name, SQLERRM);
                RAISE;
            END IF;
            PERFORM script.fn_log_and_raise_error(
                'dbops', 'fn_run_automations_codice_maiuscolo', 'E_CODICE_MAIUSCOLO',
                v_ctx_errore, NULL::uuid,
                r.schema_name || '.' || r.table_name, SQLERRM);
        END;

        PERFORM dbops.fn_audit_log_once(
            p_function_name => 'dbops.fn_run_automations_codice_maiuscolo',
            p_status        => 'OK',
            p_rule_type     => 'CODICE_MAIUSCOLO',
            p_exec_mode     => p_exec_mode,
            p_parts         => ARRAY['CODICE_MAIUSCOLO'],
            p_dry_run       => false,
            p_params        => jsonb_build_object(
                                 'table',        r.schema_name || '.' || r.table_name,
                                 'trigger',      v_nome,
                                 'trigger_vivi', r.trigger_vivi,
                                 'action',       r.azione),
            p_message       => 'Codice maiuscolo: ' || r.azione
        );

        RAISE NOTICE 'CODICE_MAIUSCOLO: % %.% (vivi: %; atteso: %)',
            r.azione, r.schema_name, r.table_name,
            COALESCE(array_to_string(r.trigger_vivi, ', '), ''),
            COALESCE(v_nome, '');
    END LOOP;
END;
$function$

COMMENT ON FUNCTION dbops.fn_run_automations_codice_maiuscolo(p_exec_mode text, p_schemas text[], p_dry_run boolean)
IS 'Automazione CODICE_MAIUSCOLO: porta i trigger script.trgfn_codice_maiuscolo (BEFORE INSERT OR UPDATE FOR EACH ROW) allo stato di dbops.fn_codice_maiuscolo_perimetro: CREA dove e'' dovuto e manca, RIGENERA dove ce n''e'' piu'' di uno, TOGLIE dove non e'' dovuto (un''eccezione di dbops.automazione_codice_eccezioni, una colonna tolta, una tabella fuori ambito). Regola per esclusione: ogni colonna codice dell''ambito, tranne le eccezioni. Il nome viene dal template della regola CODICE_MAIUSCOLO di dbops.automation_rules_tbl, che e'' anche l''interruttore: senza regola accesa la tabella non si tocca (audit WARN NO_RULE) e la convergenza del migrate si ferma. Il trigger vivo si riconosce dalla funzione, mai dal nome. Dry run con audit DRYRUN; nel giro vero audit OK per azione. Errore strutturato E_CODICE_MAIUSCOLO; un guasto dell''ambiente (script.fn_sqlstate_di_ambiente) si rilancia col suo SQLSTATE. Chiamata a ogni migrate (90_end, runAlways) e dal job notturno automations_lock_columns.';
```

</div>

---
{% include-markdown "signature-core.md" %}
