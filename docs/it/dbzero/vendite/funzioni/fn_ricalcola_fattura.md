{% include-markdown "it/dbzero/vendite/manual/fn_ricalcola_fattura.md" %}
# ⚙️ Funzione `fn_ricalcola_fattura`

```sql
CREATE FUNCTION fn_ricalcola_fattura(p_fattura_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_ricalcola_fattura(p_fattura_id bigint)
 RETURNS TABLE(imponibile_tot numeric, imposta_tot numeric, totale_escluso_imponibile numeric, totale_doc numeric)
 LANGUAGE plpgsql
AS $function$
BEGIN
  -- =========================================================
  -- Scopo:
  --   Wrapper per ricalcolo riepiloghi IVA e totali testata.
  -- =========================================================

  PERFORM vendite.fn_ricalcola_riepilogo_iva_fattura(p_fattura_id);

  RETURN QUERY
  SELECT *
  FROM vendite.fn_ricalcola_totali_fattura(p_fattura_id);
END;
$function$
```

---
{% include-markdown "signature-core.md" %}
