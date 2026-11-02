-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: fn_posta_inventario e fn_posta_rettifica sono VERBI (20260924-41):
--   applicano registra_magazzino nella prima riga e, girando come proprietario,
--   rimettono il perimetro col predicato della policy. Brief:
--   brief-db-magazzino-verbi-con-permesso, sezioni 2.2 e 3.1.
--
-- Elenco test (plan 11):
--   Il permesso
--    1) operatore senza registra_magazzino: inventario proprio -> E_PERMESSO_NEGATO
--    2) ...e non resta niente: testata CONFIRM, nessun movimento
--    3) operatore senza l'azione: rettifica propria -> E_PERMESSO_NEGATO
--   Il perimetro (con l'azione concessa)
--    4) inventario di un ALTRO emittente -> «Documento ... non trovato» (come sotto RLS)
--    5) rettifica di un altro emittente -> idem
--    6) ...e i documenti dell'altro emittente restano CONFIRM, senza movimenti (visti dal suo contesto)
--   Chi agisce
--    7) sessione senza identita' -> E_PERMESSO_NEGATO
--    8) veste CLIENTE_PORTALE -> E_PERMESSO_NEGATO
--   Il caso felice
--    9) con l'azione e nel perimetro: l'inventario si registra (POSTED, un movimento)
--   La forma
--   10) entrambi SECURITY DEFINER con search_path bloccato
--   11) entrambi chiamano script.fn_guard_azione con 'registra_magazzino'
--
-- ⚠️ Gira come l'APPLICAZIONE: i documenti dell'altro emittente si costruiscono
--   nel SUO contesto (la RLS lo pretende), e il tentativo si fa nel contesto di A.
--   Operatori COSTRUITI (fn_pgtap_crea_emittente_operatore): tecnici, non super
--   admin, senza azioni — il permesso lo concede il test.
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(11);

-- ============================================================
-- Fixture: B (l'altro emittente) con un inventario e una rettifica CONFIRM
-- ============================================================
CREATE TEMP TABLE _b AS SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _b)); END $ctx$;
CREATE TEMP TABLE _fb (mag bigint, art uuid, inv bigint, ret bigint);
DO $fix$
DECLARE v_mag bigint; v_art uuid; v_inv bigint; v_ret bigint;
BEGIN
    v_mag := dbops.fn_pgtap_crea_magazzino('PGT-VRB-B', false);
    v_art := dbops.fn_pgtap_crea_articolo('PGT-VRB-ARTB', true, false, false);
    INSERT INTO magazzino.inventari (magazzino_id) VALUES (v_mag) RETURNING id INTO v_inv;
    INSERT INTO magazzino.inventari_righe (inventario_id, articolo_id, qta_contata, costo_unitario) VALUES (v_inv, v_art, 4, 2);
    UPDATE magazzino.inventari SET stato_mag_inventario = 'CONFIRM' WHERE id = v_inv;
    INSERT INTO magazzino.rettifiche (magazzino_id) VALUES (v_mag) RETURNING id INTO v_ret;
    INSERT INTO magazzino.rettifiche_righe (rettifica_id, articolo_id, qta_delta, costo_unitario) VALUES (v_ret, v_art, 2, 3);
    UPDATE magazzino.rettifiche SET stato_mag_rettifiche = 'CONFIRM' WHERE id = v_ret;
    INSERT INTO _fb VALUES (v_mag, v_art, v_inv, v_ret);
END $fix$;

-- ============================================================
-- Fixture: A (chi agisce) con un inventario e una rettifica CONFIRM
-- ============================================================
CREATE TEMP TABLE _a AS SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _a)); END $ctx$;
CREATE TEMP TABLE _fa (mag bigint, art uuid, inv bigint, ret bigint);
DO $fix$
DECLARE v_mag bigint; v_art uuid; v_inv bigint; v_ret bigint;
BEGIN
    v_mag := dbops.fn_pgtap_crea_magazzino('PGT-VRB-A', false);
    v_art := dbops.fn_pgtap_crea_articolo('PGT-VRB-ARTA', true, false, false);
    INSERT INTO magazzino.inventari (magazzino_id) VALUES (v_mag) RETURNING id INTO v_inv;
    INSERT INTO magazzino.inventari_righe (inventario_id, articolo_id, qta_contata, costo_unitario) VALUES (v_inv, v_art, 10, 7);
    UPDATE magazzino.inventari SET stato_mag_inventario = 'CONFIRM' WHERE id = v_inv;
    INSERT INTO magazzino.rettifiche (magazzino_id) VALUES (v_mag) RETURNING id INTO v_ret;
    INSERT INTO magazzino.rettifiche_righe (rettifica_id, articolo_id, qta_delta, costo_unitario) VALUES (v_ret, v_art, 3, 9);
    UPDATE magazzino.rettifiche SET stato_mag_rettifiche = 'CONFIRM' WHERE id = v_ret;
    INSERT INTO _fa VALUES (v_mag, v_art, v_inv, v_ret);
