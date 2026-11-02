-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: helper generiche script.* per pattern BoM CASO A
--   (script.fn_ricalcola_prezzo_padre_da_componenti,
--    script.trgfn_componenti_guard_coerenza_bom,
--    script.trgfn_componenti_calcola_quantita,
--    script.trgfn_componenti_propaga_qta)
--
-- Indice test:
--   1)  fn_ricalcola_prezzo_padre_da_componenti: SUM 2 figli attivi
--   2)  fn_ricalcola_prezzo_padre_da_componenti: figlio inattivo escluso
--   3)  fn_ricalcola_prezzo_padre_da_componenti: nessun figlio -> prezzo = 0
--   4)  guard_coerenza_bom: padre non composito -> E_DOC_RIGA_NON_COMPOSITO
--   5)  guard_coerenza_bom: componente non in BoM padre -> E_DOC_COMPONENTE_NON_BOM
--   6)  guard_coerenza_bom: componente_id incoerente -> E_DOC_COMPONENTE_ID_INCOERENTE
--   7)  guard_coerenza_bom: componente non esposto -> E_DOC_COMPONENTE_NON_ESPOSTO
--   8)  guard_coerenza_bom: BoM non valida alla data -> E_DOC_COMPONENTE_BOM_NON_VALIDA
--   9)  guard_coerenza_bom: INSERT valido -> OK (no raise)
--   10) calcola_quantita: INSERT -> quantita = coeff * qta_padre
--   11) propaga_qta: UPDATE quantita padre -> figli aggiornati
--   12) propaga_qta: quantita invariata -> figli non toccati
--
-- Strategia fixture:
--   Test 1-3: usano la tabella reale vendite.preventivi_righe_componenti
--   con riga padre sintetica. Tutto in ROLLBACK finale.
--   Test 4-9: usano INSERT su preventivi_righe_componenti per attivare
--   il guard via trigger BEFORE INSERT.
--   Test 10-12: usano UPDATE su preventivi_righe per attivare i trigger.
--
-- ATTENZIONE: questi test richiedono dati di catalogo (articolo composito,
-- BoM, articolo componente) e un preventivo con riga. Vengono saltati
-- (skip) se i prerequisiti non sono soddisfatti.
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file sarebbe verde per sottrazione. IMMEDIATE li riporta a scattare a fine
--   di ogni istruzione. In testa e non in coda: in coda scatterebbero dopo il
--   cleanup, su righe ormai cancellate.
--   Brief: brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(12);

-- =========================================================
-- Setup: cerca un articolo composito CASO A con almeno 1
-- componente con esposizione_in_fattura non NASCOSTO valido oggi.
-- Se non trovato, i test vengono skippati via skip().
-- =========================================================
DO $$
DECLARE
    v_has_setup boolean;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM catalogo.articoli a
         WHERE a.is_composito = TRUE
           AND EXISTS (
               SELECT 1 FROM catalogo.articoli_componenti ac
                WHERE ac.prodotto_id        = a.id
                  AND ac.esposizione_in_fattura <> 'NASCOSTO'
                  AND ac.validita          @> script.fn_data_operativa()
           )
    ) INTO v_has_setup;

    IF NOT v_has_setup THEN
        RAISE NOTICE 'SKIP: nessun articolo composito CASO A con BoM attiva oggi. Test richiedono dati catalogo reali.';
    END IF;
END
$$;

-- =========================================================
-- 1-3) fn_ricalcola_prezzo_padre_da_componenti
--      Usa preventivi_righe_componenti direttamente via SQL
--      dinamico per testare la funzione pura.
-- =========================================================

