-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-contesto: escluso — il file legge solo lo scope e le regole delle
--   automazioni e il catalogo di PostgreSQL: nessun dato di dominio, nessuna
--   RLS. Una veste applicativa non cambierebbe nessuna risposta.
-- pgTAP test per Zero ERP
--
-- I cinque registri di dbops scadono: idempotency_keys, request_log,
-- error_log, audit_log, ai_query_log.
--   Brief: brief-be-verifica-documentazione-api, D5 e §I.5
--   80_data: automation_scope.csv (le quattro righe dbops), automation_rules_tbl.csv
--   (regole 14, 24, 25, 26); 20_code: 20261023-02 (trigger alla nascita sui primi due).
--   ai_query_log: brief-db-revisione-dbops giro 7 (D36, Q4): scope, regola 28 (90
--   giorni, base data_insert), trigger alla nascita 20261108-28.
--
-- ⭐ COSA PRESIDIA: una tabella con cleanup_at si pulisce SOLO se sta nello
--   scope delle automazioni. Fino al 2026-10-23 nessuno dei quattro c'era in
--   git: su dbdev due erano nello scope per righe scritte a mano, da zero
--   nessuno scadeva.
--
-- ⚠️ error_log e audit_log NON hanno il trigger alla nascita, di proposito: li
--   scrivono anche sessioni dblink (script.fn_log_error_only, dbops.fn_audit_log_once)
--   con un ruolo che non legge dbops.automation_rules_tbl, e il trigger farebbe
--   fallire la registrazione. La scadenza la calcola il job (fn_apply_cleanup_at).
--   Il test 4 lo tiene fermo: chi aggiungesse il trigger «per uniformita'» rompe
--   il log degli errori.
--
-- Elenco test (plan 4):
--   1) i cinque registri sono nello scope delle automazioni
--   2) ciascuno ha la sua regola: termine e colonna base
--   3) la colonna base di ogni regola esiste sulla sua tabella
--   4) il trigger alla nascita c'e' su idempotency_keys, request_log e
--      ai_query_log, NON su error_log e audit_log
-- ------------------------------------------------------------

-- ⚠️ 1. TRANSAZIONE.
BEGIN;

-- ⚠️ 3. VINCOLI DIFFERITI.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(4);

SELECT ok(
    dbops.fn_table_in_scope('dbops', 'idempotency_keys')
    AND dbops.fn_table_in_scope('dbops', 'request_log')
    AND dbops.fn_table_in_scope('dbops', 'error_log')
    AND dbops.fn_table_in_scope('dbops', 'audit_log')
    AND dbops.fn_table_in_scope('dbops', 'ai_query_log'),
    '1) I cinque registri di dbops sono nello scope: il purge li vede');

SELECT results_eq(
    $q$SELECT t.tabella, (p ->> 'ttl_days')::int, p ->> 'base_ts_column'
         FROM (VALUES ('ai_query_log'), ('audit_log'), ('error_log'), ('idempotency_keys'), ('request_log')) t(tabella)
         CROSS JOIN LATERAL dbops.fn_cleanup_at_params('dbops', t.tabella) p
        ORDER BY t.tabella$q$,
    $q$VALUES ('ai_query_log'::text,     90, 'data_insert'::text),
              ('audit_log'::text,        90, 'executed_at'::text),
              ('error_log'::text,        90, 'occurred_at'::text),
              ('idempotency_keys'::text,  1, 'data_insert'::text),
              ('request_log'::text,      90, NULL::text)$q$,
    '2) Le regole: audit_log, error_log e ai_query_log 90 giorni (come request_log), le key un giorno');

SELECT ok(
    dbops.fn_col_exists('dbops', 'audit_log',        'executed_at')
    AND dbops.fn_col_exists('dbops', 'error_log',        'occurred_at')
    AND dbops.fn_col_exists('dbops', 'idempotency_keys', 'data_insert')
    AND dbops.fn_col_exists('dbops', 'ai_query_log',     'data_insert'),
    '3) La colonna base di ogni regola esiste: altrimenti il job salterebbe la tabella (MISSING_BASE_TS_COLUMN)');

-- set_eq e non results_eq: relname e' di tipo name, e un ORDER BY sul cast a
--   text non sa quale collation usare.
SELECT set_eq(
    $q$SELECT c.relname::text
         FROM pg_trigger t
         JOIN pg_class c     ON c.oid = t.tgrelid
         JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE NOT t.tgisinternal
          AND n.nspname = 'dbops'
          AND c.relname IN ('idempotency_keys', 'request_log', 'error_log', 'audit_log', 'ai_query_log')
          AND t.tgfoid = 'dbops.trgfn_cleanup_at_alla_nascita()'::regprocedure$q$,
    $q$VALUES ('idempotency_keys'::text), ('request_log'::text), ('ai_query_log'::text)$q$,
    '4) Trigger alla nascita su idempotency_keys, request_log e ai_query_log, NON su error_log e audit_log (li scrive anche il dblink)');

SELECT * FROM finish();
ROLLBACK;
