{% include-markdown "it/dbzero/dbops/manual/fn_trigger_exists_by_function.md" %}
# ⚙️ Funzione `fn_trigger_exists_by_function`

```sql
CREATE FUNCTION fn_trigger_exists_by_function(p_rel regclass, p_fn_schema text, p_fn_name text)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION dbops.fn_trigger_exists_by_function(p_rel regclass, p_fn_schema text, p_fn_name text)
 RETURNS boolean
 LANGUAGE sql
AS $function$
    SELECT EXISTS(
      SELECT 1
        FROM pg_trigger t
        JOIN pg_proc p ON p.oid = t.tgfoid
        JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE t.tgrelid = p_rel
        AND n.nspname = p_fn_schema
        AND p.proname = p_fn_name
        AND NOT t.tgisinternal
    );
  $function$
```

---
{% include-markdown "signature-core.md" %}
