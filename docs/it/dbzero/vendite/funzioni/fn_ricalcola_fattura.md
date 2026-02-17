{% include-markdown "it/dbzero/vendite/manual/fn_ricalcola_fattura.md" %}
# ⚙️ Funzione `fn_ricalcola_fattura`

```sql
CREATE FUNCTION fn_ricalcola_fattura(p_fattura_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_ricalcola_fattura(p_fattura_id bigint)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
BEGIN
  -- =========================================================
  -- Scopo:
  --   Wrapper per ricalcolo riepiloghi IVA e totali testata.
  -- =========================================================

  IF p_fattura_id IS NULL OR p_fattura_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_ricalcola_fattura', 'E_GENERICO',
      jsonb_build_object(
        'scope','FATTURA',
        'severity','C',
        'code','E_GENERICO',
        'lotto_id', NULL,
        'fattura_id', p_fattura_id,
        'context', jsonb_build_object('detail','p_fattura_id obbligatorio')
      ),
      NULL::uuid,
      'p_fattura_id obbligatorio e > 0'
    );
  END IF;

  PERFORM vendite.fn_ricalcola_riepilogo_iva_fattura(p_fattura_id);
  PERFORM vendite.fn_ricalcola_totali_fattura(p_fattura_id);
END;
$function$

COMMENT ON FUNCTION vendite.fn_ricalcola_fattura(p_fattura_id bigint)
IS 'Wrapper di ricalcolo fattura: esegue in sequenza ricalcolo riepiloghi IVA e ricalcolo totali testata.';
```

---
{% include-markdown "signature-core.md" %}
