# ⚙️ Funzione `trgfn_preventivi_normalize`

```sql
CREATE FUNCTION trgfn_preventivi_normalize()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_preventivi_normalize()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  ----------------------------------------------------------------
  -- Imposta data se numero e' presente e data mancante
  IF TG_OP = 'INSERT' AND (NEW.numero IS NOT NULL AND btrim(NEW.numero) <> '') THEN
    IF NEW.data IS NULL OR NEW.data = 0 THEN
      NEW.data := CURRENT_DATE;
    END IF;
  END IF;

  RETURN NEW;
END;
$function$
```

---
{% include-markdown "signature-core.md" %}
