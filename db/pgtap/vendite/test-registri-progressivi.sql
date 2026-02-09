-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: vendite.fn_get_next_progressivo (reset annuale)
-- ------------------------------------------------------------
-- Indice test
-- 1) Inserimento registro di test
-- 2) Primo progressivo anno 2025 = 1
-- 3) Secondo progressivo anno 2025 = 2
-- 4) Primo progressivo anno 2026 = 1 (reset)
-- 5) Esistenza righe progressivi 2025/2026
-- 6) Cleanup completato
-- ------------------------------------------------------------

BEGIN;

SELECT plan(6);

-- ============================================================
-- 0) Costanti
-- ============================================================
CREATE TEMP TABLE tmp_costanti_reg AS
SELECT
  'pgtap_registri_progressivi'::text AS test_scope;

-- ============================================================
-- 1) Inserimento registro di test
-- ============================================================
CREATE TEMP TABLE tmp_registro AS
WITH ins AS (
  INSERT INTO vendite.registri_fatturazione (
    codice,
    descrizione,
    reset_policy,
    attivo,
    meta
  )
  SELECT
    left('REGP_' || (SELECT test_scope FROM tmp_costanti_reg), 16),
    'Registro test progressivi',
    'ANNUALE',
    true,
    jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_reg))
  RETURNING id
)
SELECT * FROM ins;

SELECT ok(
  (SELECT id IS NOT NULL FROM tmp_registro),
  'Inserimento registro di test'
);

-- ============================================================
-- 2) Progressivi per anno 2025/2026
-- ============================================================
SELECT is(
  vendite.fn_get_next_progressivo(
    p_registro_id => (SELECT id FROM tmp_registro),
    p_data => date '2025-12-31',
    p_serie => NULL
  ),
  1::bigint,
  'Primo progressivo anno 2025 = 1'
);

SELECT is(
  vendite.fn_get_next_progressivo(
    p_registro_id => (SELECT id FROM tmp_registro),
    p_data => date '2025-12-31',
    p_serie => NULL
  ),
  2::bigint,
  'Secondo progressivo anno 2025 = 2'
);

SELECT is(
  vendite.fn_get_next_progressivo(
    p_registro_id => (SELECT id FROM tmp_registro),
    p_data => date '2026-01-01',
    p_serie => NULL
  ),
  1::bigint,
  'Primo progressivo anno 2026 = 1 (reset)'
);

SELECT ok(
  (
    SELECT count(*) = 2
    FROM vendite.registri_fatturazione_progressivi rp
    WHERE rp.registro_id = (SELECT id FROM tmp_registro)
      AND rp.anno IN (2025, 2026)
  ),
  'Esistenza righe progressivi 2025/2026'
);

-- ============================================================
-- Cleanup
-- ============================================================
UPDATE vendite.registri_fatturazione
SET storicizza = false
WHERE id = (SELECT id FROM tmp_registro);

DELETE FROM vendite.registri_fatturazione_progressivi
WHERE registro_id = (SELECT id FROM tmp_registro);

DELETE FROM vendite.registri_fatturazione
WHERE id = (SELECT id FROM tmp_registro);

SELECT ok(true, 'Cleanup completato');

SELECT * FROM finish();

ROLLBACK;
