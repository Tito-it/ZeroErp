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
  v_inserted integer := 0;
  v_updated integer := 0;
  v_annullati integer := 0;
BEGIN
  -- =========================================================
  -- DEPRECATA:
  --   mantenuta per retrocompatibilita'. La logica reale ora
  --   e' in vendite.fn_sync_contabili_fondo_fattura().
  -- =========================================================

  IF p_fattura_figlia_id IS NULL OR p_fattura_figlia_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_sync_pagamento_fondo_fattura', 'E_GENERICO',
      jsonb_build_object(
        'scope','FATTURA',
        'severity','C',
        'code','E_GENERICO',
        'lotto_id', NULL,
        'fattura_id', p_fattura_figlia_id,
        'context', jsonb_build_object('detail','p_fattura_figlia_id obbligatorio')
      ),
      NULL::uuid,
      'p_fattura_figlia_id non valido'
    );
  END IF;

  SELECT s.inserted_righe, s.updated_righe, s.annullati_source
    INTO v_inserted, v_updated, v_annullati
    FROM vendite.fn_sync_contabili_fondo_fattura(
      p_fattura_figlia_id => p_fattura_figlia_id
    ) s;

  RETURN QUERY
  SELECT v_inserted, v_updated, v_annullati;
END;
$function$

COMMENT ON FUNCTION vendite.fn_sync_pagamento_fondo_fattura(p_fattura_figlia_id bigint)
IS 'Wrapper deprecato: delega a fn_sync_contabili_fondo_fattura per retrocompatibilita.';
```

---
{% include-markdown "signature-core.md" %}
