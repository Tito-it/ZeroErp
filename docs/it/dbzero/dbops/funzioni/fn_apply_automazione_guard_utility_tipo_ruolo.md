{% include-markdown "it/dbzero/dbops/manual/fn_apply_automazione_guard_utility_tipo_ruolo.md" %}
# ⚙️ Funzione `fn_apply_automazione_guard_utility_tipo_ruolo`

```sql
CREATE FUNCTION fn_apply_automazione_guard_utility_tipo_ruolo(p_exec_mode text, p_dry_run boolean)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_apply_automazione_guard_utility_tipo_ruolo(p_exec_mode text DEFAULT 'AUTO'::text, p_dry_run boolean DEFAULT false)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE
  rconf record;
  v_trigger_name text;
  v_table_qualified text;
BEGIN
  FOR rconf IN
    SELECT *
     FROM dbops.automazione_guard_utility_tipo_ruolo
     WHERE enabled = true
       AND (
         upper(btrim(exec_mode)) = 'AUTO'
         OR upper(btrim(exec_mode)) = upper(btrim(p_exec_mode))
       )
       AND soggetto_ruolo_column LIKE '%_soggetto_ruolo_id'
     ORDER BY schema_name, table_name
  LOOP
    IF NOT dbops.fn_col_exists(rconf.schema_name, rconf.table_name, rconf.utility_column)
       OR NOT dbops.fn_col_exists(rconf.schema_name, rconf.table_name, rconf.soggetto_ruolo_column)
    THEN
      CONTINUE;
    END IF;

    v_table_qualified := quote_ident(rconf.schema_name) || '.' || quote_ident(rconf.table_name);
    v_trigger_name := COALESCE(
      rconf.trigger_name,
      dbops.fn_name_from_template(
        'trg_{table}_a10_guard_utility_tipo_ruolo_ins_upd',
        rconf.schema_name,
        rconf.table_name,
        NULL,
        NULL,
        NULL,
        NULL
      )
    );

    IF p_dry_run THEN
      CONTINUE;
    END IF;

    EXECUTE format('DROP TRIGGER IF EXISTS %I ON %s;', v_trigger_name, v_table_qualified);

    EXECUTE format(
      'CREATE TRIGGER %I
       BEFORE INSERT OR UPDATE OF %I, %I ON %s
       FOR EACH ROW
       EXECUTE FUNCTION script.trgfn_guard_utility_tipo_ruolo_by_cols(%L, %L);',
      v_trigger_name,
      rconf.utility_column,
      rconf.soggetto_ruolo_column,
      v_table_qualified,
      rconf.utility_column,
      rconf.soggetto_ruolo_column
    );
  END LOOP;
END;
$function$

COMMENT ON FUNCTION dbops.fn_apply_automazione_guard_utility_tipo_ruolo(p_exec_mode text, p_dry_run boolean)
IS 'Applica trigger guard utility->tipo_ruolo sulle tabelle configurate in dbops.automazione_guard_utility_tipo_ruolo.';
```

</div>

---
{% include-markdown "signature-core.md" %}
