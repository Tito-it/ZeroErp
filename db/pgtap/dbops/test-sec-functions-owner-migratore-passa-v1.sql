-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- pgtap-runner: owner
-- pgtap-runner-motivo: il SOGGETTO del test e' il migratore. La guardia di
--   dbops.fn_sync_functions_owner lascia passare chi possiede lo schema dbops,
--   letto da session_user: la sola prova che il migratore passa ancora e' una
--   connessione vera come lui. Il verso negativo (l'app rifiutata) e' il
--   gemello test-sec-functions-owner-riservato-v1.sql, col runner di default.
--
-- Test: il migratore passa la guardia della sync
--       dbops.fn_sync_functions_owner()
-- Brief: brief-db-registro-owner-e-sync-riservati-al-migratore §3
-- ChangeSet: 20_code/dbops/20260926-11
--
-- ⚠️ PERCHÉ ESISTE. Senza questo file il presidio «il migratore passa»
--   esisterebbe solo come «il prossimo `liquibase update` muore» sul runAlways
--   90_end/20251123-04: un presidio violento e tardivo.
--
-- Elenco test (plan 2):
--  1) il runner owner È il migratore: membro del proprietario dello schema
--     dbops, o superuser. Se è rosso il 2 non dice niente — il runner owner di
--     questa macchina non è chi migra, e va detto prima di cercare altrove
--  2) SELECT dbops.fn_sync_functions_owner() come migratore → vive
--
-- In BEGIN;/ROLLBACK;: un eventuale ALTER … OWNER della sync si ritira.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(2);

SELECT ok(
    COALESCE(
        pg_catalog.pg_has_role(
            session_user,
            (SELECT n.nspowner FROM pg_catalog.pg_namespace n WHERE n.nspname = 'dbops'),
            'MEMBER')
     OR (SELECT a.rolsuper FROM pg_catalog.pg_roles a WHERE a.rolname = session_user),
        false),
    format('1. il runner owner (%s) è il migratore: membro del proprietario di dbops, o superuser',
           session_user));

SELECT lives_ok(
    $$ SELECT dbops.fn_sync_functions_owner() $$,
    '2. fn_sync_functions_owner come migratore: la guardia lascia passare');

SELECT * FROM finish();
ROLLBACK;