END $fix$;

-- ============================================================
-- 1-3 Il permesso
-- ============================================================
SELECT throws_like(
    $$ SELECT * FROM magazzino.fn_posta_inventario((SELECT inv FROM _fa)) $$,
    '%Non hai i permessi per questa operazione%',
    '1) senza registra_magazzino: l''inventario proprio non si registra (E_PERMESSO_NEGATO)');
SELECT is(
    (SELECT ((SELECT stato_mag_inventario FROM magazzino.inventari WHERE id = (SELECT inv FROM _fa)),
             (SELECT count(*) FROM magazzino.movimenti m WHERE m.magazzino_id = (SELECT mag FROM _fa)))::text),
    '(CONFIRM,0)',
    '2) ...e non resta niente: testata CONFIRM, nessun movimento');
SELECT throws_like(
    $$ SELECT * FROM magazzino.fn_posta_rettifica((SELECT ret FROM _fa)) $$,
    '%Non hai i permessi per questa operazione%',
    '3) senza registra_magazzino: la rettifica propria non si registra');

-- ============================================================
-- 4-6 Il perimetro, con l'azione concessa
-- ============================================================
DO $az$ BEGIN PERFORM dbops.fn_pgtap_concedi_azione((SELECT auth_user_id FROM _a), 'registra_magazzino'); END $az$;

SELECT throws_like(
    $$ SELECT * FROM magazzino.fn_posta_inventario((SELECT inv FROM _fb)) $$,
    '%Documento %non trovato%',
    '4) inventario di un altro emittente: non trovato — il predicato della policy, nella WHERE del FOR UPDATE');
SELECT throws_like(
    $$ SELECT * FROM magazzino.fn_posta_rettifica((SELECT ret FROM _fb)) $$,
    '%Documento %non trovato%',
    '5) rettifica di un altro emittente: non trovata');

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _b)); END $ctx$;
SELECT is(
    (SELECT ((SELECT stato_mag_inventario FROM magazzino.inventari WHERE id = (SELECT inv FROM _fb)),
             (SELECT stato_mag_rettifiche FROM magazzino.rettifiche WHERE id = (SELECT ret FROM _fb)),
             (SELECT count(*) FROM magazzino.movimenti m WHERE m.magazzino_id = (SELECT mag FROM _fb)))::text),
    '(CONFIRM,CONFIRM,0)',
    '6) visti dal contesto di B: i suoi documenti restano CONFIRM, nessun movimento');
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _a)); END $ctx$;

-- ============================================================
-- 7-8 Chi agisce
-- ============================================================
SELECT set_config('app.current_user_id', '', true);
SELECT throws_like(
    $$ SELECT * FROM magazzino.fn_posta_inventario((SELECT inv FROM _fa)) $$,
    '%Non hai i permessi per questa operazione%',
    '7) sessione senza identita'': E_PERMESSO_NEGATO');
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _a)); END $ctx$;

SELECT set_config('app.ruolo_applicativo', 'CLIENTE_PORTALE', true);
SELECT throws_like(
    $$ SELECT * FROM magazzino.fn_posta_inventario((SELECT inv FROM _fa)) $$,
    '%Non hai i permessi per questa operazione%',
    '8) veste CLIENTE_PORTALE: E_PERMESSO_NEGATO');
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _a)); END $ctx$;

-- ============================================================
-- 9 Il caso felice
-- ============================================================
CREATE TEMP TABLE _post AS SELECT * FROM magazzino.fn_posta_inventario((SELECT inv FROM _fa));
SELECT is(
    (SELECT ((SELECT count(*) FROM _post),
             (SELECT stato_mag_inventario FROM magazzino.inventari WHERE id = (SELECT inv FROM _fa)))::text),
    '(1,POSTED)',
    '9) con l''azione e nel perimetro: l''inventario si registra (un movimento, testata POSTED)');

-- ============================================================
-- 10-11 La forma
-- ============================================================
SELECT is(
    (SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'magazzino' AND p.proname IN ('fn_posta_inventario', 'fn_posta_rettifica')
        AND p.prosecdef AND p.proconfig::text LIKE '%search_path=pg_catalog, public, pg_temp%'),
    2::bigint,
    '10) i due verbi sono SECURITY DEFINER con il search_path bloccato');
SELECT is(
    (SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'magazzino' AND p.proname IN ('fn_posta_inventario', 'fn_posta_rettifica')
        AND p.prosrc LIKE '%script.fn_guard_azione(v_utente, ''registra_magazzino'')%'),
    2::bigint,
    '11) i due verbi applicano registra_magazzino con script.fn_guard_azione');

SELECT * FROM finish();
ROLLBACK;
