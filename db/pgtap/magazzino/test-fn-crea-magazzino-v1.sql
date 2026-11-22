-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Il BB del magazzino e il builder che lo usa:
--   magazzino.fn_crea_magazzino       (20261018-40)
--   dbops.fn_pgtap_crea_magazzino     (20261018-41, sul verbo dal 20261122-09)
--   Brief: brief-db-processi-accensione-per-ambiente (§5-ter.2, 2b-1 lotto 7);
--   brief-db-magazzino-tutte-le-scritture-dal-verbo (Lotto 1).
--
-- ⭐ Il caso si COSTRUISCE: un operatore costruito in sessione, con TUTTO
--   sull'area magazzino (scelta del test), un indirizzo dal builder dei
--   dettagli. L'emittente atteso e' quello dell'operatore
--   (script.fn_pgtap_emittente_operatore).
-- ⚠️ Dal Lotto 1 i magazzini sono chiusi all'applicazione: il BB si prova dal
--   verbo magazzino.fn_aggiungi_magazzino, che lo chiama. L'emittente indicato
--   (p_emittente_fiscale_id) e' la strada del provisioning, non dell'app: il
--   verbo non lo prende, e il 2 prova che dai campi non passa.
--
-- Elenco test (plan 9):
--   forma
--    1) INVOKER
--   il caso felice
--    2) l'emittente fra i campi del verbo: E_CAMPO_NON_AMMESSO
--    3) l'emittente lo mette il trigger dalla sessione
--    4) i campi facoltativi: usa_ubicazioni e predefinito scritti
--    5) un magazzino nasce attivo
--   i rifiuti
--    6) attivo fra i campi: E_CAMPO_NON_AMMESSO
--    7) campi che non sono un oggetto: E_SCRIPT_CHIAMATA_NON_VALIDA
--   il builder
--    8) dbops.fn_pgtap_crea_magazzino scrive ancora il magazzino dell'operatore
--    9) ... e chiama il verbo, non il BB e non la tabella
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(9);

CREATE TEMP TABLE t_op AS SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM t_op)); END $ctx$;
INSERT INTO config.user_override_aree (auth_user_id, area_id, livello, motivo)
SELECT o.auth_user_id, af.id, 'TUTTO', 'pgTAP: il magazzino dal verbo'
  FROM t_op o, config.aree_funzionali af
 WHERE af.schema_db = 'magazzino';


CREATE OR REPLACE FUNCTION pg_temp.corpo(p regprocedure) RETURNS text
LANGUAGE sql AS $$
    SELECT regexp_replace(p2.prosrc, '--[^\n]*', '', 'g') FROM pg_proc p2 WHERE p2.oid = p
$$;

CREATE TEMP TABLE t_m AS
SELECT script.fn_pgtap_emittente_operatore()                       AS ef,
       dbops.fn_pgtap_crea_indirizzo_dettaglio('PGT-FCM')         AS ind;

CREATE TEMP TABLE t_g AS
SELECT magazzino.fn_aggiungi_magazzino('PGT-FCM-1', 'pgTAP crea magazzino 1', m.ind,
                                   '{"usa_ubicazioni": true, "predefinito": false}'::jsonb)       AS mag1,
       magazzino.fn_aggiungi_magazzino('PGT-FCM-2', 'pgTAP crea magazzino 2', m.ind)             AS mag2,
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
SELECT is(
    dbops.fn_pgtap_codice_errore($$SELECT magazzino.fn_aggiungi_magazzino('PGT-FCM-E', 'e',
        (SELECT ind FROM t_m), jsonb_build_object('emittente_fiscale_id', (SELECT ef FROM t_m)))$$),
    'E_CAMPO_NON_AMMESSO',
    '2. l''emittente fra i campi del verbo: E_CAMPO_NON_AMMESSO');

SELECT is((SELECT mg.emittente_fiscale_id FROM t_g g JOIN magazzino.magazzini mg ON mg.id = g.mag2),
          (SELECT ef FROM t_m),
          '3. l''emittente lo mette il trigger dalla sessione');

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
    dbops.fn_pgtap_codice_errore($$SELECT magazzino.fn_aggiungi_magazzino('PGT-FCM-X', 'x',
        (SELECT ind FROM t_m), '{"attivo": false}'::jsonb)$$),
    'E_CAMPO_NON_AMMESSO',
    '6. attivo fra i campi: E_CAMPO_NON_AMMESSO');

SELECT is(
    dbops.fn_pgtap_codice_errore($$SELECT magazzino.fn_aggiungi_magazzino('PGT-FCM-Y', 'y',
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
    pg_temp.corpo('dbops.fn_pgtap_crea_magazzino(character varying, boolean, jsonb)'::regprocedure) ~ 'magazzino\.fn_aggiungi_magazzino\('
    AND pg_temp.corpo('dbops.fn_pgtap_crea_magazzino(character varying, boolean, jsonb)'::regprocedure) !~ 'magazzino\.fn_crea_magazzino\('
    AND pg_temp.corpo('dbops.fn_pgtap_crea_magazzino(character varying, boolean, jsonb)'::regprocedure) !~* 'INSERT\s+INTO',
    '9. ... e chiama il verbo, non il BB e non la tabella');

SELECT * FROM finish();

ROLLBACK;
