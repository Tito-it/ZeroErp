{% include-markdown "it/dbzero/vendite/manual/fn_crea_revisione_offerta.md" %}
# ⚙️ Funzione `fn_crea_revisione_offerta`

```sql
CREATE FUNCTION fn_crea_revisione_offerta(p_offerta_id bigint, p_user text)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_crea_revisione_offerta(p_offerta_id bigint, p_user text)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
-- Scopo:
--   Creare una nuova revisione (rev.N+1) in stato BOZZA a partire
--   da un'offerta in stato EMESSA. Copia testata, eccezioni attive
--   e utility (1:1). Il trigger z90 revisione (Step 6) marca
--   automaticamente il padre (rev.N) come SUPERATA al momento
--   dell'INSERT della testata rev.N+1.
--
-- Regole:
--   - stato corrente DEVE essere EMESSA
--   - uid e codice OFC-* generati ex novo (default + BEFORE trigger)
--   - revisione_numero = rev.N.revisione_numero + 1
--   - revisione_padre_id = p_offerta_id
--   - eccezioni: solo quelle con attivo IS TRUE; stato approvazione
--     prezzo (stato_approvazione_prezzo + pratica_approvazione_prezzo_id)
--     copiato 1:1 / carry-forward (rev2, 2026-06-01) per preservare
--     l'invariante "prezzo fuori-policy sempre marcato".
--   - utility: copia 1:1 (un record per offerta)
--   - timestamp transizione (data_emissione, ...) restano NULL
--
-- Parametri:
--   p_offerta_id : ID dell'offerta da revisionare
--   p_user       : utente che esegue l'operazione (audit)
DECLARE
    v_stato_corrente_cod  config.stati_doc_offerte.codice_interno%TYPE;
    v_stato_bozza_id      config.stati_doc_offerte.id%TYPE;
    v_new_id              vendite.offerte_commerciali.id%TYPE;
BEGIN
    -- Guard: parametro obbligatorio
    IF p_offerta_id IS NULL OR p_offerta_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_crea_revisione_offerta',
            'E_PARAMETRO_INVALIDO',
            jsonb_build_object('param', 'p_offerta_id', 'value', p_offerta_id),
            NULL::uuid,
            'p_offerta_id = ' || COALESCE(p_offerta_id::text, 'NULL')
        );
    END IF;

    -- Recupera stato corrente dell'offerta da revisionare.
    SELECT sdo.codice_interno
      INTO v_stato_corrente_cod
      FROM vendite.offerte_commerciali oc
      JOIN config.stati_doc_offerte sdo ON sdo.id = oc.stato_doc_offerta_id
     WHERE oc.id = p_offerta_id;

    -- Guard: offerta non trovata.
    IF v_stato_corrente_cod IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_crea_revisione_offerta',
            'E_PARAMETRO_INVALIDO',
            jsonb_build_object('offerta_id', p_offerta_id),
            NULL::uuid,
            'offerta non trovata: ' || p_offerta_id::text
        );
    END IF;

    -- Guard: revisione ammessa SOLO da stato EMESSA.
    -- BOZZA si modifica direttamente; ACCETTATA/RIFIUTATA/SUPERATA/ANNULLATA
    -- sono terminali immutabili.
    IF v_stato_corrente_cod <> 'EMESSA' THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_crea_revisione_offerta',
            'E_OFFERTA_REVISIONE_STATO_NON_AMMESSO',
            jsonb_build_object(
                'offerta_id',     p_offerta_id,
                'stato_corrente', v_stato_corrente_cod
            ),
            NULL::uuid,
            p_offerta_id::text,
            v_stato_corrente_cod
        );
    END IF;

    -- Recupera id stato BOZZA (config-driven, no hardcode).
    SELECT id INTO v_stato_bozza_id
      FROM config.stati_doc_offerte
     WHERE codice_interno = 'BOZZA';

    IF v_stato_bozza_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_crea_revisione_offerta',
            'E_CONFIG_MANCANTE',
            jsonb_build_object(
                'tabella', 'config.stati_doc_offerte',
                'codice',  'BOZZA'
            ),
            NULL::uuid,
            'stato BOZZA non trovato in config.stati_doc_offerte'
        );
    END IF;

    -- INSERT testata rev.N+1.
    -- uid: generato da default (uuidv7()) — non incluso nella lista colonne.
    -- codice: generato dal trigger trgfn_offerte_commerciali_gen_codice
    --   (BEFORE INSERT, Step 5) — non incluso; viene posto NULL prima
    --   del trigger, che lo sovrascrive con il prossimo OFC-NNNNNNN.
    -- I timestamp di transizione (data_emissione, data_accettazione,
    --   data_rifiuto, data_annullamento) restano NULL: la rev.N+1 parte
    --   come BOZZA e li acquisisce al momento delle proprie transizioni.
    INSERT INTO vendite.offerte_commerciali (
        emittente_fiscale_id,
        billing_account_id,
        istanza_utility_id,
        utility_id,
        listino_id,
        listino_versione_id,
        valore_variazione_globale,
        tipo_variazione_globale,
        validita_dal,
        validita_al,
        stato_doc_offerta_id,
        revisione_numero,
        revisione_padre_id,
        meta,
        user_insert,
        user_update
    )
    SELECT
        oc.emittente_fiscale_id,
        oc.billing_account_id,
        oc.istanza_utility_id,
        oc.utility_id,
        oc.listino_id,
        oc.listino_versione_id,
        oc.valore_variazione_globale,
        oc.tipo_variazione_globale,
        oc.validita_dal,
        oc.validita_al,
        v_stato_bozza_id,
        oc.revisione_numero + 1,
        p_offerta_id,
        oc.meta,
        COALESCE(p_user, CURRENT_USER),
        COALESCE(p_user, CURRENT_USER)
    FROM vendite.offerte_commerciali oc
    WHERE oc.id = p_offerta_id
    RETURNING id INTO v_new_id;

    -- Il trigger trg_offerte_commerciali_z90_revisione_ins ha gia'
    -- marcato il padre (p_offerta_id) come SUPERATA al momento
    -- dell'INSERT della testata rev.N+1 (AFTER INSERT, Step 6).

    -- Copia eccezioni rev.N -> rev.N+1 (solo righe attive, 1:1).
    -- stato_approvazione_prezzo + pratica_approvazione_prezzo_id:
    --   carry-forward 1:1 (rev2). Vedi header changelog per razionale
    --   (invariante "prezzo fuori-policy sempre marcato").
    -- Nessun remap FK necessario: offerte_commerciali_eccezioni
    -- non ha tabelle figlie che richiedano remapping.
    INSERT INTO vendite.offerte_commerciali_eccezioni (
        offerta_id,
        articolo_id,
        tipo_eccezione,
        tipo_erogazione,
        fonte_quantita_attesa,
        periodicita,
        generazione_canone,
        competenza_canone,
        prezzo_unitario,
        quantita,
        qta_operativa,
        uom_operativa_id,
        factor_to_base,
        ordine,
        attivo,
        meta,
        stato_approvazione_prezzo,
        pratica_approvazione_prezzo_id,
        user_insert,
        user_update
    )
    SELECT
        v_new_id,
        oce.articolo_id,
        oce.tipo_eccezione,
        oce.tipo_erogazione,
        oce.fonte_quantita_attesa,
        oce.periodicita,
        oce.generazione_canone,
        oce.competenza_canone,
        oce.prezzo_unitario,
        oce.quantita,
        oce.qta_operativa,
        oce.uom_operativa_id,
        oce.factor_to_base,
        oce.ordine,
        oce.attivo,
        oce.meta,
        oce.stato_approvazione_prezzo,
        oce.pratica_approvazione_prezzo_id,
        COALESCE(p_user, CURRENT_USER),
        COALESCE(p_user, CURRENT_USER)
    FROM vendite.offerte_commerciali_eccezioni oce
    WHERE oce.offerta_id = p_offerta_id
      AND oce.attivo IS TRUE;

    -- Copia utility rev.N -> rev.N+1 (1:1, un solo record per offerta).
    -- La UNIQUE (offerta_id) su offerte_commerciali_utilities garantisce
    -- che la SELECT ritorni al piu' un record.
    INSERT INTO vendite.offerte_commerciali_utilities (
        offerta_id,
        istanza_utility_id,
        utility_id,
        istanza_dati_precontrattuali_id,
        classe_utenza_id,
        tipo_utenza_id,
        param_1_num,
        param_2_txt,
        meta,
        user_insert,
        user_update
    )
    SELECT
        v_new_id,
        ocu.istanza_utility_id,
        ocu.utility_id,
        ocu.istanza_dati_precontrattuali_id,
        ocu.classe_utenza_id,
        ocu.tipo_utenza_id,
        ocu.param_1_num,
        ocu.param_2_txt,
        ocu.meta,
        COALESCE(p_user, CURRENT_USER),
        COALESCE(p_user, CURRENT_USER)
    FROM vendite.offerte_commerciali_utilities ocu
    WHERE ocu.offerta_id = p_offerta_id;

    RETURN v_new_id;
END;
$function$

COMMENT ON FUNCTION vendite.fn_crea_revisione_offerta(p_offerta_id bigint, p_user text)
IS 'Crea rev.N+1 di un''offerta EMESSA: copia testata + eccezioni attive + utility (1:1). Rev2 (2026-06-01): carry-forward 1:1 di stato_approvazione_prezzo + pratica_approvazione_prezzo_id sulle eccezioni (preserva l''invariante "prezzo fuori-policy sempre marcato"). uid e codice OFC-* generati ex novo. Il trigger z90 revisione (Step 6) marca automaticamente il padre SUPERATA. Guard: stato EMESSA obbligatorio. Parametri: p_offerta_id, p_user.';
```

---
{% include-markdown "signature-core.md" %}
