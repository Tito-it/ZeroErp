# ⚙️ Funzione `fn_snapshot_indirizzi_lotto`

```sql
CREATE FUNCTION fn_snapshot_indirizzi_lotto(p_lotto_id bigint, p_batch_size integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_snapshot_indirizzi_lotto(p_lotto_id bigint, p_batch_size integer DEFAULT 1000)
 RETURNS TABLE(fatture_count integer, inserted_rows integer, updated_rows integer, skipped_rows integer, failed_rows integer)
 LANGUAGE plpgsql
AS $function$
-- Scopo: eseguire lo snapshot degli indirizzi su tutte le fatture
--        lavorabili di un lotto, senza che una fattura definitiva
--        o una fattura difettosa fermino le altre.
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
    v_skipped       INTEGER := 0;
    v_failed        INTEGER := 0;
    v_tmp_ins       INTEGER;
    v_tmp_upd       INTEGER;
    v_err_msg       TEXT;
    v_err_state     TEXT;
BEGIN
    -- ===== Guard parametri =====
    IF p_lotto_id IS NULL OR p_lotto_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_snapshot_indirizzi_lotto', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_lotto_id', 'valore', p_lotto_id),
            NULL::uuid, 'p_lotto_id obbligatorio e > 0');
    END IF;

    IF p_batch_size IS NULL OR p_batch_size <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_snapshot_indirizzi_lotto', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_batch_size', 'valore', p_batch_size),
            NULL::uuid, 'p_batch_size obbligatorio e > 0');
    END IF;

    v_batch_size := p_batch_size;

    -- ===== Chi si lavora e chi no, in una sola lettura =====
    -- La soglia e' la stessa del guard di congelamento montato in
    -- 1.2: oltre EMESSA lo snapshot e' definitivo. Filtrare QUI e'
    -- diverso da provarci e riprendersi: non si tenta nemmeno la
    -- scrittura, quindi non si sveglia il guard.
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
        -- Nessuna fattura lavorabile: puo' essere un lotto vuoto
        -- (nulla da dire) o un lotto tutto definitivo (da dire).
        IF v_skipped > 0 THEN
            PERFORM vendite.fn_log_pipeline_fase(
                p_lotto_id, NULL, 'Snapshot indirizzi', 'I',
                format('Nessuna fattura lavorabile: %s gia'' oltre EMESSA, snapshot definitivo.', v_skipped),
                jsonb_build_object('task', 'snapshot_indirizzi_lotto',
                                   'skipped', v_skipped));
        END IF;

        RETURN QUERY SELECT 0, 0, 0, v_skipped, 0;
        RETURN;
    END IF;

    v_max := array_length(v_ids, 1);

    -- ===== Giro a batch, come il fratello IVA =====
    WHILE v_start <= v_max LOOP
        v_end   := LEAST(v_start + v_batch_size - 1, v_max);
        v_slice := v_ids[v_start:v_end];

        FOR i IN 1..array_length(v_slice, 1) LOOP
            v_fattura_id    := v_slice[i];
            v_fatture_count := v_fatture_count + 1;

            BEGIN
                SELECT r.inserted_rows, r.updated_rows
                  INTO v_tmp_ins, v_tmp_upd
                  FROM vendite.fn_snapshot_indirizzi_fattura(v_fattura_id) r;

                v_inserted := v_inserted + COALESCE(v_tmp_ins, 0);
                v_updated  := v_updated  + COALESCE(v_tmp_upd, 0);

                -- Ritiro della PROPRIA segnalazione precedente:
                -- il problema di ieri e' risolto, quindi la
                -- bandiera va abbassata. Senza, un rilancio dello
                -- step lascerebbe la fattura in ERRORE per
                -- sempre. Il filtro su meta->>'source' e'
                -- essenziale: si ritira solo cio' che questo task
                -- ha alzato, mai la segnalazione di un altro.
                -- Il resto lo fa da solo il trigger AFTER UPDATE
                -- su fatture_log, che ricalcola critical e
                -- stato_esecuzione dai soli log attivi.
                UPDATE vendite.fatture_log fl
                   SET disabilitato = TRUE
                 WHERE fl.fattura_id = v_fattura_id
                   AND fl.disabilitato IS FALSE
                   AND fl.status = 'C'
                   AND fl.meta->>'source' = 'fn_snapshot_indirizzi_lotto';

            EXCEPTION WHEN raise_exception THEN
                -- Solo gli errori di dominio (P0001) finiscono
                -- qui: un guasto di sistema ha altro SQLSTATE e
                -- deve continuare a salire. Vedi testata.
                GET STACKED DIAGNOSTICS
                    v_err_msg   = MESSAGE_TEXT,
                    v_err_state = RETURNED_SQLSTATE;

                v_failed := v_failed + 1;

                -- Marcatura critical: e' cio' che impedisce a
                -- questa fattura di diventare EMESSA, mentre le
                -- altre del lotto proseguono.
                INSERT INTO vendite.fatture_log (
                            fattura_id, data_ora, messaggio,
                            status, disabilitato, meta)
                VALUES (v_fattura_id, now(),
                        format('Snapshot indirizzi non riuscito: %s', v_err_msg),
                        'C', FALSE,
                        jsonb_build_object(
                            'task',     'snapshot_indirizzi_lotto',
                            'lotto_id', p_lotto_id,
                            'sqlstate', v_err_state,
                            'source',   'fn_snapshot_indirizzi_lotto'));
            END;
        END LOOP;

        v_start := v_end + 1;
    END LOOP;

    -- ===== Una nota sola, a fine giro, per i documenti chiusi =====
    IF v_skipped > 0 THEN
        PERFORM vendite.fn_log_pipeline_fase(
            p_lotto_id, NULL, 'Snapshot indirizzi', 'I',
            format('%s fatture non toccate perche'' oltre EMESSA: snapshot gia'' definitivo.', v_skipped),
            jsonb_build_object('task', 'snapshot_indirizzi_lotto',
                               'skipped', v_skipped,
                               'lavorate', v_fatture_count));
    END IF;

    RETURN QUERY SELECT v_fatture_count, v_inserted, v_updated, v_skipped, v_failed;
END;
$function$

COMMENT ON FUNCTION vendite.fn_snapshot_indirizzi_lotto(p_lotto_id bigint, p_batch_size integer)
IS 'Wrapper di lotto dello snapshot indirizzi, sulla forma di vendite.fn_ricalcola_riepiloghi_iva_lotto (batch + chiamata per-fattura) ma con due comportamenti diversi, entrambi voluti. (1) Le fatture oltre EMESSA si FILTRANO prima di scrivere (D-F esteso agli indirizzi): per un documento definitivo questo task non ha lavoro da fare — lo snapshot e'' stato preso in bozza ed e'' quello definitivo — quindi il giro non si ferma, non e'' fallito, le altre fatture ricevono il loro lavoro completo e resta una sola nota informativa di lotto. Il fratello IVA non filtra: con lui una sola fattura definitiva ucciderebbe il lotto. (2) Il fallimento di UNA fattura non uccide il giro: sotto-blocco BEGIN/EXCEPTION per fattura (schema gia'' in uso in fn_batch_upsert_commessa_attivita), la fattura difettosa viene marcata ''C'' su fatture_log — che e'' cio'' che le impedisce di diventare EMESSA — e il giro prosegue, cosi'' l''operatore vede TUTTI i clienti incompleti in una volta invece di scoprirne uno per esecuzione. Si cattura raise_exception (P0001), non others: gli errori di dominio arrivano tutti come P0001 da fn_log_and_raise_error, mentre un guasto di sistema (permesso negato, funzione inesistente, deadlock) ha altro SQLSTATE e deve salire. Ritorna cinque contatori — fatture_count, inserted_rows, updated_rows, skipped_rows, failed_rows — perche'' con tre un giro tutto definitivo, un giro gia'' allineato e un giro con fatture rotte si leggerebbero identici. (3) Quando lo snapshot di una fattura riesce, il task RITIRA le proprie segnalazioni critiche precedenti su quella fattura (disabilitato = true, filtrando su meta->>''source''): serve perche'' la via d''uscita voluta e'' «si rilancia lo stesso step», e senza il ritiro la fattura resterebbe in ERRORE per un problema gia'' risolto. Solo le proprie: spegnere la segnalazione di un altro task equivarrebbe a dichiarare risolto cio'' che non si e'' guardato. Il ricalcolo di critical/stato_esecuzione lo fa da se'' il trigger AFTER UPDATE su fatture_log. piano-db-satelliti-fattura Fase 2.2.';
```

---
{% include-markdown "signature-core.md" %}
