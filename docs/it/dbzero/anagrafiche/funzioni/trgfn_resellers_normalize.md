# ⚙️ Funzione `trgfn_resellers_normalize`

```sql
CREATE FUNCTION trgfn_resellers_normalize()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_resellers_normalize()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  RETURN NEW;
END;
$function$
```

---
{% include-markdown "signature-core.md" %}
