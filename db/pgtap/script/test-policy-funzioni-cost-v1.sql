-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP per Zero ERP
-- Copyright (C) 2026 Tid (Michele Carlo Titini)
--
-- Rilasciato sotto GNU GPLv3 o versione successiva.
-- Vedi LICENSE.md per il testo completo della licenza.
-- ------------------------------------------------------------
--
-- Test: ogni funzione chiamata da una policy RLS dichiara il proprio costo
--       (COST >= 1000) — changeSet 20261010-77
--
-- ⛔ IL PUNTO DI QUESTO FILE. COST e' una proprieta' invisibile nel corpo,
--   come ROWS (20261008-21) e security_invoker: un CREATE OR REPLACE FUNCTION
--   che non la ripete la riporta al default 100, senza errore e con risultati
--   identici. Se ne accorge solo il pianificatore: col default una policy vale
--   0,25 unita' a riga mentre ne costa ~10-35 (0,16-0,56 ms, misura dbdev
--   come app del 2026-10-10), e allora valutarla su TUTTA la tabella gli
--   sembra piu' conveniente che cercare per chiave. Caso:
--   vendite.fn_partite_merce su un DDT, ~33 ms su 47 in Seq Scan sotto policy.
--
-- ⭐ L'INSIEME SI DERIVA, NON SI ELENCA. Le funzioni sotto esame sono quelle
--   nominate da `qual` o `with_check` di pg_policies, non l'elenco del
--   changeSet: una policy nuova che chiama una funzione senza COST rende
--   questo test rosso da sola, senza che nessuno aggiorni una lista.
--
-- ⚠️ LA SOGLIA E' 1000, NON 5000. La proprieta' e' «il costo dichiarato e'
--   nell'ordine di grandezza vero», non «e' scritto 5000»: chi misura e
--   dichiara un valore diverso nello stesso ordine non e' un difetto. Il
--   default (100) e qualunque valore di quell'ordine restano rossi.
--
-- Elenco test (plan 3):
--  1) la derivazione non e' cieca: trova le funzioni di policy, e fra loro
--     la canarina script.fn_scope_ef_whitelist_via_ddt (il caso del DDT)
--  2) ⭐ nessuna funzione chiamata da una policy ha COST < 1000 — il messaggio
--     nomina le inadempienti
--  3) ogni nome trovato nelle policy risolve a una funzione (un nome che non
--     risolve uscirebbe dal test 2 senza essere misurato)
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: scattano al COMMIT, e qui il COMMIT non arriva mai.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: il test gira come gira l'applicazione (OPERATORE + RLS).
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(3);

-- I nomi di funzione che le policy chiamano, da qual e da with_check.
CREATE TEMP TABLE _nomi_policy AS
SELECT DISTINCT m[1] AS fn
  FROM pg_policies,
       regexp_matches(coalesce(qual, '') || ' ' || coalesce(with_check, ''),
                      '(fn_\w+)\s*\(', 'g') m;

-- ...e le funzioni a cui risolvono (fuori dai cataloghi di sistema).
CREATE TEMP TABLE _fn_policy AS
-- ⚠️ Schema e nome dal catalogo, non `oid::regprocedure::text`: come app lo
--   schema script sta nel search_path e il testo uscirebbe senza `script.`.
SELECT n.nspname || '.' || p.proname
         || '(' || pg_get_function_identity_arguments(p.oid) || ')' AS funzione,
       n.nspname AS sch, p.proname AS nome, p.procost
  FROM _nomi_policy x
  JOIN pg_proc p ON p.proname = x.fn
  JOIN pg_namespace n ON n.oid = p.pronamespace
 WHERE n.nspname NOT IN ('pg_catalog', 'information_schema');

SELECT ok(
  (SELECT count(*) FROM _fn_policy) > 0
  AND EXISTS (SELECT 1 FROM _fn_policy
               WHERE sch = 'script' AND nome = 'fn_scope_ef_whitelist_via_ddt'),
  format('1) le policy nominano %s funzioni, fra cui script.fn_scope_ef_whitelist_via_ddt (la derivazione vede)',
         (SELECT count(*) FROM _fn_policy)));

SELECT is(
  (SELECT coalesce(string_agg(funzione || ' = ' || procost, ', ' ORDER BY funzione), '')
     FROM _fn_policy
    WHERE procost < 1000),
  '',
  '2) ogni funzione chiamata da una policy dichiara COST >= 1000 (un CREATE OR REPLACE senza COST la riporta a 100)');

SELECT is(
  (SELECT coalesce(string_agg(x.fn, ', ' ORDER BY x.fn), '')
     FROM _nomi_policy x
    WHERE NOT EXISTS (SELECT 1 FROM pg_proc p WHERE p.proname = x.fn)),
  '',
  '3) ogni nome di funzione trovato nelle policy risolve a una funzione');

SELECT finish();

ROLLBACK;
