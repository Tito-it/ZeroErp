-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: I MESI SI CONTANO SUL CALENDARIO
--       script.fn_mesi_dopo · script.fn_mesi_del_tratto
--       brief-db-mese-di-un-giorno §6.6, giro 6 (20261115-62 … -64, -76, -77)
-- ------------------------------------------------------------
-- Indice test (1..16, con 7b, 8b, 12a e 12b: 19 asserzioni)
--  1-2) le due funzioni esistono con la firma attesa
--  3-4) fn_mesi_dopo restituisce date, fn_mesi_del_tratto una tabella
--  5-6) sono IMMUTABLE: il calcolo non dipende dalla sessione
--  7-7b) fn_mesi_dopo NON e' STRICT, ed e' espansa nel piano (-76)
--  8-8b) fn_mesi_del_tratto NON e' STRICT, ed e' espansa nel piano (-77)
--  9) fn_mesi_dopo sui casi costruiti (fine mese tagliata, bisestili anche
--     di secolo, cambio d'anno avanti e indietro, zero mesi)
-- 10) fn_mesi_dopo con un argomento NULL -> NULL
-- 11) fn_mesi_dopo = (<date> + make_interval(months => n))::date per
--     tredici valori di n, su ogni giorno 2023-2029 e degli inverni di
--     secolo (1899-1900, 1999-2000, 2099-2100)
-- 12a-12b) fn_mesi_del_tratto sui casi costruiti (un mese, tre, cambio d'anno,
--     febbraio bisestile)
-- 13) fn_mesi_del_tratto: estremo NULL o fine in un mese prima -> nessuna riga
-- 14-15) fn_mesi_del_tratto = generate_series(fn_mese_di(dal), al,
--        interval '1 month') su ~4.400 tratti 2023-2026, sotto due fusi
-- 16) nessuna vista e nessuna funzione degli schemi applicativi somma mesi
--     per conto suo (make_interval(months => …), un intervallo di mesi)
-- ------------------------------------------------------------
-- Scopo:
--  - sommare mesi e contare i mesi di un tratto sono aritmetica di
--    calendario: niente istanti, niente fuso. I valori attesi di 9 e 12
--    sono scritti a mano e coprono i confini che una formula sbagliata
--    tradisce: il 31 verso un mese di 30 o 28 giorni, il 29 febbraio verso
--    un anno non bisestile, dicembre verso gennaio e ritorno;
--  - le due funzioni sostituiscono (x + make_interval(months => n))::date e
--    generate_series(<date>, <date>, interval '1 month'): 11, 14 e 15
--    provano che la sostituzione non cambia nessun risultato. Le due forme
--    qui sono l'ORACOLO di cio' che si ritira, non un uso, e vivono in
--    pg_temp, che il presidio 16 non guarda;
--  - generate_series su date passa da timestamptz (la variante scelta da
--    PostgreSQL): per questo 14-15 girano in due fusi, come i test del mese.
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: il test gira come gira l'applicazione.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(19);

-- Il piano di una query, come testo (forma di script/test-mese-di-un-giorno-v1)
CREATE FUNCTION pg_temp.piano(p_query text)
 RETURNS text
 LANGUAGE plpgsql
AS $f$
DECLARE
    v_riga record;
    v_out  text := '';
BEGIN
    FOR v_riga IN EXECUTE 'EXPLAIN (VERBOSE, COSTS OFF) ' || p_query LOOP
        v_out := v_out || v_riga."QUERY PLAN" || E'\n';
    END LOOP;
    RETURN v_out;
END;
$f$;

-- Le differenze di fn_mesi_dopo dal calcolo di oggi, giorno per giorno e per
-- ogni n. Vuoto = uguali.
-- ℹ️ Il dominio: la regola dipende dalla lunghezza dei mesi e dai bisestili,
--   non dall'anno. Sette anni interi (2023-2029: due bisestili, ogni
--   lunghezza di mese, ogni giorno della settimana) e gli inverni dei tre
--   secoli, dove il bisestile ha l'eccezione (1900 e 2100 no, 2000 si'); con
--   n fino a 120 gli arrivi coprono anche gli anni intorno. Duecento anni di
--   giorni non provano di piu', e costano dieci volte tanto.
CREATE FUNCTION pg_temp.differenze_mesi_dopo()
 RETURNS text
 LANGUAGE sql
