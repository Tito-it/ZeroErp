-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: l'inventario — il piano (fn_inventario_piano, D-L2-n) e il posting
--   (fn_posta_inventario, D-L2-f/h), alla grana della riga, con le ubicazioni
--   decise dal magazzino (D-L2-m) e il ritorno in bozza (C13). Brief:
--   brief-db-magazzino-lotto-2-motore, sezioni 3, 4.5, 7.
--
-- ⚠️ Fixture COSTRUITA: un magazzino A UBICAZIONI (UX, UY) e uno senza, un
--   articolo gestito, uno per lotti, uno NON gestito.
--
-- Elenco test (plan 17 — il 7 e il 15 sono in due asserzioni):
--   1) primo conteggio (A = 10 in UX, costo 7) su merce mai movimentata: il piano dice INV_INIZIALE
--   2) il posting scrive UN movimento (riga, qta 10) e la testata va a POSTED
--   3) qta_sistema = 0 scritto sulla riga (la fotografia contro cui il conteggio e' stato posto)
--   4) il movimento porta il costo della riga (7) e la causale INV_INIZIALE
--   5) secondo inventario: A = 12 in UY con 10 in UX a registro -> piano: (UY) RETT_POS 12 e (UX) NON_CONTATA (il caso di Tid)
--   6) riapri (CONFIRM -> DRAFT, C13), aggiungi UX = 10 e una riga dell'articolo NON gestito -> INVARIATA e NON_POSTABILE con reason
--   7) il posting rifiuta TUTTO col primo motivo della check: testata ancora CONFIRM, nessun movimento nuovo (all-or-nothing)
--   8) tolta la riga cattiva (riapri): posting -> UY 12 postata, UX invariata; giacenza 22
--   9) qta_sistema 10 e 0 sulle due righe, dal piano
--  10) posting di nuovo su POSTED -> E_MAG_DOCUMENTO_TRANSIZIONE_NON_AMMESSA (valori: POSTED, POSTED)
--  11) CONFIRM senza righe -> E_MAG_DOCUMENTO_SENZA_RIGHE
--  12) riga senza ubicazione in un magazzino a ubicazioni -> piano NON_POSTABILE UBICAZIONE_OBBLIGATORIA
--  13) riga CON ubicazione nel magazzino senza -> UBICAZIONE_NON_AMMESSA
--  14) grana LOTTO: riga con lotto L confronta il lotto L (sistema 3), non l'articolo (20)
--  15) un inventario fuori perimetro (id inesistente) -> E_MAG_DOCUMENTO_NON_TROVATO (404 no-leak) e piano vuoto
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(17);

CREATE TEMP TABLE _mondo AS SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _mondo)); END $ctx$;
-- Rev 2026-09-24 (brief-db-magazzino-verbi-con-permesso §3.2): fn_posta_inventario e
--   fn_posta_rettifica sono VERBI e applicano registra_magazzino (script.fn_guard_azione);
--   l'operatore di fixture e' tecnico e non ha azioni: il permesso si costruisce qui.
DO $az$ BEGIN PERFORM dbops.fn_pgtap_concedi_azione((SELECT auth_user_id FROM _mondo), 'registra_magazzino'); END $az$;

CREATE TEMP TABLE _fix (mag bigint, mag_no bigint, ux bigint, uy bigint, art uuid, art_lotto uuid, art_no uuid, l1 bigint, l2 bigint);
DO $fix$
DECLARE v_mag bigint; v_no bigint; v_ux bigint; v_uy bigint; v_art uuid; v_lot uuid; v_nog uuid; v_l1 bigint; v_l2 bigint; v_tipo bigint;
BEGIN
    v_mag := dbops.fn_pgtap_crea_magazzino('PGT-L2I-U', true);
    v_no  := dbops.fn_pgtap_crea_magazzino('PGT-L2I-N', false);
    SELECT t.id INTO v_tipo FROM config.tipi_ubicazione t ORDER BY t.id LIMIT 1;
    INSERT INTO magazzino.ubicazioni (magazzino_id, codice, tipo_id) VALUES (v_mag, 'UX', v_tipo) RETURNING id INTO v_ux;
    INSERT INTO magazzino.ubicazioni (magazzino_id, codice, tipo_id) VALUES (v_mag, 'UY', v_tipo) RETURNING id INTO v_uy;
    v_art := dbops.fn_pgtap_crea_articolo('PGT-L2I-ART', true, false, false);
    v_lot := dbops.fn_pgtap_crea_articolo('PGT-L2I-LOT', true, true, false);
    v_nog := dbops.fn_pgtap_crea_articolo('PGT-L2I-NO', false, false, false);
    INSERT INTO magazzino.lotti (articolo_id, codice, data_arrivo) VALUES (v_lot, 'PGT-L2I-L1', script.fn_data_operativa()) RETURNING id INTO v_l1;
    INSERT INTO magazzino.lotti (articolo_id, codice, data_arrivo) VALUES (v_lot, 'PGT-L2I-L2', script.fn_data_operativa()) RETURNING id INTO v_l2;
    INSERT INTO _fix VALUES (v_mag, v_no, v_ux, v_uy, v_art, v_lot, v_nog, v_l1, v_l2);
