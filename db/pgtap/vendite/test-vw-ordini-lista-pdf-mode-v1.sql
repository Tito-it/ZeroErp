-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: vendite.vw_ordini_lista — colonna pdf_mode (azione PDF per-riga)
-- ------------------------------------------------------------
-- Indice test (1..4):
--  1) la vista espone la colonna pdf_mode
--  2) pdf_mode e' character varying (tipo dello stato)
--  3) security_invoker=on preservato (nessun buco di scope RLS)
--  4) coerenza col seed: per OGNI riga v.pdf_mode == pdf_mode dello stato
--     corrispondente (wiring JOIN corretto) — fixture-free
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

SELECT plan(4);

-- 1) colonna presente
SELECT has_column('vendite', 'vw_ordini_lista', 'pdf_mode',
  '1) vw_ordini_lista espone pdf_mode');

-- 2) tipo = character varying
SELECT is(
  (SELECT data_type FROM information_schema.columns
    WHERE table_schema='vendite' AND table_name='vw_ordini_lista' AND column_name='pdf_mode'),
  'character varying',
  '2) pdf_mode e'' character varying');

-- 3) security_invoker=on preservato dal CREATE OR REPLACE
SELECT ok(
  (SELECT array_to_string(c.reloptions, ',') LIKE '%security_invoker=on%'
       OR array_to_string(c.reloptions, ',') LIKE '%security_invoker=true%'
     FROM pg_class c
     JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname='vendite' AND c.relname='vw_ordini_lista'),
  '3) security_invoker=on preservato (no regressione scope RLS)');

-- 4) coerenza col seed: nessuna riga con pdf_mode diverso da quello dello
--    stato (JOIN per codice_interno, 1:1). Vista vuota -> 0 mismatch -> pass.
SELECT is(
  (SELECT count(*)::int
     FROM vendite.vw_ordini_lista v
     JOIN config.stati_doc_ordini sd ON sd.codice_interno = v.stato_codice_interno
    WHERE v.pdf_mode IS DISTINCT FROM sd.pdf_mode),
  0,
  '4) v.pdf_mode coerente con stati_doc_ordini.pdf_mode per ogni riga');

SELECT * FROM finish();
ROLLBACK;