AS $f$
    SELECT coalesce(string_agg(g::date::text || '+' || n, ',' ORDER BY g, n), '')
      FROM (SELECT generate_series(date '2023-01-01', date '2029-12-31', interval '1 day')
            UNION ALL
            SELECT generate_series(make_date(a - 1, 12, 1), make_date(a, 3, 31), interval '1 day')
              FROM unnest(ARRAY[1900, 2000, 2100]) a) s(g)
     CROSS JOIN unnest(ARRAY[-25, -13, -12, -11, -1, 0, 1, 2, 11, 12, 13, 25, 120]) n
     WHERE script.fn_mesi_dopo(g::date, n)
           IS DISTINCT FROM (g::date + make_interval(months => n))::date;
$f$;

-- Le differenze di fn_mesi_del_tratto dalla serie di oggi, nel fuso della
-- sessione corrente. I tratti: un inizio ogni due giorni dal 2023 al 2026
-- (un bisestile, otto cambi d'ora), con fini prima, uguali e dopo (fino a 400
-- giorni). Vuoto = uguali.
CREATE FUNCTION pg_temp.differenze_mesi_del_tratto()
 RETURNS text
 LANGUAGE sql
AS $f$
    WITH tratti AS (
        SELECT d::date AS dal, d::date + delta AS al
          FROM generate_series(date '2023-01-01', date '2026-12-31', interval '2 days') d
         CROSS JOIN unnest(ARRAY[-40, -1, 0, 20, 45, 400]) delta)
    SELECT coalesce(string_agg(t.dal || '..' || t.al, ',' ORDER BY t.dal, t.al), '')
      FROM tratti t
     WHERE ARRAY(SELECT m.mese || '/' || m.fine_mese
                   FROM script.fn_mesi_del_tratto(t.dal, t.al) m)
           IS DISTINCT FROM
           ARRAY(SELECT g::date || '/' || script.fn_fine_mese_di(g::date)
                   FROM generate_series(script.fn_mese_di(t.dal), t.al, interval '1 month') g
                  ORDER BY g);
$f$;

-- ============================================================
-- 1-8) La forma
-- ============================================================
SELECT has_function('script', 'fn_mesi_dopo', ARRAY['date', 'integer'],
  '1) script.fn_mesi_dopo(date, integer) esiste');
SELECT has_function('script', 'fn_mesi_del_tratto', ARRAY['date', 'date'],
  '2) script.fn_mesi_del_tratto(date, date) esiste');

SELECT function_returns('script', 'fn_mesi_dopo', ARRAY['date', 'integer'], 'date',
  '3) fn_mesi_dopo restituisce date');
SELECT function_returns('script', 'fn_mesi_del_tratto', ARRAY['date', 'date'], 'setof record',
  '4) fn_mesi_del_tratto restituisce una tabella (mese, fine_mese)');

-- ⭐ IMMUTABLE e' cio' che make_interval e generate_series su date non
--   davano: la prova che il calcolo non passa da un istante.
SELECT volatility_is('script', 'fn_mesi_dopo', ARRAY['date', 'integer'], 'immutable',
  '5) fn_mesi_dopo e'' IMMUTABLE');
SELECT volatility_is('script', 'fn_mesi_del_tratto', ARRAY['date', 'date'], 'immutable',
  '6) fn_mesi_del_tratto e'' IMMUTABLE');

-- ⚠️ fn_mesi_dopo NON e' STRICT, di proposito (20261115-76): il planner non
--   espande una funzione STRICT il cui corpo non e' strict, e least() non lo
--   e'. NULL -> NULL lo da' l'espressione (10). L'espansione e' la proprieta'
--   che conta: da chiamata opaca, il calcolo costa tre volte tanto (misura
--   del 2026-11-15 sullo scratch). 7b la pretende, come il 16 del mese.
SELECT isnt_strict('script', 'fn_mesi_dopo', ARRAY['date', 'integer'],
  '7) fn_mesi_dopo non e'' STRICT: e'' la condizione per espanderla');