END $fix$;

-- ============================================================
-- 1-4 Il primo conteggio
-- ============================================================
CREATE TEMP TABLE _inv1 AS SELECT NULL::bigint AS id;
DO $i$ DECLARE v_id bigint; BEGIN
    INSERT INTO magazzino.inventari (magazzino_id, data) SELECT mag, script.fn_data_operativa() - 1 FROM _fix RETURNING id INTO v_id;
    INSERT INTO magazzino.inventari_righe (inventario_id, articolo_id, qta_contata, ubicazione_id, costo_unitario) SELECT v_id, art, 10, ux, 7 FROM _fix;
    UPDATE magazzino.inventari SET stato_mag_inventario = 'CONFIRM' WHERE id = v_id;
    UPDATE _inv1 SET id = v_id;
END $i$;

SELECT is(
    (SELECT (p.esito, p.causale_codice_interno, trim_scale(p.qta_sistema), trim_scale(p.delta))::text FROM magazzino.fn_inventario_piano((SELECT id FROM _inv1)) p),
    '(INV_INIZIALE,INV_INIZIALE,0,10)',
    '1) primo conteggio su merce mai movimentata: il piano dice INV_INIZIALE, sistema 0, delta 10');

CREATE TEMP TABLE _post1 AS SELECT * FROM magazzino.fn_posta_inventario((SELECT id FROM _inv1));
SELECT is(
    (SELECT (count(*), max(trim_scale(qta)), (SELECT stato_mag_inventario FROM magazzino.inventari WHERE id = (SELECT id FROM _inv1)))::text FROM _post1),
    '(1,10,POSTED)',
    '2) il posting scrive un movimento di 10 e porta la testata a POSTED');
SELECT is((SELECT trim_scale(qta_sistema)::text FROM magazzino.inventari_righe WHERE inventario_id = (SELECT id FROM _inv1)), '0',
    '3) qta_sistema = 0 scritto sulla riga');
SELECT is(
    (SELECT (trim_scale(m.costo_unitario), c.codice_interno, script.fn_giorno_operativo(m.data_mov) = script.fn_data_operativa() - 1)::text FROM magazzino.movimenti m JOIN magazzino.causali c ON c.id = m.causale_id WHERE m.id = (SELECT movimento_id FROM _post1)),
    '(7,INV_INIZIALE,t)',
    '4) il movimento porta il costo della riga, la causale INV_INIZIALE e la data dell''inventario');

-- ============================================================
-- 5-9 Il caso di Tid: contata in UY, a registro in UX
-- ============================================================
CREATE TEMP TABLE _inv2 AS SELECT NULL::bigint AS id;
DO $i$ DECLARE v_id bigint; BEGIN
    INSERT INTO magazzino.inventari (magazzino_id) SELECT mag FROM _fix RETURNING id INTO v_id;
    INSERT INTO magazzino.inventari_righe (inventario_id, articolo_id, qta_contata, ubicazione_id) SELECT v_id, art, 12, uy FROM _fix;
    UPDATE magazzino.inventari SET stato_mag_inventario = 'CONFIRM' WHERE id = v_id;
    UPDATE _inv2 SET id = v_id;
END $i$;
SELECT is(
    (SELECT string_agg(u.codice || ':' || p.esito || ':' || trim_scale(p.qta_sistema)::text, ' ' ORDER BY p.riga_id NULLS LAST)
       FROM magazzino.fn_inventario_piano((SELECT id FROM _inv2)) p JOIN magazzino.ubicazioni u ON u.id = p.ubicazione_id),
    'UY:RETT_POS:0 UX:NON_CONTATA:10',
    '5) contata in UY con 10 in UX: (UY) RETT_POS e (UX) NON_CONTATA — informazione, non blocco');

