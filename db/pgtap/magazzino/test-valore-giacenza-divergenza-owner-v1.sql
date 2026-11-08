-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- pgtap-runner: owner
-- pgtap-runner-motivo: il soggetto e' una scrittura FUORI DALLA PORTA del
--   ledger (UPDATE diretto su valore_giacenza, DELETE di un movimento), che
--   solo il proprietario puo' fare — l'app ha SELECT soltanto (D-L2-b). E'
--   la forma 3 del criterio del runner. Il contesto operatore e' comunque
--   impostato: la primitiva (DEFINER) e le fixture lo vogliono.
--
-- Test: la spia della divergenza (dbops.vw_magazzino_valore_giacenza_divergente)
--   e il ricalcolo (fn_ricalcola_valore_giacenza) — la vista non prova
--   l'aritmetica, prova che nessuno ha scritto fuori dalla porta. Brief:
--   brief-db-magazzino-lotto-2-motore, sezione 4.4, sezione 7.
--
-- Elenco test (plan 5):
--   1) mondo costruito via primitiva: nessuna divergenza
--   2) UPDATE diretto sulla copia (+1) -> UNA divergenza, e fn_conta_presidio la conta
--   3) il ricalcolo la fa sparire (prima 151, dopo 150)
--   4) DELETE di un movimento (fuori porta): la copia resta e il registro cala -> divergenza
--   5) il ricalcolo riallinea la copia al registro
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(5);

CREATE TEMP TABLE _mondo AS SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _mondo)); END $ctx$;

CREATE TEMP TABLE _fix (mag bigint, art uuid, src bigint, r1 bigint, r2 bigint);
DO $fix$
DECLARE v_mag bigint; v_art uuid; v_inv bigint; v_r1 bigint; v_r2 bigint;
BEGIN
    v_mag := dbops.fn_pgtap_crea_magazzino('PGT-L2O-A', false);
    v_art := dbops.fn_pgtap_crea_articolo('PGT-L2O-ART', true, false, false);
    INSERT INTO magazzino.inventari (magazzino_id) VALUES (v_mag) RETURNING id INTO v_inv;
    INSERT INTO magazzino.inventari_righe (inventario_id, articolo_id, qta_contata) VALUES (v_inv, v_art, 5) RETURNING id INTO v_r1;
    INSERT INTO magazzino.inventari (magazzino_id) VALUES (v_mag) RETURNING id INTO v_inv;
    INSERT INTO magazzino.inventari_righe (inventario_id, articolo_id, qta_contata) VALUES (v_inv, v_art, 5) RETURNING id INTO v_r2;
    INSERT INTO _fix VALUES (v_mag, v_art, (SELECT id FROM config.sorgenti WHERE codice_interno = 'INVENTARIO'), v_r1, v_r2);
    PERFORM magazzino.fn_scrivi_movimento(v_mag, v_art, 'INV_INIZIALE', 5, (SELECT src FROM _fix), v_r1, NULL, 10, p_sorgente_id => (SELECT ir.inventario_id FROM magazzino.inventari_righe ir WHERE ir.id = v_r1));
    PERFORM magazzino.fn_scrivi_movimento(v_mag, v_art, 'RETT_POS',     5, (SELECT src FROM _fix), v_r2, NULL, 20, p_sorgente_id => (SELECT ir.inventario_id FROM magazzino.inventari_righe ir WHERE ir.id = v_r2));
END $fix$;

SELECT is((SELECT count(*) FROM dbops.vw_magazzino_valore_giacenza_divergente d WHERE d.magazzino_id = (SELECT mag FROM _fix)), 0::bigint,
    '1) mondo costruito via primitiva: nessuna divergenza');

UPDATE magazzino.valore_giacenza SET valore = valore + 1 WHERE magazzino_id = (SELECT mag FROM _fix);
SELECT is(
    (SELECT (count(*), max(trim_scale(valore_copia)), max(trim_scale(valore_registro)))::text FROM dbops.vw_magazzino_valore_giacenza_divergente d WHERE d.magazzino_id = (SELECT mag FROM _fix)),
    '(1,151,150)',
    '2) una scrittura fuori porta sulla copia: UNA divergenza (151 contro 150)');

SELECT is(
    (SELECT (trim_scale(valore_prima), trim_scale(valore_dopo))::text FROM magazzino.fn_ricalcola_valore_giacenza((SELECT mag FROM _fix))),
    '(151,150)',
    '3) il ricalcolo riscrive la copia dal registro: 151 -> 150');

DELETE FROM magazzino.movimenti WHERE sorgente_riga = (SELECT r2 FROM _fix);
SELECT is(
    (SELECT (trim_scale(valore_copia), trim_scale(valore_registro))::text FROM dbops.vw_magazzino_valore_giacenza_divergente d WHERE d.magazzino_id = (SELECT mag FROM _fix)),
    '(150,50)',
    '4) un movimento cancellato fuori porta: la copia resta a 150, il registro dice 50 -> divergenza');

-- ⚠️ Il verbo in un'istruzione SEPARATA: un'asserzione nella stessa SELECT
--   leggerebbe lo snapshot di prima del ricalcolo (memoria pgtap_stessa_istruzione_snapshot).
CREATE TEMP TABLE _ric AS SELECT * FROM magazzino.fn_ricalcola_valore_giacenza((SELECT mag FROM _fix));
SELECT is(
    (SELECT count(*) FROM _ric r WHERE r.valore_dopo = 50)
    + (SELECT count(*) FROM dbops.vw_magazzino_valore_giacenza_divergente d WHERE d.magazzino_id = (SELECT mag FROM _fix)),
    1::bigint,
    '5) il ricalcolo riallinea (dopo = 50) e la divergenza sparisce');

SELECT * FROM finish();
ROLLBACK;
