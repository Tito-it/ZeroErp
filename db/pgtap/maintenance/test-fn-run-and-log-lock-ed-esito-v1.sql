-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture scrive su dbops.processi e su
--   maintenance.job_run_log, che a runtime scrivono solo i job e le funzioni
--   del giornale. Il ruolo applicativo ha SELECT e basta.
--
-- Test: maintenance.fn_run_and_log — il lock non resta preso, l'esito si legge
-- ChangeSet: 20261103-56, 20261103-64 · Brief: brief-db-revisione-maintenance D2, D5
--
-- Elenco test (plan 11):
--  1) ⛔ D2: una corsa con lock e senza processo dichiarato e' respinta (23514)
--  2) ⭐ D2: ... e il lock NON resta preso (pg_locks della sessione)
--  3) ⭐ D5: un esito con _falliti > 0 rende la corsa rossa
--  4) ⭐ D5: ... con error_code E_JOB_ESITO_CON_SCARTI
--  5) ⭐ D5: ... il riepilogo intero e' in meta.esito
--  6) ⭐ D5: ... e il lavoro fatto NON e' annullato
--  7) ✅ D5: un esito con _falliti = 0 e' una corsa verde, «done», con l'esito
--  8) ✅ rows_affected di una SELECT resta il numero di righe
--  9) ✅ piu' istruzioni nella stessa stringa: EXECUTE semplice, nessun esito
-- 10) ⭐ una funzione void non scrive un esito vuoto in meta (le automazioni)
-- 11) ✅ una SELECT senza righe: rows_affected = 0
--
-- ⚠️ IL TEST 2 GUARDA pg_locks, NON pg_try_advisory_lock. Un advisory lock e'
--   RIENTRANTE nella stessa sessione: provarlo da qui direbbe «libero» anche se
--   fosse rimasto preso. Si conta invece quanti advisory lock tiene la sessione
--   prima e dopo.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(11);

-- ============================================================
-- Fixture
-- ============================================================
INSERT INTO dbops.processi (id, codice, descrizione, classe, canale,
                            jobname_pgagent, tolleranza_minuti, segno_di_vita,
                            acceso_in_sviluppo, acceso_in_produzione, spegnibile, causa_fallimento, accendibile_in_produzione)
VALUES
    (9991, 'PGTAP-ESITO-SCARTI', 'prova esito con scarti', 'MANUTENZIONE', 'COMMAND', NULL, 30, 'GIORNALE', true, true, true, 'PROGRAMMA', true),
    (9992, 'PGTAP-ESITO-PULITO', 'prova esito pulito',     'MANUTENZIONE', 'COMMAND', NULL, 30, 'GIORNALE', true, true, true, 'PROGRAMMA', true),
    (9993, 'PGTAP-ESITO-RIGHE',  'prova righe e piu'' istruzioni', 'MANUTENZIONE', 'COMMAND', NULL, 30, 'GIORNALE', true, true, true, 'PROGRAMMA', true);

-- Il «lavoro»: scrive una riga e restituisce un riepilogo. Serve a provare
-- che una corsa rossa per scarti non annulla quello che e' stato fatto.
CREATE TEMP TABLE tmp_lavoro (n integer);
CREATE FUNCTION pg_temp.fn_lavoro(p_falliti integer) RETURNS jsonb
LANGUAGE plpgsql AS $f$
BEGIN
  INSERT INTO tmp_lavoro VALUES (1);
  RETURN jsonb_build_object('_accodati', 3, '_falliti', p_falliti);
END
$f$;

CREATE TEMP TABLE tmp_lock_prima AS
SELECT count(*) AS n FROM pg_locks
 WHERE locktype = 'advisory' AND pid = pg_backend_pid();

-- ============================================================
-- 1-2. D2: l'apertura respinta non lascia il lock preso
-- ============================================================
SELECT throws_ok(
    $$ SELECT maintenance.fn_run_and_log(
           'PGTAP-ESITO-NESSUN-PROCESSO', 'step', 'SELECT 1',
           p_lock_key => hashtext('PGTAP-ESITO-NESSUN-PROCESSO')::bigint) $$,
    '23514',
    NULL,
    'D2: una corsa senza processo dichiarato e'' respinta all''apertura'
);

SELECT is(
    (SELECT count(*) FROM pg_locks
      WHERE locktype = 'advisory' AND pid = pg_backend_pid()),
    (SELECT n FROM tmp_lock_prima),
    'D2: dopo l''apertura respinta la sessione non tiene il lock'
);