-- La colonna viene da generate_series: con un letterale il planner
-- calcolerebbe tutto in anticipo e il piano non direbbe niente.
SELECT ok(
  pg_temp.piano($q$
    SELECT script.fn_mesi_dopo(g::date, 1)
      FROM generate_series(date '2026-01-01', date '2026-12-31', interval '1 day') g
  $q$) !~ 'fn_mesi_dopo',
  '7b) nel piano non resta la chiamata: fn_mesi_dopo e'' espansa nel punto d''uso');

-- ⚠️ Lo stesso per fn_mesi_del_tratto (20261115-77): il planner non espande
--   mai una funzione che restituisce righe se e' STRICT. «Un estremo NULL,
--   nessuna riga» lo da' la serie vuota (13).
SELECT isnt_strict('script', 'fn_mesi_del_tratto', ARRAY['date', 'date'],
  '8) fn_mesi_del_tratto non e'' STRICT: e'' la condizione per espanderla');
SELECT ok(
  pg_temp.piano($q$
    SELECT m.* FROM generate_series(date '2026-01-01', date '2026-01-03', interval '1 day') g
     CROSS JOIN LATERAL script.fn_mesi_del_tratto(g::date, g::date + 60) m
  $q$) !~ 'fn_mesi_del_tratto',
  '8b) nel piano non resta la chiamata: fn_mesi_del_tratto e'' espansa nel punto d''uso');

-- ============================================================
-- 9-10) fn_mesi_dopo, i casi costruiti
-- ============================================================
SELECT is(
  ARRAY[script.fn_mesi_dopo(date '2026-01-31', 1),
        script.fn_mesi_dopo(date '2024-01-31', 1),
        script.fn_mesi_dopo(date '2024-02-29', 12),
        script.fn_mesi_dopo(date '2026-03-31', -1),
        script.fn_mesi_dopo(date '2026-08-31', 1),
        script.fn_mesi_dopo(date '2026-12-15', 1),
        script.fn_mesi_dopo(date '2026-01-01', -1),
        script.fn_mesi_dopo(date '2026-05-17', 0),
        script.fn_mesi_dopo(date '2026-01-01', -13),
        script.fn_mesi_dopo(date '2026-11-30', 15),
        script.fn_mesi_dopo(date '1900-01-31', 1),
        script.fn_mesi_dopo(date '2000-01-31', 1),
        script.fn_mesi_dopo(date '2100-01-31', 1)],
  ARRAY[date '2026-02-28', date '2024-02-29', date '2025-02-28', date '2026-02-28',
        date '2026-09-30', date '2027-01-15', date '2025-12-01', date '2026-05-17',
        date '2024-12-01', date '2028-02-29',
        date '1900-02-28', date '2000-02-29', date '2100-02-28'],
  '9) fn_mesi_dopo: 31 su febbraio e su un mese di 30, 29 febbraio + 1 anno, dicembre/gennaio, 0, -13, +15, febbrai di secolo');

SELECT is(
  ARRAY[script.fn_mesi_dopo(NULL::date, 1), script.fn_mesi_dopo(date '2026-01-01', NULL::integer)],
  ARRAY[NULL::date, NULL::date],
  '10) fn_mesi_dopo: un argomento NULL -> NULL');

-- ============================================================
-- 11) fn_mesi_dopo identica al calcolo che sostituisce
-- ============================================================
-- Un fuso basta: date + interval e' un timestamp senza fuso, quindi
-- l'oracolo non dipende dalla sessione, e fn_mesi_dopo e' IMMUTABLE.
SELECT is(pg_temp.differenze_mesi_dopo(), '',
  '11) fn_mesi_dopo = (<date> + make_interval(months => n))::date su ogni giorno 1899-2101, tredici n');

-- ============================================================
-- 12-13) fn_mesi_del_tratto, i casi costruiti
-- ============================================================
SELECT is(
  ARRAY(SELECT m.mese || '/' || m.fine_mese FROM script.fn_mesi_del_tratto(date '2026-01-15', date '2026-03-10') m),
  ARRAY['2026-01-01/2026-01-31', '2026-02-01/2026-02-28', '2026-03-01/2026-03-31'],
  '12a) fn_mesi_del_tratto: tre mesi, gli estremi non tagliano il mese');
