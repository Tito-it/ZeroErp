-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Il BB del magazzino e il builder che lo usa:
--   magazzino.fn_crea_magazzino       (20261018-40)
--   dbops.fn_pgtap_crea_magazzino     (20261018-41)
--   Brief: brief-db-processi-accensione-per-ambiente (§5-ter.2, 2b-1 lotto 7).
--
-- ⭐ Il caso si COSTRUISCE: l'operatore pgTAP in sessione, un indirizzo dal
--   builder dei dettagli. L'emittente atteso e' quello dell'operatore
--   (script.fn_pgtap_emittente_operatore).
--
-- Elenco test (plan 9):
--   forma
--    1) INVOKER
--   il caso felice
--    2) emittente indicato: e' quello
--    3) emittente NULL: lo mette il trigger dalla sessione
--    4) i campi facoltativi: usa_ubicazioni e predefinito scritti
--    5) un magazzino nasce attivo
--   i rifiuti
--    6) attivo fra i campi: E_CAMPO_NON_AMMESSO
--    7) campi che non sono un oggetto: E_SCRIPT_CHIAMATA_NON_VALIDA
--   il builder
--    8) dbops.fn_pgtap_crea_magazzino scrive ancora il magazzino dell'operatore
--    9) ... e chiama il BB, non scrive la tabella
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(9);

CREATE OR REPLACE FUNCTION pg_temp.codice_errore(p_sql text) RETURNS text
LANGUAGE plpgsql AS $$
DECLARE v_c text;
BEGIN
    EXECUTE p_sql;
    RETURN NULL;
EXCEPTION WHEN SQLSTATE 'P0001' THEN
    GET STACKED DIAGNOSTICS v_c = CONSTRAINT_NAME;
    RETURN v_c;
END $$;

CREATE OR REPLACE FUNCTION pg_temp.corpo(p regprocedure) RETURNS text
LANGUAGE sql AS $$
    SELECT regexp_replace(p2.prosrc, '--[^\n]*', '', 'g') FROM pg_proc p2 WHERE p2.oid = p
$$;

CREATE TEMP TABLE t_m AS
SELECT script.fn_pgtap_emittente_operatore()                       AS ef,
       dbops.fn_pgtap_crea_indirizzo_dettaglio('PGT-FCM')         AS ind;

CREATE TEMP TABLE t_g AS
SELECT magazzino.fn_crea_magazzino('PGT-FCM-1', 'pgTAP crea magazzino 1', m.ind,
                                   '{"usa_ubicazioni": true, "predefinito": false}'::jsonb, m.ef) AS mag1,
       magazzino.fn_crea_magazzino('PGT-FCM-2', 'pgTAP crea magazzino 2', m.ind)                 AS mag2,
       dbops.fn_pgtap_crea_magazzino('PGT-FCM-3')                                                AS mag3
  FROM t_m m;

-- ============================================================
-- Forma
-- ============================================================
SELECT is(
    (SELECT p.prosecdef FROM pg_proc p
      WHERE p.oid = 'magazzino.fn_crea_magazzino(character varying, character varying, bigint, jsonb, bigint)'::regprocedure),
    false,
    '1. il BB e'' INVOKER');

-- ============================================================
-- Il caso felice
-- ============================================================
SELECT is((SELECT mg.emittente_fiscale_id FROM t_g g JOIN magazzino.magazzini mg ON mg.id = g.mag1),
          (SELECT ef FROM t_m),
          '2. emittente indicato: e'' quello');

SELECT is((SELECT mg.emittente_fiscale_id FROM t_g g JOIN magazzino.magazzini mg ON mg.id = g.mag2),
          (SELECT ef FROM t_m),
          '3. emittente NULL: lo mette il trigger dalla sessione');

SELECT is((SELECT format('%s|%s', mg.usa_ubicazioni, mg.predefinito)
             FROM t_g g JOIN magazzino.magazzini mg ON mg.id = g.mag1),
          't|f',
          '4. i campi facoltativi: usa_ubicazioni e predefinito scritti');

SELECT ok((SELECT mg.attivo FROM t_g g JOIN magazzino.magazzini mg ON mg.id = g.mag2),
          '5. un magazzino nasce attivo');

-- ============================================================
-- I rifiuti
-- ============================================================
SELECT is(
    pg_temp.codice_errore($$SELECT magazzino.fn_crea_magazzino('PGT-FCM-X', 'x',
        (SELECT ind FROM t_m), '{"attivo": false}'::jsonb)$$),
    'E_CAMPO_NON_AMMESSO',
    '6. attivo fra i campi: E_CAMPO_NON_AMMESSO');

SELECT is(
    pg_temp.codice_errore($$SELECT magazzino.fn_crea_magazzino('PGT-FCM-Y', 'y',
        (SELECT ind FROM t_m), '[]'::jsonb)$$),
    'E_SCRIPT_CHIAMATA_NON_VALIDA',
    '7. campi che non sono un oggetto: E_SCRIPT_CHIAMATA_NON_VALIDA');

-- ============================================================
-- Il builder
-- ============================================================
SELECT is((SELECT mg.emittente_fiscale_id FROM t_g g JOIN magazzino.magazzini mg ON mg.id = g.mag3),
          (SELECT ef FROM t_m),
          '8. dbops.fn_pgtap_crea_magazzino scrive ancora il magazzino dell''operatore');

SELECT ok(
    pg_temp.corpo('dbops.fn_pgtap_crea_magazzino(character varying, boolean)'::regprocedure) ~ 'magazzino\.fn_crea_magazzino\('
    AND pg_temp.corpo('dbops.fn_pgtap_crea_magazzino(character varying, boolean)'::regprocedure) !~* 'INSERT\s+INTO',
    '9. ... e chiama il BB, non scrive la tabella');

SELECT * FROM finish();

ROLLBACK;