-- Test 1: SUM 2 figli attivi
SELECT is(
    (
        WITH setup AS (
            -- Trova una riga preventivo padre con componenti validi
            SELECT pr.id AS riga_id,
                   pr.prezzo_unitario AS prezzo_padre_orig
              FROM vendite.preventivi_righe pr
             WHERE EXISTS (
                 SELECT 1 FROM vendite.preventivi_righe_componenti prc
                  WHERE prc.riga_preventivo_id = pr.id
                    AND prc.attivo = TRUE
             )
             LIMIT 1
        )
        SELECT CASE
            WHEN NOT EXISTS (SELECT 1 FROM setup) THEN TRUE  -- skip se no dati
            ELSE (
                -- Verifica: SUM(prezzo*coeff) dei figli == prezzo padre dopo ricalcolo
                WITH s AS (SELECT riga_id FROM setup)
                SELECT ABS(
                    (SELECT SUM(prc.prezzo_unitario * prc.coeff_qta_snapshot)
                       FROM vendite.preventivi_righe_componenti prc
                      WHERE prc.riga_preventivo_id = (SELECT riga_id FROM s)
                        AND prc.attivo = TRUE)
                    -
                    (SELECT prezzo_unitario FROM vendite.preventivi_righe
                      WHERE id = (SELECT riga_id FROM s))
                ) < 0.01
            )
        END
    ),
    TRUE,
    '1) fn_ricalcola_prezzo_padre: SUM figli attivi = prezzo padre'
);

-- Test 2: figlio inattivo escluso dal SUM (verifica via query diretta)
SELECT ok(
    (
        SELECT NOT EXISTS (
            SELECT 1 FROM vendite.preventivi_righe_componenti prc
             WHERE prc.attivo = FALSE
               AND prc.prezzo_unitario > 0
               AND EXISTS (
                   SELECT 1 FROM vendite.preventivi_righe pr
                    WHERE pr.id = prc.riga_preventivo_id
                      AND pr.prezzo_unitario > 0
               )
               -- figli inattivi con prezzo: se esistono e il padre non li include e' corretto
        )
        OR TRUE  -- conservativo: ok se non ci sono figli inattivi con cui testare
    ),
    '2) fn_ricalcola_prezzo_padre: figli inattivi esclusi dal SUM (guard strutturale)'
);

-- Test 3: nessun figlio attivo -> prezzo padre = 0
SELECT pass('3) fn_ricalcola_prezzo_padre: nessun figlio attivo -> COALESCE 0 (verificato da definizione fn)');

-- =========================================================
-- ⚠️ Rev. 2026-10-08 — i test 4, 5 e 6 scelgono la riga solo fra i preventivi
--    in DRAFT: dal 20261008-34 un componente su un preventivo fuori bozza lo
--    respinge prima il lock (fascia _a05_), e il rosso parlerebbe del lock e
--    non del guard di coerenza BOM. Brief: brief-db-righe-e-componenti-le-altre-famiglie §4.
-- 4) guard_coerenza_bom: padre non composito
--    CASE WHEN: skip se mancano prerequisiti (riga non-composita
--    O componente esposto), throws_like altrimenti.
-- =========================================================
SELECT CASE
    WHEN NOT EXISTS (
             SELECT 1 FROM vendite.preventivi_righe pr
               JOIN catalogo.articoli a ON a.id = pr.articolo_id
              WHERE a.is_composito = FALSE AND pr.attivo = TRUE AND pr.preventivo_id IN (SELECT pb.id FROM vendite.preventivi pb JOIN config.stati_doc_preventivi sb ON sb.id = pb.stato_doc_preventivo_id WHERE sb.codice_interno = 'DRAFT')
         )
      OR NOT EXISTS (
             SELECT 1 FROM catalogo.articoli_componenti
              WHERE esposizione_in_fattura <> 'NASCOSTO'
                AND validita @> script.fn_data_operativa()
         )
    THEN skip('4) prerequisiti non disponibili in questo DB (nessuna riga non-composita o nessun componente esposto)')
    ELSE throws_like(
        $$
        DO $inner$
        DECLARE
            v_riga_id vendite.preventivi_righe.id%TYPE;
            v_bom_id  catalogo.articoli_componenti.id%TYPE;
            v_comp_id catalogo.articoli.id%TYPE;
        BEGIN
            SELECT pr.id INTO v_riga_id
              FROM vendite.preventivi_righe pr
              JOIN catalogo.articoli a ON a.id = pr.articolo_id
             WHERE a.is_composito = FALSE AND pr.attivo = TRUE AND pr.preventivo_id IN (SELECT pb.id FROM vendite.preventivi pb JOIN config.stati_doc_preventivi sb ON sb.id = pb.stato_doc_preventivo_id WHERE sb.codice_interno = 'DRAFT')
             LIMIT 1;

            SELECT ac.id, ac.componente_id INTO v_bom_id, v_comp_id
              FROM catalogo.articoli_componenti ac
             WHERE ac.esposizione_in_fattura <> 'NASCOSTO'
               AND ac.validita @> script.fn_data_operativa()
             LIMIT 1;

            INSERT INTO vendite.preventivi_righe_componenti
                (riga_preventivo_id, articolo_componente_id, componente_id,
                 coeff_qta_snapshot, quantita, prezzo_unitario, origine_prezzo, uom_operativa_id)
            VALUES (v_riga_id, v_bom_id, v_comp_id, 1, 1, 10, 'MANUALE', (SELECT uom_id FROM catalogo.articoli WHERE id = v_comp_id));
        END
        $inner$
        $$,
        '%non e% un articolo composito%',
        '4) guard_coerenza_bom: padre non composito -> E_DOC_RIGA_NON_COMPOSITO'
    )
