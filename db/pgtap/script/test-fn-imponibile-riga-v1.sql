-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: script.fn_imponibile_riga — la sede UNICA dell'imponibile di una riga
--   di documento: quantita' x prezzo x (1 - sconto/100), a precisione piena.
--   Brief: brief-db-liste-righe-documento §8.8 (D-8.8).
--   changeSet: 20260928-16 (la funzione), 20260928-17 -> -26 (i consumatori).
--
-- ⭐ SEED-AGNOSTICO: la funzione e' PURA, prende i valori e non legge tabelle.
--   Qui non serve nessuna fixture, e i casi si COSTRUISCONO: e' la ragione per
--   cui la sede unica prende i valori e non l'id della riga.
--
-- ⛔ COSA PRESIDIA DAVVERO. Non «la funzione moltiplica»: presidia i tre punti
--   in cui una copia scritta a mano sbaglia in SILENZIO —
--     · prezzo o quantita' NULL: deve uscire NULL, non zero. Uno zero sarebbe
--       indistinguibile da una riga che vale zero (V-2/DEC-6 del DDT);
--     · sconto NULL: e' «nessuno sconto», non NULL;
--     · nessun arrotondamento: e' politica di chi consuma (round a 2 per
--       mostrare, somma piena per il riepilogo IVA, regola configurata per la
--       fattura). Una funzione che arrotondasse sposterebbe i riepiloghi.
--
-- ⚠️ I test 13-15 guardano i CONSUMATORI, e va detto cosa NON provano: che le
--   viste e le funzioni chiamino la sede unica. Se la funzione fosse sbagliata,
--   i consumatori sbaglierebbero con lei e quei test resterebbero verdi: la
--   correttezza della formula sta nei test 5-12, non li'.
--   Il 15 e' un presidio sul TESTO (regex sulla formula scritta a mano): prende
--   la ricopiatura della forma che c'era, non una riscrittura con altri nomi o
--   un altro ordine. Il perimetro e' dichiarato: viste e funzioni di `vendite`
--   e `script`.
--
-- Indice test (1..15):
--    1) la funzione esiste con la firma attesa
--    2) IMMUTABLE (il pianificatore la inlinea nelle viste)
--    3) ⭐ NON e' STRICT — lo sconto NULL e' un caso normale
--    4) PARALLEL SAFE
--    5) caso pieno
--    6) sconto NULL -> nessuno sconto
--    7) sconto zero
--    8) sconto 100 -> zero (un valore vero, non NULL)
--    9) ⛔ prezzo NULL -> NULL, non zero
--   10) ⛔ quantita' NULL -> NULL, non zero
--   11) precisione PIENA: nessun arrotondamento
--   12) quantita' negativa: il segno passa (rettifiche)
--   13) le otto viste che la usano dipendono da lei
--   14) le due funzioni plpgsql che la usano la chiamano
--   15) nessuna copia della formula a mano rimasta in vendite/script
-- ------------------------------------------------------------

BEGIN;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli
--   (il COMMIT non arriva mai). Brief: brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: il test gira come l'applicazione. La funzione non
-- legge tabelle e la RLS qui non morde niente, ma il contesto si mette lo
-- stesso: un file che fa eccezione insegna che l'eccezione si puo' fare.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(15);

-- ---- 1..4: la forma della funzione ---------------------------------------
SELECT has_function('script', 'fn_imponibile_riga',
                    ARRAY['numeric', 'numeric', 'numeric'],
                    '1) script.fn_imponibile_riga(numeric, numeric, numeric) esiste');

SELECT is(
    (SELECT provolatile::text FROM pg_proc
      WHERE oid = 'script.fn_imponibile_riga(numeric,numeric,numeric)'::regprocedure),
    'i', '2) IMMUTABLE: le viste la inlineano invece di chiamarla per riga');

-- ⭐ STRICT tornerebbe NULL appena UN parametro e' NULL, senza entrare nel
--    corpo: lo sconto NULL — riga senza sconto — darebbe NULL invece
--    dell'imponibile pieno. Nessun altro test di forma se ne accorgerebbe.
SELECT is(
    (SELECT proisstrict FROM pg_proc
      WHERE oid = 'script.fn_imponibile_riga(numeric,numeric,numeric)'::regprocedure),
    false, '3) NON e'' STRICT: sconto NULL deve dare l''imponibile pieno');

SELECT is(
    (SELECT proparallel::text FROM pg_proc
      WHERE oid = 'script.fn_imponibile_riga(numeric,numeric,numeric)'::regprocedure),
    's', '4) PARALLEL SAFE');

-- ---- 5..12: la formula -----------------------------------------------------
SELECT is(script.fn_imponibile_riga(2, 10, 10), 18::numeric,
          '5) 2 x 10 con sconto 10% = 18');

