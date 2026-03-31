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
    v_deleted_rows  INTEGER := 0;
    v_inserted_rows INTEGER := 0;
    v_stato_id      vendite.fatture.stato_doc_fiscale_id%TYPE;
    v_codice_interno config.stati_doc_fiscale.codice_interno%TYPE;
    v_stato_emittente_id anagrafiche.soggetti.stato_id%TYPE;
BEGIN
    IF p_fattura_id IS NULL OR p_fattura_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_ricalcola_riepilogo_iva_fattura', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_fattura_id', 'valore', p_fattura_id), NULL::uuid, 'p_fattura_id obbligatorio e > 0');
    END IF;

    SELECT f.stato_doc_fiscale_id INTO v_stato_id FROM vendite.fatture f WHERE f.id = p_fattura_id;

    IF v_stato_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_ricalcola_riepilogo_iva_fattura', 'E_FATTURA_NON_TROVATA',
            jsonb_build_object('fattura_id', p_fattura_id), NULL::uuid, p_fattura_id::text);
    END IF;

    SELECT s.codice_interno INTO v_codice_interno FROM config.stati_doc_fiscale s WHERE s.id = v_stato_id;

    IF v_codice_interno NOT IN ('DRAFT', 'EMESSA') THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_ricalcola_riepilogo_iva_fattura', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'stato_doc_fiscale', 'valore', v_codice_interno, 'fattura_id', p_fattura_id),
            NULL::uuid, concat('ricalcolo IVA non ammesso per stato ', v_codice_interno));
    END IF;

    -- Recupero stato emittente per override aliquota IVA
    SELECT s.stato_id INTO v_stato_emittente_id
      FROM vendite.fatture f
      JOIN anagrafiche.soggetti_ruoli sr ON sr.id = f.emittente_soggetto_ruolo_id
      JOIN anagrafiche.soggetti s ON s.id = sr.soggetto_id
     WHERE f.id = p_fattura_id;

    DELETE FROM vendite.fatture_riepiloghi_iva WHERE fattura_id = p_fattura_id;
    GET DIAGNOSTICS v_deleted_rows = ROW_COUNT;

    INSERT INTO vendite.fatture_riepiloghi_iva (fattura_id, iva_id, natura_id, esigibilita, split_payment, imponibile, imposta, arrotondamento)
    SELECT r.fattura_id, r.iva_id, n.id, r.esigibilita, r.split_payment,
           ROUND(SUM(COALESCE(r.imponibile_riga, 0)), 2),
           ROUND(ROUND(SUM(COALESCE(r.imponibile_riga, 0)), 2) * (COALESCE(config.fn_get_aliquota_iva(r.iva_id, v_stato_emittente_id), 0)::NUMERIC / 100::NUMERIC), 2),
           SUM(COALESCE(r.imponibile_riga, 0)) - ROUND(SUM(COALESCE(r.imponibile_riga, 0)), 2)
      FROM vendite.fatture_righe r
      LEFT JOIN config.iva i ON i.id = r.iva_id
      LEFT JOIN config.iva_natura n ON n.codice = r.iva_natura
     WHERE r.fattura_id = p_fattura_id
     GROUP BY r.fattura_id, r.iva_id, n.id, r.esigibilita, r.split_payment;
    GET DIAGNOSTICS v_inserted_rows = ROW_COUNT;

    RETURN QUERY SELECT v_deleted_rows, v_inserted_rows;
END;
$function$

COMMENT ON FUNCTION vendite.fn_ricalcola_riepilogo_iva_fattura(p_fattura_id bigint)
IS 'Ricalcola riepiloghi IVA fattura. Ammesso solo per DRAFT/EMESSA.';
```

---
{% include-markdown "signature-core.md" %}