SELECT is(
  ARRAY(SELECT m.mese || '/' || m.fine_mese FROM script.fn_mesi_del_tratto(date '2023-12-20', date '2024-02-05') m)
  || ARRAY(SELECT m.mese || '/' || m.fine_mese FROM script.fn_mesi_del_tratto(date '2026-04-10', date '2026-04-10') m),
  ARRAY['2023-12-01/2023-12-31', '2024-01-01/2024-01-31', '2024-02-01/2024-02-29',
        '2026-04-01/2026-04-30'],
  '12b) fn_mesi_del_tratto: cambio d''anno col febbraio bisestile, e un giorno solo');

SELECT is(
  (SELECT count(*) FROM script.fn_mesi_del_tratto(NULL::date, date '2026-03-01'))
  + (SELECT count(*) FROM script.fn_mesi_del_tratto(date '2026-03-01', NULL::date))
  + (SELECT count(*) FROM script.fn_mesi_del_tratto(date '2026-03-01', date '2026-02-27')),
  0::bigint,
  '13) fn_mesi_del_tratto: estremo NULL o fine in un mese prima -> nessuna riga');

-- ============================================================
-- 14-15) fn_mesi_del_tratto identica alla serie che sostituisce, in due fusi
-- ============================================================
SET LOCAL TimeZone = 'UTC';
SELECT is(pg_temp.differenze_mesi_del_tratto(), '',
  '14) fn_mesi_del_tratto = generate_series(fn_mese_di(dal), al, 1 mese), sessione UTC');

SET LOCAL TimeZone = 'Europe/Rome';
SELECT is(pg_temp.differenze_mesi_del_tratto(), '',
  '15) fn_mesi_del_tratto = generate_series(fn_mese_di(dal), al, 1 mese), sessione Europe/Rome');

-- ============================================================
-- 16) La sede unica, sul catalogo vivo
-- ============================================================
-- ⭐ Il gemello vivo del cancello statico (guardrail_forme_changeset.py,
--   regola mesi-intervallo). Sommare mesi e' fn_mesi_dopo, i mesi di un
--   tratto fn_mesi_del_tratto: nessun altro oggetto scrive
--   make_interval(months => …) o un intervallo di mesi ('1 month',
--   '12 months', e la grafia stampata '1 mon'::interval). Anche su un
--   istante: il giorno aziendale e' fn_giorno_operativo, e da li' si passa
--   ai mesi.
-- ℹ️ La fine del mese ('1 mon -1 days') non e' questa regola: la guarda il 19
--   di script/test-mese-di-un-giorno-v1. Le funzioni si leggono da
--   pg_get_functiondef (copre le BEGIN ATOMIC), senza i commenti `--`; le
--   estensioni si escludono per dipendenza.
SELECT is(
  (WITH oggetti AS (
     SELECT n.nspname || '.' || p.proname AS nome,
            regexp_replace(pg_get_functiondef(p.oid), '--[^\n]*', '', 'g') AS testo
       FROM pg_proc p
       JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname NOT IN ('pg_catalog', 'information_schema', 'public', 'topology', 'pgagent')
        AND n.nspname NOT LIKE 'pg\_%'
        AND p.prokind IN ('f', 'p')
        AND NOT EXISTS (SELECT 1 FROM pg_depend d
                         WHERE d.classid = 'pg_proc'::regclass AND d.objid = p.oid AND d.deptype = 'e')
     UNION ALL
     SELECT n.nspname || '.' || c.relname, pg_get_viewdef(c.oid)
       FROM pg_class c
       JOIN pg_namespace n ON n.oid = c.relnamespace
      WHERE c.relkind IN ('v', 'm')
        AND n.nspname NOT IN ('pg_catalog', 'information_schema', 'public', 'topology', 'pgagent')
        AND n.nspname NOT LIKE 'pg\_%'
        AND NOT EXISTS (SELECT 1 FROM pg_depend d
                         WHERE d.classid = 'pg_class'::regclass AND d.objid = c.oid AND d.deptype = 'e'))
   SELECT coalesce(string_agg(nome, ', ' ORDER BY nome), '')
     FROM oggetti
    WHERE testo ~* 'make_interval\s*\([^)]*\mmonths\s*=>'
       OR testo ~* '''\s*[-+]?\d+\s*mon(th)?s?\s*'''),
  '',
  '16) nessuna vista e nessuna funzione somma mesi per conto suo: e'' script.fn_mesi_dopo');

SELECT * FROM finish();
ROLLBACK;
