{% include-markdown "it/dbzero/dbops/manual/fn_run_automations_lock_columns.md" %}
# ⚙️ Funzione `fn_run_automations_lock_columns`

```sql
CREATE FUNCTION fn_run_automations_lock_columns(p_exec_mode text, p_schemas text[], p_dry_run boolean)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_run_automations_lock_columns(p_exec_mode text, p_schemas text[], p_dry_run boolean)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
/*
  Scopo
  -----
  Porta i trigger LOCK_COLUMNS (script.trgfn_lock_columns) delle tabelle in
  scope allo stato che il registro dichiara:
  - codice_interno, se presente in tabella (implicito);
  - colonne extra attive in dbops.automation_lock_columns.
  Il confronto fra atteso e vivo lo fa dbops.fn_lock_columns_divergenze:
  qui si esegue l'azione di ogni riga.

  Azioni
  ------
  CREA      trigger unico col nome da template (dbops.automation_rules_tbl)
  RIGENERA  toglie tutti i lock vivi della tabella, qualunque nome abbiano,
            e crea quello atteso
  TOGLIE    toglie tutti i lock vivi (nessuna colonna da bloccare)

  Colonne fuori dal registro
  --------------------------
  Una colonna bloccata dal vivo che il registro non nomina affatto ferma il
  giro con E_LOCK_COLUMNS, prima di qualunque DDL: convergere la
  cancellerebbe in silenzio. Si aggiunge la riga (enabled = false se il
  blocco va tolto).

  DRY RUN
  -------
  p_dry_run = true: nessuna DDL, azione e colonne perse nell'audit
  (dbops.fn_audit_log_once).
*/
DECLARE
  -- ⭐ Rev 2026-10-16: il contesto dell'errore, costruito una volta e usato
  --   dalle due chiamate del gestore (registro e involucro).
  v_ctx_errore dbops.error_log.context%TYPE;
    r        record;
    v_trg    text;
    v_cols   text;
    v_args   text;
    v_perse  text;
BEGIN
    -- ⭐ Prima di qualunque DDL, e per TUTTE le tabelle insieme: un lock nato
    --    fuori dal registro non si cancella. Chi lancia la migrate riceve
    --    l'elenco intero, non la prima tabella.
    IF NOT p_dry_run THEN
        SELECT string_agg(d.schema_name||'.'||d.table_name||' ('||array_to_string(d.colonne_perse, ', ')||')',
                          '; ' ORDER BY d.schema_name, d.table_name)
          INTO v_perse
          FROM dbops.fn_lock_columns_divergenze(p_exec_mode, p_schemas) AS d
         WHERE cardinality(d.colonne_perse) > 0;

        IF v_perse IS NOT NULL THEN
            PERFORM script.fn_log_and_raise_error(
                'database',
                'dbops.fn_run_automations_lock_columns',
                'E_LOCK_COLUMNS',
                jsonb_build_object('where', 'LOCK_COLUMNS_FUORI_REGISTRO', 'tabelle', v_perse),
                NULL::uuid,
                format('colonne bloccate da un trigger che il registro dbops.automation_lock_columns '
                       'non nomina: %s. Aggiungere le righe (enabled = false se il blocco va tolto) '
                       'prima di convergere', v_perse)
            );
        END IF;
    END IF;

    FOR r IN
        SELECT d.*
          FROM dbops.fn_lock_columns_divergenze(p_exec_mode, p_schemas) AS d
         ORDER BY d.schema_name, d.table_name
    LOOP
        IF p_dry_run THEN
            PERFORM dbops.fn_audit_log_once(
                p_function_name => 'dbops.fn_run_automations',
                p_status        => 'DRYRUN',
                p_rule_type     => 'LOCK_COLUMNS',
                p_exec_mode     => p_exec_mode,
                p_parts         => ARRAY['LOCK_COLUMNS'],
                p_dry_run       => true,
                p_params        => jsonb_build_object(
                                    'table',         r.schema_name||'.'||r.table_name,
                                    'trigger',       r.trigger_atteso,
                                    'columns',       r.colonne_attese,
                                    'trigger_vivi',  r.trigger_vivi,
                                    'colonne_perse', r.colonne_perse,
                                    'action',        'DRYRUN_'||r.azione
                                  ),
                p_message       => 'Lock columns: '||r.azione
            );
            CONTINUE;
        END IF;

        BEGIN
            FOREACH v_trg IN ARRAY r.trigger_vivi LOOP
                EXECUTE format('DROP TRIGGER IF EXISTS %I ON %I.%I',
                               v_trg, r.schema_name, r.table_name);
            END LOOP;

            IF r.azione IN ('CREA', 'RIGENERA') THEN
                SELECT string_agg(quote_ident(c), ', ' ORDER BY i)
                  INTO v_cols
                  FROM unnest(r.colonne_attese) WITH ORDINALITY AS u(c, i);
                SELECT string_agg(quote_literal(a), ', ' ORDER BY i)
                  INTO v_args
                  FROM unnest(r.argomenti_attesi) WITH ORDINALITY AS u(a, i);

                EXECUTE format($f$
                  CREATE TRIGGER %I
                  BEFORE UPDATE OF %s ON %I.%I
                  FOR EACH ROW
                  EXECUTE FUNCTION script.trgfn_lock_columns(%s)
                $f$, r.trigger_atteso, v_cols, r.schema_name, r.table_name, v_args);
            END IF;
        EXCEPTION WHEN others THEN
            -- ⭐ Rev 2026-10-16 (brief-db-presidio-job-run-a-chi-tocca D8, D10, D11):
            --   un guasto dell'AMBIENTE (script.fn_sqlstate_di_ambiente: connessione,
            --   risorse, arresto, sistema, privilegio, lock) si rilancia COM'E', col suo
            --   SQLSTATE: l'involucro lo faceva diventare P0001, e il presidio dei job lo
            --   mandava allo sviluppo. Prima si scrive nel registro errori, col contesto.
            v_ctx_errore := jsonb_build_object(
                    'where',  'LOCK_COLUMNS',
                    'table',  r.schema_name||'.'||r.table_name,
                    'azione', r.azione,
                    'error',  SQLERRM
                );
            IF script.fn_sqlstate_di_ambiente(SQLSTATE) THEN
              PERFORM script.fn_log_error_only(
                  'database', 'dbops.fn_run_automations_lock_columns', 'E_LOCK_COLUMNS',
                  v_ctx_errore, NULL::uuid, SQLERRM);
              RAISE;
            END IF;
            PERFORM script.fn_log_and_raise_error(
                'database', 'dbops.fn_run_automations_lock_columns', 'E_LOCK_COLUMNS',
                v_ctx_errore, NULL::uuid, SQLERRM);
        END;

        RAISE NOTICE 'LOCK_COLUMNS: % %.% (vivi: %; attese: %)',
            r.azione, r.schema_name, r.table_name,
            COALESCE(array_to_string(r.trigger_vivi, ', '), ''),
            COALESCE(array_to_string(r.colonne_attese, ', '), '');
    END LOOP;
END;
$function$

COMMENT ON FUNCTION dbops.fn_run_automations_lock_columns(p_exec_mode text, p_schemas text[], p_dry_run boolean)
IS 'Converge i trigger di lock columns (script.trgfn_lock_columns) verso lo stato dichiarato: codice_interno implicito + colonne attive di dbops.automation_lock_columns. Crea, rigenera (anche i lock scritti a mano, qualunque nome abbiano) o toglie, secondo dbops.fn_lock_columns_divergenze. Si ferma con E_LOCK_COLUMNS, prima di qualunque DDL, se una colonna bloccata non e'' nominata dal registro. Rev 20260926-04: assorbe dbops.fn_run_automations_drop_lock_trg (ritirata). Brief: brief-db-lock-di-colonna-fuori-registro §4 D2. ⭐ Rev 2026-10-16: nel gestore WHEN others, un guasto dell''AMBIENTE (script.fn_sqlstate_di_ambiente: 08, 53, 57, 58, 42501, 55P03) si rilancia COM''E'', col suo SQLSTATE, dopo averlo scritto nel registro errori con lo stesso codice e contesto (fn_log_error_only). Prima diventava P0001 col codice dell''involucro, e il presidio dei job (maintenance.vw_job_run_da_guardare) lo mandava allo sviluppo. I difetti di struttura escono come prima. Brief: brief-db-presidio-job-run-a-chi-tocca D8, D11.';
```

</div>

---
{% include-markdown "signature-core.md" %}
