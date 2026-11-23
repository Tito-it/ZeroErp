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
--    6) CONFIRM -> POSTED chiesto al verbo dello stato -> E_MAG_DOCUMENTO_POSTED_SOLO_DA_OPERAZIONE
--    7) ...anche con la GUC dell'operazione accesa DALL'APP: il verbo e' il proprietario, e la
--       GUC la spegne lui (fn_documento_interno_blocca): rifiutata
--   7b) attraverso il verbo fn_posta_inventario passa: GUC E proprietario, e il verbo scrive
--       anche qta_sistema sulla riga in CONFIRM (le due porte si aprono solo li')
--   Le righe:
--    8) su DRAFT si scrivono   9) in CONFIRM -> E_MAG_DOCUMENTO_RIGHE_CONGELATE
--   10) in CONFIRM con la GUC accesa DALL'APP -> congelate lo stesso (il verbo la spegne)
--   11) su POSTED -> congelate (anche la nascita)  12) su CANCEL -> congelate (rettifica)
--   Il DELETE della testata (C3):
--   13) DRAFT si elimina (le righe cascano)  14) POSTED -> E_MAG_DOCUMENTO_NON_ELIMINABILE
--   La forma:
--   15) il CHECK degli stati di inventari ha QUATTRO valori e si chiama chk_mag_inventari_stato
--   Il magazzino della testata e' IDENTITA' (R-4 del Lotto 2-bis, Tid 22-09):
--   16) le due famiglie sono dichiarate in dbops.automation_lock_columns, col loro codice
--   17) ...e il verbo di modifica non lo ammette fra i dati: E_CAMPO_NON_AMMESSO
--
-- Rev 2026-09-25 (brief-db-magazzino-verbi-con-permesso, D-V1 / P-7): la porta POSTED e le
--   righe in CONFIRM chiedono la GUC E che chi esegue sia il proprietario della tabella
--   (script.fn_is_proprietario_tabella). Il test gira come app: 7 e 10 si ribaltano (la GUC
--   accesa dall'app non apre piu'), e l'inventario del fixture arriva a POSTED dal verbo (7b),
--   con la sua riga creata in DRAFT e l'azione registra_magazzino concessa.
--
-- Rev 2026-11-23 (brief-db-magazzino-tutte-le-scritture-dal-verbo, P-5c): le scritture passano
--   dai verbi dei documenti interni (la strada dell'operatore, prima della chiusura delle
--   tabelle per l'app): i guard della tabella si provano attraverso il verbo, coi codici di
--   prima. Il 7 e il 10 provano il controesempio della GUC accesa dall'app davanti a un verbo
--   SECURITY DEFINER; il 17 il magazzino che il verbo di modifica non ammette.
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(18);

CREATE TEMP TABLE _mondo AS SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _mondo)); END $ctx$;
-- Il verbo del test 7b chiede l'azione (fn_guard_azione), che apre l'area a TUTTO: i verbi
-- dei documenti interni si chiamano direttamente.
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
    v_inv := dbops.fn_pgtap_crea_inventario(v_mag);
    -- La riga nasce in DRAFT: in CONFIRM non si potrebbe piu' scrivere, e il verbo (7b)
    -- non registra un inventario senza righe.
    PERFORM dbops.fn_pgtap_crea_riga_inventario(v_inv, v_art, 1, jsonb_build_object('costo_unitario', 7));
    v_ret := dbops.fn_pgtap_crea_rettifica(v_mag);
    INSERT INTO _fix VALUES (v_mag, v_mag_b, v_art, v_inv, v_ret);
END $fix$;

-- La matrice, sull'inventario
SELECT lives_ok($$ SELECT magazzino.fn_cambia_stato_documento_interno('INVENTARIO', (SELECT inv FROM _fix), 'CONFIRM') $$,
    '1) DRAFT -> CONFIRM');
