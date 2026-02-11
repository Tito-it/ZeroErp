{% include-markdown "it/dbzero/pagamenti/manual/fn_get_saldo_fattura.md" %}
# ⚙️ Funzione `fn_get_saldo_fattura`

```sql
CREATE FUNCTION fn_get_saldo_fattura(p_fattura_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION pagamenti.fn_get_saldo_fattura(p_fattura_id bigint)
 RETURNS TABLE(saldo numeric, has_movimenti boolean)
 LANGUAGE plpgsql
AS $function$
BEGIN
  -- =========================================================
  -- Scopo:
  --   Restituisce saldo movimenti per fattura e flag presenza.
  -- =========================================================

  IF p_fattura_id IS NULL OR p_fattura_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'database', 'pagamenti.fn_get_saldo_fattura', 'E_GENERICO',
      jsonb_build_object('detail','fattura_id obbligatoria'),
      NULL::uuid,
      'fattura_id non valido'
    );
  END IF;

  RETURN QUERY
  SELECT
    COALESCE(SUM(m.importo), 0)::numeric AS saldo,
    (COUNT(*) > 0) AS has_movimenti
  FROM pagamenti.vendite_movimenti m
  WHERE m.fattura_id = p_fattura_id
    AND m.attivo IS TRUE;
END;
$function$
```

---
{% include-markdown "signature-core.md" %}