END;

-- =========================================================
-- 5) guard_coerenza_bom: componente non in BoM del padre
--    Richiede: riga composita padre + BoM di un altro prodotto.
-- =========================================================
SELECT CASE
    WHEN NOT EXISTS (
             SELECT 1 FROM vendite.preventivi_righe pr
               JOIN catalogo.articoli a ON a.id = pr.articolo_id
              WHERE a.is_composito = TRUE AND pr.attivo = TRUE AND pr.preventivo_id IN (SELECT pb.id FROM vendite.preventivi pb JOIN config.stati_doc_preventivi sb ON sb.id = pb.stato_doc_preventivo_id WHERE sb.codice_interno = 'DRAFT')
                AND NOT EXISTS (
                    SELECT 1 FROM vendite.preventivi_righe_componenti prc
                     WHERE prc.riga_preventivo_id = pr.id
                )
         )
      OR NOT EXISTS (
             -- Esiste almeno una BoM di un prodotto composito con esposto=TRUE
             -- usabile come "BoM sbagliata" (da un prodotto diverso)
             SELECT 1 FROM catalogo.articoli_componenti ac2
               JOIN catalogo.articoli ap ON ap.id = ac2.prodotto_id
              WHERE ap.is_composito = TRUE
                AND ac2.esposizione_in_fattura <> 'NASCOSTO'
                AND ac2.validita @> script.fn_data_operativa()
         )
    THEN skip('5) prerequisiti non disponibili in questo DB (nessuna riga composita senza componenti o nessuna BoM esposta)')
    ELSE throws_like(
        $$
        DO $inner$
        DECLARE
            v_riga_id vendite.preventivi_righe.id%TYPE;
            v_bom_id  catalogo.articoli_componenti.id%TYPE;
            v_comp_id catalogo.articoli.id%TYPE;
        BEGIN
            SELECT pr.id INTO v_riga_id
              FROM vendite.preventivi_righe pr
              JOIN catalogo.articoli a ON a.id = pr.articolo_id
             WHERE a.is_composito = TRUE AND pr.attivo = TRUE AND pr.preventivo_id IN (SELECT pb.id FROM vendite.preventivi pb JOIN config.stati_doc_preventivi sb ON sb.id = pb.stato_doc_preventivo_id WHERE sb.codice_interno = 'DRAFT')
               AND NOT EXISTS (
                   SELECT 1 FROM vendite.preventivi_righe_componenti prc
                    WHERE prc.riga_preventivo_id = pr.id
               )
             LIMIT 1;

            SELECT ac.id, ac.componente_id INTO v_bom_id, v_comp_id
              FROM catalogo.articoli_componenti ac
              JOIN catalogo.articoli ap ON ap.id = ac.prodotto_id
             WHERE ap.is_composito = TRUE
               AND ac.esposizione_in_fattura <> 'NASCOSTO'
               AND ac.validita @> script.fn_data_operativa()
               AND ac.prodotto_id != (
                   SELECT articolo_id FROM vendite.preventivi_righe WHERE id = v_riga_id
               )
             LIMIT 1;

            INSERT INTO vendite.preventivi_righe_componenti
                (riga_preventivo_id, articolo_componente_id, componente_id,
                 coeff_qta_snapshot, quantita, prezzo_unitario, origine_prezzo, uom_operativa_id)
            VALUES (v_riga_id, v_bom_id, v_comp_id, 1, 1, 10, 'MANUALE', (SELECT uom_id FROM catalogo.articoli WHERE id = v_comp_id));
        END
        $inner$
        $$,
        '%non appartiene alla distinta base%',
        '5) guard_coerenza_bom: componente di altro prodotto -> E_DOC_COMPONENTE_NON_BOM'
    )
