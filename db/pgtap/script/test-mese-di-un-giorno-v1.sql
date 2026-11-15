-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: IL MESE DI UN GIORNO SI CALCOLA SUL CALENDARIO
--       script.fn_mese_di · script.fn_fine_mese_di
--       brief-db-mese-di-un-giorno §4.4 (20261114-82, -83)
-- ------------------------------------------------------------
-- Indice test (1..18)
--  1-2) le due funzioni esistono con la firma attesa
--  3-4) restituiscono date
--  5-6) sono IMMUTABLE: il calcolo non dipende dalla sessione
--  7-8) sono STRICT: il mese di nessun giorno e' nessun mese
--  9) fn_mese_di sui casi costruiti (primo, ultimo, 29 febbraio, fine anno)
-- 10) fn_fine_mese_di sui casi costruiti (28/29/30/31, bisestili del secolo)
-- 11) NULL -> NULL, tutte e due
-- 12-15) uguali al calcolo con date_trunc su ogni giorno 1899-2101,
--        sotto due fusi di sessione (UTC, Europe/Rome)
-- 16) il planner le espande: nel piano di una query non resta la chiamata
-- 17) nessuna vista e nessuna funzione degli schemi applicativi tronca con
--     date_trunc: il mese e la fine del mese hanno una sede sola
--     (brief-db-mese-di-un-giorno §4.4, giro 4: 20261115-30..-33)
-- 18) i CHECK «primo del mese» delle competenze poggiano su fn_mese_di
--     (D-1, 20261115-27..-29)
-- ------------------------------------------------------------
-- Scopo:
--  - il mese di un giorno e' aritmetica di calendario: niente istanti, niente
--    fuso. I valori attesi sono scritti a mano, non derivati da un'altra
--    formula, e coprono i confini che una formula sbagliata tradisce: il
--    giorno 1 e il 31, febbraio bisestile e no (anche il 1900 e il 2100, che
--    non lo sono, e il 2000, che lo e'), dicembre verso gennaio;
--  - le due funzioni sostituiscono date_trunc('month', <date>)::date e
--    (date_trunc('month', x) + interval '1 month - 1 day')::date: 12-15
--    provano che la sostituzione non cambia nessun risultato, su ogni giorno
--    di due secoli e mezzo, in due fusi di sessione diversi. date_trunc qui e'
--    l'ORACOLO della forma che si ritira, non un uso;
--  - 16 presidia la forma che le rende gratuite in una vista: una clausola SET
--    o un corpo plpgsql le renderebbe chiamate opache, e il test lo vede.
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: il test gira come gira l'applicazione.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(18);

-- Il piano di una query, come testo (forma di catalogo/test-distinta-alla-data-v1)
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

-- Le differenze col calcolo di oggi, su ogni giorno dell'intervallo, nel fuso
-- della sessione corrente. Vuoto = uguali.
CREATE FUNCTION pg_temp.differenze_mese()
 RETURNS text
 LANGUAGE sql
AS $f$
    SELECT coalesce(string_agg(g::date::text, ',' ORDER BY g), '')
      FROM generate_series(date '1899-01-01', date '2101-12-31', interval '1 day') g
     WHERE script.fn_mese_di(g::date) IS DISTINCT FROM date_trunc('month', g::date)::date;
$f$;

CREATE FUNCTION pg_temp.differenze_fine_mese()
 RETURNS text
 LANGUAGE sql
AS $f$
    SELECT coalesce(string_agg(g::date::text, ',' ORDER BY g), '')
      FROM generate_series(date '1899-01-01', date '2101-12-31', interval '1 day') g
     WHERE script.fn_fine_mese_di(g::date)
           IS DISTINCT FROM (date_trunc('month', g::date) + interval '1 month - 1 day')::date;
$f$;

-- ============================================================
-- 1-8) La forma
-- ============================================================
SELECT has_function('script', 'fn_mese_di', ARRAY['date'],
  '1) script.fn_mese_di(date) esiste');
SELECT has_function('script', 'fn_fine_mese_di', ARRAY['date'],
  '2) script.fn_fine_mese_di(date) esiste');

SELECT function_returns('script', 'fn_mese_di', ARRAY['date'], 'date',
  '3) fn_mese_di restituisce date');
SELECT function_returns('script', 'fn_fine_mese_di', ARRAY['date'], 'date',
  '4) fn_fine_mese_di restituisce date');

-- ⭐ IMMUTABLE e' cio' che il calcolo con date_trunc non poteva essere: e' la
--   prova che non passa dal fuso, e cio' che lo fa entrare in un CHECK.
SELECT volatility_is('script', 'fn_mese_di', ARRAY['date'], 'immutable',
  '5) fn_mese_di e'' IMMUTABLE');
SELECT volatility_is('script', 'fn_fine_mese_di', ARRAY['date'], 'immutable',
  '6) fn_fine_mese_di e'' IMMUTABLE');

-- STRICT e' il significato, non igiene (linee-guida-sql §13): il mese di un
-- giorno assente e' assente, come per date_trunc che sostituiscono.
SELECT is_strict('script', 'fn_mese_di', ARRAY['date'],
  '7) fn_mese_di e'' STRICT');
SELECT is_strict('script', 'fn_fine_mese_di', ARRAY['date'],
  '8) fn_fine_mese_di e'' STRICT');

