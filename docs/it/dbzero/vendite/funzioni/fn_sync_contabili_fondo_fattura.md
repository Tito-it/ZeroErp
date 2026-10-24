{% include-markdown "it/dbzero/vendite/manual/fn_sync_contabili_fondo_fattura.md" %}
# ⚙️ Funzione `fn_sync_contabili_fondo_fattura`

```sql
CREATE FUNCTION fn_sync_contabili_fondo_fattura(p_fattura_figlia_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_sync_contabili_fondo_fattura(p_fattura_figlia_id bigint)
 RETURNS TABLE(inserted_righe integer, updated_righe integer, annullati_source integer)
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_centro_fondo_id  pagamenti.centri_riscossione.id%TYPE;
    v_stato_contabile_codice pagamenti.vendite_contabili_stati.codice_interno%TYPE := 'VALIDATA';
    v_stato_riga_id    pagamenti.vendite_contabili_righe_stati.id%TYPE;
    v_inserted INTEGER := 0;
    v_updated  INTEGER := 0;
    v_annullati INTEGER := 0;
    v_riga_id      pagamenti.vendite_contabili_righe.id%TYPE;
    v_riga_stato_id   pagamenti.vendite_contabili_righe_stati.id%TYPE;
    v_riga_stato      pagamenti.vendite_contabili_righe_stati.codice_interno%TYPE;
    v_contabile_id pagamenti.vendite_contabili.id%TYPE;
    v_lotto_id     vendite.fatturazione_lotti.id%TYPE;
    v_data_valuta  pagamenti.vendite_contabili_righe.data_valuta%TYPE;
    v_saldo_effettivo vendite.fatture.totale_a_pagare%TYPE;
    r RECORD;
BEGIN
    IF p_fattura_figlia_id IS NULL OR p_fattura_figlia_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_sync_contabili_fondo_fattura', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_fattura_figlia_id', 'valore', p_fattura_figlia_id), NULL::uuid, 'p_fattura_figlia_id obbligatorio e > 0');
    END IF;

    -- Centro riscossione fondo fattura
    SELECT c.id INTO v_centro_fondo_id FROM pagamenti.centri_riscossione c WHERE c.attivo IS TRUE AND c.is_fondo_fattura IS TRUE ORDER BY c.id LIMIT 1;

    IF v_centro_fondo_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_sync_contabili_fondo_fattura', 'E_CONFIG_MANCANTE',
            jsonb_build_object('config', 'centri_riscossione.is_fondo_fattura'), NULL::uuid, 'il centro di riscossione dei fondi fattura');
    END IF;

    -- =========================================================
    -- Stato riga contabile target: ABBINATA, e SOLO quello.
    --
    -- 🔴 C-6: fino al 2026-08-21 qui c'era un ripiego su «uno
    --    stato qualunque» (ORDER BY s.id LIMIT 1). Era gia'
    --    sbagliato, ed e' PEGGIORATO col lotto 2: una riga
    --    ripiegata su IMPORTATA ha richiede_abbinamento = false,
    --    quindi sfuggirebbe anche al guard nuovo e resterebbe
    --    non registrabile per sempre, in silenzio.
    --    Uno stato mancante e' una configurazione rotta: si dice.
    -- =========================================================
    SELECT s.id INTO v_stato_riga_id FROM pagamenti.vendite_contabili_righe_stati s WHERE s.attivo IS TRUE AND s.codice_interno = 'ABBINATA' LIMIT 1;
    IF v_stato_riga_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_sync_contabili_fondo_fattura', 'E_CONFIG_MANCANTE',
            jsonb_build_object('config', 'vendite_contabili_righe_stati.ABBINATA'), NULL::uuid, 'lo stato ABBINATA delle righe contabili');
    END IF;

    -- Lotto associato
    SELECT lf.lotto_id INTO v_lotto_id FROM vendite.fatturazione_lotti_fatture lf WHERE lf.fattura_id = p_fattura_figlia_id ORDER BY lf.id DESC LIMIT 1;

    -- Loop fondi assegnati
    -- ⭐ Il filtro su ASSEGNATO e' cio' che, dal 2026-08-21, tiene
    --    fuori i fondi ESEGUITI: il quarto stato li porta via da
    --    qui senza che questa WHERE cambi.
    FOR r IN
        SELECT s.id AS source_id, s.fattura_sorgente_id, s.importo, s.billing_account_id, fsrc.data AS data_fattura_sorgente
          FROM vendite.fatture_fondi_fattura_source s
          JOIN vendite.tipi_fondi_fattura t ON t.id = s.tipo_fondo_fattura_id
          JOIN vendite.fatture fsrc ON fsrc.id = s.fattura_sorgente_id
         WHERE s.fattura_figlia_id = p_fattura_figlia_id AND s.attivo IS TRUE AND s.stato = 'ASSEGNATO' AND t.codice_interno = 'F_F_ADD_ACC'
         ORDER BY s.id
    LOOP
        -- =====================================================
        -- La riga contabile di QUESTO atto, letta dalla COLONNA
        -- (S1-14) e non piu' da una stringa dentro il meta.
        --
        -- ⚠️ Si cerca PRIMA di calcolare il saldo, ed e' parte
        --    del rimedio: con l'ordine vecchio un fondo con riga
        --    registrata e saldo zero passava per il ramo di
        --    annullamento (C-3) prima che la rete lo vedesse.
        --
        -- ORDER BY id DESC: per invariante c'e' una riga sola
        -- per atto, ma se ce ne fossero due vale la piu' recente.
        -- =====================================================
        SELECT cr.id, cr.stato_id, st.codice_interno
          INTO v_riga_id, v_riga_stato_id, v_riga_stato
          FROM pagamenti.vendite_contabili_righe cr
          JOIN pagamenti.vendite_contabili_righe_stati st ON st.id = cr.stato_id
         WHERE cr.attivo IS TRUE
           AND cr.fondo_source_id = r.source_id
         ORDER BY cr.id DESC
         LIMIT 1;

        -- =====================================================
        -- 🛟 S1-8 — LA RETE. Non e' il rimedio (quello e' il
        --    quarto stato del fondo): e' il fail-closed
        --    sull'invariante «un fondo ASSEGNATO non ha righe
        --    che non possono tornare ad ABBINATA».
        --
        -- ⭐ La domanda si fa alla MATRICE, non a un elenco di
        --    stati scritto qui: copre POSTATA (terminale) e
        --    anche SCARTATA, da cui non esiste passaggio verso
        --    ABBINATA — e che oggi farebbe cadere il ricalcolo
        --    della fattura con un errore che accusa il ricalcolo.
        --
        -- ⛔ Si LOGGA e si salta: mai un RAISE, questa funzione
        --    e' su percorso vivo della pipeline.
        -- =====================================================
        IF v_riga_id IS NOT NULL
           AND v_riga_stato_id IS DISTINCT FROM v_stato_riga_id
           AND NOT EXISTS (
               SELECT 1
                 FROM pagamenti.transizioni_stati_contabile_riga t
                WHERE t.stato_da_id = v_riga_stato_id
                  AND t.stato_a_id  = v_stato_riga_id
                  AND t.attivo IS TRUE)
        THEN
            INSERT INTO vendite.fatture_log (fattura_id, data_ora, messaggio, status, disabilitato, meta, data_insert, user_insert, data_update, user_update)
            VALUES (
                p_fattura_figlia_id,
                now(),
                format('Fondo non sincronizzato: la riga contabile e'' in stato %s e da li'' non si torna ad ABBINATA', v_riga_stato),
                'W',
                FALSE,
                jsonb_build_object(
                    'source_id',         r.source_id,
                    'contabile_riga_id', v_riga_id,
                    'stato_riga',        v_riga_stato,
                    'error_code',        'W_FONDO_RIGA_CONTABILE_NON_AGGIORNABILE',
                    'cause',             'RIGA_NON_RIPORTABILE_AD_ABBINATA'),
                now(), current_user, now(), current_user);
            CONTINUE;
        END IF;

        -- Formula unica (changeSet 20260815-05): il residuo della
        -- sorgente al netto del contributo di QUESTO fondo.
        v_saldo_effettivo := vendite.fn_saldo_sorgente_fondo(r.fattura_sorgente_id, r.source_id);

        IF COALESCE(v_saldo_effettivo, 0) = 0 THEN
            -- ⭐ La ragione dell'annullamento sta ora SUL DATO, non
            --    solo nel comportamento: chi guarda la riga sa
            --    perche' e' finita li'.
            UPDATE vendite.fatture_fondi_fattura_source s
               SET stato = 'ANNULLATO',
                   motivo = COALESCE(s.motivo, 'Sorgente gia coperta: saldo effettivo zero alla sincronizzazione contabile'),
                   data_update = now(), user_update = current_user
             WHERE s.id = r.source_id AND s.stato IS DISTINCT FROM 'ANNULLATO';
            IF FOUND THEN v_annullati := v_annullati + 1; END IF;
            CONTINUE;
        END IF;

        v_data_valuta := CASE WHEN script.fn_data_operativa() > r.data_fattura_sorgente THEN script.fn_data_operativa() ELSE r.data_fattura_sorgente END;

        v_contabile_id := pagamenti.fn_get_or_create_vendite_contabile(
            p_centro_riscossione_id => v_centro_fondo_id, p_data_contabile => r.data_fattura_sorgente,
            p_data_registrazione => r.data_fattura_sorgente, p_ente_incasso_id => NULL, p_lotto_id => v_lotto_id,
            p_codice_stato_interno => v_stato_contabile_codice,
            p_meta => jsonb_build_object('origine', 'FONDO_FATTURA', 'fattura_figlia_id', p_fattura_figlia_id));

        IF v_riga_id IS NULL THEN
            INSERT INTO pagamenti.vendite_contabili_righe (contabile_id, riferimento_ente, data_pagamento, data_valuta, data_operazione, importo, fattura_id, billing_account_id, stato_id, motivo_sospeso, fondo_source_id, meta, attivo, data_insert, user_insert, data_update, user_update)
            VALUES (v_contabile_id, concat('FONDO_SRC_', r.source_id::TEXT), r.data_fattura_sorgente, v_data_valuta, now(), r.importo, r.fattura_sorgente_id, r.billing_account_id, v_stato_riga_id, NULL, r.source_id, jsonb_build_object('origine', 'FONDO_FATTURA', 'fattura_figlia_id', p_fattura_figlia_id), TRUE, now(), current_user, now(), current_user);
            v_inserted := v_inserted + 1;
        ELSE
            -- ⚠️ `- 'fondo_source_id'` toglie la chiave storica dal
            --    meta: il legame ha una colonna, e due sorgenti di
            --    verita' sulla stessa cosa sono il difetto che
            --    S1-14 chiude.
            UPDATE pagamenti.vendite_contabili_righe cr SET contabile_id = v_contabile_id, riferimento_ente = concat('FONDO_SRC_', r.source_id::TEXT), data_pagamento = r.data_fattura_sorgente, data_valuta = v_data_valuta, data_operazione = r.data_fattura_sorgente, importo = r.importo, fattura_id = r.fattura_sorgente_id, billing_account_id = r.billing_account_id, stato_id = v_stato_riga_id, motivo_sospeso = NULL, fondo_source_id = r.source_id, meta = (COALESCE(cr.meta, '{}'::JSONB) - 'fondo_source_id') || jsonb_build_object('origine', 'FONDO_FATTURA', 'fattura_figlia_id', p_fattura_figlia_id), data_update = now(), user_update = current_user WHERE cr.id = v_riga_id;
            v_updated := v_updated + 1;
        END IF;
    END LOOP;

    RETURN QUERY SELECT v_inserted, v_updated, v_annullati;
END;
$function$

COMMENT ON FUNCTION vendite.fn_sync_contabili_fondo_fattura(p_fattura_figlia_id bigint)
IS 'Sync righe contabili dei fondi fattura assegnati. Annulla le source a saldo effettivo zero e ne SCRIVE LA RAGIONE nella colonna `motivo`. Il saldo effettivo si legge da vendite.fn_saldo_sorgente_fondo: la stessa formula serve al guard di capienza di fn_applica_fondi_fattura, e due copie della regola che decide se un fondo e'' ancora dovuto darebbero prima o poi due risposte diverse. ⭐ rev 2026-08-21 (cantiere incassi, lotto 3), tre modifiche. (1) S1-14: il legame con l''atto si legge e si scrive sulla COLONNA pagamenti.vendite_contabili_righe.fondo_source_id, non piu'' su meta->>''fondo_source_id'', che nell''UPDATE viene tolta dal meta — `meta->>''origine''` resta perche'' risponde a un''altra domanda. (2) S1-8, la RETE: se un fondo ASSEGNATO ha una riga contabile dalla quale la matrice non ammette il ritorno ad ABBINATA, la riga NON si aggiorna — si salta e si logga W_FONDO_RIGA_CONTABILE_NON_AGGIORNABILE su vendite.fatture_log. ⛔ Si logga e non si solleva: questa funzione e'' chiamata incondizionatamente da fn_ricalcola_totali_fattura, cioe'' sta sul percorso vivo della pipeline, e un W_ sollevato sarebbe un HTTP 500. ⭐ La domanda si fa alla matrice e non a un elenco scritto dentro il guard, quindi copre anche una riga SCARTATA, da cui non esiste passaggio verso ABBINATA. ⚠️ Non e'' piu'' il rimedio di C-2/C-3: quelli li chiude il quarto stato del fondo (ESEGUITO), che porta l''atto fuori dal filtro ASSEGNATO di questo ciclo. Questa e'' la rete sull''invariante. (3) tipi ancorati con %TYPE anche in FIRMA e nei due DECLARE che ancora non lo usavano (le tre colonne del RETURNS TABLE restano integer: sono contatori, non il riflesso di una colonna). (4) C-6: spento il fallback fail-open sul lookup dello stato ABBINATA — ripiegare su «uno stato qualunque» dopo il lotto 2 significava atterrare su IMPORTATA, che ha richiede_abbinamento = false e quindi sfugge anche al guard nuovo. ⚠️ Le righe contabili che crea sono ABBINATA, cioe'' POSTABILI: il giorno del posting diventeranno movimenti veri, ed e'' corretto (la sorgente e'' saldata per TRASFERIMENTO), ma ogni misura di «incassato» deve escludere i centri non-cassa. Coda del D-3 di brief-db-fondo-fattura-ricalcolo-e-governo §8.2.';
```

</div>

---
{% include-markdown "signature-core.md" %}
