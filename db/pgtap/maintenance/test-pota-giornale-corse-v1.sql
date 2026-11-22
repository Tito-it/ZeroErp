-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture scrive su dbops.processi e su
--   maintenance.job_run_log, che a runtime scrivono solo il seed, i job e le
--   funzioni del giornale; e la potatura cancella, cosa che l'applicazione non
--   puo' fare (non ha DELETE sul giornale).
--
-- Test: la ritenzione del giornale delle corse
--   maintenance.fn_pota_giornale_corse, maintenance.proc_pota_giornale_corse_job,
--   dbops.processi.potatura_esclusione, il processo pota_giornale_corse
-- ChangeSet: 20261122-29 … -32 · Brief: brief-db-giornale-corse-indici §7, §8
--
-- Elenco test (plan 19):
--  1-2) ✅ la funzione esiste, e PUBLIC non la esegue
--  3) ✅ zeroerp_app non esegue la procedura del job
--  4) ✅ la procedura pota a 12 mesi dal giorno aziendale (fn_mesi_dopo, -12)
--  5) ✅ potatura_esclusione rifiuta la stringa vuota
--  6) ⭐ STRICT: con la soglia NULL non cancella niente
--  7) ⭐ l'esito porta la soglia e le righe cancellate
--  8) ⭐ una corsa chiusa e vecchia, che non e' «l'ultima» di niente, si cancella
--  9-13) ⭐ della coppia (processo, jobname) restano, vecchie: l'ultima fallita,
--     l'ultima col ruolo (e di pgAgent), la corsa aperta, l'ultima conclusa e
--     vera, l'ultima in assoluto
-- 14) ⭐ LA COPPIA, NON IL JOBNAME: lo stesso jobname ha corse PIU' RECENTI di
--     un altro processo, e le ultime della prima coppia restano lo stesso (test
--     9-13); resta anche l'ultima dell'altra coppia
-- 15) ⭐ una corsa recente rende potabile la vecchia della stessa coppia, e
--     resta
-- 16) ⭐ le corse di un processo con potatura_esclusione non si potano
-- 17-18) ✅ il seed: le tre corsie della fatturazione dichiarano l'esclusione;
--     il processo pota_giornale_corse e' a catalogo, pgAgent, fuori dalla
--     convergenza di CI
-- 19) ✅ il job pgAgent, se pgAgent c'e', ha il passo dietro il cancello
--     della sveglia — skip dove pgAgent non c'e' (la CI)
--
-- ⚠️ Le corse si COSTRUISCONO (regola zero, corollario sui test): la soglia
--   della prova e' 400 giorni fa, e le righe della fixture stanno a 450-550
--   giorni. La potatura gira su tutto il giornale, dentro la transazione che
--   finisce in ROLLBACK: le asserzioni guardano solo le righe della fixture.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(19);

-- ── 1-4: le porte ────────────────────────────────────────────
SELECT has_function('maintenance', 'fn_pota_giornale_corse', ARRAY['timestamp with time zone'],
    'maintenance.fn_pota_giornale_corse(timestamptz) esiste');

SELECT ok(
    NOT has_function_privilege('public', 'maintenance.fn_pota_giornale_corse(timestamp with time zone)', 'EXECUTE'),
    'PUBLIC non esegue la potatura'
);

SELECT ok(
    NOT has_function_privilege('zeroerp_app', 'maintenance.proc_pota_giornale_corse_job()', 'EXECUTE'),
    'zeroerp_app non esegue la procedura del job'
);

SELECT ok(
    (SELECT p.prosrc ~ 'fn_pota_giornale_corse\(script\.fn_inizio_giorno_operativo\(script\.fn_mesi_dopo\(script\.fn_giorno_operativo\(now\(\)\), -12\)\)\)'
       FROM pg_proc p
      WHERE p.oid = 'maintenance.proc_pota_giornale_corse_job()'::regprocedure),
    'la procedura pota a 12 mesi, dall''inizio del giorno aziendale'
);

-- ── Fixture ─────────────────────────────────────────────────
INSERT INTO dbops.processi (id, codice, descrizione, classe, canale, causa_fallimento, potatura_esclusione)
VALUES (9991, 'PGTAP-POTA',         'prova potatura',          'MANUTENZIONE', 'CODA', 'PROGRAMMA', NULL),
       (9992, 'PGTAP-POTA-ALTRO',   'prova potatura, altro',   'MANUTENZIONE', 'CODA', 'PROGRAMMA', NULL),
       (9993, 'PGTAP-POTA-ESCLUSO', 'prova potatura, escluso', 'MANUTENZIONE', 'CODA', 'PROGRAMMA',
        'prova: le corse si tengono tutte');

