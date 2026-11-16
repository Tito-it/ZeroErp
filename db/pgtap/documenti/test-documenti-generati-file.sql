-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: documenti.documenti_generati_file
--   - guard A7-bis (immutabilita' file)
--   - C: indice parziale uq_documenti_generati_file_principale
--   - C: vincolo unique (documento_generato_id, file_tipo_id, ordinamento)
-- ------------------------------------------------------------
-- Indice test (1..8):
--  1) Setup: documento generato con un file principale
--  2) Un secondo file con is_principale=true sullo stesso documento bloccato
--  3) Un secondo file con is_principale=false sullo stesso documento ammesso
--  4) Stesso (doc, file_tipo, ordinamento) bloccato
--  5) Stesso (doc, file_tipo) con ordinamento diverso ammesso
--  6) A7-bis: UPDATE storage_key bloccato
--  7) A7-bis: UPDATE is_principale bloccato
--  8) A7-bis: UPDATE meta (non protetto) ammesso
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

-- ⭐ La stampa e' di un preventivo VERO, del mondo dell'operatore in sessione: dal
--   lotto D di brief-db-sorgente-documento-e-riga il guard unico verifica che il
--   documento stampato esista, e la chiave di un preventivo e' il suo uid.
CREATE TEMP TABLE _dg_src AS
SELECT p.preventivo_uid FROM dbops.fn_pgtap_crea_preventivo('dg file', 'DRAFT') p;


SELECT plan(8);

-- ============================================================
-- Setup: documento generato + file principale
-- ============================================================
CREATE TEMP TABLE tmp_dgf_ctx AS
SELECT
  (SELECT ef.id FROM anagrafiche.emittenti_fiscali ef
    WHERE ef.attivo = true ORDER BY ef.id LIMIT 1)               AS emittente_id,
  (SELECT s.id FROM config.sorgenti s
    WHERE s.codice_interno = 'PREVENTIVO')                       AS sorgente_id,
  (SELECT t.id FROM documenti.tipi_documento_output t
    WHERE t.codice_interno = 'PREVENTIVO')                       AS tipo_output_id,
  (SELECT r.id FROM documenti.render_engine_documento r
    WHERE r.codice_interno = 'WEASYPRINT')                       AS render_id,
  (SELECT f.id FROM documenti.tipi_file_documento f
    WHERE f.codice_interno = 'PDF_FINALE')                       AS file_tipo_id;

WITH ins_t AS (
  INSERT INTO documenti.template_documenti (
    tipo_documento_output_id, codice, codice_interno, descrizione,
    sorgente_tipo_id, context_builder_code, emittente_fiscale_id,
    is_default, attivo
  )
  SELECT tipo_output_id, 'PGTAP-DGF', 'PGTAP_DGF', 'Template per file',
         sorgente_id, 'pgtap.builder', emittente_id, false, true
    FROM tmp_dgf_ctx WHERE emittente_id IS NOT NULL
  RETURNING id
)
SELECT id INTO TEMP TABLE tmp_dgf_template FROM ins_t;

WITH ins_v AS (
  INSERT INTO documenti.template_documenti_versioni (
    template_documento_id, versione, stato, titolo, html_template,
    render_engine_id, valido_dal, valido_al, versione_contesto
  )
  SELECT (SELECT id FROM tmp_dgf_template),
         1, 'BOZZA', 'v1', '<html>v1</html>',
         (SELECT render_id FROM tmp_dgf_ctx),
         DATE '2026-01-01', DATE '2026-12-31', 1
  RETURNING id
)
SELECT id INTO TEMP TABLE tmp_dgf_versione FROM ins_v;

-- ⚠️ Una versione nasce in bozza ed esce dalla bozza solo dal verbo della
--   pubblicazione (guard dello stato, 20261116-02): la fixture lo percorre.
SELECT documenti.fn_pubblica_template_documento_versione(
  (SELECT id FROM tmp_dgf_versione), DATE '2026-01-01', 1, DATE '2026-12-31');

-- ⚠️ La stampa nasce col suo PDF principale (dbops.fn_pgtap_stampa_con_pdf): senza,
--   non si registra (guard differito, che IMMEDIATE fa scattare a fine istruzione).
CREATE TEMP TABLE tmp_dgf_doc AS
SELECT dbops.fn_pgtap_stampa_con_pdf($i$
  INSERT INTO documenti.documenti_generati (
    tipo_documento_output_id, template_documento_id, template_versione_id,
    sorgente_tipo_id, sorgente_uid, sorgente_riga, progressivo_sorgente,
    titolo, nome_file, context_json, context_hash, template_hash, pdf_hash,
    emittente_fiscale_id
  )
  SELECT
    (SELECT tipo_output_id FROM tmp_dgf_ctx),
    (SELECT id FROM tmp_dgf_template),
    (SELECT id FROM tmp_dgf_versione),
    (SELECT sorgente_id FROM tmp_dgf_ctx),
    (SELECT preventivo_uid FROM _dg_src), NULL, 1,
    'Doc file', 'doc-file.pdf',
    '{"y": 1, "_meta": {"context_version": 1}}'::jsonb,
    repeat('1', 64), repeat('2', 64), repeat('3', 64),
    (SELECT emittente_id FROM tmp_dgf_ctx)$i$) AS id;

