{% include-markdown "it/dbzero/vendite/manual/fn_genera_scadenze_lotto.md" %}
# ⚙️ Funzione `fn_genera_scadenze_lotto`

```sql
CREATE FUNCTION fn_genera_scadenze_lotto(p_lotto_id bigint, p_batch_size integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_genera_scadenze_lotto(p_lotto_id bigint, p_batch_size integer DEFAULT 1000)
 RETURNS TABLE(fatture_count integer, deleted_rows integer, inserted_rows integer, skipped_rows integer, skipped_errore_rows integer, failed_rows integer)
 LANGUAGE plpgsql
AS $function$
-- Scopo: generare il piano rate su tutte le fatture LAVORABILI di
--        un lotto, senza che una fattura chiusa o una fattura
--        difettosa fermino le altre.
-- Uso:   task genera_scadenze_lotto dello step EMESSA.
-- Regole: due filtri DIVERSI e contati a parte — oltre soglia
--         (D-F) e in ERRORE (D-Q): il primo non ha lavoro da
--         fare, il secondo e' un rifiuto che tocca allo step a
--         monte riprovare.
DECLARE
    v_ids         BIGINT[];
    v_slice       BIGINT[];
    v_fattura_id  vendite.fatture.id%TYPE;
    v_start       INTEGER := 1;
    v_end         INTEGER := 0;
    v_max         INTEGER := 0;
    v_batch_size  INTEGER := 1000;
    v_count       INTEGER := 0;
    v_deleted     INTEGER := 0;
    v_inserted    INTEGER := 0;
    v_skipped     INTEGER := 0;
    v_skip_err    INTEGER := 0;
    v_failed      INTEGER := 0;
    v_tmp_del     INTEGER;
    v_tmp_ins     INTEGER;
    v_err_msg     TEXT;
    v_err_state   TEXT;
BEGIN
    -- ===== Guard parametri =====
    IF p_lotto_id IS NULL OR p_lotto_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_genera_scadenze_lotto', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_lotto_id', 'valore', p_lotto_id),
            NULL::uuid, 'p_lotto_id obbligatorio e > 0');
    END IF;

    IF p_batch_size IS NULL OR p_batch_size <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_genera_scadenze_lotto', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_batch_size', 'valore', p_batch_size),
            NULL::uuid, 'p_batch_size obbligatorio e > 0');
    END IF;

    v_batch_size := p_batch_size;

    -- ===== Chi si lavora e chi no, in una sola lettura =====
    -- I due motivi di salto restano distinti fino in fondo: per
    -- chi legge il cockpit, «chiusa» e «rotta» sono l'opposto.
    -- `critico_altrui`: esiste un log critico ATTIVO alzato da un
    -- task diverso da questo. Non si guarda `stato_esecuzione`,
    -- che dice solo «c'e' un critico» senza dire di chi: filtrare
    -- su quella colonna chiuderebbe fuori anche le fatture marcate
    -- da NOI, e il ritiro di D-Q non sarebbe piu' raggiungibile.
    WITH lavorabili AS (
        SELECT lf.fattura_id,
               s.codice_interno AS stato,
               EXISTS (
                   SELECT 1
                     FROM vendite.fatture_log fl
                    WHERE fl.fattura_id = lf.fattura_id
                      AND fl.status = 'C'
                      AND fl.disabilitato IS FALSE
                      AND fl.meta->>'task' IS DISTINCT FROM 'genera_scadenze_lotto'
               ) AS critico_altrui
          FROM vendite.fatturazione_lotti_fatture lf
          JOIN vendite.fatture f ON f.id = lf.fattura_id
          LEFT JOIN config.stati_doc_fiscale s ON s.id = f.stato_doc_fiscale_id
         WHERE lf.lotto_id = p_lotto_id
    )
    SELECT array_agg(l.fattura_id ORDER BY l.fattura_id)
               FILTER (WHERE l.stato IN ('DRAFT', 'EMESSA')
                         AND NOT l.critico_altrui),
           count(*)
               FILTER (WHERE l.stato IS NULL
                          OR l.stato NOT IN ('DRAFT', 'EMESSA')),
           count(*)
               FILTER (WHERE l.stato IN ('DRAFT', 'EMESSA')
                         AND l.critico_altrui)
      INTO v_ids, v_skipped, v_skip_err
      FROM lavorabili l;

    v_skipped  := COALESCE(v_skipped, 0);
    v_skip_err := COALESCE(v_skip_err, 0);

    IF v_ids IS NULL THEN
        IF v_skipped > 0 OR v_skip_err > 0 THEN
            PERFORM vendite.fn_log_pipeline_fase(
                p_lotto_id, NULL, 'Generazione scadenze', 'I',
                format('Nessuna fattura lavorabile: %s oltre EMESSA, %s in errore.',
                       v_skipped, v_skip_err),
                jsonb_build_object('task', 'genera_scadenze_lotto',
                                   'skipped', v_skipped,
                                   'skipped_errore', v_skip_err));
        END IF;

        RETURN QUERY SELECT 0, 0, 0, v_skipped, v_skip_err, 0;
        RETURN;
    END IF;

    v_max := array_length(v_ids, 1);

    WHILE v_start <= v_max LOOP
        v_end   := LEAST(v_start + v_batch_size - 1, v_max);
        v_slice := v_ids[v_start:v_end];

        FOR i IN 1..array_length(v_slice, 1) LOOP
            v_fattura_id := v_slice[i];
            v_count      := v_count + 1;

            BEGIN
                SELECT r.deleted_rows, r.inserted_rows
                  INTO v_tmp_del, v_tmp_ins
                  FROM vendite.fn_genera_scadenze_fattura(v_fattura_id) r;

                v_deleted  := v_deleted  + COALESCE(v_tmp_del, 0);
                v_inserted := v_inserted + COALESCE(v_tmp_ins, 0);

                -- Ritiro della PROPRIA segnalazione precedente: il
                -- problema e' risolto, la bandiera si abbassa.
                -- ⚠️ Filtro sul TASK, non sul nome della funzione:
                -- le funzioni si rinominano, il task_code no. Mai
                -- le righe di un altro task.
                UPDATE vendite.fatture_log fl
                   SET disabilitato = TRUE
                 WHERE fl.fattura_id = v_fattura_id
                   AND fl.disabilitato IS FALSE
                   AND fl.status = 'C'
                   AND fl.meta->>'task' = 'genera_scadenze_lotto';

            EXCEPTION WHEN raise_exception THEN
                -- Solo gli errori di dominio (P0001) finiscono qui:
                -- un guasto di sistema ha altro SQLSTATE e deve
                -- continuare a salire.
                GET STACKED DIAGNOSTICS
                    v_err_msg   = MESSAGE_TEXT,
                    v_err_state = RETURNED_SQLSTATE;

                v_failed := v_failed + 1;

                INSERT INTO vendite.fatture_log (
                            fattura_id, data_ora, messaggio,
                            status, disabilitato, meta)
                VALUES (v_fattura_id, now(),
                        format('Generazione scadenze non riuscita: %s', v_err_msg),
                        'C', FALSE,
                        jsonb_build_object(
                            'task',     'genera_scadenze_lotto',
                            'lotto_id', p_lotto_id,
                            'sqlstate', v_err_state,
                            'source',   'fn_genera_scadenze_lotto'));
            END;
        END LOOP;

        v_start := v_end + 1;
    END LOOP;

    -- ===== Una nota sola, a fine giro, per chi e' stato saltato =====
    IF v_skipped > 0 OR v_skip_err > 0 THEN
        PERFORM vendite.fn_log_pipeline_fase(
            p_lotto_id, NULL, 'Generazione scadenze', 'I',
            format('%s fatture non toccate perche'' oltre EMESSA, %s perche'' in errore; %s lavorate.',
                   v_skipped, v_skip_err, v_count),
            jsonb_build_object('task', 'genera_scadenze_lotto',
                               'skipped', v_skipped,
                               'skipped_errore', v_skip_err,
                               'lavorate', v_count));
    END IF;

    RETURN QUERY SELECT v_count, v_deleted, v_inserted,
                        v_skipped, v_skip_err, v_failed;
END;
$function$

COMMENT ON FUNCTION vendite.fn_genera_scadenze_lotto(p_lotto_id bigint, p_batch_size integer)
IS 'Fase 4.2 — wrapper di lotto del generatore del piano rate, task genera_scadenze_lotto dello step EMESSA. Modello: fn_snapshot_fattura_lotto. DUE filtri distinti e contati a parte, e la distinzione e'' sostanziale (D-Q pt.2): le fatture oltre la soglia DRAFT/EMESSA si saltano perche'' non hanno lavoro da fare (D-F), quelle con stato_esecuzione = ERRORE si saltano e NON si riprovano, perche'' questo e'' uno step a VALLE del DRAFT e li'' la fattura e'' un rifiuto, non un candidato — riprovarla qui vorrebbe dire portare verso la numerazione un documento gia'' dichiarato difettoso. Un contatore unico direbbe «cinque saltate» senza distinguere cinque documenti chiusi da cinque rotti, che per il cockpit sono l''opposto. Il fallimento di UNA fattura non uccide il giro (D-Q pt.1): sotto-blocco per fattura, marcatura C su fatture_log, si cattura raise_exception e non others. Al successo il task ritira le PROPRIE segnalazioni filtrando su meta->>''task'' e mai sul nome della funzione (D-Q pt.3).';
```

---
{% include-markdown "signature-core.md" %}