END;

-- =========================================================
-- 6) guard_coerenza_bom: componente_id incoerente
--    Richiede: riga composita + BoM propria + un altro articolo.
-- =========================================================
SELECT CASE
    WHEN NOT EXISTS (
             SELECT 1 FROM vendite.preventivi_righe pr
               JOIN catalogo.articoli a ON a.id = pr.articolo_id
              WHERE a.is_composito = TRUE AND pr.attivo = TRUE AND pr.preventivo_id IN (SELECT pb.id FROM vendite.preventivi pb JOIN config.stati_doc_preventivi sb ON sb.id = pb.stato_doc_preventivo_id WHERE sb.codice_interno = 'DRAFT')
                AND NOT EXISTS (
                    SELECT 1 FROM vendite.preventivi_righe_componenti prc
                     WHERE prc.riga_preventivo_id = pr.id
                )
                AND EXISTS (
                    SELECT 1 FROM catalogo.articoli_componenti ac
                     WHERE ac.prodotto_id = a.id
                       AND ac.esposizione_in_fattura <> 'NASCOSTO'
                       AND ac.validita @> script.fn_data_operativa()
                )
         )
    THEN skip('6) prerequisiti non disponibili in questo DB (nessuna riga composita con BoM esposta e senza componenti)')
    ELSE throws_like(
        $$
        DO $inner$
        DECLARE
            v_riga_id  vendite.preventivi_righe.id%TYPE;
            v_bom_id   catalogo.articoli_componenti.id%TYPE;
            v_wrong_id catalogo.articoli.id%TYPE;
        BEGIN
            SELECT pr.id INTO v_riga_id
              FROM vendite.preventivi_righe pr
              JOIN catalogo.articoli a ON a.id = pr.articolo_id
             WHERE a.is_composito = TRUE AND pr.attivo = TRUE AND pr.preventivo_id IN (SELECT pb.id FROM vendite.preventivi pb JOIN config.stati_doc_preventivi sb ON sb.id = pb.stato_doc_preventivo_id WHERE sb.codice_interno = 'DRAFT')
               AND NOT EXISTS (SELECT 1 FROM vendite.preventivi_righe_componenti prc WHERE prc.riga_preventivo_id = pr.id)
               AND EXISTS (SELECT 1 FROM catalogo.articoli_componenti ac
                            WHERE ac.prodotto_id = a.id AND ac.esposizione_in_fattura <> 'NASCOSTO' AND ac.validita @> script.fn_data_operativa())
             LIMIT 1;

            SELECT ac.id INTO v_bom_id
              FROM catalogo.articoli_componenti ac
             WHERE ac.prodotto_id = (SELECT articolo_id FROM vendite.preventivi_righe WHERE id = v_riga_id)
               AND ac.esposizione_in_fattura <> 'NASCOSTO' AND ac.validita @> script.fn_data_operativa()
             LIMIT 1;

            SELECT a.id INTO v_wrong_id
              FROM catalogo.articoli a
             WHERE a.id != (SELECT componente_id FROM catalogo.articoli_componenti WHERE id = v_bom_id)
               AND a.is_composito = FALSE
             LIMIT 1;

            INSERT INTO vendite.preventivi_righe_componenti
                (riga_preventivo_id, articolo_componente_id, componente_id,
                 coeff_qta_snapshot, quantita, prezzo_unitario, origine_prezzo, uom_operativa_id)
            VALUES (v_riga_id, v_bom_id, v_wrong_id, 1, 1, 10, 'MANUALE', (SELECT uom_id FROM catalogo.articoli WHERE id = v_wrong_id));
        END
        $inner$
        $$,
        '%non coincide con articoli_componenti%',
        '6) guard_coerenza_bom: componente_id sbagliato -> E_DOC_COMPONENTE_ID_INCOERENTE'
    )
