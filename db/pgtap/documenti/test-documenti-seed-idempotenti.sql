-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: idempotenza seed lookup documenti + parametri storage
-- ------------------------------------------------------------
-- Indice test (1..10):
--  1) Conteggio righe lookup tipi_documento_output >= 1 (PREVENTIVO seed)
--  2) Conteggio righe lookup render_engine_documento >= 1 (WEASYPRINT seed)
--  3) Conteggio righe lookup tipi_file_documento >= 1 (PDF_FINALE seed)
--  4) Conteggio righe lookup tipi_asset_documento >= 6 (LOGO,FIRMA,...)
--  5) Nessun duplicato di codice_interno su tipi_documento_output
--  6) Nessun duplicato di codice_interno su render_engine_documento
--  7) Nessun duplicato di codice_interno su tipi_file_documento
--  8) Nessun duplicato di codice_interno su tipi_asset_documento
--  9) Parametri storage documenti caricati in config.parameters (>= 8)
-- 10) Nessun duplicato di code per parametri documenti_*
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

-- 1..4) Seed presenti in numero atteso
SELECT cmp_ok(
  (SELECT COUNT(*) FROM documenti.tipi_documento_output)::int,
  '>=', 1,
  'Seed tipi_documento_output: almeno 1 riga (PREVENTIVO)'
);
SELECT cmp_ok(
  (SELECT COUNT(*) FROM documenti.render_engine_documento)::int,
  '>=', 1,
  'Seed render_engine_documento: almeno 1 riga (WEASYPRINT)'
);
SELECT cmp_ok(
  (SELECT COUNT(*) FROM documenti.tipi_file_documento)::int,
  '>=', 1,
  'Seed tipi_file_documento: almeno 1 riga (PDF_FINALE)'
);
SELECT cmp_ok(
  (SELECT COUNT(*) FROM documenti.tipi_asset_documento)::int,
  '>=', 6,
  'Seed tipi_asset_documento: 6 righe attese (LOGO,FIRMA,IMMAGINE,PDF,CSS,ALTRO)'
);

-- 5..8) Idempotenza seed: nessun duplicato codice_interno
SELECT is(
  (SELECT COUNT(*)::int FROM (
     SELECT codice_interno FROM documenti.tipi_documento_output
      GROUP BY codice_interno HAVING COUNT(*) > 1
   ) d),
  0,
  'Idempotenza tipi_documento_output: nessun codice_interno duplicato'
);
SELECT is(
  (SELECT COUNT(*)::int FROM (
     SELECT codice_interno FROM documenti.render_engine_documento
      GROUP BY codice_interno HAVING COUNT(*) > 1
   ) d),
  0,
  'Idempotenza render_engine_documento: nessun codice_interno duplicato'
);
SELECT is(
  (SELECT COUNT(*)::int FROM (
     SELECT codice_interno FROM documenti.tipi_file_documento
      GROUP BY codice_interno HAVING COUNT(*) > 1
   ) d),
  0,
  'Idempotenza tipi_file_documento: nessun codice_interno duplicato'
);
SELECT is(
  (SELECT COUNT(*)::int FROM (
     SELECT codice_interno FROM documenti.tipi_asset_documento
      GROUP BY codice_interno HAVING COUNT(*) > 1
   ) d),
  0,
  'Idempotenza tipi_asset_documento: nessun codice_interno duplicato'
);

-- 9..10) Parametri storage in config.parameters
SELECT cmp_ok(
  (SELECT COUNT(*) FROM config.parameters
    WHERE code LIKE 'documenti_%')::int,
  '>=', 8,
  'Seed parametri storage documenti_*: almeno 8 (storage_provider/endpoint/...)'
);
SELECT is(
  (SELECT COUNT(*)::int FROM (
     SELECT code FROM config.parameters
      WHERE code LIKE 'documenti_%'
      GROUP BY code HAVING COUNT(*) > 1
   ) d),
  0,
  'Idempotenza parametri documenti_*: nessun code duplicato'
);

SELECT * FROM finish();
ROLLBACK;