SELECT throws_ok(
    $$UPDATE dbops.processi SET potatura_esclusione = '  ' WHERE id = 9991$$,
    '23514',
    NULL,
    'potatura_esclusione non e'' mai vuota: un''esclusione dice perche'''
);

-- Il messaggio e' l'etichetta della riga. Coppia (PGTAP-POTA, PGTAP-POTA-A),
-- dalla piu' vecchia; nessuna e' l'ultima della coppia per piu' di una ragione
-- che il test non dichiari.
INSERT INTO maintenance.job_run_log
    (jobname, processo_codice, origine, ruolo_sessione, started_at, ended_at, ok, saltata, message)
VALUES
    ('PGTAP-POTA-A', 'PGTAP-POTA', 'COMMAND', NULL,          now() - interval '550 days', now() - interval '550 days', true,  false, 'a-vecchia-1'),
    ('PGTAP-POTA-A', 'PGTAP-POTA', 'COMMAND', NULL,          now() - interval '545 days', now() - interval '545 days', true,  false, 'a-vecchia-2'),
    ('PGTAP-POTA-A', 'PGTAP-POTA', 'COMMAND', NULL,          now() - interval '540 days', now() - interval '540 days', false, false, 'a-fallita'),
    ('PGTAP-POTA-A', 'PGTAP-POTA', 'PGAGENT', 'zeroerp_job', now() - interval '530 days', now() - interval '530 days', true,  false, 'a-ruolo-pgagent'),
    ('PGTAP-POTA-A', 'PGTAP-POTA', 'COMMAND', NULL,          now() - interval '520 days', NULL,                        NULL,  false, 'a-aperta'),
    ('PGTAP-POTA-A', 'PGTAP-POTA', 'COMMAND', NULL,          now() - interval '510 days', now() - interval '510 days', true,  false, 'a-conclusa'),
    ('PGTAP-POTA-A', 'PGTAP-POTA', 'COMMAND', NULL,          now() - interval '500 days', now() - interval '500 days', NULL,  true,  'a-saltata'),
-- Lo stesso jobname, un altro processo, corse piu' recenti ma sempre vecchie.
    ('PGTAP-POTA-A', 'PGTAP-POTA-ALTRO', 'COMMAND', NULL,          now() - interval '480 days', now() - interval '480 days', true, false, 'altro-vecchia'),
    ('PGTAP-POTA-A', 'PGTAP-POTA-ALTRO', 'PGAGENT', 'zeroerp_job', now() - interval '470 days', now() - interval '470 days', true, false, 'altro-ultima'),
-- Coppia (PGTAP-POTA, PGTAP-POTA-B): una vecchia e una recente.
    ('PGTAP-POTA-B', 'PGTAP-POTA', 'COMMAND', NULL, now() - interval '550 days', now() - interval '550 days', true, false, 'b-vecchia'),
    ('PGTAP-POTA-B', 'PGTAP-POTA', 'COMMAND', NULL, now() - interval '10 days',  now() - interval '10 days',  true, false, 'b-recente'),
-- Il processo escluso: due corse vecchie, la prima non e' l'ultima di niente.
    ('PGTAP-POTA-X', 'PGTAP-POTA-ESCLUSO', 'COMMAND', NULL, now() - interval '550 days', now() - interval '550 days', true, false, 'x-vecchia'),
    ('PGTAP-POTA-X', 'PGTAP-POTA-ESCLUSO', 'COMMAND', NULL, now() - interval '540 days', now() - interval '540 days', true, false, 'x-ultima');

CREATE TEMP TABLE _fixture ON COMMIT DROP AS
SELECT id, message AS etichetta
  FROM maintenance.job_run_log
 WHERE processo_codice IN ('PGTAP-POTA', 'PGTAP-POTA-ALTRO', 'PGTAP-POTA-ESCLUSO');

CREATE FUNCTION pg_temp.resta(p_etichetta text) RETURNS boolean LANGUAGE sql AS $f$
    SELECT EXISTS (SELECT 1 FROM maintenance.job_run_log l
                     JOIN _fixture f ON f.id = l.id
                    WHERE f.etichetta = p_etichetta)
$f$;

