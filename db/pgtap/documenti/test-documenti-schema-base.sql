-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: schema documenti + tabelle base + check minori (E1..E4)
-- Riferimento: sviluppo-documenti-db.md §13.3 F
-- ------------------------------------------------------------
-- Indice test (1..18):
--  1) Schema documenti presente
--  2) Tabella documenti.tipi_documento_output presente
--  3) Tabella documenti.tipi_asset_documento presente
--  4) Tabella documenti.tipi_file_documento presente
--  5) Tabella documenti.render_engine_documento presente
--  6) Tabella documenti.template_documenti presente
--  7) Tabella documenti.template_documenti_versioni presente
--  8) Tabella documenti.template_asset presente
--  9) Tabella documenti.documenti_generati presente
-- 10) Tabella documenti.documenti_generati_file presente
-- 11) Schema 'documenti,*all' registrato in dbops.automation_scope
-- 12) E1: chk_template_documenti_file_name_pattern_non_vuoto presente
-- 13) E2: chk_template_documenti_versioni_context_schema_obj presente
-- 14) E3: chk_template_documenti_versioni_html_template_non_vuoto presente
-- 15) E4: chk_documenti_generati_context_json_obj presente
-- 16) C: colonna is_principale presente su documenti_generati_file
-- 17) C: indice parziale uq_documenti_generati_file_principale presente
-- 18) C: vincolo uq_documenti_generati_file_doc_tipo_ord presente
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

SELECT plan(18);

-- 1) Schema documenti presente
SELECT ok(
  EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'documenti'),
  'Schema documenti presente'
);

-- 2..10) Tabelle base
SELECT ok(
  EXISTS (SELECT 1 FROM information_schema.tables
          WHERE table_schema = 'documenti' AND table_name = 'tipi_documento_output'),
  'Tabella documenti.tipi_documento_output presente'
);
SELECT ok(
  EXISTS (SELECT 1 FROM information_schema.tables
          WHERE table_schema = 'documenti' AND table_name = 'tipi_asset_documento'),
  'Tabella documenti.tipi_asset_documento presente'
);
SELECT ok(
  EXISTS (SELECT 1 FROM information_schema.tables
          WHERE table_schema = 'documenti' AND table_name = 'tipi_file_documento'),
  'Tabella documenti.tipi_file_documento presente'
);
SELECT ok(
  EXISTS (SELECT 1 FROM information_schema.tables
          WHERE table_schema = 'documenti' AND table_name = 'render_engine_documento'),
  'Tabella documenti.render_engine_documento presente'
);
SELECT ok(
  EXISTS (SELECT 1 FROM information_schema.tables
          WHERE table_schema = 'documenti' AND table_name = 'template_documenti'),
  'Tabella documenti.template_documenti presente'
);
SELECT ok(
  EXISTS (SELECT 1 FROM information_schema.tables
          WHERE table_schema = 'documenti' AND table_name = 'template_documenti_versioni'),
  'Tabella documenti.template_documenti_versioni presente'
);
SELECT ok(
  EXISTS (SELECT 1 FROM information_schema.tables
          WHERE table_schema = 'documenti' AND table_name = 'template_asset'),
  'Tabella documenti.template_asset presente'
);
SELECT ok(
  EXISTS (SELECT 1 FROM information_schema.tables
          WHERE table_schema = 'documenti' AND table_name = 'documenti_generati'),
  'Tabella documenti.documenti_generati presente'
);
SELECT ok(
  EXISTS (SELECT 1 FROM information_schema.tables
          WHERE table_schema = 'documenti' AND table_name = 'documenti_generati_file'),
  'Tabella documenti.documenti_generati_file presente'
);

-- 11) Scope automazioni registrato per schema documenti
SELECT ok(
  EXISTS (
    SELECT 1 FROM dbops.automation_scope
    WHERE schema_name = 'documenti' AND table_like = '*all'
  ),
  'Scope automazioni documenti,*all registrato'
);

-- 12..15) Check E1..E4 presenti
SELECT ok(
  EXISTS (
    SELECT 1 FROM information_schema.table_constraints
    WHERE table_schema = 'documenti'
      AND table_name = 'template_documenti'
      AND constraint_name = 'chk_template_documenti_file_name_pattern_non_vuoto'
      AND constraint_type = 'CHECK'
  ),
  'E1: chk_template_documenti_file_name_pattern_non_vuoto presente'
);
SELECT ok(
  EXISTS (
    SELECT 1 FROM information_schema.table_constraints
    WHERE table_schema = 'documenti'
      AND table_name = 'template_documenti_versioni'
      AND constraint_name = 'chk_template_documenti_versioni_context_schema_obj'
      AND constraint_type = 'CHECK'
  ),
  'E2: chk_template_documenti_versioni_context_schema_obj presente'
);
SELECT ok(
  EXISTS (
    SELECT 1 FROM information_schema.table_constraints
    WHERE table_schema = 'documenti'
      AND table_name = 'template_documenti_versioni'
      AND constraint_name = 'chk_template_documenti_versioni_html_template_non_vuoto'
      AND constraint_type = 'CHECK'
  ),
  'E3: chk_template_documenti_versioni_html_template_non_vuoto presente'
);
SELECT ok(
  EXISTS (
    SELECT 1 FROM information_schema.table_constraints
    WHERE table_schema = 'documenti'
      AND table_name = 'documenti_generati'
      AND constraint_name = 'chk_documenti_generati_context_json_obj'
      AND constraint_type = 'CHECK'
  ),
  'E4: chk_documenti_generati_context_json_obj presente'
);

-- 16..18) Step C: is_principale + indice parziale + unique nuovo
SELECT ok(
  EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'documenti'
      AND table_name = 'documenti_generati_file'
      AND column_name = 'is_principale'
      AND is_nullable = 'NO'
  ),
  'C: colonna is_principale presente NOT NULL su documenti_generati_file'
);
SELECT ok(
  to_regclass('documenti.uq_documenti_generati_file_principale') IS NOT NULL,
  'C: indice parziale uq_documenti_generati_file_principale presente'
);
SELECT ok(
  EXISTS (
    SELECT 1 FROM information_schema.table_constraints
    WHERE table_schema = 'documenti'
      AND table_name = 'documenti_generati_file'
      AND constraint_name = 'uq_documenti_generati_file_doc_tipo_ord'
      AND constraint_type = 'UNIQUE'
  ),
  'C: vincolo uq_documenti_generati_file_doc_tipo_ord presente'
);

SELECT * FROM finish();
ROLLBACK;
