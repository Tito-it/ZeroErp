{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_indirizzi_base_normalize.md" %}
# ⚙️ Funzione `trgfn_indirizzi_base_normalize`

```sql
CREATE FUNCTION trgfn_indirizzi_base_normalize()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_indirizzi_base_normalize()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  IF NEW.indirizzo_dettaglio_id IS NOT NULL THEN
    -- pulisco i fallback/liberi (evita mix normalizzato+libero)
    NEW.stato_id             := NULL;
    NEW.indirizzo_libero     := NULL;
    NEW.comune_id            := NULL;
    NEW.codice_postale_id    := NULL;
    NEW.administrative_area  := NULL;
    NEW.locality             := NULL;
    NEW.sublocality          := NULL;
    NEW.postal_box           := NULL;

    -- geoloc: coerente con sync_geoloc (si ricalcola da indirizzi_dettaglio)
    NEW.geoloc := NULL;

  ELSE
    -- caso libero/internazionale: default minimo
    IF NEW.stato_id IS NULL THEN
      NEW.stato_id := script.fn_get_default_by_param(
        'config',
        'stati',
        'codice_iso3',
        'state_code_iso3',
        TG_NAME
      )::integer;
    END IF;
  END IF;

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_indirizzi_base_normalize()
IS 'Trigger function generica: normalizza indirizzi (ruolo/soggetto). Se indirizzo_dettaglio_id presente pulisce fallback/liberi; altrimenti imposta default su stato_id.';
```

---
{% include-markdown "signature-core.md" %}
