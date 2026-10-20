{% include-markdown "it/dbzero/vendite/manual/fn_get_lotto_segnalazioni_summary.md" %}
# ⚙️ Funzione `fn_get_lotto_segnalazioni_summary`

```sql
CREATE FUNCTION fn_get_lotto_segnalazioni_summary(p_lotto_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_get_lotto_segnalazioni_summary(p_lotto_id bigint)
 RETURNS TABLE(fatture_critical_count bigint, fatture_warning_count bigint, lotto_critical_count bigint, lotto_warning_count bigint, lotto_info_count bigint, fatture_stato_esecuzione_errore_count bigint, documenti_bloccanti_count bigint, documenti_presi_in_carico_count bigint, critiche_giro_count bigint, esiti_stato_esecuzione_errore_count bigint, fermo boolean)
 LANGUAGE plpgsql
AS $function$
-- Scopo: il riepilogo delle segnalazioni di UN lotto per il backend
--        (banner, runner): i dieci conteggi piu' il verdetto `fermo`.
--        ⭐ Dal 2026-09-19 e' un LETTORE: gli aggregati vivono in
--        vendite.vw_lotti_segnalazioni_summary, la sede unica che
--        legge anche il presidio dbops.vw_lotti_fermi_da_guardare.
--        Un addendo nuovo si aggiunge LI', non qui.
BEGIN
    -- Guard: parametro obbligatorio
    IF p_lotto_id IS NULL OR p_lotto_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_get_lotto_segnalazioni_summary', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_lotto_id', 'valore', p_lotto_id),
            NULL::uuid, 'p_lotto_id obbligatorio e > 0'
        );
    END IF;

    -- ⚠️ I NUMERI RESTANO NELLO STESSO ORDINE e `fermo` VA IN CODA:
    --   il backend mappa la riga per posizione, e una colonna in
    --   mezzo farebbe scivolare le altre senza che niente protesti.
    -- ⭐ Il predicato `s.lotto_id = p_lotto_id` viene spinto dentro
    --   le quattro GROUP BY della vista (verificato con EXPLAIN):
    --   e' la stessa lettura per lotto delle vecchie CTE.
    RETURN QUERY
    SELECT s.fatture_critical_count,
           s.fatture_warning_count,
           s.lotto_critical_count,
           s.lotto_warning_count,
           s.lotto_info_count,
           s.fatture_stato_esecuzione_errore_count,
           s.documenti_bloccanti_count,
           s.documenti_presi_in_carico_count,
           s.critiche_giro_count,
           s.esiti_stato_esecuzione_errore_count,
           s.fermo
      FROM vendite.vw_lotti_segnalazioni_summary s
     WHERE s.lotto_id = p_lotto_id;

    -- ⭐ UNA RIGA SEMPRE. Lotto inesistente — o fuori dal perimetro
    --   di chi legge: la vista e' security_invoker — risponde zeri
    --   e `fermo = false`, com'era prima (le CTE su zero righe
    --   davano COALESCE a zero). Il backend legge la testata PRIMA
    --   e risponde 404: questi zeri non arrivano a una persona
    --   come «tutto a posto».
    IF NOT FOUND THEN
        RETURN QUERY
        SELECT 0::bigint, 0::bigint, 0::bigint, 0::bigint, 0::bigint,
               0::bigint, 0::bigint, 0::bigint, 0::bigint, 0::bigint,
               false;
    END IF;
END;
$function$

COMMENT ON FUNCTION vendite.fn_get_lotto_segnalazioni_summary(p_lotto_id bigint)
IS 'Il riepilogo delle segnalazioni di un lotto per il backend: dieci conteggi piu'' il verdetto. ⭐⭐ rev 2026-09-19 (brief-db-osservabilita-lotto-fermo-r6-indici, D-1 di Tid: «la regola va a DB»): la funzione e'' un LETTORE di vendite.vw_lotti_segnalazioni_summary — gli aggregati vivono nella vista, una riga per lotto, e la legge anche il presidio dbops.vw_lotti_fermi_da_guardare; un addendo nuovo si aggiunge nella vista, non qui. UNDICESIMA colonna in coda, `fermo` = (fatture_critical + lotto_critical) > 0 OR fatture_stato_esecuzione_errore > 0 OR esiti_stato_esecuzione_errore > 0: e'' il verdetto che LottoSegnalazioniService.evaluate_lotto_status calcolava come is_error/blocks_next_step, e da oggi il backend lo LEGGE e non lo ricalcola. ⛔ Fino al 2026-09-19 questa COMMENT diceva «blocks_next_step resta in Python»: non piu''. I DIECI conteggi restano, nello stesso ordine, per la FRASE del banner: i sei storici contano SEGNALAZIONI (C/W/I per canale fattura e lotto, righe di ponte in ERRORE); i tre del 2026-09-08 contano GESTI (documenti_bloccanti_count = documenti con almeno una critica viva, DISTINCT sulla chiave; documenti_presi_in_carico_count = il denominatore, contato sugli ESITI e non sul perimetro, vuoto sui giri di massa; critiche_giro_count = le critiche senza documento, che bloccano e non hanno niente da togliere); il decimo (2026-09-12, D2) conta i documenti presi in carico il cui ultimo esito e'' ERRORE — ESCLUSO non conta, e'' la via d''uscita dichiarata. ⚠️ Le colonne sono IN CODA e nell''ordine storico perche'' il backend legge questa riga per POSIZIONE: infilarne una in mezzo mostrerebbe numeri plausibili e falsi, senza fallire. ⚠️ UNA riga sempre: su un lotto inesistente o fuori perimetro (la vista e'' security_invoker) risponde zeri e fermo=false, come prima — il backend legge la testata prima e risponde 404. Brief precedenti: brief-db-uscita-documento-dal-giro §7, brief-db-rilancio-step-non-rivede-le-proprie-commesse D2.';
```

</div>

---
{% include-markdown "signature-core.md" %}
