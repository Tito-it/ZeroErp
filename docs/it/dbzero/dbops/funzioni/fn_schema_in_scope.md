{% include-markdown "it/dbzero/dbops/manual/fn_schema_in_scope.md" %}
# ⚙️ Funzione `fn_schema_in_scope`

```sql
CREATE FUNCTION fn_schema_in_scope(p_rule_target text, p_schemas text[])
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_schema_in_scope(p_rule_target text, p_schemas text[])
 RETURNS boolean
 LANGUAGE plpgsql
 IMMUTABLE
AS $function$
 DECLARE s text;
 BEGIN
   /*  Helper: match rispetto allo scope (array di schemi) */
   IF p_rule_target IS NULL THEN
     RETURN false;
   END IF;
   IF lower(p_rule_target)='*all' THEN
     RETURN true;
   END IF;
   IF p_schemas IS NULL OR array_length(p_schemas,1) IS NULL THEN
     RETURN false;
   END IF;
   FOREACH s IN ARRAY p_schemas LOOP
     IF lower(p_rule_target)=lower(s) THEN
       RETURN true;
     END IF;
   END LOOP;
   RETURN false;
 END;
 $function$
```

</div>

---
{% include-markdown "signature-core.md" %}
