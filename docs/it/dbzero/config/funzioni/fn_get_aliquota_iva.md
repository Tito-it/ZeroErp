{% include-markdown "it/dbzero/config/manual/fn_get_aliquota_iva.md" %}
# ⚙️ Funzione `fn_get_aliquota_iva`

```sql
CREATE FUNCTION fn_get_aliquota_iva(p_iva_id integer, p_stato_id integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION config.fn_get_aliquota_iva(p_iva_id integer, p_stato_id integer)
 RETURNS numeric
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_aliquota config.iva.aliquota_iva%TYPE;
BEGIN
    -- Guard: p_iva_id obbligatorio
    IF p_iva_id IS NULL OR p_iva_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'config',
            'fn_get_aliquota_iva',
            'E_PARAMETRO_INVALIDO',
            jsonb_build_object(
                'parametro', 'p_iva_id',
                'valore', p_iva_id
            ),
            NULL::uuid,
            'p_iva_id obbligatorio e > 0'
        );
    END IF;

    -- Recupera aliquota con override per stato
    SELECT COALESCE(s.aliquota_override, i.aliquota_iva)
      INTO v_aliquota
      FROM config.iva i
      LEFT JOIN config.iva_stati s
        ON s.iva_id = i.id
       AND s.stato_id = p_stato_id
     WHERE i.id = p_iva_id;

    IF v_aliquota IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'config',
            'fn_get_aliquota_iva',
            'E_CODICE',
            jsonb_build_object('iva_id', p_iva_id),
            NULL::uuid,
            p_iva_id::text, 'config.iva'
        );
    END IF;

    RETURN v_aliquota;
END;
$function$

COMMENT ON FUNCTION config.fn_get_aliquota_iva(p_iva_id integer, p_stato_id integer)
IS 'Aliquota IVA con override per stato (config.iva_stati). Errori: E_PARAMETRO_INVALIDO, E_CODICE.';
```

---
{% include-markdown "signature-core.md" %}
