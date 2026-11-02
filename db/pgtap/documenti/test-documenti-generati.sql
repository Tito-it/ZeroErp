-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: documenti.documenti_generati
--   - guard A5 (delete block)
--   - guard A6 (coerenza referenziale)
--   - guard A7 (immutabilita' snapshot)
--   - unique progressivo con sorgente_riga NULL (NULLS NOT DISTINCT)
--   - unique uid
-- ------------------------------------------------------------
-- Indice test (1..10):
--  1) Setup: emittente, template e versione PUBBLICATA disponibili
--  2) Insert documento generato coerente passa
--  3) A6: tipo_documento_output_id incoerente bloccato
--  4) A6: emittente_fiscale_id incoerente bloccato
--  5) NULLS NOT DISTINCT: due righe con stesso (sorgente_tipo, sorgente_uid,
--     sorgente_riga=NULL, progressivo) bloccate
--  6) A5: DELETE fisico documenti_generati bloccato
--  7) A7: UPDATE context_json bloccato
--  8) A7: UPDATE template_versione_id bloccato
--  9) A7: UPDATE stato (non protetto) ammesso
-- 10) A7: UPDATE meta (non protetto) ammesso
-- ⚠️ Dal 2026-09-30 ogni contesto porta _meta.context_version e la versione
--    versione_contesto (brief-db-documenti-versione-contesto-template): senza,
--    il guard della forma (20260930-20, BEFORE INSERT) parlerebbe al posto dei
--    rifiuti che questi test attendono — il 23505 del test 5 per primo. Il
--    guard ha il suo file: test-documenti-versione-contesto-v1.sql.
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

SELECT plan(10);

-- ============================================================
-- Setup contesto: template + versione PUBBLICATA
-- ============================================================
CREATE TEMP TABLE tmp_dg_ctx AS
SELECT
  (SELECT ef.id FROM anagrafiche.emittenti_fiscali ef
    WHERE ef.attivo = true ORDER BY ef.id LIMIT 1)               AS emittente_id,
  (SELECT s.id FROM config.sorgenti s
    WHERE s.codice_interno = 'PREVENTIVO')                       AS sorgente_id,
  (SELECT t.id FROM documenti.tipi_documento_output t
    WHERE t.codice_interno = 'PREVENTIVO')                       AS tipo_output_id,
  (SELECT r.id FROM documenti.render_engine_documento r
    WHERE r.codice_interno = 'WEASYPRINT')                       AS render_id;

WITH ins_t AS (
  INSERT INTO documenti.template_documenti (
    tipo_documento_output_id, codice, codice_interno, descrizione,
    sorgente_tipo_id, context_builder_code, emittente_fiscale_id,
    is_default, attivo
  )
  SELECT tipo_output_id, 'PGTAP-DG', 'PGTAP_DG', 'Template per generati',
         sorgente_id, 'pgtap.builder', emittente_id, false, true
    FROM tmp_dg_ctx
   WHERE emittente_id IS NOT NULL
  RETURNING id
)
SELECT id INTO TEMP TABLE tmp_dg_template FROM ins_t;

WITH ins_v AS (
  INSERT INTO documenti.template_documenti_versioni (
    template_documento_id, versione, stato, titolo, html_template,
    render_engine_id, valido_dal, valido_al, versione_contesto
  )
  SELECT (SELECT id FROM tmp_dg_template),
         1, 'PUBBLICATA', 'v1', '<html>v1</html>',
         (SELECT render_id FROM tmp_dg_ctx),
         DATE '2026-01-01', DATE '2026-12-31', 1
  RETURNING id
)
SELECT id INTO TEMP TABLE tmp_dg_versione FROM ins_v;

-- 1) Pre-condizione: setup completo
SELECT ok(
  (SELECT COUNT(*) FROM tmp_dg_versione) = 1,
  'Setup: emittente, template e versione PUBBLICATA disponibili'
);

-- ============================================================
-- 2) Insert documento generato coerente
-- ============================================================
INSERT INTO documenti.documenti_generati (
  tipo_documento_output_id, template_documento_id, template_versione_id,
  sorgente_tipo_id, sorgente_uid, sorgente_riga, progressivo_sorgente,
  titolo, nome_file, context_json, context_hash, template_hash, pdf_hash,
  emittente_fiscale_id
)
SELECT
  (SELECT tipo_output_id FROM tmp_dg_ctx),
  (SELECT id FROM tmp_dg_template),
  (SELECT id FROM tmp_dg_versione),
  (SELECT sorgente_id FROM tmp_dg_ctx),
  'PGTAP-SOURCE-001', NULL, 1,
  'Doc 1', 'doc1.pdf',
  '{"tot": 100, "_meta": {"context_version": 1}}'::jsonb,
  repeat('1', 64), repeat('2', 64), repeat('3', 64),
  (SELECT emittente_id FROM tmp_dg_ctx);

SELECT is(
  (SELECT COUNT(*)::int FROM documenti.documenti_generati
    WHERE template_versione_id = (SELECT id FROM tmp_dg_versione)),
  1,
  'Insert documento generato coerente passa'
);

-- ============================================================
-- 3) A6: tipo_documento_output_id incoerente bloccato
-- ============================================================
SELECT throws_ok(
  $$INSERT INTO documenti.documenti_generati (
      tipo_documento_output_id, template_documento_id, template_versione_id,
      sorgente_tipo_id, sorgente_uid, sorgente_riga, progressivo_sorgente,
      titolo, nome_file, context_json, context_hash, template_hash, pdf_hash,
      emittente_fiscale_id
    )
    SELECT
      99999,
      (SELECT id FROM tmp_dg_template),
      (SELECT id FROM tmp_dg_versione),
      (SELECT sorgente_id FROM tmp_dg_ctx),
      'PGTAP-SOURCE-002', NULL, 2,
      'Doc bad tipo', 'doc-bad.pdf',
      '{"x": 1, "_meta": {"context_version": 1}}'::jsonb,
      repeat('a', 64), repeat('b', 64), repeat('c', 64),
      (SELECT emittente_id FROM tmp_dg_ctx)$$,
  NULL,
  NULL,
  'A6: tipo_documento_output_id incoerente bloccato'
);