SELECT lives_ok($$ SELECT magazzino.fn_cambia_stato_documento_interno('INVENTARIO', (SELECT inv FROM _fix), 'DRAFT') $$,
    '2) CONFIRM -> DRAFT: riapri (C13, il piano si corregge in bozza)');
-- ...e sulla rettifica, per CANCEL
SELECT lives_ok($$ SELECT magazzino.fn_cambia_stato_documento_interno('RETTIFICA', (SELECT ret FROM _fix), 'CONFIRM');
                   SELECT magazzino.fn_cambia_stato_documento_interno('RETTIFICA', (SELECT ret FROM _fix), 'CANCEL') $$,
    '3) CONFIRM -> CANCEL (rettifica: la stessa matrice)');
SELECT throws_like($$ SELECT magazzino.fn_cambia_stato_documento_interno('RETTIFICA', (SELECT ret FROM _fix), 'DRAFT') $$,
    '%Il documento è in stato CANCEL: il passaggio a DRAFT non è ammesso.%',
    '4) CANCEL e'' terminale');
SELECT throws_like($$ SELECT magazzino.fn_cambia_stato_documento_interno('INVENTARIO', (SELECT inv FROM _fix), 'POSTED') $$,
    '%Il documento è in stato DRAFT: il passaggio a POSTED non è ammesso.%',
    '5) DRAFT -> POSTED: fuori matrice (si passa da CONFIRM)');

-- La porta POSTED
SELECT magazzino.fn_cambia_stato_documento_interno('INVENTARIO', (SELECT inv FROM _fix), 'CONFIRM');
SELECT throws_like($$ SELECT magazzino.fn_cambia_stato_documento_interno('INVENTARIO', (SELECT inv FROM _fix), 'POSTED') $$,
    '%non si porta a POSTED con un aggiornamento diretto: passa dall''operazione di registrazione.%',
    '6) CONFIRM -> POSTED chiesto al verbo dello stato: E_MAG_DOCUMENTO_POSTED_SOLO_DA_OPERAZIONE');
-- La GUC accesa dentro throws_like la annulla gia' la sottotransazione del rifiuto; il
-- reset dopo e' una cintura, perche' il test 7b deve partire a GUC spenta.
SELECT throws_like($$ SELECT set_config('zeroerp.magazzino_posting_inventario', (SELECT inv::text FROM _fix), true);
                      SELECT magazzino.fn_cambia_stato_documento_interno('INVENTARIO', (SELECT inv FROM _fix), 'POSTED') $$,
    '%non si porta a POSTED con un aggiornamento diretto: passa dall''operazione di registrazione.%',
    '7) ...anche con la GUC dell''operazione accesa dall''app davanti al verbo: rifiutata (il verbo la spegne)');
SELECT set_config('zeroerp.magazzino_posting_inventario', '', true);
SELECT lives_ok($$ SELECT * FROM magazzino.fn_posta_inventario((SELECT inv FROM _fix)) $$,
    '7b) attraverso il verbo passa: GUC e proprietario, e qta_sistema scritta sulla riga in CONFIRM');

-- Le righe: un secondo inventario per gli stati DRAFT / CONFIRM
CREATE TEMP TABLE _inv2 AS SELECT NULL::bigint AS id, NULL::bigint AS riga;
DO $i$ DECLARE v_id bigint; v_r bigint; BEGIN
    v_id := dbops.fn_pgtap_crea_inventario((SELECT mag FROM _fix));
    v_r  := dbops.fn_pgtap_crea_riga_inventario(v_id, (SELECT art FROM _fix), 1);
    UPDATE _inv2 SET id = v_id, riga = v_r;
END $i$;
SELECT lives_ok($$ SELECT magazzino.fn_modifica_riga_documento_interno('INVENTARIO', (SELECT id FROM _inv2),
                          (SELECT riga FROM _inv2), '{"qta_contata": 2}') $$,
    '8) su una testata DRAFT le righe si scrivono');
