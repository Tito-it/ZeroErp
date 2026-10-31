-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: la regola dei periodi del canone, vendite.fn_canone_periodi
--       (changeSet 20261029-25, brief-db-contratto-righe-periodiche-in-commessa §6.7,
--       Lotto 6). Decisioni di Tid G-2, G-3 (2026-10-28) e F-2 … F-7 (2026-10-29):
--       calendario dal mese di partenza; anticipati = appena cominciato, normali =
--       appena finito; il mese a meta' a giorni, i mesi interi a mesi; un pezzo per
--       anno; resto dell'arrotondamento sull'ultimo pezzo; competenza = mese del giro.
--
-- ⭐ Building block puro: nessuna fixture, legge solo il seed di config.periodicita.
-- ⚠️ I codici d'errore si leggono dal canale CONSTRAINT dell'eccezione, non dalla frase.
--
-- Indice test (1..15):
--   Gli esempi di Tid (bimestrale, contratto dal 15/01, giro di marzo)
--    1) normali: il primo periodo parziale 15/01-28/02, a giorni il mese a meta'
--    2) anticipati: anche il periodo 01/03-30/04, appena cominciato
--    3) competenza_mese = il mese del giro su tutti i pezzi
--   Il mese di partenza e la spezzatura (F-2)
--    4) trimestrale da novembre: nov-gen si spezza in nov-dic e gen
--    5) …e i due pezzi sommano esattamente il periodo (resto sull'ultimo)
--    6) trimestrale da febbraio: un contratto dal 01/01 cade nel periodo nov-gen
--    7) annuale da luglio, contratto dal 15/08: due pezzi, mese a meta' a giorni
--   La fine e il «da» (G-2)
--    8) contratto cessato il 15/03: l'ultimo periodo si taglia e va a giorni
--    9) il «da»: i periodi gia' addebitati si saltano
--   10) normali: il periodo non ancora finito non si addebita
--   11) normali: il giorno dopo la fine si'
--   I parametri
--   12) periodicita' fuori vocabolario: E_PARAMETRO_INVALIDO
--   13) mese di partenza 13: E_PARAMETRO_INVALIDO
--   14) fine prima dell'inizio: E_PARAMETRO_INVALIDO
--   La forma
--   15) STABLE e SECURITY INVOKER
-- ------------------------------------------------------------

BEGIN;
SET CONSTRAINTS ALL IMMEDIATE;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(15);

-- Scopo: i pezzi come testo ordinato, «dal..al=frazione».
CREATE OR REPLACE FUNCTION pg_temp.pezzi(p_dal date, p_al date, p_per text, p_mese int,
                                         p_gen text, p_giro date, p_da date DEFAULT NULL)
RETURNS text LANGUAGE sql STABLE AS $fx$
    SELECT coalesce(string_agg(p.periodo_dal || '..' || p.periodo_al || '=' || p.frazione,
                               ' ' ORDER BY p.periodo_dal), '-')
      FROM vendite.fn_canone_periodi(p_dal, p_al, p_per, p_mese::smallint, p_gen, p_giro, p_da) p;
$fx$;

-- Scopo: il codice d'errore di uno statement che deve fallire (canale CONSTRAINT).
CREATE OR REPLACE FUNCTION pg_temp.codice(p_sql text)
RETURNS text LANGUAGE plpgsql AS $fx$
DECLARE v_cst text;
BEGIN
    BEGIN
        EXECUTE p_sql;
        RETURN 'NESSUN ERRORE';
    EXCEPTION WHEN OTHERS THEN
        GET STACKED DIAGNOSTICS v_cst = CONSTRAINT_NAME;
        RETURN coalesce(nullif(v_cst, ''), '-');
    END;
END;
$fx$;

-- ============================================================
-- 1-3) Gli esempi di Tid
-- ============================================================
-- Gennaio dal 15: 17/31; febbraio intero: 1; diviso i 2 mesi del bimestre.
SELECT is(pg_temp.pezzi('2026-01-15', NULL, 'BIMESTRALE', 1, 'FINE_PERIODO', '2026-03-05'),
    '2026-01-15..2026-02-28=0.774194',
    '1) normali, giro di marzo: 15/01-28/02, il mese a meta'' a giorni');

SELECT is(pg_temp.pezzi('2026-01-15', NULL, 'BIMESTRALE', 1, 'INIZIO_PERIODO', '2026-03-05'),
    '2026-01-15..2026-02-28=0.774194 2026-03-01..2026-04-30=1.000000',
    '2) anticipati, giro di marzo: anche 01/03-30/04, appena cominciato');

SELECT is(
    (SELECT string_agg(DISTINCT p.competenza_mese::text, ' ')
       FROM vendite.fn_canone_periodi('2026-01-15', NULL, 'BIMESTRALE', 1::smallint,
                                      'INIZIO_PERIODO', '2026-03-05') p),
    '2026-03-01',
    '3) competenza_mese = il mese del giro su tutti i pezzi (F-6)');

