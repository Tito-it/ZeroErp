              CREATE OR REPLACE FUNCTION config.trgfn_stradario_upd_dlt_storico_stradario()
              RETURNS trigger AS $$
              BEGIN
                IF TG_OP = 'UPDATE' AND NEW.storicizza THEN

                  -- 1) Se esiste uno snapshot aperto, lo chiudo; altrimenti lo creo da OLD
                  IF EXISTS (
                    SELECT 1
                      FROM storico.stradario
                     WHERE stradario_id = OLD.id
                       AND valid_to IS NULL
                  ) THEN
                    UPDATE storico.stradario
                       SET valid_to = CURRENT_DATE
                     WHERE stradario_id = OLD.id
                       AND valid_to   IS NULL;
                  ELSE
                    INSERT INTO storico.stradario (
                      stradario_id,
                      stradario_generale_id, comune_id, codice_postale_id,
                      descrizione_via,
                      geoloc, extra_info,
                      valid_to,
                      data_insert, user_insert
                    )
                    VALUES (
                      OLD.id,
                      OLD.stradario_generale_id, OLD.comune_id, OLD.codice_postale_id,
                      (SELECT descrizione
                         FROM config.stradario_generale
                        WHERE id = OLD.stradario_generale_id),
                      OLD.geoloc, OLD.extra_info,
                      CURRENT_DATE,
                      NOW(),
                      CURRENT_USER
                    );
                  END IF;

                  -- 2) Inserisco sempre lo snapshot NEW
                  INSERT INTO storico.stradario (
                    stradario_id,
                    stradario_generale_id, comune_id, codice_postale_id,
                    descrizione_via,
                    geoloc, extra_info,
                    valid_from,
                    data_insert, user_insert
                  )
                  VALUES (
                    NEW.id,
                    NEW.stradario_generale_id, NEW.comune_id, NEW.codice_postale_id,
                    (SELECT descrizione
                       FROM config.stradario_generale
                      WHERE id = NEW.stradario_generale_id),
                    NEW.geoloc, NEW.extra_info,
                    CURRENT_DATE,
                    NOW(),
                    CURRENT_USER
                  );

                  -- 3) Reset del flag prima dell’UPDATE
                  NEW.storicizza := false;

                  RETURN NEW;

                ELSIF TG_OP = 'DELETE' THEN

                  -- 1) Se esiste uno snapshot aperto, lo chiudo; altrimenti creo uno “finale”
                  IF EXISTS (
                    SELECT 1
                      FROM storico.stradario
                     WHERE stradario_id = OLD.id
                       AND valid_to IS NULL
                  ) THEN
                    UPDATE storico.stradario
                       SET valid_to = CURRENT_DATE
                     WHERE stradario_id = OLD.id
                       AND valid_to   IS NULL;
                  ELSE
                    INSERT INTO storico.stradario (
                      stradario_id,
                      stradario_generale_id, comune_id, codice_postale_id,
                      descrizione_via,
                      geoloc, extra_info,
                      valid_to,
                      data_insert, user_insert
                    )
                    VALUES (
                      OLD.id,
                      OLD.stradario_generale_id, OLD.comune_id, OLD.codice_postale_id,
                      (SELECT descrizione
                         FROM config.stradario_generale
                        WHERE id = OLD.stradario_generale_id),
                      OLD.geoloc, OLD.extra_info,
                      CURRENT_DATE,
                      NOW(),
                      CURRENT_USER
                    );
                  END IF;

                  RETURN OLD;
                END IF;

                -- Per tutte le altre operazioni (UPDATE senza flag, INSERT, ecc.)
                IF TG_OP = 'UPDATE' THEN
                  RETURN NEW;
                ELSE
                  RETURN OLD;
                END IF;
              END;
              $$ LANGUAGE plpgsql;
