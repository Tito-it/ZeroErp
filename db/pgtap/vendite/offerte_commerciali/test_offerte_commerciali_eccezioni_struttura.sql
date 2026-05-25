-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: struttura vendite.offerte_commerciali_eccezioni (Step 3).
--       Mirror fedele di contratti_righe: enum tipo_eccezione_contratto,
--       5 CHECK semantici, 2 UNIQUE parziali, esclusione campi I4.
--
-- Indice test (1..10):
--   1)  Tabella vendite.offerte_commerciali_eccezioni esiste
--   2)  tipo_eccezione usa enum vendite.tipo_eccezione_contratto (B3)
--   3)  fonte_quantita_attesa NOT NULL
--   4)  CHECK chk_offerte_eccezioni_tipo_erog presente
--   5)  CHECK chk_offerte_eccezioni_fonte_qta presente
--   6)  CHECK chk_offerte_eccezioni_coerenza_canone presente
--   7)  CHECK chk_offerte_eccezioni_coerenza_fonte_erogazione presente
--   8)  CHECK chk_offerte_eccezioni_prezzo_per_tipo_eccezione presente
--   9)  UNIQUE parziale uq_offerte_eccezioni_one_eccezione_per_articolo presente
--  10)  Campi I4 assenti: stato_approvazione_prezzo e pratica_approvazione_prezzo_id
-- ------------------------------------------------------------

BEGIN;
SELECT plan(10);

-- ============================================================
-- 1) Tabella esiste
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM information_schema.tables
         WHERE table_schema = 'vendite'
           AND table_name   = 'offerte_commerciali_eccezioni'
    ),
    '1) vendite.offerte_commerciali_eccezioni esiste'
);

-- ============================================================
-- 2) tipo_eccezione usa enum vendite.tipo_eccezione_contratto (B3)
--    Il riuso dello stesso enum rende il push 1:1 triviale.
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1
          FROM information_schema.columns c
          JOIN pg_attribute a   ON a.attname = c.column_name
          JOIN pg_class t       ON t.oid = a.attrelid
          JOIN pg_namespace nt  ON nt.oid = t.relnamespace
          JOIN pg_type ty       ON ty.oid = a.atttypid
          JOIN pg_namespace nty ON nty.oid = ty.typnamespace
         WHERE c.table_schema = 'vendite'
           AND c.table_name   = 'offerte_commerciali_eccezioni'
           AND c.column_name  = 'tipo_eccezione'
           AND ty.typname     = 'tipo_eccezione_contratto'
           AND nty.nspname    = 'vendite'
    ),
    '2) tipo_eccezione usa enum vendite.tipo_eccezione_contratto (B3)'
);

-- ============================================================
-- 3) fonte_quantita_attesa NOT NULL
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM information_schema.columns
         WHERE table_schema = 'vendite'
           AND table_name   = 'offerte_commerciali_eccezioni'
           AND column_name  = 'fonte_quantita_attesa'
           AND is_nullable  = 'NO'
    ),
    '3) fonte_quantita_attesa NOT NULL (specchio contratti_righe I3)'
);

-- ============================================================
-- 4) CHECK chk_offerte_eccezioni_tipo_erog (specchio chk_contrighe_tipo_erog)
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_constraint c
          JOIN pg_class t   ON t.oid = c.conrelid
          JOIN pg_namespace n ON n.oid = t.relnamespace
         WHERE n.nspname = 'vendite'
           AND t.relname = 'offerte_commerciali_eccezioni'
           AND c.conname = 'chk_offerte_eccezioni_tipo_erog'
           AND c.contype = 'c'
    ),
    '4) CHECK chk_offerte_eccezioni_tipo_erog presente (I3)'
);

-- ============================================================
-- 5) CHECK chk_offerte_eccezioni_fonte_qta (specchio chk_contrighe_fonte_qta)
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_constraint c
          JOIN pg_class t   ON t.oid = c.conrelid
          JOIN pg_namespace n ON n.oid = t.relnamespace
         WHERE n.nspname = 'vendite'
           AND t.relname = 'offerte_commerciali_eccezioni'
           AND c.conname = 'chk_offerte_eccezioni_fonte_qta'
           AND c.contype = 'c'
    ),
    '5) CHECK chk_offerte_eccezioni_fonte_qta presente (I3)'
);

-- ============================================================
-- 6) CHECK chk_offerte_eccezioni_coerenza_canone
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_constraint c
          JOIN pg_class t   ON t.oid = c.conrelid
          JOIN pg_namespace n ON n.oid = t.relnamespace
         WHERE n.nspname = 'vendite'
           AND t.relname = 'offerte_commerciali_eccezioni'
           AND c.conname = 'chk_offerte_eccezioni_coerenza_canone'
           AND c.contype = 'c'
    ),
    '6) CHECK chk_offerte_eccezioni_coerenza_canone presente (I3)'
);

-- ============================================================
-- 7) CHECK chk_offerte_eccezioni_coerenza_fonte_erogazione
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_constraint c
          JOIN pg_class t   ON t.oid = c.conrelid
          JOIN pg_namespace n ON n.oid = t.relnamespace
         WHERE n.nspname = 'vendite'
           AND t.relname = 'offerte_commerciali_eccezioni'
           AND c.conname = 'chk_offerte_eccezioni_coerenza_fonte_erogazione'
           AND c.contype = 'c'
    ),
    '7) CHECK chk_offerte_eccezioni_coerenza_fonte_erogazione presente (I3)'
);

-- ============================================================
-- 8) CHECK chk_offerte_eccezioni_prezzo_per_tipo_eccezione
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_constraint c
          JOIN pg_class t   ON t.oid = c.conrelid
          JOIN pg_namespace n ON n.oid = t.relnamespace
         WHERE n.nspname = 'vendite'
           AND t.relname = 'offerte_commerciali_eccezioni'
           AND c.conname = 'chk_offerte_eccezioni_prezzo_per_tipo_eccezione'
           AND c.contype = 'c'
    ),
    '8) CHECK chk_offerte_eccezioni_prezzo_per_tipo_eccezione presente (I3)'
);

-- ============================================================
-- 9) UNIQUE parziale per (offerta_id, articolo_id) su OVERRIDE/ESCLUSIONE
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_indexes
         WHERE schemaname = 'vendite'
           AND tablename  = 'offerte_commerciali_eccezioni'
           AND indexname  = 'uq_offerte_eccezioni_one_eccezione_per_articolo'
    ),
    '9) UNIQUE parziale uq_offerte_eccezioni_one_eccezione_per_articolo presente'
);

-- ============================================================
-- 10) Campi I4 assenti: NO stato_approvazione_prezzo, NO pratica_approvazione_prezzo_id
--     (non previsti per l''offerta pre-negoziazione)
-- ============================================================
SELECT ok(
    NOT EXISTS (
        SELECT 1 FROM information_schema.columns
         WHERE table_schema = 'vendite'
           AND table_name   = 'offerte_commerciali_eccezioni'
           AND column_name IN ('stato_approvazione_prezzo', 'pratica_approvazione_prezzo_id')
    ),
    '10) Campi I4 assenti: stato_approvazione_prezzo e pratica_approvazione_prezzo_id non presenti'
);

SELECT * FROM finish();
ROLLBACK;
