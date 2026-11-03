-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- pgtap-runner: owner
-- pgtap-runner-motivo: il test 3 esegue il runner di pulizia in simulazione,
--   che legge pg_class e il registro delle automazioni come fa il job.
--
-- Test: il giro di pulizia esegue le regole che il registro dichiara
--   maintenance.proc_automations_cleanup_job · dbops.fn_run_automations_cleanup
--   dbops.automation_rules_tbl · dbops.fn_resolve_scope
-- ChangeSet: 20261103-58 · Brief: brief-db-revisione-maintenance D4
--
-- Elenco test (plan 3):
--  1) ⭐ la procedura del job non fissa piu' gli schemi: passa l'ambito NULL
--     (presidio sul TESTO del corpo)
--  2) ⭐ ogni regola CLEANUP_* attiva punta a uno schema che l'ambito del
--     registro comprende: nessuna regola senza esecutore
--  3) ✅ il runner gira in simulazione con l'ambito del registro
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(3);

SELECT ok(
    (SELECT p.prosrc NOT LIKE '%ARRAY[%'
            AND p.prosrc LIKE '%fn_run_automations_cleanup(''''SCHEDULED'''', NULL,%'
       FROM pg_proc p
       JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'maintenance'
        AND p.proname = 'proc_automations_cleanup_job'),
    'Il job di pulizia passa al runner l''ambito NULL, cioe'' quello del registro'
);

SELECT is(
    (SELECT string_agg(r.id::text || ':' || r.target_schema, ', ' ORDER BY r.id)
       FROM dbops.automation_rules_tbl r
      WHERE r.enabled
        AND upper(btrim(r.rule_type)) IN ('CLEANUP_AT', 'CLEANUP_PURGE')
        AND lower(r.target_schema) <> '*all'
        AND NOT (r.target_schema = ANY (dbops.fn_resolve_scope(NULL)))),
    NULL,
    'Ogni regola di pulizia attiva punta a uno schema dell''ambito del registro'
);

SELECT lives_ok(
    $$ SELECT dbops.fn_run_automations_cleanup('SCHEDULED', NULL, true) $$,
    'Il runner di pulizia gira in simulazione con l''ambito del registro'
);

SELECT * FROM finish();

ROLLBACK;
