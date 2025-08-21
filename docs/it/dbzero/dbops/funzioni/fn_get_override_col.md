# ⚙️ Funzione `fn_get_override_col`

```sql
CREATE FUNCTION fn_get_override_col(p_schema text, p_table text, p_role text, p_default text)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION dbops.fn_get_override_col(p_schema text, p_table text, p_role text, p_default text)
 RETURNS text
 LANGUAGE sql
AS $function$
     SELECT COALESCE((
       SELECT col_name
         FROM dbops.automation_overrides_cols
       WHERE schema_name=p_schema
         AND table_name=p_table
         AND col_role=p_role
       LIMIT 1
     ), p_default);
   $function$
```

---
{% include-markdown "signature-core.md" %}
