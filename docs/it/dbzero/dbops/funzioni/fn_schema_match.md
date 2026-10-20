{% include-markdown "it/dbzero/dbops/manual/fn_schema_match.md" %}
# ⚙️ Funzione `fn_schema_match`

```sql
CREATE FUNCTION fn_schema_match(p_rule_target text, p_schema text)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_schema_match(p_rule_target text, p_schema text)
 RETURNS boolean
 LANGUAGE plpgsql
 IMMUTABLE
AS $function$
  BEGIN
  /*  Helper: match su singolo schema */
    IF p_rule_target IS NULL THEN
      RETURN false; -- con NOT NULL non dovrebbe capitare; manteniamo difensivo
    END IF;
    IF lower(p_rule_target)='*all' THEN
      RETURN true;
    END IF;
    RETURN lower(p_rule_target)=lower(p_schema);
  END;
  $function$
```

</div>

---
{% include-markdown "signature-core.md" %}
