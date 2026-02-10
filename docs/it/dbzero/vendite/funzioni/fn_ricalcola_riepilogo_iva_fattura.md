{% include-markdown "it/dbzero/vendite/manual/fn_ricalcola_riepilogo_iva_fattura.md" %}
# ⚙️ Funzione `fn_ricalcola_riepilogo_iva_fattura`

```sql
CREATE FUNCTION fn_ricalcola_riepilogo_iva_fattura(p_fattura_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_ricalcola_riepilogo_iva_fattura(p_fattura_id bigint)
 RETURNS TABLE(deleted_rows integer, inserted_rows integer)
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_deleted_rows integer := 0;
  v_inserted_rows integer := 0;
  v_stato_id vendite.fatture.stato_doc_fiscale_id%TYPE;
  v_codice_interno config.stati_doc_fiscale.codice_interno%TYPE;
  v_stato_emittente_id anagrafiche.soggetti.stato_id%TYPE;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Ricalcolo riepiloghi IVA per singola fattura.
  --
  -- Regole:
  --   - p_fattura_id obbligatorio
  --   - ammesso solo per stati DRAFT/EMESSA
  --   - imponibile arrotondato a 2 dec (half-up)
  --   - imposta calcolata da imponibile arrotondato * aliquota_iva
  -- =========================================================

  IF p_fattura_id IS NULL OR p_fattura_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'database', 'vendite.fn_ricalcola_riepilogo_iva_fattura', 'E_GENERICO',
      jsonb_build_object('detail','p_fattura_id obbligatorio'),
      NULL::uuid,
      'p_fattura_id obbligatorio e > 0'
    );
  END IF;

  SELECT f.stato_doc_fiscale_id
    INTO v_stato_id
    FROM vendite.fatture f
   WHERE f.id = p_fattura_id;

  IF v_stato_id IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'database', 'vendite.fn_ricalcola_riepilogo_iva_fattura', 'E_GENERICO',
      jsonb_build_object('detail','stato_doc_fiscale_id mancante'),
      NULL::uuid,
      'Stato documento non valorizzato'
    );
  END IF;

  SELECT s.codice_interno
    INTO v_codice_interno
    FROM config.stati_doc_fiscale s
   WHERE s.id = v_stato_id;

  IF v_codice_interno NOT IN ('DRAFT', 'EMESSA') THEN
    PERFORM script.fn_log_and_raise_error(
      'database', 'vendite.fn_ricalcola_riepilogo_iva_fattura', 'E_GENERICO',
      jsonb_build_object('detail','ricalcolo IVA non ammesso', 'stato', v_codice_interno),
      NULL::uuid,
      concat('Ricalcolo IVA non ammesso per stato documento ', v_codice_interno)
    );
  END IF;

  -- recupero stato emittente per eventuale override aliquota IVA 
  SELECT s.stato_id
    INTO v_stato_emittente_id
    FROM vendite.fatture f
    JOIN anagrafiche.soggetti_ruoli sr
      ON sr.id = f.emittente_soggetto_ruolo_id
    JOIN anagrafiche.soggetti s
      ON s.id = sr.soggetto_id
   WHERE f.id = p_fattura_id;

  -- Reset riepiloghi esistenti (se presenti) 
  DELETE FROM vendite.fatture_riepiloghi_iva
   WHERE fattura_id = p_fattura_id;
  GET DIAGNOSTICS v_deleted_rows = ROW_COUNT;



  -- Ricalcolo riepiloghi IVA con imponibile arrotondato a 2 decimali (half-up) e 
  -- imposta calcolata da imponibile arrotondato * aliquota_iva, 
  -- recuperando aliquota con eventuale override per stato emittente tramite fn_get_aliquota_iva
  INSERT INTO vendite.fatture_riepiloghi_iva (
    fattura_id,
    iva_id,
    natura_id,
    esigibilita,
    split_payment,
    imponibile,
    imposta,
    arrotondamento
  )
  SELECT
    r.fattura_id,
    r.iva_id,
    n.id AS natura_id,
    r.esigibilita,
    r.split_payment,
    ROUND(SUM(COALESCE(r.imponibile_riga, 0)), 2) AS imponibile,
    ROUND(
      ROUND(SUM(COALESCE(r.imponibile_riga, 0)), 2)
      * (
          COALESCE(
            config.fn_get_aliquota_iva(r.iva_id, v_stato_emittente_id),
            0
          )::numeric / 100::numeric
        ),
      2
    ) AS imposta,
    SUM(COALESCE(r.imponibile_riga, 0)) - ROUND(SUM(COALESCE(r.imponibile_riga, 0)), 2) AS arrotondamento
  
  FROM vendite.fatture_righe r
  LEFT JOIN config.iva i
    ON i.id = r.iva_id
  LEFT JOIN config.iva_natura n
    ON n.codice = r.iva_natura
  WHERE r.fattura_id = p_fattura_id
  GROUP BY r.fattura_id, r.iva_id, n.id, r.esigibilita, r.split_payment;
  GET DIAGNOSTICS v_inserted_rows = ROW_COUNT;

  RETURN QUERY
  SELECT v_deleted_rows, v_inserted_rows;
END;
$function$
```

---
{% include-markdown "signature-core.md" %}
