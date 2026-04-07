-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Schema: catalogo
-- Ambito: seed automatico UoM operativa base + lock UPDATE su uom_id
--
-- Indice test (0..7):
--   1) Funzione catalogo.trgfn_articoli_seed_uom_base presente
--   2) Trigger trg_articoli_a10_seed_uom_base_ins presente
--   3) Trigger trg_articoli_a10_protect_uom_id_upd presente
--   4) Setup: riferimenti FK reali disponibili
--   5) INSERT articolo crea riga is_base=true in articoli_uom_operativa
--   6) Solo UNA riga is_base=true per articolo dopo seed
--   7) UPDATE articoli.uom_id bloccato (CODICE_NON_MODIFICABILE)
--   8) Override GUC consente la modifica in manutenzione
-- ------------------------------------------------------------

BEGIN;

SELECT plan(8);

-- ============================================================
-- 1) Funzione presente
-- ============================================================
SELECT has_function(
    'catalogo', 'trgfn_articoli_seed_uom_base',
    ARRAY[]::text[],
    '1) catalogo.trgfn_articoli_seed_uom_base presente'
);

-- ============================================================
-- 2) Trigger seed presente
-- ============================================================
SELECT ok(
    EXISTS(
        SELECT 1
          FROM pg_trigger t
          JOIN pg_class c ON c.oid = t.tgrelid
          JOIN pg_namespace n ON n.oid = c.relnamespace
         WHERE n.nspname = 'catalogo'
           AND c.relname = 'articoli'
           AND t.tgname = 'trg_articoli_a10_seed_uom_base_ins'
           AND NOT t.tgisinternal
    ),
    '2) trigger trg_articoli_a10_seed_uom_base_ins presente su catalogo.articoli'
);

-- ============================================================
-- 3) Trigger lock presente
-- ============================================================
SELECT ok(
    EXISTS(
        SELECT 1
          FROM pg_trigger t
          JOIN pg_class c ON c.oid = t.tgrelid
          JOIN pg_namespace n ON n.oid = c.relnamespace
         WHERE n.nspname = 'catalogo'
           AND c.relname = 'articoli'
           AND t.tgname = 'trg_articoli_a10_protect_uom_id_upd'
           AND NOT t.tgisinternal
    ),
    '3) trigger trg_articoli_a10_protect_uom_id_upd presente su catalogo.articoli'
);

-- ============================================================
-- Setup riferimenti FK reali
-- ============================================================
CREATE TEMP TABLE tmp_test_keys AS
SELECT to_char(clock_timestamp(), 'YYYYMMDDHH24MISSMS') AS ts;

CREATE TEMP TABLE tmp_refs AS
SELECT
    (SELECT id FROM catalogo.unita_misura WHERE attivo = true ORDER BY id LIMIT 1)            AS uom1_id,
    (SELECT id FROM catalogo.unita_misura WHERE attivo = true ORDER BY id LIMIT 1 OFFSET 1)   AS uom2_id,
    (SELECT id FROM vendite.articoli_gruppi WHERE attivo = true ORDER BY id LIMIT 1)          AS gruppo_id,
    (SELECT id FROM vendite.articoli_tipologie WHERE attivo = true ORDER BY id LIMIT 1)       AS tipo_id,
    (SELECT id FROM vendite.articoli_spesa WHERE attivo = true ORDER BY id LIMIT 1)           AS spesa_id,
    (SELECT id FROM config.iva WHERE attivo = true ORDER BY id LIMIT 1)                       AS iva_id;

-- ============================================================
-- 4) Setup OK
-- ============================================================
SELECT ok(
    (SELECT uom1_id   FROM tmp_refs) IS NOT NULL
    AND (SELECT uom2_id   FROM tmp_refs) IS NOT NULL
    AND (SELECT gruppo_id FROM tmp_refs) IS NOT NULL
    AND (SELECT tipo_id   FROM tmp_refs) IS NOT NULL
    AND (SELECT spesa_id  FROM tmp_refs) IS NOT NULL
    AND (SELECT iva_id    FROM tmp_refs) IS NOT NULL,
    '4) riferimenti FK reali tutti disponibili (2 UoM, gruppo, tipo, spesa, iva)'
);

-- ============================================================
-- 5) INSERT articolo crea riga is_base=true in articoli_uom_operativa
-- ============================================================
CREATE TEMP TABLE tmp_art (id uuid);

INSERT INTO catalogo.articoli (
    codice,
    descrizione,
    uom_id,
    tipo_voce_id,
    gruppo_voce_id,
    spesa_id,
    iva_id
)
SELECT
    'TEST_SEED_' || (SELECT ts FROM tmp_test_keys),
    'Articolo test seed UoM base',
    (SELECT uom1_id   FROM tmp_refs),
    (SELECT tipo_id   FROM tmp_refs),
    (SELECT gruppo_id FROM tmp_refs),
    (SELECT spesa_id  FROM tmp_refs),
    (SELECT iva_id    FROM tmp_refs)
RETURNING id;

INSERT INTO tmp_art (id)
SELECT id FROM catalogo.articoli
 WHERE codice = 'TEST_SEED_' || (SELECT ts FROM tmp_test_keys);

SELECT ok(
    EXISTS(
        SELECT 1 FROM catalogo.articoli_uom_operativa
         WHERE articolo_id = (SELECT id FROM tmp_art)
           AND uom_id      = (SELECT uom1_id FROM tmp_refs)
           AND is_base     = true
           AND factor_to_base = 1
    ),
    '5) seed AFTER INSERT: riga is_base=true creata con uom_id e factor_to_base=1'
);

-- ============================================================
-- 6) Solo UNA riga is_base=true per articolo
-- ============================================================
SELECT is(
    (SELECT count(*)::int FROM catalogo.articoli_uom_operativa
       WHERE articolo_id = (SELECT id FROM tmp_art)
         AND is_base = true),
    1,
    '6) esattamente 1 riga is_base=true per articolo dopo seed'
);

-- ============================================================
-- 7) UPDATE uom_id bloccato (CODICE_NON_MODIFICABILE)
-- ============================================================
SELECT throws_ok(
    format(
        'UPDATE catalogo.articoli SET uom_id = %s WHERE id = %L',
        (SELECT uom2_id FROM tmp_refs),
        (SELECT id FROM tmp_art)
    ),
    NULL,
    NULL,
    '7) UPDATE articoli.uom_id bloccato dal trigger lock'
);

-- ============================================================
-- 8) Override GUC consente la modifica
-- ============================================================
SET LOCAL zeroerp.allow_lock_columns_override = 'on';

SELECT lives_ok(
    format(
        'UPDATE catalogo.articoli SET uom_id = %s WHERE id = %L',
        (SELECT uom2_id FROM tmp_refs),
        (SELECT id FROM tmp_art)
    ),
    '8) GUC zeroerp.allow_lock_columns_override=on consente UPDATE uom_id'
);

RESET zeroerp.allow_lock_columns_override;

-- ============================================================
SELECT * FROM finish();
ROLLBACK;
