{% include-markdown "it/dbzero/vendite/manual/fn_sync_pagamento_fondo_fattura.md" %}
# ⚙️ Funzione `fn_sync_pagamento_fondo_fattura`

```sql
CREATE FUNCTION fn_sync_pagamento_fondo_fattura(p_fattura_figlia_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_sync_pagamento_fondo_fattura(p_fattura_figlia_id bigint)
 RETURNS TABLE(inserted_movimenti integer, updated_movimenti integer, annullati_source integer)
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_inserted INTEGER := 0;
    v_updated  INTEGER := 0;
    v_annullati INTEGER := 0;
BEGIN
    IF p_fattura_figlia_id IS NULL OR p_fattura_figlia_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_sync_pagamento_fondo_fattura', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_fattura_figlia_id', 'valore', p_fattura_figlia_id), NULL::uuid, 'p_fattura_figlia_id obbligatorio e > 0');
    END IF;

    SELECT s.inserted_righe, s.updated_righe, s.annullati_source INTO v_inserted, v_updated, v_annullati
      FROM vendite.fn_sync_contabili_fondo_fattura(p_fattura_figlia_id => p_fattura_figlia_id) s;

    RETURN QUERY SELECT v_inserted, v_updated, v_annullati;
END;
$function$

COMMENT ON FUNCTION vendite.fn_sync_pagamento_fondo_fattura(p_fattura_figlia_id bigint)
IS 'Wrapper deprecato: delega a fn_sync_contabili_fondo_fattura.';
```

---
{% include-markdown "signature-core.md" %}