-- ============================================================
-- 4-7) Il mese di partenza e la spezzatura
-- ============================================================
SELECT is(pg_temp.pezzi('2025-11-01', NULL, 'TRIMESTRALE', 11, 'INIZIO_PERIODO', '2025-11-10'),
    '2025-11-01..2025-12-31=0.666667 2026-01-01..2026-01-31=0.333333',
    '4) trimestrale da novembre: nov-gen si spezza al 31/12 in nov-dic e gen');

-- ⚠️ Le righe devono esserci: una somma NULL non sarebbe 1.
SELECT is(
    (SELECT sum(p.frazione) FROM vendite.fn_canone_periodi('2025-11-01', NULL, 'TRIMESTRALE',
                                 11::smallint, 'INIZIO_PERIODO', '2025-11-10') p),
    1.000000::numeric,
    '5) …e i pezzi sommano esattamente il periodo: il resto va sull''ultimo');

SELECT is(pg_temp.pezzi('2026-01-01', NULL, 'TRIMESTRALE', 2, 'INIZIO_PERIODO', '2026-01-05'),
    '2026-01-01..2026-01-31=0.333333',
    '6) trimestrale da febbraio: il contratto dal 01/01 cade nel periodo nov-gen, 1 mese su 3');

-- Agosto dal 15: 17/31, poi set-dic 4 mesi: (17/31 + 4) / 12; poi gen-giu 6/12.
SELECT is(pg_temp.pezzi('2026-08-15', NULL, 'ANNUALE', 7, 'INIZIO_PERIODO', '2026-08-20'),
    '2026-08-15..2026-12-31=0.379032 2027-01-01..2027-06-30=0.500000',
    '7) annuale da luglio, contratto dal 15/08: un pezzo per anno, il mese a meta'' a giorni');

-- ============================================================
-- 8-11) La fine e il «da»
-- ============================================================
SELECT is(pg_temp.pezzi('2026-01-01', '2026-03-15', 'MENSILE', 1, 'FINE_PERIODO', '2026-06-01'),
    '2026-01-01..2026-01-31=1.000000 2026-02-01..2026-02-28=1.000000 2026-03-01..2026-03-15=0.483871',
    '8) cessato il 15/03: fino alla fine, l''ultimo periodo a giorni (15/31), niente dopo');

SELECT is(pg_temp.pezzi('2026-01-01', NULL, 'MENSILE', 1, 'INIZIO_PERIODO', '2026-03-10', '2026-02-01'),
    '2026-02-01..2026-02-28=1.000000 2026-03-01..2026-03-31=1.000000',
    '9) il «da» (giorno dopo l''ultimo addebito): gennaio si salta, gli arretrati dovuti ci sono');

SELECT is(pg_temp.pezzi('2026-03-01', NULL, 'MENSILE', 1, 'FINE_PERIODO', '2026-03-31'),
    '-',
    '10) normali: marzo non e'' finito il 31/03, non si addebita');

SELECT is(pg_temp.pezzi('2026-03-01', NULL, 'MENSILE', 1, 'FINE_PERIODO', '2026-04-01'),
    '2026-03-01..2026-03-31=1.000000',
    '11) normali: il giorno dopo la fine si''');

-- ============================================================
-- 12-14) I parametri
-- ============================================================
SELECT is(pg_temp.codice($$SELECT * FROM vendite.fn_canone_periodi('2026-01-01', NULL, 'XX', 1::smallint, 'INIZIO_PERIODO', '2026-03-10')$$),
    'E_PARAMETRO_INVALIDO',
    '12) periodicita'' fuori vocabolario: E_PARAMETRO_INVALIDO');

SELECT is(pg_temp.codice($$SELECT * FROM vendite.fn_canone_periodi('2026-01-01', NULL, 'MENSILE', 13::smallint, 'INIZIO_PERIODO', '2026-03-10')$$),
    'E_PARAMETRO_INVALIDO',
    '13) mese di partenza 13: E_PARAMETRO_INVALIDO');

SELECT is(pg_temp.codice($$SELECT * FROM vendite.fn_canone_periodi('2026-03-01', '2026-01-31', 'MENSILE', 1::smallint, 'INIZIO_PERIODO', '2026-03-10')$$),
    'E_PARAMETRO_INVALIDO',
    '14) fine prima dell''inizio: E_PARAMETRO_INVALIDO');

-- ============================================================
-- 15) La forma
-- ============================================================
SELECT is(
    (SELECT p.provolatile::text || '/' || p.prosecdef::text
       FROM pg_proc p
      WHERE p.oid = 'vendite.fn_canone_periodi(date, date, character varying, smallint, character varying, date, date)'::regprocedure),
    's/false',
    '15) STABLE e SECURITY INVOKER');

SELECT * FROM finish();
ROLLBACK;
