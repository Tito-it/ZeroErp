-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP — registrazione run job headless: colonne origine/meta + funzioni
--         script.fn_job_run_start / fn_job_run_end (J1/J2/J3).
--
-- Vedi: brief-db-job-run-registrazione.md
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

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file sarebbe verde per sottrazione. IMMEDIATE li riporta a scattare a fine
--   di ogni istruzione. In testa e non in coda: in coda scatterebbero dopo il
--   cleanup, su righe ormai cancellate.
--   Brief: brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

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
-- ⚠️ Si passa dall'entry point, non da una INSERT diretta. maintenance.job_run_log
--   la scrivono i job (maintenance.fn_run_and_log) e script.fn_job_run_start, che e'
--   SECURITY DEFINER: il ruolo applicativo ha solo SELECT, ed e' corretto cosi'.
--   La INSERT diretta falliva con «permesso negato» invece che col CHECK — e il test
--   lo diceva forte perche' pretende lo SQLSTATE (23514), che e' esattamente il motivo
--   per cui lo si pretende. Dall'entry point il CHECK scatta lo stesso, e il collaudo
--   diventa piu' fedele: e' la porta da cui ci passa l'applicazione.
SELECT throws_ok(
    $$ SELECT script.fn_job_run_start('t_check','XXX') $$,
    '23514',
    NULL,
    'CHECK chk_job_run_log_origine rifiuta origine non valida'
);

-- ---- 8..11: fn_job_run_start happy-path (no lock) ----
-- ⛔ 2026-09-05: `chk_job_run_log_processo_dichiarato` pretende che un run NUOVO
--   dichiari il proprio processo (DB-5). Questa fixture ne apriva uno muto —
--   collaudava la vecchia tolleranza, non la registrazione.
--   ⇒ Si passa un processo VERO del catalogo, scelto in modo deterministico:
--     cosi' il file continua a collaudare cio' che collaudava — l'apertura e la
--     chiusura del run — invece di inciampare su un vincolo che non e' suo.
CREATE TEMP TABLE _r ON COMMIT DROP AS
    SELECT * FROM script.fn_job_run_start(
        'test_job', 'CRON', NULL, NULL, NULL,
        (SELECT codice FROM dbops.processi
          WHERE classe = 'MANUTENZIONE' AND attivo
          ORDER BY id LIMIT 1));

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
        -- ⚠️ Funzione cercata per NOME, non per firma letterale: la firma
        --   cambia quando si aggiungono parametri (2026-09-04: +attore), e
        --   un test che la scrive a mano fallisce per il MOTIVO SBAGLIATO —
        --   segnala la firma invece del privilegio che deve presidiare.
        (SELECT p.oid
           FROM pg_catalog.pg_proc p
           JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
          WHERE n.nspname = 'script' AND p.proname = 'fn_job_run_start'),
        'EXECUTE'),
    'fn_job_run_start: PUBLIC senza EXECUTE'
);
-- ⚠️ Per NOME come il test accanto (2026-10-16: +p_sqlstate in coda, 20261016-40;
--   la firma letterale a otto parametri non esiste piu').
SELECT ok(
    NOT has_function_privilege('public',
        (SELECT p.oid
           FROM pg_catalog.pg_proc p
           JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
          WHERE n.nspname = 'script' AND p.proname = 'fn_job_run_end'),
        'EXECUTE'),
    'fn_job_run_end: PUBLIC senza EXECUTE'
);

SELECT * FROM finish();
ROLLBACK;
