-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: param VENDITE_DASHBOARD_RITARDO_DATA_MINIMA presente nel seed e
--       leggibile come data ISO (seed parameters_vendite_defaults, id 60)
-- Brief: brief-db-parametro-data-minima-ritardo-dashboard (R-1)
-- ------------------------------------------------------------
-- Indice test (1..3):
--  1) VENDITE_DASHBOARD_RITARDO_DATA_MINIMA presente con default_value = '2020-01-01'
--  2) default_value e' nella forma ISO YYYY-MM-DD (quella che il BE legge)
--  3) default_value e' una data valida (il cast non solleva)
--
-- ℹ️ Nessun guard DB valida il formato del valore: lo valida il lettore
--    (vendite_service). 2) e 3) presidiano il SEED, non un guard: un valore
--    non ISO nel CSV sarebbe un 500 alla prima richiesta della dashboard, e la
--    CI e' il posto in cui si vede prima.
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

SELECT plan(3);

-- 1) Il parametro c'e' col valore deciso da Tid (2026-10-08).
SELECT is(
  (SELECT default_value FROM config.parameters
    WHERE code = 'VENDITE_DASHBOARD_RITARDO_DATA_MINIMA'),
  '2020-01-01',
  '1) VENDITE_DASHBOARD_RITARDO_DATA_MINIMA presente con default_value = 2020-01-01'
);

-- 2) Forma ISO: e' il contratto con il BE, che la legge come data.
SELECT ok(
  (SELECT default_value ~ '^\d{4}-\d{2}-\d{2}$' FROM config.parameters
    WHERE code = 'VENDITE_DASHBOARD_RITARDO_DATA_MINIMA'),
  '2) default_value nella forma ISO YYYY-MM-DD'
);

-- 3) La forma non basta (2020-02-30 la rispetta): il valore dev'essere una data.
SELECT lives_ok(
  $$SELECT default_value::date FROM config.parameters
     WHERE code = 'VENDITE_DASHBOARD_RITARDO_DATA_MINIMA'$$,
  '3) default_value e'' una data valida'
);

SELECT * FROM finish();

ROLLBACK;
