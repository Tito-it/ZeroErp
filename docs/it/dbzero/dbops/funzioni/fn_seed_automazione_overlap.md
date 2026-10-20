{% include-markdown "it/dbzero/dbops/manual/fn_seed_automazione_overlap.md" %}
# ⚙️ Funzione `fn_seed_automazione_overlap`

```sql
CREATE FUNCTION fn_seed_automazione_overlap(p_schemas text[])
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_seed_automazione_overlap(p_schemas text[] DEFAULT NULL::text[])
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_schemas text[];
  rtab record;
  v_dal_col text;
  v_al_col text;
  v_active boolean;
  v_key_cols text[];
  v_note text;
  v_con record;
  v_con_def text;
  v_idx record;
  v_idx_def text;
  v_cols_text text;
  v_cols_arr text[];
  v_constraint_name text;
  v_rel regclass;
  v_range_col text;
BEGIN
  v_schemas := dbops.fn_resolve_scope(p_schemas);

  FOR rtab IN
    SELECT n.nspname AS schema_name,
           c.relname AS table_name,
           (quote_ident(n.nspname)||'.'||quote_ident(c.relname))::regclass AS rel
      FROM pg_class c
      JOIN pg_namespace n ON n.oid=c.relnamespace
     WHERE c.relkind='r'
       AND n.nspname = ANY(v_schemas)
       AND n.nspname <> 'storico'
       AND dbops.fn_table_in_scope(n.nspname, c.relname)
  LOOP
    v_rel := rtab.rel;
    v_dal_col := NULL;
    v_al_col := NULL;
    v_active := false;
    v_key_cols := NULL;
    v_note := NULL;
    v_constraint_name := NULL;
    v_range_col := NULL;

    IF dbops.fn_col_exists(rtab.schema_name, rtab.table_name, 'valido_dal')
       AND dbops.fn_col_exists(rtab.schema_name, rtab.table_name, 'valido_al') THEN
      v_dal_col := 'valido_dal';
      v_al_col := 'valido_al';
    ELSIF dbops.fn_col_exists(rtab.schema_name, rtab.table_name, 'valid_from')
       AND dbops.fn_col_exists(rtab.schema_name, rtab.table_name, 'valid_to') THEN
      v_dal_col := 'valid_from';
      v_al_col := 'valid_to';
    ELSE
      CONTINUE;
    END IF;

    -- Detection colonna daterange/tstzrange nativa
    -- Cerca 'validita' come nome standard per la colonna range nativa
    SELECT a.attname
      INTO v_range_col
      FROM pg_attribute a
      JOIN pg_type t ON t.oid = a.atttypid
     WHERE a.attrelid = v_rel
       AND a.attname = 'validita'
       AND t.typname IN ('daterange', 'tstzrange')
       AND NOT a.attisdropped;

    -- 1) Esclude se esiste un vincolo EXCLUDE gia` definito
    SELECT con.conname AS conname,
           pg_get_constraintdef(con.oid) AS condef
      INTO v_con
      FROM pg_constraint con
     WHERE con.conrelid = v_rel
       AND con.contype = 'x'
     ORDER BY con.oid
     LIMIT 1;

    IF FOUND THEN
      v_con_def := v_con.condef;
      v_constraint_name := v_con.conname;
      SELECT array_agg(m[1])
        INTO v_key_cols
        FROM regexp_matches(v_con_def, '([a-zA-Z_][a-zA-Z0-9_]*) WITH =', 'g') AS m;
      IF array_length(v_key_cols, 1) IS NOT NULL THEN
        v_active := true;
        v_note := 'exclude_constraint_detected';
      ELSE
        v_note := 'exclude_detected_keys_not_parsed';
      END IF;
    END IF;

    -- 2) Se non trovato, prova con indice GiST con daterange
    IF NOT v_active THEN
      FOR v_idx IN
        SELECT idx.relname AS index_name,
               pg_get_indexdef(idx.oid) AS idx_def
          FROM pg_index i
          JOIN pg_class idx ON idx.oid = i.indexrelid
         WHERE i.indrelid = v_rel
           AND i.indisvalid
      LOOP
        v_idx_def := v_idx.idx_def;
        IF v_idx_def ILIKE '%USING gist%'
           AND v_idx_def ILIKE '%' || v_dal_col || '%'
           AND v_idx_def ILIKE '%daterange(%'
        THEN
          v_cols_text := substring(v_idx_def FROM 'USING gist \\((.*)\\)$');
          v_cols_text := regexp_replace(v_cols_text, 'daterange\\(.*\\)$', '', 'g');
          v_cols_text := regexp_replace(btrim(v_cols_text), ',\\s*$', '');
          IF v_cols_text IS NOT NULL AND btrim(v_cols_text) <> '' THEN
            v_cols_arr := string_to_array(v_cols_text, ',');
            SELECT array_agg(btrim(c)) INTO v_key_cols FROM unnest(v_cols_arr) AS c;
          END IF;

          IF array_length(v_key_cols, 1) IS NOT NULL THEN
            v_active := true;
            v_note := 'gist_index_detected';
          ELSE
            v_note := 'gist_index_keys_not_parsed';
          END IF;
          EXIT;
        END IF;
      END LOOP;
    END IF;

    -- 3) Se ancora non attivo, prova con UNIQUE/PK che include il periodo
    IF NOT v_active THEN
      FOR v_con IN
        SELECT conname, contype, conkey
          FROM pg_constraint
         WHERE conrelid = v_rel
           AND contype IN ('p','u')
      LOOP
        SELECT array_agg(att.attname ORDER BY u.ord)
          INTO v_cols_arr
          FROM unnest(v_con.conkey) WITH ORDINALITY AS u(attnum, ord)
          JOIN pg_attribute att
            ON att.attrelid = v_rel
           AND att.attnum = u.attnum;

        IF v_cols_arr IS NOT NULL AND v_dal_col = ANY(v_cols_arr) THEN
          v_key_cols := array_remove(v_cols_arr, v_dal_col);
          v_key_cols := array_remove(v_key_cols, v_al_col);
          IF array_length(v_key_cols, 1) IS NOT NULL THEN
            v_active := true;
            v_note := 'unique_with_period_detected';
          ELSE
            v_note := 'unique_detected_no_keys';
          END IF;
          EXIT;
        END IF;
      END LOOP;
    END IF;

    IF NOT v_active AND v_note IS NULL THEN
      v_note := 'non_versionata_o_non_rilevabile';
    END IF;

    -- 4) Fallback: mappa chiavi note per tabelle versionate senza indizi strutturali
    IF v_key_cols IS NULL OR array_length(v_key_cols, 1) IS NULL THEN
      IF rtab.schema_name = 'vendite' AND rtab.table_name = 'contratti' THEN
        v_key_cols := ARRAY['billing_account_id','istanza_utility_id','utility_id','ambito'];
        v_active := true;
        v_note := 'default_keys_assigned';
      ELSIF rtab.schema_name = 'catalogo' AND rtab.table_name = 'articoli_componenti' THEN
        v_key_cols := ARRAY['prodotto_id','componente_id'];
        v_active := true;
        v_note := 'default_keys_assigned';
      ELSIF rtab.schema_name = 'catalogo' AND rtab.table_name = 'unita_misura_conversioni' THEN
        v_key_cols := ARRAY['uom_from_id','uom_to_id'];
        v_active := true;
        v_note := 'default_keys_assigned';
      END IF;
    END IF;

    INSERT INTO dbops.automazione_overlap (
      target_schema,
      target_table,
      key_columns,
      valido_dal_col,
      valido_al_col,
      range_bounds,
      constraint_name,
      active,
      exec_mode,
      note,
      range_col,
      data_insert,
      user_insert,
      data_update,
      user_update
    )
    VALUES (
      rtab.schema_name,
      rtab.table_name,
      v_key_cols,
      v_dal_col,
      v_al_col,
      '[]',
      v_constraint_name,
      v_active,
      'AUTO',
      v_note,
      v_range_col,
      now(),
      CURRENT_USER,
      now(),
      CURRENT_USER
    )
    ON CONFLICT (target_schema, target_table)
    DO UPDATE SET
      key_columns     = EXCLUDED.key_columns,
      valido_dal_col  = EXCLUDED.valido_dal_col,
      valido_al_col   = EXCLUDED.valido_al_col,
      range_bounds    = EXCLUDED.range_bounds,
      constraint_name = EXCLUDED.constraint_name,
      active          = EXCLUDED.active,
      exec_mode       = EXCLUDED.exec_mode,
      note            = EXCLUDED.note,
      range_col       = EXCLUDED.range_col,
      data_update     = now(),
      user_update     = CURRENT_USER;
  END LOOP;
END;
$function$

COMMENT ON FUNCTION dbops.fn_seed_automazione_overlap(p_schemas text[])
IS 'Popola dbops.automazione_overlap rilevando tabelle con valido_dal/valido_al o valid_from/valid_to. Rileva anche la presenza di colonna daterange nativa (validita) e popola range_col.';
```

</div>

---
{% include-markdown "signature-core.md" %}
