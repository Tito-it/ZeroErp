-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test F1-DB-T3: promo_articoli (overlay pricing v5 - STADIO 0).
-- Copre CHECK vincoli, EXCLUDE no-overlap, colonna generata validita.
--
-- Elenco test (1..9):
--   1) tipo_variazione = 'PERCENTUALE' con valore > 0 ammesso
--   2) tipo_variazione = 'VALORE_FISSO' con valore > 0 ammesso
--   3) tipo_variazione = 'PREZZO_FISSO' con valore = 0 ammesso (prezzo assoluto)
--   4) tipo_variazione = 'PERCENTUALE' con valore = 0 ammesso (chk_promo_articoli_valore rimosso 15-04-2026)
--   5) tipo_variazione fuori dominio (es. 'SCONTO') -> fallisce
--   6) valido_al < valido_dal -> guard comune delle date (E_DATA_AL_MINORE_DAL)
--   7) codice UNIQUE: insert duplicato fallisce
--   8) EXCLUDE no-overlap: stessa (articolo, uom) con periodo overlappato -> fallisce
--   9) La colonna generata validita popola il daterange
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

SELECT plan(9);

-- Precondizioni: un articolo COSTRUITO (nasce merce, non solo componente) e
-- la sua UoM base. ⚠️ Rev 2026-10-14 (20261014-05, D-6 di
-- brief-db-articoli-ammessi-per-documento): una promo su un articolo solo
-- componente e' rifiutata, e «il primo articolo attivo per id» poteva
-- esserlo. In due istruzioni: la riga nata dal builder non e' visibile a una
-- JOIN della stessa istruzione.
CREATE TEMP TABLE tmp_ctx_articolo AS
SELECT dbops.fn_pgtap_crea_articolo('PGTAP-PROMO-T3', false) AS articolo_id,
       NULL::bigint AS uom_id;
UPDATE tmp_ctx_articolo t SET uom_id = a.uom_id
  FROM catalogo.articoli a
 WHERE a.id = t.articolo_id;

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

-- 4) PERCENTUALE con valore = 0 ora ammesso (CHECK chk_promo_articoli_valore
-- rimosso il 15-04-2026: la convenzione di segno e' demandata a UI/business).
SELECT lives_ok(
    $$INSERT INTO vendite.promo_articoli(codice, descrizione, articolo_id, uom_id,
          tipo_variazione, valore_variazione, valido_dal, valido_al)
      SELECT 'PGTAP_PROMO_PERC_ZERO', 'Test PERC zero', a.articolo_id, a.uom_id,
             'PERCENTUALE', 0, '2030-10-01', '2030-12-31'
        FROM tmp_ctx_articolo a$$,
    'PERCENTUALE con valore = 0 ora ammesso (nessun vincolo DB sul segno)'
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

-- 6) valido_al < valido_dal: parla il guard comune delle date (2026-09-23,
--    brief-db-guard-date-validita). Prima rifiutava il costruttore del
--    daterange della colonna generata, 22000, con una frase tecnica.
SELECT throws_like(
    $$INSERT INTO vendite.promo_articoli(codice, descrizione, articolo_id, uom_id,
          tipo_variazione, valore_variazione, valido_dal, valido_al)
      SELECT 'PGTAP_PROMO_DATE_BAD', 'Test date invertite', a.articolo_id, a.uom_id,
             'PERCENTUALE', 5, '2031-06-01', '2031-01-01'
        FROM tmp_ctx_articolo a$$,
    '%è inferiore alla data dal%',
    'valido_al < valido_dal: parla il guard comune delle date (E_DATA_AL_MINORE_DAL)'
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

-- 9) Colonna generata validita.
-- Il costruttore daterange('[]') normalizza a '[)' con +1 giorno sul superiore.
SELECT is(
    (SELECT validita::text FROM vendite.promo_articoli
      WHERE codice = 'PGTAP_PROMO_PERC'),
    '[2030-01-01,2030-04-01)',
    'La colonna generata validita e'' sincronizzata (daterange normalizzato [), +1gg su valido_al)'
);

SELECT * FROM finish();
ROLLBACK;
