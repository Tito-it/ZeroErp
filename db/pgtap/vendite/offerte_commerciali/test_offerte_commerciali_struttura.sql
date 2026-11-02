-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: struttura vendite.offerte_commerciali (Step 2).
--       Verifica esistenza tabella, colonne strutturali, vincoli,
--       FK, CHECK e addenda A1/A2 (motivazione_rifiuto, data_annullamento).
--
-- Indice test (1..12):
--   1)  Tabella vendite.offerte_commerciali esiste
--   2)  uid NOT NULL UNIQUE
--   3)  codice NOT NULL UNIQUE
--   4)  istanza_utility_id NOT NULL (B2)
--   5)  utility_id NOT NULL (B2)
--   6)  data_annullamento presente (addendum A2)
--   7)  motivazione_rifiuto presente (addendum A1)
--   8)  FK fk_offerte_commerciali_stato_doc presente
--   9)  FK fk_offerte_commerciali_revisione_padre self-ref presente
--  10)  CHECK chk_offerte_tipo_variazione_globale presente
--  11)  CHECK chk_offerte_variazione_globale_coerenza presente
--  12)  CHECK chk_offerte_revisione_numero presente
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;
SELECT plan(12);

-- ============================================================
-- 1) Tabella esiste
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM information_schema.tables
         WHERE table_schema = 'vendite'
           AND table_name   = 'offerte_commerciali'
    ),
    '1) vendite.offerte_commerciali esiste'
);

-- ============================================================
-- 2) uid NOT NULL UNIQUE
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM information_schema.columns
         WHERE table_schema = 'vendite'
           AND table_name   = 'offerte_commerciali'
           AND column_name  = 'uid'
           AND is_nullable  = 'NO'
    )
    AND EXISTS (
        SELECT 1 FROM pg_constraint c
          JOIN pg_class t   ON t.oid = c.conrelid
          JOIN pg_namespace n ON n.oid = t.relnamespace
         WHERE n.nspname  = 'vendite'
           AND t.relname  = 'offerte_commerciali'
           AND c.conname  = 'uq_offerte_commerciali_uid'
           AND c.contype  = 'u'
    ),
    '2) uid NOT NULL + UNIQUE uq_offerte_commerciali_uid'
);

-- ============================================================
-- 3) codice NOT NULL UNIQUE
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM information_schema.columns
         WHERE table_schema = 'vendite'
           AND table_name   = 'offerte_commerciali'
           AND column_name  = 'codice'
           AND is_nullable  = 'NO'
    )
    AND EXISTS (
        SELECT 1 FROM pg_constraint c
          JOIN pg_class t   ON t.oid = c.conrelid
          JOIN pg_namespace n ON n.oid = t.relnamespace
         WHERE n.nspname  = 'vendite'
           AND t.relname  = 'offerte_commerciali'
           AND c.conname  = 'uq_offerte_commerciali_codice'
           AND c.contype  = 'u'
    ),
    '3) codice NOT NULL + UNIQUE uq_offerte_commerciali_codice'
);

-- ============================================================
-- 4) istanza_utility_id NOT NULL (B2: specchio contratti)
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM information_schema.columns
         WHERE table_schema = 'vendite'
           AND table_name   = 'offerte_commerciali'
           AND column_name  = 'istanza_utility_id'
           AND is_nullable  = 'NO'
    ),
    '4) istanza_utility_id NOT NULL (B2: offerta mono-utility, specchio contratti)'
);

-- ============================================================
-- 5) utility_id NOT NULL (B2)
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM information_schema.columns
         WHERE table_schema = 'vendite'
           AND table_name   = 'offerte_commerciali'
           AND column_name  = 'utility_id'
           AND is_nullable  = 'NO'
    ),
    '5) utility_id NOT NULL (B2: specchio contratti.utility_id)'
);

-- ============================================================
-- 6) data_annullamento presente (addendum A2: BOZZA->ANNULLATA)
-- ============================================================
SELECT has_column(
    'vendite', 'offerte_commerciali', 'data_annullamento',
    '6) data_annullamento presente (addendum A2)'
);

-- ============================================================
-- 7) motivazione_rifiuto presente (addendum A1: primo cittadino)
-- ============================================================
SELECT has_column(
    'vendite', 'offerte_commerciali', 'motivazione_rifiuto',
    '7) motivazione_rifiuto presente (addendum A1)'
);

-- ============================================================
-- 8) FK fk_offerte_commerciali_stato_doc → config.stati_doc_offerte
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_constraint c
          JOIN pg_class t   ON t.oid = c.conrelid
          JOIN pg_namespace n ON n.oid = t.relnamespace
         WHERE n.nspname = 'vendite'
           AND t.relname = 'offerte_commerciali'
           AND c.conname = 'fk_offerte_commerciali_stato_doc'
           AND c.contype = 'f'
    ),
    '8) FK fk_offerte_commerciali_stato_doc presente'
);

-- ============================================================
-- 9) FK self-ref fk_offerte_commerciali_revisione_padre
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_constraint c
          JOIN pg_class t   ON t.oid = c.conrelid
          JOIN pg_namespace n ON n.oid = t.relnamespace
         WHERE n.nspname = 'vendite'
           AND t.relname = 'offerte_commerciali'
           AND c.conname = 'fk_offerte_commerciali_revisione_padre'
           AND c.contype = 'f'
    ),
    '9) FK self-ref fk_offerte_commerciali_revisione_padre presente'
);

-- ============================================================
-- 10) CHECK chk_offerte_tipo_variazione_globale (I2: VARCHAR, non FK)
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_constraint c
          JOIN pg_class t   ON t.oid = c.conrelid
          JOIN pg_namespace n ON n.oid = t.relnamespace
         WHERE n.nspname = 'vendite'
           AND t.relname = 'offerte_commerciali'
           AND c.conname = 'chk_offerte_tipo_variazione_globale'
           AND c.contype = 'c'
    ),
    '10) CHECK chk_offerte_tipo_variazione_globale presente (I2: VARCHAR+CHECK)'
);

-- ============================================================
-- 11) CHECK chk_offerte_variazione_globale_coerenza
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_constraint c
          JOIN pg_class t   ON t.oid = c.conrelid
          JOIN pg_namespace n ON n.oid = t.relnamespace
         WHERE n.nspname = 'vendite'
           AND t.relname = 'offerte_commerciali'
           AND c.conname = 'chk_offerte_variazione_globale_coerenza'
           AND c.contype = 'c'
    ),
    '11) CHECK chk_offerte_variazione_globale_coerenza presente'
);

-- ============================================================
-- 12) CHECK chk_offerte_revisione_numero (>= 1)
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_constraint c
          JOIN pg_class t   ON t.oid = c.conrelid
          JOIN pg_namespace n ON n.oid = t.relnamespace
         WHERE n.nspname = 'vendite'
           AND t.relname = 'offerte_commerciali'
           AND c.conname = 'chk_offerte_revisione_numero'
           AND c.contype = 'c'
    ),
    '12) CHECK chk_offerte_revisione_numero presente'
);

SELECT * FROM finish();
ROLLBACK;
