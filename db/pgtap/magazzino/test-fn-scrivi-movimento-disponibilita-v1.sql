-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- pgtap-runner: owner
-- pgtap-runner-motivo: il soggetto sono i CONTROLLI della primitiva
--   magazzino.fn_scrivi_movimento, che dal 2026-09-24 l'app non esegue piu': la
--   raggiunge solo dai verbi fn_posta_inventario / fn_posta_rettifica
--   (brief-db-magazzino-verbi-con-permesso, P-4). Chiamarla coi parametri che il
--   test sceglie e' cosa che solo uno scrittore privilegiato puo' fare: forma 3
--   del criterio del runner, come i test del ledger del Lotto 2. Il contesto
--   operatore resta impostato: il guard di scope e i controlli lo leggono.
--
-- Test: la disponibilita' nella primitiva (passo 11 di sezione 4.2) e la
--   check che UI e primitiva condividono, script.fn_check_disponibilita_uscita
--   (sezione 4.3, D-L2-d). Brief: brief-db-magazzino-lotto-2-motore, sezione 7.
--
-- ⚠️ Fixture COSTRUITA: azienda e operatore dall'helper, un magazzino, un
--   articolo semplice e uno per lotti (due lotti, 3 + 17), le sorgenti (un
--   inventario DRAFT con una riga per ogni scrittura), due blocchi (attesi
--   APERTA in uscita): uno manuale senza sorgente (-4) e uno con sorgente
--   (-5, la riga r4). Giacenza dell'articolo semplice: 20.
-- ⚠️ consente_stock_negativo e' falso su tutte le causali del seed (fatto
--   datato 18-09): il caso si COSTRUISCE alzando il flag in transazione.
--
-- Elenco test (plan 9):
--   1) uscita 21 su giacenza 20 -> E_MAG_GIACENZA_INSUFFICIENTE, «disponibili 20, richiesti 21»
--   2) uscita 12 con blocchi altrui -4 e -5 -> E_MAG_MERCE_BLOCCATA, «11 pezzi disponibili (9 bloccati per altri): richiesti 12»
--   3) la stessa uscita con la SORGENTE del blocco -5 -> quello non e' altrui: passa (giacenza 8)
--   4) is_rettifica (RETT_NEG -7 con blocco -4 su giacenza 8): ignora i blocchi, passa (giacenza 1)
--   5) ...ma NON il fisico: RETT_NEG -5 su giacenza 1 -> E_MAG_GIACENZA_INSUFFICIENTE
--   6) grana LOTTO: articolo per lotti 20 (3 + 17), uscita 5 dal lotto da 3 -> «disponibili 3, richiesti 5»
--   7) la check chiamata da sola (come operatore) da' lo STESSO primo motivo che la madre solleva
--   8) ...e i suoi valori sono quelli della frase (una sede sola: non possono divergere)
--   9) consente_stock_negativo (costruito): l'uscita passa sotto zero
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(9);

CREATE TEMP TABLE _mondo AS SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _mondo)); END $ctx$;

CREATE TEMP TABLE _fix (mag bigint, art uuid, art_lotto uuid, l1 bigint, l2 bigint, src bigint,
                        r1 bigint, r2 bigint, r3 bigint, r4 bigint, r5 bigint, r6 bigint, r7 bigint, r8 bigint, r9 bigint);
DO $fix$
DECLARE
    v_mag bigint; v_art uuid; v_art_lotto uuid; v_l1 bigint; v_l2 bigint; v_inv bigint; v_tmp bigint;
    v_r bigint[] := '{}'; i int;
    v_src bigint := (SELECT id FROM config.sorgenti WHERE codice_interno = 'INVENTARIO');