-- ============================================================
-- 4) A6: emittente_fiscale_id incoerente bloccato
-- ============================================================
DO $$
DECLARE
  v_em2 bigint;
BEGIN
  SELECT ef.id INTO v_em2
    FROM anagrafiche.emittenti_fiscali ef
   WHERE ef.id <> (SELECT emittente_id FROM tmp_dg_ctx)
     AND ef.attivo = true
   ORDER BY ef.id
   LIMIT 1;

  IF v_em2 IS NULL THEN v_em2 := 999999; END IF;

  CREATE TEMP TABLE tmp_dg_em2 AS SELECT v_em2 AS id;
END$$;

SELECT throws_ok(
  format($q$
    INSERT INTO documenti.documenti_generati (
      tipo_documento_output_id, template_documento_id, template_versione_id,
      sorgente_tipo_id, sorgente_uid, sorgente_riga, progressivo_sorgente,
      titolo, nome_file, context_json, context_hash, template_hash, pdf_hash,
      emittente_fiscale_id
    )
    SELECT
      (SELECT tipo_output_id FROM tmp_dg_ctx),
      (SELECT id FROM tmp_dg_template),
      (SELECT id FROM tmp_dg_versione),
      (SELECT sorgente_id FROM tmp_dg_ctx),
      'PGTAP-SOURCE-003', NULL, 3,
      'Doc bad em', 'doc-bad-em.pdf',
      '{"x": 2, "_meta": {"context_version": 1}}'::jsonb,
      repeat('a', 64), repeat('b', 64), repeat('c', 64),
      %s
  $q$, (SELECT id FROM tmp_dg_em2)),
  NULL,
  NULL,
  'A6: emittente_fiscale_id incoerente bloccato'
);

-- ============================================================
-- 5) NULLS NOT DISTINCT: stesso (sorgente_tipo, uid, riga=NULL, progressivo)
-- ============================================================
SELECT throws_ok(
  $$INSERT INTO documenti.documenti_generati (
      tipo_documento_output_id, template_documento_id, template_versione_id,
      sorgente_tipo_id, sorgente_uid, sorgente_riga, progressivo_sorgente,
      titolo, nome_file, context_json, context_hash, template_hash, pdf_hash,
      emittente_fiscale_id
    )
    SELECT
      (SELECT tipo_output_id FROM tmp_dg_ctx),
      (SELECT id FROM tmp_dg_template),
      (SELECT id FROM tmp_dg_versione),
      (SELECT sorgente_id FROM tmp_dg_ctx),
      'PGTAP-SOURCE-001', NULL, 1,
      'Doc dup', 'doc-dup.pdf',
      '{"x": 9, "_meta": {"context_version": 1}}'::jsonb,
      repeat('a', 64), repeat('b', 64), repeat('c', 64),
      (SELECT emittente_id FROM tmp_dg_ctx)$$,
  '23505',
  NULL,
  'NULLS NOT DISTINCT: dup (sorgente_tipo, uid, riga=NULL, progressivo) bloccato'
);

-- ============================================================
-- 6) A5: DELETE fisico documenti_generati bloccato
-- ============================================================
SELECT throws_ok(
  $$DELETE FROM documenti.documenti_generati
     WHERE template_versione_id = (SELECT id FROM tmp_dg_versione)$$,
  NULL,
  NULL,
  'A5: DELETE fisico documenti_generati bloccato'
);

-- ============================================================
-- 7) A7: UPDATE context_json bloccato
-- ============================================================
SELECT throws_ok(
  $$UPDATE documenti.documenti_generati
       SET context_json = '{"hack": true}'::jsonb
     WHERE template_versione_id = (SELECT id FROM tmp_dg_versione)$$,
  NULL,
  NULL,
  'A7: UPDATE context_json bloccato'
);

-- 8) A7: UPDATE template_versione_id bloccato
SELECT throws_ok(
  $$UPDATE documenti.documenti_generati
       SET template_versione_id = 999999
     WHERE template_versione_id = (SELECT id FROM tmp_dg_versione)$$,
  NULL,
  NULL,
  'A7: UPDATE template_versione_id bloccato'
);

-- 9) A7: UPDATE stato (campo non protetto) ammesso
UPDATE documenti.documenti_generati
   SET stato = 'ARCHIVIATO'
 WHERE template_versione_id = (SELECT id FROM tmp_dg_versione);

SELECT is(
  (SELECT stato FROM documenti.documenti_generati
    WHERE template_versione_id = (SELECT id FROM tmp_dg_versione)),
  'ARCHIVIATO',
  'A7: UPDATE stato (GENERATO -> ARCHIVIATO) ammesso'
);

-- 10) A7: UPDATE meta (campo non protetto) ammesso
UPDATE documenti.documenti_generati
   SET meta = '{"audit": "test"}'::jsonb
 WHERE template_versione_id = (SELECT id FROM tmp_dg_versione);

SELECT is(
  (SELECT meta->>'audit' FROM documenti.documenti_generati
    WHERE template_versione_id = (SELECT id FROM tmp_dg_versione)),
  'test',
  'A7: UPDATE meta (non protetto) ammesso'
);

SELECT * FROM finish();
ROLLBACK;
