# ⚙️ Funzione `fn_snapshot_fattura_lotto`

```sql
CREATE FUNCTION fn_snapshot_fattura_lotto(p_lotto_id bigint, p_batch_size integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_snapshot_fattura_lotto(p_lotto_id bigint, p_batch_size integer DEFAULT 1000)
 RETURNS TABLE(fatture_count integer, inserted_rows integer, updated_rows integer, intestazioni_scritte integer, skipped_rows integer, failed_rows integer)
 LANGUAGE plpgsql
AS $function$
-- Scopo: scrivere lo snapshot della fattura — indirizzi E
--        intestazione fiscale — su tutte le fatture lavorabili di
--        un lotto, senza che una fattura definitiva o una fattura
--        difettosa fermino le altre.
-- Uso:   task snapshot_indirizzi_lotto dello step DRAFT.
DECLARE
    v_ids           BIGINT[];
    v_slice         BIGINT[];
    v_fattura_id    vendite.fatture.id%TYPE;
    v_start         INTEGER := 1;
    v_end           INTEGER := 0;
    v_max           INTEGER := 0;
    v_batch_size    INTEGER := 1000;
    v_fatture_count INTEGER := 0;
    v_inserted      INTEGER := 0;
    v_updated       INTEGER := 0;
    v_intestazioni  INTEGER := 0;
    v_skipped       INTEGER := 0;
    v_failed        INTEGER := 0;
    v_tmp_ins       INTEGER;
    v_tmp_upd       INTEGER;
    v_tmp_int       BOOLEAN;
    v_err_msg       TEXT;
    v_err_state     TEXT;
BEGIN
    -- ===== Guard parametri =====
    IF p_lotto_id IS NULL OR p_lotto_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_snapshot_fattura_lotto', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_lotto_id', 'valore', p_lotto_id),
            NULL::uuid, 'p_lotto_id obbligatorio e > 0');
    END IF;

    IF p_batch_size IS NULL OR p_batch_size <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_snapshot_fattura_lotto', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_batch_size', 'valore', p_batch_size),
            NULL::uuid, 'p_batch_size obbligatorio e > 0');
    END IF;

    v_batch_size := p_batch_size;

    -- ===== Chi si lavora e chi no, in una sola lettura =====
    -- Soglia identica al guard di congelamento: oltre EMESSA lo
    -- snapshot e' definitivo. Filtrare QUI e' diverso da provarci
    -- e riprendersi: non si tenta nemmeno la scrittura.
    SELECT array_agg(lf.fattura_id ORDER BY lf.fattura_id)
               FILTER (WHERE s.codice_interno IN ('DRAFT', 'EMESSA')),
           count(*)
               FILTER (WHERE s.codice_interno IS NULL
                          OR s.codice_interno NOT IN ('DRAFT', 'EMESSA'))
      INTO v_ids, v_skipped
      FROM vendite.fatturazione_lotti_fatture lf
      JOIN vendite.fatture f ON f.id = lf.fattura_id
      LEFT JOIN config.stati_doc_fiscale s ON s.id = f.stato_doc_fiscale_id
     WHERE lf.lotto_id = p_lotto_id;

    v_skipped := COALESCE(v_skipped, 0);

    IF v_ids IS NULL THEN
        IF v_skipped > 0 THEN
            PERFORM vendite.fn_log_pipeline_fase(
                p_lotto_id, NULL, 'Snapshot fattura', 'I',
                format('Nessuna fattura lavorabile: %s gia'' oltre EMESSA, snapshot definitivo.', v_skipped),
                jsonb_build_object('task', 'snapshot_indirizzi_lotto',
                                   'skipped', v_skipped));
        END IF;

        RETURN QUERY SELECT 0, 0, 0, 0, v_skipped, 0;
        RETURN;
    END IF;

    v_max := array_length(v_ids, 1);

    WHILE v_start <= v_max LOOP
        v_end   := LEAST(v_start + v_batch_size - 1, v_max);
        v_slice := v_ids[v_start:v_end];

        FOR i IN 1..array_length(v_slice, 1) LOOP
            v_fattura_id    := v_slice[i];
            v_fatture_count := v_fatture_count + 1;

            BEGIN
                -- Le due sorelle, nello stesso sotto-blocco: se
                -- una fallisce non resta niente di parziale.
                SELECT r.inserted_rows, r.updated_rows
                  INTO v_tmp_ins, v_tmp_upd
                  FROM vendite.fn_snapshot_indirizzi_fattura(v_fattura_id) r;

                SELECT r.scritta
                  INTO v_tmp_int
                  FROM vendite.fn_snapshot_intestazione_fattura(v_fattura_id) r;

                v_inserted := v_inserted + COALESCE(v_tmp_ins, 0);
                v_updated  := v_updated  + COALESCE(v_tmp_upd, 0);

                IF v_tmp_int IS TRUE THEN
                    v_intestazioni := v_intestazioni + 1;
                END IF;

                -- Ritiro della PROPRIA segnalazione precedente:
                -- il problema e' risolto, la bandiera si abbassa.
                -- ⚠️ Il filtro e' sul TASK e non sul nome della
                -- funzione: le funzioni si rinominano (e' appena
                -- successo), il task_code no. Mai le righe altrui.
                UPDATE vendite.fatture_log fl
                   SET disabilitato = TRUE
                 WHERE fl.fattura_id = v_fattura_id
                   AND fl.disabilitato IS FALSE
                   AND fl.status = 'C'
                   AND fl.meta->>'task' = 'snapshot_indirizzi_lotto';

            EXCEPTION WHEN raise_exception THEN
                -- Solo gli errori di dominio (P0001) finiscono
                -- qui: un guasto di sistema ha altro SQLSTATE e
                -- deve continuare a salire.
                GET STACKED DIAGNOSTICS
                    v_err_msg   = MESSAGE_TEXT,
                    v_err_state = RETURNED_SQLSTATE;

                v_failed := v_failed + 1;

                INSERT INTO vendite.fatture_log (
                            fattura_id, data_ora, messaggio,
                            status, disabilitato, meta)
                VALUES (v_fattura_id, now(),
                        format('Snapshot fattura non riuscito: %s', v_err_msg),
                        'C', FALSE,
                        jsonb_build_object(
                            'task',     'snapshot_indirizzi_lotto',
                            'lotto_id', p_lotto_id,
                            'sqlstate', v_err_state,
                            'source',   'fn_snapshot_fattura_lotto'));
            END;
        END LOOP;

        v_start := v_end + 1;
    END LOOP;

    -- ===== Una nota sola, a fine giro, per i documenti chiusi =====
    IF v_skipped > 0 THEN
        PERFORM vendite.fn_log_pipeline_fase(
            p_lotto_id, NULL, 'Snapshot fattura', 'I',
            format('%s fatture non toccate perche'' oltre EMESSA: snapshot gia'' definitivo.', v_skipped),
            jsonb_build_object('task', 'snapshot_indirizzi_lotto',
                               'skipped', v_skipped,
                               'lavorate', v_fatture_count));
    END IF;

    RETURN QUERY SELECT v_fatture_count, v_inserted, v_updated,
                        v_intestazioni, v_skipped, v_failed;
END;
$function$

COMMENT ON FUNCTION vendite.fn_snapshot_fattura_lotto(p_lotto_id bigint, p_batch_size integer)
IS 'Wrapper di lotto dello snapshot della fattura: chiama le due sorelle — fn_snapshot_indirizzi_fattura e fn_snapshot_intestazione_fattura — nello stesso giro e nella stessa transazione. Rinominata da fn_snapshot_indirizzi_lotto il 2026-07-31: da quando scrive anche l''intestazione, il vecchio nome diceva meta'' della verita'' (precedente D-L). Il task_code del registry resta `snapshot_indirizzi_lotto`, che e'' l''identita'' stabile del passo di pipeline. (1) Le fatture oltre EMESSA si FILTRANO prima di scrivere (D-F esteso): per un documento definitivo non c''e'' lavoro da fare, quindi il giro non si ferma e resta una sola nota informativa di lotto. (2) Il fallimento di UNA fattura non uccide il giro (D-Q): sotto-blocco BEGIN/EXCEPTION che comprende ENTRAMBE le sorelle — se una fallisce non resta niente di parziale — la fattura viene marcata ''C'' su fatture_log e il giro prosegue. Si cattura raise_exception (P0001), non others. (3) Al successo il task ritira le PROPRIE segnalazioni, filtrando su meta->>''task'': il source e'' il nome della funzione e le funzioni si rinominano, il task_code no. Sei contatori: fatture_count, inserted_rows, updated_rows, intestazioni_scritte, skipped_rows, failed_rows — l''intestazione non produce righe e non poteva entrare in inserted/updated senza mescolare unita'' di misura. piano-db-satelliti-fattura Fase 2.2 + brief intestazione §3.3.';
```

---
{% include-markdown "signature-core.md" %}
