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

    -- ⚠️ L'esistenza si misura con NOT FOUND, non con l'IS NULL di
    --    una colonna NULLABILE. `stato_doc_fiscale_id` puo' essere
    --    NULL su una fattura che esiste: il codice precedente la
    --    dichiarava «non trovata» e mandava a cercare un documento
    --    che invece era li'.
    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_ricalcola_riepilogo_iva_fattura', 'E_FATTURA_NON_TROVATA',
            jsonb_build_object('fattura_id', p_fattura_id), NULL::uuid, p_fattura_id::text);
    END IF;

    -- La fattura c'e' ma non ha stato: e' un'altra cosa, e va detta
    -- come tale. Senza stato non si puo' decidere se il ricalcolo
    -- sia ammesso, quindi non si procede.
    IF v_stato_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_ricalcola_riepilogo_iva_fattura', 'E_VALORE_MANCANTE',
            jsonb_build_object('fattura_id', p_fattura_id, 'campo', 'stato_doc_fiscale_id'),
            NULL::uuid, concat('stato_doc_fiscale_id della fattura ', p_fattura_id));
    END IF;

    SELECT s.codice_interno INTO v_codice_interno FROM config.stati_doc_fiscale s WHERE s.id = v_stato_id;

    -- ⚠️ `IS NULL OR`: senza, uno stato non risolvibile renderebbe
    --    l'espressione NULL — e `NULL NOT IN (...)` NON e' vero,
    --    quindi l'IF non scatterebbe e il ricalcolo procederebbe su
    --    un documento di stato ignoto. Oggi il ramo e' IRRAGGIUNGIBILE
    --    (la FK fk_fatture_stato_doc_fiscale ammette solo id validi, e
    --    il NULL e' respinto sopra): si tiene perche' costa zero e non
    --    fa dipendere questo guard da un vincolo di un'altra tabella.
    IF v_codice_interno IS NULL OR v_codice_interno NOT IN ('DRAFT', 'EMESSA') THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_ricalcola_riepilogo_iva_fattura', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'stato_doc_fiscale', 'valore', v_codice_interno,
                               'stato_doc_fiscale_id', v_stato_id, 'fattura_id', p_fattura_id),
            NULL::uuid, concat('ricalcolo IVA non ammesso per stato ', COALESCE(v_codice_interno, '(non risolvibile)')));
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
IS 'Ricalcola i riepiloghi IVA di una fattura (DELETE + INSERT per fattura_id), raggruppando le righe per aliquota/natura/esigibilita/split e applicando l''override di aliquota per stato dell''emittente. Ammesso SOLO in DRAFT o EMESSA: oltre quella soglia il documento e'' uno snapshot fiscale. rev 2026-08-02: due difetti chiusi sul controllo dello stato, opposti fra loro e con la stessa radice — usare un valore nullabile come prova di esistenza. (1) L''esistenza si misura con NOT FOUND: stato_doc_fiscale_id e'' NULLABLE, quindi l''IS NULL precedente dichiarava «fattura non trovata» anche per una fattura che esiste ma non ha stato, mandando a cercare un documento presente; ora i due casi hanno messaggi distinti (E_FATTURA_NON_TROVATA vs E_VALORE_MANCANTE). (2) Il guard di stato era fail-open nella FORMA: con codice_interno NULL l''espressione NOT IN vale NULL e l''IF non sarebbe scattato; il ramo e'' pero'' IRRAGGIUNGIBILE oggi (la FK fk_fatture_stato_doc_fiscale ammette solo id validi e il NULL e'' respinto dal punto 1), quindi l''IS NULL OR aggiunto e'' difesa in profondita'' e non la correzione di un bug vivo — si tiene perche'' costa zero e svincola il guard da un constraint di un''altra tabella. Trovati adeguando le fixture al guard D-K della Fase 4b.';
```

---
{% include-markdown "signature-core.md" %}
