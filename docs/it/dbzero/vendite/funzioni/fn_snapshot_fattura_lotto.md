{% include-markdown "it/dbzero/vendite/manual/fn_snapshot_fattura_lotto.md" %}
# ⚙️ Funzione `fn_snapshot_fattura_lotto`

```sql
CREATE FUNCTION fn_snapshot_fattura_lotto(p_lotto_id bigint, p_batch_size integer)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

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
    -- ⭐ Il codice di dominio viaggia nel campo CONSTRAINT della
    --    diagnostica, ed E' un codice di config.codici_errore:
    --    ancorato li', che ne e' l'unica definizione di dominio.
    --    (I due vicini restano TEXT: il testo di un messaggio e
    --    uno sqlstate non sono valori di una colonna.)
    v_err_code      config.codici_errore.codice%TYPE;
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
    -- ⭐ LA SOGLIA E' UN DATO, non una lista scritta qui (D33).
    --    Fino al 2026-08-30 questa funzione portava la propria copia di
    --    `NOT IN ('DRAFT','EMESSA')`. Erano OTTO copie della stessa frase,
    --    e `config.stati_doc_fiscale.congela_fiscale` era nata (I10) proprio
    --    per toglierle: era stata collegata a un solo lettore.
    -- ⚠️ Il comportamento NON cambia: verificato che sui sei stati esistenti
    --    colonna e lista dicono la stessa cosa. Cambia la SEDE, cioe' quante
    --    cose vanno toccate il giorno che il confine si sposta - da otto a una.
    -- ⚠️ E il trattamento dello STATO MANCANTE resta identico a prima: e' una
    --    decisione di questa funzione, non della soglia.
    -- Soglia identica al guard di congelamento, e ora: oltre EMESSA lo
    -- snapshot e' definitivo. Filtrare QUI e' diverso da provarci
    -- e riprendersi: non si tenta nemmeno la scrittura.
    SELECT array_agg(lf.fattura_id ORDER BY lf.fattura_id)
               FILTER (WHERE s.congela_fiscale IS FALSE),
           count(*)
               FILTER (WHERE COALESCE(s.congela_fiscale, true))
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
                    v_err_state = RETURNED_SQLSTATE,
                    -- ⭐ Il codice registrato a catalogo: e'
                    --    l'unica cosa che dice QUALE errore e'
                    --    stato, visto che lo sqlstate di un
                    --    errore di dominio e' sempre P0001.
                    v_err_code  = CONSTRAINT_NAME;

                v_failed := v_failed + 1;

                INSERT INTO vendite.fatture_log (
                            fattura_id, data_ora, messaggio,
                            status, disabilitato, meta)
                VALUES (v_fattura_id, now(),
                        format('Snapshot fattura non riuscito: %s', v_err_msg),
                        'C', FALSE,
                        jsonb_strip_nulls(jsonb_build_object(
                            'task',       'snapshot_indirizzi_lotto',
                            'lotto_id',   p_lotto_id,
                            'sqlstate',   v_err_state,
                            -- ⚠️ strip_nulls: una chiave presente e
                            --    vuota si legge peggio di una assente
                            --    (in lista, «non lo so» e «non c'e'»
                            --    diventano la stessa cella bianca).
                            'error_code', v_err_code,
                            'source',     'fn_snapshot_fattura_lotto')));
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
IS 'Wrapper di lotto dello snapshot della fattura: chiama le due sorelle — fn_snapshot_indirizzi_fattura e fn_snapshot_intestazione_fattura — nello stesso giro e nella stessa transazione. Rinominata da fn_snapshot_indirizzi_lotto il 2026-07-31: da quando scrive anche l''intestazione, il vecchio nome diceva meta'' della verita'' (precedente D-L). Il task_code del registry resta `snapshot_indirizzi_lotto`, che e'' l''identita'' stabile del passo di pipeline. (1) Le fatture oltre EMESSA si FILTRANO prima di scrivere (D-F esteso): per un documento definitivo non c''e'' lavoro da fare, quindi il giro non si ferma e resta una sola nota informativa di lotto. (2) Il fallimento di UNA fattura non uccide il giro (D-Q): sotto-blocco BEGIN/EXCEPTION che comprende ENTRAMBE le sorelle — se una fallisce non resta niente di parziale — la fattura viene marcata ''C'' su fatture_log e il giro prosegue. Si cattura raise_exception (P0001), non others. (3) Al successo il task ritira le PROPRIE segnalazioni, filtrando su meta->>''task'': il source e'' il nome della funzione e le funzioni si rinominano, il task_code no. Sei contatori: fatture_count, inserted_rows, updated_rows, intestazioni_scritte, skipped_rows, failed_rows — l''intestazione non produce righe e non poteva entrare in inserted/updated senza mescolare unita'' di misura. piano-db-satelliti-fattura Fase 2.2 + brief intestazione §3.3. ⭐ rev 2026-08-21 (cantiere brief-db-liste-drawer-lotto, L1/P-3): il ramo EXCEPTION cattura anche CONSTRAINT_NAME e lo scrive in meta->>''error_code''. Prima registrava solo RETURNED_SQLSTATE, che qui vale SEMPRE P0001 per costruzione — la clausola cattura `raise_exception` e nient''altro — quindi come codice non distingueva niente: una chiave che risponde sempre lo stesso valore. Il codice registrato a catalogo, quello su cui il backend mappa status HTTP e ui_action, viaggia nel campo CONSTRAINT della diagnostica, dove lo mette script.fn_log_and_raise_error. jsonb_strip_nulls e non jsonb_build_object nudo: CONSTRAINT_NAME e'' vuoto quando l''errore non viene da fn_log_and_raise_error (un CHECK violato, per dire), e una chiave presente con valore null in una lista si legge come una cella bianca indistinguibile da «non c''e''». Le altre quattro chiavi non sono mai nulle, quindi lo strip non puo'' mangiare altro. FORWARD-ONLY: le righe di log gia'' scritte non hanno il codice e non lo avranno mai, perche'' dal testo del messaggio non e'' ricostruibile.';
```

</div>

---
{% include-markdown "signature-core.md" %}
