-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test — P-3 di brief-db-osservabilita-lotto-fermo-r6-indici: gli
--   indici delle due letture trasversali (il giornale per finestra, error_log
--   per area/funzione/tx_id) e l'indice FK acceso su fatturazione_lotti_log.
--   ChangeSet: 20260919-05 (giornale), -06 (error_log), -07 (policy FK).
--
-- ⭐ COSA PRESIDIA QUESTO FILE, IN UNA RIGA:
--     ogni filtro che il backend dichiarera' in whitelist (pezzi E e G del
--     piano) ha un indice da cui partire — e il prefisso su function_name lo
--     ha con l'opclass giusta, perche' con la collation it_IT un btree
--     ordinario non serve un LIKE 'x%'.
--
-- ⚠️ E' un test di STRUTTURA (has_index, opclass, la riga di policy). Il
--   piano di esecuzione NON si asserisce qui: su un database ricostruito da
--   zero le tabelle sono vuote e il planner sceglie il seq scan per costo, non
--   per mancanza di indice — un EXPLAIN pinnato sarebbe rosso per il motivo
--   sbagliato. L'EXPLAIN sul DB vero, per ogni filtro, lo fa il backend prima
--   di consegnare (piano BE/FE §3.1 e §4.1).
--
-- ⚠️ Il test 9 guarda l'indice che dbops.apply_fk_index_policy() crea in
--   90_end (runAlways): su un migrate ordinario c'e'. La riga di policy (test
--   8) e' cio' che lo chiede, l'indice e' cio' che ne e' uscito.
--
-- Elenco test (plan 10):
--  1-4) giornale: un indice per tempo su ciascuna delle quattro sorgenti
--  5)   error_log: (occurred_at)
--  6)   error_log: (area, occurred_at) e (tx_id)
--  7)   error_log: (function_name, occurred_at) con text_pattern_ops sulla prima
--  8)   policy FK: fk_fatturazione_lotti_log_lotto e' consentito = true, col
--       dll_command che nomina l'indice canonico
--  9)   l'indice FK ix_fatturazione_lotti_log_lotto_id esiste
-- 10)   nessuno dei nuovi e' un duplicato esatto (dbops.vw_duplicate_indexes)
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(10);

-- ============================================================
-- 1-4) Il giornale per tempo
-- ============================================================
SELECT has_index('vendite', 'event_log', 'ix_event_log_event_time', ARRAY['event_time'],
    '1. event_log: indice per tempo (event_time)');
SELECT has_index('vendite', 'fatture_log', 'ix_fatture_log_data_ora', ARRAY['data_ora'],
    '2. fatture_log: indice per tempo (data_ora)');
SELECT has_index('vendite', 'fatturazione_lotti_log', 'ix_fatturazione_lotti_log_data_ora', ARRAY['data_ora'],
    '3. fatturazione_lotti_log: indice per tempo (data_ora)');
SELECT has_index('vendite', 'fatturazione_lotti_task_runs', 'ix_fatturazione_lotti_task_runs_started_at', ARRAY['started_at'],
    '4. fatturazione_lotti_task_runs: indice per tempo (started_at, la colonna di `quando` dal 19-09)');

-- ============================================================
-- 5-7) error_log
-- ============================================================
SELECT has_index('dbops', 'error_log', 'ix_error_log_occurred_at', ARRAY['occurred_at'],
    '5. error_log: la finestra (occurred_at)');

SELECT ok(
    (SELECT count(*) FROM pg_indexes
      WHERE schemaname = 'dbops' AND tablename = 'error_log'
        AND indexname IN ('ix_error_log_area_occurred_at', 'ix_error_log_tx_id')) = 2,
    '6. error_log: (area, occurred_at) e (tx_id)'
);

-- ⛔ L'opclass e' il punto: con la collation it_IT.UTF-8 un btree ordinario su
--   function_name NON serve `LIKE 'fn_x%'`. text_pattern_ops sulla prima
--   colonna serve `=` e il prefisso; l'ORDER BY sta sulla seconda.
SELECT is(
    (SELECT string_agg(oc.opcname, ',' ORDER BY k.ord)
       FROM pg_index i
       JOIN pg_class c ON c.oid = i.indexrelid
       JOIN pg_namespace n ON n.oid = c.relnamespace
       CROSS JOIN LATERAL unnest(i.indclass) WITH ORDINALITY AS k(opc, ord)
       JOIN pg_opclass oc ON oc.oid = k.opc
      WHERE n.nspname = 'dbops' AND c.relname = 'ix_error_log_function_name_occurred_at'),
    'text_pattern_ops,timestamptz_ops',
    '7. error_log: (function_name text_pattern_ops, occurred_at) — il prefisso usa l''indice'
);

-- ============================================================
-- 8-9) La FK di fatturazione_lotti_log, decisa e accesa
-- ============================================================
SELECT is(
    (SELECT (p.consentito, p.dll_command LIKE 'CREATE INDEX IF NOT EXISTS ix_fatturazione_lotti_log_lotto_id ON %')::text
       FROM dbops.fk_index_policy p
      WHERE p.schema_name = 'vendite' AND p.table_name = 'fatturazione_lotti_log'
        AND p.constraint_name = 'fk_fatturazione_lotti_log_lotto'),
    (true, true)::text,
    '8. policy FK: fk_fatturazione_lotti_log_lotto consentito = true, dll_command col nome canonico'
);

SELECT has_index('vendite', 'fatturazione_lotti_log', 'ix_fatturazione_lotti_log_lotto_id', ARRAY['lotto_id'],
    '9. l''indice FK ix_fatturazione_lotti_log_lotto_id esiste (creato da apply_fk_index_policy in 90_end)');

-- ============================================================
-- 10) Niente duplicati esatti
-- ============================================================
SELECT is(
    (SELECT count(*)::int FROM dbops.vw_duplicate_indexes d
      WHERE d::text LIKE '%ix_error_log_%'
         OR d::text LIKE '%ix_event_log_event_time%'
         OR d::text LIKE '%ix_fatture_log_data_ora%'
         OR d::text LIKE '%ix_fatturazione_lotti_log_%'
         OR d::text LIKE '%ix_fatturazione_lotti_task_runs_started_at%'),
    0,
    '10. nessuno degli indici nuovi e'' un duplicato esatto di uno esistente'
);

SELECT * FROM finish();
ROLLBACK;
