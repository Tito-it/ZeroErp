-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Copyright (C) 2026 Tid (Michele Carlo Titini)
--
-- Rilasciato sotto GNU GPLv3 o versione successiva.
-- Vedi LICENSE.md per il testo completo della licenza.
-- ------------------------------------------------------------
-- Test: le funzioni che portano SET plan_cache_mode = force_generic_plan la
--       portano ancora. Presidio UNICO della clausola: una funzione nuova
--       che la riceve si aggiunge qui, con la sua misura datata.
--         script.fn_available_actions_ddt           (20261010-83)
--         vendite.fn_list_ddt_da_pushare            (20261010-84)
--         vendite.fn_resi_riga_tetti_accredito      (20261011-42)
--         vendite.fn_documento_lineage_nodi         (20261011-67, anche jit = off)
--         vendite.fn_documento_lineage_archi        (20261011-67, anche jit = off)
--       Brief: brief-db-segment-base-commesse-attivita §6 (le prime due),
--       brief-db-plancache-funzioni-con-query-incorporate §5bis (la terza),
--       brief-db-lineage-seminata-per-chiave §8.4 (le due della lineage).
--       Sostituisce test-fn-available-actions-ddt-piano-generico-v1.
--
-- Elenco test (plan 7):
--  1) ⭐ la capability del DDT porta la clausola
--  2) la clausola non cambia il contratto: la capability risponde un blob per
--     un DDT costruito, e NULL per un id che non esiste
--  3) ⭐ il lister dei DDT da spingere porta la clausola (chiamato per DDT dal
--     backend: auto 1,30 s, generico 0,45 s su 56 chiamate, dbdev come app,
--     2026-10-10)
--  4) ⭐ i tetti dell'accredito portano la clausola, ACCANTO a SET search_path
--     (SECURITY DEFINER: un CREATE OR REPLACE deve ripeterle tutte e due).
--     Guard del ponte: auto 7,1 ms, generico 1,5 ms a chiamata, dbdev come
--     app, 2026-10-11
--  5) i tetti, con la clausola, rispondono 0|0 su una riga che non esiste
--     (il fail-closed della funzione non dipende dal piano)
--  6) ⭐ fn_documento_lineage_nodi porta plan_cache_mode = force_generic_plan
--     E jit = off
--  7) ⭐ fn_documento_lineage_archi, idem. Con un seme non costante il piano
--     tiene i rami dei due modi, e il JIT ne compilava le espressioni a ogni
--     chiamata: ~4,8 s contro 25 ms, anche a database vuoto (dbdev come app,
--     2026-10-11). Sono SQL: la clausola le rende non incorporabili, e si
--     pianificano una volta per sessione
--
-- ⛔ IL PUNTO DI QUESTO FILE. La clausola e' una proprieta' invisibile nel
--   corpo, come ROWS (20261008-21) e COST (20261010-77): un CREATE OR REPLACE
--   FUNCTION che non ripete `SET plan_cache_mode = force_generic_plan` la
--   perde, con risultati identici. Se ne accorge solo il tempo: in modo `auto`
--   la plancache ripianifica a ogni chiamata la query incorporata con un
--   parametro (capability su 56 DDT: generico 0,61 s, auto 1,42 s — dbdev
--   come app, 2026-10-10).
-- ⛔ La clausola non si mette «per igiene»: entra in questo elenco solo una
--   funzione su cui la misura ha mostrato il difetto.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(7);

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

SELECT ok(
  (SELECT 'plan_cache_mode=force_generic_plan' = ANY (coalesce(p.proconfig, ARRAY[]::text[]))
      AND EXISTS (SELECT 1 FROM unnest(p.proconfig) c WHERE c LIKE 'search\_path=%')
     FROM pg_proc p
    WHERE p.oid = 'vendite.fn_resi_riga_tetti_accredito(bigint, bigint)'::regprocedure),
  '4) fn_resi_riga_tetti_accredito porta SET plan_cache_mode = force_generic_plan accanto a SET search_path (un CREATE OR REPLACE senza le clausole le perde)');

SELECT is(
  (SELECT t.accredito_dovuto::text || '|' || t.qta_riga_fattura::text
     FROM vendite.fn_resi_riga_tetti_accredito(-1, -1) t),
  '0|0',
  '5) con la clausola i tetti restano fail-closed: 0|0 su una riga di reso e una riga di fattura che non esistono');

SELECT ok(
  (SELECT coalesce(p.proconfig, ARRAY[]::text[]) @> ARRAY['plan_cache_mode=force_generic_plan', 'jit=off']
     FROM pg_proc p
    WHERE p.oid = 'vendite.fn_documento_lineage_nodi(bigint[], text[])'::regprocedure),
  '6) fn_documento_lineage_nodi porta SET plan_cache_mode = force_generic_plan e SET jit = off (un CREATE OR REPLACE senza le clausole le perde)');

SELECT ok(
  (SELECT coalesce(p.proconfig, ARRAY[]::text[]) @> ARRAY['plan_cache_mode=force_generic_plan', 'jit=off']
     FROM pg_proc p
    WHERE p.oid = 'vendite.fn_documento_lineage_archi(bigint[], text[])'::regprocedure),
  '7) fn_documento_lineage_archi porta SET plan_cache_mode = force_generic_plan e SET jit = off (un CREATE OR REPLACE senza le clausole le perde)');

SELECT * FROM finish();
ROLLBACK;
