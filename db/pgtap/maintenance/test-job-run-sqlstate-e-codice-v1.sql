-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture scrive su dbops.processi (catalogo del
--   migratore) e apre corse con script.fn_job_run_start come il backend.
--
-- Test: le porte di scrittura del giornale dei job tengono lo SQLSTATE separato
--   dal codice d'errore (maintenance.job_run_log.sqlstate)
-- ChangeSet: 00_schema/maintenance/20261016-35 · 20_code/maintenance/20261016-38
--   · 20261016-39 (provision) · 20_code/script/20261016-40
-- Brief: brief-db-presidio-job-run-a-chi-tocca §4.2, §4.4 (D5)
--
-- Elenco test (plan 9):
--  1) la colonna rifiuta cio' che non ha la forma di uno SQLSTATE
--  2) ⭐ script.fn_job_run_end chiamata come oggi dal backend (otto argomenti
--     per posizione) risolve sulla firma nuova e lascia sqlstate NULL
--  3) ⭐ con il nono argomento scrive lo SQLSTATE, e error_code resta il codice
--     del backend
--  4) la firma vecchia di fn_job_run_end non esiste piu' (nessun overload)
--  5) l'applicazione esegue fn_job_run_end, PUBLIC no
--  6) maintenance.fn_job_run_log_failure ha UNA firma, con p_sqlstate in coda
--     e default
--  7) e il verbale scrive la colonna (presidio sul testo)
--  8) fn_run_and_log legge il canale CONSTRAINT solo col contratto P0001
--     (presidio sul testo)
--  9) e passa lo SQLSTATE al verbale fuori transazione (presidio sul testo)
--
-- ────────────────────────────────────────────────────────────────
-- ⚠️ I TEST 7-9 SONO PRESIDI SUL TESTO, e si dichiarano tali. Il ramo di
--   fallimento di fn_run_and_log non e' osservabile in una transazione di
--   prova: rilancia sempre (il suo UPDATE muore col RAISE) e il verbale va su
--   una connessione dblink, cioe' FUORI dal ROLLBACK di questo file — un
--   fallimento provocato qui lascerebbe una riga rossa vera nel giornale.
--   Stessa scelta di test-job-run-log-failure-out-of-tx (test 6).
-- ⚠️ La conversione delle righe di prima (20261016-35) non e' costruibile dopo
--   il fatto: e' un ALTER ... USING, e su un database da zero non ha righe.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(9);

INSERT INTO dbops.processi (id, codice, descrizione, classe, canale, causa_fallimento)
VALUES (9971, 'PGTAP-SQLSTATE-PROC', 'prova sqlstate del giornale', 'MANUTENZIONE', 'CODA', 'PROGRAMMA');

-- ============================================================
-- 1. La forma
-- ============================================================
SELECT throws_ok(
    $$INSERT INTO maintenance.job_run_log (jobname, processo_codice, sqlstate)
      VALUES ('PGTAP-SQLSTATE-FORMA', 'PGTAP-SQLSTATE-PROC', 'OperationalError')$$,
    '23514',
    NULL,
    '1. la colonna rifiuta cio'' che non ha la forma di uno SQLSTATE'
);

-- ============================================================
-- 2..5. La porta del backend
-- ============================================================
CREATE TEMP TABLE _corse ON COMMIT DROP AS
SELECT 'otto'::text AS caso, s.id
  FROM script.fn_job_run_start('PGTAP-SQLSTATE-OTTO', 'CRON', NULL, NULL, NULL,
                               'PGTAP-SQLSTATE-PROC', NULL) s;
INSERT INTO _corse
SELECT 'nove', s.id
  FROM script.fn_job_run_start('PGTAP-SQLSTATE-NOVE', 'CRON', NULL, NULL, NULL,
                               'PGTAP-SQLSTATE-PROC', NULL) s;

