# ⚙️ Funzione `fn_trigger_exists_by_name`

```sql
CREATE FUNCTION fn_trigger_exists_by_name(p_rel regclass, p_trigger_name text)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION dbops.fn_trigger_exists_by_name(p_rel regclass, p_trigger_name text)
 RETURNS boolean
 LANGUAGE sql
AS $function$
    SELECT EXISTS(
      SELECT 1 FROM pg_trigger t
      WHERE t.tgrelid = p_rel
        AND t.tgname  = p_trigger_name
        AND NOT t.tgisinternal
    );
  $function$
```

---
{% include-markdown "signature-core.md" %}
