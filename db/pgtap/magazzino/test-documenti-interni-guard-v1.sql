-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: i due guard di famiglia dei documenti interni (D-L2-h, C3, C13):
--   trgfn_documento_interno_guard_transizione (matrice, porta POSTED, DELETE)
--   e trgfn_documento_interno_righe_guard_testata (righe congelate). Brief:
--   brief-db-magazzino-lotto-2-motore, sezione 3, 4.5, 7.
--
-- Elenco test (plan 18):
--   La matrice (la stessa per le due famiglie, senza COUNTING):
--    1) DRAFT -> CONFIRM passa   2) CONFIRM -> DRAFT passa (riapri, C13)
--    3) CONFIRM -> CANCEL passa  4) CANCEL -> DRAFT -> E_MAG_DOCUMENTO_TRANSIZIONE_NON_AMMESSA (terminale)
--    5) DRAFT -> POSTED -> TRANSIZIONE_NON_AMMESSA (si passa da CONFIRM)
--   La porta POSTED:
--    6) CONFIRM -> POSTED con UPDATE diretto -> E_MAG_DOCUMENTO_POSTED_SOLO_DA_OPERAZIONE
--    7) ...anche con la GUC dell'operazione accesa DALL'APP: rifiutata (D-V1, la GUC da sola non apre)
--   7b) attraverso il verbo fn_posta_inventario passa: GUC E proprietario, e il verbo scrive
--       anche qta_sistema sulla riga in CONFIRM (le due porte si aprono solo li')
--   Le righe:
--    8) su DRAFT si scrivono   9) in CONFIRM scritte dall'app -> E_MAG_DOCUMENTO_RIGHE_CONGELATE
--   10) in CONFIRM con la GUC accesa DALL'APP -> congelate lo stesso (D-V1)
--   11) su POSTED -> congelate (UPDATE)  12) su CANCEL -> congelate (DELETE)
--   Il DELETE della testata (C3):
--   13) DRAFT si elimina (le righe cascano)  14) POSTED -> E_MAG_DOCUMENTO_NON_ELIMINABILE
--   La forma:
--   15) il CHECK degli stati di inventari ha QUATTRO valori e si chiama chk_mag_inventari_stato
--   Il magazzino della testata e' IDENTITA' (R-4 del Lotto 2-bis, Tid 22-09):
--   16) le due famiglie sono dichiarate in dbops.automation_lock_columns, col loro codice
--   17) ...e il lock generato rifiuta lo spostamento — skip se l'automazione non l'ha ancora scritto
--
-- Rev 2026-09-25 (brief-db-magazzino-verbi-con-permesso, D-V1 / P-7): la porta POSTED e le
--   righe in CONFIRM chiedono la GUC E che chi esegue sia il proprietario della tabella
--   (script.fn_is_proprietario_tabella). Il test gira come app: 7 e 10 si ribaltano (la GUC
--   accesa dall'app non apre piu'), e l'inventario del fixture arriva a POSTED dal verbo (7b),
--   con la sua riga creata in DRAFT e l'azione registra_magazzino concessa.
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(18);

CREATE TEMP TABLE _mondo AS SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _mondo)); END $ctx$;
-- Il verbo del test 7b chiede l'azione (fn_guard_azione): la si concede all'operatore del mondo.
DO $az$ BEGIN PERFORM dbops.fn_pgtap_concedi_azione((SELECT auth_user_id FROM _mondo), 'registra_magazzino'); END $az$;

