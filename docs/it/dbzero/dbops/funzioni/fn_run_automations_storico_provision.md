{% include-markdown "it/dbzero/dbops/manual/fn_run_automations_storico_provision.md" %}
# ⚙️ Funzione `fn_run_automations_storico_provision`

```sql
CREATE FUNCTION fn_run_automations_storico_provision(p_exec_mode text, p_schemas text[], p_dry_run boolean)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_run_automations_storico_provision(p_exec_mode text, p_schemas text[], p_dry_run boolean)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
      DECLARE
        rtab record;
        rrule record;
        -- array: %TYPE non compone con [] (elementi: dbops.automation_scope.schema_name)
        v_schemas text[];
        -- esiti calcolati qui: nessuna colonna ne e' il riflesso
        has_flag boolean;
        storicizza_col dbops.automation_overrides_cols.col_name%TYPE;
        fk_col dbops.automation_overrides_cols.col_name%TYPE;
        -- letto dai params jsonb della regola: nessuna colonna lo porta
        create_gin boolean;
      BEGIN
        v_schemas := dbops.fn_resolve_scope(p_schemas);

        /*
          Scopo:
          - Scansiona le tabelle degli schemi in scope (risolti da fn_resolve_scope), escludendo lo schema storico.
          - Per ogni tabella, applica le regole abilitate con rule_type = ''STORICO_PROVISION'' compatibili con exec_mode e target schema/table.
          - Se la tabella espone una colonna di flag storicizza (default ''storicizza'', override tramite automation_overrides_cols: key ''STORICIZZA_COL''),
            invoca fn_ensure_storico_table per creare/aggiornare la corrispondente tabella in storico.*.
          - La colonna FK nello storico è calcolata come <table_name>_id (override tramite automation_overrides_cols: key ''STORICO_FK'').
          - Parametro create_gin_index (in params JSON della regola) abilita la creazione dell''indice GIN sullo snapshot nello storico.

          Parametri:
          - p_exec_mode: modalità di esecuzione (es. ''AUTO'', ''MANUAL''); una regola è applicata se exec_mode = ''AUTO'' oppure exec_mode = p_exec_mode.
          - p_schemas: lista schemi target; può includere scope/wildcard risolti da fn_resolve_scope.
          - p_dry_run: se TRUE, esegue in modalità simulata (nessun DDL effettivo), demandando la gestione al helper fn_ensure_storico_table.
        */


        -- loop tabelle degli schemi target
        FOR rtab IN
          SELECT n.nspname AS schema_name, c.relname AS table_name
          FROM pg_class c
          JOIN pg_namespace n ON n.oid=c.relnamespace
          WHERE c.relkind='r' AND n.nspname = ANY(v_schemas)
          AND n.nspname <> 'storico'   
          AND dbops.fn_table_in_scope(n.nspname, c.relname)
        LOOP
          -- regole 'STORICO_PROVISION' pertinenti (schema match con wildcard *all + target_table)
          FOR rrule IN
            SELECT *
            FROM dbops.automation_rules_tbl r
            WHERE r.enabled
              AND r.rule_type='STORICO_PROVISION'
              AND (r.exec_mode='AUTO' OR r.exec_mode=p_exec_mode)
              AND dbops.fn_schema_match(r.target_schema, rtab.schema_name)
              AND (r.target_table = '*all' OR rtab.table_name = r.target_table)
          LOOP
            --  parametri regola
            create_gin := COALESCE((rrule.params->>'create_gin_index')::boolean, false);

            /*IF COALESCE((rrule.params->>'auto_provision')::boolean, false) IS NOT TRUE THEN
              CONTINUE;
            END IF; */

            -- colonna storicizza (override: STORICIZZA_COL)
            storicizza_col := dbops.fn_get_override_col(rtab.schema_name, rtab.table_name, 'STORICIZZA_COL', 'storicizza');
            has_flag := dbops.fn_col_exists(rtab.schema_name, rtab.table_name, storicizza_col);
            IF NOT has_flag THEN
              CONTINUE;
            END IF;

            -- calcolo FK colonna storico (override: STORICO_FK)
            fk_col := dbops.fn_get_override_col(rtab.schema_name, rtab.table_name, 'STORICO_FK', rtab.table_name||'_id');

            -- crea tabella storico se manca (dry-run / ok / error handling già dentro helper)
            PERFORM dbops.fn_ensure_storico_table(rtab.schema_name, rtab.table_name, fk_col, create_gin, p_dry_run);
          END LOOP;
        END LOOP;
      END;
      $function$

COMMENT ON FUNCTION dbops.fn_run_automations_storico_provision(p_exec_mode text, p_schemas text[], p_dry_run boolean)
IS 'Provisioning delle shadow storico.<tabella> con le regole STORICO_PROVISION di dbops.automation_rules_tbl. Per ogni tabella (relkind r) degli schemi di dbops.fn_resolve_scope(p_schemas), escluso storico, che dbops.fn_table_in_scope ammette, applica le regole abilitate che valgono per lo schema (dbops.fn_schema_match) e per la tabella (target_table *all, o il nome esatto della tabella) e la cui exec_mode e'' AUTO o uguale a p_exec_mode (il CHECK della tabella ammette AUTO, CI, SCHEDULED). Una tabella entra solo se ha la colonna del flag di storicizzazione (storicizza, o l''override STORICIZZA_COL di dbops.automation_overrides_cols); la colonna che punta alla madre nella shadow e'' <tabella>_id, o l''override STORICO_FK. Per ognuna chiama dbops.fn_ensure_storico_table, che crea la shadow solo se manca e non modifica quelle esistenti; il parametro create_gin_index della regola chiede l''indice GIN sullo snapshot. p_dry_run: nessun DDL, audit DRYRUN.';
```

</div>

---
{% include-markdown "signature-core.md" %}