-- ============================================================
-- 3-6. D5: riuscita con scarti
-- ============================================================
SELECT maintenance.fn_run_and_log(
    'PGTAP-ESITO-SCARTI', 'step', 'SELECT pg_temp.fn_lavoro(2);',
    p_lock_key => hashtext('PGTAP-ESITO-SCARTI')::bigint);

SELECT is(
    (SELECT ok FROM maintenance.job_run_log
      WHERE processo_codice = 'PGTAP-ESITO-SCARTI' ORDER BY id DESC LIMIT 1),
    false,
    'D5: un esito con _falliti > 0 rende la corsa rossa'
);

SELECT is(
    (SELECT error_code FROM maintenance.job_run_log
      WHERE processo_codice = 'PGTAP-ESITO-SCARTI' ORDER BY id DESC LIMIT 1),
    'E_JOB_ESITO_CON_SCARTI',
    'D5: la corsa rossa per scarti porta E_JOB_ESITO_CON_SCARTI'
);

SELECT is(
    (SELECT meta -> 'esito' ->> '_accodati' FROM maintenance.job_run_log
      WHERE processo_codice = 'PGTAP-ESITO-SCARTI' ORDER BY id DESC LIMIT 1),
    '3',
    'D5: il riepilogo intero sta in meta.esito'
);

SELECT is(
    (SELECT count(*)::integer FROM tmp_lavoro),
    1,
    'D5: il lavoro fatto non e'' annullato dalla corsa rossa'
);

-- ============================================================
-- 7. D5: un esito senza scarti e' verde
-- ============================================================
SELECT maintenance.fn_run_and_log(
    'PGTAP-ESITO-PULITO', 'step', 'SELECT pg_temp.fn_lavoro(0)');

SELECT ok(
    (SELECT ok AND message = 'done' AND meta -> 'esito' ->> '_falliti' = '0'
       FROM maintenance.job_run_log
      WHERE processo_codice = 'PGTAP-ESITO-PULITO' ORDER BY id DESC LIMIT 1),
    'D5: un esito con _falliti = 0 e'' una corsa verde, done, con l''esito in meta'
);

-- ============================================================
-- 8-9. Quello che c'era resta: righe contate, piu' istruzioni eseguite
-- ============================================================
SELECT maintenance.fn_run_and_log(
    'PGTAP-ESITO-RIGHE', 'righe', 'SELECT generate_series(1, 3)');

SELECT is(
    (SELECT rows_affected::integer FROM maintenance.job_run_log
      WHERE processo_codice = 'PGTAP-ESITO-RIGHE' AND stepname = 'righe'
      ORDER BY id DESC LIMIT 1),
    3,
    'rows_affected di una SELECT resta il numero di righe'
);

SELECT maintenance.fn_run_and_log(
    'PGTAP-ESITO-RIGHE', 'due', 'SELECT 1; SELECT 2;');

SELECT ok(
    (SELECT ok AND NOT (meta ? 'esito')
       FROM maintenance.job_run_log
      WHERE processo_codice = 'PGTAP-ESITO-RIGHE' AND stepname = 'due'
      ORDER BY id DESC LIMIT 1),
    'Piu'' istruzioni nella stessa stringa: corsa verde, nessun esito letto'
);

-- ============================================================
-- 10-11. Il giro 2: esito vuoto e risultato senza righe
-- ============================================================
SELECT maintenance.fn_run_and_log(
    'PGTAP-ESITO-RIGHE', 'void', 'SELECT pg_sleep(0)');

SELECT ok(
    (SELECT ok AND NOT (meta ? 'esito')
       FROM maintenance.job_run_log
      WHERE processo_codice = 'PGTAP-ESITO-RIGHE' AND stepname = 'void'
      ORDER BY id DESC LIMIT 1),
    'Una funzione void non scrive un esito vuoto in meta'
);

SELECT maintenance.fn_run_and_log(
    'PGTAP-ESITO-RIGHE', 'vuota', 'SELECT 1 WHERE false');

SELECT is(
    (SELECT rows_affected::integer FROM maintenance.job_run_log
      WHERE processo_codice = 'PGTAP-ESITO-RIGHE' AND stepname = 'vuota'
      ORDER BY id DESC LIMIT 1),
    0,
    'Una SELECT senza righe: rows_affected = 0'
);

SELECT * FROM finish();

ROLLBACK;