BEGIN
    v_mag := dbops.fn_pgtap_crea_magazzino('PGT-L2D-A', false);
    v_art := dbops.fn_pgtap_crea_articolo('PGT-L2D-ART', true, false, false);
    v_art_lotto := dbops.fn_pgtap_crea_articolo('PGT-L2D-LOT', true, true, false);
    INSERT INTO magazzino.lotti (articolo_id, codice, data_arrivo) VALUES (v_art_lotto, 'PGT-L2D-L1', script.fn_data_operativa()) RETURNING id INTO v_l1;
    INSERT INTO magazzino.lotti (articolo_id, codice, data_arrivo) VALUES (v_art_lotto, 'PGT-L2D-L2', script.fn_data_operativa()) RETURNING id INTO v_l2;
    FOR i IN 1..9 LOOP
        INSERT INTO magazzino.inventari (magazzino_id) VALUES (v_mag) RETURNING id INTO v_inv;
        INSERT INTO magazzino.inventari_righe (inventario_id, articolo_id, qta_contata) VALUES (v_inv, v_art, i) RETURNING id INTO v_tmp;
        v_r := v_r || v_tmp;
    END LOOP;
    INSERT INTO _fix VALUES (v_mag, v_art, v_art_lotto, v_l1, v_l2, v_src, v_r[1], v_r[2], v_r[3], v_r[4], v_r[5], v_r[6], v_r[7], v_r[8], v_r[9]);

    -- Giacenza 20 dell'articolo semplice; 3 + 17 di quello per lotti.
    PERFORM magazzino.fn_scrivi_movimento(v_mag, v_art, 'INV_INIZIALE', 10, v_src, v_r[1], NULL, 5, p_sorgente_id => (SELECT ir.inventario_id FROM magazzino.inventari_righe ir WHERE ir.id = v_r[1]));
    PERFORM magazzino.fn_scrivi_movimento(v_mag, v_art, 'RETT_POS',     10, v_src, v_r[2], NULL, 5, p_sorgente_id => (SELECT ir.inventario_id FROM magazzino.inventari_righe ir WHERE ir.id = v_r[2]));
    PERFORM magazzino.fn_scrivi_movimento(v_mag, v_art_lotto, 'INV_INIZIALE',  3, v_src, v_r[8], NULL, 5, v_l1, p_sorgente_id => (SELECT ir.inventario_id FROM magazzino.inventari_righe ir WHERE ir.id = v_r[8]));
    PERFORM magazzino.fn_scrivi_movimento(v_mag, v_art_lotto, 'RETT_POS',     17, v_src, v_r[9], NULL, 5, v_l2, p_sorgente_id => (SELECT ir.inventario_id FROM magazzino.inventari_righe ir WHERE ir.id = v_r[9]));

    -- I blocchi: uno manuale (senza sorgente), uno con la sorgente r4.
    INSERT INTO magazzino.movimenti_attesi (articolo_id, magazzino_id, qta, causale_id, stato, nota)
    VALUES (v_art, v_mag, -4, (SELECT id FROM magazzino.causali WHERE codice_interno = 'SCARICO_VEN'), 'APERTA', 'blocco manuale');
    -- rev 2026-11-09 (lotto M): la provenienza del modello, l'inventario e la sua riga.
    INSERT INTO magazzino.movimenti_attesi (articolo_id, magazzino_id, qta, causale_id, stato, sorgente_tipo_id, sorgente_id, sorgente_riga)
    VALUES (v_art, v_mag, -5, (SELECT id FROM magazzino.causali WHERE codice_interno = 'SCARICO_VEN'), 'APERTA', v_src,
            (SELECT ir.inventario_id FROM magazzino.inventari_righe ir WHERE ir.id = v_r[4]), v_r[4]);
END $fix$;

SELECT throws_like(
    $$ SELECT magazzino.fn_scrivi_movimento(mag, art, 'SCARICO_VEN', -21, src, r3, p_sorgente_id => (SELECT ir.inventario_id FROM magazzino.inventari_righe ir WHERE ir.id = r3)) FROM _fix $$,
    '%Giacenza insufficiente per l''articolo PGT-L2D-ART nel magazzino PGT-L2D-A: disponibili 20, richiesti 21.%',
    '1) oltre la giacenza: E_MAG_GIACENZA_INSUFFICIENTE con i valori nella frase');