UPDATE magazzino.inventari SET stato_mag_inventario = 'DRAFT' WHERE id = (SELECT id FROM _inv2);
INSERT INTO magazzino.inventari_righe (inventario_id, articolo_id, qta_contata, ubicazione_id) SELECT id, (SELECT art FROM _fix), 10, (SELECT ux FROM _fix) FROM _inv2;
INSERT INTO magazzino.inventari_righe (inventario_id, articolo_id, qta_contata, ubicazione_id) SELECT id, (SELECT art_no FROM _fix), 3, (SELECT ux FROM _fix) FROM _inv2;
UPDATE magazzino.inventari SET stato_mag_inventario = 'CONFIRM' WHERE id = (SELECT id FROM _inv2);
SELECT is(
    (SELECT string_agg(p.esito || COALESCE(':' || p.posting_blocco_reason, ''), ' ' ORDER BY p.riga_id NULLS LAST)
       FROM magazzino.fn_inventario_piano((SELECT id FROM _inv2)) p WHERE p.riga_id IS NOT NULL),
    'RETT_POS INVARIATA NON_POSTABILE:ARTICOLO_NON_GESTITO',
    '6) riaperto e completato: UY RETT_POS, UX INVARIATA, e la riga non gestita NON_POSTABILE col reason');

SELECT throws_like(
    $$ SELECT * FROM magazzino.fn_posta_inventario((SELECT id FROM _inv2)) $$,
    '%non è gestito a magazzino%',
    '7a) il posting rifiuta col primo motivo della STESSA check');
SELECT is(
    (SELECT ((SELECT stato_mag_inventario FROM magazzino.inventari WHERE id = (SELECT id FROM _inv2)),
             (SELECT count(*) FROM magazzino.movimenti m WHERE m.magazzino_id = (SELECT mag FROM _fix)))::text),
    '(CONFIRM,1)',
    '7b) ...e non resta niente: testata CONFIRM, un solo movimento a registro (all-or-nothing)');

UPDATE magazzino.inventari SET stato_mag_inventario = 'DRAFT' WHERE id = (SELECT id FROM _inv2);
DELETE FROM magazzino.inventari_righe WHERE inventario_id = (SELECT id FROM _inv2) AND articolo_id = (SELECT art_no FROM _fix);
UPDATE magazzino.inventari SET stato_mag_inventario = 'CONFIRM' WHERE id = (SELECT id FROM _inv2);
-- ⚠️ Il verbo in un'istruzione SEPARATA (memoria pgtap_stessa_istruzione_snapshot).
CREATE TEMP TABLE _post2 AS SELECT * FROM magazzino.fn_posta_inventario((SELECT id FROM _inv2));
SELECT is(
    (SELECT (count(*), max(trim_scale(qta)), (SELECT trim_scale(g.qta) FROM magazzino.vw_giacenza g WHERE g.magazzino_id = (SELECT mag FROM _fix) AND g.articolo_id = (SELECT art FROM _fix)))::text
       FROM _post2),
    '(1,12,22)',
    '8) tolta la riga cattiva: una riga postata (UY 12), UX invariata, giacenza 22');
SELECT is(
    (SELECT string_agg(u.codice || '=' || trim_scale(r.qta_sistema)::text, ' ' ORDER BY u.codice)
       FROM magazzino.inventari_righe r JOIN magazzino.ubicazioni u ON u.id = r.ubicazione_id WHERE r.inventario_id = (SELECT id FROM _inv2)),
    'UX=10 UY=0',
    '9) qta_sistema sulle righe, dal piano');

-- ============================================================
-- 10-13 I rifiuti dell'operazione e del piano
-- ============================================================
SELECT throws_like(
    $$ SELECT * FROM magazzino.fn_posta_inventario((SELECT id FROM _inv2)) $$,
    '%Il documento è in stato POSTED: il passaggio a POSTED non è ammesso.%',
    '10) posting di nuovo: la transizione da POSTED');

CREATE TEMP TABLE _inv3 AS SELECT NULL::bigint AS id;
DO $i$ DECLARE v_id bigint; BEGIN
    INSERT INTO magazzino.inventari (magazzino_id, stato_mag_inventario) SELECT mag, 'CONFIRM' FROM _fix RETURNING id INTO v_id;
    UPDATE _inv3 SET id = v_id;
END $i$;
SELECT throws_like(
    $$ SELECT * FROM magazzino.fn_posta_inventario((SELECT id FROM _inv3)) $$,
    '%non ha righe: niente da registrare.%',
    '11) CONFIRM senza righe: E_MAG_DOCUMENTO_SENZA_RIGHE');

