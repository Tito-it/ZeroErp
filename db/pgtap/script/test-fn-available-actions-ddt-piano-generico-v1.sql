-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Copyright (C) 2026 Tid (Michele Carlo Titini)
--
-- Rilasciato sotto GNU GPLv3 o versione successiva.
-- Vedi LICENSE.md per il testo completo della licenza.
-- ------------------------------------------------------------
-- Test: le funzioni plpgsql che chiamano la diagnosi del push con un
--       parametro si pianificano una volta (plan_cache_mode =
--       force_generic_plan): script.fn_available_actions_ddt (20261010-83) e
--       vendite.fn_list_ddt_da_pushare (20261010-84).
--       Brief: brief-db-segment-base-commesse-attivita §6.
--
-- Elenco test (plan 3):
--  1) ⭐ la capability porta la clausola SET plan_cache_mode = force_generic_plan
--  2) la clausola non cambia il contratto: la capability risponde un blob per
--     un DDT costruito, e NULL per un id che non esiste
--  3) ⭐ il lister porta la stessa clausola (chiamato per DDT dal backend:
--     auto 1,30 s, generico 0,45 s su 56 chiamate, dbdev come app, 2026-10-10)
--
-- ⛔ IL PUNTO DI QUESTO FILE. La clausola e' una proprieta' invisibile nel
--   corpo, come ROWS (20261008-21) e COST (20261010-77): un CREATE OR REPLACE
--   FUNCTION che non ripete `SET plan_cache_mode = force_generic_plan` la
--   perde, con risultati identici. Se ne accorge solo il tempo: in modo `auto`
--   la plancache ripianificava a ogni chiamata la diagnosi incorporata
--   (capability su 56 DDT: generico 0,61 s, auto 1,42 s — dbdev come app,
--   2026-10-10).
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(3);

SELECT ok(
  (SELECT 'plan_cache_mode=force_generic_plan' = ANY (coalesce(p.proconfig, ARRAY[]::text[]))
     FROM pg_proc p
    WHERE p.oid = 'script.fn_available_actions_ddt(bigint)'::regprocedure),
  '1) fn_available_actions_ddt porta SET plan_cache_mode = force_generic_plan (un CREATE OR REPLACE senza la clausola la perde)');

-- Un DDT in bozza, costruito: il contratto del blob non dipende dal piano.
CREATE TEMP TABLE tmp_cli_pg AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('pgtap_piano_generico');

CREATE TEMP TABLE tmp_ddt_pg AS
WITH ins AS (
  INSERT INTO vendite.ddt (destinatario_soggetto_ruolo_id, stato_doc_ddt_id, data,
      billing_account_id, valuta_id, emittente_fiscale_id, storicizza, meta)
  SELECT c.soggetto_ruolo_id,
         (SELECT s.id FROM config.stati_doc_ddt s WHERE s.codice_interno = 'DRAFT' LIMIT 1),
         DATE '2026-09-01', c.billing_account_id,
         (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1),
         script.fn_pgtap_emittente_operatore(),
         false, jsonb_build_object('test_scope', 'pgtap_piano_generico')
    FROM tmp_cli_pg c
  RETURNING id)
SELECT id AS ddt_id FROM ins;

SELECT is(
  (SELECT (script.fn_available_actions_ddt(ddt_id) ->> 'stato_codice') FROM tmp_ddt_pg)
    || '|' || COALESCE(script.fn_available_actions_ddt(-1)::text, 'NULL'),
  'DRAFT|NULL',
  '2) con la clausola il contratto non cambia: blob per il DDT costruito, NULL per un id inesistente');

SELECT ok(
  (SELECT 'plan_cache_mode=force_generic_plan' = ANY (coalesce(p.proconfig, ARRAY[]::text[]))
     FROM pg_proc p
    WHERE p.oid = 'vendite.fn_list_ddt_da_pushare(date, bigint, integer, bigint)'::regprocedure),
  '3) fn_list_ddt_da_pushare porta SET plan_cache_mode = force_generic_plan (un CREATE OR REPLACE senza la clausola la perde)');

SELECT * FROM finish();
ROLLBACK;