DO $chiusure$
BEGIN
    -- Otto argomenti per posizione, come registered_job oggi.
    PERFORM script.fn_job_run_end((SELECT id FROM _corse WHERE caso = 'otto'),
                                  false, 'rotto', NULL, 'OperationalError', 'dettaglio',
                                  NULL::jsonb, NULL);
    PERFORM script.fn_job_run_end((SELECT id FROM _corse WHERE caso = 'nove'),
                                  false, 'rotto', NULL, 'OperationalError', 'dettaglio',
                                  NULL::jsonb, NULL, '53100');
END
$chiusure$;

SELECT is(
    (SELECT coalesce(l.sqlstate, '<NULL>') || ' | ' || l.error_code
       FROM maintenance.job_run_log l JOIN _corse c ON c.id = l.id
      WHERE c.caso = 'otto'),
    '<NULL> | OperationalError',
    '2. fn_job_run_end con otto argomenti risolve sulla firma nuova, sqlstate NULL'
);

SELECT is(
    (SELECT l.sqlstate || ' | ' || l.error_code
       FROM maintenance.job_run_log l JOIN _corse c ON c.id = l.id
      WHERE c.caso = 'nove'),
    '53100 | OperationalError',
    '3. col nono argomento scrive lo SQLSTATE, e error_code resta il codice del backend'
);

SELECT is(
    to_regprocedure('script.fn_job_run_end(bigint, boolean, text, bigint, text, text, jsonb, text)'),
    NULL,
    '4. la firma a otto parametri non esiste piu'': nessun overload'
);

SELECT ok(
    has_function_privilege('zeroerp_app',
        'script.fn_job_run_end(bigint, boolean, text, bigint, text, text, jsonb, text, text)', 'EXECUTE')
    AND NOT EXISTS (
        SELECT 1
          FROM pg_proc p, aclexplode(coalesce(p.proacl, acldefault('f', p.proowner))) a
         WHERE p.oid = 'script.fn_job_run_end(bigint, boolean, text, bigint, text, text, jsonb, text, text)'::regprocedure
           AND a.grantee = 0 AND a.privilege_type = 'EXECUTE'),
    '5. l''applicazione esegue fn_job_run_end, PUBLIC no'
);

-- ============================================================
-- 6..9. Il verbale e fn_run_and_log
-- ============================================================
SELECT results_eq(
    $$SELECT pg_get_function_identity_arguments(p.oid) || ' || ' ||
             (pg_get_function_arguments(p.oid) LIKE '%p_sqlstate text DEFAULT NULL::text')::text
        FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
       WHERE n.nspname = 'maintenance' AND p.proname = 'fn_job_run_log_failure'$$,
    $$VALUES ('p_jobname text, p_stepname text, p_started_at timestamp with time zone, p_run_uuid uuid, p_origine character varying, p_processo_codice text, p_auth_user_id integer, p_message text, p_error_code text, p_error_detail text, p_sqlstate text || true')$$,
    '6. il verbale dei fallimenti ha una firma sola, con p_sqlstate in coda e default'
);

SELECT ok(
    (SELECT p.prosrc LIKE '%auth_user_id, ruolo_sessione, sqlstate)%'
       FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'maintenance' AND p.proname = 'fn_job_run_log_failure'),
    '7. il verbale scrive la colonna sqlstate (presidio sul testo)'
);

SELECT ok(
    (SELECT p.prosrc LIKE '%CONSTRAINT_NAME%'
        AND p.prosrc LIKE '%v_sqlstate = ''P0001'' AND NULLIF(v_vincolo, '''') IS NOT NULL%'
       FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'maintenance' AND p.proname = 'fn_run_and_log'),
    '8. fn_run_and_log prende il codice di dominio solo col contratto P0001 + CONSTRAINT (presidio sul testo)'
);

SELECT ok(
    (SELECT p.prosrc LIKE '%p_sqlstate        => v_sqlstate%'
        AND p.prosrc LIKE '%sqlstate     = v_sqlstate%'
       FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'maintenance' AND p.proname = 'fn_run_and_log'),
    '9. fn_run_and_log scrive lo SQLSTATE e lo passa al verbale fuori transazione (presidio sul testo)'
);

SELECT * FROM finish();

ROLLBACK;
