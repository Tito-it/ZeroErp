-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: catalogo.vw_articoli_uom_operativa_dettaglio (Fase 6 BE
-- 28-04-2026, migration 20260428-06).
--
-- Capability esposte:
--   puo_eliminarsi          BOOLEAN  = NOT is_base
--   motivo_non_eliminabile  TEXT     = 'UOM_BASE_NON_ELIMINABILE' [NULL se eliminabile]
--
-- Setup: usiamo ART_TEST_BASE come articolo prodotto e creiamo 2
-- righe articoli_uom_operativa nel test:
--   - is_base=true   (UoM base, non eliminabile)
--   - is_base=false  (UoM operativa secondaria, eliminabile)
-- ROLLBACK ripristina lo stato.
--
-- Indice test (1..6):
--   1. presenza vista
--   2. UoM BASE: puo_eliminarsi = false
--   3. UoM BASE: motivo_non_eliminabile = 'UOM_BASE_NON_ELIMINABILE'
--   4. UoM SECONDARIA: puo_eliminarsi = true
--   5. UoM SECONDARIA: motivo_non_eliminabile = NULL
--   6. denormalizzazione articolo_codice/uom_codice presenti
-- ------------------------------------------------------------

BEGIN;
SELECT plan(6);

-- =========================================================
-- 1) Presenza vista
-- =========================================================
SELECT has_view(
    'catalogo', 'vw_articoli_uom_operativa_dettaglio',
    '1) catalogo.vw_articoli_uom_operativa_dettaglio presente'
);

-- =========================================================
-- Setup fixture: ART_TEST_BASE + 2 UoM (1 base + 1 secondaria)
-- Le UoM seed: id 1 (base esistente nel csv), id 2 (secondaria).
-- Per indipendenza dal seed (che potrebbe gia' avere riga is_base
-- per ART_TEST_BASE), creiamo righe ad-hoc su una UoM "vuota" e
-- forziamo il pulizia preventiva.
-- =========================================================
CREATE TEMP TABLE _t_ctx AS
SELECT
    (SELECT id FROM catalogo.articoli WHERE codice = 'ART_TEST_BASE') AS art_id,
    (SELECT id FROM catalogo.unita_misura ORDER BY id LIMIT 1)        AS uom_a_id,
    (SELECT id FROM catalogo.unita_misura ORDER BY id OFFSET 1 LIMIT 1) AS uom_b_id;

DO $pgtap$
BEGIN
    IF (SELECT art_id IS NULL OR uom_a_id IS NULL OR uom_b_id IS NULL FROM _t_ctx) THEN
        RAISE EXCEPTION 'Seed mancante: ART_TEST_BASE o 2+ UoM in catalogo.unita_misura.';
    END IF;
END
$pgtap$;

-- Pulizia preventiva: rimuovi eventuali righe gia' presenti per
-- ART_TEST_BASE che usano uom_a_id o uom_b_id (es. seed
-- articoli_uom_operativa.csv id 9002).
DELETE FROM catalogo.articoli_uom_operativa
 WHERE articolo_id = (SELECT art_id FROM _t_ctx)
   AND uom_id IN ((SELECT uom_a_id FROM _t_ctx), (SELECT uom_b_id FROM _t_ctx));

CREATE TEMP TABLE _t_uom_riga (kind text, uom_op_id bigint);

-- Riga BASE (uom_a)
WITH ins AS (
    INSERT INTO catalogo.articoli_uom_operativa (
        articolo_id, uom_id, is_base, factor_to_base, attivo
    )
    SELECT art_id, uom_a_id, true, 1, true FROM _t_ctx
    RETURNING id
)
INSERT INTO _t_uom_riga (kind, uom_op_id) SELECT 'base', id FROM ins;

-- Riga SECONDARIA (uom_b)
WITH ins AS (
    INSERT INTO catalogo.articoli_uom_operativa (
        articolo_id, uom_id, is_base, factor_to_base, attivo
    )
    SELECT art_id, uom_b_id, false, 6, true FROM _t_ctx
    RETURNING id
)
INSERT INTO _t_uom_riga (kind, uom_op_id) SELECT 'secondaria', id FROM ins;

-- =========================================================
-- 2..3) Riga BASE
-- =========================================================
SELECT is(
    (SELECT puo_eliminarsi
       FROM catalogo.vw_articoli_uom_operativa_dettaglio
      WHERE id = (SELECT uom_op_id FROM _t_uom_riga WHERE kind = 'base')),
    false,
    '2) UoM BASE: puo_eliminarsi = false'
);
SELECT is(
    (SELECT motivo_non_eliminabile
       FROM catalogo.vw_articoli_uom_operativa_dettaglio
      WHERE id = (SELECT uom_op_id FROM _t_uom_riga WHERE kind = 'base')),
    'UOM_BASE_NON_ELIMINABILE',
    '3) UoM BASE: motivo_non_eliminabile = UOM_BASE_NON_ELIMINABILE'
);

-- =========================================================
-- 4..5) Riga SECONDARIA
-- =========================================================
SELECT is(
    (SELECT puo_eliminarsi
       FROM catalogo.vw_articoli_uom_operativa_dettaglio
      WHERE id = (SELECT uom_op_id FROM _t_uom_riga WHERE kind = 'secondaria')),
    true,
    '4) UoM SECONDARIA: puo_eliminarsi = true (NOT is_base)'
);
SELECT is(
    (SELECT motivo_non_eliminabile
       FROM catalogo.vw_articoli_uom_operativa_dettaglio
      WHERE id = (SELECT uom_op_id FROM _t_uom_riga WHERE kind = 'secondaria')),
    NULL::text,
    '5) UoM SECONDARIA: motivo_non_eliminabile = NULL'
);

-- =========================================================
-- 6) Denormalizzazione: articolo_codice e uom_codice valorizzati
-- =========================================================
SELECT ok(
    (SELECT articolo_codice = 'ART_TEST_BASE'
        AND uom_codice IS NOT NULL
       FROM catalogo.vw_articoli_uom_operativa_dettaglio
      WHERE id = (SELECT uom_op_id FROM _t_uom_riga WHERE kind = 'base')),
    '6) Denormalizzazione: articolo_codice e uom_codice valorizzati per la riga BASE'
);

SELECT * FROM finish();
ROLLBACK;
