-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: pagamenti.fn_get_or_create_vendite_contabile
-- ------------------------------------------------------------
-- Indice test
-- 1) Presenza funzione fn_get_or_create_vendite_contabile
-- 2) Riferimenti minimi presenti (centro/stato/tipo_doc per lotto)
-- 3) Create contabile senza lotto
-- 4) Reuse contabile senza lotto (stessi parametri)
-- 5) Create contabile con lotto e link tabella ponte
-- 6) Reuse contabile con stesso lotto
-- 7) Idempotenza link lotto-contabile (una sola riga ponte)
-- 8) Guard parametri: blocco centro_riscossione_id non valido
-- ------------------------------------------------------------

BEGIN;

SELECT plan(8);

-- ============================================================
-- 0) Costanti
-- ============================================================
CREATE TEMP TABLE tmp_costanti_goc AS
SELECT
  'pgtap_get_or_create_contabile'::text AS test_scope,
  date_trunc('month', current_date)::date AS data_contabile,
  current_date::date AS data_registrazione;

-- ============================================================
-- 1) Presenza funzione
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'pagamenti'
      AND p.proname = 'fn_get_or_create_vendite_contabile'
  ),
  'Presenza funzione fn_get_or_create_vendite_contabile'
);

-- ============================================================
-- 2) Riferimenti minimi
-- ============================================================
CREATE TEMP TABLE tmp_centro_ref AS
WITH existing AS (
  SELECT c.id
  FROM pagamenti.centri_riscossione c
  WHERE c.attivo IS TRUE
  ORDER BY c.id
  LIMIT 1
), ins AS (
  INSERT INTO pagamenti.centri_riscossione (
    codice,
    codice_interno,
    descrizione,
    is_compensazione,
    is_fondo_fattura,
    attivo,
    meta
  )
  SELECT
    'GOC_CENTRO_' || to_char(clock_timestamp(), 'YYMMDDHH24MISSMS'),
    'GOC_TEST',
    'Centro riscossione test fn_get_or_create',
    false,
    false,
    true,
    jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_goc))
  WHERE NOT EXISTS (SELECT 1 FROM existing)
  RETURNING id
)
SELECT id FROM existing
UNION ALL
SELECT id FROM ins;

CREATE TEMP TABLE tmp_stato_ref AS
WITH existing AS (
  SELECT s.codice_interno
  FROM pagamenti.vendite_contabili_stati s
  WHERE s.attivo IS TRUE
  ORDER BY s.id
  LIMIT 1
), ins AS (
  INSERT INTO pagamenti.vendite_contabili_stati (
    codice,
    codice_interno,
    descrizione,
    is_final,
    ordine,
    attivo,
    meta
  )
  SELECT
    'GOC_STATO_' || to_char(clock_timestamp(), 'YYMMDDHH24MISSMS'),
    'GOC_STATO',
    'Stato contabile test fn_get_or_create',
    false,
    10,
    true,
    jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_goc))
  WHERE NOT EXISTS (SELECT 1 FROM existing)
  RETURNING codice_interno
)
SELECT codice_interno FROM existing
UNION ALL
SELECT codice_interno FROM ins;

CREATE TEMP TABLE tmp_tipo_doc_ref AS
SELECT id
FROM config.tipi_doc_fiscale
WHERE attivo IS TRUE
ORDER BY id
LIMIT 1;

CREATE TEMP TABLE tmp_lotto_ref AS
WITH existing AS (
  SELECT l.id
  FROM vendite.fatturazione_lotti l
  ORDER BY l.id DESC
  LIMIT 1
), ins AS (
  INSERT INTO vendite.fatturazione_lotti (
    tipo_doc_fiscale_id,
    competenza_mese,
    meta
  )
  SELECT
    (SELECT id FROM tmp_tipo_doc_ref),
    (SELECT data_contabile FROM tmp_costanti_goc),
    jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_goc))
  WHERE NOT EXISTS (SELECT 1 FROM existing)
    AND (SELECT id FROM tmp_tipo_doc_ref) IS NOT NULL
  RETURNING id
)
SELECT id FROM existing
UNION ALL
SELECT id FROM ins;

SELECT ok(
  (SELECT count(*) = 1 FROM tmp_centro_ref)
  AND (SELECT count(*) = 1 FROM tmp_stato_ref)
  AND (SELECT count(*) = 1 FROM tmp_tipo_doc_ref)
  AND (SELECT count(*) = 1 FROM tmp_lotto_ref),
  'Riferimenti minimi presenti (centro/stato/tipo_doc per lotto)'
);

