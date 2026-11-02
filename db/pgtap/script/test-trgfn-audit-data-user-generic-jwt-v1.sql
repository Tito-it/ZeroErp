-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: trgfn_audit_data_user_generic con JWT (app.jwt_user)
-- (changeset 20260227-07, 20260227-08)
-- ------------------------------------------------------------
-- Indice test (1..10):
--  1) Funzione trigger presente
--  2) Trigger migrato a BEFORE INSERT OR UPDATE
--  3) INSERT senza JWT: user_insert = CURRENT_USER
--  4) INSERT senza JWT: user_update = CURRENT_USER
--  5) INSERT con JWT: user_insert = JWT user
--  6) INSERT con JWT: user_update = JWT user
--  7) UPDATE con JWT: user_update = JWT user
--  8) UPDATE con JWT: user_insert invariato (non sovrascritto)
--  9) JWT stringa vuota: fallback a CURRENT_USER
-- 10) Reset JWT: fallback a CURRENT_USER
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
-- TEST 1: Funzione trigger presente
-- ============================================================

SELECT ok(
  EXISTS (
    SELECT 1 FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'script'
      AND p.proname = 'trgfn_audit_data_user_generic'
  ),
  'Funzione trigger presente'
);

-- ============================================================
-- TEST 2: Trigger migrato a BEFORE INSERT OR UPDATE
-- ============================================================

SELECT ok(
  EXISTS (
    SELECT 1 FROM pg_trigger t
    JOIN pg_class c ON c.oid = t.tgrelid
    JOIN pg_namespace n ON n.oid = c.relnamespace
    JOIN pg_proc p ON p.oid = t.tgfoid
    JOIN pg_namespace pn ON pn.oid = p.pronamespace
    WHERE pn.nspname = 'script'
      AND p.proname = 'trgfn_audit_data_user_generic'
      AND n.nspname = 'config'
      AND c.relname = 'unita_organizzative'
      -- tgtype bit: BEFORE=2, ROW=1, INSERT=4, UPDATE=16 → 2+1+4+16 = 23
      AND t.tgtype = 23
  ),
  'Trigger migrato a BEFORE INSERT OR UPDATE su unita_organizzative'
);

-- ============================================================
-- SETUP: codice univoco per test
-- ============================================================

CREATE TEMP TABLE tmp_audit_test AS
SELECT
  'PGTAP-AUDIT-' || substr(md5(clock_timestamp()::text), 1, 8) AS codice_test;

-- ============================================================
-- TEST 3-4: INSERT senza JWT → fallback CURRENT_USER
-- ============================================================

-- Assicura che la GUC non sia impostata
SELECT set_config('app.jwt_user', '', true);

INSERT INTO config.unita_organizzative (codice, codice_interno, descrizione)
VALUES (
  (SELECT codice_test FROM tmp_audit_test),
  (SELECT codice_test FROM tmp_audit_test),
  'Test audit JWT pgTAP'
);

SELECT is(
  (
    SELECT user_insert FROM config.unita_organizzative
    WHERE codice = (SELECT codice_test FROM tmp_audit_test)
  ),
  CURRENT_USER::text,
  'INSERT senza JWT: user_insert = CURRENT_USER'
);

SELECT is(
  (
    SELECT user_update FROM config.unita_organizzative
    WHERE codice = (SELECT codice_test FROM tmp_audit_test)
  ),
  CURRENT_USER::text,
  'INSERT senza JWT: user_update = CURRENT_USER'
);

-- ============================================================
-- TEST 5-6: INSERT con JWT → usa JWT user
-- ============================================================

SELECT set_config('app.jwt_user', 'test.jwt@pgtap.zero', true);

DELETE FROM config.unita_organizzative
WHERE codice = (SELECT codice_test FROM tmp_audit_test);

INSERT INTO config.unita_organizzative (codice, codice_interno, descrizione)
VALUES (
  (SELECT codice_test FROM tmp_audit_test),
  (SELECT codice_test FROM tmp_audit_test),
  'Test audit JWT pgTAP - con JWT'
);

SELECT is(
  (
    SELECT user_insert FROM config.unita_organizzative
    WHERE codice = (SELECT codice_test FROM tmp_audit_test)
  ),
  'test.jwt@pgtap.zero',
  'INSERT con JWT: user_insert = JWT user'
);

SELECT is(
  (
    SELECT user_update FROM config.unita_organizzative
    WHERE codice = (SELECT codice_test FROM tmp_audit_test)
  ),
  'test.jwt@pgtap.zero',
  'INSERT con JWT: user_update = JWT user'
);

-- ============================================================
-- TEST 7-8: UPDATE con JWT → user_update aggiornato, user_insert invariato
-- ============================================================

SELECT set_config('app.jwt_user', 'altro.utente@pgtap.zero', true);

UPDATE config.unita_organizzative
SET descrizione = 'Test audit JWT pgTAP - updated'
WHERE codice = (SELECT codice_test FROM tmp_audit_test);

SELECT is(
  (
    SELECT user_update FROM config.unita_organizzative
    WHERE codice = (SELECT codice_test FROM tmp_audit_test)
  ),
  'altro.utente@pgtap.zero',
  'UPDATE con JWT: user_update = JWT user'
);

SELECT is(
  (
    SELECT user_insert FROM config.unita_organizzative
    WHERE codice = (SELECT codice_test FROM tmp_audit_test)
  ),
  'test.jwt@pgtap.zero',
  'UPDATE con JWT: user_insert invariato (non sovrascritto)'
);

-- ============================================================
-- TEST 9: JWT stringa vuota → fallback CURRENT_USER
-- ============================================================

SELECT set_config('app.jwt_user', '', true);

UPDATE config.unita_organizzative
SET descrizione = 'Test audit JWT pgTAP - empty jwt'
WHERE codice = (SELECT codice_test FROM tmp_audit_test);

SELECT is(
  (
    SELECT user_update FROM config.unita_organizzative
    WHERE codice = (SELECT codice_test FROM tmp_audit_test)
  ),
  CURRENT_USER::text,
  'JWT stringa vuota: fallback a CURRENT_USER'
);

-- ============================================================
-- TEST 10: Reset JWT (NULL) → fallback CURRENT_USER
-- ============================================================

RESET app.jwt_user;

UPDATE config.unita_organizzative
SET descrizione = 'Test audit JWT pgTAP - reset jwt'
WHERE codice = (SELECT codice_test FROM tmp_audit_test);

SELECT is(
  (
    SELECT user_update FROM config.unita_organizzative
    WHERE codice = (SELECT codice_test FROM tmp_audit_test)
  ),
  CURRENT_USER::text,
  'Reset JWT: fallback a CURRENT_USER'
);

SELECT * FROM finish();
ROLLBACK;