CREATE TEMP TABLE _inv4 AS SELECT NULL::bigint AS id;
DO $i$ DECLARE v_id bigint; BEGIN
    INSERT INTO magazzino.inventari (magazzino_id) SELECT mag FROM _fix RETURNING id INTO v_id;
    INSERT INTO magazzino.inventari_righe (inventario_id, articolo_id, qta_contata) SELECT v_id, art, 1 FROM _fix;
    UPDATE _inv4 SET id = v_id;
END $i$;
SELECT is(
    (SELECT p.esito || ':' || p.posting_blocco_reason FROM magazzino.fn_inventario_piano((SELECT id FROM _inv4)) p WHERE p.riga_id IS NOT NULL),
    'NON_POSTABILE:UBICAZIONE_OBBLIGATORIA',
    '12) riga senza ubicazione in un magazzino a ubicazioni: il piano lo dice prima (D-L2-m)');

CREATE TEMP TABLE _inv5 AS SELECT NULL::bigint AS id;
DO $i$ DECLARE v_id bigint; BEGIN
    INSERT INTO magazzino.inventari (magazzino_id) SELECT mag_no FROM _fix RETURNING id INTO v_id;
    INSERT INTO magazzino.inventari_righe (inventario_id, articolo_id, qta_contata, ubicazione_id) SELECT v_id, art, 1, ux FROM _fix;
    UPDATE _inv5 SET id = v_id;
END $i$;
SELECT is(
    (SELECT p.esito || ':' || p.posting_blocco_reason FROM magazzino.fn_inventario_piano((SELECT id FROM _inv5)) p WHERE p.riga_id IS NOT NULL),
    'NON_POSTABILE:UBICAZIONE_NON_AMMESSA',
    '13) riga con ubicazione in un magazzino senza: UBICAZIONE_NON_AMMESSA');

-- ============================================================
-- 14 La grana del lotto
-- ============================================================
CREATE TEMP TABLE _inv6 AS SELECT NULL::bigint AS id;
DO $i$ DECLARE v_id bigint; BEGIN
    -- 3 nel lotto L1 e 17 nel lotto L2 (magazzino senza ubicazioni), postati
    INSERT INTO magazzino.inventari (magazzino_id) SELECT mag_no FROM _fix RETURNING id INTO v_id;
    INSERT INTO magazzino.inventari_righe (inventario_id, articolo_id, qta_contata, lotto_id) SELECT v_id, art_lotto, 3, l1 FROM _fix;
    INSERT INTO magazzino.inventari_righe (inventario_id, articolo_id, qta_contata, lotto_id) SELECT v_id, art_lotto, 17, l2 FROM _fix;
    UPDATE magazzino.inventari SET stato_mag_inventario = 'CONFIRM' WHERE id = v_id;
    PERFORM magazzino.fn_posta_inventario(v_id);
    -- il conteggio nuovo: L1 = 5
    INSERT INTO magazzino.inventari (magazzino_id) SELECT mag_no FROM _fix RETURNING id INTO v_id;
    INSERT INTO magazzino.inventari_righe (inventario_id, articolo_id, qta_contata, lotto_id) SELECT v_id, art_lotto, 5, l1 FROM _fix;
    UPDATE magazzino.inventari SET stato_mag_inventario = 'CONFIRM' WHERE id = v_id;
    UPDATE _inv6 SET id = v_id;
END $i$;
SELECT is(
    (SELECT string_agg(p.esito || ':' || trim_scale(p.qta_sistema)::text || ':' || COALESCE(trim_scale(p.delta)::text, '-'), ' ' ORDER BY p.riga_id NULLS LAST)
       FROM magazzino.fn_inventario_piano((SELECT id FROM _inv6)) p),
    'RETT_POS:3:2 NON_CONTATA:17:-',
    '14) grana LOTTO: la riga col lotto L1 confronta L1 (3, delta 2); L2 e'' una posizione NON_CONTATA');

-- ============================================================
-- 15 Fuori perimetro
-- ============================================================
SELECT throws_like(
    $$ SELECT * FROM magazzino.fn_posta_inventario(999999999) $$,
    '%Documento 999999999 non trovato.%',
    '15a) inventario inesistente (o fuori perimetro): E_MAG_DOCUMENTO_NON_TROVATO');
SELECT is((SELECT count(*) FROM magazzino.fn_inventario_piano(999999999)), 0::bigint,
    '15b) ...e il piano risponde zero righe (il 404 lo da'' il BE sulla testata)');

SELECT * FROM finish();
ROLLBACK;
