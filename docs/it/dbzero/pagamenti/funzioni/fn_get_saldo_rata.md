{% include-markdown "it/dbzero/pagamenti/manual/fn_get_saldo_rata.md" %}
# ⚙️ Funzione `fn_get_saldo_rata`

```sql
CREATE FUNCTION fn_get_saldo_rata(p_scadenza_id bigint, p_escludi_contabile_riga_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION pagamenti.fn_get_saldo_rata(p_scadenza_id bigint, p_escludi_contabile_riga_id bigint DEFAULT NULL::bigint)
 RETURNS TABLE(saldo numeric, in_lavorazione numeric, incassato numeric, has_movimenti boolean)
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_importo        vendite.fatture_scadenze.importo%TYPE;
    v_movimenti      pagamenti.vendite_contabili_righe.importo%TYPE;
    v_incassato      pagamenti.vendite_contabili_righe.importo%TYPE;
    v_in_lavorazione pagamenti.vendite_contabili_righe.importo%TYPE;
    v_has_movimenti  boolean;
BEGIN
    -- =========================================================
    -- Guard di parametro: un id nullo o non positivo non esce da
    -- nessuna interfaccia — lo produce solo un chiamante rotto.
    -- =========================================================
    IF p_scadenza_id IS NULL OR p_scadenza_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'pagamenti.fn_get_saldo_rata',
            'E_PAGAMENTI_CHIAMATA_NON_VALIDA',
            jsonb_build_object('parametro', 'p_scadenza_id', 'valore', p_scadenza_id),
            NULL::uuid,
            'pagamenti.fn_get_saldo_rata',
            'p_scadenza_id obbligatorio e maggiore di zero');
    END IF;

    IF p_escludi_contabile_riga_id IS NOT NULL AND p_escludi_contabile_riga_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'pagamenti.fn_get_saldo_rata',
            'E_PAGAMENTI_CHIAMATA_NON_VALIDA',
            jsonb_build_object('parametro', 'p_escludi_contabile_riga_id',
                               'valore', p_escludi_contabile_riga_id),
            NULL::uuid,
            'pagamenti.fn_get_saldo_rata',
            'p_escludi_contabile_riga_id, se fornito, deve essere maggiore di zero');
    END IF;

    -- =========================================================
    -- L'importo della rata.
    -- ⚠️ La tabella ha la RLS: «non esiste» e «non la vedi»
    --    arrivano qui allo stesso modo, ed e' la stessa scelta
    --    gia' fatta da fn_get_saldo_fattura. Dove la differenza
    --    conta — il guard di coerenza — la domanda si fa fuori
    --    dalla row security con script.fn_check_scadenza_di_fattura.
    -- =========================================================
    SELECT s.importo
      INTO v_importo
      FROM vendite.fatture_scadenze s
     WHERE s.id = p_scadenza_id;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'pagamenti.fn_get_saldo_rata',
            'E_RATA_NON_TROVATA',
            jsonb_build_object('scadenza_id', p_scadenza_id),
            NULL::uuid,
            p_scadenza_id::text);
    END IF;

    -- =========================================================
    -- Cio' che e' REGISTRATO, e quanto di quello e' cassa vera.
    -- ⚠️ `incassato` pretende che il centro ci sia e che non sia
    --    ne' fondo fattura ne' compensazione: un movimento senza
    --    centro non e' «denaro arrivato», e' un canale non
    --    dichiarato. Su una misura di cassa si sta dalla parte
    --    prudente.
    -- =========================================================
    SELECT COALESCE(SUM(m.importo), 0),
           COALESCE(SUM(m.importo) FILTER (
               WHERE c.id IS NOT NULL
                 AND c.is_fondo_fattura IS FALSE
                 AND c.is_compensazione IS FALSE), 0),
           COUNT(*) > 0
      INTO v_movimenti, v_incassato, v_has_movimenti
      FROM pagamenti.vendite_movimenti m
      LEFT JOIN pagamenti.centri_riscossione c ON c.id = m.centro_riscossione_id
     WHERE m.scadenza_id = p_scadenza_id
       AND m.attivo IS TRUE
       AND (p_escludi_contabile_riga_id IS NULL
            OR m.contabile_riga_id IS DISTINCT FROM p_escludi_contabile_riga_id);

    -- =========================================================
    -- Cio' che e' DICHIARATO e non ancora registrato.
    -- ⚠️ Come la gemella di fattura: righe postabili sotto una
    --    testata NON finale. Una riga sotto una distinta chiusa
    --    non e' in lavorazione, e' ferma.
    -- =========================================================
    SELECT COALESCE(SUM(cr.importo), 0)
      INTO v_in_lavorazione
      FROM pagamenti.vendite_contabili_righe cr
      JOIN pagamenti.vendite_contabili_righe_stati st ON st.id = cr.stato_id
      JOIN pagamenti.vendite_contabili co ON co.id = cr.contabile_id
      JOIN pagamenti.vendite_contabili_stati cs ON cs.id = co.stato_id
     WHERE cr.scadenza_id = p_scadenza_id
       AND cr.attivo IS TRUE
       AND st.is_postabile IS TRUE
       AND cs.is_final IS NOT TRUE
       AND (p_escludi_contabile_riga_id IS NULL
            OR cr.id <> p_escludi_contabile_riga_id);

    RETURN QUERY SELECT
        COALESCE(v_importo, 0) - COALESCE(v_movimenti, 0),
        COALESCE(v_in_lavorazione, 0),
        COALESCE(v_incassato, 0),
        COALESCE(v_has_movimenti, false);
END;
$function$

COMMENT ON FUNCTION pagamenti.fn_get_saldo_rata(p_scadenza_id bigint, p_escludi_contabile_riga_id bigint)
IS 'Il saldo di una RATA, in tre numeri: `saldo` = importo della rata meno i movimenti registrati; `in_lavorazione` = quanto e'' gia'' dichiarato su righe contabili pronte ma non ancora registrato; `incassato` = quanto di cio'' che e'' registrato e'' DENARO DAVVERO ARRIVATO. ⭐ La terza colonna e'' §4 del brief madre e non e'' un lusso: i centri is_fondo_fattura e is_compensazione NON SONO CASSA — un movimento su quei centri salda il documento (il denaro si e'' mosso per trasferimento) ma in banca non e'' entrato niente, e chi misura gli incassi sommando tutti i movimenti misura un''altra cosa senza saperlo. ⚠️ Un movimento SENZA centro non entra in `incassato`: «canale non dichiarato» non e'' «denaro arrivato», e su una misura di cassa si sta dalla parte prudente. ⚠️ `saldo` e `in_lavorazione` restano DUE colonne, com''e'' due funzioni a livello di fattura (fn_get_saldo_fattura e fn_get_saldo_fattura_contabili): il registrato e il dichiarato non si sommano in un numero solo o non si capisce piu'' che cosa si guarda. Chi vuole sapere «quanto spazio c''e'' ancora» fa `saldo - in_lavorazione`, ed e'' cio'' che fa il guard di capienza. ⭐ p_escludi_contabile_riga_id ha lo stesso mestiere del p_source_id di vendite.fn_saldo_sorgente_fondo: chi sta scrivendo una riga chiede quanto spazio c''era PRIMA di se'', o si troverebbe a confrontarsi con se'' stesso. ⚠️ Le righe in lavorazione escludono le distinte finali, come la gemella di fattura: una riga sotto una distinta chiusa non e'' in lavorazione, e'' ferma. ⚠️ La tabella delle rate ha la RLS: «non esiste» e «non la vedi» danno lo stesso E_RATA_NON_TROVATA, stessa scelta di E_FATTURA_NON_TROVATA — dove la differenza conta si usa script.fn_check_scadenza_di_fattura, che gira fuori dalla row security. ⚠️ NON e'' dichiarata STABLE: il ramo d''errore scrive nel registro, e promettere stabilita'' su una funzione che in un ramo scrive autorizza il planner a scelte che quel ramo non regge. S2-6 del cantiere incassi.';
```

---
{% include-markdown "signature-core.md" %}
