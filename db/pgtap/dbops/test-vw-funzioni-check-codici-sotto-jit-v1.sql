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
--       — changeSet 20261010-43
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
--   20261010-43 erano ~9.400 / ~10.500 / ~27.700: margine largo, e la stima
--   viene dalla STRUTTURA (pg_proc), non dai dati — uguale in CI.
--
-- Elenco test (plan 3):
--  1) dbops.vw_funzioni_check_codici: costo stimato sotto la soglia del JIT
--  2) dbops.vw_punti_primo_motivo (il rubinetto, la legge): idem
--  3) dbops.vw_punti_canale_campo (il presidio C2, la legge): idem
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: scattano al COMMIT, e qui il COMMIT non arriva mai.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: il test gira come gira l'applicazione (OPERATORE + RLS).
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(3);

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

SELECT finish();

ROLLBACK;
