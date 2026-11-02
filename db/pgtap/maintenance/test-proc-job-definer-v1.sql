-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: le procedure dei job girano come il PROPRIETARIO, e le chiama solo chi
--       deve (fase 1-bis dei ruoli di sistema)
-- Brief: brief-db-ruoli-di-sistema §3.1, §5 (D-2 di Tid, 2026-10-14)
-- ChangeSet: 20261014-55
--
-- Elenco test (plan 7):
--  1) il perimetro non e' vuoto (censimento non degradato)
--  2) ⭐ ogni maintenance.proc_*_job e' SECURITY DEFINER
--  3) ⛔ ogni maintenance.proc_*_job fissa il search_path
--  4) ogni maintenance.proc_*_job e' del proprietario dello schema maintenance
--  5) ⛔ PUBLIC non ha EXECUTE su nessuna maintenance.proc_*_job
--  6) ⛔ zeroerp_app non ha EXECUTE su nessuna maintenance.proc_*_job
--  7) dove il ruolo zeroerp_job esiste, ha EXECUTE su tutte (skip dichiarato
--     finche' il provisioning dei ruoli di sistema non lo crea)
--
-- ── Perche' ───────────────────────────────────────────────────────────
--   pgAgent si colleghera' come `zeroerp_job`, che non possiede niente e puo'
--   SOLO chiamare queste procedure: il lavoro gira come il proprietario perche'
--   sono DEFINER, e cio' che creano nasce suo. Due modi di rompere il disegno
--   in silenzio, e questo file li vede tutti e due:
--   * una procedura nuova nata INVOKER: di notte girerebbe come zeroerp_job,
--     cioe' senza diritti — o, peggio, come chiunque la lanci;
--   * una procedura DEFINER con l'EXECUTE di PUBLIC (il default di
--     PostgreSQL): chiunque lancerebbe le automazioni come proprietario.
--
-- ⭐ Il perimetro e' il NOME (`proc_%_job` in maintenance), come per il
--   presidio dei jobname (dbops/test-processi-jobname-wrapper): una procedura
--   nuova ci entra da sola, senza che nessuno aggiorni un elenco.
-- ⚠️ Il proprietario atteso e' quello dello SCHEMA, non un nome: titodb su
--   dbdev, zeroerp in CI, zeroerp_owner dopo la fase 3. Il test vale in tutti.
-- ⚠️ Legge solo il catalogo: gira come zeroerp_app, nessuna fixture.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(7);

CREATE TEMP TABLE _t_proc ON COMMIT DROP AS
SELECT p.oid,
       p.oid::regprocedure::text AS firma,
       p.prosecdef,
       p.proconfig,
       p.proowner,
       n.nspowner
  FROM pg_catalog.pg_proc p
  JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
 WHERE n.nspname = 'maintenance'
   AND p.prokind = 'p'
   AND p.proname LIKE 'proc\_%\_job';

-- ============================================================
-- 1. Il censimento
-- ============================================================
SELECT cmp_ok(
    (SELECT count(*) FROM _t_proc)::bigint, '>', 0::bigint,
    '1. il perimetro delle procedure dei job non e'' vuoto');

-- ============================================================
-- 2..4. Girano come il proprietario
-- ============================================================
SELECT is_empty(
    $$SELECT firma FROM _t_proc WHERE NOT prosecdef$$,
    '2. ogni maintenance.proc_*_job e'' SECURITY DEFINER');

SELECT is_empty(
    $$SELECT firma FROM _t_proc
       WHERE NOT EXISTS (SELECT 1 FROM unnest(proconfig) c
                          WHERE c LIKE 'search\_path=%')$$,
    '3. ogni maintenance.proc_*_job fissa il search_path');

SELECT is_empty(
    $$SELECT firma || ' e'' di ' || pg_get_userbyid(proowner)
       FROM _t_proc WHERE proowner <> nspowner$$,
    '4. ogni maintenance.proc_*_job e'' del proprietario dello schema maintenance');

-- ============================================================
-- 5..7. La chiama solo chi deve
-- ============================================================
SELECT is_empty(
    $$SELECT firma FROM _t_proc
       WHERE has_function_privilege('public', oid, 'EXECUTE')$$,
    '5. PUBLIC non ha EXECUTE su nessuna maintenance.proc_*_job');

SELECT is_empty(
    $$SELECT firma FROM _t_proc
       WHERE has_function_privilege('zeroerp_app', oid, 'EXECUTE')$$,
    '6. zeroerp_app non ha EXECUTE su nessuna maintenance.proc_*_job');

SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = 'zeroerp_job')
        THEN skip('7. il ruolo zeroerp_job non esiste ancora: lo crea il provisioning dei '
                  'ruoli di sistema (brief-db-ruoli-di-sistema, fase 1)', 1)
    ELSE is_empty(
        $$SELECT firma FROM _t_proc
           WHERE NOT has_function_privilege('zeroerp_job', oid, 'EXECUTE')$$,
        '7. zeroerp_job ha EXECUTE su ogni maintenance.proc_*_job')
END;

SELECT * FROM finish();
ROLLBACK;
