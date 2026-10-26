{% include-markdown "it/dbzero/vendite/manual/fn_log_lotto_esito_fatture.md" %}
# ⚙️ Funzione `fn_log_lotto_esito_fatture`

```sql
CREATE FUNCTION fn_log_lotto_esito_fatture(p_lotto_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_log_lotto_esito_fatture(p_lotto_id bigint)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_has_critical BOOLEAN;
    v_has_warning  BOOLEAN;
    v_status       CHARACTER;
BEGIN
    IF p_lotto_id IS NULL OR p_lotto_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_log_lotto_esito_fatture', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_lotto_id', 'valore', p_lotto_id), NULL::uuid, 'p_lotto_id obbligatorio e > 0');
    END IF;

    SELECT EXISTS (
        SELECT 1 FROM vendite.fatturazione_lotti_fatture lf
        JOIN vendite.fatture_log fl ON fl.fattura_id = lf.fattura_id
        WHERE lf.lotto_id = p_lotto_id AND fl.disabilitato IS FALSE AND fl.status = 'C'
    ) INTO v_has_critical;

    SELECT EXISTS (
        SELECT 1 FROM vendite.fatturazione_lotti_fatture lf
        JOIN vendite.fatture_log fl ON fl.fattura_id = lf.fattura_id
        WHERE lf.lotto_id = p_lotto_id AND fl.disabilitato IS FALSE AND fl.status = 'W'
    ) INTO v_has_warning;

    v_status := CASE WHEN v_has_critical THEN 'C' WHEN v_has_warning THEN 'W' ELSE 'I' END;

    PERFORM vendite.fn_log_pipeline_fase(p_lotto_id, NULL, 'Esito fatture lotto', v_status, NULL, jsonb_build_object('source', 'fatture_log'));
END;
$function$

COMMENT ON FUNCTION vendite.fn_log_lotto_esito_fatture(p_lotto_id bigint)
IS 'Esito lotto dai log fatture (C/W/I) → evento sintetico su fatturazione_lotti_log.';
```

</div>

---
{% include-markdown "signature-core.md" %}
