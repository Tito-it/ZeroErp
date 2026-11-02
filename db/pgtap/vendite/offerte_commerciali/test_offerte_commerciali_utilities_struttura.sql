-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: struttura vendite.offerte_commerciali_utilities (Step 3).
--       Mirror fedele di contratti_utilities: relazione 1:1 con l'offerta
--       (UNIQUE offerta_id), tutti i campi business inclusi (A3).
--
-- Indice test (1..5):
--   1)  Tabella vendite.offerte_commerciali_utilities esiste
--   2)  UNIQUE (offerta_id) — relazione 1:1 con l'offerta (B1)
--   3)  FK offerta_id -> offerte_commerciali con CASCADE
--   4)  Campi business presenti: tipo_utenza_id, classe_utenza_id,
--       param_1_num, param_2_txt, istanza_dati_precontrattuali_id (A3)
--   5)  meta presente e NOT NULL
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;
SELECT plan(5);

-- ============================================================
-- 1) Tabella esiste
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM information_schema.tables
         WHERE table_schema = 'vendite'
           AND table_name   = 'offerte_commerciali_utilities'
    ),
    '1) vendite.offerte_commerciali_utilities esiste'
);

-- ============================================================
-- 2) UNIQUE (offerta_id): relazione 1:1 con offerta (B1)
--    contratti_utilities ha UNIQUE (contratto_id); il mirror ha UNIQUE (offerta_id).
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_constraint c
          JOIN pg_class t   ON t.oid = c.conrelid
          JOIN pg_namespace n ON n.oid = t.relnamespace
         WHERE n.nspname = 'vendite'
           AND t.relname = 'offerte_commerciali_utilities'
           AND c.conname = 'uq_offerte_commerciali_utilities_offerta_id'
           AND c.contype = 'u'
    ),
    '2) UNIQUE uq_offerte_commerciali_utilities_offerta_id presente (1:1 con offerta, B1)'
);

-- ============================================================
-- 3) FK offerta_id → offerte_commerciali con ON DELETE CASCADE
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_constraint c
          JOIN pg_class t   ON t.oid = c.conrelid
          JOIN pg_namespace n ON n.oid = t.relnamespace
         WHERE n.nspname = 'vendite'
           AND t.relname = 'offerte_commerciali_utilities'
           AND c.conname = 'fk_offerte_utilities_offerta'
           AND c.contype = 'f'
           AND c.confdeltype = 'c'  -- CASCADE
    ),
    '3) FK fk_offerte_utilities_offerta presente con ON DELETE CASCADE'
);

-- ============================================================
-- 4) Campi business A3: tipo_utenza_id, classe_utenza_id,
--    param_1_num, param_2_txt, istanza_dati_precontrattuali_id
-- ============================================================
SELECT ok(
    (SELECT COUNT(*) = 5
       FROM information_schema.columns
      WHERE table_schema = 'vendite'
        AND table_name   = 'offerte_commerciali_utilities'
        AND column_name IN (
            'tipo_utenza_id',
            'classe_utenza_id',
            'param_1_num',
            'param_2_txt',
            'istanza_dati_precontrattuali_id'
        )
    ),
    '4) Campi business A3 presenti: tipo_utenza_id, classe_utenza_id, param_1_num, param_2_txt, istanza_dati_precontrattuali_id'
);

-- ============================================================
-- 5) meta presente e NOT NULL
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM information_schema.columns
         WHERE table_schema = 'vendite'
           AND table_name   = 'offerte_commerciali_utilities'
           AND column_name  = 'meta'
           AND is_nullable  = 'NO'
    ),
    '5) meta NOT NULL presente'
);

SELECT * FROM finish();
ROLLBACK;
