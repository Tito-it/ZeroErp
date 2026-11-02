-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Elenco test (plan 8):
--  1) Trigger trgfn_tipi_ruoli_guard_entita_ref esiste
--  2) Trigger trg_tipi_ruoli_a10_guard_entita_ref_ins_upd esiste
--  3) Guard: entita_colonna_codice NOT NULL con entita_tabella NULL lancia errore
--  4) Guard: entita_tabella inesistente lancia errore
--  5) Guard: entita_tabella senza soggetto_ruolo_id lancia errore
--  6) Guard: colonna codice inesistente lancia errore
--  7) Valori correnti di entita_tabella superano la validazione (coerenza dati)
--  8) Vista vw_clienti_codice_ba ha colonne soggetto_ruolo_id e codice
-- ------------------------------------------------------------

-- ⚠️ Transazione, e non e' una formalita'. Il cleanup di questo file sta in
--   coda: col runner vero (pg_prove gira con ON_ERROR_STOP) un fallimento a
--   meta' non ci arriva mai, e i dati di prova restano nel database a rompere
--   la corsa successiva — che vede un rosso non suo.
--   Brief: brief-db-pgtap-runner-rls-baseline §15.3.
BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file diventerebbe verde per sottrazione. Nel DB ce ne sono 365.
--   IMMEDIATE li riporta a scattare a fine di OGNI istruzione — cioe' esatta-
--   mente come si comportavano prima, quando il file girava in autocommit e
--   ogni istruzione era una transazione a se'. In testa e non in coda apposta:
--   in coda scatterebbero tutti insieme DOPO il cleanup, su righe ormai
--   cancellate. Brief: brief-db-pgtap-runner-rls-baseline §17.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(8);

-- ID del primo tipo ruolo per i test di guard
CREATE TEMP TABLE tmp_tr AS
SELECT id FROM config.tipi_ruoli ORDER BY id LIMIT 1;

-- =========================================================
-- Test 1-2: Esistenza funzione e trigger
-- =========================================================

-- 1) Funzione trigger esiste
SELECT has_function(
  'config',
  'trgfn_tipi_ruoli_guard_entita_ref',
  'Funzione trgfn_tipi_ruoli_guard_entita_ref esiste nello schema config'
);

-- 2) Trigger esiste su tipi_ruoli
SELECT has_trigger(
  'config',
  'tipi_ruoli',
  'trg_tipi_ruoli_a10_guard_entita_ref_ins_upd',
  'Trigger guard entita_ref esiste su config.tipi_ruoli'
);

-- =========================================================
-- Test 3: Guard coerenza NULL
-- =========================================================

-- entita_colonna_codice NOT NULL con entita_tabella NULL
SELECT throws_ok(
  format(
    $$UPDATE config.tipi_ruoli SET entita_tabella = NULL, entita_colonna_codice = 'codice' WHERE id = %s$$,
    (SELECT id FROM tmp_tr)
  ),
  'P0001',
  NULL,
  'Guard: entita_colonna_codice NOT NULL con entita_tabella NULL lancia errore'
);

-- =========================================================
-- Test 4: Guard tabella inesistente
-- =========================================================

SELECT throws_ok(
  format(
    $$UPDATE config.tipi_ruoli SET entita_tabella = 'schema_falso.tabella_falsa', entita_colonna_codice = NULL WHERE id = %s$$,
    (SELECT id FROM tmp_tr)
  ),
  'P0001',
  NULL,
  'Guard: entita_tabella inesistente lancia errore'
);

-- =========================================================
-- Test 5: Guard tabella senza soggetto_ruolo_id
-- =========================================================

-- config.tipi_ruoli esiste ma non ha soggetto_ruolo_id
SELECT throws_ok(
  format(
    $$UPDATE config.tipi_ruoli SET entita_tabella = 'config.tipi_ruoli', entita_colonna_codice = NULL WHERE id = %s$$,
    (SELECT id FROM tmp_tr)
  ),
  'P0001',
  NULL,
  'Guard: entita_tabella senza soggetto_ruolo_id lancia errore'
);

-- =========================================================
-- Test 6: Guard colonna codice inesistente
-- =========================================================

-- anagrafiche.fornitori esiste e ha soggetto_ruolo_id, ma non ha 'colonna_falsa'
SELECT throws_ok(
  format(
    $$UPDATE config.tipi_ruoli SET entita_tabella = 'anagrafiche.fornitori', entita_colonna_codice = 'colonna_falsa' WHERE id = %s$$,
    (SELECT id FROM tmp_tr)
  ),
  'P0001',
  NULL,
  'Guard: colonna codice inesistente lancia errore'
);

-- =========================================================
-- Test 7: Dati correnti sono coerenti
-- =========================================================

-- Tutti i tipi ruolo con entita_tabella NOT NULL devono avere
-- passato la validazione del trigger (regclass valido)
SELECT ok(
  COALESCE(
    (
      SELECT bool_and(to_regclass(entita_tabella) IS NOT NULL)
      FROM config.tipi_ruoli
      WHERE entita_tabella IS NOT NULL
    ),
    true
  ),
  'Valori correnti di entita_tabella sono tutti regclass validi'
);

-- =========================================================
-- Test 8: Vista vw_clienti_codice_ba ha le colonne attese
-- =========================================================

SELECT ok(
  (
    SELECT count(*) = 2
    FROM pg_catalog.pg_attribute a
    WHERE a.attrelid = 'anagrafiche.vw_clienti_codice_ba'::regclass
      AND a.attname IN ('soggetto_ruolo_id', 'codice')
      AND a.attnum > 0
      AND NOT a.attisdropped
  ),
  'Vista vw_clienti_codice_ba ha colonne soggetto_ruolo_id e codice'
);

SELECT * FROM finish();

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia nulla dietro di se'. Le DELETE del cleanup restano
-- perche' dove sono un'asserzione devono girare davvero.
ROLLBACK;
