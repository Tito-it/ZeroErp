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
  -- Generazione codice se assente
  IF NEW.codice IS NULL OR btrim(NEW.codice) = '' THEN
          NEW.codice := script.fn_generate_codice('fornitori');
  ELSE
          NEW.codice := btrim(NEW.codice);
  END IF;

  RETURN NEW;
END$function$
```

---
{% include-markdown "signature-core.md" %}
