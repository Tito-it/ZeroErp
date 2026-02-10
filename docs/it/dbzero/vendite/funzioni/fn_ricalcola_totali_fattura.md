{% include-markdown "it/dbzero/vendite/manual/fn_ricalcola_totali_fattura.md" %}
# ⚙️ Funzione `fn_ricalcola_totali_fattura`

```sql
CREATE FUNCTION fn_ricalcola_totali_fattura(p_fattura_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_ricalcola_totali_fattura(p_fattura_id bigint)
 RETURNS TABLE(imponibile_tot numeric, imposta_tot numeric, totale_escluso_imponibile numeric, totale_doc numeric)
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_imponibile_tot numeric := 0;
  v_imposta_tot numeric := 0;
  v_totale_escluso_imponibile numeric := 0;
  v_bollo numeric := 0;
  v_arr_prec numeric := 0;
  v_arr_att numeric := 0;
  v_totale_doc numeric := 0;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Ricalcolo totali testata fattura.
  --
  -- Regole:
  --   - p_fattura_id obbligatorio
  --   - imponibile/imposta da riepiloghi IVA
  --   - totale_escluso_imponibile da righe con articolo.fondo_fattura=true
  -- =========================================================

  IF p_fattura_id IS NULL OR p_fattura_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'database', 'vendite.fn_ricalcola_totali_fattura', 'E_GENERICO',
      jsonb_build_object('detail','p_fattura_id obbligatorio'),
      NULL::uuid,
      'p_fattura_id obbligatorio e > 0'
    );
  END IF;

  -- Ricalcolo imponibile_tot e imposta_tot da riepiloghi IVA
  SELECT
    COALESCE(SUM(r.imponibile), 0),
    COALESCE(SUM(r.imposta), 0)
    INTO v_imponibile_tot, v_imposta_tot
  FROM vendite.fatture_riepiloghi_iva r
  WHERE r.fattura_id = p_fattura_id;

  -- Ricalcolo totale_escluso_imponibile da righe con articolo.fondo_fattura=true
  SELECT
    COALESCE(SUM(COALESCE(fr.totale_riga, fr.imponibile_riga, 0)), 0)
    INTO v_totale_escluso_imponibile
  FROM vendite.fatture_righe fr
  JOIN catalogo.articoli a
    ON a.id = fr.articolo_id
  WHERE fr.fattura_id = p_fattura_id
    AND a.fondo_fattura IS TRUE;

  -- Recupero bollo e arrotondamenti da testata fattura questo va rivisto
  SELECT
    COALESCE(f.bollo_importo, 0),
    COALESCE(f.arrotondamento_precedente, 0),
    COALESCE(f.arrotondamento_attuale, 0)
    INTO v_bollo, v_arr_prec, v_arr_att
  FROM vendite.fatture f
  WHERE f.id = p_fattura_id;

  -- Calcolo totale_doc come somma di imponibile_tot, imposta_tot, totale_escluso_imponibile, bollo e arrotondamenti
  v_totale_doc := v_imponibile_tot
    + v_imposta_tot
    + v_totale_escluso_imponibile
    + v_bollo
    + v_arr_prec
    + v_arr_att;


  UPDATE vendite.fatture
     SET imponibile_tot = v_imponibile_tot,
         imposta_tot = v_imposta_tot,
         totale_escluso_imponibile = v_totale_escluso_imponibile,
         totale_doc = v_totale_doc,
         data_update = now(),
         user_update = current_user
   WHERE id = p_fattura_id;

  RETURN QUERY
  SELECT v_imponibile_tot, v_imposta_tot, v_totale_escluso_imponibile, v_totale_doc;
END;
$function$
```

---
{% include-markdown "signature-core.md" %}
