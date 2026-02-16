{% include-markdown "it/dbzero/dbops/manual/fn_seed_automazione_guard_utility_tipo_ruolo.md" %}
# ⚙️ Funzione `fn_seed_automazione_guard_utility_tipo_ruolo`

```sql
CREATE FUNCTION fn_seed_automazione_guard_utility_tipo_ruolo(p_schemas text[])
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION dbops.fn_seed_automazione_guard_utility_tipo_ruolo(p_schemas text[] DEFAULT NULL::text[])
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_schemas text[];
  rtab record;
  v_soggetto_ruolo_col text;
BEGIN
  v_schemas := dbops.fn_resolve_scope(p_schemas);

  FOR rtab IN
    SELECT n.nspname AS schema_name,
           c.relname AS table_name
      FROM pg_class c
      JOIN pg_namespace n ON n.oid = c.relnamespace
     WHERE c.relkind = 'r'
       AND n.nspname = ANY(v_schemas)
       AND n.nspname <> 'storico'
       AND dbops.fn_table_in_scope(n.nspname, c.relname)
       AND dbops.fn_col_exists(n.nspname, c.relname, 'utility_id')
  LOOP
    SELECT att.attname
      INTO v_soggetto_ruolo_col
      FROM pg_constraint con
      JOIN unnest(con.conkey) WITH ORDINALITY AS k(attnum, ord) ON true
      JOIN pg_attribute att
        ON att.attrelid = con.conrelid
       AND att.attnum = k.attnum
      JOIN pg_class cref ON cref.oid = con.confrelid
      JOIN pg_namespace nref ON nref.oid = cref.relnamespace
      JOIN pg_class c ON c.oid = con.conrelid
      JOIN pg_namespace n ON n.oid = c.relnamespace
     WHERE con.contype = 'f'
       AND n.nspname = rtab.schema_name
       AND c.relname = rtab.table_name
       AND nref.nspname = 'anagrafiche'
       AND cref.relname = 'soggetti_ruoli'
       AND att.attname LIKE '%_soggetto_ruolo_id'
     ORDER BY
       att.attname
     LIMIT 1;

    IF v_soggetto_ruolo_col IS NULL THEN
      SELECT a.attname
        INTO v_soggetto_ruolo_col
        FROM pg_attribute a
        JOIN pg_class c ON c.oid = a.attrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
       WHERE n.nspname = rtab.schema_name
         AND c.relname = rtab.table_name
         AND a.attnum > 0
         AND NOT a.attisdropped
         AND a.attname LIKE '%_soggetto_ruolo_id'
       ORDER BY a.attname
       LIMIT 1;
    END IF;

    IF v_soggetto_ruolo_col IS NULL THEN
      CONTINUE;
    END IF;

    INSERT INTO dbops.automazione_guard_utility_tipo_ruolo (
      schema_name,
      table_name,
      utility_column,
      soggetto_ruolo_column,
      enabled,
      exec_mode,
      meta
    )
    VALUES (
      rtab.schema_name,
      rtab.table_name,
      'utility_id',
      v_soggetto_ruolo_col,
      true,
      'AUTO',
      jsonb_build_object(
        'seed', 'auto_detect_fk_soggetti_ruoli',
        'seeded_at', now()
      )
    )
    ON CONFLICT (schema_name, table_name) DO NOTHING;
  END LOOP;
END;
$function$
```

---
{% include-markdown "signature-core.md" %}
