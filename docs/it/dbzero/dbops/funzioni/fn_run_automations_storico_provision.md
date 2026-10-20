{% include-markdown "it/dbzero/dbops/manual/fn_run_automations_storico_provision.md" %}
# ⚙️ Funzione `fn_run_automations_storico_provision`

```sql
CREATE FUNCTION fn_run_automations_storico_provision(p_exec_mode text, p_schemas text[], p_dry_run boolean)
```

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
        v_schemas text[] ;
        has_flag boolean;
        storicizza_col text;
        fk_col text;
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
              AND (UPPER(r.target_table) = '*ALL' OR rtab.table_name ILIKE r.target_table)
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
IS '
  Provisioning automatico delle tabelle storico (storico.<tabella>) tramite regole in dbops.automation_rules_tbl.

  Scopo:
  - Scansiona le tabelle degli schemi in scope (risolti da fn_resolve_scope), escludendo lo schema storico.
  - Per ogni tabella, applica le regole abilitate con rule_type = ''''STORICO_PROVISION'''' compatibili con exec_mode e target schema/table.
  - Se la tabella espone una colonna di flag storicizza (default ''''storicizza'''', override tramite automation_overrides_cols: key ''''STORICIZZA_COL''''),
    invoca fn_ensure_storico_table per creare/aggiornare la corrispondente tabella in storico.*.
  - La colonna FK nello storico è calcolata come <table_name>_id (override tramite automation_overrides_cols: key ''''STORICO_FK'''').
  - Parametro create_gin_index (in params JSON della regola) abilita la creazione dell''''indice GIN sullo snapshot nello storico.

  Parametri:
  - p_exec_mode: modalità di esecuzione (es. ''''AUTO'''', ''''MANUAL''''); una regola è applicata se exec_mode = ''''AUTO'''' oppure exec_mode = p_exec_mode.
  - p_schemas: lista schemi target; può includere scope/wildcard risolti da fn_resolve_scope.
  - p_dry_run: se TRUE, esegue in modalità simulata (nessun DDL effettivo), demandando la gestione al helper fn_ensure_storico_table.

  Note:
  - Le tabelle prive della colonna storicizza (o override) vengono ignorate.
  - La funzione è pensata per essere richiamata da automazioni/maintenance e si appoggia agli helper dbops per scope, override e provisioning.
  ';
```

</div>

---
{% include-markdown "signature-core.md" %}
