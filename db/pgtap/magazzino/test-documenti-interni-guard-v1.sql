-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: i due guard di famiglia dei documenti interni (D-L2-h, C3, C13):
--   trgfn_documento_interno_guard_transizione (matrice, porta POSTED, DELETE)
--   e trgfn_documento_interno_righe_guard_testata (righe congelate). Brief:
--   brief-db-magazzino-lotto-2-motore, sezione 3, 4.5, 7.
--
-- Elenco test (plan 15):
--   La matrice (la stessa per le due famiglie, senza COUNTING):
--    1) DRAFT -> CONFIRM passa   2) CONFIRM -> DRAFT passa (riapri, C13)
--    3) CONFIRM -> CANCEL passa  4) CANCEL -> DRAFT -> E_MAG_DOCUMENTO_TRANSIZIONE_NON_AMMESSA (terminale)
--    5) DRAFT -> POSTED -> TRANSIZIONE_NON_AMMESSA (si passa da CONFIRM)
--   La porta POSTED:
--    6) CONFIRM -> POSTED con UPDATE diretto -> E_MAG_DOCUMENTO_POSTED_SOLO_DA_OPERAZIONE
--    7) ...e con la GUC dell'operazione (set_config transazionale) passa: e' cosi' che fn_posta_* la apre
--   Le righe:
--    8) su DRAFT si scrivono   9) in CONFIRM scritte dall'app -> E_MAG_DOCUMENTO_RIGHE_CONGELATE
--   10) in CONFIRM con la GUC -> passa (e' l'operazione che fissa qta_sistema)
--   11) su POSTED -> congelate (UPDATE)  12) su CANCEL -> congelate (DELETE)
--   Il DELETE della testata (C3):
--   13) DRAFT si elimina (le righe cascano)  14) POSTED -> E_MAG_DOCUMENTO_NON_ELIMINABILE
--   La forma:
--   15) il CHECK degli stati di inventari ha QUATTRO valori e si chiama chk_mag_inventari_stato
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(15);

CREATE TEMP TABLE _mondo AS SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _mondo)); END $ctx$;

CREATE TEMP TABLE _fix (mag bigint, art uuid, inv bigint, ret bigint);
DO $fix$
DECLARE v_mag bigint; v_art uuid; v_inv bigint; v_ret bigint;
BEGIN
    v_mag := dbops.fn_pgtap_crea_magazzino('PGT-L2G-A', false);
    v_art := dbops.fn_pgtap_crea_articolo('PGT-L2G-ART', true, false, false);
    INSERT INTO magazzino.inventari (magazzino_id) VALUES (v_mag) RETURNING id INTO v_inv;
    INSERT INTO magazzino.rettifiche (magazzino_id) VALUES (v_mag) RETURNING id INTO v_ret;
    INSERT INTO _fix VALUES (v_mag, v_art, v_inv, v_ret);
END $fix$;

-- La matrice, sull'inventario
SELECT lives_ok($$ UPDATE magazzino.inventari SET stato_mag_inventario = 'CONFIRM' WHERE id = (SELECT inv FROM _fix) $$,
    '1) DRAFT -> CONFIRM');
SELECT lives_ok($$ UPDATE magazzino.inventari SET stato_mag_inventario = 'DRAFT' WHERE id = (SELECT inv FROM _fix) $$,
    '2) CONFIRM -> DRAFT: riapri (C13, il piano si corregge in bozza)');
-- ...e sulla rettifica, per CANCEL
SELECT lives_ok($$ UPDATE magazzino.rettifiche SET stato_mag_rettifiche = 'CONFIRM' WHERE id = (SELECT ret FROM _fix);
                   UPDATE magazzino.rettifiche SET stato_mag_rettifiche = 'CANCEL'  WHERE id = (SELECT ret FROM _fix) $$,
    '3) CONFIRM -> CANCEL (rettifica: la stessa matrice)');
SELECT throws_like($$ UPDATE magazzino.rettifiche SET stato_mag_rettifiche = 'DRAFT' WHERE id = (SELECT ret FROM _fix) $$,
    '%Il documento è in stato CANCEL: il passaggio a DRAFT non è ammesso.%',
    '4) CANCEL e'' terminale');
SELECT throws_like($$ UPDATE magazzino.inventari SET stato_mag_inventario = 'POSTED' WHERE id = (SELECT inv FROM _fix) $$,
    '%Il documento è in stato DRAFT: il passaggio a POSTED non è ammesso.%',
    '5) DRAFT -> POSTED: fuori matrice (si passa da CONFIRM)');