SELECT throws_like(
    $$ SELECT magazzino.fn_scrivi_movimento(mag, art, 'SCARICO_VEN', -12, src, r3, p_sorgente_id => (SELECT ir.inventario_id FROM magazzino.inventari_righe ir WHERE ir.id = r3)) FROM _fix $$,
    '%L''articolo PGT-L2D-ART nel magazzino PGT-L2D-A ha 11 pezzi disponibili (9 bloccati per altri): richiesti 12.%',
    '2) dentro la giacenza ma oltre i blocchi ALTRUI: E_MAG_MERCE_BLOCCATA');

SELECT lives_ok(
    $$ SELECT magazzino.fn_scrivi_movimento(mag, art, 'SCARICO_VEN', -12, src, r4, p_sorgente_id => (SELECT ir.inventario_id FROM magazzino.inventari_righe ir WHERE ir.id = r4)) FROM _fix $$,
    '3) la stessa uscita con la sorgente del blocco -5: quel blocco non e'' altrui, passa');

SELECT lives_ok(
    $$ SELECT magazzino.fn_scrivi_movimento(mag, art, 'RETT_NEG', -7, src, r5, p_sorgente_id => (SELECT ir.inventario_id FROM magazzino.inventari_righe ir WHERE ir.id = r5)) FROM _fix $$,
    '4) is_rettifica: il fatto vince sulla promessa — RETT_NEG passa sotto il blocco');

SELECT throws_like(
    $$ SELECT magazzino.fn_scrivi_movimento(mag, art, 'RETT_NEG', -5, src, r6, p_sorgente_id => (SELECT ir.inventario_id FROM magazzino.inventari_righe ir WHERE ir.id = r6)) FROM _fix $$,
    '%disponibili 1, richiesti 5.%',
    '5) ...ma non sotto il fisico: E_MAG_GIACENZA_INSUFFICIENTE');

SELECT throws_like(
    $$ SELECT magazzino.fn_scrivi_movimento(mag, art_lotto, 'SCARICO_VEN', -5, src, r7, NULL, NULL, l1, p_sorgente_id => (SELECT ir.inventario_id FROM magazzino.inventari_righe ir WHERE ir.id = r7)) FROM _fix $$,
    '%disponibili 3, richiesti 5.%',
    '6) grana LOTTO: l''articolo ne ha 20, il lotto 3 — l''uscita di 5 dal lotto si ferma sul lotto');

SELECT is(
    (SELECT script.fn_check_disponibilita_uscita(mag, art, 5) -> 0 ->> 'codice' FROM _fix),
    'E_MAG_GIACENZA_INSUFFICIENTE',
    '7) la check da sola, come operatore, da'' lo stesso primo motivo che la madre solleva');
SELECT is(
    (SELECT script.fn_check_disponibilita_uscita(mag, art, 5) -> 0 -> 'valori' FROM _fix),
    '["PGT-L2D-ART", "PGT-L2D-A", "1", "5"]'::jsonb,
    '8) ...e i suoi valori sono quelli della frase del 5: una sede sola');

-- Il caso costruito: consente_stock_negativo su SCARICO_VEN, in transazione.
UPDATE magazzino.causali SET consente_stock_negativo = true WHERE codice_interno = 'SCARICO_VEN';
SELECT lives_ok(
    $$ SELECT magazzino.fn_scrivi_movimento(mag, art, 'SCARICO_VEN', -100, src, r6, p_sorgente_id => (SELECT ir.inventario_id FROM magazzino.inventari_righe ir WHERE ir.id = r6)) FROM _fix $$,
    '9) consente_stock_negativo: l''uscita passa sotto zero (ne'' fisico ne'' blocchi)');

SELECT * FROM finish();
ROLLBACK;
