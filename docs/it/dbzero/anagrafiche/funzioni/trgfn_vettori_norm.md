# ⚙️ Funzione `trgfn_vettori_norm`

```sql
CREATE FUNCTION trgfn_vettori_norm()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_vettori_norm()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
 BEGIN
   IF NEW.codice IS NOT NULL THEN
     NEW.codice := upper(btrim(NEW.codice));
   ELSE
     NEW.codice := script.fn_generate_codice('vettori');
   END IF;
   RETURN NEW;
 END$function$
```

---
{% include-markdown "signature-core.md" %}
