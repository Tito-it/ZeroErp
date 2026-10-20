{% include-markdown "it/dbzero/dbops/manual/fn_search_column_usage.md" %}
# ⚙️ Funzione `fn_search_column_usage`

```sql
CREATE FUNCTION fn_search_column_usage(p_column_name text)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_search_column_usage(p_column_name text)
 RETURNS TABLE(object_type text, schema_name text, object_name text)
 LANGUAGE sql
 STABLE
AS $function$
-- Function: dbops.fn_search_column_usage
-- Purpose: Given a column name, returns references in views, materialized views, rules, functions, and constraints.
-- Usage example:
-- SELECT * FROM dbops.fn_search_column_usage('nome_campo');

    -- SEARCH STANDARD VIEWS
    SELECT
        'view'          AS object_type,
        schemaname      AS schema_name,
        viewname        AS object_name
    FROM pg_catalog.pg_views
    WHERE definition ILIKE '%' || p_column_name || '%'

    UNION ALL

    -- SEARCH MATERIALIZED VIEWS
    SELECT
        'materialized_view' AS object_type,
        schemaname          AS schema_name,
        matviewname         AS object_name
    FROM pg_catalog.pg_matviews
    WHERE definition ILIKE '%' || p_column_name || '%'

    UNION ALL

    -- SEARCH RULES
    SELECT
        'rule'           AS object_type,
        schemaname       AS schema_name,
        rulename         AS object_name
    FROM pg_catalog.pg_rules
    WHERE definition ILIKE '%' || p_column_name || '%'

    UNION ALL

    -- SEARCH FUNCTIONS (source code)
    SELECT
        'function'      AS object_type,
        n.nspname       AS schema_name,
        p.proname       AS object_name
    FROM pg_catalog.pg_proc p
    JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
    WHERE p.prosrc ILIKE '%' || p_column_name || '%'

    UNION ALL

    -- SEARCH CHECK CONSTRAINTS
    SELECT
        'constraint'    AS object_type,
        n.nspname       AS schema_name,
        conname         AS object_name
    FROM pg_catalog.pg_constraint con
    JOIN pg_catalog.pg_namespace n ON n.oid = con.connamespace
    WHERE con.conbin ILIKE '%' || p_column_name || '%';
$function$
```

</div>

---
{% include-markdown "signature-core.md" %}
