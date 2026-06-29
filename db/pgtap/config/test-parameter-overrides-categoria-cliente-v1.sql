-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: Step 1.1 refactor cascata parametri
--       Nuova dimensione categoria_cliente_id su config.parameter_overrides
--       Migrations:
--         20260515-06 (ALTER TABLE — colonna + FK + UNIQUE v4 + indice)
--         20260515-07 (trigger trg_parameter_overrides_a10_cat_clienti_req_attivo_ins_upd)
--
-- Indice test (1..12):
--   1)  Colonna categoria_cliente_id presente
--   2)  Colonna nullable (smallint NULL)
--   3)  FK fk_overrides_categoria_cliente presente
--   4)  FK: ON UPDATE CASCADE
--   5)  FK: ON DELETE RESTRICT
--   6)  Indice ix_overrides_param_categoria_cliente presente
--   7)  UNIQUE v4 presente (uq_overrides_full_scope_v4)
--   8)  UNIQUE v3 rimosso (uq_overrides_full_scope_v3)
--   9)  Trigger guard categoria attiva presente
--  10)  INSERT override con categoria attiva -> ok
--  11)  INSERT override con categoria_cliente_id NULL -> ok
--  12)  INSERT override con categoria disattiva -> raise
-- ------------------------------------------------------------

BEGIN;
SELECT plan(12);

-- ============================================================
-- Setup: parametro esistente + due categorie clienti test
-- ============================================================
CREATE TEMP TABLE tmp_cat_ctx AS
SELECT
    (SELECT id FROM config.parameters ORDER BY id LIMIT 1) AS param_id;

-- Due categorie test: una attiva, una disattiva.
-- IDs alti per evitare collisioni con dati seed.
INSERT INTO anagrafiche.categorie_clienti
    (id, codice, codice_interno, descrizione, partecipa_promo, ordinamento, attivo)
VALUES
    (9001, 'TEST_CATCLI_ATTIVA',   'TEST_CATCLI_ATTIVA',   'Categoria test attiva',   TRUE, 900, TRUE),
    (9002, 'TEST_CATCLI_DISATTIVA','TEST_CATCLI_DISATTIVA','Categoria test disattiva', TRUE, 901, FALSE);

-- ============================================================
-- 1) Colonna presente
-- ============================================================
SELECT has_column(
    'config', 'parameter_overrides', 'categoria_cliente_id',
    '1) Colonna categoria_cliente_id presente su config.parameter_overrides'
);

-- ============================================================
-- 2) Colonna nullable + tipo smallint
-- ============================================================
SELECT ok(
    (SELECT is_nullable = 'YES' AND data_type = 'smallint'
       FROM information_schema.columns
      WHERE table_schema  = 'config'
        AND table_name    = 'parameter_overrides'
        AND column_name   = 'categoria_cliente_id'),
    '2) categoria_cliente_id e'' smallint nullable'
);

-- ============================================================
-- 3) FK presente (per nome constraint)
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_constraint c
          JOIN pg_class t       ON t.oid = c.conrelid
          JOIN pg_namespace ns  ON ns.oid = t.relnamespace
         WHERE ns.nspname  = 'config'
           AND t.relname   = 'parameter_overrides'
           AND c.conname   = 'fk_overrides_categoria_cliente'
           AND c.contype   = 'f'
    ),
    '3) FK fk_overrides_categoria_cliente presente'
);

-- ============================================================
-- 4) FK ON UPDATE CASCADE (confupdtype = 'c')
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_constraint c
          JOIN pg_class t      ON t.oid = c.conrelid
          JOIN pg_namespace ns ON ns.oid = t.relnamespace
         WHERE ns.nspname  = 'config'
           AND t.relname   = 'parameter_overrides'
           AND c.conname   = 'fk_overrides_categoria_cliente'
           AND c.confupdtype = 'c'   -- CASCADE
    ),
    '4) FK: ON UPDATE CASCADE'
);

-- ============================================================
-- 5) FK ON DELETE RESTRICT (confdeltype = 'r')
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_constraint c
          JOIN pg_class t      ON t.oid = c.conrelid
          JOIN pg_namespace ns ON ns.oid = t.relnamespace
         WHERE ns.nspname  = 'config'
           AND t.relname   = 'parameter_overrides'
           AND c.conname   = 'fk_overrides_categoria_cliente'
           AND c.confdeltype = 'r'   -- RESTRICT
    ),
    '5) FK: ON DELETE RESTRICT'
);

