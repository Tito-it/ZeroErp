{% include-markdown "it/dbzero/pagamenti/manual/fn_get_saldo_rata.md" %}
# ⚙️ Funzione `fn_get_saldo_rata`

```sql
CREATE FUNCTION fn_get_saldo_rata(p_scadenza_id bigint, p_escludi_contabile_riga_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pagamenti.fn_get_saldo_rata(p_scadenza_id bigint, p_escludi_contabile_riga_id bigint DEFAULT NULL::bigint)
 RETURNS TABLE(saldo numeric, in_lavorazione numeric, incassato numeric, has_movimenti boolean)
 LANGUAGE plpgsql
AS $function$
-- Scopo: il saldo di UNA rata — la porta a un elemento del nucleo
--        pagamenti.fn_get_saldi_rate. Qui stanno il guard di
--        parametro e l'errore; la formula sta nel nucleo.
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
    -- La formula sta nel NUCLEO: qui si chiede per un elemento.
    -- ⚠️ La tabella ha la RLS: «non esiste» e «non la vedi»
    --    arrivano qui allo stesso modo (zero righe), ed e' la
    --    stessa scelta gia' fatta da fn_get_saldo_fattura. Dove
    --    la differenza conta — il guard di coerenza — la domanda
    --    si fa fuori dalla row security con
    --    script.fn_check_scadenza_di_fattura.
    -- =========================================================
    RETURN QUERY
        SELECT r.saldo, r.in_lavorazione, r.incassato, r.has_movimenti
          FROM pagamenti.fn_get_saldi_rate(ARRAY[p_scadenza_id], p_escludi_contabile_riga_id) r;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'pagamenti.fn_get_saldo_rata',
            'E_RATA_NON_TROVATA',
            jsonb_build_object('scadenza_id', p_scadenza_id),
            NULL::uuid,
            p_scadenza_id::text);
    END IF;
END;
$function$

COMMENT ON FUNCTION pagamenti.fn_get_saldo_rata(p_scadenza_id bigint, p_escludi_contabile_riga_id bigint)
IS 'Il saldo di una RATA, in tre numeri: `saldo` = importo della rata meno i movimenti registrati; `in_lavorazione` = quanto e'' gia'' dichiarato su righe contabili pronte ma non ancora registrato; `incassato` = quanto di cio'' che e'' registrato e'' DENARO DAVVERO ARRIVATO. ⭐ rev 2026-09-17 (brief-db-distinta-ricerca-rate §4-bis.4, P-3): e'' la PORTA A UN ELEMENTO del nucleo set-based pagamenti.fn_get_saldi_rate — la formula sta la'', scritta una volta per tutte le porte (questa, vw_saldi_rate, la JOIN LATERAL sulla pagina); qui restano il guard di parametro e l''errore. Firma, RETURNS e comportamento invariati. ⭐ La terza colonna e'' §4 del brief madre e non e'' un lusso: i centri is_fondo_fattura e is_compensazione NON SONO CASSA — un movimento su quei centri salda il documento (il denaro si e'' mosso per trasferimento) ma in banca non e'' entrato niente, e chi misura gli incassi sommando tutti i movimenti misura un''altra cosa senza saperlo. ⚠️ Un movimento SENZA centro non entra in `incassato`: «canale non dichiarato» non e'' «denaro arrivato», e su una misura di cassa si sta dalla parte prudente. ⚠️ `saldo` e `in_lavorazione` restano DUE colonne, com''e'' due funzioni a livello di fattura (fn_get_saldo_fattura e fn_get_saldo_fattura_contabili): il registrato e il dichiarato non si sommano in un numero solo o non si capisce piu'' che cosa si guarda. Chi vuole sapere «quanto spazio c''e'' ancora» fa `saldo - in_lavorazione`, ed e'' cio'' che fa il guard di capienza. ⭐ p_escludi_contabile_riga_id ha lo stesso mestiere del p_source_id di vendite.fn_saldo_sorgente_fondo: chi sta scrivendo una riga chiede quanto spazio c''era PRIMA di se'', o si troverebbe a confrontarsi con se'' stesso. ⚠️ Le righe in lavorazione escludono le distinte finali, come la gemella di fattura: una riga sotto una distinta chiusa non e'' in lavorazione, e'' ferma. ⚠️ La tabella delle rate ha la RLS: «non esiste» e «non la vedi» danno lo stesso E_RATA_NON_TROVATA, stessa scelta di E_FATTURA_NON_TROVATA — dove la differenza conta si usa script.fn_check_scadenza_di_fattura, che gira fuori dalla row security. ⚠️ NON e'' dichiarata STABLE: il ramo d''errore scrive nel registro, e promettere stabilita'' su una funzione che in un ramo scrive autorizza il planner a scelte che quel ramo non regge (il nucleo, che non solleva mai, lo e''). S2-6 del cantiere incassi.';
```

</div>

---
{% include-markdown "signature-core.md" %}
