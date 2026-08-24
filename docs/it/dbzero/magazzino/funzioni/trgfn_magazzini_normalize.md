{% include-markdown "it/dbzero/magazzino/manual/trgfn_magazzini_normalize.md" %}
# ⚙️ Funzione `trgfn_magazzini_normalize`

```sql
CREATE FUNCTION trgfn_magazzini_normalize()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION magazzino.trgfn_magazzini_normalize()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  IF NEW.codice IS NOT NULL THEN
    NEW.codice := upper(btrim(NEW.codice));
  END IF;
  RETURN NEW;
END$function$

COMMENT ON FUNCTION magazzino.trgfn_magazzini_normalize()
IS 'Normalizza i dati magazzino.';
```

---
{% include-markdown "signature-core.md" %}
