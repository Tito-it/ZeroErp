-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test F1-DB-T3: promo_articoli (overlay pricing v5 - STADIO 0).
-- Copre CHECK vincoli, EXCLUDE no-overlap, trigger set_validita.
--
-- Elenco test (1..9):
--   1) tipo_variazione = 'PERCENTUALE' con valore > 0 ammesso
--   2) tipo_variazione = 'VALORE_FISSO' con valore > 0 ammesso
--   3) tipo_variazione = 'PREZZO_FISSO' con valore = 0 ammesso (prezzo assoluto)
--   4) tipo_variazione = 'PERCENTUALE' con valore = 0 vietato (chk_promo_articoli_valore)
--   5) tipo_variazione fuori dominio (es. 'SCONTO') -> fallisce
--   6) valido_al < valido_dal -> costruttore daterange fallisce (22000)
--   7) codice UNIQUE: insert duplicato fallisce
--   8) EXCLUDE no-overlap: stessa (articolo, uom) con periodo overlappato -> fallisce
--   9) Trigger set_validita popola validita daterange
-- ------------------------------------------------------------

BEGIN;
SELECT plan(9);

-- Precondizioni: serve un articolo attivo e una uom attiva (qualsiasi).
CREATE TEMP TABLE tmp_ctx_articolo AS
SELECT id AS articolo_id, uom_id
  FROM catalogo.articoli
 WHERE attivo IS TRUE
 ORDER BY id
 LIMIT 1;

-- 1) PERCENTUALE positivo ammesso
SELECT lives_ok(
    $$INSERT INTO vendite.promo_articoli(codice, descrizione, articolo_id, uom_id,
          tipo_variazione, valore_variazione, valido_dal, valido_al)
      SELECT 'PGTAP_PROMO_PERC', 'Test PERCENTUALE', a.articolo_id, a.uom_id,
             'PERCENTUALE', 10, '2030-01-01', '2030-03-31'
        FROM tmp_ctx_articolo a$$,
    'Promo PERCENTUALE con valore > 0 ammessa'
);

-- 2) VALORE_FISSO positivo ammesso
SELECT lives_ok(
    $$INSERT INTO vendite.promo_articoli(codice, descrizione, articolo_id, uom_id,
          tipo_variazione, valore_variazione, valido_dal, valido_al)
      SELECT 'PGTAP_PROMO_VFISS', 'Test VALORE_FISSO', a.articolo_id, a.uom_id,
             'VALORE_FISSO', 5, '2030-04-01', '2030-06-30'
        FROM tmp_ctx_articolo a$$,
    'Promo VALORE_FISSO con valore > 0 ammessa'
);

-- 3) PREZZO_FISSO con valore = 0 ammesso (prezzo assoluto libero, check >= 0)
SELECT lives_ok(
    $$INSERT INTO vendite.promo_articoli(codice, descrizione, articolo_id, uom_id,
          tipo_variazione, valore_variazione, valido_dal, valido_al)
      SELECT 'PGTAP_PROMO_PFISS', 'Test PREZZO_FISSO', a.articolo_id, a.uom_id,
             'PREZZO_FISSO', 0, '2030-07-01', '2030-09-30'
        FROM tmp_ctx_articolo a$$,
    'Promo PREZZO_FISSO con valore 0 ammessa (chk_promo_articoli_valore: PREZZO_FISSO >= 0)'
);

-- 4) PERCENTUALE con valore = 0 vietato (chk > 0 per variazioni relative)
SELECT throws_ok(
    $$INSERT INTO vendite.promo_articoli(codice, descrizione, articolo_id, uom_id,
          tipo_variazione, valore_variazione, valido_dal, valido_al)
      SELECT 'PGTAP_PROMO_PERC_ZERO', 'Test PERC zero', a.articolo_id, a.uom_id,
             'PERCENTUALE', 0, '2030-10-01', '2030-12-31'
        FROM tmp_ctx_articolo a$$,
    '23514',
    NULL,
    'PERCENTUALE con valore = 0 viola chk_promo_articoli_valore'
);

-- 5) tipo_variazione fuori dominio
SELECT throws_ok(
    $$INSERT INTO vendite.promo_articoli(codice, descrizione, articolo_id, uom_id,
          tipo_variazione, valore_variazione, valido_dal, valido_al)
      SELECT 'PGTAP_PROMO_BAD', 'Test tipo invalido', a.articolo_id, a.uom_id,
             'SCONTO', 10, '2031-01-01', '2031-03-31'
        FROM tmp_ctx_articolo a$$,
    '23514',
    NULL,
    'tipo_variazione fuori dominio viola chk_promo_articoli_tipo_variazione'
);

-- 6) valido_al < valido_dal: daterange lo rifiuta prima di qualsiasi CHECK.
SELECT throws_ok(
    $$INSERT INTO vendite.promo_articoli(codice, descrizione, articolo_id, uom_id,
          tipo_variazione, valore_variazione, valido_dal, valido_al)
      SELECT 'PGTAP_PROMO_DATE_BAD', 'Test date invertite', a.articolo_id, a.uom_id,
             'PERCENTUALE', 5, '2031-06-01', '2031-01-01'
        FROM tmp_ctx_articolo a$$,
    '22000',
    NULL,
    'valido_al < valido_dal: daterange(valido_dal, valido_al) fallisce con 22000'
);

-- 7) codice UNIQUE
SELECT throws_ok(
    $$INSERT INTO vendite.promo_articoli(codice, descrizione, articolo_id, uom_id,
          tipo_variazione, valore_variazione, valido_dal, valido_al)
      SELECT 'PGTAP_PROMO_PERC', 'Duplicato codice', a.articolo_id, a.uom_id,
             'PERCENTUALE', 8, '2032-01-01', '2032-03-31'
        FROM tmp_ctx_articolo a$$,
    '23505',
    NULL,
    'Insert con codice duplicato viola uq_promo_articoli_codice'
);

-- 8) EXCLUDE no-overlap su (articolo, uom) attivi
SELECT throws_ok(
    $$INSERT INTO vendite.promo_articoli(codice, descrizione, articolo_id, uom_id,
          tipo_variazione, valore_variazione, valido_dal, valido_al)
      SELECT 'PGTAP_PROMO_OVERLAP', 'Test overlap', a.articolo_id, a.uom_id,
             'PERCENTUALE', 5, '2030-02-01', '2030-02-28'
        FROM tmp_ctx_articolo a$$,
    '23P01',
    NULL,
    'EXCLUDE blocca overlap su (articolo, uom) attive'
);

-- 9) Trigger set_validita.
-- Il costruttore daterange('[]') normalizza a '[)' con +1 giorno sul superiore.
SELECT is(
    (SELECT validita::text FROM vendite.promo_articoli
      WHERE codice = 'PGTAP_PROMO_PERC'),
    '[2030-01-01,2030-04-01)',
    'Trigger set_validita sincronizza validita (daterange normalizzato [), +1gg su valido_al)'
);

SELECT * FROM finish();
ROLLBACK;
