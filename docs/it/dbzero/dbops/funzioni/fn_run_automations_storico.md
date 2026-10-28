{% include-markdown "it/dbzero/dbops/manual/fn_run_automations_storico.md" %}
# ⚙️ Funzione `fn_run_automations_storico`

```sql
CREATE FUNCTION fn_run_automations_storico(p_exec_mode text, p_schemas text[], p_dry_run boolean)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_run_automations_storico(p_exec_mode text, p_schemas text[], p_dry_run boolean)
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
  has_sto boolean;
  fk_col   text;
  tmpl     text;
  trg_name text;
  exist_strat text;
BEGIN

      /*
        Scopo
        -----
        Esegue l'automazione di provisioning dei trigger di storico sulle tabelle "in scope",
        applicando le regole abilitate in dbops.automation_rules_tbl di tipo 'STORICO'.

        La funzione:
        1) risolve lo scope degli schemi (dbops.fn_resolve_scope),
        2) scorre tutte le tabelle (relkind='r') degli schemi target (escluso 'storico'),
          filtrate da dbops.fn_table_in_scope(schema, table),
        3) per ogni tabella applica le regole STORICO compatibili con:
          - enabled = true
          - exec_mode = 'AUTO' oppure exec_mode = p_exec_mode
          - match su schema (dbops.fn_schema_match)
          - match su tabella: '*ALL' oppure pattern ILIKE su r.target_table
        4) se esiste la tabella storico corrispondente (storico.<table_name>),
          assicura la presenza del trigger UPDATE+DELETE sulla tabella base usando:
          - nome trigger derivato da template (rrule.name_template, default 'trg_z90_{table}_storico_upd_dlt')
          - funzione trigger generica script.trgfn_storico_generic(fk_col)

        Esistenza trigger / strategie
        -----------------------------
        La creazione del trigger è condizionata da rrule.existence_strategy (default 'BY_NAME'):
        - BY_NAME     : verifica esistenza per nome trigger
        - BY_FUNCTION : verifica esistenza per funzione trigger
        - BOTH        : considera presente se esiste per nome OR per funzione
        Questo evita duplicazioni e permette migrazioni graduali da trigger legacy a trigger generici.

        Colonna FK logica (fk_col)
        --------------------------
        Determina la colonna FK logica passata alla funzione trigger tramite:
        - override (dbops.fn_get_override_col) con chiave 'STORICO_FK'
        - fallback: <table_name>_id
        ⛔ rev 2026-09-25: prima di montare il trigger si verifica che fk_col sia
        una colonna della gemella; se non lo e' si solleva E_STORICO_FK_COL_ASSENTE.
        Un trigger montato con una colonna che non c'e' muore alla prima chiusura
        di uno snapshot, cioe' su ogni UPDATE/DELETE di una riga storicizzata
        (brief-db-storico-colonna-fk-dei-trigger).

        Modalità DRY RUN
        ---------------
        Se p_dry_run=true non esegue DDL (CREATE TRIGGER/DROP TRIGGER) e registra invece
        un audit con dbops.fn_audit_log_once indicando cosa verrebbe creato.

        Error handling
        --------------
        - duplicate_object: logga SKIP_EXISTS su audit (trigger già presente)
        - altri errori: log strutturato e rilancio tramite script.fn_log_and_raise_error
          includendo tabella e messaggio SQLERRM.
      */




v_schemas := dbops.fn_resolve_scope(p_schemas);

FOR rtab IN
  SELECT n.nspname AS schema_name,
        c.relname  AS table_name,
        (quote_ident(n.nspname)||'.'||quote_ident(c.relname))::regclass AS rel
  FROM pg_class c
  JOIN pg_namespace n ON n.oid=c.relnamespace
  WHERE c.relkind='r'
    AND n.nspname = ANY(v_schemas)
    AND n.nspname <> 'storico'                  
    AND dbops.fn_table_in_scope(n.nspname, c.relname)
LOOP
  FOR rrule IN
    SELECT *
    FROM dbops.automation_rules_tbl r
    WHERE r.enabled
      AND upper(btrim(r.rule_type))='STORICO'
      AND (upper(btrim(r.exec_mode)) = 'AUTO' OR r.exec_mode = p_exec_mode)
      AND dbops.fn_schema_match(r.target_schema, rtab.schema_name)
      AND (UPPER (r.target_table) = '*ALL' OR rtab.table_name ILIKE r.target_table)

      ORDER BY r.priority, r.id
    LOOP
      exist_strat := COALESCE(rrule.existence_strategy,'BY_NAME');

      SELECT EXISTS(
        SELECT 1 FROM pg_class c2
        JOIN pg_namespace n2 ON n2.oid=c2.relnamespace
      WHERE n2.nspname='storico'
        AND c2.relkind='r'
        AND c2.relname=rtab.table_name
      ) INTO has_sto;

      IF has_sto THEN
        fk_col := dbops.fn_get_override_col(rtab.schema_name, rtab.table_name, 'STORICO_FK', rtab.table_name||'_id');

        tmpl     := COALESCE(rrule.name_template, 'trg_z90_{table}_storico_upd_dlt');
        trg_name := dbops.fn_name_from_template(tmpl, rtab.schema_name, rtab.table_name, NULL,NULL,NULL, 'upd_dlt');
        exist_strat := COALESCE(rrule.existence_strategy,'BY_NAME');

        IF (exist_strat='BY_NAME'     AND NOT dbops.fn_trigger_exists_by_name(rtab.rel, trg_name))
        OR (exist_strat='BY_FUNCTION' AND NOT dbops.fn_trigger_exists_by_function(rtab.rel,'script','trgfn_upd_dlt_storico_generic'))
        OR (exist_strat='BOTH'        AND NOT (dbops.fn_trigger_exists_by_name(rtab.rel, trg_name)
                                          OR dbops.fn_trigger_exists_by_function(rtab.rel,'script','trgfn_upd_dlt_storico_generic')))
        THEN
          -- rev 2026-09-25 ⛔ Il rubinetto: l'argomento del trigger deve essere
          --   una colonna della gemella. Il trigger lo scoprirebbe solo alla
          --   prima chiusura di uno snapshot, respingendo la scrittura della
          --   madre (E_SNAPSHOT_CLOSE_ERROR). Cinque gemelle del 2025 erano
          --   nate col nome al singolare e senza eccezione STORICO_FK: qui si
          --   sarebbero fermate alla nascita. Vale anche in dry run: un «verrebbe
          --   creato» su un trigger rotto e' una risposta sbagliata.
          --   Fuori dal blocco BEGIN/EXCEPTION sotto, che lo ribattezzerebbe
          --   E_STORICO_UD.
          IF NOT EXISTS (
            SELECT 1
              FROM pg_attribute a
             WHERE a.attrelid = format('storico.%I', rtab.table_name)::regclass
               AND a.attname  = fk_col
               AND a.attnum   > 0
               AND NOT a.attisdropped
          ) THEN
            PERFORM script.fn_log_and_raise_error(
              'database', 'dbops.fn_run_automations_storico', 'E_STORICO_FK_COL_ASSENTE',
              jsonb_build_object('table', rtab.schema_name||'.'||rtab.table_name,
                                 'storico', 'storico.'||rtab.table_name,
                                 'fk_col', fk_col),
              NULL::uuid,
              fk_col, 'storico.'||rtab.table_name, rtab.schema_name||'.'||rtab.table_name);
          END IF;

          IF p_dry_run THEN
            PERFORM dbops.fn_audit_log_once(
              p_function_name => 'fn_run_automations_storico',
              p_status => 'DRYRUN', p_rule_type => 'STORICO', p_dry_run => true,
              p_params => jsonb_build_object('table', rtab.schema_name||'.'||rtab.table_name,'trigger', trg_name,'action','DRYRUN_CREATE_TRIGGER_UD'),
              p_message => 'Storico UPDATE+DELETE trigger would be created'
            );
          ELSE
            BEGIN
              EXECUTE format($f$
                CREATE TRIGGER %I
                BEFORE UPDATE OR DELETE ON %I.%I
                FOR EACH ROW
                EXECUTE FUNCTION script.trgfn_storico_generic(%L)
              $f$, trg_name, rtab.schema_name, rtab.table_name, fk_col);
            EXCEPTION WHEN duplicate_object THEN
              -- rev 2026-08-04 (bonifica F3): la chiamata era posizionale con
              --   il 3o e 4o argomento invertiti (rule_type al posto di
              --   p_params jsonb, e il jsonb al posto di p_message). Resa a
              --   nomi, come la sorella in DRYRUN qui sopra.
              PERFORM dbops.fn_audit_log_once(
                p_function_name => 'fn_run_automations_storico',
                p_status        => 'SKIP_EXISTS',
                p_rule_type     => 'STORICO',
                p_params        => jsonb_build_object('table', rtab.schema_name||'.'||rtab.table_name,'trigger', trg_name::text),
                p_message       => 'Trigger already present');
            WHEN OTHERS THEN
              -- ⭐ Rev 2026-10-16 (brief-db-presidio-job-run-a-chi-tocca D8, D10, D11):
              --   un guasto dell'AMBIENTE (script.fn_sqlstate_di_ambiente: connessione,
              --   risorse, arresto, sistema, privilegio, lock) si rilancia COM'E', col suo
              --   SQLSTATE: l'involucro lo faceva diventare P0001, e il presidio dei job lo
              --   mandava allo sviluppo. Prima si scrive nel registro errori, col contesto.
              v_ctx_errore := jsonb_build_object('table', rtab.schema_name||'.'||rtab.table_name,'error',SQLERRM);
              IF script.fn_sqlstate_di_ambiente(SQLSTATE) THEN
                PERFORM script.fn_log_error_only(
                    'dbops', 'run_automations', 'E_STORICO_UD',
                    v_ctx_errore, NULL::uuid, SQLERRM);
                RAISE;
              END IF;
              PERFORM script.fn_log_and_raise_error(
                  'dbops', 'run_automations', 'E_STORICO_UD',
                  v_ctx_errore, NULL::uuid, SQLERRM);
            END;
          END IF;
        END IF;

      END IF;
    END LOOP;
  END LOOP;
END;


$function$

COMMENT ON FUNCTION dbops.fn_run_automations_storico(p_exec_mode text, p_schemas text[], p_dry_run boolean)
IS 'Automazione STORICO: monta il trigger generico di storicizzazione sulle tabelle che hanno la gemella in schema storico, passandogli la colonna FK della gemella (override STORICO_FK, altrimenti <tabella>_id). rev 2026-09-25: prima di montare il trigger verifica che quella colonna esista nella gemella, e se no solleva E_STORICO_FK_COL_ASSENTE: un trigger con una colonna che non c''e'' muore alla prima chiusura di uno snapshot, cioe'' su ogni UPDATE/DELETE di una riga storicizzata. Cinque gemelle del 2025 (parameters, comuni, indirizzi, indirizzi_dettaglio, catasto_unita_immobiliari) erano nate col nome al singolare e senza eccezione; rinominate da 20260925-26. Brief: brief-db-storico-colonna-fk-dei-trigger. rev 2026-09-01: rimosso il ramo drop_legacy_ud, una pulizia puntata su nomi di trigger che non sono mai esistiti (brief-db-richieste-aperte-dal-backend-2, coda C). ⭐ Rev 2026-10-16: nel gestore WHEN others, un guasto dell''AMBIENTE (script.fn_sqlstate_di_ambiente: 08, 53, 57, 58, 42501, 55P03) si rilancia COM''E'', col suo SQLSTATE, dopo averlo scritto nel registro errori con lo stesso codice e contesto (fn_log_error_only). Prima diventava P0001 col codice dell''involucro, e il presidio dei job (maintenance.vw_job_run_da_guardare) lo mandava allo sviluppo. I difetti di struttura escono come prima. Brief: brief-db-presidio-job-run-a-chi-tocca D8, D11.';
```

</div>

---
{% include-markdown "signature-core.md" %}
