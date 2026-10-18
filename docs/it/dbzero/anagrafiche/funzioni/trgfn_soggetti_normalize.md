{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_soggetti_normalize.md" %}
# ⚙️ Funzione `trgfn_soggetti_normalize`

```sql
CREATE FUNCTION trgfn_soggetti_normalize()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_soggetti_normalize()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  ------------------------------------------------------------------
  -- 1) Imposta stato_id di default da config.stati se e' NULL
  IF NEW.stato_id IS NULL THEN
    NEW.stato_id := script.fn_stato_proposto_id(TG_NAME);           -- cast al tipo integer di stato_id
  END IF;

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_soggetti_normalize()
IS 'Normalize: imposta stato_id default (script.fn_stato_proposto_id, rev 2026-10-18: prima state_code_iso3 con fn_get_default_by_param, ritirati; D-1 di Tid); generazione codice demandata al sistema_codici.';
```

---
{% include-markdown "signature-core.md" %}
