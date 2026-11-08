-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
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

-- ⛔ Rev 2026-11-03 (D16 di migliorie-generali-da-test-valutazione): le date
--   erano LETTERALI (2030-2032). Il guard vendite.trgfn_promo_articoli_guard_
--   data_driven crea una promo solo se `valido_dal` e' DOPO oggi
--   (fn_data_operativa): scritte quando erano future, dal 2030-01-01 i test
--   1..4 sarebbero diventati rossi da soli. Ora derivano tutte da UNA base, il
--   primo del mese fra un anno: sempre nel futuro, trimestri consecutivi che
--   non si sovrappongono (test 1..4), e il test 8 cade DENTRO il primo.
CREATE TEMP TABLE tmp_promo_date AS
WITH b AS (
    SELECT (date_trunc('month', script.fn_data_operativa()) + interval '1 year')::date AS base
)
SELECT base                                           AS t1_dal,
       (base + interval '3 months'  - interval '1 day')::date AS t1_al,
       (base + interval '3 months')::date              AS t2_dal,
       (base + interval '6 months'  - interval '1 day')::date AS t2_al,
       (base + interval '6 months')::date              AS t3_dal,
       (base + interval '9 months'  - interval '1 day')::date AS t3_al,
       (base + interval '9 months')::date              AS t4_dal,
       (base + interval '12 months' - interval '1 day')::date AS t4_al,
       (base + interval '12 months')::date             AS t5_dal,
       (base + interval '15 months' - interval '1 day')::date AS t5_al,
       -- test 6: al PRIMA di dal
       (base + interval '17 months')::date             AS t6_dal,
       (base + interval '12 months')::date             AS t6_al,
       (base + interval '24 months')::date             AS t7_dal,
       (base + interval '27 months' - interval '1 day')::date AS t7_al,
       -- test 8: un mese dentro il trimestre del test 1
       (base + interval '1 month')::date               AS t8_dal,
       (base + interval '2 months'  - interval '1 day')::date AS t8_al
  FROM b;

-- 1) PERCENTUALE positivo ammesso
SELECT lives_ok(
    $$INSERT INTO vendite.promo_articoli(codice, descrizione, articolo_id, uom_id,
          tipo_variazione, valore_variazione, valido_dal, valido_al)
      SELECT 'PGTAP_PROMO_PERC', 'Test PERCENTUALE', a.articolo_id, a.uom_id,
             'PERCENTUALE', 10, d.t1_dal, d.t1_al
        FROM tmp_ctx_articolo a, tmp_promo_date d$$,
    'Promo PERCENTUALE con valore > 0 ammessa'
);

-- 2) VALORE_FISSO positivo ammesso
SELECT lives_ok(
    $$INSERT INTO vendite.promo_articoli(codice, descrizione, articolo_id, uom_id,
          tipo_variazione, valore_variazione, valido_dal, valido_al)
      SELECT 'PGTAP_PROMO_VFISS', 'Test VALORE_FISSO', a.articolo_id, a.uom_id,
             'VALORE_FISSO', 5, d.t2_dal, d.t2_al
        FROM tmp_ctx_articolo a, tmp_promo_date d$$,
    'Promo VALORE_FISSO con valore > 0 ammessa'
);

-- 3) PREZZO_FISSO con valore = 0 ammesso (prezzo assoluto libero, check >= 0)
SELECT lives_ok(
    $$INSERT INTO vendite.promo_articoli(codice, descrizione, articolo_id, uom_id,
          tipo_variazione, valore_variazione, valido_dal, valido_al)
      SELECT 'PGTAP_PROMO_PFISS', 'Test PREZZO_FISSO', a.articolo_id, a.uom_id,
             'PREZZO_FISSO', 0, d.t3_dal, d.t3_al
        FROM tmp_ctx_articolo a, tmp_promo_date d$$,
    'Promo PREZZO_FISSO con valore 0 ammessa (chk_promo_articoli_valore: PREZZO_FISSO >= 0)'
);

-- 4) PERCENTUALE con valore = 0 ora ammesso (CHECK chk_promo_articoli_valore
-- rimosso il 15-04-2026: la convenzione di segno e' demandata a UI/business).
SELECT lives_ok(
    $$INSERT INTO vendite.promo_articoli(codice, descrizione, articolo_id, uom_id,
          tipo_variazione, valore_variazione, valido_dal, valido_al)
      SELECT 'PGTAP_PROMO_PERC_ZERO', 'Test PERC zero', a.articolo_id, a.uom_id,
             'PERCENTUALE', 0, d.t4_dal, d.t4_al
        FROM tmp_ctx_articolo a, tmp_promo_date d$$,
    'PERCENTUALE con valore = 0 ora ammesso (nessun vincolo DB sul segno)'
);

-- 5) tipo_variazione fuori dominio
SELECT throws_ok(
    $$INSERT INTO vendite.promo_articoli(codice, descrizione, articolo_id, uom_id,
          tipo_variazione, valore_variazione, valido_dal, valido_al)
      SELECT 'PGTAP_PROMO_BAD', 'Test tipo invalido', a.articolo_id, a.uom_id,
             'SCONTO', 10, d.t5_dal, d.t5_al
        FROM tmp_ctx_articolo a, tmp_promo_date d$$,
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
             'PERCENTUALE', 5, d.t6_dal, d.t6_al
        FROM tmp_ctx_articolo a, tmp_promo_date d$$,
    '%è inferiore alla data dal%',
    'valido_al < valido_dal: parla il guard comune delle date (E_DATA_AL_MINORE_DAL)'
);

-- 7) codice UNIQUE
SELECT throws_ok(
    $$INSERT INTO vendite.promo_articoli(codice, descrizione, articolo_id, uom_id,
          tipo_variazione, valore_variazione, valido_dal, valido_al)
      SELECT 'PGTAP_PROMO_PERC', 'Duplicato codice', a.articolo_id, a.uom_id,
             'PERCENTUALE', 8, d.t7_dal, d.t7_al
        FROM tmp_ctx_articolo a, tmp_promo_date d$$,
    '23505',
    NULL,
    'Insert con codice duplicato viola uq_promo_articoli_codice'
);

-- 8) EXCLUDE no-overlap su (articolo, uom) attivi
SELECT throws_ok(
    $$INSERT INTO vendite.promo_articoli(codice, descrizione, articolo_id, uom_id,
          tipo_variazione, valore_variazione, valido_dal, valido_al)
      SELECT 'PGTAP_PROMO_OVERLAP', 'Test overlap', a.articolo_id, a.uom_id,
             'PERCENTUALE', 5, d.t8_dal, d.t8_al
        FROM tmp_ctx_articolo a, tmp_promo_date d$$,
    '23P01',
    NULL,
    'EXCLUDE blocca overlap su (articolo, uom) attive'
);

-- 9) Colonna generata validita.
-- Il costruttore daterange('[]') normalizza a '[)' con +1 giorno sul superiore.
SELECT is(
    (SELECT validita::text FROM vendite.promo_articoli
      WHERE codice = 'PGTAP_PROMO_PERC'),
    (SELECT '[' || t1_dal || ',' || (t1_al + 1) || ')' FROM tmp_promo_date),
    'La colonna generata validita e'' sincronizzata (daterange normalizzato [), +1gg su valido_al)'
);

SELECT * FROM finish();
ROLLBACK;
