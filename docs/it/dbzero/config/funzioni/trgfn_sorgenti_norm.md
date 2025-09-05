# ⚙️ Funzione `trgfn_sorgenti_norm`

```sql
CREATE FUNCTION trgfn_sorgenti_norm()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION config.trgfn_sorgenti_norm()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  IF NEW.codice_interno IS NOT NULL THEN
    NEW.codice_interno := upper(btrim(NEW.codice_interno));
  END IF;
  RETURN NEW;
END$function$
```

---
{% include-markdown "signature-core.md" %}