-- ============================================================
-- 3) Create contabile senza lotto
-- ============================================================
CREATE TEMP TABLE tmp_contabile_no_lotto AS
SELECT pagamenti.fn_get_or_create_vendite_contabile(
  p_centro_riscossione_id => (SELECT id FROM tmp_centro_ref),
  p_data_contabile => (SELECT data_contabile FROM tmp_costanti_goc),
  p_data_registrazione => (SELECT data_registrazione FROM tmp_costanti_goc),
  p_ente_incasso_id => NULL,
  p_lotto_id => NULL,
  p_codice_stato_interno => (SELECT codice_interno FROM tmp_stato_ref),
  p_meta => jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_goc), 'case', 'no_lotto')
) AS contabile_id;

SELECT ok(
  (SELECT contabile_id IS NOT NULL FROM tmp_contabile_no_lotto),
  'Create contabile senza lotto'
);

-- ============================================================
-- 4) Reuse contabile senza lotto
-- ============================================================
SELECT is(
  pagamenti.fn_get_or_create_vendite_contabile(
    p_centro_riscossione_id => (SELECT id FROM tmp_centro_ref),
    p_data_contabile => (SELECT data_contabile FROM tmp_costanti_goc),
    p_data_registrazione => (SELECT data_registrazione FROM tmp_costanti_goc),
    p_ente_incasso_id => NULL,
    p_lotto_id => NULL,
    p_codice_stato_interno => (SELECT codice_interno FROM tmp_stato_ref),
    p_meta => jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_goc), 'case', 'no_lotto_reuse')
  ),
  (SELECT contabile_id::bigint FROM tmp_contabile_no_lotto),
  'Reuse contabile senza lotto (stessi parametri)'
);

-- ============================================================
-- 5) Create contabile con lotto e link
-- ============================================================
CREATE TEMP TABLE tmp_contabile_lotto AS
SELECT pagamenti.fn_get_or_create_vendite_contabile(
  p_centro_riscossione_id => (SELECT id FROM tmp_centro_ref),
  p_data_contabile => (SELECT data_contabile FROM tmp_costanti_goc),
  p_data_registrazione => (SELECT data_registrazione FROM tmp_costanti_goc),
  p_ente_incasso_id => NULL,
  p_lotto_id => (SELECT id FROM tmp_lotto_ref),
  p_codice_stato_interno => (SELECT codice_interno FROM tmp_stato_ref),
  p_meta => jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_goc), 'case', 'with_lotto')
) AS contabile_id;

SELECT ok(
  EXISTS (
    SELECT 1
    FROM pagamenti.vendite_contabili_lotti l
    WHERE l.lotto_id = (SELECT id FROM tmp_lotto_ref)
      AND l.contabile_id = (SELECT contabile_id FROM tmp_contabile_lotto)
  ),
  'Create contabile con lotto e link tabella ponte'
);

-- ============================================================
-- 6) Reuse contabile con stesso lotto
-- ============================================================
SELECT is(
  pagamenti.fn_get_or_create_vendite_contabile(
    p_centro_riscossione_id => (SELECT id FROM tmp_centro_ref),
    p_data_contabile => (SELECT data_contabile FROM tmp_costanti_goc),
    p_data_registrazione => (SELECT data_registrazione FROM tmp_costanti_goc),
    p_ente_incasso_id => NULL,
    p_lotto_id => (SELECT id FROM tmp_lotto_ref),
    p_codice_stato_interno => (SELECT codice_interno FROM tmp_stato_ref),
    p_meta => jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_goc), 'case', 'with_lotto_reuse')
  ),
  (SELECT contabile_id::bigint FROM tmp_contabile_lotto),
  'Reuse contabile con stesso lotto'
);

-- ============================================================
-- 7) Idempotenza link lotto-contabile
-- ============================================================
SELECT is(
  (
    SELECT count(*)::int
    FROM pagamenti.vendite_contabili_lotti l
    WHERE l.lotto_id = (SELECT id FROM tmp_lotto_ref)
      AND l.contabile_id = (SELECT contabile_id FROM tmp_contabile_lotto)
  ),
  1,
  'Idempotenza link lotto-contabile (una sola riga ponte)'
);

-- ============================================================
-- 8) Guard parametri
-- ============================================================
SELECT throws_ok(
  $$
  SELECT pagamenti.fn_get_or_create_vendite_contabile(
    p_centro_riscossione_id => 0,
    p_data_contabile => current_date,
    p_data_registrazione => current_date,
    p_ente_incasso_id => NULL,
    p_lotto_id => NULL,
    p_codice_stato_interno => (SELECT codice_interno FROM tmp_stato_ref),
    p_meta => '{}'::jsonb
  );
  $$,
  'P0001',
  NULL,
  'Guard parametri: blocco centro_riscossione_id non valido'
);

SELECT * FROM finish();

ROLLBACK;
