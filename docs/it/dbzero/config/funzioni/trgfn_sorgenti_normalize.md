{% include-markdown "it/dbzero/config/manual/trgfn_sorgenti_normalize.md" %}
# ⚙️ Funzione `trgfn_sorgenti_normalize`

```sql
CREATE FUNCTION trgfn_sorgenti_normalize()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION config.trgfn_sorgenti_normalize()
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

</div>

---
{% include-markdown "signature-core.md" %}
