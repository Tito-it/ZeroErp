-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: le funzioni dello scope di storico riconoscono il proprietario della
-- shadow dai privilegi, non dal nome (D52).
-- Brief: brief-db-revisione-dbops, giro 9, blocco 9b (§24). changeSet 20261109-56.
--
-- ⚠️ Il caso vero (un ruolo membro di zeroerp_owner che arma una shadow) vuole un
--   ruolo nuovo, cioe' CREATEROLE, che il runner dei pgTAP non ha. Si prova la
--   forma del corpo: la domanda e' pg_has_role(..., 'USAGE'), e il nome del
--   proprietario non si confronta piu' con current_user. Il ramo vero lo prova
--   chi arma da un membro (provisioning, cluster usa-e-getta).
--
-- Elenco test (plan 4):
--   1) fn_storico_arma_scope chiede i privilegi del proprietario
--   2) ... e non confronta il nome con current_user
--   3) fn_storico_backfill_scope chiede i privilegi del proprietario
--   4) ... e non confronta il nome con current_user
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(4);

SELECT matches((SELECT prosrc FROM pg_proc
                 WHERE oid = 'dbops.fn_storico_arma_scope(text, text, boolean)'::regprocedure),
    'pg_has_role\(current_user, v_owner, ''USAGE''\)',
    '1) fn_storico_arma_scope: il proprietario e'' chi ne ha i privilegi');

SELECT doesnt_match((SELECT prosrc FROM pg_proc
                      WHERE oid = 'dbops.fn_storico_arma_scope(text, text, boolean)'::regprocedure),
    'v_owner\s*(<>|=)\s*current_user',
    '2) fn_storico_arma_scope: nessun confronto del nome con current_user');

SELECT matches((SELECT prosrc FROM pg_proc
                 WHERE oid = 'dbops.fn_storico_backfill_scope(text, text)'::regprocedure),
    'pg_has_role\(current_user, v_owner, ''USAGE''\)',
    '3) fn_storico_backfill_scope: il proprietario e'' chi ne ha i privilegi');

SELECT doesnt_match((SELECT prosrc FROM pg_proc
                      WHERE oid = 'dbops.fn_storico_backfill_scope(text, text)'::regprocedure),
    'v_owner\s*(<>|=)\s*current_user',
    '4) fn_storico_backfill_scope: nessun confronto del nome con current_user');

SELECT * FROM finish();

ROLLBACK;
