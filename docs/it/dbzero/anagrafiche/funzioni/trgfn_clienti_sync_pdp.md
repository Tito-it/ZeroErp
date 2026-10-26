{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_clienti_sync_pdp.md" %}
# ⚙️ Funzione `trgfn_clienti_sync_pdp`

```sql
CREATE FUNCTION trgfn_clienti_sync_pdp()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_clienti_sync_pdp()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  IF NEW.istanza_utility_id IS NOT NULL THEN
    SELECT iu.pdp_id
    INTO NEW.pdp_id
    FROM anagrafiche.istanze_utilities iu
    WHERE iu.id = NEW.istanza_utility_id;

    -- opzionale: se non trovato, azzera pdp_id
    IF NOT FOUND THEN
      NEW.pdp_id := NULL;
    END IF;
  END IF;
  RETURN NEW;
END$function$

COMMENT ON FUNCTION anagrafiche.trgfn_clienti_sync_pdp()
IS 'Allinea la colonna denormalizzata pdp_id in base a anagrafiche.istanze_utilities(istanza_utility_id)';
```

</div>

---
{% include-markdown "signature-core.md" %}
