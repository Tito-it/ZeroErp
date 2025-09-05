# ⚙️ Funzione `trgfn_resellers_norm`

```sql
CREATE FUNCTION trgfn_resellers_norm()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_resellers_norm()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
 BEGIN
   IF NEW.codice IS NOT NULL THEN
     NEW.codice := upper(btrim(NEW.codice));
   ELSE
     NEW.codice := script.fn_generate_codice('resellers');
   END IF;
   RETURN NEW;
 END$function$
```

---
{% include-markdown "signature-core.md" %}
