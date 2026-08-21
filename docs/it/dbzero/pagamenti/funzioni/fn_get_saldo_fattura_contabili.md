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
  --   fattura, sommando solo le righe contabili che stanno in
  --   uno stato postabile e appartengono a una testata non
  --   ancora finale.
  --
  -- Regole:
  --   - riga attiva e in stato is_postabile;
  --   - testata non finale. ⚠️ Dal 2026-08-21 lo stato della
  --     testata e' obbligatorio (20260821-12), quindi il JOIN e'
  --     interno: il ramo "testata senza stato" non esiste piu'.
  --   - ⚠️ questo filtro NON e' il presidio contro la riga
  --     appesa a una testata gia' chiusa (difetto C-5 del piano):
  --     quella la fermano i guard della slice 1. Qui si esclude
  --     un documento chiuso, non si ripara un'anomalia.
  -- =========================================================

  IF p_fattura_id IS NULL OR p_fattura_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'database', 'pagamenti.fn_get_saldo_fattura_contabili', 'E_PAGAMENTI_CHIAMATA_NON_VALIDA',
      jsonb_build_object(
        'detail', 'fattura_id obbligatoria e maggiore di zero',
        'p_fattura_id', p_fattura_id
      ),
      NULL::uuid,
      'pagamenti.fn_get_saldo_fattura_contabili', 'p_fattura_id (obbligatorio, maggiore di zero)'
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
  JOIN pagamenti.vendite_contabili_stati cs
    ON cs.id = c.stato_id
  WHERE cr.fattura_id = p_fattura_id
    AND cr.attivo IS TRUE
    AND s.is_postabile IS TRUE
    AND cs.is_final IS FALSE;
END;
$function$

COMMENT ON FUNCTION pagamenti.fn_get_saldo_fattura_contabili(p_fattura_id bigint)
IS 'Restituisce il saldo contabile fattura dalle righe in stato postabile sotto una testata non finale. Rev 2026-08-21: tolto il ramo "testata senza stato" (LEFT JOIN + COALESCE su is_final), reso impossibile dal NOT NULL su vendite_contabili.stato_id; guard di chiamata su E_PAGAMENTI_CHIAMATA_NON_VALIDA (TECNICO): un p_fattura_id <= 0 non esce da nessuna interfaccia, e l''operatore non ha niente da correggere; tipi ancorati con %TYPE in firma e RETURNS TABLE.';
```

---
{% include-markdown "signature-core.md" %}
