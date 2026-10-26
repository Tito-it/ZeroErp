{% include-markdown "it/dbzero/pagamenti/manual/fn_get_saldo_fattura_contabili.md" %}
# ⚙️ Funzione `fn_get_saldo_fattura_contabili`

```sql
CREATE FUNCTION fn_get_saldo_fattura_contabili(p_fattura_id bigint, p_escludi_contabile_riga_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pagamenti.fn_get_saldo_fattura_contabili(p_fattura_id bigint, p_escludi_contabile_riga_id bigint DEFAULT NULL::bigint)
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
  --   - ⭐ p_escludi_contabile_riga_id (2026-09-18, P-6): chi sta
  --     scrivendo una riga chiede quanto era dichiarato PRIMA di
  --     se', o si confronterebbe con se' stesso. Stessa forma e
  --     stesso mestiere della sorella fn_get_saldo_rata.
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

  -- Un id di esclusione fornito e non positivo non esce da nessuna
  -- interfaccia: lo produce solo un chiamante rotto (TECNICO).
  IF p_escludi_contabile_riga_id IS NOT NULL AND p_escludi_contabile_riga_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'database', 'pagamenti.fn_get_saldo_fattura_contabili', 'E_PAGAMENTI_CHIAMATA_NON_VALIDA',
      jsonb_build_object(
        'detail', 'p_escludi_contabile_riga_id, se fornito, deve essere maggiore di zero',
        'p_fattura_id', p_fattura_id,
        'p_escludi_contabile_riga_id', p_escludi_contabile_riga_id
      ),
      NULL::uuid,
      'pagamenti.fn_get_saldo_fattura_contabili', 'p_escludi_contabile_riga_id, se fornito, deve essere maggiore di zero'
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
    AND cs.is_final IS FALSE
    -- La riga che sta scrivendo non conta se' stessa (stessa
    -- condizione del nucleo fn_get_saldi_rate, CTE `lav`).
    AND (p_escludi_contabile_riga_id IS NULL
         OR cr.id <> p_escludi_contabile_riga_id);
END;
$function$

COMMENT ON FUNCTION pagamenti.fn_get_saldo_fattura_contabili(p_fattura_id bigint, p_escludi_contabile_riga_id bigint)
IS 'Restituisce il saldo contabile fattura dalle righe in stato postabile sotto una testata non finale. ⭐ Rev 2026-09-18 (P-6, brief-db-distinta-ricerca-rate §4.6): + p_escludi_contabile_riga_id DEFAULT NULL — la riga che sta scrivendo chiede quanto era dichiarato PRIMA di se'', la stessa forma della sorella fn_get_saldo_rata e del nucleo fn_get_saldi_rate; senza, chi corregge una riga SENZA rata (fondo fattura, riga manuale «fattura si'', rata no») leggeva un in-lavorazione che contava la riga stessa. DROP + CREATE perche'' cambia la firma: un secondo overload accanto alla vecchia (bigint) sarebbe ambiguo per ogni chiamata a un argomento. Rev 2026-08-21: tolto il ramo "testata senza stato" (LEFT JOIN + COALESCE su is_final), reso impossibile dal NOT NULL su vendite_contabili.stato_id; guard di chiamata su E_PAGAMENTI_CHIAMATA_NON_VALIDA (TECNICO): un p_fattura_id <= 0 — e un p_escludi <= 0 — non esce da nessuna interfaccia, e l''operatore non ha niente da correggere; tipi ancorati con %TYPE in firma e RETURNS TABLE.';
```

</div>

---
{% include-markdown "signature-core.md" %}
