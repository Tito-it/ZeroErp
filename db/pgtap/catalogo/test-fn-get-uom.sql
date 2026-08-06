-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Funzioni: catalogo.fn_get_uom_base, catalogo.fn_get_uom_factor
-- ------------------------------------------------------------

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
-- ⚠️ Questo file non apre una transazione propria: la riga va prima di plan().
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(9);

CREATE TEMP TABLE tmp_seed AS
SELECT
  (SELECT id FROM catalogo.articoli WHERE codice = 'ART_TEST_BASE')     AS art_base_id,
  (SELECT id FROM catalogo.articoli WHERE codice = 'ART_TEST_FALLBACK') AS art_fallback_id;

SELECT ok(
  (SELECT art_base_id IS NOT NULL FROM tmp_seed),
  'Seed articolo base presente'
);

SELECT ok(
  (SELECT art_fallback_id IS NOT NULL FROM tmp_seed),
  'Seed articolo fallback presente'
);

SELECT is(
  catalogo.fn_get_uom_base((SELECT art_base_id FROM tmp_seed)),
  1::bigint,
  'UoM base articolo base'
);

SELECT is(
  catalogo.fn_get_uom_base((SELECT art_fallback_id FROM tmp_seed)),
  14::bigint,
  'UoM base articolo fallback'
);

SELECT is(
  catalogo.fn_get_uom_factor((SELECT art_base_id FROM tmp_seed), 1),
  1::numeric,
  'Fattore base = 1'
);

SELECT is(
  catalogo.fn_get_uom_factor((SELECT art_base_id FROM tmp_seed), 2),
  6::numeric,
  'Fattore da articoli_uom_operativa'
);

SELECT is(
  catalogo.fn_get_uom_factor((SELECT art_fallback_id FROM tmp_seed), 15),
  2::numeric,
  'Fallback conversione diretta'
);

SELECT is(
  catalogo.fn_get_uom_factor((SELECT art_fallback_id FROM tmp_seed), 13),
  0.25::numeric,
  'Fallback conversione inversa'
);

SELECT is(
  catalogo.fn_get_uom_factor((SELECT art_fallback_id FROM tmp_seed), 9999),
  NULL,
  'Nessuna conversione trovata: NULL'
);
