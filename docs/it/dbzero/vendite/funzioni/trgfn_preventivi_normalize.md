{% include-markdown "it/dbzero/vendite/manual/trgfn_preventivi_normalize.md" %}
# ⚙️ Funzione `trgfn_preventivi_normalize`

```sql
CREATE FUNCTION trgfn_preventivi_normalize()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_preventivi_normalize()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  ----------------------------------------------------------------
  -- Imposta data se numero e' presente e data mancante
  IF TG_OP = 'INSERT' AND (NEW.numero IS NOT NULL AND btrim(NEW.numero) <> '') THEN
    IF NEW.data IS NULL  THEN
      NEW.data := script.fn_data_operativa();
    END IF;
  END IF;

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_preventivi_normalize()
IS 'Normalize: imposta data se numero presente e valore mancante.';
```

</div>

---
{% include-markdown "signature-core.md" %}
