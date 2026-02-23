-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: vendite.fn_list_attivita_sorgenti_abilitate (changeset 20260223-04)
-- ------------------------------------------------------------
-- Indice test (1..6):
-- 1) Funzione fn_list_attivita_sorgenti_abilitate presente
-- 2) Esistono sorgenti abilitate+attive in policy
-- 3) Conteggio funzione = conteggio tabella policy attiva/abilitata
-- 4) Nessuna riga funzione con abilitata=false
-- 5) Nessuna riga funzione con block_scope non valido
-- 6) Chiamata con utility_id NULL valida
-- ------------------------------------------------------------

BEGIN;
SELECT plan(6);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite'
      AND p.proname = 'fn_list_attivita_sorgenti_abilitate'
  ),
  'Funzione fn_list_attivita_sorgenti_abilitate presente'
);

SELECT ok(
  (
    SELECT COUNT(*)
    FROM vendite.attivita_fatturabili_sorgenti_branch_policy
    WHERE attivo IS TRUE
      AND abilitata IS TRUE
  ) > 0,
  'Esistono sorgenti abilitate+attive in policy'
);

SELECT is(
  (
    SELECT COUNT(*)
    FROM vendite.fn_list_attivita_sorgenti_abilitate(NULL)
  ),
  (
    SELECT COUNT(*)
    FROM vendite.attivita_fatturabili_sorgenti_branch_policy
    WHERE attivo IS TRUE
      AND abilitata IS TRUE
  )::bigint,
  'Conteggio funzione = conteggio tabella policy attiva/abilitata'
);

SELECT is(
  (
    SELECT COUNT(*)
    FROM vendite.fn_list_attivita_sorgenti_abilitate(NULL)
    WHERE abilitata IS FALSE
  ),
  0::bigint,
  'Nessuna riga funzione con abilitata=false'
);

SELECT is(
  (
    SELECT COUNT(*)
    FROM vendite.fn_list_attivita_sorgenti_abilitate(NULL)
    WHERE block_scope NOT IN ('BRANCH', 'GLOBAL')
  ),
  0::bigint,
  'Nessuna riga funzione con block_scope non valido'
);

SELECT lives_ok(
  $$ SELECT COUNT(*) FROM vendite.fn_list_attivita_sorgenti_abilitate(NULL); $$,
  'Chiamata con utility_id NULL valida'
);

SELECT * FROM finish();
ROLLBACK;

