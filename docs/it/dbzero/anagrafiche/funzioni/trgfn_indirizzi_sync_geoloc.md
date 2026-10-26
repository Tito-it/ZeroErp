{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_indirizzi_sync_geoloc.md" %}
# ⚙️ Funzione `trgfn_indirizzi_sync_geoloc`

```sql
CREATE FUNCTION trgfn_indirizzi_sync_geoloc()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_indirizzi_sync_geoloc()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
  BEGIN
    IF NEW.indirizzo_dettaglio_id IS NOT NULL THEN
      SELECT civic_geoloc INTO NEW.geoloc
        FROM anagrafiche.indirizzi_dettaglio
      WHERE id = NEW.indirizzo_dettaglio_id;
    END IF;
    RETURN NEW;
  END;
  $function$

COMMENT ON FUNCTION anagrafiche.trgfn_indirizzi_sync_geoloc()
IS 'La funzione di trigger per sincronizzare la geolocalizzazione degli indirizzi da anagrafiche.indirizzi_dettaglio.';
```

</div>

---
{% include-markdown "signature-core.md" %}
