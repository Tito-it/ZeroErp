-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: il test scrive nel registro delle regole e degli override (dbops.automation_rules_tbl, dbops.automation_overrides_cols), che e' configurazione delle migrazioni
-- pgTAP test per Zero ERP
--
-- Il registro delle automazioni rifiuta una regola malformata, invece di
-- lasciare ai runner il compito di difendersi; e l'ambito non ha doppi.
-- Brief: brief-db-revisione-dbops, giro 10b (D2, D13, D17, D17-bis, D20, D27, R1)
--
-- Elenco test (plan 17):
--  1)    la strategia d'esistenza non c'e' piu' (N1)
--  2-10) ⭐ il CHECK rifiuta: tipo sconosciuto, modo non canonico, ttl_days
--        testuale, ttl_days zero, scadenza in un modo diverso da AUTO,
--        batch_limit non intero, trigger senza nome, ATTIVO senza require,
--        ATTIVO senza l'hash della FK
--  11)   una regola di scadenza ben formata entra
--  12)   un ruolo di colonna fuori vocabolario e' rifiutato (anche AUDIT_TS)
--  13-14) fn_resolve_scope: nessun doppio dal registro, lista del chiamante pulita
--  15)   la regola AUDIT_UPDATE non porta piu' i nomi delle colonne di audit
--  16)   nessuna funzione nomina existence_strategy
--  17)   nessun dry run firma col nome della funzione ritirata
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(17);

SELECT hasnt_column('dbops', 'automation_rules_tbl', 'existence_strategy',
    '1) la regola non ha una strategia d''esistenza: il trigger si riconosce dalla funzione');

-- Una regola di prova: lo schema non esiste, nessun runner la incontra.
CREATE FUNCTION pg_temp.regola(p_tipo text, p_modo text, p_nome text, p_params jsonb)
 RETURNS void
 LANGUAGE sql
AS $f$
    INSERT INTO dbops.automation_rules_tbl
           (enabled, rule_type, target_schema, target_table, exec_mode, name_template, params, priority, note)
    VALUES (true, p_tipo, 'pgtap_regole', 'pgtap_t', p_modo, p_nome, p_params, 999, 'pgTAP');
$f$;

SELECT throws_ok($$ SELECT pg_temp.regola('NON_ESISTE', 'AUTO', 'trg_x', '{}') $$,
    '23514', NULL, '2) un tipo di regola sconosciuto e'' rifiutato');
SELECT throws_ok($$ SELECT pg_temp.regola('TX_ID', 'auto', 'trg_{table}_x', '{}') $$,
    '23514', NULL, '3) un modo non canonico (auto) e'' rifiutato');
SELECT throws_ok($$ SELECT pg_temp.regola('CLEANUP_AT', 'AUTO', NULL, '{"ttl_days": "trenta"}') $$,
    '23514', NULL, '4) un ttl_days testuale e'' rifiutato: fermava il giro e gli INSERT dei registri');
SELECT throws_ok($$ SELECT pg_temp.regola('CLEANUP_AT', 'AUTO', NULL, '{"ttl_days": 0}') $$,
    '23514', NULL, '5) un ttl_days zero e'' rifiutato: le righe nascerebbero scadute');
SELECT throws_ok($$ SELECT pg_temp.regola('CLEANUP_AT', 'CI', NULL, '{"ttl_days": 10}') $$,
    '23514', NULL, '6) una scadenza in un modo diverso da AUTO e'' rifiutata: il trigger alla nascita non ha un modo');
SELECT throws_ok($$ SELECT pg_temp.regola('CLEANUP_PURGE', 'AUTO', NULL, '{"batch_limit": 1.5}') $$,
    '23514', NULL, '7) un batch_limit non intero e'' rifiutato');
SELECT throws_ok($$ SELECT pg_temp.regola('TX_ID', 'AUTO', NULL, '{}') $$,
    '23514', NULL, '8) una regola che monta un trigger senza il nome e'' rifiutata: il nome sta nel registro');
SELECT throws_ok($$ SELECT pg_temp.regola('ATTIVO', 'AUTO', '{"block": "trg_{parent}_{child}_{fkhash6_if_long}"}', '{}') $$,
    '23514', NULL, '9) ATTIVO senza il nome del require e'' rifiutato');
SELECT throws_ok($$ SELECT pg_temp.regola('ATTIVO', 'AUTO', '{"block": "trg_{parent}_{child}_b", "require": "trg_{child}_{parent}_r"}', '{}') $$,
    '23514', NULL, '10) ATTIVO senza l''hash della FK nei nomi e'' rifiutato: due FK della stessa coppia avrebbero un nome solo');

SELECT lives_ok($$ SELECT pg_temp.regola('CLEANUP_AT', 'AUTO', NULL,
                    '{"ttl_days": 30, "cleanup_column": "cleanup_at", "base_ts_column": "data_insert", "apply_on_update": false}') $$,
    '11) una regola di scadenza ben formata entra');

SELECT throws_ok($$ INSERT INTO dbops.automation_overrides_cols (schema_name, table_name, col_role, col_name)
                    VALUES ('pgtap_regole', 'pgtap_t', 'AUDIT_TS', 'quando') $$,
    '23514', NULL, '12) un ruolo di colonna fuori vocabolario e'' rifiutato: le colonne di audit hanno nome fisso');

-- ============================================================
-- L'ambito
-- ============================================================
SELECT is(
    (SELECT cardinality(dbops.fn_resolve_scope(NULL))),
    (SELECT count(DISTINCT s)::int FROM unnest(dbops.fn_resolve_scope(NULL)) AS u(s)),
    '13) fn_resolve_scope: uno schema con piu'' righe nel registro compare una volta');

SELECT is(
    dbops.fn_resolve_scope(ARRAY[' pgtap_regole ', 'pgtap_regole', '', '*all']),
    ARRAY['pgtap_regole'],
    '14) fn_resolve_scope: la lista del chiamante torna pulita, senza spazi, vuoti e doppi');

-- ============================================================
-- Il seed e il codice
-- ============================================================
SELECT ok(
    NOT EXISTS (SELECT 1 FROM dbops.automation_rules_tbl
                 WHERE rule_type = 'AUDIT_UPDATE'
                   AND (params ? 'audit_ts' OR params ? 'audit_user')),
    '15) la regola AUDIT_UPDATE non porta i nomi delle colonne di audit: sono fissi');

SELECT is(
    (SELECT COALESCE(array_agg(p.oid::regprocedure::text ORDER BY 1), ARRAY[]::text[])
       FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname IN ('dbops', 'script', 'maintenance')
        AND p.prokind = 'f'
        AND pg_get_functiondef(p.oid) LIKE '%existence\_strategy%'),
    ARRAY[]::text[],
    '16) nessuna funzione legge existence_strategy');

SELECT is(
    (SELECT COALESCE(array_agg(p.oid::regprocedure::text ORDER BY 1), ARRAY[]::text[])
       FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'dbops'
        AND p.prokind = 'f'
        AND pg_get_functiondef(p.oid) LIKE '%p\_function\_name => ''dbops.fn\_run\_automations''%'),
    ARRAY[]::text[],
    '17) nessun dry run firma col nome di dbops.fn_run_automations, che non esiste piu''');

SELECT * FROM finish();
ROLLBACK;
