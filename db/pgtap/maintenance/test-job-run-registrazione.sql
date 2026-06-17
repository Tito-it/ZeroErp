-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP — registrazione run job headless: colonne origine/meta + funzioni
--         script.fn_job_run_start / fn_job_run_end (J1/J2/J3).
--
-- Vedi: docs/it/dev/work-in-progress/brief-db-job-run-registrazione.md
--
-- Copre struttura + happy-path start/end + postura SECURITY DEFINER + REVOKE PUBLIC.
-- NON copre l'anti-overlap reale: l'advisory lock di sessione e' re-entrant -> due
-- start con la stessa lock_key nella STESSA sessione tornano entrambi acquired=true;
-- l'overlap vero e' cross-connessione (due run cron) e non e' testabile in un singolo
-- BEGIN pgTAP (vedi brief §6). I test usano lock_key=NULL per non lasciare lock.
--
-- BEGIN;/ROLLBACK; — read-mostly (gli INSERT del run vengono annullati).
-- ------------------------------------------------------------

BEGIN;
SELECT plan(21);

-- ---- 1..6: colonne origine/meta ----
SELECT has_column('maintenance', 'job_run_log', 'origine', 'origine esiste');
SELECT col_not_null('maintenance', 'job_run_log', 'origine', 'origine NOT NULL');
SELECT ok(
    (SELECT column_default LIKE '%PGAGENT%'
     FROM information_schema.columns
     WHERE table_schema='maintenance' AND table_name='job_run_log' AND column_name='origine'),
    'origine default PGAGENT'
);
SELECT has_column('maintenance', 'job_run_log', 'meta', 'meta esiste');
SELECT col_not_null('maintenance', 'job_run_log', 'meta', 'meta NOT NULL');
SELECT ok(
    (SELECT column_default LIKE '%{}%'
     FROM information_schema.columns
     WHERE table_schema='maintenance' AND table_name='job_run_log' AND column_name='meta'),
    'meta default {}'
);

-- ---- 7: CHECK rifiuta origine non valida ----
SELECT throws_ok(
    $$ INSERT INTO maintenance.job_run_log(jobname, origine) VALUES ('t_check','XXX') $$,
    '23514',
    NULL,
    'CHECK chk_job_run_log_origine rifiuta origine non valida'
);

-- ---- 8..11: fn_job_run_start happy-path (no lock) ----
CREATE TEMP TABLE _r ON COMMIT DROP AS
    SELECT * FROM script.fn_job_run_start('test_job', 'CRON', NULL, NULL, NULL);

SELECT ok((SELECT acquired FROM _r), 'start: acquired = true');
SELECT ok((SELECT run_uuid IS NOT NULL FROM _r), 'start: run_uuid non null');
SELECT is(
    (SELECT origine FROM maintenance.job_run_log WHERE id = (SELECT id FROM _r)),
    'CRON', 'start: riga con origine CRON'
);
SELECT ok(
    (SELECT ended_at IS NULL FROM maintenance.job_run_log WHERE id = (SELECT id FROM _r)),
    'start: ended_at null (run aperto)'
);

-- ---- 12..15: fn_job_run_end happy-path ----
SELECT script.fn_job_run_end((SELECT id FROM _r), TRUE, 'done', 5::bigint, NULL, NULL, '{"k":1}'::jsonb, NULL);

SELECT ok(
    (SELECT ok FROM maintenance.job_run_log WHERE id = (SELECT id FROM _r)),
    'end: ok = true'
);
SELECT ok(
    (SELECT ended_at IS NOT NULL FROM maintenance.job_run_log WHERE id = (SELECT id FROM _r)),
    'end: ended_at valorizzato'
);
SELECT is(
    (SELECT meta->>'k' FROM maintenance.job_run_log WHERE id = (SELECT id FROM _r)),
    '1', 'end: meta aggiornato'
);
SELECT is(
    (SELECT rows_affected FROM maintenance.job_run_log WHERE id = (SELECT id FROM _r)),
    5::bigint, 'end: rows_affected'
);

-- ---- 16..19: postura SECURITY DEFINER + search_path fisso ----
SELECT ok(
    (SELECT p.prosecdef FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
     WHERE n.nspname='script' AND p.proname='fn_job_run_start'),
    'fn_job_run_start: SECURITY DEFINER'
);
SELECT ok(
    (SELECT p.prosecdef FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
     WHERE n.nspname='script' AND p.proname='fn_job_run_end'),
    'fn_job_run_end: SECURITY DEFINER'
);
SELECT ok(
    (SELECT array_to_string(p.proconfig, ',') LIKE '%search_path=%'
     FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
     WHERE n.nspname='script' AND p.proname='fn_job_run_start'),
    'fn_job_run_start: search_path fisso'
);
SELECT ok(
    (SELECT array_to_string(p.proconfig, ',') LIKE '%search_path=%'
     FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
     WHERE n.nspname='script' AND p.proname='fn_job_run_end'),
    'fn_job_run_end: search_path fisso'
);

-- ---- 20..21: REVOKE EXECUTE FROM PUBLIC ----
SELECT ok(
    NOT has_function_privilege('public',
        'script.fn_job_run_start(text,text,text,text,text)', 'EXECUTE'),
    'fn_job_run_start: PUBLIC senza EXECUTE'
);
SELECT ok(
    NOT has_function_privilege('public',
        'script.fn_job_run_end(bigint,boolean,text,bigint,text,text,jsonb,text)', 'EXECUTE'),
    'fn_job_run_end: PUBLIC senza EXECUTE'
);

SELECT * FROM finish();
ROLLBACK;
