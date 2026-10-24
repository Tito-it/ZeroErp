-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP per Zero ERP
-- Copyright (C) 2026 Tid (Michele Carlo Titini)
--
-- Rilasciato sotto GNU GPLv3 o versione successiva.
-- Vedi LICENSE.md per il testo completo della licenza.
-- ------------------------------------------------------------
--
-- Test: la risalita funzione -> check -> codici resta SOTTO LA SOGLIA DEL JIT
--       — changeSet 20261010-43, 20261012-25/-26
--
-- ⛔ IL PUNTO DI QUESTO FILE. Il prefiltro `prosrc LIKE '%fn\_check\_%'`
--   della CTE `funzioni` di dbops.vw_funzioni_check_codici e' una proprieta'
--   invisibile nei risultati, come ROWS sulle funzioni (20261008-21) e
--   security_invoker sulle viste: un CREATE OR REPLACE che lo perde restituisce
--   le STESSE righe, e nessun test di comportamento se ne accorge. Se ne
--   accorge solo il pianificatore: senza, la stima arrivava a ~637 milioni e
--   ogni lettura pagava ~1,1 s di compilazione JIT per ~110 ms di lavoro
--   (misura dbdev, come app, 2026-10-10).
--   ⇒ Si asserisce la proprieta' che conta — il costo STIMATO resta sotto
--   jit_above_cost — sulla vista e sui suoi due lettori, che ne ereditano la
--   stima. Non si pinna il testo del filtro: un'altra cura che tenga bassa la
--   stima andrebbe bene uguale.
--
-- ⚠️ La soglia e' il DEFAULT di PostgreSQL (100.000), scritta qui e non letta
--   da current_setting('jit_above_cost'): la proprieta' e' «la vista non chiede
--   il JIT su un'installazione normale», e una macchina col JIT spento (-1) o
--   la soglia alzata la renderebbe verde a vuoto. Al 2026-10-10 i costi dopo
--   20261010-43 erano ~9.400 / ~10.500 / ~27.700.
--
-- ⛔ rev 2026-10-12 — LA PREMESSA ERA SBAGLIATA. Qui c'era scritto che la stima
--   «viene dalla STRUTTURA (pg_proc), non dai dati — uguale in CI». Non e' cosi':
--   viene dalle STATISTICHE di pg_proc, e un autoanalyze le cambia. Su zeroerp_ci,
--   dopo l'autoanalyze delle 00:15 del 12-10, il prefiltro stimava 32 corpi (veri
--   170) e il test 3 e' andato rosso a ~192.000, il test 1 a ~92.000. Il verde del
--   10-10 si reggeva su una sottostima.
--   La cura (20261012-25/-26) toglie i moltiplicatori falsi: regexp_matches
--   (ROWS 10 dichiarato, vere 0,03-0,94) passa da dbops.fn_regexp_occorrenze
--   (ROWS 1), regexp_split_to_table (1.000) da unnest(regexp_split_to_array), e
--   l'estrazione delle deleghe e' materializzata. Dopo: ~11.600 / ~12.700 /
--   ~32.100, e con il prefiltro forzato a 594 corpi ~18.000 / ~19.100 / ~45.000.
--   ⇒ I test 1-3 restano la misura; i test 4 e 5 presidiano le due proprieta'
--   invisibili della cura, che un REPLACE potrebbe perdere senza cambiare una
--   riga.
--
-- Elenco test (plan 5):
--  1) dbops.vw_funzioni_check_codici: costo stimato sotto la soglia del JIT
--  2) dbops.vw_punti_primo_motivo (il rubinetto, la legge): idem
--  3) dbops.vw_punti_canale_campo (il presidio C2, la legge): idem
--  4) dbops.fn_regexp_occorrenze dichiara ROWS 1 e non si inlinea (plpgsql)
--  5) la vista non chiama direttamente regexp_matches ne' regexp_split_to_table
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: scattano al COMMIT, e qui il COMMIT non arriva mai.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: il test gira come gira l'applicazione (OPERATORE + RLS).
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(5);

-- Il costo totale stimato di `SELECT * FROM <vista>`, dal piano in JSON.
--   Nessuna esecuzione: EXPLAIN senza ANALYZE.
CREATE FUNCTION pg_temp.costo_stimato(p_vista regclass) RETURNS numeric
LANGUAGE plpgsql AS $fn$
DECLARE v_piano json;
BEGIN
    EXECUTE format('EXPLAIN (FORMAT JSON) SELECT * FROM %s', p_vista) INTO v_piano;
    RETURN (v_piano -> 0 -> 'Plan' ->> 'Total Cost')::numeric;
END $fn$;

SELECT cmp_ok(
  pg_temp.costo_stimato('dbops.vw_funzioni_check_codici'::regclass),
  '<', 100000::numeric,
  '1) vw_funzioni_check_codici: costo stimato sotto la soglia del JIT (un REPLACE senza il prefiltro lo riporta a ~637 milioni)');

SELECT cmp_ok(
  pg_temp.costo_stimato('dbops.vw_punti_primo_motivo'::regclass),
  '<', 100000::numeric,
  '2) vw_punti_primo_motivo: costo stimato sotto la soglia del JIT');

SELECT cmp_ok(
  pg_temp.costo_stimato('dbops.vw_punti_canale_campo'::regclass),
  '<', 100000::numeric,
  '3) vw_punti_canale_campo: costo stimato sotto la soglia del JIT');

-- 4) La cardinalita' dichiarata: ROWS 1, e plpgsql perche' una LANGUAGE sql
--    verrebbe inlineata e il ROWS ignorato.
SELECT is(
  (SELECT p.prorows::text || '|' || l.lanname || '|' || p.proretset::text
     FROM pg_proc p
     JOIN pg_namespace n ON n.oid = p.pronamespace
     JOIN pg_language l ON l.oid = p.prolang
    WHERE n.nspname = 'dbops' AND p.proname = 'fn_regexp_occorrenze'),
  '1|plpgsql|true',
  '4) dbops.fn_regexp_occorrenze: ROWS 1, plpgsql (non si inlinea), set-returning');

-- 5) La vista non torna alle funzioni di sistema a cardinalita' falsa (la
--    definizione ricostruita non ha commenti: si legge il codice).
SELECT ok(
  pg_get_viewdef('dbops.vw_funzioni_check_codici'::regclass) !~ '\m(regexp_matches|regexp_split_to_table)\s*\(',
  '5) vw_funzioni_check_codici: nessuna chiamata diretta a regexp_matches o regexp_split_to_table');

SELECT finish();

ROLLBACK;
