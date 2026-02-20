# ⚙️ Funzione `trgfn_ddt_normalize`

```sql
CREATE FUNCTION trgfn_ddt_normalize()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_ddt_normalize()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  ----------------------------------------------------------------
  -- Imposta anno/data se numero e' presente e anno/data mancanti
  IF TG_OP = 'INSERT' AND (NEW.numero IS NOT NULL AND btrim(NEW.numero) <> '') THEN
    IF NEW.anno IS NULL OR NEW.anno = 0 THEN
      NEW.anno := EXTRACT(YEAR FROM CURRENT_DATE)::smallint;
    END IF;
    IF NEW.data IS NULL  THEN
      NEW.data := CURRENT_DATE;
    END IF;
  END IF;

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_ddt_normalize()
IS 'Normalize: imposta anno/data se numero presente e valori mancanti.';
```

---
{% include-markdown "signature-core.md" %}
