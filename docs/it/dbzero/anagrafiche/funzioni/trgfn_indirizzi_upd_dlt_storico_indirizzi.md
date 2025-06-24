# ⚙️ Funzione `trgfn_indirizzi_upd_dlt_storico_indirizzi`

```sql
CREATE FUNCTION trgfn_indirizzi_upd_dlt_storico_indirizzi()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_indirizzi_upd_dlt_storico_indirizzi()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  ----------------------------------------------------------------
  -- UPDATE: solo se modifica_storica = true
  ----------------------------------------------------------------
  IF TG_OP = 'UPDATE' AND NEW.modifica_storica THEN

    -- 1) Chiudo precedente snapshot o creo quello iniziale
    IF EXISTS (
      SELECT 1
        FROM storico.indirizzi
       WHERE indirizzi_id = OLD.id
         AND valid_to IS NULL
    ) THEN
      -- chiudo il precedente
      UPDATE storico.indirizzi
         SET valid_to = CURRENT_DATE
       WHERE indirizzi_id = OLD.id
         AND valid_to IS NULL;
    ELSE
      -- creo snapshot iniziale con i valori OLD
      INSERT INTO storico.indirizzi (
        soggetto_ruolo_id, tipo_indirizzo_id, indirizzi_dettaglio_id,
        indirizzo_libero, stato_id, administrative_area, locality,
        sublocality, postal_box, geoloc, comune_id, codice_postale_id,
        valid_from, valid_to, data_insert, user_insert, indirizzi_id
      ) VALUES (
        OLD.soggetto_ruolo_id, OLD.tipo_indirizzo_id, OLD.indirizzi_dettaglio_id,
        OLD.indirizzo_libero, OLD.stato_id,      OLD.administrative_area,
        OLD.locality,          OLD.sublocality,   OLD.postal_box,
        OLD.geoloc,            OLD.comune_id,     OLD.codice_postale_id,
        CURRENT_DATE,          CURRENT_DATE,      NOW(),
        CURRENT_USER,          OLD.id
      );
    END IF;

    -- 2) Inserisco sempre il snapshot con i valori NEW
    INSERT INTO storico.indirizzi (
      soggetto_ruolo_id, tipo_indirizzo_id, indirizzi_dettaglio_id,
      indirizzo_libero, stato_id, administrative_area, locality,
      sublocality, postal_box, geoloc, comune_id, codice_postale_id,
      valid_from, data_insert, user_insert, indirizzi_id
    ) VALUES (
      NEW.soggetto_ruolo_id, NEW.tipo_indirizzo_id, NEW.indirizzi_dettaglio_id,
      NEW.indirizzo_libero, NEW.stato_id,      NEW.administrative_area,
      NEW.locality,         NEW.sublocality,    NEW.postal_box,
      NEW.geoloc,           NEW.comune_id,      NEW.codice_postale_id,
      CURRENT_DATE,         NOW(),              CURRENT_USER,
      NEW.id
    );

    -- 3) Reset del flag PRIMA che l’UPDATE venga scritto
    NEW.modifica_storica := false;

    RETURN NEW;

  ----------------------------------------------------------------
  -- DELETE: solo se modifica_storica = true
  ----------------------------------------------------------------
  ELSIF TG_OP = 'DELETE'  THEN

    -- 1) Chiudo precedente snapshot o creo uno “finale”
    IF EXISTS (
      SELECT 1
        FROM storico.indirizzi
       WHERE indirizzi_id = OLD.id
         AND valid_to IS NULL
    ) THEN
      UPDATE storico.indirizzi
         SET valid_to = CURRENT_DATE
       WHERE indirizzi_id = OLD.id
         AND valid_to IS NULL;
    ELSE
      INSERT INTO storico.indirizzi (
        soggetto_ruolo_id, tipo_indirizzo_id, indirizzi_dettaglio_id,
        indirizzo_libero, stato_id, administrative_area, locality,
        sublocality, postal_box, geoloc, comune_id, codice_postale_id,
        valid_from, valid_to, data_insert, user_insert, indirizzi_id
      ) VALUES (
        OLD.soggetto_ruolo_id, OLD.tipo_indirizzo_id, OLD.indirizzi_dettaglio_id,
        OLD.indirizzo_libero, OLD.stato_id,      OLD.administrative_area,
        OLD.locality,         OLD.sublocality,   OLD.postal_box,
        OLD.geoloc,           OLD.comune_id,     OLD.codice_postale_id,
        CURRENT_DATE,         CURRENT_DATE,      NOW(),
        CURRENT_USER,         OLD.id
      );
    END IF;

    RETURN OLD;
  END IF;

  ----------------------------------------------------------------
  -- TUTTI GLI ALTRI CASI (UPDATE senza flag, INSERT, ecc.)
  ----------------------------------------------------------------
  IF TG_OP = 'UPDATE' THEN
    RETURN NEW;
  ELSE
    RETURN OLD;
  END IF;
END;
$function$
```