-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: modello compensazioni su vendite_contabili
-- ------------------------------------------------------------
-- Indice test
-- 1) Presenza funzioni trigger/model
-- 2) Riferimenti minimi presenti (centri/stato/compensazione/lotto)
-- 3) Blocco mutua esclusione compensazione+lotto in fn_get_or_create
-- 4) Blocco centro non-compensazione con compensazione_id
-- 5) Create contabile compensazione con centro valido
-- 6) Blocco link lotto su testata contabile di compensazione
-- 7) Unicita compensazione_id su vendite_contabili
-- ------------------------------------------------------------

BEGIN;

SELECT plan(7);

-- ============================================================
-- 0) Costanti
-- ============================================================
CREATE TEMP TABLE tmp_costanti_ccm AS
SELECT
  'pgtap_compensazioni_contabili_model'::text AS test_scope,
  date_trunc('month', current_date)::date AS competenza_mese;

-- ============================================================
-- 1) Presenza funzioni trigger/model
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'pagamenti'
      AND p.proname = 'trgfn_vendite_contabili_lotti_guard_compensazione'
  )
  AND EXISTS (
    SELECT 1
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'pagamenti'
      AND p.proname = 'fn_get_or_create_vendite_contabile'
  ),
  'Presenza funzioni trigger/model'
);

-- ============================================================
-- 2) Riferimenti minimi
-- ============================================================
CREATE TEMP TABLE tmp_centro_comp AS
WITH existing AS (
  SELECT c.id
  FROM pagamenti.centri_riscossione c
  WHERE c.attivo IS TRUE
    AND c.is_compensazione IS TRUE
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
    'CCM_COMP_' || to_char(clock_timestamp(), 'YYMMDDHH24MISSMS'),
    'CCM_COMP',
    'Centro compensazione test CCM',
    true,
    false,
    true,
    jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_ccm))
  WHERE NOT EXISTS (SELECT 1 FROM existing)
  RETURNING id
)
SELECT id FROM existing
UNION ALL
SELECT id FROM ins;

CREATE TEMP TABLE tmp_centro_std AS
WITH existing AS (
  SELECT c.id
  FROM pagamenti.centri_riscossione c
  WHERE c.attivo IS TRUE
    AND COALESCE(c.is_compensazione, false) IS FALSE
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
    'CCM_STD_' || to_char(clock_timestamp(), 'YYMMDDHH24MISSMS'),
    'CCM_STD',
    'Centro standard test CCM',
    false,
    false,
    true,
    jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_ccm))
  WHERE NOT EXISTS (SELECT 1 FROM existing)
  RETURNING id
)
SELECT id FROM existing
UNION ALL
SELECT id FROM ins;

CREATE TEMP TABLE tmp_stato_ref AS
SELECT s.codice_interno
FROM pagamenti.vendite_contabili_stati s
WHERE s.attivo IS TRUE
ORDER BY s.id
LIMIT 1;

CREATE TEMP TABLE tmp_compensazione AS
WITH ins AS (
  INSERT INTO pagamenti.compensazioni (
    meta
  )
  SELECT jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_ccm))
  RETURNING id
)
SELECT * FROM ins;

CREATE TEMP TABLE tmp_tipo_doc_ref AS
SELECT id
FROM config.tipi_doc_fiscale
WHERE attivo IS TRUE
ORDER BY id
LIMIT 1;

CREATE TEMP TABLE tmp_lotto_ref AS
WITH ins AS (
  INSERT INTO vendite.fatturazione_lotti (
    tipo_doc_fiscale_id,
    competenza_mese,
    meta
  )
  SELECT
    (SELECT id FROM tmp_tipo_doc_ref),
    (SELECT competenza_mese FROM tmp_costanti_ccm),
    jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_ccm))
  RETURNING id
)
SELECT * FROM ins;

SELECT ok(
  (SELECT count(*) = 1 FROM tmp_centro_comp)
  AND (SELECT count(*) = 1 FROM tmp_centro_std)
  AND (SELECT count(*) = 1 FROM tmp_stato_ref)
  AND (SELECT count(*) = 1 FROM tmp_compensazione)
  AND (SELECT count(*) = 1 FROM tmp_lotto_ref),
  'Riferimenti minimi presenti (centri/stato/compensazione/lotto)'
);

