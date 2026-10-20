{% include-markdown "it/dbzero/vendite/manual/fn_ricalcola_totali_ordine.md" %}
# ⚙️ Funzione `fn_ricalcola_totali_ordine`

```sql
CREATE FUNCTION fn_ricalcola_totali_ordine(p_ordine_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_ricalcola_totali_ordine(p_ordine_id bigint)
 RETURNS TABLE(ordine_id bigint, imponibile_tot numeric, sconto_tot numeric, iva_tot numeric, totale_doc numeric)
 LANGUAGE plpgsql
AS $function$
-- Scopo: ricalcolare i totali di testata ordine partendo dal
-- riepilogo IVA derivato. La view riepilogo e' la sorgente del
-- calcolo fiscale: somma imponibili per aliquota, arrotonda
-- l'imponibile aggregato e calcola l'imposta su quel valore.
--
-- La funzione aggiorna solo vendite.ordini; non crea righe
-- riepilogo persistenti e non somma direttamente i componenti
-- BoM, gia' confluiti nel prezzo della riga padre.
DECLARE
    v_imponibile vendite.ordini.imponibile_tot%TYPE := 0;
    v_sconto     vendite.ordini.sconto_tot%TYPE := 0;
    v_iva        vendite.ordini.iva_tot%TYPE := 0;
    v_totale     vendite.ordini.totale_doc%TYPE := 0;
    v_lordo      vendite.ordini.imponibile_tot%TYPE := 0;
BEGIN
    IF p_ordine_id IS NULL OR p_ordine_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite',
            'fn_ricalcola_totali_ordine',
            'E_PARAMETRO_INVALIDO',
            jsonb_build_object('param', 'p_ordine_id', 'value', p_ordine_id),
            NULL::uuid,
            'p_ordine_id = ' || COALESCE(p_ordine_id::text, 'NULL')
        );
    END IF;

    -- Step 1: totali fiscalmente corretti da riepilogo IVA.
    SELECT
        COALESCE(SUM(r.imponibile), 0),
        COALESCE(SUM(r.imposta),    0),
        COALESCE(SUM(r.totale_riga), 0)
      INTO v_imponibile, v_iva, v_totale
      FROM vendite.vw_ordini_riepilogo_iva_dettaglio r
     WHERE r.ordine_id = p_ordine_id;

    -- Step 2: sconto testata = lordo righe - imponibile aggregato.
    SELECT ROUND(COALESCE(SUM(b.imponibile_lordo_full), 0), 2)
      INTO v_lordo
      FROM vendite.vw_ordini_righe_iva_base b
     WHERE b.ordine_id = p_ordine_id;

    v_sconto := v_lordo - v_imponibile;

    -- Step 3: aggiorna testata ordine.
    UPDATE vendite.ordini o
       SET imponibile_tot = v_imponibile,
           sconto_tot     = v_sconto,
           iva_tot        = v_iva,
           totale_doc     = v_totale
     WHERE o.id = p_ordine_id;

    RETURN QUERY
    SELECT p_ordine_id, v_imponibile, v_sconto, v_iva, v_totale;
END
$function$

COMMENT ON FUNCTION vendite.fn_ricalcola_totali_ordine(p_ordine_id bigint)
IS 'Ricalcola i totali di testata ordine sommando vendite.vw_ordini_riepilogo_iva_dettaglio. IVA calcolata su imponibile aggregato per aliquota, come nei preventivi. sconto_tot = lordo righe arrotondato meno imponibile aggregato. Firma e RETURNS TABLE usano %TYPE su vendite.ordini.*.';
```

</div>

---
{% include-markdown "signature-core.md" %}
