-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Copyright (C) 2026 Tid (Michele Carlo Titini)
--
-- Rilasciato sotto GNU AGPLv3 o versione successiva.
-- Vedi LICENSE.md per il testo completo della licenza.
-- ------------------------------------------------------------
-- Test: il catalogo dei regimi fiscali e' in SOLA LETTURA per l'applicazione
--   (D-8, Tid 2026-11-22, brief-db-fornitore-doppioni-del-soggetto §7.4: la
--   Q10 del 2026-11-14 applicata). Lo scrive il mirror del CSV, cioe' il
--   migratore. La sola porta dell'app e' il builder dei regimi di prova (D-9).
--   ChangeSet: 90_end/20261121-16, 20_code/dbops/20261121-17.
--
-- Elenco test (plan 6):
--   La sola lettura
--   1) all'applicazione SELECT si', INSERT, UPDATE e DELETE no
--   2) come applicazione, un UPDATE risponde 42501
--   3) come applicazione, un INSERT risponde 42501
--   Il builder dei regimi di prova, come applicazione, in SVILUPPO
--   4) crea un regime spento, col segno di prova in meta
--   5) un codice_interno del catalogo: uq_regimi_fiscali_codice_interno
--   6) un codice del catalogo: uq_regimi_fiscali_codice
--
-- Scopo:
--  - 1 e' la terza sede della postura (linee-guida-sql §11.8): il forward
--    90_end/20261121-16, il loop 90_end/ci_apply/20260205-41 e il blocco
--    «POSTURA DICHIARATA» di scripts/sql/provision_zeroerp.sql devono dire la
--    stessa cosa, e su un database ricostruito da zero lo dice solo questo test.
--  - ⚠️ Gira come l'APPLICAZIONE (runner di default): 2 e 3 sono veri solo li'.
--  - ⚠️ 2 e 3 nominano colonne che esistono (id, codice_interno): su una colonna
--    assente il parser risponderebbe 42703, rosso per il motivo sbagliato.
--  - ⭐ 4-6 girano in SVILUPPO, l'ambiente della CI (provisioning fase post,
--    ambiente=SVILUPPO): il ramo PRODUZIONE del builder lo costruisce
--    db/pgtap/dbops/test-etichette-di-prova-v1.sql, che riscrive l'ambiente
--    come owner. I regimi del test (RF95, RF94) li costruisce il test; RF01
--    e' del seed di 80_data, cioe' del contratto.
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(6);

-- 1
SELECT is(
  (SELECT string_agg(p, ', ' ORDER BY p)
     FROM unnest(ARRAY['SELECT', 'INSERT', 'UPDATE', 'DELETE']) p
    WHERE has_table_privilege('zeroerp_app', 'config.regimi_fiscali', p) IS DISTINCT FROM (p = 'SELECT')),
  NULL,
  '1) config.regimi_fiscali: all''applicazione solo SELECT');

-- 2
SELECT throws_ok(
  $$UPDATE config.regimi_fiscali SET id = id WHERE false$$,
  '42501',
  NULL,
  '2) come applicazione, un UPDATE dei regimi risponde 42501');

-- 3
SELECT throws_ok(
  $$INSERT INTO config.regimi_fiscali (codice_interno) SELECT 'RF99' WHERE false$$,
  '42501',
  NULL,
  '3) come applicazione, un INSERT nei regimi risponde 42501');

-- 4
-- ⚠️ Il builder si chiama UNA volta, in una tabella: in un WHERE una funzione
--   VOLATILE girerebbe per ogni riga del catalogo.
CREATE TEMP TABLE _rf ON COMMIT DROP AS
SELECT dbops.fn_crea_regime_fiscale_di_prova('RF95', 'PGTAP-RF95', 'Regime di prova spento', false) AS id;

SELECT is(
  (SELECT string_agg(format('%s|%s', r.attivo::text, r.meta ->> 'di_prova'), ',')
     FROM config.regimi_fiscali r JOIN _rf ON _rf.id = r.id),
  'false|true',
  '4) come applicazione, il builder crea un regime spento, col segno di prova in meta');

-- 5
SELECT is(
  dbops.fn_pgtap_codice_errore(
    $$SELECT dbops.fn_crea_regime_fiscale_di_prova('RF01', 'PGTAP-RF01', 'Doppione del catalogo', true)$$),
  'uq_regimi_fiscali_codice_interno',
  '5) un codice_interno del catalogo non si riscrive: uq_regimi_fiscali_codice_interno');

-- 6
SELECT is(
  dbops.fn_pgtap_codice_errore(format(
    $$SELECT dbops.fn_crea_regime_fiscale_di_prova('RF94', %L, 'Doppione del codice', true)$$,
    COALESCE((SELECT r.codice FROM config.regimi_fiscali r WHERE r.codice_interno = 'RF01'), '<RF01 assente dal seed>'))),
  'uq_regimi_fiscali_codice',
  '6) un codice del catalogo non si riusa: uq_regimi_fiscali_codice');

SELECT * FROM finish();
ROLLBACK;
