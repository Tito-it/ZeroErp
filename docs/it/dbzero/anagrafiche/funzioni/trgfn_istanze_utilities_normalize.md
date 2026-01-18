{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_istanze_utilities_normalize.md" %}
# ⚙️ Funzione `trgfn_istanze_utilities_normalize`

```sql
CREATE FUNCTION trgfn_istanze_utilities_normalize()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_istanze_utilities_normalize()
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
