-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- pgtap-runner: owner
-- pgtap-runner-motivo: il test scrive righe nel giornale dei job
--   (maintenance.job_run_log) e chiama maintenance.fn_run_and_log: sono
--   scritture che il ruolo applicativo non fa e non deve fare (il giornale lo
--   legge soltanto). Tutto in transazione, annullato.
--
-- Test: il giornale dei job dice con che ruolo e' girata ogni corsa, e il
--       presidio «nessun superuser al lavoro» (D-5)
-- Brief: brief-db-ruoli-di-sistema §7 D-5
-- ChangeSet: 20261015-01 (colonna) · -02 (fn_run_and_log) · -04 (vista)
--
-- Elenco test (plan 8):
--  1) la colonna ruolo_sessione c'e', nullable e SENZA default
--  2) ⭐ una corsa registrata da fn_run_and_log porta session_user
--  3) ⭐ anche la riga SALTATA (lock occupato) porta session_user
--  4) ⛔ la vista prende l'ULTIMA corsa di un processo fatta da un superuser
--  5) ⛔ e non quella di un processo la cui ultima corsa e' di un non-superuser,
--     anche se prima ce n'era una da superuser
--  6) ⛔ ne' una corsa senza ruolo registrato (NULL), ne' il ruolo di chi non
--     esiste piu': «non registrato» non e' un guasto
--  7) il presidio e' a catalogo: ZERO, chi agisce il SISTEMISTA
--  8) zeroerp_app la puo' leggere (il pannello e il digest la leggono come app)
--
-- ── Perche' la colonna non ha default ─────────────────────────────────
--   La riga di una corsa FALLITA la scrive maintenance.fn_job_run_log_failure
--   via dblink, in un'altra sessione: un default `session_user` direbbe il ruolo
--   del canale di log. Quella funzione e' di un superuser e si aggiorna col
--   provision-post (20261015-03): non la si chiama da qui, perche' la riga che
--   scrive sopravvive al ROLLBACK (vedi test-job-run-log-failure-out-of-tx). Il
--   suo percorso e' provato da capo a fondo nel brief (§14).
--
-- ── Perche' la vista guarda solo «superuser» ──────────────────────────
--   Le procedure dei job sono chiamabili solo da proprietario, zeroerp_job e
--   superuser (EXECUTE tolto a PUBLIC, test-proc-job-definer-v1), e il giornale
--   non distingue pgAgent da ci_apply. Si giudica da rolsuper, mai dal nome: il
--   test usa `postgres` (superuser in ogni installazione PostgreSQL) e
--   `zeroerp_app` (mai superuser), ma la vista non li nomina.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(8);

-- ============================================================
-- 1. La colonna
-- ============================================================
SELECT is(
    (SELECT a.attnotnull::text || '/' || (d.adbin IS NOT NULL)::text
       FROM pg_catalog.pg_attribute a
       LEFT JOIN pg_catalog.pg_attrdef d ON d.adrelid = a.attrelid AND d.adnum = a.attnum
      WHERE a.attrelid = 'maintenance.job_run_log'::regclass
        AND a.attname = 'ruolo_sessione' AND NOT a.attisdropped),
    'false/false',
    '1. job_run_log.ruolo_sessione esiste, nullable e senza default');

-- ============================================================
-- I processi di prova
-- ============================================================
-- ⚠️ Una corsa nuova deve dichiarare il suo processo
--   (chk_job_run_log_processo_dichiarato, FK su dbops.processi): si seminano,
--   come fa dbops/test-presidio-processi-testo-per-causa-v1. Canale CODA: niente
--   job pgAgent da dichiarare.
INSERT INTO dbops.processi (id, codice, descrizione, classe, canale)
VALUES (9701, 'PGTAP-RUOLO-CORSA',   'prova ruolo', 'MANUTENZIONE', 'CODA'),
       (9702, 'PGTAP-RUOLO-SALTATA', 'prova ruolo', 'MANUTENZIONE', 'CODA'),
       (9703, 'PGTAP-SU-ULTIMA',     'prova ruolo', 'MANUTENZIONE', 'CODA'),
       (9704, 'PGTAP-SU-PRIMA',      'prova ruolo', 'MANUTENZIONE', 'CODA'),
       (9705, 'PGTAP-SU-NULL',       'prova ruolo', 'MANUTENZIONE', 'CODA'),
       (9706, 'PGTAP-SU-SPARITO',    'prova ruolo', 'MANUTENZIONE', 'CODA');

-- ============================================================
-- 2..3. fn_run_and_log scrive il ruolo
-- ============================================================
CREATE TEMP TABLE _t0 ON COMMIT DROP AS SELECT clock_timestamp() AS t0;

DO $corsa$ BEGIN PERFORM maintenance.fn_run_and_log('PGTAP-RUOLO-CORSA', 'passo', 'SELECT 1'); END $corsa$;

SELECT is(
    (SELECT ruolo_sessione FROM maintenance.job_run_log
      WHERE jobname = 'PGTAP-RUOLO-CORSA' AND started_at >= (SELECT t0 FROM _t0)),
    session_user::text,
    '2. una corsa di fn_run_and_log porta ruolo_sessione = session_user');

-- ⚠️ La riga SALTATA nasce quando il lock della corsa e' gia' preso da
--   un'ALTRA sessione: dalla stessa, pg_try_advisory_lock riesce sempre. Il
--   lock lo tiene una sessione dblink, se il canale c'e'; altrimenti il caso
--   non si costruisce e lo si dichiara con skip.
CREATE TEMP TABLE _t_saltata ON COMMIT DROP AS SELECT false AS costruita, ''::text AS motivo;
DO $saltata$
DECLARE
    v_dsn text := nullif(current_setting('myapp.dblink_log_connection', true), '');
