{% include-markdown "it/dbzero/vendite/manual/fn_get_totale_fondi_fattura.md" %}
# ⚙️ Funzione `fn_get_totale_fondi_fattura`

```sql
CREATE FUNCTION fn_get_totale_fondi_fattura(p_fattura_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_get_totale_fondi_fattura(p_fattura_id bigint)
 RETURNS numeric
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_totale vendite.fatture_fondi_fattura.importo%TYPE;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Restituisce il totale fondi fattura attivi per la fattura.
  -- =========================================================

  IF p_fattura_id IS NULL OR p_fattura_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_get_totale_fondi_fattura', 'E_GENERICO',
      jsonb_build_object(
        'scope','FATTURA',
        'severity','C',
        'code','E_GENERICO',
        'lotto_id', NULL,
        'fattura_id', p_fattura_id,
        'context', jsonb_build_object('detail','fattura_id obbligatoria')
      ),
      NULL::uuid,
      'fattura_id non valido'
    );
  END IF;

  SELECT COALESCE(SUM(ff.importo), 0)
    INTO v_totale
    FROM vendite.fatture_fondi_fattura ff
   WHERE ff.fattura_id = p_fattura_id
     AND ff.attivo IS TRUE;

  RETURN v_totale;
END;
$function$

COMMENT ON FUNCTION vendite.fn_get_totale_fondi_fattura(p_fattura_id bigint)
IS 'Restituisce il totale dei fondi fattura attivi associati alla fattura.';
```

---
{% include-markdown "signature-core.md" %}