-- ============================================================
-- 6) Indice per lookup COALESCE presente
-- ============================================================
SELECT has_index(
    'config', 'parameter_overrides',
    'ix_overrides_param_categoria_cliente',
    '6) Indice ix_overrides_param_categoria_cliente presente'
);

-- ============================================================
-- 7) UNIQUE v4 presente
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_constraint c
          JOIN pg_class t      ON t.oid = c.conrelid
          JOIN pg_namespace ns ON ns.oid = t.relnamespace
         WHERE ns.nspname = 'config'
           AND t.relname  = 'parameter_overrides'
           AND c.conname  = 'uq_overrides_full_scope_v4'
           AND c.contype  = 'u'
    ),
    '7) UNIQUE uq_overrides_full_scope_v4 presente'
);

-- ============================================================
-- 8) UNIQUE v3 rimosso
-- ============================================================
SELECT ok(
    NOT EXISTS (
        SELECT 1 FROM pg_constraint c
          JOIN pg_class t      ON t.oid = c.conrelid
          JOIN pg_namespace ns ON ns.oid = t.relnamespace
         WHERE ns.nspname = 'config'
           AND t.relname  = 'parameter_overrides'
           AND c.conname  = 'uq_overrides_full_scope_v3'
    ),
    '8) UNIQUE uq_overrides_full_scope_v3 rimosso'
);

-- ============================================================
-- 9) Trigger guard presente
--    Il framework genera il nome con suffisso hash (es. ..._require_at_431944):
--    si verifica per funzione + tabella padre, non per nome esatto.
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1
          FROM pg_trigger t
          JOIN pg_class c      ON c.oid = t.tgrelid
          JOIN pg_namespace ns ON ns.oid = c.relnamespace
          JOIN pg_proc p       ON p.oid = t.tgfoid
         WHERE ns.nspname = 'config'
           AND c.relname  = 'parameter_overrides'
           AND p.proname  = 'trgfn_child_requires_active_parent'
           AND NOT t.tgisinternal
           AND pg_get_triggerdef(t.oid) ILIKE '%categorie_clienti%'
    ),
    '9) Trigger guard categoria attiva presente (nome generato dal framework)'
);

-- ============================================================
-- 10) INSERT override con categoria attiva -> ok
-- ============================================================
SELECT lives_ok(
    format(
        $$INSERT INTO config.parameter_overrides
              (parameter_id, overridden_value, categoria_cliente_id)
          VALUES (%L::bigint, 'TEST_VALUE', 9001)$$,
        (SELECT param_id FROM tmp_cat_ctx)
    ),
    '10) INSERT override con categoria attiva -> ok'
);

-- ============================================================
-- 11) INSERT override con categoria_cliente_id NULL -> ok
-- ============================================================
SELECT lives_ok(
    format(
        $$INSERT INTO config.parameter_overrides
              (parameter_id, overridden_value, categoria_cliente_id)
          VALUES (%L::bigint, 'TEST_VALUE_NULL', NULL)$$,
        (SELECT param_id FROM tmp_cat_ctx)
    ),
    '11) INSERT override con categoria_cliente_id NULL -> ok'
);

-- ============================================================
-- 12) INSERT override con categoria disattiva -> raise
--     Il guard e' un CONSTRAINT TRIGGER DEFERRABLE INITIALLY DEFERRED: la
--     violazione emerge al check del vincolo, non all'INSERT. Si forza il check
--     immediato per osservare il raise in modo sincrono nel throws_ok.
-- ============================================================
SET CONSTRAINTS ALL IMMEDIATE;

SELECT throws_ok(
    format(
        $$INSERT INTO config.parameter_overrides
              (parameter_id, overridden_value, categoria_cliente_id)
          VALUES (%L::bigint, 'TEST_VALUE_DIS', 9002)$$,
        (SELECT param_id FROM tmp_cat_ctx)
    ),
    'P0001',
    NULL,
    '12) INSERT override con categoria disattiva -> raise'
);

SELECT * FROM finish();
ROLLBACK;