-- La porta POSTED
UPDATE magazzino.inventari SET stato_mag_inventario = 'CONFIRM' WHERE id = (SELECT inv FROM _fix);
SELECT throws_like($$ UPDATE magazzino.inventari SET stato_mag_inventario = 'POSTED' WHERE id = (SELECT inv FROM _fix) $$,
    '%non si porta a POSTED con un aggiornamento diretto: passa dall''operazione di registrazione.%',
    '6) CONFIRM -> POSTED con un UPDATE diretto: E_MAG_DOCUMENTO_POSTED_SOLO_DA_OPERAZIONE');
SELECT lives_ok($$ SELECT set_config('zeroerp.magazzino_posting_inventario', (SELECT inv::text FROM _fix), true);
                   UPDATE magazzino.inventari SET stato_mag_inventario = 'POSTED' WHERE id = (SELECT inv FROM _fix);
                   SELECT set_config('zeroerp.magazzino_posting_inventario', '', true) $$,
    '7) ...e con la GUC dell''operazione passa (e'' cosi'' che fn_posta_* apre la porta)');

-- Le righe: un secondo inventario per gli stati DRAFT / CONFIRM
CREATE TEMP TABLE _inv2 AS SELECT NULL::bigint AS id, NULL::bigint AS riga;
DO $i$ DECLARE v_id bigint; v_r bigint; BEGIN
    INSERT INTO magazzino.inventari (magazzino_id) SELECT mag FROM _fix RETURNING id INTO v_id;
    INSERT INTO magazzino.inventari_righe (inventario_id, articolo_id, qta_contata) SELECT v_id, art, 1 FROM _fix RETURNING id INTO v_r;
    UPDATE _inv2 SET id = v_id, riga = v_r;
END $i$;
SELECT lives_ok($$ UPDATE magazzino.inventari_righe SET qta_contata = 2 WHERE id = (SELECT riga FROM _inv2) $$,
    '8) su una testata DRAFT le righe si scrivono');
UPDATE magazzino.inventari SET stato_mag_inventario = 'CONFIRM' WHERE id = (SELECT id FROM _inv2);
SELECT throws_like($$ UPDATE magazzino.inventari_righe SET qta_contata = 3 WHERE id = (SELECT riga FROM _inv2) $$,
    '%Il documento è in stato CONFIRM: le righe non si modificano più.%',
    '9) in CONFIRM scritte dall''app: E_MAG_DOCUMENTO_RIGHE_CONGELATE');
SELECT lives_ok($$ SELECT set_config('zeroerp.magazzino_posting_inventario', (SELECT id::text FROM _inv2), true);
                   UPDATE magazzino.inventari_righe SET qta_sistema = 0 WHERE id = (SELECT riga FROM _inv2);
                   SELECT set_config('zeroerp.magazzino_posting_inventario', '', true) $$,
    '10) in CONFIRM con la GUC dell''operazione: passa (e'' lei a fissare qta_sistema)');
-- la riga del primo inventario (POSTED): serve una riga; e' congelata anche l'INSERT
SELECT throws_like($$ INSERT INTO magazzino.inventari_righe (inventario_id, articolo_id, qta_contata) SELECT inv, art, 1 FROM _fix $$,
    '%Il documento è in stato POSTED: le righe non si modificano più.%',
    '11) su POSTED: congelate (anche l''INSERT)');
SELECT throws_like($$ INSERT INTO magazzino.rettifiche_righe (rettifica_id, articolo_id, qta_delta) SELECT ret, art, 1 FROM _fix $$,
    '%Il documento è in stato CANCEL: le righe non si modificano più.%',
    '12) su CANCEL: congelate (rettifiche_righe, stessa funzione)');

-- Il DELETE della testata (C3)
UPDATE magazzino.inventari SET stato_mag_inventario = 'DRAFT' WHERE id = (SELECT id FROM _inv2);
SELECT lives_ok($$ DELETE FROM magazzino.inventari WHERE id = (SELECT id FROM _inv2) $$,
    '13) una DRAFT si elimina, e le righe cascano (il guard delle righe non ferma la cascata)');
SELECT throws_like($$ DELETE FROM magazzino.inventari WHERE id = (SELECT inv FROM _fix) $$,
    '%Il documento è in stato POSTED: non si può eliminare, solo una bozza si elimina.%',
    '14) una POSTED non si elimina: E_MAG_DOCUMENTO_NON_ELIMINABILE');

-- La forma
SELECT is(
    (SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid = 'magazzino.inventari'::regclass AND conname = 'chk_mag_inventari_stato'),
    'CHECK (((stato_mag_inventario)::text = ANY ((ARRAY[''DRAFT''::character varying, ''CONFIRM''::character varying, ''POSTED''::character varying, ''CANCEL''::character varying])::text[])))',
    '15) il CHECK degli stati ha quattro valori e si chiama chk_mag_inventari_stato (COUNTING e'' uscito, D-L2-h)');

SELECT * FROM finish();
ROLLBACK;