-- ⚠️ Due magazzini, e il secondo serve al test 17: per provare che un documento
--   NON si sposta serve un posto dove non deve poter andare.
CREATE TEMP TABLE _fix (mag bigint, mag_b bigint, art uuid, inv bigint, ret bigint);
DO $fix$
DECLARE v_mag bigint; v_mag_b bigint; v_art uuid; v_inv bigint; v_ret bigint;
BEGIN
    v_mag   := dbops.fn_pgtap_crea_magazzino('PGT-L2G-A', false);
    v_mag_b := dbops.fn_pgtap_crea_magazzino('PGT-L2G-B', false);
    v_art := dbops.fn_pgtap_crea_articolo('PGT-L2G-ART', true, false, false);
    INSERT INTO magazzino.inventari (magazzino_id) VALUES (v_mag) RETURNING id INTO v_inv;
    -- La riga nasce in DRAFT: in CONFIRM l'app non la potrebbe piu' scrivere, e il verbo (7b)
    -- non registra un inventario senza righe.
    INSERT INTO magazzino.inventari_righe (inventario_id, articolo_id, qta_contata, costo_unitario)
    VALUES (v_inv, v_art, 1, 7);
    INSERT INTO magazzino.rettifiche (magazzino_id) VALUES (v_mag) RETURNING id INTO v_ret;
    INSERT INTO _fix VALUES (v_mag, v_mag_b, v_art, v_inv, v_ret);
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
-- La GUC accesa dentro throws_like la annulla gia' la sottotransazione del rifiuto; il
-- reset dopo e' una cintura, perche' il test 7b deve partire a GUC spenta.
SELECT throws_like($$ SELECT set_config('zeroerp.magazzino_posting_inventario', (SELECT inv::text FROM _fix), true);
                      UPDATE magazzino.inventari SET stato_mag_inventario = 'POSTED' WHERE id = (SELECT inv FROM _fix) $$,
    '%non si porta a POSTED con un aggiornamento diretto: passa dall''operazione di registrazione.%',
    '7) ...anche con la GUC dell''operazione accesa dall''app: rifiutata (D-V1, la GUC da sola non apre)');
SELECT set_config('zeroerp.magazzino_posting_inventario', '', true);
SELECT lives_ok($$ SELECT * FROM magazzino.fn_posta_inventario((SELECT inv FROM _fix)) $$,
    '7b) attraverso il verbo passa: GUC e proprietario, e qta_sistema scritta sulla riga in CONFIRM');

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
SELECT throws_like($$ SELECT set_config('zeroerp.magazzino_posting_inventario', (SELECT id::text FROM _inv2), true);
                      UPDATE magazzino.inventari_righe SET qta_sistema = 0 WHERE id = (SELECT riga FROM _inv2) $$,
    '%Il documento è in stato CONFIRM: le righe non si modificano più.%',
    '10) in CONFIRM con la GUC accesa dall''app: congelate lo stesso (D-V1)');
SELECT set_config('zeroerp.magazzino_posting_inventario', '', true);
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

-- ============================================================
-- 16-17 Il magazzino della testata non si sposta (R-4)
-- ============================================================
-- ⛔ La sede e' il LOCK DI COLONNA, non un ramo nel guard di famiglia: un
--   documento che cambia magazzino ha anche le RIGHE (che restano a nominare
--   ubicazioni di la') e il PIANO (che confronta la giacenza di qua). Un ramo
--   nel guard chiuderebbe un caso su tre — stessa lezione di
--   ubicazioni.magazzino_id, 2026-09-21.
SELECT is(
    (SELECT string_agg(l.target_table || ':' || l.error_code, ' ' ORDER BY l.target_table)
       FROM dbops.automation_lock_columns l
      WHERE l.target_schema = 'magazzino'
        AND l.target_table IN ('inventari', 'rettifiche')
        AND l.column_name = 'magazzino_id'
        AND l.enabled),
    'inventari:E_MAG_DOCUMENTO_MAGAZZINO_IMMUTABILE rettifiche:E_MAG_DOCUMENTO_MAGAZZINO_IMMUTABILE',
    '16) le due famiglie dichiarano magazzino_id immutabile, con lo stesso codice');

-- Il trigger lo genera l'automazione: si cerca per FUNZIONE e argomenti, mai per nome.
SELECT CASE
    WHEN EXISTS (SELECT 1 FROM pg_trigger t JOIN pg_proc p ON p.oid = t.tgfoid
                  WHERE t.tgrelid = 'magazzino.inventari'::regclass AND NOT t.tgisinternal
                    AND p.proname = 'trgfn_lock_columns'
                    AND pg_get_triggerdef(t.oid) LIKE '%''magazzino_id''%')
    THEN throws_like(
        $$ UPDATE magazzino.inventari SET magazzino_id = (SELECT mag_b FROM _fix) WHERE id = (SELECT inv FROM _fix) $$,
        '%Il magazzino di un inventario o di una rettifica non si cambia (colonna magazzino_id)%',
        '17) il lock generato rifiuta lo spostamento del documento')
    ELSE skip('17) lock su magazzino_id non ancora generato (ci_apply / job automations_lock_columns): niente da misurare', 1)
END;

SELECT * FROM finish();
ROLLBACK;