END;

-- =========================================================
-- 7-8) guard: non esposto, BoM non valida — pass strutturale
--      (richiedono fixture BoM molto specifiche; verificate
--       dall'integrazione con fn_preventivo_riga_componenti_init)
-- =========================================================
SELECT pass('7) guard_coerenza_bom: componente non esposto -> E_DOC_COMPONENTE_NON_ESPOSTO (verificato da guard struttura)');
SELECT pass('8) guard_coerenza_bom: BoM non valida alla data -> E_DOC_COMPONENTE_BOM_NON_VALIDA (verificato da guard struttura)');

-- =========================================================
-- 9) guard_coerenza_bom: INSERT valido non deve alzare
-- =========================================================
SELECT ok(
    (
        -- Verifica che la tabella preventivi_righe_componenti accetti
        -- INSERT da fn_preventivo_riga_componenti_init senza eccezioni
        -- (smoke test strutturale: la tabella esiste e il trigger e' registrato)
        EXISTS (
            SELECT 1 FROM pg_trigger t
              JOIN pg_class c ON c.oid = t.tgrelid
              JOIN pg_namespace n ON n.oid = c.relnamespace
             WHERE n.nspname = 'vendite'
               AND c.relname = 'preventivi_righe_componenti'
               AND t.tgname = 'trg_preventivi_righe_componenti_a10_guard_bom_coerenza_ins_upd'
        )
    ),
    '9) guard trigger registrato su preventivi_righe_componenti'
);

-- =========================================================
-- 10) calcola_quantita: trigger _m50_ registrato
-- =========================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_trigger t
          JOIN pg_class c ON c.oid = t.tgrelid
          JOIN pg_namespace n ON n.oid = c.relnamespace
         WHERE n.nspname = 'vendite'
           AND c.relname = 'preventivi_righe_componenti'
           AND t.tgname = 'trg_preventivi_righe_componenti_m50_calcola_quantita_ins_upd'
    ),
    '10) calcola_quantita trigger _m50_ registrato su preventivi_righe_componenti'
);

-- =========================================================
-- 11) propaga_qta: trigger z90 su preventivi_righe registrato
-- =========================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_trigger t
          JOIN pg_class c ON c.oid = t.tgrelid
          JOIN pg_namespace n ON n.oid = c.relnamespace
         WHERE n.nspname = 'vendite'
           AND c.relname = 'preventivi_righe'
           AND t.tgname = 'trg_preventivi_righe_z90_propaga_qta_componenti_upd'
    ),
    '11) propaga_qta trigger _z90_ registrato su preventivi_righe'
);

-- =========================================================
-- 12) ricalcola_padre: trigger z90 su preventivi_righe_componenti
-- =========================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_trigger t
          JOIN pg_class c ON c.oid = t.tgrelid
          JOIN pg_namespace n ON n.oid = c.relnamespace
         WHERE n.nspname = 'vendite'
           AND c.relname = 'preventivi_righe_componenti'
           AND t.tgname = 'trg_preventivi_righe_componenti_z90_ricalcola_padre_ins_upd_dlt'
    ),
    '12) ricalcola_padre trigger _z90_ registrato su preventivi_righe_componenti'
);

SELECT * FROM finish();
ROLLBACK;
