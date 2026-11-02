-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: la rettifica — fn_posta_rettifica (D-L2-g): il delta e' dato, la
--   causale dal segno, il costo della riga solo in entrata, i blocchi non
--   fermano (is_rettifica), il fisico si'. Brief:
--   brief-db-magazzino-lotto-2-motore, sezione 4.5, sezione 7.
--
-- Elenco test (plan 6):
--   1) giacenza 10 (costo 7): rettifica +3 con costo 9 e -2 -> due movimenti, RETT_POS a 9 e RETT_NEG alla media
--   2) la testata va a POSTED e la giacenza e' 11
--   3) RETT_NEG sotto un blocco altrui (-20 su giacenza 11): passa — il fatto vince sulla promessa
--   4) RETT_NEG oltre la giacenza (-30) -> rifiuto fisico (E_MAG_GIACENZA_INSUFFICIENTE)
--   5) ...e la testata resta CONFIRM, nessun movimento nuovo
--   6) posting di una DRAFT -> E_MAG_DOCUMENTO_TRANSIZIONE_NON_AMMESSA (DRAFT, POSTED)
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(6);

CREATE TEMP TABLE _mondo AS SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _mondo)); END $ctx$;
-- Rev 2026-09-24 (brief-db-magazzino-verbi-con-permesso §3.2): fn_posta_inventario e
--   fn_posta_rettifica sono VERBI e applicano registra_magazzino (script.fn_guard_azione);
--   l'operatore di fixture e' tecnico e non ha azioni: il permesso si costruisce qui.
DO $az$ BEGIN
    PERFORM dbops.fn_pgtap_concedi_azione((SELECT auth_user_id FROM _mondo), 'registra_magazzino');
    -- Rev 2026-09-28 (Lotto 3, D-L3-j): il blocco del test 3 si apre col verbo.
    PERFORM dbops.fn_pgtap_concedi_azione((SELECT auth_user_id FROM _mondo), 'blocca_merce');
END $az$;

CREATE TEMP TABLE _fix (mag bigint, art uuid);
DO $fix$
DECLARE v_mag bigint; v_art uuid; v_inv bigint;
BEGIN
    v_mag := dbops.fn_pgtap_crea_magazzino('PGT-L2R-A', false);
    v_art := dbops.fn_pgtap_crea_articolo('PGT-L2R-ART', true, false, false);
    INSERT INTO _fix VALUES (v_mag, v_art);
    -- giacenza 10 a 7 EUR, via inventario
    INSERT INTO magazzino.inventari (magazzino_id) VALUES (v_mag) RETURNING id INTO v_inv;
    INSERT INTO magazzino.inventari_righe (inventario_id, articolo_id, qta_contata, costo_unitario) VALUES (v_inv, v_art, 10, 7);
    UPDATE magazzino.inventari SET stato_mag_inventario = 'CONFIRM' WHERE id = v_inv;
    PERFORM magazzino.fn_posta_inventario(v_inv);
END $fix$;

-- 1-2) +3 a 9, -2
CREATE TEMP TABLE _ret1 AS SELECT NULL::bigint AS id;
DO $r$ DECLARE v_id bigint; BEGIN
    INSERT INTO magazzino.rettifiche (magazzino_id) SELECT mag FROM _fix RETURNING id INTO v_id;
    INSERT INTO magazzino.rettifiche_righe (rettifica_id, articolo_id, qta_delta, costo_unitario) SELECT v_id, art, 3, 9 FROM _fix;
    INSERT INTO magazzino.rettifiche_righe (rettifica_id, articolo_id, qta_delta) SELECT v_id, art, -2 FROM _fix;
    UPDATE magazzino.rettifiche SET stato_mag_rettifiche = 'CONFIRM' WHERE id = v_id;
    UPDATE _ret1 SET id = v_id;
END $r$;
CREATE TEMP TABLE _post1 AS SELECT * FROM magazzino.fn_posta_rettifica((SELECT id FROM _ret1));
SELECT is(
    (SELECT string_agg(c.codice_interno || '@' || trim_scale(m.costo_unitario)::text, ' ' ORDER BY m.id)
       FROM _post1 p JOIN magazzino.movimenti m ON m.id = p.movimento_id JOIN magazzino.causali c ON c.id = m.causale_id),
    'RETT_POS@9 RETT_NEG@7.461538',
    '1) due movimenti: RETT_POS al costo della riga (9), RETT_NEG alla media corrente ((70+27)/13)');
