-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: DDL vendite.commesse_push_log (changeset 20260224-39)
-- ------------------------------------------------------------
-- Indice test (1..8):
-- 1) tabella commesse_push_log presente
-- 2) colonna run_at presente
-- 3) colonna risultato presente
-- 4) vincolo check stato presente
-- 5) vincolo check durata_ms presente
-- 6) indice ix_commesse_push_log_run_at presente
-- 7) stato invalido bloccato
-- 8) insert valido consentito
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

SELECT ok(
  to_regclass('vendite.commesse_push_log') IS NOT NULL,
  'tabella commesse_push_log presente'
);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM information_schema.columns c
    WHERE c.table_schema = 'vendite'
      AND c.table_name = 'commesse_push_log'
      AND c.column_name = 'run_at'
  ),
  'colonna run_at presente'
);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM information_schema.columns c
    WHERE c.table_schema = 'vendite'
      AND c.table_name = 'commesse_push_log'
      AND c.column_name = 'risultato'
  ),
  'colonna risultato presente'
);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
    WHERE nsp.nspname = 'vendite'
      AND rel.relname = 'commesse_push_log'
      AND con.conname = 'chk_commesse_push_log_stato'
  ),
  'vincolo check stato presente'
);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
    WHERE nsp.nspname = 'vendite'
      AND rel.relname = 'commesse_push_log'
      AND con.conname = 'chk_commesse_push_log_durata_ms'
  ),
  'vincolo check durata_ms presente'
);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM pg_indexes i
    WHERE i.schemaname = 'vendite'
      AND i.tablename = 'commesse_push_log'
      AND i.indexname = 'ix_commesse_push_log_run_at'
  ),
  'indice ix_commesse_push_log_run_at presente'
);

SELECT throws_ok(
  $$
    INSERT INTO vendite.commesse_push_log (stato, dry_run)
    VALUES ('KO', false);
  $$,
  '23514',
  NULL,
  'stato invalido bloccato'
);

WITH ins AS (
  INSERT INTO vendite.commesse_push_log (
    dry_run,
    source_types,
    risultato,
    stato,
    durata_ms
  )
  VALUES (
    true,
    ARRAY['HandlerPreventivi', 'HandlerOrdini'],
    jsonb_build_object('HandlerPreventivi', jsonb_build_object('created', 2, 'errors', '[]'::jsonb)),
    'COMPLETATO',
    1200
  )
  RETURNING id
)
SELECT ok(
  EXISTS (SELECT 1 FROM ins),
  'insert valido consentito'
);

SELECT * FROM finish();
ROLLBACK;
