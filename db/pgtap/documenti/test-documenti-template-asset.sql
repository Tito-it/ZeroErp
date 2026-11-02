-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: documenti.template_asset
--   - dedup (emittente_fiscale_id, sha256)
--   - guard A3 (delete block fisico)
--   - guard A4 (immutabilita' file/hash/storage)
-- ------------------------------------------------------------
-- Indice test (1..7):
--  1) Setup: emittente fiscale disponibile, asset di base creato
--  2) Dedup sha256: stesso emittente + stesso sha256 bloccato
--  3) Stesso sha256 ammesso per emittente diverso (skip soft se em2 assente)
--  4) A3: DELETE fisico asset bloccato (sempre)
--  5) A4: UPDATE storage_key bloccato
--  6) A4: UPDATE sha256 bloccato
--  7) A4: UPDATE meta (non protetto) ammesso
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

SELECT plan(7);

-- ============================================================
-- Setup contesto + asset di base
-- ============================================================
CREATE TEMP TABLE tmp_ta_ctx AS
SELECT
  (SELECT ef.id FROM anagrafiche.emittenti_fiscali ef
    WHERE ef.attivo = true ORDER BY ef.id LIMIT 1)        AS emittente_id,
  (SELECT t.id FROM documenti.tipi_asset_documento t
    WHERE t.codice_interno = 'LOGO')                      AS tipo_logo_id;

WITH ins AS (
  INSERT INTO documenti.template_asset (
    codice, codice_interno, descrizione, asset_tipo_id,
    mime_type, file_name, file_size_bytes, storage_key, sha256,
    emittente_fiscale_id, attivo
  )
  SELECT 'PGTAP-ASSET-1', 'PGTAP_ASSET_1', 'Logo test',
         tipo_logo_id, 'image/png', 'logo.png', 1024,
         's3://bucket/pgtap/logo.png',
         repeat('a', 64),
         emittente_id, true
    FROM tmp_ta_ctx
   WHERE emittente_id IS NOT NULL
  RETURNING id
)
SELECT id INTO TEMP TABLE tmp_ta_asset FROM ins;

-- 1) Pre-condizione
SELECT ok(
  (SELECT COUNT(*) > 0 FROM tmp_ta_asset),
  'Setup: emittente fiscale disponibile, asset di base creato'
);

-- ============================================================
-- 2) Dedup sha256: stesso (emittente, sha256) bloccato
-- ============================================================
SELECT throws_ok(
  $$INSERT INTO documenti.template_asset (
      codice, codice_interno, descrizione, asset_tipo_id,
      mime_type, file_name, file_size_bytes, storage_key, sha256,
      emittente_fiscale_id, attivo
    )
    SELECT 'PGTAP-ASSET-1-BIS', 'PGTAP_ASSET_1_BIS', 'dup sha',
           tipo_logo_id, 'image/png', 'logo2.png', 2048,
           's3://bucket/pgtap/logo2.png',
           repeat('a', 64),
           emittente_id, true
      FROM tmp_ta_ctx$$,
  '23505',
  NULL,
  'Dedup sha256: stesso (emittente, sha256) bloccato'
);

-- ============================================================
-- 3) Stesso sha256 ammesso per emittente diverso (skip soft se em2 assente)
-- ============================================================
DO $$
DECLARE
  v_em2 bigint;
  v_ok  boolean := true;
BEGIN
  SELECT ef.id INTO v_em2
    FROM anagrafiche.emittenti_fiscali ef
   WHERE ef.attivo = true
     AND ef.id <> (SELECT emittente_id FROM tmp_ta_ctx)
   ORDER BY ef.id
   LIMIT 1;

  IF v_em2 IS NOT NULL THEN
    INSERT INTO documenti.template_asset (
      codice, codice_interno, descrizione, asset_tipo_id,
      mime_type, file_name, file_size_bytes, storage_key, sha256,
      emittente_fiscale_id, attivo
    )
    VALUES (
      'PGTAP-ASSET-EM2', 'PGTAP_ASSET_EM2', 'Logo em2',
      (SELECT tipo_logo_id FROM tmp_ta_ctx),
      'image/png', 'logo.png', 1024,
      's3://bucket/em2/logo.png',
      repeat('a', 64),
      v_em2, true
    );
    -- success: v_ok resta true
  END IF;

  CREATE TEMP TABLE tmp_ta_em2 AS SELECT v_ok AS ok;
EXCEPTION WHEN OTHERS THEN
  CREATE TEMP TABLE tmp_ta_em2 AS SELECT false AS ok;
END$$;

SELECT ok(
  (SELECT ok FROM tmp_ta_em2),
  'Stesso sha256 ammesso per emittente diverso (o skip soft se em2 assente)'
);

-- ============================================================
-- 4) A3: DELETE fisico asset bloccato (sempre)
-- ============================================================
SELECT throws_ok(
  $$DELETE FROM documenti.template_asset
     WHERE id = (SELECT id FROM tmp_ta_asset)$$,
  NULL,
  NULL,
  'A3: DELETE fisico template_asset sempre bloccato'
);

-- ============================================================
-- 5) A4: UPDATE storage_key bloccato
-- ============================================================
SELECT throws_ok(
  $$UPDATE documenti.template_asset
       SET storage_key = 's3://hack/logo.png'
     WHERE id = (SELECT id FROM tmp_ta_asset)$$,
  NULL,
  NULL,
  'A4: UPDATE storage_key bloccato'
);

-- 6) A4: UPDATE sha256 bloccato
SELECT throws_ok(
  $$UPDATE documenti.template_asset
       SET sha256 = repeat('b', 64)
     WHERE id = (SELECT id FROM tmp_ta_asset)$$,
  NULL,
  NULL,
  'A4: UPDATE sha256 bloccato'
);

-- 7) A4: UPDATE meta (non protetto) ammesso
UPDATE documenti.template_asset
   SET meta = '{"asset_test": "ok"}'::jsonb
 WHERE id = (SELECT id FROM tmp_ta_asset);

SELECT is(
  (SELECT meta->>'asset_test' FROM documenti.template_asset
    WHERE id = (SELECT id FROM tmp_ta_asset)),
  'ok',
  'A4: UPDATE meta (non protetto) ammesso'
);

SELECT * FROM finish();
ROLLBACK;
