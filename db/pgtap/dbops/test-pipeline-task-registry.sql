-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Funzioni: dbops.fn_check_pipeline_task_registered, dbops.fn_get_pipeline_task_implementation
-- ------------------------------------------------------------
-- Indice test
-- 1) Presenza fn_check_pipeline_task_registered
-- 2) Presenza fn_get_pipeline_task_implementation
-- 3) Setup dominio/task/impl di test
-- 4) fn_check_pipeline_task_registered ritorna true
-- 5) fn_get_pipeline_task_implementation risolve implementazione richiesta
-- 6) fn_get_pipeline_task_implementation fallback su default
-- 7) fn_check_pipeline_task_registered errore su task assente
-- 8) fn_get_pipeline_task_implementation errore se manca default
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file sarebbe verde per sottrazione. IMMEDIATE li riporta a scattare a fine
--   di ogni istruzione. In testa e non in coda: in coda scatterebbero dopo il
--   cleanup, su righe ormai cancellate.
--   Brief: brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(8);

CREATE TEMP TABLE tmp_registry_ctx AS
SELECT 'pgtap_ptr_' || to_char(clock_timestamp(), 'YYMMDDHH24MISS') AS test_scope;

CREATE TEMP TABLE tmp_registry_ids (
  dominio_id bigint,
  task_id bigint,
  impl_id bigint,
  task_no_default_id bigint
);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'dbops'
      AND p.proname = 'fn_check_pipeline_task_registered'
  ),
  'Presenza fn_check_pipeline_task_registered'
);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'dbops'
      AND p.proname = 'fn_get_pipeline_task_implementation'
  ),
  'Presenza fn_get_pipeline_task_implementation'
);

WITH ins_dom AS (
  INSERT INTO dbops.domini_task (codice, descrizione, attivo, meta)
  SELECT
    left('PTR_' || (SELECT test_scope FROM tmp_registry_ctx), 30),
    'Dominio test pipeline task',
    true,
    jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_registry_ctx))
  RETURNING id
),
ins_task AS (
  INSERT INTO dbops.pipeline_task_registry (dominio_id, task_code, descrizione, attivo, meta)
  SELECT
    (SELECT id FROM ins_dom),
    'select_attivita',
    'Task test select_attivita',
    true,
    jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_registry_ctx))
  RETURNING id
),
ins_impl AS (
  INSERT INTO dbops.pipeline_task_registry_impl (
    task_registry_id,
    implementation_key,
    handler_code,
    is_default,
    attivo,
    meta
  )
  SELECT
    (SELECT id FROM ins_task),
    'default',
    'select_attivita_default',
    true,
    true,
    jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_registry_ctx))
  RETURNING id
),
ins_task_no_def AS (
  INSERT INTO dbops.pipeline_task_registry (dominio_id, task_code, descrizione, attivo, meta)
  SELECT
    (SELECT id FROM ins_dom),
    'task_no_default',
    'Task senza default',
    true,
    jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_registry_ctx))
  RETURNING id
)
INSERT INTO tmp_registry_ids (dominio_id, task_id, impl_id, task_no_default_id)
SELECT
  (SELECT id FROM ins_dom),
  (SELECT id FROM ins_task),
  (SELECT id FROM ins_impl),
  (SELECT id FROM ins_task_no_def);

SELECT ok(
  (SELECT dominio_id FROM tmp_registry_ids) IS NOT NULL
  AND (SELECT task_id FROM tmp_registry_ids) IS NOT NULL
  AND (SELECT impl_id FROM tmp_registry_ids) IS NOT NULL,
  'Setup dominio/task/impl di test'
);

SELECT ok(
  dbops.fn_check_pipeline_task_registered(
    (SELECT dominio_id FROM tmp_registry_ids),
    'select_attivita'
  ),
  'fn_check_pipeline_task_registered ritorna true'
);

SELECT is(
  (
    SELECT handler_code
    FROM dbops.fn_get_pipeline_task_implementation(
      (SELECT dominio_id FROM tmp_registry_ids),
      'select_attivita',
      'default'
    )
  ),
  'select_attivita_default',
  'fn_get_pipeline_task_implementation risolve implementazione richiesta'
);

SELECT is(
  (
    SELECT handler_code
    FROM dbops.fn_get_pipeline_task_implementation(
      (SELECT dominio_id FROM tmp_registry_ids),
      'select_attivita',
      'non_esiste'
    )
  ),
  'select_attivita_default',
  'fn_get_pipeline_task_implementation fallback su default'
);

SELECT throws_ok(
  $$
  SELECT dbops.fn_check_pipeline_task_registered(
    (SELECT dominio_id FROM tmp_registry_ids),
    'task_inesistente'
  );
  $$,
  'P0001',
  NULL,
  'fn_check_pipeline_task_registered errore su task assente'
);

SELECT throws_ok(
  $$
  SELECT *
  FROM dbops.fn_get_pipeline_task_implementation(
    (SELECT dominio_id FROM tmp_registry_ids),
    'task_no_default',
    NULL
  );
  $$,
  'P0001',
  NULL,
  'fn_get_pipeline_task_implementation errore se manca default'
);

DELETE FROM dbops.pipeline_task_registry_impl
WHERE meta ->> 'test_scope' = (SELECT test_scope FROM tmp_registry_ctx);

DELETE FROM dbops.pipeline_task_registry
WHERE meta ->> 'test_scope' = (SELECT test_scope FROM tmp_registry_ctx);

DELETE FROM dbops.domini_task
WHERE meta ->> 'test_scope' = (SELECT test_scope FROM tmp_registry_ctx);

SELECT * FROM finish();

ROLLBACK;