BEGIN
    -- ⚠️ to_regprocedure con la firma: dblink_connect ha due firme, e to_regproc
    --   su un nome con piu' firme restituisce NULL (il test era in skip per questo).
    IF to_regprocedure('public.dblink_connect(text,text)') IS NULL OR v_dsn IS NULL THEN
        UPDATE _t_saltata SET motivo = 'nessun canale dblink su questo database per tenere il lock da un''altra sessione';
        RETURN;
    END IF;
    BEGIN
        PERFORM public.dblink_connect('pgtap_lock_ruolo', v_dsn);
        PERFORM public.dblink_exec('pgtap_lock_ruolo', 'SELECT pg_advisory_lock(987654321)');
        PERFORM maintenance.fn_run_and_log('PGTAP-RUOLO-SALTATA', 'passo', 'SELECT 1', 987654321::bigint);
        PERFORM public.dblink_exec('pgtap_lock_ruolo', 'SELECT pg_advisory_unlock(987654321)');
        PERFORM public.dblink_disconnect('pgtap_lock_ruolo');
        UPDATE _t_saltata SET costruita = true;
    EXCEPTION WHEN OTHERS THEN
        BEGIN PERFORM public.dblink_disconnect('pgtap_lock_ruolo'); EXCEPTION WHEN OTHERS THEN NULL; END;
        UPDATE _t_saltata SET motivo = 'la sessione dblink per tenere il lock non si apre: ' || SQLERRM;
    END;
END
$saltata$;

SELECT CASE
    WHEN NOT (SELECT costruita FROM _t_saltata)
        THEN skip('3. ' || (SELECT motivo FROM _t_saltata), 1)
    ELSE is(
        (SELECT saltata::text || '/' || ruolo_sessione FROM maintenance.job_run_log
          WHERE jobname = 'PGTAP-RUOLO-SALTATA' AND started_at >= (SELECT t0 FROM _t0)),
        'true/' || session_user::text,
        '3. anche la riga saltata (lock occupato) porta ruolo_sessione = session_user')
END;

-- ============================================================
-- 4..6. La vista: si costruiscono le corse
-- ============================================================
INSERT INTO maintenance.job_run_log (jobname, processo_codice, started_at, ended_at, ok, message, ruolo_sessione)
VALUES
    -- l'ultima corsa e' di un superuser -> presidio
    ('PGTAP-SU-ULTIMA',  'PGTAP-SU-ULTIMA',  now() - interval '2 hours', now() - interval '2 hours', true, 'pgtap', 'zeroerp_app'),
    ('PGTAP-SU-ULTIMA',  'PGTAP-SU-ULTIMA',  now() - interval '1 hour',  now() - interval '1 hour',  true, 'pgtap', 'postgres'),
    -- c'era un superuser, ma l'ultima e' di un non-superuser -> no
    ('PGTAP-SU-PRIMA',   'PGTAP-SU-PRIMA',   now() - interval '2 hours', now() - interval '2 hours', true, 'pgtap', 'postgres'),
    ('PGTAP-SU-PRIMA',   'PGTAP-SU-PRIMA',   now() - interval '1 hour',  now() - interval '1 hour',  true, 'pgtap', 'zeroerp_app'),
    -- nessun ruolo registrato / un ruolo che non esiste -> no
    ('PGTAP-SU-NULL',    'PGTAP-SU-NULL',    now() - interval '1 hour',  now() - interval '1 hour',  true, 'pgtap', NULL),
    ('PGTAP-SU-SPARITO', 'PGTAP-SU-SPARITO', now() - interval '1 hour',  now() - interval '1 hour',  true, 'pgtap', 'pgtap_ruolo_che_non_esiste');

SELECT is(
    (SELECT ruolo_sessione FROM maintenance.vw_job_run_da_superuser
      WHERE processo_codice = 'PGTAP-SU-ULTIMA'),
    'postgres',
    '4. la vista prende l''ultima corsa di un processo fatta da un superuser');

SELECT is_empty(
    $$SELECT 1 FROM maintenance.vw_job_run_da_superuser WHERE processo_codice = 'PGTAP-SU-PRIMA'$$,
    '5. un processo la cui ULTIMA corsa e'' di un non-superuser non c''e'', anche con un superuser prima');

SELECT is_empty(
    $$SELECT 1 FROM maintenance.vw_job_run_da_superuser
       WHERE processo_codice IN ('PGTAP-SU-NULL', 'PGTAP-SU-SPARITO')$$,
    '6. ne'' le corse senza ruolo registrato, ne'' il ruolo di chi non esiste piu''');

-- ============================================================
-- 7..8. Il catalogo e chi la legge
-- ============================================================
SELECT is(
    (SELECT natura || '/' || chi_agisce FROM dbops.presidi
      WHERE vista = 'maintenance.vw_job_run_da_superuser'),
    'ZERO/SISTEMISTA',
    '7. il presidio e'' a catalogo: ZERO, lo spegne chi gestisce il database');

SELECT ok(
    has_table_privilege('zeroerp_app', 'maintenance.vw_job_run_da_superuser', 'SELECT'),
    '8. zeroerp_app legge la vista (il pannello e il digest la leggono come app)');

SELECT * FROM finish();
ROLLBACK;
