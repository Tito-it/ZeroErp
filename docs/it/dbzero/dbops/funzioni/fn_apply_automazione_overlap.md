{% include-markdown "it/dbzero/dbops/manual/fn_apply_automazione_overlap.md" %}
# ⚙️ Funzione `fn_apply_automazione_overlap`

```sql
CREATE FUNCTION fn_apply_automazione_overlap(p_exec_mode text, p_dry_run boolean)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION dbops.fn_apply_automazione_overlap(p_exec_mode text, p_dry_run boolean)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE
  rconf record;
  v_rel regclass;
  v_cols text[];
  v_col text;
  v_key_expr text;
  v_range_expr text;
  v_bounds text;
  v_constraint text;
  v_constraint_exists boolean;
  v_any_exclusion boolean;
BEGIN
  FOR rconf IN
    SELECT *
      FROM dbops.automazione_overlap
     WHERE active
       AND (upper(btrim(exec_mode)) = 'AUTO' OR exec_mode = p_exec_mode)
     ORDER BY target_schema, target_table
  LOOP
    v_rel := (quote_ident(rconf.target_schema)||'.'||quote_ident(rconf.target_table))::regclass;

    IF rconf.key_columns IS NULL OR array_length(rconf.key_columns, 1) IS NULL THEN
      CONTINUE;
    END IF;

    IF NOT dbops.fn_col_exists(rconf.target_schema, rconf.target_table, rconf.valido_dal_col)
       OR NOT dbops.fn_col_exists(rconf.target_schema, rconf.target_table, rconf.valido_al_col) THEN
      CONTINUE;
    END IF;

    v_cols := ARRAY[]::text[];
    FOREACH v_col IN ARRAY rconf.key_columns
    LOOP
      IF dbops.fn_col_exists(rconf.target_schema, rconf.target_table, v_col) THEN
        v_cols := array_append(v_cols, quote_ident(v_col) || ' WITH =');
      END IF;
    END LOOP;

    IF array_length(v_cols, 1) IS NULL THEN
      CONTINUE;
    END IF;

    v_bounds := COALESCE(NULLIF(btrim(rconf.range_bounds), ''), '[]');
    v_range_expr := format(
      'daterange(%I, COALESCE(%I, ''infinity''::date), %L) WITH &&',
      rconf.valido_dal_col,
      rconf.valido_al_col,
      v_bounds
    );

    v_key_expr := array_to_string(v_cols, ', ');

    v_constraint := COALESCE(rconf.constraint_name,
                     dbops.fn_name_from_template('ex_{table}_no_overlap', rconf.target_schema, rconf.target_table, NULL, NULL, NULL, NULL));

    -- Se il nome e' gia' usato da un indice o altro oggetto, usa un suffisso
    IF EXISTS (
      SELECT 1
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
       WHERE n.nspname = rconf.target_schema
         AND c.relname = v_constraint
    ) THEN
      v_constraint := dbops.fn_name_from_template('ex_{table}_no_overlap_c', rconf.target_schema, rconf.target_table, NULL, NULL, NULL, NULL);
    END IF;

    SELECT EXISTS (
      SELECT 1
        FROM pg_constraint con
       WHERE con.conrelid = v_rel
         AND con.contype = 'x'
         AND con.conname = v_constraint
    )
    INTO v_constraint_exists;

    SELECT EXISTS (
      SELECT 1
        FROM pg_constraint con
       WHERE con.conrelid = v_rel
         AND con.contype = 'x'
         AND pg_get_constraintdef(con.oid) ILIKE '%' || rconf.valido_dal_col || '%'
         AND pg_get_constraintdef(con.oid) ILIKE '%' || rconf.valido_al_col || '%'
    )
    INTO v_any_exclusion;

    IF v_constraint_exists OR v_any_exclusion THEN
      CONTINUE;
    END IF;

    IF p_dry_run THEN
      PERFORM dbops.fn_audit_log_once(
        p_function_name => 'dbops.fn_apply_automazione_overlap',
        p_status        => 'DRYRUN',
        p_rule_type     => 'OVERLAP',
        p_exec_mode     => p_exec_mode,
        p_parts         => ARRAY['OVERLAP'],
        p_dry_run       => true,
        p_params        => jsonb_build_object(
                            'table', rconf.target_schema||'.'||rconf.target_table,
                            'constraint', v_constraint,
                            'key_columns', rconf.key_columns,
                            'valido_dal_col', rconf.valido_dal_col,
                            'valido_al_col', rconf.valido_al_col,
                            'range_bounds', v_bounds,
                            'action', 'DRYRUN_CREATE_EXCLUDE'
                          ),
        p_message       => 'Exclude constraint would be created'
      );
      CONTINUE;
    END IF;

    EXECUTE format(
      'ALTER TABLE %I.%I ADD CONSTRAINT %I EXCLUDE USING gist (%s, %s)',
      rconf.target_schema,
      rconf.target_table,
      v_constraint,
      v_key_expr,
      v_range_expr
    );
  END LOOP;
END;
$function$
```

---
{% include-markdown "signature-core.md" %}
