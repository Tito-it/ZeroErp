{% include-markdown "it/dbzero/script/manual/fn_get_tipo_contatto_id.md" %}
# ⚙️ Funzione `fn_get_tipo_contatto_id`

```sql
CREATE FUNCTION fn_get_tipo_contatto_id(p_cod_int_tipo_contatto character varying)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_get_tipo_contatto_id(p_cod_int_tipo_contatto character varying)
 RETURNS integer
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_id  INTEGER;
    v_tx  UUID;
BEGIN
    -- 0) Recupero o genero il tx_id per il log
    v_tx := dbops.fn_get_or_create_session_tx_id();

    -- 1) Recupera l'ID del tipo di contatto
    -- rev 2026-08-04 (bonifica riferimenti morti, F2): la colonna di
    --   config.tipi_contatti e' `codice_interno`, non
    --   `cod_int_tipo_contatto`. Il nome del PARAMETRO resta com'e': e'
    --   parte della firma e cambiarlo romperebbe le chiamate a nome.
    SELECT id
      INTO v_id
      FROM config.tipi_contatti
    WHERE codice_interno = p_cod_int_tipo_contatto;

    -- 2) Se non trovato, loggo e sollevo eccezione
    IF v_id IS NULL THEN

        PERFORM script.fn_log_and_raise_error(
            'database',                                 -- p_area
            'script.fn_get_tipo_contatto_id',           -- p_function_name
            'E_DEFAULT_CONTATTO_MISSING',                -- p_error_code
            jsonb_build_object(                         -- p_context
              'cod_int_tipo_contatto', p_cod_int_tipo_contatto,
              'tabella', 'config.tipi_contatti',
              'campo', 'cod_int_tipo_contatto'
            ),
            v_tx ,                                        -- p_tx_id       
            VARIADIC ARRAY[]::text[]
        );

    END IF;

    RETURN v_id;
END;
$function$

COMMENT ON FUNCTION script.fn_get_tipo_contatto_id(p_cod_int_tipo_contatto character varying)
IS 'Recupera l''ID del tipo di contatto dal codice interno';
```

</div>

---
{% include-markdown "signature-core.md" %}
