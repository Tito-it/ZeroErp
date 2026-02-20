{% include-markdown "it/dbzero/vendite/manual/fn_sync_fatture_log_critical_lotto.md" %}
# ⚙️ Funzione `fn_sync_fatture_log_critical_lotto`

```sql
CREATE FUNCTION fn_sync_fatture_log_critical_lotto(p_fattura_ids bigint[])
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_sync_fatture_log_critical_lotto(p_fattura_ids bigint[])
 RETURNS void
 LANGUAGE plpgsql
AS $function$
BEGIN
  -- =======================================================
  -- Scopo:
  --   Dato un set di fatture toccate da fatture_log:
  --   1) ricalcola fatture.critical su log attivi C
  --   2) aggiorna stato_esecuzione in lotti_fatture
  --      solo su lotti aperti o in esecuzione.
  -- =======================================================
  IF p_fattura_ids IS NULL OR array_length(p_fattura_ids, 1) IS NULL THEN
    RETURN;
  END IF;

  WITH changed AS (
    SELECT DISTINCT x.fattura_id
    FROM unnest(p_fattura_ids) AS x(fattura_id)
    WHERE x.fattura_id IS NOT NULL
      AND x.fattura_id > 0
  ),
  calc AS (
    SELECT
      c.fattura_id,
      EXISTS (
        SELECT 1
        FROM vendite.fatture_log fl
        WHERE fl.fattura_id = c.fattura_id
          AND fl.disabilitato IS FALSE
          AND fl.status = 'C'
      ) AS has_critical
    FROM changed c
  )
  UPDATE vendite.fatture f
     SET critical = calc.has_critical,
         data_update = now(),
         user_update = current_user
    FROM calc
   WHERE f.id = calc.fattura_id
     AND f.critical IS DISTINCT FROM calc.has_critical;

  WITH changed AS (
    SELECT DISTINCT x.fattura_id
    FROM unnest(p_fattura_ids) AS x(fattura_id)
    WHERE x.fattura_id IS NOT NULL
      AND x.fattura_id > 0
  ),
  calc AS (
    SELECT
      c.fattura_id,
      EXISTS (
        SELECT 1
        FROM vendite.fatture_log fl
        WHERE fl.fattura_id = c.fattura_id
          AND fl.disabilitato IS FALSE
          AND fl.status = 'C'
      ) AS has_critical
    FROM changed c
  )
  UPDATE vendite.fatturazione_lotti_fatture lf
     SET stato_esecuzione = CASE
           WHEN calc.has_critical THEN 'ERRORE'
           ELSE 'OK'
         END,
         data_update = now(),
         user_update = current_user
    FROM calc,
         vendite.fatturazione_lotti l
   WHERE lf.fattura_id = calc.fattura_id
     AND l.id = lf.lotto_id
     AND COALESCE(lf.esclusa, false) IS FALSE
     AND (
           l.stato_lotto = 'IN_ESECUZIONE'
           OR l.stato_operativo = 'APERTO'
         )
     AND lf.stato_esecuzione IS DISTINCT FROM CASE
           WHEN calc.has_critical THEN 'ERRORE'
           ELSE 'OK'
         END;
END
$function$

COMMENT ON FUNCTION vendite.fn_sync_fatture_log_critical_lotto(p_fattura_ids bigint[])
IS 'Ricalcola fatture.critical da fatture_log attivi (C) e propaga stato_esecuzione su lotti_fatture per lotti APERTO/IN_ESECUZIONE.';
```

---
{% include-markdown "signature-core.md" %}
