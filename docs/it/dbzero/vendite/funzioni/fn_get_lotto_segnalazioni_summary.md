{% include-markdown "it/dbzero/vendite/manual/fn_get_lotto_segnalazioni_summary.md" %}
# ⚙️ Funzione `fn_get_lotto_segnalazioni_summary`

```sql
CREATE FUNCTION fn_get_lotto_segnalazioni_summary(p_lotto_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_get_lotto_segnalazioni_summary(p_lotto_id bigint)
 RETURNS TABLE(fatture_critical_count bigint, fatture_warning_count bigint, lotto_critical_count bigint, lotto_warning_count bigint, lotto_info_count bigint, fatture_stato_esecuzione_errore_count bigint)
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
               COUNT(*) FILTER (WHERE ll.status = 'I') AS li
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
    ponte_agg AS (
        -- ⭐ Nemmeno questo: stessa ragione di fatture_agg.
        SELECT COUNT(*) FILTER (WHERE lf.stato_esecuzione = 'ERRORE') AS pe
          FROM vendite.fatturazione_lotti_fatture lf
         WHERE lf.lotto_id = p_lotto_id
    )
    SELECT COALESCE(fa.fc, 0), COALESCE(fa.fw, 0),
           COALESCE(la.lc, 0), COALESCE(la.lw, 0), COALESCE(la.li, 0),
           COALESCE(pa.pe, 0)
      FROM fatture_agg fa CROSS JOIN lotto_agg la CROSS JOIN ponte_agg pa;
END;
$function$

COMMENT ON FUNCTION vendite.fn_get_lotto_segnalazioni_summary(p_lotto_id bigint)
IS 'Riepilogo segnalazioni lotto attive (log fatture/lotto) + conteggio ponte errore. ⭐ Rev 2026-09-08: il ramo del LOG DI LOTTO non conta piu'' le critiche dei documenti USCITI dal giro (esito ESCLUSO) — cosi'' il lotto riparte quando esce l''ultimo documento che lo teneva fermo, senza che nessuno ritiri una segnalazione e senza toccare blocks_next_step, che continua a chiedere «zero critiche vive». ⚠️ Una segnalazione con gruppo_key NULL CONTA: vuol dire «e'' del giro» — un emittente non risolto, una configurazione mancante — e non ha nessun documento da togliere. ⭐ Gli altri due aggregati non sono stati toccati e non e'' una dimenticanza: leggono entrambi attraverso fatturazione_lotti_fatture, e l''uscita cancella la bozza, quindi la riga di ponte sparisce e i loro conteggi scendono da soli. 🔴 Finche'' chi scrive le segnalazioni non ne dichiara la gruppo_key, questa modifica non sblocca niente: le critiche del pull nascono a NULL e contano tutte (contratto §6 del brief). Brief: brief-db-uscita-documento-dal-giro §5.3.';
```

---
{% include-markdown "signature-core.md" %}
