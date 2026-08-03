{% include-markdown "it/dbzero/vendite/manual/fn_riporta_lotto_a_draft.md" %}
# ⚙️ Funzione `fn_riporta_lotto_a_draft`

```sql
CREATE FUNCTION fn_riporta_lotto_a_draft(p_lotto_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_riporta_lotto_a_draft(p_lotto_id bigint)
 RETURNS TABLE(updated_lotti integer, updated_attivita integer, deleted_fatture integer, deleted_righe integer, riemesse_attivita integer, annullati_task_run integer)
 LANGUAGE plpgsql
AS $function$
-- Scopo: rollback di un lotto PRE-FISCALE verso DRAFT — delega la
--        pulizia alla primitiva, azzera lo STATO DI ESECUZIONE del
--        lotto (task_run ad ANNULLATO) e lo marca come riaperto.
--        Il lotto resta vivo e ripartira' dallo step DRAFT.
-- Perimetro (RD-1): si torna indietro per QUALSIASI motivo.
--        MASSIVO **e** GIORNALIERO, su lotti DRAFT o EMESSA.
-- RD-4:  il ripristino delle TABELLE non si scrive qui, e' della
--        primitiva. Qui vive lo stato del LOTTO — stato fiscale,
--        stato operativo, riaperto_il e stato di esecuzione.
-- RD-6:  🔴 i task_run si chiudono ad ANNULLATO, altrimenti
--        fn_resolve_lotto_task_execution_mode li vede COMPLETATO e
--        risponde SKIP: il lotto riaperto rilancia A VUOTO.
DECLARE
    v_tipo_lotto           vendite.fatturazione_lotti.tipo_lotto%TYPE;
    v_stato_doc_fiscale_id vendite.fatturazione_lotti.stato_doc_fiscale_id%TYPE;
    v_lock_batch_id        vendite.fatturazione_lotti.lock_batch_id%TYPE;
    v_draft_id             config.stati_doc_fiscale.id%TYPE;
    v_emessa_id            config.stati_doc_fiscale.id%TYPE;
    v_fatture_ids          BIGINT[];
    v_numerate             INTEGER := 0;
    v_bad_fatture          INTEGER := 0;
    v_updated_lotti        INTEGER := 0;
    v_updated_attivita     INTEGER := 0;
    v_deleted_fatture      INTEGER := 0;
    v_deleted_righe        INTEGER := 0;
    v_riemesse_attivita    INTEGER := 0;
    v_annullati_task_run   INTEGER := 0;
BEGIN
    IF p_lotto_id IS NULL OR p_lotto_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_riporta_lotto_a_draft', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_lotto_id', 'valore', p_lotto_id), NULL::uuid, 'p_lotto_id obbligatorio e > 0');
    END IF;

    SELECT fl.tipo_lotto, fl.stato_doc_fiscale_id, fl.lock_batch_id
      INTO v_tipo_lotto, v_stato_doc_fiscale_id, v_lock_batch_id
      FROM vendite.fatturazione_lotti fl WHERE fl.id = p_lotto_id;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_riporta_lotto_a_draft', 'E_VALORE_MANCANTE',
            jsonb_build_object('lotto_id', p_lotto_id), NULL::uuid, concat('lotto_id ', p_lotto_id));
    END IF;

    SELECT s.id INTO v_draft_id FROM config.stati_doc_fiscale s WHERE s.codice_interno = 'DRAFT' AND s.attivo IS TRUE LIMIT 1;
    IF v_draft_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_riporta_lotto_a_draft', 'E_CONFIG_MANCANTE',
            jsonb_build_object('codice_interno', 'DRAFT'), NULL::uuid, 'stato DRAFT non configurato');
    END IF;

    SELECT s.id INTO v_emessa_id FROM config.stati_doc_fiscale s WHERE s.codice_interno = 'EMESSA' AND s.attivo IS TRUE LIMIT 1;
    IF v_emessa_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_riporta_lotto_a_draft', 'E_CONFIG_MANCANTE',
            jsonb_build_object('codice_interno', 'EMESSA'), NULL::uuid, 'stato EMESSA non configurato');
    END IF;

    -- Il lotto dev'essere PRE-FISCALE. Oltre EMESSA c'e' la
    -- numerazione, e da li' non si torna.
    IF v_stato_doc_fiscale_id IS DISTINCT FROM v_draft_id
       AND v_stato_doc_fiscale_id IS DISTINCT FROM v_emessa_id THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_riporta_lotto_a_draft', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'stato_doc_fiscale', 'valore', v_stato_doc_fiscale_id, 'lotto_id', p_lotto_id),
            NULL::uuid, concat('ritorno a DRAFT solo da DRAFT o EMESSA, stato=', v_stato_doc_fiscale_id));
    END IF;

    SELECT count(*) INTO v_bad_fatture
      FROM vendite.fatture f JOIN vendite.fatturazione_lotti_fatture lf ON lf.fattura_id = f.id
     WHERE lf.lotto_id = p_lotto_id
       AND f.stato_doc_fiscale_id IS DISTINCT FROM v_draft_id
       AND f.stato_doc_fiscale_id IS DISTINCT FROM v_emessa_id;

    IF v_bad_fatture > 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_riporta_lotto_a_draft', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'fatture_non_pre_fiscali', 'count', v_bad_fatture, 'lotto_id', p_lotto_id),
            NULL::uuid, concat('fatture non pre-fiscali (DRAFT/EMESSA): ', v_bad_fatture));
    END IF;

    -- ⚠️ Guard ESPLICITO sul numero: si guarda il FATTO, non lo stato
    -- che dovrebbe implicarlo. Il danno sarebbe irreversibile.
    SELECT count(*) INTO v_numerate
      FROM vendite.fatture f JOIN vendite.fatturazione_lotti_fatture lf ON lf.fattura_id = f.id
     WHERE lf.lotto_id = p_lotto_id AND f.numero IS NOT NULL;

    IF v_numerate > 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_riporta_lotto_a_draft', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'fatture_numerate', 'count', v_numerate, 'lotto_id', p_lotto_id),
            NULL::uuid, concat('fatture gia'' numerate: ', v_numerate));
    END IF;

    SELECT array_agg(lf.fattura_id) INTO v_fatture_ids
      FROM vendite.fatturazione_lotti_fatture lf WHERE lf.lotto_id = p_lotto_id;
    IF v_fatture_ids IS NULL THEN v_fatture_ids := ARRAY[]::BIGINT[]; END IF;

    -- Concorrenza (punto E): dopo TUTTE le guard, com'e' convenzione —
    -- una chiamata invalida non deve serializzare gli altri. Forma a
    -- DUE argomenti, entrambi int4 (unico overload a due esistente):
    -- la chiave passa da hashtext e non da un cast, che esploderebbe
    -- oltre i 2 miliardi.
    PERFORM pg_advisory_xact_lock(
        hashtext('vendite.fn_riporta_lotto_a_draft'),
        hashtext(p_lotto_id::text)
    );

    -- Pulizia: tutta della primitiva (RD-4). Il lock_batch_id SI passa,
    -- perche' e' un reset GLOBALE del lotto — e' il per-fattura che deve
    -- passare NULL (C-22).
    SELECT c.deleted_fatture, c.deleted_righe, c.updated_attivita, c.riemesse_attivita
      INTO v_deleted_fatture, v_deleted_righe, v_updated_attivita, v_riemesse_attivita
      FROM vendite.fn_cleanup_fatture_by_ids(v_fatture_ids, v_lock_batch_id) AS c;

    -- 🔴 RD-6 — lo stato di esecuzione del lotto.
    -- fn_resolve_lotto_task_execution_mode legge l'ULTIMO task_run per
    -- (lotto, task, stato_doc): COMPLETATO -> SKIP, ANNULLATO -> RUN.
    -- Senza questo passo il lotto riaperto rilancia e i task vengono
    -- saltati tutti, in silenzio: nessun errore, nessun task_run nuovo,
    -- e il giro sembra riuscito.
    -- ⚠️ NON basta `attivo = false`: quella SELECT non filtra su
    -- `attivo`. La leva e' l'ESITO, e la funzione per scriverlo esiste
    -- gia' — non si inventa un meccanismo nuovo.
    -- ⚠️ Si annullano le corse di TUTTI gli step, non solo di DRAFT: il
    -- lotto risalira' l'intera catena, e la pulizia ha cancellato tutto
    -- cio' che quelle corse avevano prodotto — nessuna deve piu' avere
    -- voce sul giro successivo.
    WITH da_annullare AS (
      SELECT r.id
        FROM vendite.fatturazione_lotti_task_runs r
       WHERE r.lotto_id = p_lotto_id
         AND r.attivo IS TRUE
         AND r.task_stato IS DISTINCT FROM 'ANNULLATO'
    ), annullati AS (
      SELECT vendite.fn_cancel_lotto_task_run(
               d.id,
               jsonb_build_object('motivo', 'ritorno_a_draft', 'lotto_id', p_lotto_id)
             )
        FROM da_annullare d
    )
    SELECT count(*)::INTEGER INTO v_annullati_task_run FROM annullati;

    -- stato_operativo torna APERTO: il lotto ha di nuovo lavoro da
    -- fare. stato_lotto NON si tocca — ha una macchina a stati cablata
    -- in Python e da COMPLETATO come da ERRORE l'unica transizione
    -- ammessa e' verso IN_ESECUZIONE, che e' quello che fara' il giro
    -- successivo.
    UPDATE vendite.fatturazione_lotti
       SET stato_doc_fiscale_id = v_draft_id,
           stato_operativo      = 'APERTO',
           riaperto_il          = now(),
           data_update          = now(),
           user_update          = current_user
     WHERE id = p_lotto_id;
    GET DIAGNOSTICS v_updated_lotti = ROW_COUNT;

    RETURN QUERY SELECT v_updated_lotti, v_updated_attivita, v_deleted_fatture,
                        v_deleted_righe, v_riemesse_attivita, v_annullati_task_run;
END;
$function$

COMMENT ON FUNCTION vendite.fn_riporta_lotto_a_draft(p_lotto_id bigint)
IS 'Rollback di un lotto PRE-FISCALE (DRAFT o EMESSA) verso DRAFT, per MASSIVO e GIORNALIERO. Delega TUTTA la pulizia delle tabelle a fn_cleanup_fatture_by_ids (RD-4) e si occupa dello stato del LOTTO: stato fiscale a DRAFT, stato_operativo APERTO, riaperto_il (RD-2) e stato di ESECUZIONE. 🔴 RD-6: chiude ad ANNULLATO tutti i task_run attivi del lotto, perche'' fn_resolve_lotto_task_execution_mode legge l''ultimo task_run e su COMPLETATO risponde SKIP — senza questo passo il lotto riaperto rilancia A VUOTO, senza errori e senza task_run nuovi. ⚠️ Non basterebbe attivo = false: quella SELECT non filtra su attivo. Le corse non si cancellano: si chiudono con esito, e il giro nuovo apre tentativo = MAX+1, quindi la storia resta leggibile per intero. RD-1: si torna indietro per QUALSIASI motivo; cio'' che resta vietato e'' numerare un documento incoerente (guard D-K). ⚠️ Rifiuta se una sola fattura e'' gia'' NUMERATA: guarda il numero, non lo stato. Sorella di fn_annulla_lotto_da_draft, che invece CHIUDE il lotto portandolo ad ANNULLATA.';
```

---
{% include-markdown "signature-core.md" %}
