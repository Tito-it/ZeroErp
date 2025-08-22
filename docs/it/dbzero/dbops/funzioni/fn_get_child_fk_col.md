# ⚙️ Funzione `fn_get_child_fk_col`

```sql
CREATE FUNCTION fn_get_child_fk_col(p_conoid oid)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION dbops.fn_get_child_fk_col(p_conoid oid)
 RETURNS text
 LANGUAGE plpgsql
AS $function$
  DECLARE
    v_child_oid oid;
    v_col smallint;
    v_name text;
  BEGIN
    SELECT c.conrelid, c.conkey[1] INTO v_child_oid, v_col
    FROM pg_constraint c
    WHERE c.oid = p_conoid;

    SELECT a.attname INTO v_name
    FROM pg_attribute a
    WHERE a.attrelid = v_child_oid
      AND a.attnum   = v_col;

    RETURN v_name;
  END;
  $function$
```

---
{% include-markdown "signature-core.md" %}
