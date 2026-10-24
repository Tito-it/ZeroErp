{% include-markdown "it/dbzero/vendite/manual/fn_crea_revisione_offerta.md" %}
# ⚙️ Funzione `fn_crea_revisione_offerta`

```sql
CREATE FUNCTION fn_crea_revisione_offerta(p_offerta_id bigint, p_user text)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_crea_revisione_offerta(p_offerta_id bigint, p_user text)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
-- rev 2026-10-24 (20261024-18, brief-modello-documento-vendita N-1/P-2):
--   lo stato iniziale non si scrive piu' qui: lo mette il trigger della
--   nascita (script.trgfn_doc_stato_iniziale), letto dal vocabolario.
-- Scopo:
--   Creare una nuova revisione (rev.N+1) in stato BOZZA a partire
--   da un'offerta in stato EMESSA. Copia testata, eccezioni attive
--   coi loro componenti, e utility (1:1). Il trigger z90 revisione (Step 6) marca
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
--   - componenti delle eccezioni copiate: TUTTI (anche gli opzionali
--     spenti, che sono una scelta), rimappati sull'eccezione nuova;
--     stato e pratica di approvazione 1:1 come sulle eccezioni
--     (rev 2026-10-05: prima non si copiavano)
--   - utility: copia 1:1 (un record per offerta)
--   - indirizzi: copia 1:1 di tutti gli slot, come la revisione del
--     preventivo (rev 2026-10-11, D-4 di Tid)
--   - timestamp transizione (data_emissione, ...) restano NULL
--   - listino_versione_id NULL: la revisione congela alla sua emissione
--     (rev 2026-10-07, A-D3, brief-db-offerta-emissione-ed-erogazione)
--
-- Parametri:
--   p_offerta_id : ID dell'offerta da revisionare
--   p_user       : utente che esegue l'operazione (audit)
DECLARE
    v_stato_corrente_cod  config.stati_doc_offerte.codice_interno%TYPE;
    v_new_id              vendite.offerte_commerciali.id%TYPE;
    v_ecc                 vendite.offerte_commerciali_eccezioni%ROWTYPE;
    v_new_ecc_id          vendite.offerte_commerciali_eccezioni.id%TYPE;
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

    -- Guard (rev 2026-09-24): nessuna revisione con un prezzo IN ATTESA.
    --   Le eccezioni si ricopiano con stato e pratica di approvazione (sotto):
    --   una in attesa resterebbe legata alla pratica della rev N, e sulla
    --   rev N+1 l'attesa non finirebbe piu'. Decisione di Tid del 2026-09-24:
    --   prima l'esito, poi la revisione.
    -- ⭐ Il predicato e' script.fn_check_prezzi_in_attesa, lo STESSO con cui
    --   fn_available_actions_offerta spegne «Crea revisione». Approvato e
    --   rifiutato NON bloccano: si ricopiano.
    PERFORM script.fn_raise_primo_motivo_se_presente(
        'vendite', 'fn_crea_revisione_offerta',
        script.fn_check_prezzi_in_attesa('vendite.offerte_commerciali'::regclass, p_offerta_id),
        NULL,
        NULL::uuid,
        jsonb_build_object('offerta_id', p_offerta_id));

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
        -- ⭐ rev 2026-10-07 (decisione A-D3 di Tid): la revisione NON
        -- eredita la versione congelata del padre. E' una proposta nuova,
        -- mandata in un giorno nuovo: vive sulla versione in vigore e la
        -- congela alla SUA emissione. Con la copia, una revisione su una
        -- versione nel frattempo chiusa non si emetteva piu'.
        NULL,
        oc.valore_variazione_globale,
        oc.tipo_variazione_globale,
        oc.validita_dal,
        oc.validita_al,
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

    -- Copia eccezioni rev.N -> rev.N+1 (solo righe attive, 1:1), e per
    -- ciascuna i suoi componenti, rimappati sull'eccezione nuova.
    -- stato_approvazione_prezzo + pratica_approvazione_prezzo_id:
    --   carry-forward 1:1 (rev2), sulle eccezioni e sui componenti.
    --   Vedi header changelog per razionale (invariante "prezzo
    --   fuori-policy sempre marcato").
    -- ⭐ rev 2026-10-05 (brief-db-righe-esclusione-solo-non-si-vende
    --   §8.2 B1): fino a oggi questo blocco diceva «nessun remap
    --   necessario: le eccezioni non hanno tabelle figlie», e non era
    --   vero — offerte_commerciali_eccezioni_componenti e' la figlia.
    --   Una revisione di un'offerta con un bundle nasceva senza
    --   componenti, e il push la portava cosi' nel contratto.
    -- Una riga alla volta, con RETURNING, come fn_push_offerta_a_contratto:
    --   la corrispondenza vecchia -> nuova e' quella dell'INSERT, non un
    --   ordine di assegnazione degli id dato per scontato.
    -- I componenti si copiano TUTTI, attivi e no: un opzionale spento e'
    --   una scelta dell'offerta, e la revisione e' la stessa offerta
    --   (stessa regola del push). I trigger del componente lavorano come
    --   alla nascita: m50 ricalcola la quantita' dalla madre, z90 il
    --   prezzo della madre dai componenti ATTIVI — cioe' lo stesso
    --   prezzo della rev N, che lo stesso trigger aveva calcolato.
    FOR v_ecc IN
        SELECT oce.*
          FROM vendite.offerte_commerciali_eccezioni oce
         WHERE oce.offerta_id = p_offerta_id
           AND oce.attivo IS TRUE
         ORDER BY oce.id
    LOOP
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
        VALUES (
            v_new_id,
            v_ecc.articolo_id,
            v_ecc.tipo_eccezione,
            v_ecc.tipo_erogazione,
            v_ecc.fonte_quantita_attesa,
            v_ecc.periodicita,
            v_ecc.generazione_canone,
            v_ecc.competenza_canone,
            v_ecc.prezzo_unitario,
            v_ecc.quantita,
            v_ecc.qta_operativa,
            v_ecc.uom_operativa_id,
            v_ecc.factor_to_base,
            v_ecc.ordine,
            v_ecc.attivo,
            v_ecc.meta,
            v_ecc.stato_approvazione_prezzo,
            v_ecc.pratica_approvazione_prezzo_id,
            COALESCE(p_user, CURRENT_USER),
            COALESCE(p_user, CURRENT_USER)
        )
        RETURNING id INTO v_new_ecc_id;

        -- Un componente SPENTO in attesa si copia SENZA marca e senza pratica
        -- (D-3 di Tid, 2026-10-08, brief-db-righe-e-componenti-debiti-residui
        -- §3): la pratica e' della rev N, e sulla rev N+1 non si esiterebbe
        -- mai. Un attivo in attesa qui non arriva (guard di testa). Approvato e
        -- rifiutato si copiano 1:1. ⚠️ La richiesta nuova alla riaccensione e'
        -- dell'L3 dei componenti, che non esiste ancora: debito dichiarato.
        INSERT INTO vendite.offerte_commerciali_eccezioni_componenti (
            eccezione_offerta_id,
            articolo_componente_id,
            componente_id,
            coeff_qta_snapshot,
            quantita,
            uom_operativa_id,
            factor_to_base,
            qta_operativa,
            prezzo_unitario,
            iva_id,
            origine_prezzo,
            prezzo_resolver_context,
            stato_approvazione_prezzo,
            pratica_approvazione_prezzo_id,
            meta,
            ordine,
            attivo,
            user_insert,
            user_update
        )
        SELECT
            v_new_ecc_id,
            occ.articolo_componente_id,
            occ.componente_id,
            occ.coeff_qta_snapshot,
            occ.quantita,
            occ.uom_operativa_id,
            occ.factor_to_base,
            occ.qta_operativa,
            occ.prezzo_unitario,
            occ.iva_id,
            occ.origine_prezzo,
            occ.prezzo_resolver_context,
            CASE WHEN occ.attivo IS NOT TRUE AND occ.stato_approvazione_prezzo = 'PENDING'
                 THEN NULL ELSE occ.stato_approvazione_prezzo END,
            CASE WHEN occ.attivo IS NOT TRUE AND occ.stato_approvazione_prezzo = 'PENDING'
                 THEN NULL ELSE occ.pratica_approvazione_prezzo_id END,
            occ.meta,
            occ.ordine,
            occ.attivo,
            COALESCE(p_user, CURRENT_USER),
            COALESCE(p_user, CURRENT_USER)
        FROM vendite.offerte_commerciali_eccezioni_componenti occ
        WHERE occ.eccezione_offerta_id = v_ecc.id
        ORDER BY occ.id;
    END LOOP;

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

    -- Copia indirizzi rev.N -> rev.N+1 (rev 2026-10-11, D-4 di Tid,
    -- brief-db-indirizzi-documento-seguono-il-cliente). La revisione e' lo
    -- stesso documento: senza, nasceva senza indirizzi e perdeva Fatturazione,
    -- Fornitura e Residenza scelte sulla rev.N. Stessa forma della gemella
    -- vendite.fn_crea_revisione_preventivo: tutti gli slot, snapshot e
    -- origini 1:1. La testata ha lo stesso cliente (BA, istanza copiati),
    -- quindi il guard d'origine li trova del cliente; la rev.N+1 e' in BOZZA
    -- e il lock dei satelliti lascia scrivere.
    INSERT INTO vendite.offerte_commerciali_indirizzi (
        offerta_id, tipo_indirizzo_id, snapshot,
        origine_indirizzo_id, origine_soggetto_ruolo_id,
        user_insert, user_update
    )
    SELECT
        v_new_id, oi.tipo_indirizzo_id, oi.snapshot,
        oi.origine_indirizzo_id, oi.origine_soggetto_ruolo_id,
        COALESCE(p_user, CURRENT_USER), COALESCE(p_user, CURRENT_USER)
    FROM vendite.offerte_commerciali_indirizzi oi
    WHERE oi.offerta_id = p_offerta_id;

    RETURN v_new_id;
END;
$function$

COMMENT ON FUNCTION vendite.fn_crea_revisione_offerta(p_offerta_id bigint, p_user text)
IS 'Crea rev.N+1 di un''offerta EMESSA: copia testata + eccezioni attive coi loro componenti + utility (1:1). Rev2 (2026-06-01): carry-forward 1:1 di stato_approvazione_prezzo + pratica_approvazione_prezzo_id sulle eccezioni (preserva l''invariante "prezzo fuori-policy sempre marcato"). uid e codice OFC-* generati ex novo. Il trigger z90 revisione (Step 6) marca automaticamente il padre SUPERATA. Guard: stato EMESSA obbligatorio. Parametri: p_offerta_id, p_user. rev 2026-09-24 (20260924-35, decisione di Tid): nessuna revisione con un prezzo IN ATTESA — guard sul primo motivo di script.fn_check_prezzi_in_attesa (eccezioni e loro componenti attivi PENDING), lo stesso con cui la capability spegne «Crea revisione»: un''eccezione in attesa ricopiata restava legata alla pratica della rev N. Approvato e rifiutato continuano a ricopiarsi. Firma e RETURNS ancorati con %TYPE, SECURITY INVOKER esplicito. Brief: brief-db-preventivi-congelamento-pricing §10. rev 2026-10-05 (20261005-19, decisione di Tid): la revisione copia anche i COMPONENTI delle eccezioni copiate (vendite.offerte_commerciali_eccezioni_componenti), tutti, rimappati sull''eccezione nuova riga per riga con RETURNING, con stato e pratica di approvazione 1:1. Prima una revisione di un''offerta con un bundle nasceva senza componenti e il push la portava cosi'' nel contratto. Brief: brief-db-righe-esclusione-solo-non-si-vende §8.2 B1. rev 2026-10-07 (brief-db-offerta-emissione-ed-erogazione §C.1.1, decisione A-D3 di Tid): la revisione nasce con listino_versione_id NULL e congela la versione alla sua emissione (trgfn_offerte_commerciali_guard_transizione). Prima ricopiava la versione congelata del padre, e una revisione su una versione nel frattempo chiusa non si emetteva più. Il listino e la variazione globale si ricopiano come prima. rev 2026-10-08 (20261008-88, brief-db-righe-e-componenti-debiti-residui §3, D-3 di Tid): un componente SPENTO in PENDING di un''eccezione copiata si copia con stato_approvazione_prezzo e pratica_approvazione_prezzo_id a NULL. La pratica e'' della rev N e sulla rev N+1 non si esiterebbe mai; un attivo in attesa continua a fermare la revisione, approvato e rifiutato si copiano 1:1. La richiesta nuova alla riaccensione e'' dell''L3 dei componenti, che non esiste ancora (debito dichiarato). Gemella: fn_crea_revisione_preventivo (20261008-87). rev 2026-10-11 (brief-db-indirizzi-documento-seguono-il-cliente, D-4 di Tid): la revisione copia anche gli INDIRIZZI (vendite.offerte_commerciali_indirizzi), tutti gli slot con snapshot e origini 1:1, come fn_crea_revisione_preventivo. Prima la rev.N+1 nasceva senza indirizzi. Stesso cliente sulla testata: il guard d''origine li trova del cliente.';
```

</div>

---
{% include-markdown "signature-core.md" %}
