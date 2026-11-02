-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: lookup documenti — unique codice/codice_interno + lock + seed idempotenti
-- ------------------------------------------------------------
-- Indice test (1..14):
--  1) Seed PREVENTIVO presente in tipi_documento_output
--  2) Seed WEASYPRINT presente in render_engine_documento
--  3) Seed PDF_FINALE presente in tipi_file_documento
--  4) Seed asset base (LOGO, FIRMA, IMMAGINE, PDF, CSS, ALTRO) presente
--  5) Unique codice_interno su tipi_documento_output (duplicato bloccato)
--  6) Unique codice_interno su tipi_asset_documento (duplicato bloccato)
--  7) Unique codice_interno su tipi_file_documento (duplicato bloccato)
--  8) Unique codice_interno su render_engine_documento (duplicato bloccato)
--  9) Lock columns: trigger su tipi_documento_output presente
-- 10) Lock columns: trigger su tipi_asset_documento presente
-- 11) Lock columns: trigger su tipi_file_documento presente
-- 12) Lock columns: trigger su render_engine_documento presente
-- 13) Lock effettivo: UPDATE codice_interno su PREVENTIVO bloccato
-- 14) Codice_interno raw seed coerente con CSV (unicita' applicata su 6 asset)
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

SELECT plan(14);

-- 1..4) Seed presenti
SELECT ok(
  EXISTS (SELECT 1 FROM documenti.tipi_documento_output
          WHERE codice_interno = 'PREVENTIVO'),
  'Seed PREVENTIVO presente in tipi_documento_output'
);
SELECT ok(
  EXISTS (SELECT 1 FROM documenti.render_engine_documento
          WHERE codice_interno = 'WEASYPRINT'),
  'Seed WEASYPRINT presente in render_engine_documento'
);
SELECT ok(
  EXISTS (SELECT 1 FROM documenti.tipi_file_documento
          WHERE codice_interno = 'PDF_FINALE'),
  'Seed PDF_FINALE presente in tipi_file_documento'
);
SELECT is(
  (SELECT count(*)::int
     FROM documenti.tipi_asset_documento
    WHERE codice_interno IN ('LOGO','FIRMA','IMMAGINE','PDF','CSS','ALTRO')),
  6,
  'Seed asset base (LOGO,FIRMA,IMMAGINE,PDF,CSS,ALTRO) presente'
);

-- 5..8) Unique codice_interno: tentativo di insert duplicato deve fallire
SELECT throws_ok(
  $$INSERT INTO documenti.tipi_documento_output(codice, codice_interno, descrizione, attivo)
    VALUES ('PREVENTIVO_DUP', 'PREVENTIVO', 'dup', true)$$,
  '23505',
  NULL,
  'Unique codice_interno su tipi_documento_output (duplicato bloccato)'
);
SELECT throws_ok(
  $$INSERT INTO documenti.tipi_asset_documento(codice, codice_interno, descrizione, attivo)
    VALUES ('LOGO_DUP', 'LOGO', 'dup', true)$$,
  '23505',
  NULL,
  'Unique codice_interno su tipi_asset_documento (duplicato bloccato)'
);
SELECT throws_ok(
  $$INSERT INTO documenti.tipi_file_documento(codice, codice_interno, descrizione, attivo)
    VALUES ('PDF_FINALE_DUP', 'PDF_FINALE', 'dup', true)$$,
  '23505',
  NULL,
  'Unique codice_interno su tipi_file_documento (duplicato bloccato)'
);
SELECT throws_ok(
  $$INSERT INTO documenti.render_engine_documento(codice, codice_interno, descrizione, attivo)
    VALUES ('WEASYPRINT_DUP', 'WEASYPRINT', 'dup', true)$$,
  '23505',
  NULL,
  'Unique codice_interno su render_engine_documento (duplicato bloccato)'
);

-- 9..12) Trigger LOCK_COLUMNS provisionato dall'automazione standard
SELECT ok(
  EXISTS (
    SELECT 1 FROM pg_trigger t
    JOIN pg_class c ON c.oid = t.tgrelid
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'documenti'
      AND c.relname = 'tipi_documento_output'
      AND t.tgname = 'trg_tipi_documento_output_a10_lock_columns_upd'
      AND NOT t.tgisinternal
  ),
  'Lock columns: trigger su tipi_documento_output presente'
);
SELECT ok(
  EXISTS (
    SELECT 1 FROM pg_trigger t
    JOIN pg_class c ON c.oid = t.tgrelid
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'documenti'
      AND c.relname = 'tipi_asset_documento'
      AND t.tgname = 'trg_tipi_asset_documento_a10_lock_columns_upd'
      AND NOT t.tgisinternal
  ),
  'Lock columns: trigger su tipi_asset_documento presente'
);
SELECT ok(
  EXISTS (
    SELECT 1 FROM pg_trigger t
    JOIN pg_class c ON c.oid = t.tgrelid
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'documenti'
      AND c.relname = 'tipi_file_documento'
      AND t.tgname = 'trg_tipi_file_documento_a10_lock_columns_upd'
      AND NOT t.tgisinternal
  ),
  'Lock columns: trigger su tipi_file_documento presente'
);
SELECT ok(
  EXISTS (
    SELECT 1 FROM pg_trigger t
    JOIN pg_class c ON c.oid = t.tgrelid
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'documenti'
      AND c.relname = 'render_engine_documento'
      AND t.tgname = 'trg_render_engine_documento_a10_lock_columns_upd'
      AND NOT t.tgisinternal
  ),
  'Lock columns: trigger su render_engine_documento presente'
);

-- 13) Lock effettivo: tentativo UPDATE codice_interno su seed PREVENTIVO deve fallire
SELECT throws_ok(
  $$UPDATE documenti.tipi_documento_output
       SET codice_interno = 'PREVENTIVO_MOD'
     WHERE codice_interno = 'PREVENTIVO'$$,
  NULL,
  NULL,
  'Lock effettivo: UPDATE codice_interno su PREVENTIVO bloccato'
);

-- 14) Coerenza seed asset: assenza duplicati codice_interno
SELECT is(
  (SELECT count(*)::int FROM (
     SELECT codice_interno
       FROM documenti.tipi_asset_documento
      GROUP BY codice_interno
     HAVING count(*) > 1
   ) dup),
  0,
  'Seed asset documenti: nessun codice_interno duplicato'
);

SELECT * FROM finish();
ROLLBACK;
