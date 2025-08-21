# ⚙️ Funzione `fn_col_exists`

```sql
CREATE FUNCTION fn_col_exists(p_schema text, p_table text, p_col text)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION dbops.fn_col_exists(p_schema text, p_table text, p_col text)
 RETURNS boolean
 LANGUAGE sql
AS $function$
    SELECT EXISTS(
      SELECT 1
        FROM information_schema.columns
      WHERE table_schema=p_schema
        AND table_name=p_table
        AND column_name=p_col
    );
  $function$
```

---
{% include-markdown "signature-core.md" %}