CREATE TEMP TABLE tmp_dgf_file AS
SELECT f.id FROM documenti.documenti_generati_file f
 WHERE f.documento_generato_id = (SELECT id FROM tmp_dgf_doc) AND f.is_principale;

-- 1) Pre-condizione
SELECT ok(
  (SELECT COUNT(*) FROM tmp_dgf_file) = 1,
  'Setup: documento generato con un file principale'
);

-- ============================================================
-- 2) C: secondo file is_principale=true sullo stesso documento bloccato
--    (indice parziale uq_documenti_generati_file_principale)
-- ============================================================
SELECT throws_ok(
  $$INSERT INTO documenti.documenti_generati_file (
      documento_generato_id, file_tipo_id, mime_type, file_name,
      file_size_bytes, storage_key, sha256, ordinamento, is_principale
    )
    SELECT (SELECT id FROM tmp_dgf_doc),
           (SELECT file_tipo_id FROM tmp_dgf_ctx),
           'application/pdf', 'altro.pdf',
           5120, 's3://bucket/pgtap/altro.pdf',
           repeat('e', 64), 2, true$$,
  '23505',
  NULL,
  'C: secondo file is_principale=true sullo stesso documento bloccato'
);

-- ============================================================
-- 3) Secondo file is_principale=false sullo stesso documento ammesso
--    (con ordinamento diverso per evitare collisione su uq doc/tipo/ord)
-- ============================================================
INSERT INTO documenti.documenti_generati_file (
  documento_generato_id, file_tipo_id, mime_type, file_name,
  file_size_bytes, storage_key, sha256, ordinamento, is_principale
)
SELECT (SELECT id FROM tmp_dgf_doc),
       (SELECT file_tipo_id FROM tmp_dgf_ctx),
       'application/pdf', 'accessorio.pdf',
       3072, 's3://bucket/pgtap/accessorio.pdf',
       repeat('d', 64), 2, false;

SELECT is(
  (SELECT COUNT(*)::int FROM documenti.documenti_generati_file
    WHERE documento_generato_id = (SELECT id FROM tmp_dgf_doc)),
  2,
  'Secondo file is_principale=false sullo stesso documento ammesso'
);

-- ============================================================
-- 4) C: stesso (doc, file_tipo, ordinamento) bloccato
-- ============================================================
SELECT throws_ok(
  $$INSERT INTO documenti.documenti_generati_file (
      documento_generato_id, file_tipo_id, mime_type, file_name,
      file_size_bytes, storage_key, sha256, ordinamento, is_principale
    )
    SELECT (SELECT id FROM tmp_dgf_doc),
           (SELECT file_tipo_id FROM tmp_dgf_ctx),
           'application/pdf', 'altro2.pdf',
           1024, 's3://bucket/pgtap/altro2.pdf',
           repeat('c', 64), 1, false$$,
  '23505',
  NULL,
  'C: stesso (doc, file_tipo, ordinamento) bloccato (uq_doc_tipo_ord)'
);

-- ============================================================
-- 5) C: stesso (doc, file_tipo) con ordinamento distinto ammesso
--    (gia' verificato implicitamente dal test 3, ma esplicitiamo:
--     conferma che count=2 sotto stesso file_tipo_id e' valido)
-- ============================================================
SELECT is(
  (SELECT COUNT(*)::int FROM documenti.documenti_generati_file
    WHERE documento_generato_id = (SELECT id FROM tmp_dgf_doc)
      AND file_tipo_id = (SELECT file_tipo_id FROM tmp_dgf_ctx)),
  2,
  'C: stesso (doc, file_tipo) con ordinamento distinto ammesso'
);

-- ============================================================
-- 6) A7-bis: UPDATE storage_key bloccato
-- ============================================================
SELECT throws_ok(
  $$UPDATE documenti.documenti_generati_file
       SET storage_key = 's3://hack/finale.pdf'
     WHERE id = (SELECT id FROM tmp_dgf_file)$$,
  NULL,
  NULL,
  'A7-bis: UPDATE storage_key bloccato'
);

-- 7) A7-bis: UPDATE is_principale bloccato
SELECT throws_ok(
  $$UPDATE documenti.documenti_generati_file
       SET is_principale = false
     WHERE id = (SELECT id FROM tmp_dgf_file)$$,
  NULL,
  NULL,
  'A7-bis: UPDATE is_principale bloccato'
);

-- 8) A7-bis: UPDATE meta (non protetto) ammesso
UPDATE documenti.documenti_generati_file
   SET meta = '{"checked": true}'::jsonb
 WHERE id = (SELECT id FROM tmp_dgf_file);

SELECT is(
  (SELECT meta->>'checked' FROM documenti.documenti_generati_file
    WHERE id = (SELECT id FROM tmp_dgf_file)),
  'true',
  'A7-bis: UPDATE meta (non protetto) ammesso'
);

SELECT * FROM finish();
ROLLBACK;
