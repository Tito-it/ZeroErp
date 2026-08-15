{% include-markdown "it/dbzero/vendite/manual/fn_sync_contabili_fondo_fattura.md" %}
# ⚙️ Funzione `fn_sync_contabili_fondo_fattura`

```sql
CREATE FUNCTION fn_sync_contabili_fondo_fattura(p_fattura_figlia_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_sync_contabili_fondo_fattura(p_fattura_figlia_id bigint)
 RETURNS TABLE(inserted_righe integer, updated_righe integer, annullati_source integer)
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_centro_fondo_id  pagamenti.centri_riscossione.id%TYPE;
    v_stato_contabile_codice TEXT := 'VALIDATA';
    v_stato_riga_id    pagamenti.vendite_contabili_righe_stati.id%TYPE;
    v_inserted INTEGER := 0;
    v_updated  INTEGER := 0;
    v_annullati INTEGER := 0;
    v_riga_id      pagamenti.vendite_contabili_righe.id%TYPE;
    v_contabile_id pagamenti.vendite_contabili.id%TYPE;
    v_lotto_id     vendite.fatturazione_lotti.id%TYPE;
    v_data_valuta  pagamenti.vendite_contabili_righe.data_valuta%TYPE;
    v_saldo_effettivo NUMERIC;
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
            jsonb_build_object('config', 'centri_riscossione.is_fondo_fattura'), NULL::uuid, 'centro riscossione fondo fattura non configurato');
    END IF;

    -- Stato riga contabile target
    SELECT s.id INTO v_stato_riga_id FROM pagamenti.vendite_contabili_righe_stati s WHERE s.attivo IS TRUE AND s.codice_interno = 'ABBINATA' LIMIT 1;
    IF v_stato_riga_id IS NULL THEN
        SELECT s.id INTO v_stato_riga_id FROM pagamenti.vendite_contabili_righe_stati s WHERE s.attivo IS TRUE ORDER BY s.id LIMIT 1;
    END IF;
    IF v_stato_riga_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_sync_contabili_fondo_fattura', 'E_CONFIG_MANCANTE',
            jsonb_build_object('config', 'vendite_contabili_righe_stati'), NULL::uuid, 'stato riga contabile non configurato');
    END IF;

    -- Lotto associato
    SELECT lf.lotto_id INTO v_lotto_id FROM vendite.fatturazione_lotti_fatture lf WHERE lf.fattura_id = p_fattura_figlia_id ORDER BY lf.id DESC LIMIT 1;

    -- Loop fondi assegnati
    FOR r IN
        SELECT s.id AS source_id, s.fattura_sorgente_id, s.importo, s.billing_account_id, fsrc.data AS data_fattura_sorgente
          FROM vendite.fatture_fondi_fattura_source s
          JOIN vendite.tipi_fondi_fattura t ON t.id = s.tipo_fondo_fattura_id
          JOIN vendite.fatture fsrc ON fsrc.id = s.fattura_sorgente_id
         WHERE s.fattura_figlia_id = p_fattura_figlia_id AND s.attivo IS TRUE AND s.stato = 'ASSEGNATO' AND t.codice_interno = 'F_F_ADD_ACC'
         ORDER BY s.id
    LOOP
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

        v_data_valuta := CASE WHEN current_date > r.data_fattura_sorgente THEN current_date ELSE r.data_fattura_sorgente END;

        v_contabile_id := pagamenti.fn_get_or_create_vendite_contabile(
            p_centro_riscossione_id => v_centro_fondo_id, p_data_contabile => r.data_fattura_sorgente,
            p_data_registrazione => r.data_fattura_sorgente, p_ente_incasso_id => NULL, p_lotto_id => v_lotto_id,
            p_codice_stato_interno => v_stato_contabile_codice,
            p_meta => jsonb_build_object('origine', 'FONDO_FATTURA', 'fattura_figlia_id', p_fattura_figlia_id));

        SELECT cr.id INTO v_riga_id FROM pagamenti.vendite_contabili_righe cr
         WHERE cr.attivo IS TRUE AND COALESCE(cr.meta->>'origine', '') = 'FONDO_FATTURA' AND COALESCE(cr.meta->>'fondo_source_id', '') = r.source_id::TEXT ORDER BY cr.id DESC LIMIT 1;

        IF v_riga_id IS NULL THEN
            INSERT INTO pagamenti.vendite_contabili_righe (contabile_id, riferimento_ente, data_pagamento, data_valuta, data_operazione, importo, fattura_id, billing_account_id, stato_id, motivo_sospeso, meta, attivo, data_insert, user_insert, data_update, user_update)
            VALUES (v_contabile_id, concat('FONDO_SRC_', r.source_id::TEXT), r.data_fattura_sorgente, v_data_valuta, now(), r.importo, r.fattura_sorgente_id, r.billing_account_id, v_stato_riga_id, NULL, jsonb_build_object('origine', 'FONDO_FATTURA', 'fondo_source_id', r.source_id, 'fattura_figlia_id', p_fattura_figlia_id), TRUE, now(), current_user, now(), current_user);
            v_inserted := v_inserted + 1;
        ELSE
            UPDATE pagamenti.vendite_contabili_righe cr SET contabile_id = v_contabile_id, riferimento_ente = concat('FONDO_SRC_', r.source_id::TEXT), data_pagamento = r.data_fattura_sorgente, data_valuta = v_data_valuta, data_operazione = r.data_fattura_sorgente, importo = r.importo, fattura_id = r.fattura_sorgente_id, billing_account_id = r.billing_account_id, stato_id = v_stato_riga_id, motivo_sospeso = NULL, meta = COALESCE(cr.meta, '{}'::JSONB) || jsonb_build_object('origine', 'FONDO_FATTURA', 'fondo_source_id', r.source_id, 'fattura_figlia_id', p_fattura_figlia_id), data_update = now(), user_update = current_user WHERE cr.id = v_riga_id;
            v_updated := v_updated + 1;
        END IF;
    END LOOP;

    RETURN QUERY SELECT v_inserted, v_updated, v_annullati;
END;
$function$

COMMENT ON FUNCTION vendite.fn_sync_contabili_fondo_fattura(p_fattura_figlia_id bigint)
IS 'Sync righe contabili dei fondi fattura assegnati. Annulla le source a saldo effettivo zero, e dal 2026-08-15 ne SCRIVE LA RAGIONE nella colonna `motivo` invece di lasciarla implicita nel comportamento. Il saldo effettivo si legge da vendite.fn_saldo_sorgente_fondo: la stessa formula serve al guard di capienza di fn_applica_fondi_fattura, e due copie della regola che decide se un fondo e'' ancora dovuto darebbero prima o poi due risposte diverse alla stessa domanda. ⚠️ L''ANNULLATO automatico resta, ed e'' una scelta: e'' della stessa specie di quello rimosso da fn_genera_fondi_fattura_source, ma opera su fondi GIA'' ASSEGNATI — il denaro si e'' gia'' mosso, e toglierlo senza il processo rimborsi di `pagamenti` lascerebbe scoperto il doppio conteggio. ⚠️ Le righe contabili che crea sono ABBINATA, cioe'' POSTABILI: il giorno del posting diventeranno movimenti veri, ed e'' corretto (la sorgente e'' saldata per TRASFERIMENTO), ma ogni misura di «incassato» deve escludere i centri non-cassa. Coda del D-3 di brief-db-fondo-fattura-ricalcolo-e-governo §8.2.';
```

---
{% include-markdown "signature-core.md" %}
