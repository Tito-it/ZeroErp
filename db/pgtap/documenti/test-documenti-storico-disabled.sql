-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: verifica disabilitazione storico per documenti_generati(_file) (Step B)
--   - tabelle storico assenti
--   - colonna storicizza assente sulle 2 tabelle (segnale framework)
--   - trigger storico assenti
--   - storico ATTIVO per le altre tabelle del modulo (template, asset, lookup)
-- ------------------------------------------------------------
-- Indice test (1..10):
--  1) Tabella storico.documenti_generati assente
--  2) Tabella storico.documenti_generati_file assente
--  3) Colonna storicizza assente su documenti.documenti_generati
--  4) Colonna storicizza assente su documenti.documenti_generati_file
--  5) Nessun trigger storico su documenti.documenti_generati
--  6) Nessun trigger storico su documenti.documenti_generati_file
--  7) Tabella storico.template_documenti presente (storico attivo)
--  8) Tabella storico.template_documenti_versioni presente (storico attivo)
--  9) Tabella storico.template_asset presente (storico attivo)
-- 10) Tabella storico.tipi_documento_output presente (storico attivo lookup)
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

-- 1..2) Tabelle storico per documenti_generati* assenti
SELECT ok(
  to_regclass('storico.documenti_generati') IS NULL,
  'B: tabella storico.documenti_generati assente'
);
SELECT ok(
  to_regclass('storico.documenti_generati_file') IS NULL,
  'B: tabella storico.documenti_generati_file assente'
);

-- 3..4) Colonna storicizza assente (segnale di disabilitazione)
SELECT ok(
  NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'documenti'
      AND table_name = 'documenti_generati'
      AND column_name = 'storicizza'
  ),
  'B: colonna storicizza assente su documenti.documenti_generati'
);
SELECT ok(
  NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'documenti'
      AND table_name = 'documenti_generati_file'
      AND column_name = 'storicizza'
  ),
  'B: colonna storicizza assente su documenti.documenti_generati_file'
);

-- 5..6) Nessun trigger storico (per nome o per funzione storico_generic)
SELECT ok(
  NOT EXISTS (
    SELECT 1 FROM pg_trigger t
    JOIN pg_class c ON c.oid = t.tgrelid
    JOIN pg_namespace n ON n.oid = c.relnamespace
    JOIN pg_proc p ON p.oid = t.tgfoid
    WHERE n.nspname = 'documenti'
      AND c.relname = 'documenti_generati'
      AND p.proname IN ('trgfn_storico_generic', 'trgfn_upd_dlt_storico_generic')
      AND NOT t.tgisinternal
  ),
  'B: nessun trigger storico su documenti.documenti_generati'
);
SELECT ok(
  NOT EXISTS (
    SELECT 1 FROM pg_trigger t
    JOIN pg_class c ON c.oid = t.tgrelid
    JOIN pg_namespace n ON n.oid = c.relnamespace
    JOIN pg_proc p ON p.oid = t.tgfoid
    WHERE n.nspname = 'documenti'
      AND c.relname = 'documenti_generati_file'
      AND p.proname IN ('trgfn_storico_generic', 'trgfn_upd_dlt_storico_generic')
      AND NOT t.tgisinternal
  ),
  'B: nessun trigger storico su documenti.documenti_generati_file'
);

-- 7..10) Storico ATTIVO per le altre tabelle (template, asset, lookup)
SELECT ok(
  to_regclass('storico.template_documenti') IS NOT NULL,
  'B: tabella storico.template_documenti presente (storico attivo)'
);
SELECT ok(
  to_regclass('storico.template_documenti_versioni') IS NOT NULL,
  'B: tabella storico.template_documenti_versioni presente (storico attivo)'
);
SELECT ok(
  to_regclass('storico.template_asset') IS NOT NULL,
  'B: tabella storico.template_asset presente (storico attivo)'
);
SELECT ok(
  to_regclass('storico.tipi_documento_output') IS NOT NULL,
  'B: tabella storico.tipi_documento_output presente (storico attivo lookup)'
);

SELECT * FROM finish();
ROLLBACK;