-- ── 6-7: la chiamata ─────────────────────────────────────────
SELECT ok(
    maintenance.fn_pota_giornale_corse(NULL) IS NULL
    AND (SELECT count(*) FROM maintenance.job_run_log l JOIN _fixture f ON f.id = l.id) = 13,
    'STRICT: con la soglia NULL non cancella niente'
);

CREATE TEMP TABLE _esito ON COMMIT DROP AS
SELECT maintenance.fn_pota_giornale_corse(now() - interval '400 days') AS esito;

SELECT ok(
    (SELECT jsonb_exists(esito, 'soglia') AND (esito ->> 'cancellate')::bigint >= 3 FROM _esito),
    'l''esito porta la soglia e le righe cancellate'
);

-- ── 8-16: che cosa resta ─────────────────────────────────────
SELECT ok(NOT pg_temp.resta('a-vecchia-1') AND NOT pg_temp.resta('a-vecchia-2'),
    'una corsa chiusa e vecchia che non e'' l''ultima di niente si cancella');
SELECT ok(pg_temp.resta('a-fallita'),       'resta l''ultima fallita della coppia');
SELECT ok(pg_temp.resta('a-ruolo-pgagent'), 'resta l''ultima col ruolo e di pgAgent della coppia');
SELECT ok(pg_temp.resta('a-aperta'),        'resta la corsa aperta, a qualunque eta''');
SELECT ok(pg_temp.resta('a-conclusa'),      'resta l''ultima conclusa e vera della coppia');
SELECT ok(pg_temp.resta('a-saltata'),       'resta l''ultima in assoluto della coppia, anche se saltata');
SELECT ok(pg_temp.resta('altro-ultima') AND NOT pg_temp.resta('altro-vecchia'),
    'la chiave e'' la coppia: l''altro processo sullo stesso jobname tiene la sua ultima, e non toglie la protezione alla prima coppia');
SELECT ok(pg_temp.resta('b-recente') AND NOT pg_temp.resta('b-vecchia'),
    'una corsa recente rende potabile la vecchia della stessa coppia, e resta');
SELECT ok(pg_temp.resta('x-vecchia') AND pg_temp.resta('x-ultima'),
    'le corse di un processo con potatura_esclusione non si potano');

-- ── 17-19: il seed e il job ──────────────────────────────────
SELECT is(
    (SELECT count(*)::integer FROM dbops.processi
      WHERE codice IN ('run_fatturazione_batch', 'FATTURAZIONE_GIRO', 'FATTURAZIONE_NUMERA')
        AND potatura_esclusione IS NOT NULL),
    3,
    'le tre corsie della fatturazione dichiarano potatura_esclusione (seed)'
);

SELECT is(
    (SELECT classe || '/' || canale || '/' || jobname_pgagent || '/' || (ci_esclusione IS NOT NULL)::text
       FROM dbops.processi WHERE codice = 'pota_giornale_corse'),
    'MANUTENZIONE/PGAGENT/pota_giornale_corse/true',
    'pota_giornale_corse e'' a catalogo: manutenzione, pgAgent, fuori dalla convergenza di CI (seed)'
);

-- ⚠️ pgagent solo in una query DINAMICA: dove lo schema non c'e' (la CI) una
--   query statica fallirebbe al parsing anche nel ramo che non gira.
CREATE FUNCTION pg_temp.passo_del_job() RETURNS boolean LANGUAGE plpgsql AS $f$
DECLARE v_ok boolean;
BEGIN
    EXECUTE $q$
        SELECT count(*) = 1
          FROM pgagent.pga_job j
          JOIN pgagent.pga_jobstep s ON s.jstjobid = j.jobid
         WHERE j.jobname = 'pota_giornale_corse'
           AND s.jstcode ~ 'fn_sveglia_accesa\(''pota_giornale_corse''\)'
           AND s.jstcode ~ 'CALL maintenance\.proc_pota_giornale_corse_job\(\)'
    $q$ INTO v_ok;
    RETURN v_ok;
END
$f$;

SELECT CASE
    WHEN to_regnamespace('pgagent') IS NULL
         OR NOT has_schema_privilege('pgagent', 'USAGE')
    THEN skip('pgAgent non c''e'' (la CI): il job non nasce', 1)
    ELSE ok(pg_temp.passo_del_job(),
            'il job pgAgent chiama la procedura dietro il cancello della sveglia')
END;

SELECT * FROM finish();

ROLLBACK;
