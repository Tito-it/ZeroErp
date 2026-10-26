{% include-markdown "it/dbzero/dbops/manual/fn_apply_automazione_overlap.md" %}
# ⚙️ Funzione `fn_apply_automazione_overlap`

```sql
CREATE FUNCTION fn_apply_automazione_overlap(p_exec_mode text, p_dry_run boolean)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_apply_automazione_overlap(p_exec_mode text, p_dry_run boolean)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
-- Scopo: applica vincoli EXCLUDE GiST su tabelle configurate in
--   dbops.automazione_overlap (active=true). Dual codepath periodo:
--   colonna daterange nativa (range_col) o espressione calcolata
--   (valido_dal/al). Chiavi: colonne semplici (key_columns, validate e
--   quotate) + espressioni (key_expressions, as-is). EXCLUDE parziali
--   via where_predicate (NULL = totale). Idempotente: skippa se esiste
--   gia' EXCLUDE/temporal UNIQUE sulla colonna periodo.
DECLARE
  rconf                  record;
  v_rel                  regclass;
  v_cols                 text[];
  v_col                  text;
  v_key_expr             text;
  v_range_expr           text;
  v_where                text;
  v_bounds               text;
  v_constraint           text;
  v_constraint_exists    boolean;
  v_any_exclusion        boolean;
  v_temporal_unique_exists boolean;
  v_skip_status          text;
BEGIN
  v_skip_status := CASE WHEN p_dry_run THEN 'DRYRUN' ELSE 'WARN' END;
  FOR rconf IN
    SELECT *
      FROM dbops.automazione_overlap
     WHERE active
       AND (upper(btrim(exec_mode)) = 'AUTO' OR exec_mode = p_exec_mode)
     ORDER BY target_schema, target_table
  LOOP
    v_rel := (quote_ident(rconf.target_schema)||'.'||quote_ident(rconf.target_table))::regclass;

    -- Serve almeno una chiave: colonna semplice o espressione
    IF (rconf.key_columns IS NULL OR array_length(rconf.key_columns, 1) IS NULL)
       AND (rconf.key_expressions IS NULL OR array_length(rconf.key_expressions, 1) IS NULL) THEN
      PERFORM dbops.fn_audit_log_once(
        p_function_name => 'dbops.fn_apply_automazione_overlap',
        p_status        => v_skip_status,
        p_rule_type     => 'OVERLAP',
        p_exec_mode     => p_exec_mode,
        p_parts         => ARRAY['OVERLAP'],
        p_dry_run       => p_dry_run,
        p_params        => jsonb_build_object(
                            'table', rconf.target_schema||'.'||rconf.target_table,
                            'reason', 'NO_KEY_COLUMNS'
                          ),
        p_message       => 'Skip: nessuna chiave (key_columns e key_expressions vuote)'
      );
      CONTINUE;
    END IF;

    -- Validazione colonne periodo
    IF rconf.range_col IS NOT NULL THEN
      IF NOT dbops.fn_col_exists(rconf.target_schema, rconf.target_table, rconf.range_col) THEN
        PERFORM dbops.fn_audit_log_once(
          p_function_name => 'dbops.fn_apply_automazione_overlap',
          p_status        => v_skip_status,
          p_rule_type     => 'OVERLAP',
          p_exec_mode     => p_exec_mode,
          p_parts         => ARRAY['OVERLAP'],
          p_dry_run       => p_dry_run,
          p_params        => jsonb_build_object(
                              'table', rconf.target_schema||'.'||rconf.target_table,
                              'range_col', rconf.range_col,
                              'reason', 'RANGE_COL_MISSING'
                            ),
          p_message       => 'Skip: range_col not found in table'
        );
        CONTINUE;
      END IF;
    ELSE
      IF NOT dbops.fn_col_exists(rconf.target_schema, rconf.target_table, rconf.valido_dal_col)
         OR NOT dbops.fn_col_exists(rconf.target_schema, rconf.target_table, rconf.valido_al_col) THEN
        PERFORM dbops.fn_audit_log_once(
          p_function_name => 'dbops.fn_apply_automazione_overlap',
          p_status        => v_skip_status,
          p_rule_type     => 'OVERLAP',
          p_exec_mode     => p_exec_mode,
          p_parts         => ARRAY['OVERLAP'],
          p_dry_run       => p_dry_run,
          p_params        => jsonb_build_object(
                              'table', rconf.target_schema||'.'||rconf.target_table,
                              'valido_dal_col', rconf.valido_dal_col,
                              'valido_al_col', rconf.valido_al_col,
                              'reason', 'PERIOD_COLUMNS_MISSING'
                            ),
          p_message       => 'Skip: period columns missing'
        );
        CONTINUE;
      END IF;
    END IF;

    -- Costruzione key expression: 1) colonne semplici (validate+quotate)
    v_cols := ARRAY[]::text[];
    IF rconf.key_columns IS NOT NULL THEN
      FOREACH v_col IN ARRAY rconf.key_columns
      LOOP
        IF dbops.fn_col_exists(rconf.target_schema, rconf.target_table, v_col) THEN
          v_cols := array_append(v_cols, quote_ident(v_col) || ' WITH =');
        END IF;
      END LOOP;
    END IF;

    -- 2) espressioni (key_expressions): iniettate as-is (DDL di fiducia)
    IF rconf.key_expressions IS NOT NULL THEN
      FOREACH v_col IN ARRAY rconf.key_expressions
      LOOP
        IF COALESCE(btrim(v_col), '') <> '' THEN
          v_cols := array_append(v_cols, v_col || ' WITH =');
        END IF;
      END LOOP;
    END IF;

    IF array_length(v_cols, 1) IS NULL THEN
      PERFORM dbops.fn_audit_log_once(
        p_function_name => 'dbops.fn_apply_automazione_overlap',
        p_status        => v_skip_status,
        p_rule_type     => 'OVERLAP',
        p_exec_mode     => p_exec_mode,
        p_parts         => ARRAY['OVERLAP'],
        p_dry_run       => p_dry_run,
        p_params        => jsonb_build_object(
                            'table', rconf.target_schema||'.'||rconf.target_table,
                            'key_columns', rconf.key_columns,
                            'key_expressions', rconf.key_expressions,
                            'reason', 'KEY_COLUMNS_NOT_FOUND'
                          ),
        p_message       => 'Skip: chiavi non risolte (colonne assenti, nessuna espressione)'
      );
      CONTINUE;
    END IF;

    -- Costruzione range expression: dual codepath
    IF rconf.range_col IS NOT NULL THEN
      v_range_expr := format('%I WITH &&', rconf.range_col);
    ELSE
      v_bounds := COALESCE(NULLIF(btrim(rconf.range_bounds), ''), '[]');
      v_range_expr := format(
        'daterange(%I, COALESCE(%I, ''infinity''::date), %L) WITH &&',
        rconf.valido_dal_col,
        rconf.valido_al_col,
        v_bounds
      );
    END IF;

    v_key_expr := array_to_string(v_cols, ', ');

    -- Coda WHERE per EXCLUDE parziale (where_predicate e' DDL di fiducia,
    -- iniettato as-is). NULL/vuoto => vincolo totale (nessuna coda).
    v_where := CASE
                 WHEN COALESCE(btrim(rconf.where_predicate), '') <> ''
                   THEN ' WHERE (' || rconf.where_predicate || ')'
                 ELSE ''
               END;

    v_constraint := COALESCE(rconf.constraint_name,
                     dbops.fn_name_from_template('ex_{table}_no_overlap', rconf.target_schema, rconf.target_table, NULL, NULL, NULL, NULL));

    IF EXISTS (
      SELECT 1 FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
       WHERE n.nspname = rconf.target_schema AND c.relname = v_constraint
    ) THEN
      v_constraint := dbops.fn_name_from_template('ex_{table}_no_overlap_c', rconf.target_schema, rconf.target_table, NULL, NULL, NULL, NULL);
    END IF;

    -- Verifica idempotenza: una scan su pg_constraint con LATERAL
    SELECT
        bool_or(con.contype = 'x' AND con.conname = v_constraint),
        bool_or(con.contype = 'x'
                AND cd.cdef ILIKE '%' || COALESCE(rconf.range_col, rconf.valido_dal_col) || '%'),
        bool_or(con.contype = 'u'
                AND cd.cdef ILIKE '%WITHOUT OVERLAPS%'
                AND cd.cdef ILIKE '%' || COALESCE(rconf.range_col, rconf.valido_dal_col) || '%')
    FROM pg_constraint con
    CROSS JOIN LATERAL (SELECT pg_get_constraintdef(con.oid)) AS cd(cdef)
    WHERE con.conrelid = v_rel
    INTO v_constraint_exists, v_any_exclusion, v_temporal_unique_exists;

    IF v_constraint_exists OR v_any_exclusion OR v_temporal_unique_exists THEN
      PERFORM dbops.fn_audit_log_once(
        p_function_name => 'dbops.fn_apply_automazione_overlap',
        p_status        => v_skip_status,
        p_rule_type     => 'OVERLAP',
        p_exec_mode     => p_exec_mode,
        p_parts         => ARRAY['OVERLAP'],
        p_dry_run       => p_dry_run,
        p_params        => jsonb_build_object(
                            'table', rconf.target_schema||'.'||rconf.target_table,
                            'constraint', v_constraint,
                            'reason', CASE
                              WHEN v_temporal_unique_exists THEN 'TEMPORAL_UNIQUE_EXISTS'
                              ELSE 'EXCLUDE_EXISTS'
                            END
                          ),
        p_message       => CASE
          WHEN v_temporal_unique_exists
            THEN 'Skip: temporal unique (WITHOUT OVERLAPS) already present'
          ELSE 'Skip: exclude constraint already present'
        END
      );
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
                            'key_expressions', rconf.key_expressions,
                            'range_col', rconf.range_col,
                            'valido_dal_col', rconf.valido_dal_col,
                            'valido_al_col', rconf.valido_al_col,
                            'range_bounds', COALESCE(rconf.range_bounds, '[]'),
                            'where_predicate', rconf.where_predicate,
                            'action', 'DRYRUN_CREATE_EXCLUDE'
                          ),
        p_message       => 'Exclude constraint would be created'
      );
      CONTINUE;
    END IF;

    EXECUTE format(
      'ALTER TABLE %I.%I ADD CONSTRAINT %I EXCLUDE USING gist (%s, %s)%s',
      rconf.target_schema,
      rconf.target_table,
      v_constraint,
      v_key_expr,
      v_range_expr,
      v_where
    );
    PERFORM dbops.fn_audit_log_once(
      p_function_name => 'dbops.fn_apply_automazione_overlap',
      p_status        => 'OK',
      p_rule_type     => 'OVERLAP',
      p_exec_mode     => p_exec_mode,
      p_parts         => ARRAY['OVERLAP'],
      p_dry_run       => false,
      p_params        => jsonb_build_object(
                          'table', rconf.target_schema||'.'||rconf.target_table,
                          'constraint', v_constraint,
                          'key_columns', rconf.key_columns,
                          'key_expressions', rconf.key_expressions,
                          'range_col', rconf.range_col,
                          'valido_dal_col', rconf.valido_dal_col,
                          'valido_al_col', rconf.valido_al_col,
                          'range_bounds', COALESCE(rconf.range_bounds, '[]'),
                          'where_predicate', rconf.where_predicate,
                          'action', 'CREATE_EXCLUDE'
                        ),
      p_message       => 'Exclude constraint created'
    );
  END LOOP;
END;
$function$

COMMENT ON FUNCTION dbops.fn_apply_automazione_overlap(p_exec_mode text, p_dry_run boolean)
IS 'Applica i vincoli EXCLUDE GiST in base a dbops.automazione_overlap. Chiavi: key_columns (colonne validate+quotate) + key_expressions (espressioni as-is). EXCLUDE parziali via where_predicate (NULL = totale). Dual codepath periodo (range_col o valido_dal/al). Idempotente per EXCLUDE/temporal UNIQUE PG18. key_expressions/where_predicate sono DDL di fiducia DBA-only.';
```

</div>

---
{% include-markdown "signature-core.md" %}