SELECT magazzino.fn_cambia_stato_documento_interno('INVENTARIO', (SELECT id FROM _inv2), 'CONFIRM');
SELECT throws_like($$ SELECT magazzino.fn_modifica_riga_documento_interno('INVENTARIO', (SELECT id FROM _inv2),
                             (SELECT riga FROM _inv2), '{"qta_contata": 3}') $$,
    '%Il documento è in stato CONFIRM: le righe non si modificano più.%',
    '9) in CONFIRM: E_MAG_DOCUMENTO_RIGHE_CONGELATE');
SELECT throws_like($$ SELECT set_config('zeroerp.magazzino_posting_inventario', (SELECT id::text FROM _inv2), true);
                      SELECT magazzino.fn_modifica_riga_documento_interno('INVENTARIO', (SELECT id FROM _inv2),
                             (SELECT riga FROM _inv2), '{"qta_contata": 4}') $$,
    '%Il documento è in stato CONFIRM: le righe non si modificano più.%',
    '10) in CONFIRM con la GUC accesa dall''app davanti al verbo: congelate lo stesso');
SELECT set_config('zeroerp.magazzino_posting_inventario', '', true);
-- la riga del primo inventario (POSTED): e' congelata anche la nascita
SELECT throws_like($$ SELECT magazzino.fn_aggiungi_riga_inventario(inv, art, 1) FROM _fix $$,
    '%Il documento è in stato POSTED: le righe non si modificano più.%',
    '11) su POSTED: congelate (anche la nascita di una riga)');
SELECT throws_like($$ SELECT magazzino.fn_aggiungi_riga_rettifica(ret, art, 1) FROM _fix $$,
    '%Il documento è in stato CANCEL: le righe non si modificano più.%',
    '12) su CANCEL: congelate (rettifiche_righe, stessa funzione)');

-- L'eliminazione della testata (C3)
SELECT magazzino.fn_cambia_stato_documento_interno('INVENTARIO', (SELECT id FROM _inv2), 'DRAFT');
SELECT lives_ok($$ SELECT magazzino.fn_elimina_documento_interno('INVENTARIO', (SELECT id FROM _inv2)) $$,
    '13) una DRAFT si elimina, e le righe cascano (il guard delle righe non ferma la cascata)');
SELECT throws_like($$ SELECT magazzino.fn_elimina_documento_interno('INVENTARIO', (SELECT inv FROM _fix)) $$,
    '%Il documento è in stato POSTED: non si può eliminare, solo una bozza si elimina.%',
    '14) una POSTED non si elimina: E_MAG_DOCUMENTO_NON_ELIMINABILE');

-- La forma
-- ⚠️ Rev 2026-11-22 (20261122-40): il testo si legge da dbops.fn_pgtap_definizione_vincolo,
--   non da pg_get_constraintdef. Sulla 19 un `IN (...)` su varchar ha due testi: nato sul
--   database (la CI, un'installazione nuova) `ANY ((ARRAY['X'::character varying, ...])::text[])`,
--   riletto da un dump della 18 (dbdev, lo scratch) `ANY (ARRAY[('X'::character varying)::text, ...])`.
--   Il BB riporta il secondo al primo: si asserisce la forma del vincolo nato.
SELECT is(
    dbops.fn_pgtap_definizione_vincolo('magazzino.inventari', 'chk_mag_inventari_stato'),
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

-- La strada dell'operatore e' il verbo di modifica: il magazzino non e' fra le colonne
-- che ammette (lo decide la nascita). Il lock resta per chi scrive da proprietario.
SELECT is(
    dbops.fn_pgtap_codice_errore($$SELECT magazzino.fn_modifica_documento_interno('INVENTARIO', f.inv,
                                          jsonb_build_object('magazzino_id', f.mag_b)) FROM _fix f$$),
    'E_CAMPO_NON_AMMESSO',
    '17) il verbo di modifica non sposta il documento: magazzino_id non e'' fra i dati ammessi');

SELECT * FROM finish();
ROLLBACK;
