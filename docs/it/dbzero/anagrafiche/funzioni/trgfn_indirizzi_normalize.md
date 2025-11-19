{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_indirizzi_normalize.md" %}
# ⚙️ Funzione `trgfn_indirizzi_normalize`

```sql
CREATE FUNCTION trgfn_indirizzi_normalize()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_indirizzi_normalize()
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
      ELSE
          -- se non c'è indirizzo_dettaglio, allora imposto i valori di default
          IF NEW.stato_id IS NULL THEN  
            NEW.stato_id := script.fn_get_default_by_param(
              'config',           -- schema della tabella lookup
              'stati',            -- tabella di lookup
              'codice_iso3',        -- colonna di filtro in config.stati
              'state_code_iso3',  -- codice parametro in config.parameters
              TG_NAME             -- nome del trigger chiamante
            )::integer;           -- cast al tipo integer di stato_id
          END IF;   

    END IF;

    RETURN NEW;
  END;
  $function$
```

---
{% include-markdown "signature-core.md" %}
