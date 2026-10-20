{% include-markdown "it/dbzero/vendite/manual/fn_sync_fatture_log_critical_lotto.md" %}
# ⚙️ Funzione `fn_sync_fatture_log_critical_lotto`

```sql
CREATE FUNCTION fn_sync_fatture_log_critical_lotto(p_fattura_ids bigint[])
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_sync_fatture_log_critical_lotto(p_fattura_ids bigint[])
 RETURNS void
 LANGUAGE plpgsql
AS $function$
BEGIN
  -- =========================================================
  -- Scopo:
  --   Ricalcola flag critical sulle fatture toccate da log
  --   e propaga stato_esecuzione sul ponte lotto-fattura.
  --
  -- Regole:
  --   - mapping stato_esecuzione delegato a helper condiviso
  --   - has_critical=true -> ERRORE
  --   - lotto IN_ESECUZIONE -> RUNNING
  --   - altri casi attivi -> COMPLETED
  --
  -- rev 2026-08-04 (D-M): via il predicato su lf.esclusa e
  --   l'argomento p_esclusa all'helper.
  -- =========================================================
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
     SET stato_esecuzione = vendite.fn_resolve_stato_esecuzione(
           p_stato_source => l.stato_lotto,
           p_has_critical => calc.has_critical,
           p_fatturato => false,
           p_default_stato_esecuzione => 'COMPLETED'
         ),
         data_update = now(),
         user_update = current_user
    FROM calc,
         vendite.fatturazione_lotti l
   WHERE lf.fattura_id = calc.fattura_id
     AND l.id = lf.lotto_id
     AND (
           l.stato_lotto = 'IN_ESECUZIONE'
           OR l.stato_operativo = 'APERTO'
         )
     AND lf.stato_esecuzione IS DISTINCT FROM vendite.fn_resolve_stato_esecuzione(
           p_stato_source => l.stato_lotto,
           p_has_critical => calc.has_critical,
           p_fatturato => false,
           p_default_stato_esecuzione => 'COMPLETED'
         );
END
$function$

COMMENT ON FUNCTION vendite.fn_sync_fatture_log_critical_lotto(p_fattura_ids bigint[])
IS 'Ricalcola fatture.critical e propaga stato_esecuzione su lotti_fatture tramite helper condiviso. rev 2026-08-04 (D-M): via il predicato su lf.esclusa, che era una condizione sempre vera, e via l''argomento p_esclusa all''helper.';
```

</div>

---
{% include-markdown "signature-core.md" %}
