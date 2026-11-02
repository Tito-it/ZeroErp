-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP per Zero ERP
-- Copyright (C) 2026 Tid (Michele Carlo Titini)
--
-- Rilasciato sotto GNU AGPLv3 o versione successiva.
-- Vedi LICENSE.md per il testo completo della licenza.
-- ------------------------------------------------------------
--
-- Test: le funzioni set-returning che restituiscono UNA riga lo dichiarano
--       (ROWS 1) — changeSet 20261008-21
--
-- ⛔ IL PUNTO DI QUESTO FILE. ROWS e' una proprieta' invisibile nel corpo,
--   come security_invoker sulle viste: un CREATE OR REPLACE FUNCTION che non
--   la ripete la riporta a 1000, senza errore. Nessun test di comportamento
--   se ne accorge — i risultati restano identici. Se ne accorge solo il
--   pianificatore: in vw_dash_competenza_gruppi le due funzioni stanno in
--   LATERAL, la stima si moltiplica (18,7 milioni di righe per 84 vere) e la
--   vista paga ~1 s di compilazione JIT per 20 ms di lavoro (misura dbdev
--   2026-10-08).
--
-- Elenco test (plan 4):
--  1) fn_resolve_registro_documento dichiara ROWS 1
--  2) fn_get_sorgente_documento_ref dichiara ROWS 1
--  3) ... e fn_resolve_registro_documento restituisce davvero UNA riga, anche
--     su un billing account che non esiste (il ramo «tutto NULL»)
--  4) ... e fn_get_sorgente_documento_ref restituisce davvero UNA riga, anche
--     su una sorgente che non esiste
--  ⚠️ 3 e 4 sono la controprova: ROWS 1 su una funzione che restituisse piu'
--     righe sarebbe una stima falsa nell'altro verso.
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: scattano al COMMIT, e qui il COMMIT non arriva mai.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: il test gira come gira l'applicazione (OPERATORE + RLS).
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(4);

SELECT is(
  (SELECT p.prorows::int FROM pg_proc p
     JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite' AND p.proname = 'fn_resolve_registro_documento'),
  1,
  '1) fn_resolve_registro_documento dichiara ROWS 1 (un CREATE OR REPLACE senza ROWS la riporta a 1000)');

SELECT is(
  (SELECT p.prorows::int FROM pg_proc p
     JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite' AND p.proname = 'fn_get_sorgente_documento_ref'),
  1,
  '2) fn_get_sorgente_documento_ref dichiara ROWS 1 (un CREATE OR REPLACE senza ROWS la riporta a 1000)');

SELECT is(
  (SELECT count(*)::int FROM vendite.fn_resolve_registro_documento(999999999::bigint, NULL, NULL)),
  1,
  '3) fn_resolve_registro_documento restituisce una riga anche su un billing account inesistente');

SELECT is(
  (SELECT count(*)::int FROM vendite.fn_get_sorgente_documento_ref(999999999::bigint, 'pgtap-inesistente')),
  1,
  '4) fn_get_sorgente_documento_ref restituisce una riga anche su una sorgente inesistente');

SELECT finish();

ROLLBACK;
