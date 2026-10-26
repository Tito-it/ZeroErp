{% include-markdown "it/dbzero/vendite/manual/fn_ricalcola_fattura.md" %}
# ⚙️ Funzione `fn_ricalcola_fattura`

```sql
CREATE FUNCTION fn_ricalcola_fattura(p_fattura_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_ricalcola_fattura(p_fattura_id bigint)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
BEGIN
    IF p_fattura_id IS NULL OR p_fattura_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_ricalcola_fattura', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_fattura_id', 'valore', p_fattura_id), NULL::uuid, 'p_fattura_id obbligatorio e > 0');
    END IF;

    PERFORM vendite.fn_ricalcola_riepilogo_iva_fattura(p_fattura_id);
    PERFORM vendite.fn_ricalcola_totali_fattura(p_fattura_id);
END;
$function$

COMMENT ON FUNCTION vendite.fn_ricalcola_fattura(p_fattura_id bigint)
IS 'Wrapper ricalcolo fattura: riepiloghi IVA + totali testata.';
```

</div>

---
{% include-markdown "signature-core.md" %}
