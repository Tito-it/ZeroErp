{% include-markdown "it/dbzero/dbops/manual/fn_search_column_usage.md" %}
# ⚙️ Funzione `fn_search_column_usage`

```sql
CREATE FUNCTION fn_search_column_usage(p_column_name name)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_search_column_usage(p_column_name name)
 RETURNS TABLE(object_type text, schema_name name, object_name text)
 LANGUAGE sql
 STABLE
AS $function$
    -- Viste
    SELECT 'view'::text        AS object_type,
           schemaname          AS schema_name,
           viewname::text      AS object_name
      FROM pg_catalog.pg_views
     WHERE definition ILIKE '%' || p_column_name || '%'

    UNION ALL

    -- Viste materializzate
    SELECT 'materialized_view'::text,
           schemaname,
           matviewname::text
      FROM pg_catalog.pg_matviews
     WHERE definition ILIKE '%' || p_column_name || '%'

    UNION ALL

    -- Regole
    SELECT 'rule'::text,
           schemaname,
           rulename::text
      FROM pg_catalog.pg_rules
     WHERE definition ILIKE '%' || p_column_name || '%'

    UNION ALL

    -- Funzioni: il corpo senza commenti, anche delle BEGIN ATOMIC
    SELECT 'function'::text,
           n.nspname,
           p.proname::text
      FROM pg_catalog.pg_proc p
      JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
     WHERE dbops.fn_corpo_funzione(p.oid) ILIKE '%' || p_column_name || '%'

    UNION ALL

    -- Vincoli: la definizione in chiaro. conbin scrive le colonne
    -- per numero (:varattno N) e non le nominerebbe mai.
    SELECT 'constraint'::text,
           n.nspname,
           con.conname::text
      FROM pg_catalog.pg_constraint con
      JOIN pg_catalog.pg_namespace n ON n.oid = con.connamespace
     WHERE pg_catalog.pg_get_constraintdef(con.oid) ILIKE '%' || p_column_name || '%';
$function$

COMMENT ON FUNCTION dbops.fn_search_column_usage(p_column_name name)
IS 'Strumento DBA: dove si nomina una colonna, dato il suo nome. Cerca nelle definizioni di viste, viste materializzate e regole, nel corpo delle funzioni (letto da dbops.fn_corpo_funzione: senza commenti, anche per le funzioni SQL BEGIN ATOMIC) e nella definizione dei vincoli (pg_get_constraintdef: CHECK, FK, UNIQUE, chiavi). Il confronto e'' per SOTTOSTRINGA e senza maiuscole: cercando id esce quasi tutto, e un nome uguale in un''altra tabella esce lo stesso. E'' un elenco da guardare, non le dipendenze: quelle esatte stanno in pg_depend. Nessun chiamante applicativo.';
```

</div>

---
{% include-markdown "signature-core.md" %}
