-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: il seed dei vocabolari di documenti e dei parametri dello storage
-- ------------------------------------------------------------
-- Il seed di 80_data e' parte del progetto: le righe che porta si asseriscono
-- per intero, non contandole. Un valore che manca, o uno in piu' che nessun
-- changeSet ha scritto, fa rosso. L'unicita' si asserisce dove e' scritta, nel
-- vincolo: contare i duplicati di una colonna gia' UNIQUE non prova niente.
--
-- Indice test (1..10):
--  1) tipi_documento_output: i sei documenti di vendita
--  2) render_engine_documento: WEASYPRINT
--  3) tipi_file_documento: PDF_FINALE e ALLEGATO
--  4) tipi_asset_documento: LOGO, FIRMA, IMMAGINE, PDF, CSS
--  5-8) codice_interno dei quattro vocabolari e' UNIQUE (vincolo)
--  9) config.parameters: i nove parametri documenti_*
-- 10) config.parameters.code e' UNIQUE (vincolo)
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

-- 1..4) Il seed dei quattro vocabolari, per intero
SELECT set_eq(
  $$SELECT codice_interno::text FROM documenti.tipi_documento_output$$,
  ARRAY['PREVENTIVO', 'CONTRATTO', 'OFFERTA_COMMERCIALE', 'ORDINE_VENDITA', 'DDT_VENDITA',
        'FATTURA_VENDITA'],
  '1) tipi_documento_output: i sei documenti di vendita'
);
SELECT set_eq(
  $$SELECT codice_interno::text FROM documenti.render_engine_documento$$,
  ARRAY['WEASYPRINT'],
  '2) render_engine_documento: WEASYPRINT'
);
SELECT set_eq(
  $$SELECT codice_interno::text FROM documenti.tipi_file_documento$$,
  ARRAY['PDF_FINALE', 'ALLEGATO'],
  '3) tipi_file_documento: PDF_FINALE e ALLEGATO'
);
SELECT set_eq(
  $$SELECT codice_interno::text FROM documenti.tipi_asset_documento$$,
  ARRAY['LOGO', 'FIRMA', 'IMMAGINE', 'PDF', 'CSS'],
  '4) tipi_asset_documento: LOGO, FIRMA, IMMAGINE, PDF, CSS'
);

-- 5..8) L'unicita' del codice interno e' un vincolo
SELECT col_is_unique('documenti', 'tipi_documento_output',   'codice_interno', '5) tipi_documento_output.codice_interno e'' UNIQUE');
SELECT col_is_unique('documenti', 'render_engine_documento', 'codice_interno', '6) render_engine_documento.codice_interno e'' UNIQUE');
SELECT col_is_unique('documenti', 'tipi_file_documento',     'codice_interno', '7) tipi_file_documento.codice_interno e'' UNIQUE');
SELECT col_is_unique('documenti', 'tipi_asset_documento',    'codice_interno', '8) tipi_asset_documento.codice_interno e'' UNIQUE');

-- 9..10) I parametri dello storage dei documenti
SELECT set_eq(
  $$SELECT code::text FROM config.parameters WHERE code LIKE 'documenti\_%'$$,
  ARRAY['documenti_storage_provider', 'documenti_storage_endpoint', 'documenti_storage_base_url',
        'documenti_storage_bucket', 'documenti_storage_prefix', 'documenti_storage_secret_ref',
        'documenti_asset_upload_max_mb', 'documenti_pdf_generato_max_mb',
        'documenti_allegato_upload_max_mb'],
  '9) config.parameters: i nove parametri documenti_*'
);
SELECT col_is_unique('config', 'parameters', 'code', '10) config.parameters.code e'' UNIQUE');

SELECT * FROM finish();
ROLLBACK;