SELECT is(
    (SELECT ((SELECT stato_mag_rettifiche FROM magazzino.rettifiche WHERE id = (SELECT id FROM _ret1)),
             (SELECT trim_scale(g.qta) FROM magazzino.vw_giacenza g WHERE g.magazzino_id = (SELECT mag FROM _fix) AND g.articolo_id = (SELECT art FROM _fix)))::text),
    '(POSTED,11)',
    '2) testata POSTED, giacenza 11');

-- 3) sotto un blocco altrui
-- Rev 2026-09-28: l'app non scrive piu' movimenti_attesi, il blocco lo apre il verbo.
DO $b$ BEGIN PERFORM magazzino.fn_apri_blocco((SELECT mag FROM _fix), (SELECT art FROM _fix), 20, NULL, 'blocco'); END $b$;
CREATE TEMP TABLE _ret2 AS SELECT NULL::bigint AS id;
DO $r$ DECLARE v_id bigint; BEGIN
    INSERT INTO magazzino.rettifiche (magazzino_id) SELECT mag FROM _fix RETURNING id INTO v_id;
    INSERT INTO magazzino.rettifiche_righe (rettifica_id, articolo_id, qta_delta) SELECT v_id, art, -5 FROM _fix;
    UPDATE magazzino.rettifiche SET stato_mag_rettifiche = 'CONFIRM' WHERE id = v_id;
    UPDATE _ret2 SET id = v_id;
END $r$;
SELECT lives_ok(
    $$ SELECT * FROM magazzino.fn_posta_rettifica((SELECT id FROM _ret2)) $$,
    '3) RETT_NEG sotto un blocco altrui: passa, il fatto vince sulla promessa (D-L2-d)');

-- 4-5) oltre la giacenza (6 dopo il 3)
CREATE TEMP TABLE _ret3 AS SELECT NULL::bigint AS id;
DO $r$ DECLARE v_id bigint; BEGIN
    INSERT INTO magazzino.rettifiche (magazzino_id) SELECT mag FROM _fix RETURNING id INTO v_id;
    INSERT INTO magazzino.rettifiche_righe (rettifica_id, articolo_id, qta_delta) SELECT v_id, art, -30 FROM _fix;
    UPDATE magazzino.rettifiche SET stato_mag_rettifiche = 'CONFIRM' WHERE id = v_id;
    UPDATE _ret3 SET id = v_id;
END $r$;
SELECT throws_like(
    $$ SELECT * FROM magazzino.fn_posta_rettifica((SELECT id FROM _ret3)) $$,
    '%disponibili 6, richiesti 30.%',
    '4) RETT_NEG oltre la giacenza: il fisico resta');
SELECT is(
    (SELECT ((SELECT stato_mag_rettifiche FROM magazzino.rettifiche WHERE id = (SELECT id FROM _ret3)),
             (SELECT count(*) FROM magazzino.movimenti m WHERE m.magazzino_id = (SELECT mag FROM _fix)))::text),
    '(CONFIRM,4)',
    '5) ...la testata resta CONFIRM e i movimenti sono ancora quattro');

-- 6) una DRAFT
CREATE TEMP TABLE _ret4 AS SELECT NULL::bigint AS id;
DO $r$ DECLARE v_id bigint; BEGIN
    INSERT INTO magazzino.rettifiche (magazzino_id) SELECT mag FROM _fix RETURNING id INTO v_id;
    UPDATE _ret4 SET id = v_id;
END $r$;
SELECT throws_like(
    $$ SELECT * FROM magazzino.fn_posta_rettifica((SELECT id FROM _ret4)) $$,
    '%Il documento è in stato DRAFT: il passaggio a POSTED non è ammesso.%',
    '6) posting di una DRAFT: E_MAG_DOCUMENTO_TRANSIZIONE_NON_AMMESSA');

SELECT * FROM finish();
ROLLBACK;
