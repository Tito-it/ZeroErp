-- ============================================================
-- Indice test
-- 1) Stato_doc_fiscale di test creato
-- 2) Lotto di test creato
-- 3) Pipeline di test creata (lista processi presente)
-- 4) Pipeline step eseguito (task select_attivita) e log fase presente
-- ============================================================

BEGIN;

SELECT plan(4);

-- ============================================================
-- Setup
-- ============================================================
CREATE TEMP TABLE tmp_pipeline_costanti AS
SELECT
  'pgtap_fp_' || to_char(clock_timestamp(), 'YYMMDDHH24MISS') AS test_scope;

CREATE TEMP TABLE tmp_pipeline_ids (
  stato_doc_fiscale_id bigint,
  tipo_doc_fiscale_id bigint,
  utility_id integer,
  lotto_id bigint
);

-- Stato_doc_fiscale di test (applica_lotto=true)
WITH ins AS (
  INSERT INTO config.stati_doc_fiscale (
    codice,
    descrizione,
    attivo,
    ordine,
    meta,
    codice_interno,
    applica_lotto,
    applica_fattura
  )
  SELECT
    left('TP_' || (SELECT test_scope FROM tmp_pipeline_costanti), 30),
    'Stato pipeline test',
    true,
    999,
    jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_pipeline_costanti)),
    left('TP_' || (SELECT test_scope FROM tmp_pipeline_costanti), 30),
    true,
    false
  RETURNING id
)
INSERT INTO tmp_pipeline_ids (stato_doc_fiscale_id)
SELECT id FROM ins;

SELECT ok(
  (SELECT stato_doc_fiscale_id FROM tmp_pipeline_ids) IS NOT NULL,
  'Stato_doc_fiscale di test creato'
);

-- Tipo documento fiscale attivo (fallback)
UPDATE tmp_pipeline_ids
SET tipo_doc_fiscale_id = (
  SELECT id
  FROM config.tipi_doc_fiscale
  WHERE attivo IS TRUE
  ORDER BY id
  LIMIT 1
);

-- Utility attiva (obbligatoria per lotto)
UPDATE tmp_pipeline_ids
SET utility_id = (
  SELECT id
  FROM config.utilities
  --WHERE attivo IS TRUE
  ORDER BY id
  LIMIT 1
);

-- Lotto di test
UPDATE tmp_pipeline_ids
SET lotto_id = vendite.fn_create_fatturazione_lotto(
  date '2026-01-01',
  (SELECT tipo_doc_fiscale_id FROM tmp_pipeline_ids),
  (SELECT utility_id FROM tmp_pipeline_ids),
  NULL,
  uuidv7(),
  jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_pipeline_costanti))
);

SELECT ok(
  (SELECT lotto_id FROM tmp_pipeline_ids) IS NOT NULL,
  'Lotto di test creato'
);

-- Pipeline (step con task select_attivita) gia` caricata da seed
SELECT ok(
  (SELECT count(*) FROM vendite.fatturazione_pipeline
    WHERE processi @> '[{"task":"select_attivita"}]'::jsonb
  ) >= 1,
  'Pipeline presente con lista processi'
);

-- ============================================================
-- 2) Esecuzione step pipeline
-- ============================================================
SELECT vendite.fn_execute_pipeline_step(
  (SELECT lotto_id FROM tmp_pipeline_ids),
  (SELECT stato_doc_fiscale_id FROM vendite.fatturazione_pipeline
   WHERE processi @> '[{"task":"select_attivita"}]'::jsonb
   ORDER BY id
   LIMIT 1),
  false,
  false
);

SELECT ok(
  (SELECT count(*) FROM vendite.fatturazione_lotti_log
    WHERE lotto_id = (SELECT lotto_id FROM tmp_pipeline_ids)
      AND fase = 'Caricamento lista attivita'
      AND status = 'I'
  ) >= 1,
  'Log fase pipeline inserito'
);

-- ============================================================
-- Cleanup
-- ============================================================
UPDATE vendite.fatturazione_lotti
SET storicizza = false
WHERE id = (SELECT lotto_id FROM tmp_pipeline_ids);

DELETE FROM vendite.fatturazione_lotti_log
WHERE lotto_id = (SELECT lotto_id FROM tmp_pipeline_ids);

DELETE FROM vendite.fatturazione_lotti
WHERE id = (SELECT lotto_id FROM tmp_pipeline_ids);

DELETE FROM config.stati_doc_fiscale
WHERE id = (SELECT stato_doc_fiscale_id FROM tmp_pipeline_ids);

SELECT * FROM finish();

ROLLBACK;
