{% include-markdown "it/dbzero/pagamenti/manual/fn_get_saldo_fattura_contabili.md" %}
# ⚙️ Funzione `fn_get_saldo_fattura_contabili`

```sql
CREATE FUNCTION fn_get_saldo_fattura_contabili(p_fattura_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION pagamenti.fn_get_saldo_fattura_contabili(p_fattura_id bigint)
 RETURNS TABLE(saldo_contabile numeric, has_righe_postabili boolean)
 LANGUAGE plpgsql
AS $function$
BEGIN
  -- =========================================================
  -- Scopo:
  --   Restituisce il saldo contabile "in lavorazione" di una
  --   fattura, sommando solo righe contabili in stati postabili.
  -- =========================================================

  IF p_fattura_id IS NULL OR p_fattura_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'database', 'pagamenti.fn_get_saldo_fattura_contabili', 'E_GENERICO',
      jsonb_build_object('detail','fattura_id obbligatoria'),
      NULL::uuid,
      'fattura_id non valido'
    );
  END IF;

  RETURN QUERY
  SELECT
    COALESCE(SUM(cr.importo), 0)::numeric AS saldo_contabile,
    (COUNT(*) > 0) AS has_righe_postabili
  FROM pagamenti.vendite_contabili_righe cr
  JOIN pagamenti.vendite_contabili_righe_stati s
    ON s.id = cr.stato_id
  JOIN pagamenti.vendite_contabili c
    ON c.id = cr.contabile_id
  LEFT JOIN pagamenti.vendite_contabili_stati cs
    ON cs.id = c.stato_id
  WHERE cr.fattura_id = p_fattura_id
    AND cr.attivo IS TRUE
    AND s.is_postabile IS TRUE
    AND COALESCE(cs.is_final, false) IS FALSE;
END;
$function$
```

---
{% include-markdown "signature-core.md" %}
