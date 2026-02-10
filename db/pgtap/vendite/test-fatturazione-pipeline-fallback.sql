-- ============================================================
-- Indice test
-- 1) Setup: stato/config di test creati
-- 2) Resolve con utility+tipo_doc -> livello UTILITY_TIPO_DOC
-- 3) Resolve con utility -> livello UTILITY
-- 4) Resolve con tipo_doc -> livello TIPO_DOC
-- 5) Resolve fallback globale -> livello FALLBACK
-- 6) Lista step risolta usa la configurazione piu` specifica
-- 7) Guard resolve: p_stato_doc_fiscale_id obbligatorio (NULL)
-- 8) Guard list: p_tipo_lotto obbligatorio (NULL)
-- ============================================================

BEGIN;

SELECT plan(8);

CREATE TEMP TABLE tmp_pipeline_fb_costanti AS
SELECT
  'pgtap_fp_fb_' || to_char(clock_timestamp(), 'YYMMDDHH24MISS') AS test_scope;

CREATE TEMP TABLE tmp_pipeline_fb_ids (
  stato_doc_fiscale_id bigint,
  utility_id integer,
  tipo_doc_fiscale_id bigint
);

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
    left('TPFB_' || (SELECT test_scope FROM tmp_pipeline_fb_costanti), 30),
    'Stato pipeline fallback test',
    true,
    998,
    jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_pipeline_fb_costanti)),
    left('TPFB_' || (SELECT test_scope FROM tmp_pipeline_fb_costanti), 30),
    true,
    false
  RETURNING id
)
INSERT INTO tmp_pipeline_fb_ids (stato_doc_fiscale_id)
SELECT id FROM ins;

UPDATE tmp_pipeline_fb_ids
SET utility_id = (
  SELECT id
  FROM config.utilities
  ORDER BY id
  LIMIT 1
);

UPDATE tmp_pipeline_fb_ids
SET tipo_doc_fiscale_id = (
  SELECT id
  FROM config.tipi_doc_fiscale
  WHERE attivo IS TRUE
  ORDER BY id
  LIMIT 1
);

SELECT ok(
  (SELECT stato_doc_fiscale_id FROM tmp_pipeline_fb_ids) IS NOT NULL
  AND (SELECT utility_id FROM tmp_pipeline_fb_ids) IS NOT NULL
  AND (SELECT tipo_doc_fiscale_id FROM tmp_pipeline_fb_ids) IS NOT NULL,
  'Setup: stato/config di test creati'
);

INSERT INTO vendite.fatturazione_pipeline (
  descrizione,
  tipo_lotto,
  utility_id,
  tipo_doc_fiscale_id,
  stato_doc_fiscale_id,
  processi,
  rollback,
  attivo,
  meta
)
SELECT
  'Cfg fallback',
  'MASSIVO',
  NULL,
  NULL,
  i.stato_doc_fiscale_id,
  '[{"task":"noop","fase":"fallback"}]'::jsonb,
  '[]'::jsonb,
  true,
  jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_pipeline_fb_costanti), 'cfg', 'fallback')
FROM tmp_pipeline_fb_ids i;

INSERT INTO vendite.fatturazione_pipeline (
  descrizione,
  tipo_lotto,
  utility_id,
  tipo_doc_fiscale_id,
  stato_doc_fiscale_id,
  processi,
  rollback,
  attivo,
  meta
)
SELECT
  'Cfg utility',
  'MASSIVO',
  i.utility_id,
  NULL,
  i.stato_doc_fiscale_id,
  '[{"task":"noop","fase":"utility"}]'::jsonb,
  '[]'::jsonb,
  true,
  jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_pipeline_fb_costanti), 'cfg', 'utility')
FROM tmp_pipeline_fb_ids i;

INSERT INTO vendite.fatturazione_pipeline (
  descrizione,
  tipo_lotto,
  utility_id,
  tipo_doc_fiscale_id,
  stato_doc_fiscale_id,
  processi,
  rollback,
  attivo,
  meta
)
SELECT
  'Cfg tipo_doc',
  'MASSIVO',
  NULL,
  i.tipo_doc_fiscale_id,
  i.stato_doc_fiscale_id,
  '[{"task":"noop","fase":"tipo_doc"}]'::jsonb,
  '[]'::jsonb,
  true,
  jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_pipeline_fb_costanti), 'cfg', 'tipo_doc')
FROM tmp_pipeline_fb_ids i;

INSERT INTO vendite.fatturazione_pipeline (
  descrizione,
  tipo_lotto,
  utility_id,
  tipo_doc_fiscale_id,
  stato_doc_fiscale_id,
  processi,
  rollback,
  attivo,
  meta
)
SELECT
  'Cfg utility+tipo_doc',
  'MASSIVO',
  i.utility_id,
  i.tipo_doc_fiscale_id,
  i.stato_doc_fiscale_id,
  '[{"task":"noop","fase":"utility_tipo_doc"}]'::jsonb,
  '[]'::jsonb,
  true,
  jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_pipeline_fb_costanti), 'cfg', 'utility_tipo_doc')
FROM tmp_pipeline_fb_ids i;

SELECT is(
  (
    SELECT livello_match
    FROM vendite.fn_resolve_fatturazione_pipeline_step(
      p_tipo_lotto => 'MASSIVO',
      p_stato_doc_fiscale_id => (SELECT stato_doc_fiscale_id FROM tmp_pipeline_fb_ids),
      p_utility_id => (SELECT utility_id FROM tmp_pipeline_fb_ids),
      p_tipo_doc_fiscale_id => (SELECT tipo_doc_fiscale_id FROM tmp_pipeline_fb_ids),
      p_rollback => false
    )
  ),
  'UTILITY_TIPO_DOC',
  'Resolve con utility+tipo_doc -> livello UTILITY_TIPO_DOC'
);

SELECT is(
  (
    SELECT livello_match
    FROM vendite.fn_resolve_fatturazione_pipeline_step(
      p_tipo_lotto => 'MASSIVO',
      p_stato_doc_fiscale_id => (SELECT stato_doc_fiscale_id FROM tmp_pipeline_fb_ids),
      p_utility_id => (SELECT utility_id FROM tmp_pipeline_fb_ids),
      p_tipo_doc_fiscale_id => NULL,
      p_rollback => false
    )
  ),
  'UTILITY',
  'Resolve con utility -> livello UTILITY'
);

SELECT is(
  (
    SELECT livello_match
    FROM vendite.fn_resolve_fatturazione_pipeline_step(
      p_tipo_lotto => 'MASSIVO',
      p_stato_doc_fiscale_id => (SELECT stato_doc_fiscale_id FROM tmp_pipeline_fb_ids),
      p_utility_id => NULL,
      p_tipo_doc_fiscale_id => (SELECT tipo_doc_fiscale_id FROM tmp_pipeline_fb_ids),
      p_rollback => false
    )
  ),
  'TIPO_DOC',
  'Resolve con tipo_doc -> livello TIPO_DOC'
);

SELECT is(
  (
    SELECT livello_match
    FROM vendite.fn_resolve_fatturazione_pipeline_step(
      p_tipo_lotto => 'MASSIVO',
      p_stato_doc_fiscale_id => (SELECT stato_doc_fiscale_id FROM tmp_pipeline_fb_ids),
      p_utility_id => NULL,
      p_tipo_doc_fiscale_id => NULL,
      p_rollback => false
    )
  ),
  'FALLBACK',
  'Resolve fallback globale -> livello FALLBACK'
);

SELECT is(
  (
    SELECT descrizione
    FROM vendite.fn_list_fatturazione_pipeline_steps(
      p_tipo_lotto => 'MASSIVO',
      p_utility_id => (SELECT utility_id FROM tmp_pipeline_fb_ids),
      p_tipo_doc_fiscale_id => (SELECT tipo_doc_fiscale_id FROM tmp_pipeline_fb_ids)
    )
    WHERE stato_doc_fiscale_id = (SELECT stato_doc_fiscale_id FROM tmp_pipeline_fb_ids)
  ),
  'Cfg utility+tipo_doc',
  'Lista step risolta usa la configurazione piu` specifica'
);

SELECT throws_ok(
  $$
  SELECT *
  FROM vendite.fn_resolve_fatturazione_pipeline_step(
    p_tipo_lotto => 'MASSIVO',
    p_stato_doc_fiscale_id => NULL,
    p_utility_id => NULL,
    p_tipo_doc_fiscale_id => NULL,
    p_rollback => false
  );
  $$,
  'P0001',
  NULL,
  'Guard resolve: p_stato_doc_fiscale_id obbligatorio (NULL)'
);

SELECT throws_ok(
  $$
  SELECT *
  FROM vendite.fn_list_fatturazione_pipeline_steps(
    p_tipo_lotto => NULL,
    p_utility_id => NULL,
    p_tipo_doc_fiscale_id => NULL
  );
  $$,
  'P0001',
  NULL,
  'Guard list: p_tipo_lotto obbligatorio (NULL)'
);

DELETE FROM vendite.fatturazione_pipeline
WHERE meta ->> 'test_scope' = (SELECT test_scope FROM tmp_pipeline_fb_costanti);

DELETE FROM config.stati_doc_fiscale
WHERE id = (SELECT stato_doc_fiscale_id FROM tmp_pipeline_fb_ids);

SELECT * FROM finish();

ROLLBACK;
