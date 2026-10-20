{% include-markdown "it/dbzero/dbops/manual/fn_find_function_usage.md" %}
# ⚙️ Funzione `fn_find_function_usage`

```sql
CREATE FUNCTION fn_find_function_usage(p_function_name text)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_find_function_usage(p_function_name text)
 RETURNS TABLE(object_type text, schema_name text, object_name text)
 LANGUAGE sql
 STABLE
AS $function$
  -- 1) Funzioni che richiamano p_function_name nel loro corpo
  SELECT
    'function'::TEXT AS object_type,
    ns.nspname AS schema_name,
    p.proname || '(' || pg_get_function_identity_arguments(p.oid) || ')' AS object_name
  FROM pg_proc p
  JOIN pg_namespace ns ON ns.oid = p.pronamespace
  WHERE p.prosrc LIKE '%' || p_function_name || '%'  -- presenza del nome nel sorgente PL/pgSQL
    AND p.proname <> p_function_name

  UNION ALL

  -- 2) Trigger che invocano p_function_name
  SELECT
    'trigger'::TEXT AS object_type,
    ns.nspname AS schema_name,
    rel.relname AS object_name
  FROM pg_trigger tr
  JOIN pg_proc tgt ON tgt.oid = tr.tgfoid
  JOIN pg_class rel  ON rel.oid = tr.tgrelid
  JOIN pg_namespace ns ON ns.oid = rel.relnamespace
  WHERE tgt.proname = p_function_name

  UNION ALL

  -- 3) Event trigger che invocano p_function_name
  SELECT
    'event_trigger'::TEXT AS object_type,
    NULL::TEXT AS schema_name,
    et.evtevent || ' on ' || tgt.proname AS object_name
  FROM pg_event_trigger et
  JOIN pg_proc tgt ON tgt.oid = et.evtfoid
  WHERE tgt.proname = p_function_name
  $function$

COMMENT ON FUNCTION dbops.fn_find_function_usage(p_function_name text)
IS 'trova tutte le foreign key che fanno riferimento
      ad una tabella specificata in input.';
```

</div>

---
{% include-markdown "signature-core.md" %}