-- ============================================================
-- 3) Blocco mutua esclusione compensazione+lotto
-- ============================================================
SELECT throws_ok(
  $$
  SELECT pagamenti.fn_get_or_create_vendite_contabile(
    p_centro_riscossione_id => (SELECT id FROM tmp_centro_comp),
    p_data_contabile => current_date,
    p_data_registrazione => current_date,
    p_ente_incasso_id => NULL,
    p_compensazione_id => (SELECT id FROM tmp_compensazione),
    p_lotto_id => (SELECT id FROM tmp_lotto_ref),
    p_codice_stato_interno => (SELECT codice_interno FROM tmp_stato_ref),
    p_meta => '{}'::jsonb
  );
  $$,
  'P0001',
  NULL,
  'Blocco mutua esclusione compensazione+lotto in fn_get_or_create'
);

-- ============================================================
-- 4) Blocco centro non-compensazione con compensazione_id
-- ============================================================
SELECT throws_ok(
  $$
  SELECT pagamenti.fn_get_or_create_vendite_contabile(
    p_centro_riscossione_id => (SELECT id FROM tmp_centro_std),
    p_data_contabile => current_date,
    p_data_registrazione => current_date,
    p_ente_incasso_id => NULL,
    p_compensazione_id => (SELECT id FROM tmp_compensazione),
    p_lotto_id => NULL,
    p_codice_stato_interno => (SELECT codice_interno FROM tmp_stato_ref),
    p_meta => '{}'::jsonb
  );
  $$,
  'P0001',
  NULL,
  'Blocco centro non-compensazione con compensazione_id'
);

-- ============================================================
-- 5) Create contabile compensazione con centro valido
-- ============================================================
CREATE TEMP TABLE tmp_contabile_comp AS
SELECT pagamenti.fn_get_or_create_vendite_contabile(
  p_centro_riscossione_id => (SELECT id FROM tmp_centro_comp),
  p_data_contabile => current_date,
  p_data_registrazione => current_date,
  p_ente_incasso_id => NULL,
  p_compensazione_id => (SELECT id FROM tmp_compensazione),
  p_lotto_id => NULL,
  p_codice_stato_interno => (SELECT codice_interno FROM tmp_stato_ref),
  p_meta => jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_ccm), 'case', 'contabile_comp')
) AS contabile_id;

SELECT ok(
  (SELECT contabile_id IS NOT NULL FROM tmp_contabile_comp),
  'Create contabile compensazione con centro valido'
);

-- ============================================================
-- 6) Blocco link lotto su testata contabile di compensazione
-- ============================================================
SELECT throws_ok(
  $$
  INSERT INTO pagamenti.vendite_contabili_lotti (lotto_id, contabile_id, meta)
  VALUES (
    (SELECT id FROM tmp_lotto_ref),
    (SELECT contabile_id FROM tmp_contabile_comp),
    '{}'::jsonb
  );
  $$,
  'P0001',
  NULL,
  'Blocco link lotto su testata contabile di compensazione'
);

-- ============================================================
-- 7) Unicita compensazione_id su vendite_contabili
-- ============================================================
SELECT throws_ok(
  $$
  INSERT INTO pagamenti.vendite_contabili (
    codice,
    centro_riscossione_id,
    compensazione_id,
    data_contabile,
    data_registrazione,
    stato_id,
    meta
  )
  VALUES (
    'CCM_DUP_' || to_char(clock_timestamp(), 'YYMMDDHH24MISSMS'),
    (SELECT id FROM tmp_centro_comp),
    (SELECT id FROM tmp_compensazione),
    current_date,
    current_date,
    (SELECT s.id
       FROM pagamenti.vendite_contabili_stati s
      WHERE s.codice_interno = (SELECT codice_interno FROM tmp_stato_ref)
      LIMIT 1),
    '{}'::jsonb
  );
  $$,
  '23505',
  NULL,
  'Unicita compensazione_id su vendite_contabili'
);

SELECT * FROM finish();

ROLLBACK;
