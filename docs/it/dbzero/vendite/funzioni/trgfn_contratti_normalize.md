{% include-markdown "it/dbzero/vendite/manual/trgfn_contratti_normalize.md" %}
# ⚙️ Funzione `trgfn_contratti_normalize`

```sql
CREATE FUNCTION trgfn_contratti_normalize()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_contratti_normalize()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  ----------------------------------------------------------------
  -- Imposta data se numero e' presente e data mancante
  IF TG_OP = 'INSERT' AND (NEW.numero IS NOT NULL AND btrim(NEW.numero) <> '') THEN
    IF NEW.data IS NULL  THEN
      NEW.data := CURRENT_DATE;
    END IF;
  END IF;

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_contratti_normalize()
IS 'Normalize: imposta data se numero presente e valore mancante.';
```

---
{% include-markdown "signature-core.md" %}
