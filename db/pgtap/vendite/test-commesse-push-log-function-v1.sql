-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: vendite.fn_log_commessa_push_run (changeset 20260224-40)
-- ------------------------------------------------------------
-- Indice test (1..7):
-- 1) funzione presente
-- 2) stato vuoto -> errore
-- 3) stato invalido -> errore
-- 4) durata negativa -> errore
-- 5) insert COMPLETATO -> id valorizzato
-- 6) stato normalizzato in uppercase
-- 7) payload source_types/risultato persistito
-- ------------------------------------------------------------

BEGIN;
SELECT plan(7);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite'
      AND p.proname = 'fn_log_commessa_push_run'
  ),
  'funzione presente'
);

SELECT throws_ok(
  $$ SELECT vendite.fn_log_commessa_push_run(p_stato => '   '); $$,
  'P0001',
  NULL,
  'stato vuoto -> errore'
);

SELECT throws_ok(
  $$ SELECT vendite.fn_log_commessa_push_run(p_stato => 'KO'); $$,
  'P0001',
  NULL,
  'stato invalido -> errore'
);

SELECT throws_ok(
  $$ SELECT vendite.fn_log_commessa_push_run(p_stato => 'COMPLETATO', p_durata_ms => -1); $$,
  'P0001',
  NULL,
  'durata negativa -> errore'
);

CREATE TEMP TABLE tmp_push_log_ok AS
SELECT vendite.fn_log_commessa_push_run(
  p_dry_run => true,
  p_source_types => ARRAY['HandlerPreventivi', 'HandlerOrdini'],
  p_risultato => jsonb_build_object('HandlerPreventivi', jsonb_build_object('created', 3, 'errors', '[]'::jsonb)),
  p_stato => 'COMPLETATO',
  p_durata_ms => 1500
) AS push_log_id;

SELECT ok(
  (SELECT push_log_id IS NOT NULL FROM tmp_push_log_ok),
  'insert COMPLETATO -> id valorizzato'
);

CREATE TEMP TABLE tmp_push_log_upper AS
SELECT vendite.fn_log_commessa_push_run(
  p_stato => 'parziale'
) AS push_log_id;

SELECT is(
  (
    SELECT l.stato
    FROM vendite.commesse_push_log l
    WHERE l.id = (SELECT push_log_id FROM tmp_push_log_upper)
  ),
  'PARZIALE'::varchar,
  'stato normalizzato in uppercase'
);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM vendite.commesse_push_log l
    WHERE l.id = (SELECT push_log_id FROM tmp_push_log_ok)
      AND l.source_types = ARRAY['HandlerPreventivi', 'HandlerOrdini']::text[]
      AND l.risultato ? 'HandlerPreventivi'
  ),
  'payload source_types/risultato persistito'
);

SELECT * FROM finish();
ROLLBACK;
