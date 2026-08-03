{% include-markdown "it/dbzero/vendite/manual/fn_riporta_lotto_a_draft.md" %}
# ⚙️ Funzione `fn_riporta_lotto_a_draft`

```sql
CREATE FUNCTION fn_riporta_lotto_a_draft(p_lotto_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_riporta_lotto_a_draft(p_lotto_id bigint)
 RETURNS TABLE(updated_lotti integer, updated_attivita integer, deleted_fatture integer, deleted_righe integer, riemesse_attivita integer)
 LANGUAGE plpgsql
AS $function$
-- Scopo: rollback di un lotto PRE-FISCALE verso DRAFT — cancella le
--        fatture, ripristina attivita' e commesse_attivita (delegando
--        tutto alla primitiva) e marca il lotto come riaperto. Il
--        lotto resta vivo e ripartira' dallo step DRAFT.
-- Perimetro (RD-1): si torna indietro per QUALSIASI motivo. Nessun
--        guard sulla causa. MASSIVO **e** GIORNALIERO, su lotti
--        DRAFT o EMESSA.
-- RD-4:  il ripristino NON si scrive qui. Questa funzione decide
--        COSA si riporta indietro e in quale stato lascia il lotto;
--        il COME si ripulisce e' della primitiva, che ha tre
--        chiamanti e deve comportarsi allo stesso modo per tutti.
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
    -- numerazione, e da li' non si torna: e' il punto di non ritorno
    -- del documento fiscale, non una scelta di questa funzione.
    IF v_stato_doc_fiscale_id IS DISTINCT FROM v_draft_id
       AND v_stato_doc_fiscale_id IS DISTINCT FROM v_emessa_id THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_riporta_lotto_a_draft', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'stato_doc_fiscale', 'valore', v_stato_doc_fiscale_id, 'lotto_id', p_lotto_id),
            NULL::uuid, concat('ritorno a DRAFT solo da DRAFT o EMESSA, stato=', v_stato_doc_fiscale_id));
    END IF;

    -- Stesso criterio sulle fatture (perimetro pre-fiscale, D-L.2).
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

    -- ⚠️ Guard ESPLICITO sul numero, e non solo sullo stato. A EMESSA
    -- la fattura non e' numerata (C-19), quindi il controllo di stato
    -- basterebbe: ma il danno qui sarebbe irreversibile — cancellare
    -- una fattura gia' numerata apre un buco nella numerazione
    -- fiscale. Si guarda il FATTO (il numero), non lo stato che
    -- dovrebbe implicarlo.
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

    -- Concorrenza (punto E dell'analisi): il runner ha il suo
    -- E_PIPELINE_LOTTO_IN_ESECUZIONE, ma e' applicativo e non protegge
    -- chi chiama la funzione per altra via.
    -- POSIZIONE: dopo TUTTE le guard e i lookup di validazione, com'e'
    -- convenzione di casa — una chiamata invalida (lotto inesistente,
    -- fattura numerata) non deve serializzare gli altri chiamanti. Qui
    -- il rischio TOCTOU e' benigno: due ritorni concorrenti sullo stesso
    -- lotto portano entrambi allo stesso esito, il secondo non trova
    -- piu' fatture da cancellare.
    -- ⚠️ Forma a DUE argomenti (quella a uno condivide uno spazio di
    -- lock globale con feature scorrelate), e i due argomenti sono DUE
    -- int4: `(integer, integer)` e `(bigint)` sono gli unici overload
    -- esistenti. La chiave passa da hashtext e NON da un cast, perche'
    -- `p_lotto_id::int` esploderebbe oltre i 2 miliardi mentre una
    -- collisione di hash serializza due lotti diversi — cioe' sbaglia
    -- dalla parte prudente.
    PERFORM pg_advisory_xact_lock(
        hashtext('vendite.fn_riporta_lotto_a_draft'),
        hashtext(p_lotto_id::text)
    );

    -- ⚠️ Qui il lock_batch_id SI passa, ed e' corretto: e' un reset
    -- GLOBALE del lotto, quindi deve liberare anche le attivita'
    -- agganciate al batch che non sono mai diventate riga. E' il
    -- per-fattura che deve passare NULL (C-22).
    -- RD-4: il ripristino delle commesse_attivita arriva da qui, non
    -- si riscrive. Se domani la pulizia dovra' toccare un livello in
    -- piu', lo si aggiunge in UN posto e le tre chiamanti lo ereditano.
    SELECT c.deleted_fatture, c.deleted_righe, c.updated_attivita, c.riemesse_attivita
      INTO v_deleted_fatture, v_deleted_righe, v_updated_attivita, v_riemesse_attivita
      FROM vendite.fn_cleanup_fatture_by_ids(v_fatture_ids, v_lock_batch_id) AS c;

    -- stato_operativo torna APERTO: il lotto ha di nuovo lavoro da
    -- fare. stato_lotto NON si tocca di proposito — ha una macchina a
    -- stati cablata in Python, e da COMPLETATO come da ERRORE l'unica
    -- transizione ammessa e' verso IN_ESECUZIONE, che e' esattamente
    -- quello che fara' il prossimo giro.
    UPDATE vendite.fatturazione_lotti
       SET stato_doc_fiscale_id = v_draft_id,
           stato_operativo      = 'APERTO',
           riaperto_il          = now(),
           data_update          = now(),
           user_update          = current_user
     WHERE id = p_lotto_id;
    GET DIAGNOSTICS v_updated_lotti = ROW_COUNT;

    RETURN QUERY SELECT v_updated_lotti, v_updated_attivita, v_deleted_fatture, v_deleted_righe, v_riemesse_attivita;
END;
$function$

COMMENT ON FUNCTION vendite.fn_riporta_lotto_a_draft(p_lotto_id bigint)
IS 'Rollback di un lotto PRE-FISCALE (DRAFT o EMESSA) verso DRAFT, per MASSIVO e GIORNALIERO. Delega TUTTA la pulizia a fn_cleanup_fatture_by_ids — fatture, righe, riepiloghi, log, note, link, storno arrotondamenti, sblocco attivita_fatturabili e ritorno delle commesse_attivita a NON_EMESSA (RD-4): questa funzione decide COSA si riporta indietro, non COME si ripulisce. Marca il lotto con riaperto_il (RD-2), lo rimette APERTO e lo lascia vivo: ripartira'' dallo step DRAFT. RD-1: si torna indietro per QUALSIASI motivo, nessun guard sulla causa; cio'' che resta vietato e'' numerare un documento incoerente (guard D-K). ⚠️ Rifiuta se una sola fattura e'' gia'' NUMERATA: il controllo guarda il numero e non lo stato, perche'' il danno sarebbe irreversibile. ⚠️ NON tocca i task_runs: nessuno li consulta per decidere (misurato 2026-08-03), sono un registro di esecuzione. Sorella di fn_annulla_lotto_da_draft, che invece CHIUDE il lotto portandolo ad ANNULLATA.';
```

---
{% include-markdown "signature-core.md" %}
