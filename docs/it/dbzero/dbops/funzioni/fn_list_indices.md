{% include-markdown "it/dbzero/dbops/manual/fn_list_indices.md" %}
# ⚙️ Funzione `fn_list_indices`

```sql
CREATE FUNCTION fn_list_indices(p_schema text, p_table text)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_list_indices(p_schema text, p_table text DEFAULT NULL::text)
 RETURNS TABLE(schema_name text, table_name text, index_name text, is_unique boolean, is_primary boolean, index_def text)
 LANGUAGE sql
AS $function$
    SELECT
      ns.nspname::TEXT        AS schema_name,
      tbl.relname::TEXT       AS table_name,
      idx.relname::TEXT       AS index_name,
      ix.indisunique          AS is_unique,
      ix.indisprimary         AS is_primary,
      pg_get_indexdef(ix.indexrelid) AS index_def
    FROM pg_index ix
    JOIN pg_class tbl  ON tbl.oid = ix.indrelid
    JOIN pg_class idx  ON idx.oid = ix.indexrelid
    JOIN pg_namespace ns ON ns.oid = tbl.relnamespace
    WHERE ns.nspname = p_schema
      AND (p_table IS NULL OR tbl.relname = p_table)
    ORDER BY tbl.relname, idx.relname;
$function$
```

</div>

---
{% include-markdown "signature-core.md" %}
