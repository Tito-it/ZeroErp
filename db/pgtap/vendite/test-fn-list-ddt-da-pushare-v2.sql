-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: vendite.fn_list_ddt_da_pushare — parametro p_ddt_id (v2)
-- ------------------------------------------------------------
-- Indice test (1..4):
-- 1) Firma funzione: 4 parametri (pronargs)
-- 2) p_ddt_id NULL: smoke — funzione eseguita senza eccezioni (regressione batch)
-- 3) p_ddt_id inesistente: 0 righe, no errore
-- 4) uom_id non NULL per righe pushable (fix bug proiezione NULL)
-- ------------------------------------------------------------

BEGIN;
SELECT plan(4);

-- ============================================================
-- TEST 1) Firma funzione: 4 parametri
-- ============================================================
SELECT ok(
  (SELECT p.pronargs = 4
     FROM pg_proc p
     JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite'
      AND p.proname = 'fn_list_ddt_da_pushare'
    LIMIT 1),
  'fn_list_ddt_da_pushare ha 4 parametri (pronargs = 4)'
);

-- ============================================================
-- TEST 2) p_ddt_id NULL: smoke — regressione batch invariata
-- ============================================================
SELECT ok(
  (SELECT COUNT(*) >= 0
     FROM vendite.fn_list_ddt_da_pushare(p_ddt_id => NULL)),
  'p_ddt_id NULL: funzione eseguita senza eccezioni (smoke regressione batch)'
);

-- ============================================================
-- TEST 3) p_ddt_id inesistente: 0 righe, no errore
-- ============================================================
SELECT ok(
  NOT EXISTS (
    SELECT 1
    FROM vendite.fn_list_ddt_da_pushare(p_ddt_id => 999999999::bigint)
  ),
  'p_ddt_id inesistente: 0 righe, no errore'
);

-- ============================================================
-- TEST 4) uom_id non NULL per righe pushable (fix bug proiezione NULL)
-- ============================================================
SELECT ok(
  NOT EXISTS (
    SELECT 1 FROM vendite.fn_list_ddt_da_pushare(p_limit => 1) WHERE uom_id IS NULL
  ),
  'fn_list_ddt_da_pushare: uom_id valorizzato da catalogo.articoli (fix bug proiezione NULL)'
);

SELECT * FROM finish();
ROLLBACK;
