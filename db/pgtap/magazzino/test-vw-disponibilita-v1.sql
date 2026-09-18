-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: le viste della disponibilita' (M-3, D-L2-j): vw_disponibilita e
--   vw_disponibilita_articolo. Brief: brief-db-magazzino-lotto-2-motore,
--   sezione 4.6, sezione 7.
--
-- Elenco test (plan 7):
--   1) giacenza 10, blocco -4 -> bloccata -4, disponibile 6, n_blocchi 1 (in COLONNE: la somma)
--   2) un blocco CHIUSA non conta
--   3) un atteso in ENTRATA (in arrivo) non e' un blocco e non conta
--   4) un articolo con un blocco e SENZA movimenti compare (giacenza 0, disponibile negativo)
--   5) la grana per articolo somma i magazzini e li conta
--   6) niente colonne impegnata / potenziale / in_arrivo (D-L2-j: entrano con chi le sa riempire)
--   7) security_invoker su entrambe
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(7);

CREATE TEMP TABLE _mondo AS SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _mondo)); END $ctx$;

CREATE TEMP TABLE _fix (mag_a bigint, mag_b bigint, art uuid, art2 uuid);
DO $fix$
DECLARE v_a bigint; v_b bigint; v_art uuid; v_art2 uuid; v_inv bigint; v_cau_out bigint; v_cau_in bigint;
BEGIN
    v_a := dbops.fn_pgtap_crea_magazzino('PGT-L2W-A', false);
    v_b := dbops.fn_pgtap_crea_magazzino('PGT-L2W-B', false);
    v_art  := dbops.fn_pgtap_crea_articolo('PGT-L2W-ART', true, false, false);
    v_art2 := dbops.fn_pgtap_crea_articolo('PGT-L2W-ART2', true, false, false);
    INSERT INTO _fix VALUES (v_a, v_b, v_art, v_art2);
    -- giacenza 10 in A e 5 in B, via inventario
    INSERT INTO magazzino.inventari (magazzino_id) VALUES (v_a) RETURNING id INTO v_inv;
    INSERT INTO magazzino.inventari_righe (inventario_id, articolo_id, qta_contata) VALUES (v_inv, v_art, 10);
    UPDATE magazzino.inventari SET stato_mag_inventario = 'CONFIRM' WHERE id = v_inv;
    PERFORM magazzino.fn_posta_inventario(v_inv);
    INSERT INTO magazzino.inventari (magazzino_id) VALUES (v_b) RETURNING id INTO v_inv;
    INSERT INTO magazzino.inventari_righe (inventario_id, articolo_id, qta_contata) VALUES (v_inv, v_art, 5);
    UPDATE magazzino.inventari SET stato_mag_inventario = 'CONFIRM' WHERE id = v_inv;
    PERFORM magazzino.fn_posta_inventario(v_inv);
    SELECT id INTO v_cau_out FROM magazzino.causali WHERE codice_interno = 'SCARICO_VEN';
    SELECT id INTO v_cau_in  FROM magazzino.causali WHERE codice_interno = 'CARICO_ACQ';
    -- i blocchi: -4 aperto, -50 chiuso, +100 in arrivo (A, art); -3 aperto su art2 in B (senza movimenti)
    INSERT INTO magazzino.movimenti_attesi (articolo_id, magazzino_id, qta, causale_id, stato, nota) VALUES (v_art, v_a, -4, v_cau_out, 'APERTA', 'b');
    INSERT INTO magazzino.movimenti_attesi (articolo_id, magazzino_id, qta, causale_id, stato, data_chiusura, nota) VALUES (v_art, v_a, -50, v_cau_out, 'CHIUSA', now(), 'c');
    INSERT INTO magazzino.movimenti_attesi (articolo_id, magazzino_id, qta, causale_id, stato, nota) VALUES (v_art, v_a, 100, v_cau_in, 'APERTA', 'arrivo');
    INSERT INTO magazzino.movimenti_attesi (articolo_id, magazzino_id, qta, causale_id, stato, nota) VALUES (v_art2, v_b, -3, v_cau_out, 'APERTA', 'b2');
END $fix$;

SELECT is(
    (SELECT (trim_scale(giacenza), trim_scale(bloccata), trim_scale(disponibile), n_blocchi)::text FROM magazzino.vw_disponibilita d JOIN _fix f ON d.magazzino_id = f.mag_a AND d.articolo_id = f.art),
    '(10,-4,6,1)',
    '1) giacenza 10, blocco -4: bloccata -4, disponibile 6 (la somma), un blocco');
SELECT is(
    (SELECT count(*) FROM magazzino.movimenti_attesi a JOIN _fix f ON a.magazzino_id = f.mag_a AND a.articolo_id = f.art WHERE a.stato = 'CHIUSA'),
    1::bigint,
    '2) il blocco CHIUSA c''e'' (fixture) e non e'' entrato nel conto del test 1');
SELECT is(
    (SELECT count(*) FROM magazzino.movimenti_attesi a JOIN _fix f ON a.magazzino_id = f.mag_a AND a.articolo_id = f.art WHERE a.qta > 0 AND a.stato = 'APERTA'),
    1::bigint,
    '3) l''atteso in entrata c''e'' (fixture) e non e'' entrato nel conto del test 1: non e'' un blocco');
SELECT is(
    (SELECT (trim_scale(giacenza), trim_scale(disponibile))::text FROM magazzino.vw_disponibilita d JOIN _fix f ON d.magazzino_id = f.mag_b AND d.articolo_id = f.art2),
    '(0,-3)',
    '4) un articolo con un blocco e senza movimenti compare: giacenza 0, disponibile -3 (FULL JOIN)');
SELECT is(
    (SELECT (trim_scale(giacenza), trim_scale(bloccata), trim_scale(disponibile), n_magazzini)::text FROM magazzino.vw_disponibilita_articolo d JOIN _fix f ON d.articolo_id = f.art),
    '(15,-4,11,2)',
    '5) per articolo: 10 + 5, bloccata -4, disponibile 11, due magazzini');
SELECT is(
    (SELECT count(*) FROM pg_attribute WHERE attrelid = 'magazzino.vw_disponibilita'::regclass AND attname IN ('impegnata', 'potenziale', 'in_arrivo')),
    0::bigint,
    '6) niente impegnata / potenziale / in_arrivo: aspettano D-17');
SELECT is(
    (SELECT string_agg(c.relname || '=' || c.reloptions::text, ' ' ORDER BY c.relname) FROM pg_class c WHERE c.oid IN ('magazzino.vw_disponibilita'::regclass, 'magazzino.vw_disponibilita_articolo'::regclass)),
    'vw_disponibilita={security_invoker=true} vw_disponibilita_articolo={security_invoker=true}',
    '7) security_invoker su entrambe');

SELECT * FROM finish();
ROLLBACK;