SELECT is(script.fn_imponibile_riga(2, 10, NULL), 20::numeric,
          '6) sconto NULL = nessuno sconto');

SELECT is(script.fn_imponibile_riga(2, 10, 0), 20::numeric,
          '7) sconto zero');

-- Uno sconto del 100% e' un valore VERO: la riga vale zero, e zero e' il fatto.
SELECT is(script.fn_imponibile_riga(3, 7.5, 100), 0::numeric,
          '8) sconto 100% = zero, non NULL');

-- ⛔ Il caso per cui la sede unica esiste: la riga senza prezzo (DDT di solo
--    trasporto) NON vale zero, non ha valore.
SELECT is(script.fn_imponibile_riga(5, NULL, 10), NULL::numeric,
          '9) prezzo NULL -> NULL, mai uno zero finto');

SELECT is(script.fn_imponibile_riga(NULL, 10, 10), NULL::numeric,
          '10) quantita'' NULL -> NULL');

-- ⚠️ 1 x 1 x (1 - 33.3333/100) = 0.666667 esatto. Con un round a 2 uscirebbe
--    0.67: e sommato su molte righe sposterebbe il riepilogo IVA, che somma il
--    pieno e arrotonda la somma.
SELECT is(script.fn_imponibile_riga(1, 1, 33.3333), 0.666667::numeric,
          '11) precisione piena: nessun arrotondamento');

SELECT is(script.fn_imponibile_riga(-2, 10, 10), -18::numeric,
          '12) quantita'' negativa: il segno passa');

-- ---- 13..15: i consumatori -------------------------------------------------
-- Le viste registrano in pg_depend la funzione che chiamano (tramite la loro
-- regola di riscrittura): e' il catalogo a dirlo, non il testo.
SELECT set_eq(
    $$SELECT DISTINCT n.nspname || '.' || c.relname
        FROM pg_depend d
        JOIN pg_rewrite rw ON rw.oid = d.objid
        JOIN pg_class c ON c.oid = rw.ev_class
        JOIN pg_namespace n ON n.oid = c.relnamespace
       WHERE d.classid = 'pg_rewrite'::regclass
         AND d.refobjid = 'script.fn_imponibile_riga(numeric,numeric,numeric)'::regprocedure$$,
    ARRAY['vendite.vw_preventivi_righe_dettaglio',
          'vendite.vw_ordini_righe_dettaglio',
          'vendite.vw_ddt_righe_dettaglio',
          'vendite.vw_ordini_righe_iva_base',
          'vendite.vw_ddt_righe_iva_base',
          'vendite.vw_dash_fatturazione_preventivi',
          'vendite.vw_dash_fatturazione_ordini',
          'vendite.vw_dash_fatturazione_ddt'],
    '13) le otto viste che calcolavano l''imponibile a mano ora dipendono dalla sede unica');

-- ⚠️ Una plpgsql non registra dipendenze: qui si guarda il testo, commenti
--    esclusi, cercando la CHIAMATA (nome seguito da parentesi).
SELECT is(
    (SELECT count(*)::integer FROM pg_proc p
      WHERE p.oid IN ('vendite.fn_ricalcola_riepilogo_iva_preventivo(bigint)'::regprocedure,
                      'vendite.trgfn_fatture_righe_importo()'::regprocedure)
        AND regexp_replace(p.prosrc, '--[^\n]*', '', 'g') ~ 'script\.fn_imponibile_riga\s*\('),
    2,
    '14) ricalcolo IVA del preventivo e imponibile di fattura chiamano la sede unica');

-- ⛔ La regressione che si vuole vedere: qualcuno RICOPIA la formula invece di
--    chiamare la funzione. La regex prende la forma che c'era (lo sconto
--    COALESCE a zero diviso cento, con o senza cast, anche come 100.0).
SELECT is(
    (SELECT count(*)::integer FROM (
        SELECT pg_get_viewdef(c.oid) AS testo
          FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
         WHERE n.nspname IN ('vendite', 'script') AND c.relkind IN ('v', 'm')
        UNION ALL
        SELECT regexp_replace(p.prosrc, '--[^\n]*', '', 'g')
          FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
         WHERE n.nspname IN ('vendite', 'script')
           AND p.oid <> 'script.fn_imponibile_riga(numeric,numeric,numeric)'::regprocedure
    ) x
     WHERE testo ~ 'sconto_percentuale\s*,\s*(\(0\)::numeric|0::numeric|0)\s*\)\s*/\s*(\(100\)::numeric|100::numeric|100\.0|100)'),
    0,
    '15) nessuna copia a mano della formula dell''imponibile in vendite/script');

SELECT * FROM finish();
ROLLBACK;
