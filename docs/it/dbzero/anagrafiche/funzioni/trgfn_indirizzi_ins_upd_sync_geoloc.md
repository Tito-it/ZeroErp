{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_indirizzi_ins_upd_sync_geoloc.md" %}
# ⚙️ Funzione `trgfn_indirizzi_ins_upd_sync_geoloc`

```sql
CREATE FUNCTION trgfn_indirizzi_ins_upd_sync_geoloc()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_indirizzi_ins_upd_sync_geoloc()
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
```

---
{% include-markdown "signature-core.md" %}
