{% include-markdown "it/dbzero/script/manual/fn_check_ins_soggetto_ruolo.md" %}
# Funzione `fn_check_ins_soggetto_ruolo`

```sql
CREATE FUNCTION fn_check_ins_soggetto_ruolo(p_soggetto_id uuid, p_soggetto_ruolo_id integer, p_cd_int_ruolo character varying)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_check_ins_soggetto_ruolo(p_soggetto_id uuid, p_soggetto_ruolo_id integer, p_cd_int_ruolo character varying)
 RETURNS integer
 LANGUAGE plpgsql
AS $function$
  DECLARE
      v_ruolo_id   INTEGER;
      v_new_id     INTEGER;
      v_count      INTEGER;
  BEGIN

      -- Se p_soggetto_ruolo_id IS NULL o = 0:
      --   - Recupera il ruolo_id corrispondente a cd_int_ruolo
      --   - Inserisce in anagrafiche.soggetti_ruoli un nuovo record:
      --       (soggetto_id = p_soggetto_id, ruolo_id = <quello trovato>, user_insert = current_user)
      --   - Restituisce l'id del record appena creato.
      --
      -- Se p_soggetto_ruolo_id IS NOT NULL e > 0:
      --   - Controlla che esista un record in anagrafiche.soggetti_ruoli con
      --       id = p_soggetto_ruolo_id
      --       soggetto_id = p_soggetto_id
      --       ruolo_id = <id trovato da cd_int_ruolo>
      --   - Se non lo trova, RAISE EXCEPTION
      --   - Se lo trova, restituisce p_soggetto_ruolo_id


      -- 1) Trovo l'ID del ruolo corrispondente a cd_int_ruolo
      SELECT r.id
        INTO v_ruolo_id
      FROM config.tipi_ruoli r
      WHERE r.cd_int_ruolo = p_cd_int_ruolo
      LIMIT 1;

      IF v_ruolo_id IS NULL THEN
           
            RAISE EXCEPTION '%', 
            script.fn_get_messaggio(
            'E_COD_INT_RUOLO', '',
            VARIADIC ARRAY[
                p_cd_int_ruolo::text
                ]
                );				
      END IF;

      -- 2) Se soggetto_ruolo_id non è passato (NULL o 0), creiamo un nuovo record
      IF p_soggetto_ruolo_id IS NULL OR p_soggetto_ruolo_id = 0 THEN
          INSERT INTO anagrafiche.soggetti_ruoli(
              soggetto_id,
              ruolo_id,
              user_insert
          ) VALUES (
              p_soggetto_id,
              v_ruolo_id,
              current_user
          )
          RETURNING id
          INTO v_new_id;

          RETURN v_new_id;
      END IF;

      -- 3) Altrimenti (p_soggetto_ruolo_id > 0), verifico che quel record esista e corrisponda
      SELECT COUNT(*) 
        INTO v_count
      FROM anagrafiche.soggetti_ruoli sr
      WHERE sr.id         = p_soggetto_ruolo_id
        AND sr.soggetto_id = p_soggetto_id
        AND sr.ruolo_id    = v_ruolo_id;

      IF v_count = 0 THEN
              RAISE EXCEPTION '%', 
          script.fn_get_messaggio(
          'E_SOGGETTI_RUOLI', '',
          VARIADIC ARRAY[
            p_soggetto_ruolo_id::text,
            p_soggetto_id::text,
            v_ruolo_id::text
              ]
              );
      END IF;

      -- Se siamo qui, il record esiste: restituisco lo stesso ID passato
      RETURN p_soggetto_ruolo_id;
  END;
  $function$
```