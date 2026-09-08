{% include-markdown "it/dbzero/vendite/manual/fn_get_lotto_segnalazioni_summary.md" %}
# ⚙️ Funzione `fn_get_lotto_segnalazioni_summary`

```sql
CREATE FUNCTION fn_get_lotto_segnalazioni_summary(p_lotto_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_get_lotto_segnalazioni_summary(p_lotto_id bigint)
 RETURNS TABLE(fatture_critical_count bigint, fatture_warning_count bigint, lotto_critical_count bigint, lotto_warning_count bigint, lotto_info_count bigint, fatture_stato_esecuzione_errore_count bigint, documenti_bloccanti_count bigint, documenti_presi_in_carico_count bigint, critiche_giro_count bigint)
 LANGUAGE plpgsql
AS $function$

BEGIN
    -- Guard: parametro obbligatorio
    IF p_lotto_id IS NULL OR p_lotto_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_get_lotto_segnalazioni_summary', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_lotto_id', 'valore', p_lotto_id),
            NULL::uuid, 'p_lotto_id obbligatorio e > 0'
        );
    END IF;

    RETURN QUERY
    WITH fatture_agg AS (
        -- ⭐ Non si tocca: la bozza cancellata porta via la riga di
        --    ponte, e questo conteggio scende da se'.
        SELECT COUNT(*) FILTER (WHERE fl.status = 'C') AS fc,
               COUNT(*) FILTER (WHERE fl.status = 'W') AS fw
          FROM vendite.fatturazione_lotti_fatture lf
          JOIN vendite.fatture_log fl ON fl.fattura_id = lf.fattura_id
         WHERE lf.lotto_id = p_lotto_id AND fl.disabilitato IS FALSE
    ),
    lotto_agg AS (
        SELECT COUNT(*) FILTER (WHERE ll.status = 'C') AS lc,
               COUNT(*) FILTER (WHERE ll.status = 'W') AS lw,
               COUNT(*) FILTER (WHERE ll.status = 'I') AS li,
               -- ⭐ QUANTI DOCUMENTI, non quante segnalazioni. Un documento con
               --   tre critiche e' UN documento fermo: il banner dice all'operatore
               --   quanti gesti gli restano, e i gesti sono uno per documento.
               --   ⚠️ DISTINCT sulla chiave, e solo dove la chiave c'e'.
               COUNT(DISTINCT ll.gruppo_key)
                   FILTER (WHERE ll.status = 'C'
                             AND ll.gruppo_key IS NOT NULL)      AS docs_bloccanti,
               -- ⭐ E LE CRITICHE DEL GIRO, che sono l'altra meta' del vocabolario
               --   (§4.1) e NON sono documenti: emittente non risolto,
               --   configurazione mancante. Bloccano e non hanno niente da togliere.
               -- ⛔ Senza questo numero il banner direbbe «0 documenti su 4» su un
               --   lotto fermo — cioe' che non c'e' niente da fare mentre il giro
               --   e' bloccato. Il terzo numero non e' un di piu': e' cio' che
               --   rende la frase vera.
               COUNT(*) FILTER (WHERE ll.status = 'C'
                             AND ll.gruppo_key IS NULL)          AS critiche_giro
          FROM vendite.fatturazione_lotti_log ll
         WHERE ll.lotto_id = p_lotto_id AND ll.disabilitato IS FALSE
           -- ⭐ La segnalazione di un documento USCITO non conta piu':
           --   non e' stata ritirata, e' che il suo documento non e'
           --   piu' in gioco. Resta leggibile nella storia del lotto.
           -- ⚠️ Con `gruppo_key` NULL il NOT EXISTS e' vero e la riga
           --   CONTA: «segnalazione del giro» ferma il giro. La regola
           --   viene gratis dal confronto, non e' un ramo a parte.
           AND NOT EXISTS (
               SELECT 1
                 FROM vendite.fatturazione_lotti_esiti e
                WHERE e.lotto_id         = ll.lotto_id
                  AND e.gruppo_key       = ll.gruppo_key
                  AND e.stato_esecuzione = 'ESCLUSO')
    ),
    esiti_agg AS (
        -- ⭐ IL DENOMINATORE, e la sorgente non e' scontata: si contano gli
        --   ESITI, cioe' i documenti che il lotto ha PRESO IN CARICO.
        -- ⛔ NON `fatturazione_lotti_gruppi`: il perimetro e' VUOTO sui giri di
        --   massa — e' esattamente la ragione per cui fatturazione_lotti_esiti
        --   e' nata il 2026-09-07. Col perimetro il banner direbbe «su 0» su
        --   meta' dei giri, e nessuno collegherebbe il difetto a questa riga.
        SELECT COUNT(*) AS dt
          FROM vendite.fatturazione_lotti_esiti e
         WHERE e.lotto_id = p_lotto_id
    ),
    ponte_agg AS (
        -- ⭐ Nemmeno questo: stessa ragione di fatture_agg.
        SELECT COUNT(*) FILTER (WHERE lf.stato_esecuzione = 'ERRORE') AS pe
          FROM vendite.fatturazione_lotti_fatture lf
         WHERE lf.lotto_id = p_lotto_id
    )
    -- ⚠️ I TRE NUMERI NUOVI VANNO IN CODA, e non e' estetica: il backend
    --   legge questa riga per POSIZIONE (row[0]..row[5]). Infilarli in mezzo
    --   farebbe scivolare i sei esistenti, e una lettura posizionale sbagliata
    --   non protesta: mostrerebbe numeri plausibili e falsi.
    SELECT COALESCE(fa.fc, 0), COALESCE(fa.fw, 0),
           COALESCE(la.lc, 0), COALESCE(la.lw, 0), COALESCE(la.li, 0),
           COALESCE(pa.pe, 0),
           COALESCE(la.docs_bloccanti, 0),
           COALESCE(ea.dt, 0),
           COALESCE(la.critiche_giro, 0)
      FROM fatture_agg fa CROSS JOIN lotto_agg la CROSS JOIN ponte_agg pa
                          CROSS JOIN esiti_agg ea;
END;
$function$

COMMENT ON FUNCTION vendite.fn_get_lotto_segnalazioni_summary(p_lotto_id bigint)
IS 'Il riepilogo delle segnalazioni di un lotto: sei conteggi storici piu'' tre per il BANNER, aggiunti il 2026-09-08. ⭐ I sei contano SEGNALAZIONI; i tre nuovi contano GESTI, perche'' l''operatore ne ha uno per DOCUMENTO (togli questo dal giro) e un documento con tre critiche resta un documento solo. documenti_bloccanti_count = quanti documenti hanno almeno una critica viva (DISTINCT sulla chiave); documenti_presi_in_carico_count = il denominatore; critiche_giro_count = le critiche che un documento NON ce l''hanno. ⛔ Il terzo numero non e'' un di piu'': senza, N documenti su M direbbe 0 documenti su 4 su un lotto fermo per un emittente non risolto, cioe'' che non c''e'' niente da fare mentre il giro e'' bloccato. Le critiche sono di DUE specie (brief §4.1) e una non e'' un documento. ⛔ Il denominatore si conta sugli ESITI e non sul perimetro: fatturazione_lotti_gruppi e'' vuota sui giri di massa, ed e'' la ragione per cui la tabella degli esiti e'' nata. ⚠️ I tre descrivono il canale LOTTO, dove la gruppo_key vive: gli altri due canali parlano per FATTURA, e una bozza puo'' coprire piu'' documenti, quindi non sono sommabili senza scommettere. ⭐ Il filtro sui documenti USCITI dal giro non si ripete: i due conteggi nascono dentro lotto_agg, che ce l''ha gia''. ⚠️ Le colonne nuove sono IN CODA perche'' il backend legge questa riga per POSIZIONE: infilarle in mezzo mostrerebbe numeri plausibili e falsi, senza fallire. ⛔ blocks_next_step resta in Python e non deve sapere niente di questi tre: sono per la FRASE, non per la decisione. Brief: brief-db-uscita-documento-dal-giro §7.';
```

---
{% include-markdown "signature-core.md" %}
