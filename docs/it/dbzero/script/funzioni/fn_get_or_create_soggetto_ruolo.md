# ⚙️ Funzione `fn_get_or_create_soggetto_ruolo`

```sql
CREATE FUNCTION fn_get_or_create_soggetto_ruolo(p_soggetto_id uuid, p_cd_int_ruolo character varying)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_get_or_create_soggetto_ruolo(p_soggetto_id uuid, p_cd_int_ruolo character varying)
 RETURNS integer
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_tipo_ruolo_id  integer;
    v_id        integer;
BEGIN

  -- ------------------------------------------------------------
  -- Funzione factory per ottenere o creare un legame in anagrafiche.soggetti_ruoli
  -- per la coppia (p_soggetto_id, p_cd_int_ruolo).
  -- Se il legame esiste già, ne restituisce l'ID; altrimenti lo crea.  
  -- Input :
  --   - p_soggetto_id:   UUID del soggetto in anagrafiche.soggetti
  --   - p_cd_int_ruolo:  Codice interno del ruolo (config.tipi_ruoli.codice_interno)
  -- Output:
  --   - integer: ID del record in anagrafiche.soggetti_ruoli
  -- ------------------------------------------------------------

    -- 1) Validazione soggetto
    IF p_soggetto_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'fn_get_or_create_soggetto_ruolo',
            'E_SOGGETTO_NULL',
            jsonb_build_object(
                'soggetto_id', p_soggetto_id,
                'codice_interno_ruolo', p_cd_int_ruolo
            ),
            NULL::uuid,
            p_soggetto_id::text, 
            p_cd_int_ruolo::text
        );
        --RAISE EXCEPTION 'soggetto_id mancante per fn_get_or_create_soggetto_ruolo.'
        --    USING ERRCODE = 'P0001';
    END IF;

    -- 2) Risolvo l''ID del ruolo da config.tipi_ruoli
    SELECT r.id
      INTO v_tipo_ruolo_id
      FROM config.tipi_ruoli r
    WHERE r.codice_interno = p_cd_int_ruolo
    LIMIT 1;

    IF v_tipo_ruolo_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'fn_get_or_create_soggetto_ruolo',
            'E_COD_INT_RUOLO',
            jsonb_build_object('codice_interno', p_cd_int_ruolo),
            NULL::uuid,
            p_cd_int_ruolo::text
        );
        --RAISE EXCEPTION 'Codice interno ruolo non valido in fn_get_or_create_soggetto_ruolo: %',
        --    p_cd_int_ruolo
        --    USING ERRCODE = 'P0001';
    END IF;

    -- 3) Cerco se esiste già un legame soggetto↔ruolo
    SELECT sr.id
      INTO v_id
      FROM anagrafiche.soggetti_ruoli sr
    WHERE sr.soggetto_id = p_soggetto_id
      AND sr.tipo_ruolo_id    = v_tipo_ruolo_id
    ORDER BY sr.id
    LIMIT 1;

    IF v_id IS NOT NULL THEN
        RETURN v_id;
    END IF;

    -- 4) Non esiste: provo a crearlo
    BEGIN
        INSERT INTO anagrafiche.soggetti_ruoli (
            soggetto_id,
            tipo_ruolo_id,     -- FIX tipo_ruolo_id. 
            extra
        )
        VALUES (
            p_soggetto_id,
            v_tipo_ruolo_id,
            '{}'::jsonb
        )
        RETURNING id INTO v_id;

        RETURN v_id;

    EXCEPTION
        WHEN unique_violation THEN
            -- Qualcun altro ha creato contemporaneamente lo stesso legame:
            -- rileggo e ritorno l'ID esistente.
            SELECT sr.id
              INTO v_id
              FROM anagrafiche.soggetti_ruoli sr
            WHERE sr.soggetto_id = p_soggetto_id
              AND sr.tipo_ruolo_id    = v_tipo_ruolo_id
            ORDER BY sr.id
            LIMIT 1;

            IF v_id IS NULL THEN
                -- Caso anomalo: unique_violation ma non trovo il record
                PERFORM script.fn_log_and_raise_error(
                    'database',
                    'fn_get_or_create_soggetto_ruolo',
                    'E_SOGGETTI_RUOLI_RACE',
                    jsonb_build_object(
                        'soggetto_id',    p_soggetto_id,
                        'ruolo_id',       v_tipo_ruolo_id,
                        'codice_interno', p_cd_int_ruolo
                    ),
                    NULL::uuid,
                    p_soggetto_id::text, 
                    v_tipo_ruolo_id::text,
                    p_cd_int_ruolo::text
                );
              --  RAISE EXCEPTION 'Race condition su soggetti_ruoli per soggetto %, ruolo %.',
              --      p_soggetto_id, v_tipo_ruolo_id
              --      USING ERRCODE = 'P0001';
            END IF;

            RETURN v_id;
    END;
END;
$function$
```

---
{% include-markdown "signature-core.md" %}
