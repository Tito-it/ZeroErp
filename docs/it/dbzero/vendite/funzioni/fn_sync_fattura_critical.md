{% include-markdown "it/dbzero/vendite/manual/fn_sync_fattura_critical.md" %}
# ⚙️ Funzione `fn_sync_fattura_critical`

```sql
CREATE FUNCTION fn_sync_fattura_critical(p_fattura_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_sync_fattura_critical(p_fattura_id bigint)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_has_critical BOOLEAN;
BEGIN
    IF p_fattura_id IS NULL OR p_fattura_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_sync_fattura_critical', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_fattura_id', 'valore', p_fattura_id), NULL::uuid, 'p_fattura_id obbligatorio e > 0');
    END IF;

    SELECT EXISTS (SELECT 1 FROM vendite.fatture_log WHERE fattura_id = p_fattura_id AND disabilitato IS FALSE AND status = 'C') INTO v_has_critical;

    UPDATE vendite.fatture SET critical = COALESCE(v_has_critical, FALSE), data_update = now(), user_update = current_user WHERE id = p_fattura_id;
END;
$function$

COMMENT ON FUNCTION vendite.fn_sync_fattura_critical(p_fattura_id bigint)
IS 'Allinea fatture.critical in base ai log attivi di gravita C.';
```

</div>

---
{% include-markdown "signature-core.md" %}
