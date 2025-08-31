# ⚙️ Funzione `trgfn_fornitori_guard`

```sql
CREATE FUNCTION trgfn_fornitori_guard()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.trgfn_fornitori_guard()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  -- Normalizza canale_fe (uppercase, no spazi)
  IF NEW.canale_fe IS NOT NULL THEN
    NEW.canale_fe := upper(regexp_replace(NEW.canale_fe, '\s+', '', 'g'));
  END IF;


  RETURN NEW;
END$function$
```

---
{% include-markdown "signature-core.md" %}
