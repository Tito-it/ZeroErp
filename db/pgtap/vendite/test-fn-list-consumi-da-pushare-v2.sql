-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: vendite.fn_list_consumi_da_pushare — parametro p_consumo_id (v2)
-- ------------------------------------------------------------
-- Indice test (1..3):
-- 1) Firma funzione: 4 parametri (pronargs)
-- 2) p_consumo_id NULL: smoke — funzione eseguita senza eccezioni (regressione batch)
-- 3) p_consumo_id inesistente: 0 righe, no errore
-- ------------------------------------------------------------

BEGIN;
SELECT plan(3);

-- ============================================================
-- TEST 1) Firma funzione: 4 parametri
-- ============================================================
SELECT ok(
  (SELECT p.pronargs = 4
     FROM pg_proc p
     JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite'
      AND p.proname = 'fn_list_consumi_da_pushare'
    LIMIT 1),
  'fn_list_consumi_da_pushare ha 4 parametri (pronargs = 4)'
);

-- ============================================================
-- TEST 2) p_consumo_id NULL: smoke — regressione batch invariata
-- ============================================================
SELECT ok(
  (SELECT COUNT(*) >= 0
     FROM vendite.fn_list_consumi_da_pushare(p_consumo_id => NULL)),
  'p_consumo_id NULL: funzione eseguita senza eccezioni (smoke regressione batch)'
);

-- ============================================================
-- TEST 3) p_consumo_id inesistente: 0 righe, no errore
-- ============================================================
SELECT ok(
  NOT EXISTS (
    SELECT 1
    FROM vendite.fn_list_consumi_da_pushare(p_consumo_id => 999999999::bigint)
  ),
  'p_consumo_id inesistente: 0 righe, no errore'
);

SELECT * FROM finish();
ROLLBACK;
