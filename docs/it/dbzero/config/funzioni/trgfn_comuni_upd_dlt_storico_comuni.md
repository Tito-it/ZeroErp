# Funzione `trgfn_comuni_upd_dlt_storico_comuni`

```sql
CREATE FUNCTION trgfn_comuni_upd_dlt_storico_comuni()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION config.trgfn_comuni_upd_dlt_storico_comuni()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  IF TG_OP = 'UPDATE' AND NEW.storicizza THEN

    -- 1) Se esiste uno snapshot aperto, lo chiudo; altrimenti lo creo da OLD
    IF EXISTS (
      SELECT 1
        FROM storico.comuni
       WHERE comune_id = OLD.id
         AND valid_to IS NULL
    ) THEN
      UPDATE storico.comuni
         SET valid_to = CURRENT_DATE
       WHERE comune_id = OLD.id
         AND valid_to   IS NULL;
    ELSE
      INSERT INTO storico.comuni (
        comune_id,
        descrizione,
        extra_country,
        
        valid_to,
        data_insert,
        user_insert
      )
      VALUES (
        OLD.id,
        OLD.descrizione,
        OLD.extra_country,
        
        CURRENT_DATE,
        NOW(),
        CURRENT_USER
      );
    END IF;

    -- 2) Inserisco sempre lo snapshot NEW
    INSERT INTO storico.comuni (
      comune_id,
      descrizione,
      extra_country,
      valid_from,
      data_insert,
      user_insert
    )
    VALUES (
      NEW.id,
      NEW.descrizione,
      NEW.extra_country,
      CURRENT_DATE,
      NOW(),
      CURRENT_USER
    );

    -- 3) Reset del flag prima dell’UPDATE
    NEW.storicizza := false;

    RETURN NEW;

  ELSIF TG_OP = 'DELETE'  THEN

    -- 1) Se esiste uno snapshot aperto, lo chiudo; altrimenti creo uno “finale”
    IF EXISTS (
      SELECT 1
        FROM storico.comuni
       WHERE comune_id = OLD.id
         AND valid_to IS NULL
    ) THEN
      UPDATE storico.comuni
         SET valid_to = CURRENT_DATE
       WHERE comune_id = OLD.id
         AND valid_to   IS NULL;
    ELSE
      INSERT INTO storico.comuni (
        comune_id,
        descrizione,
        extra_country,
        valid_from,
        valid_to,
        data_insert,
        user_insert
      )
      VALUES (
        OLD.id,
        OLD.descrizione,
        OLD.extra_country,
        CURRENT_DATE,
        CURRENT_DATE,
        NOW(),
        CURRENT_USER
      );
    END IF;

    RETURN OLD;
  END IF;

  -- Per tutti gli altri casi (UPDATE senza flag, INSERT, ecc.)
  IF TG_OP = 'UPDATE' THEN
    RETURN NEW;
  ELSE
    RETURN OLD;
  END IF;
END;
$function$
```