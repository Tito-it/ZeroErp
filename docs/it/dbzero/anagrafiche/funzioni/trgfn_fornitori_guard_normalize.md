# ⚙️ Funzione `trgfn_fornitori_guard_normalize`

```sql
CREATE FUNCTION trgfn_fornitori_guard_normalize()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_fornitori_guard_normalize()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  -- Normalizza canale_fe (uppercase, no spazi)
  IF NEW.canale_fe IS NOT NULL THEN
    NEW.canale_fe := upper(regexp_replace(NEW.canale_fe, '\s+', '', 'g'));
  END IF;
  -- Normalizza codice se presente
  /*
  IF NEW.codice IS NOT NULL AND btrim(NEW.codice) <> '' THEN
    NEW.codice := btrim(NEW.codice);
  END IF;
  */  

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_fornitori_guard_normalize()
IS 'Guard/normalize: canale_fe e codice (no generazione automatica).';
```

---
{% include-markdown "signature-core.md" %}
