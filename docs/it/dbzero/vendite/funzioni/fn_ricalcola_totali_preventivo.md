{% include-markdown "it/dbzero/vendite/manual/fn_ricalcola_totali_preventivo.md" %}
# ⚙️ Funzione `fn_ricalcola_totali_preventivo`

```sql
CREATE FUNCTION fn_ricalcola_totali_preventivo(p_preventivo_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_ricalcola_totali_preventivo(p_preventivo_id bigint)
 RETURNS TABLE(preventivo_id bigint, totale_imponibile numeric, totale_iva numeric, totale_documento numeric)
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_imponibile  vendite.preventivi.totale_imponibile%TYPE;
  v_iva         vendite.preventivi.totale_iva%TYPE;
  v_totale      vendite.preventivi.totale_documento%TYPE;
BEGIN
  -- ==========================================================
  -- Scopo:
  --   Ricalcolare i totali della testata preventivo a partire
  --   dalle righe attive con quantita > 0.
  --
  -- Regole:
  --   - imponibile = SUM(qta * prezzo * (1 - sconto/100))
  --   - iva = SUM(imponibile_riga * aliquota/100) per aliquota
  --   - totale = imponibile + iva
  --   - arrotondamento a 2 decimali
  --   - se nessuna riga attiva: totali = 0
  --
  -- Parametri:
  --   p_preventivo_id : ID del preventivo da ricalcolare
  --
  -- Ritorna:
  --   preventivo_id, totale_imponibile, totale_iva, totale_documento
  --
  -- Nota:
  --   Invocata anche dal trigger AFTER su preventivi_righe.
  -- ==========================================================

  -- Guard: parametro obbligatorio
  IF p_preventivo_id IS NULL OR p_preventivo_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_ricalcola_totali_preventivo',
      'E_PARAMETRO_INVALIDO',
      jsonb_build_object('param', 'p_preventivo_id', 'value', p_preventivo_id),
      NULL::uuid,
      'p_preventivo_id = ' || COALESCE(p_preventivo_id::text, 'NULL')
    );
  END IF;

  -- Calcola imponibile e IVA dalle righe attive.
  -- Arrotondamento per riga (correttezza fiscale): prima si arrotonda
  -- importo e IVA di ogni riga, poi si sommano i valori arrotondati.
  WITH righe_calc AS (
    SELECT
      ROUND(
        pr.quantita * pr.prezzo_unitario
        * (1 - COALESCE(pr.sconto_percentuale, 0) / 100),
        2
      ) AS importo_riga,
      ROUND(
        pr.quantita * pr.prezzo_unitario
        * (1 - COALESCE(pr.sconto_percentuale, 0) / 100)
        * COALESCE(iva.aliquota_iva, 0) / 100,
        2
      ) AS iva_riga
    FROM vendite.preventivi_righe pr
    LEFT JOIN config.iva iva ON iva.id = pr.iva_id
    WHERE pr.preventivo_id = p_preventivo_id
      AND pr.attivo IS TRUE
      AND pr.quantita > 0
  )
  SELECT
    COALESCE(SUM(rc.importo_riga), 0),
    COALESCE(SUM(rc.iva_riga), 0)
  INTO v_imponibile, v_iva
  FROM righe_calc rc;

  -- Totale documento
  v_totale := v_imponibile + v_iva;

  -- Aggiorna testata
  UPDATE vendite.preventivi p
     SET totale_imponibile = v_imponibile,
         totale_iva        = v_iva,
         totale_documento  = v_totale
   WHERE p.id = p_preventivo_id;

  -- Ritorna risultato
  RETURN QUERY
  SELECT p_preventivo_id, v_imponibile, v_iva, v_totale;
END
$function$

COMMENT ON FUNCTION vendite.fn_ricalcola_totali_preventivo(p_preventivo_id bigint)
IS 'Ricalcola totali preventivo (imponibile, IVA, totale) da righe attive. Invocata direttamente o via trigger AFTER su preventivi_righe.';
```

---
{% include-markdown "signature-core.md" %}
