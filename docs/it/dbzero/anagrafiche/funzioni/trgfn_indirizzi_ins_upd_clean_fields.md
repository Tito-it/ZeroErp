{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_indirizzi_ins_upd_clean_fields.md" %}
# ⚙️ Funzione `trgfn_indirizzi_ins_upd_clean_fields`

```sql
CREATE FUNCTION trgfn_indirizzi_ins_upd_clean_fields()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_indirizzi_ins_upd_clean_fields()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
  BEGIN
    IF NEW.indirizzo_dettaglio_id IS NOT NULL THEN
      -- pulisco i fallback
      NEW.stato_id             := NULL;
      NEW.indirizzo_libero     := NULL;
      NEW.comune_id            := NULL;
      NEW.codice_postale_id    := NULL;
      NEW.administrative_area  := NULL;
      NEW.locality             := NULL;
      NEW.sublocality          := NULL;
      NEW.postal_box           := NULL;
      -- geoloc puoi lasciarlo, oppure pulirlo se preferisci:
      NEW.geoloc := NULL;
    END IF;

    RETURN NEW;
  END;
  $function$
```
---
{% include-markdown "signature-core.md" %}