-- ============================================================
-- 9-11) I casi costruiti
-- ============================================================
SELECT is(
  ARRAY[script.fn_mese_di(date '2026-01-01'),
        script.fn_mese_di(date '2026-01-31'),
        script.fn_mese_di(date '2026-02-28'),
        script.fn_mese_di(date '2024-02-29'),
        script.fn_mese_di(date '2026-04-30'),
        script.fn_mese_di(date '2026-12-31'),
        script.fn_mese_di(date '2027-01-01')],
  ARRAY[date '2026-01-01', date '2026-01-01', date '2026-02-01', date '2024-02-01',
        date '2026-04-01', date '2026-12-01', date '2027-01-01'],
  '9) fn_mese_di: primo, ultimo, febbraio, 29 febbraio, 30, fine anno, capodanno');

SELECT is(
  ARRAY[script.fn_fine_mese_di(date '2026-01-01'),
        script.fn_fine_mese_di(date '2026-02-15'),
        script.fn_fine_mese_di(date '2024-02-01'),
        script.fn_fine_mese_di(date '2026-04-30'),
        script.fn_fine_mese_di(date '2026-12-31'),
        script.fn_fine_mese_di(date '1900-02-10'),
        script.fn_fine_mese_di(date '2000-02-10'),
        script.fn_fine_mese_di(date '2100-02-10')],
  ARRAY[date '2026-01-31', date '2026-02-28', date '2024-02-29', date '2026-04-30',
        date '2026-12-31', date '1900-02-28', date '2000-02-29', date '2100-02-28'],
  '10) fn_fine_mese_di: 31, 28, 29, 30, dicembre, i tre febbrai di secolo');

SELECT is(
  ARRAY[script.fn_mese_di(NULL::date), script.fn_fine_mese_di(NULL::date)],
  ARRAY[NULL::date, NULL::date],
  '11) NULL -> NULL');

-- ============================================================
-- 12-15) Identiche al calcolo che sostituiscono, in due fusi
-- ============================================================
SET LOCAL TimeZone = 'UTC';
SELECT is(pg_temp.differenze_mese(), '',
  '12) fn_mese_di = date_trunc(''month'', <date>)::date su ogni giorno, sessione UTC');
SELECT is(pg_temp.differenze_fine_mese(), '',
  '13) fn_fine_mese_di = date_trunc + 1 mese - 1 giorno su ogni giorno, sessione UTC');

SET LOCAL TimeZone = 'Europe/Rome';
SELECT is(pg_temp.differenze_mese(), '',
  '14) fn_mese_di = date_trunc(''month'', <date>)::date su ogni giorno, sessione Europe/Rome');
SELECT is(pg_temp.differenze_fine_mese(), '',
  '15) fn_fine_mese_di = date_trunc + 1 mese - 1 giorno su ogni giorno, sessione Europe/Rome');

-- ============================================================
-- 16) Espanse dal planner
-- ============================================================
-- La colonna viene da generate_series: con un letterale il planner
-- calcolerebbe tutto in anticipo e il piano non direbbe niente.
SELECT ok(
  pg_temp.piano($q$
    SELECT script.fn_mese_di(g::date), script.fn_fine_mese_di(g::date)
      FROM generate_series(date '2026-01-01', date '2026-12-31', interval '1 day') g
  $q$) !~ 'fn_(fine_)?mese_di',
  '16) nel piano non resta la chiamata: le due funzioni sono espanse nel punto d''uso');

-- ============================================================
-- 17) La sede unica, sul catalogo vivo
-- ============================================================
-- ⭐ Il gemello vivo del cancello statico (guardrail_forme_changeset.py,
--   regola date-trunc), che guarda solo i changeSet nuovi: qui si legge
--   cio' che il database ESEGUE. Su un istante date_trunc tronca nel fuso
--   della sessione, su una data passa da un istante: in entrambi i casi la
--   sede e' un'altra (fn_mese_di, fn_fine_mese_di, fn_giorno_operativo).
-- ⚠️ Le funzioni si leggono da pg_get_functiondef, non da prosrc, che per
--   una BEGIN ATOMIC e' vuoto (linee-guida-sql §5c). I commenti `--` si
--   tolgono prima di cercare: fn_giorno_operativo nomina date_trunc nel
--   suo, per dire che lo sostituisce. Gli oggetti delle estensioni non sono
--   del progetto, e si escludono per dipendenza, non per nome.
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
    WHERE testo ~* '\mdate_trunc\s*\('),
  '',
  '17) nessuna vista e nessuna funzione tronca con date_trunc: il mese e'' script.fn_mese_di');

-- 18) La stessa regola dal lato del vincolo. Il comportamento lo provano i
--   test delle tabelle (vendite/test-attivita-fatturabili rifiuta la riga
--   fuori dal primo del mese); qui si legge che la regola e' quella del BB, e
--   che nessun CHECK di competenza la riscrive con EXTRACT(day).
SELECT is(
  -- Nomi dal catalogo, non da regclass::text, che dipende dal search_path.
  ARRAY(SELECT n.nspname || '.' || r.relname || '.' || c.conname
          FROM pg_constraint c
          JOIN pg_class r ON r.oid = c.conrelid
          JOIN pg_namespace n ON n.oid = r.relnamespace
         WHERE c.conname IN ('chk_attivita_competenza_mese_primo',
                             'chk_commesse_attivita_comp_mese_primo',
                             'chk_preventivi_competenza_mese_primo')
           AND pg_get_constraintdef(c.oid) ~ 'fn_mese_di\(competenza_mese\)'
           AND pg_get_constraintdef(c.oid) !~* 'extract'
         ORDER BY 1),
  ARRAY['vendite.attivita_fatturabili.chk_attivita_competenza_mese_primo',
        'vendite.commesse_attivita.chk_commesse_attivita_comp_mese_primo',
        'vendite.preventivi.chk_preventivi_competenza_mese_primo'],
  '18) i tre CHECK del primo del mese sono competenza_mese = fn_mese_di(competenza_mese)');

SELECT * FROM finish();
ROLLBACK;
