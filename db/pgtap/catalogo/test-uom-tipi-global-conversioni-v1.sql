-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Schema: catalogo
-- Ambito: tipologie UoM e guard conversioni globali
-- ------------------------------------------------------------

-- Indice test eseguiti:
-- 1) Seed tipo MASSA disponibile
-- 2) Seed tipo LUNGHEZZA disponibile
-- 3) Inserimento UoM test di tipo MASSA e LUNGHEZZA
-- 4) Conversione globale same-type ammessa
-- 5) Conversione globale cross-type bloccata

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
-- ⚠️ Questo file non apre una transazione propria: la riga va prima di plan().
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(5);

CREATE TEMP TABLE tmp_uom_tipo_test AS
SELECT
  to_char(clock_timestamp(), 'YYYYMMDDHH24MISSMS') AS ts,
  COALESCE((SELECT MAX(id) FROM catalogo.unita_misura), 0) + 3001 AS mass_a_id,
  COALESCE((SELECT MAX(id) FROM catalogo.unita_misura), 0) + 3002 AS mass_b_id,
  COALESCE((SELECT MAX(id) FROM catalogo.unita_misura), 0) + 3003 AS len_a_id,
  (SELECT id FROM catalogo.uom_tipi WHERE codice = 'MASSA') AS tipo_massa_id,
  (SELECT id FROM catalogo.uom_tipi WHERE codice = 'LUNGHEZZA') AS tipo_lunghezza_id;

SELECT ok(
  (SELECT tipo_massa_id IS NOT NULL FROM tmp_uom_tipo_test),
  'Seed tipo UoM MASSA disponibile'
);

SELECT ok(
  (SELECT tipo_lunghezza_id IS NOT NULL FROM tmp_uom_tipo_test),
  'Seed tipo UoM LUNGHEZZA disponibile'
);

SELECT lives_ok(
  $$
    INSERT INTO catalogo.unita_misura (
      id, codice, descrizione, descrizione_fattura, tipo_uom_id, attivo
    )
    SELECT mass_a_id, 'TM' || right(ts, 6), 'TEST MASSA A', 'TEST MASSA A', tipo_massa_id, true
      FROM tmp_uom_tipo_test;

    INSERT INTO catalogo.unita_misura (
      id, codice, descrizione, descrizione_fattura, tipo_uom_id, attivo
    )
    SELECT mass_b_id, 'TN' || right(ts, 6), 'TEST MASSA B', 'TEST MASSA B', tipo_massa_id, true
      FROM tmp_uom_tipo_test;

    INSERT INTO catalogo.unita_misura (
      id, codice, descrizione, descrizione_fattura, tipo_uom_id, attivo
    )
    SELECT len_a_id, 'TL' || right(ts, 6), 'TEST LUNGHEZZA', 'TEST LUNGHEZZA', tipo_lunghezza_id, true
      FROM tmp_uom_tipo_test;
  $$,
  'Inserimento UoM test con tipologie esplicite'
);

SELECT lives_ok(
  $$
    INSERT INTO catalogo.unita_misura_conversioni (
      uom_from_id, uom_to_id, fattore, valido_dal, attivo
    )
    SELECT mass_a_id, mass_b_id, 1000, DATE '2026-04-28', true
      FROM tmp_uom_tipo_test;
  $$,
  'Conversione globale tra UoM della stessa tipologia ammessa'
);

SELECT throws_like(
  $$
    INSERT INTO catalogo.unita_misura_conversioni (
      uom_from_id, uom_to_id, fattore, valido_dal, attivo
    )
    SELECT mass_a_id, len_a_id, 2, DATE '2026-04-28', true
      FROM tmp_uom_tipo_test;
  $$,
  '%tipologia diversa%',
  'Conversione globale tra tipologie diverse bloccata'
);
