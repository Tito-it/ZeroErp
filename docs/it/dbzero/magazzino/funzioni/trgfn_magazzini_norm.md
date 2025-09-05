# ⚙️ Funzione `trgfn_magazzini_norm`

```sql
CREATE FUNCTION trgfn_magazzini_norm()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION magazzino.trgfn_magazzini_norm()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  IF NEW.codice IS NOT NULL THEN
    NEW.codice := upper(btrim(NEW.codice));
  END IF;
  RETURN NEW;
END$function$
```

---
{% include-markdown "signature-core.md" %}
