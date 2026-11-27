-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Copyright (C) 2026 Tid (Michele Carlo Titini)
--
-- Rilasciato sotto GNU AGPLv3 o versione successiva.
-- Vedi LICENSE.md per il testo completo della licenza.
-- ------------------------------------------------------------
-- rev 2026-11-27 (brief-db-porte-aperte-dalla-sola-guc §15, giro 10-quater): gli override utente sono in sola lettura per l'app; l'override LETTURA del caso 12, con la sua validita', lo scrive dbops.fn_pgtap_scrivi_override dal verbo. Attese invariate.
-- Test: le anagrafiche di magazzino sono in SOLA LETTURA per l'applicazione
--   (Lotto 1, brief-db-magazzino-tutte-le-scritture-dal-verbo, D-M1 = C,
--   D-M7 = b): magazzini, ubicazioni, lotti, seriali li scrivono i verbi
--   fn_aggiungi_* / fn_modifica_*; eventi dei seriali e note non hanno
--   scrittore applicativo. E i builder pgTAP, che passano dai verbi.
--   ChangeSet: 90_end/20261122-10, 20_code/dbops/20261122-09.
--
-- Elenco test (plan 14):
--   La sola lettura
--    1) all'applicazione SELECT si', INSERT, UPDATE e DELETE no, sulle quindici
--       tabelle (le note: la madre e le nove partizioni)
--    2) come applicazione, UPDATE di magazzini: 42501
--    3) come applicazione, INSERT in magazzini: 42501
--    4) come applicazione, UPDATE di ubicazioni: 42501
--    5) come applicazione, UPDATE di lotti: 42501
--    6) come applicazione, UPDATE di assets: 42501
--    7) come applicazione, UPDATE di eventi_assets: 42501
--    8) come applicazione, INSERT nella madre delle note: 42501
--    9) come applicazione, INSERT in una partizione delle note: 42501
--   I builder, come applicazione, con un operatore BLOCCATO
--   10) fn_pgtap_crea_magazzino: il magazzino nasce, dell'emittente
--       dell'operatore, con i campi di p_campi
--   11) ... e l'operatore torna senza override d'area
--   12) con un override LETTURA del test: il builder costruisce, e l'override
--       torna LETTURA con la sua validita'
--   13) ubicazione, lotto di magazzino e seriale nascono dai loro builder
--   14) i quattro builder chiamano il verbo fn_aggiungi_*, non il BB e non
--       la tabella
--
-- Scopo:
--  - 1 e' la terza sede della postura (linee-guida-sql §11.8): il forward
--    90_end/20261122-10, il loop 90_end/ci_apply/20260205-41 e il blocco
--    «POSTURA DICHIARATA» di scripts/sql/provision_zeroerp.sql devono dire la
--    stessa cosa, e su un database ricostruito da zero lo dice solo questo test.
--  - ⚠️ Gira come l'APPLICAZIONE (runner di default): 2-9 sono veri solo li'.
--  - ⚠️ 2-9 nominano colonne che esistono: su una colonna assente il parser
--    risponderebbe 42703, rosso per il motivo sbagliato.
--  - ⭐ 10-13 usano un operatore costruito (fn_pgtap_crea_emittente_operatore:
--    nessuna riga d'area, BLOCCATO ovunque): il builder deve aprire l'area per
--    la nascita e rimetterla com'era.
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(14);

CREATE OR REPLACE FUNCTION pg_temp.corpo(p regprocedure) RETURNS text
LANGUAGE sql AS $$
    SELECT regexp_replace(p2.prosrc, '--[^\n]*', '', 'g') FROM pg_proc p2 WHERE p2.oid = p
$$;

-- 1
SELECT is(
  (SELECT string_agg(t || ':' || p, ', ' ORDER BY t, p)
     FROM unnest(ARRAY[
              'magazzino.magazzini', 'magazzino.ubicazioni', 'magazzino.lotti',
              'magazzino.assets', 'magazzino.eventi_assets', 'magazzino.note',
              'magazzino.note_asset', 'magazzino.note_evento_asset',
              'magazzino.note_inventario', 'magazzino.note_inventario_riga',
              'magazzino.note_movimento', 'magazzino.note_rettifica',
              'magazzino.note_rettifica_riga', 'magazzino.note_trasferimento',
              'magazzino.note_trasferimento_riga']) t,
          unnest(ARRAY['SELECT', 'INSERT', 'UPDATE', 'DELETE']) p
    WHERE has_table_privilege('zeroerp_app', t, p) IS DISTINCT FROM (p = 'SELECT')),
  NULL,
  '1) anagrafiche di magazzino, eventi dei seriali e note: all''applicazione solo SELECT');

-- 2-9
SELECT throws_ok($$UPDATE magazzino.magazzini SET id = id WHERE false$$,
  '42501', NULL, '2) come applicazione, un UPDATE dei magazzini risponde 42501');
SELECT throws_ok($$INSERT INTO magazzino.magazzini (codice) SELECT 'PGT-X' WHERE false$$,
  '42501', NULL, '3) come applicazione, un INSERT nei magazzini risponde 42501');
SELECT throws_ok($$UPDATE magazzino.ubicazioni SET id = id WHERE false$$,
  '42501', NULL, '4) come applicazione, un UPDATE delle ubicazioni risponde 42501');
SELECT throws_ok($$UPDATE magazzino.lotti SET id = id WHERE false$$,
  '42501', NULL, '5) come applicazione, un UPDATE dei lotti risponde 42501');
SELECT throws_ok($$UPDATE magazzino.assets SET id = id WHERE false$$,
  '42501', NULL, '6) come applicazione, un UPDATE dei seriali risponde 42501');
SELECT throws_ok($$UPDATE magazzino.eventi_assets SET id = id WHERE false$$,
  '42501', NULL, '7) come applicazione, un UPDATE degli eventi dei seriali risponde 42501');
SELECT throws_ok($$INSERT INTO magazzino.note (testo) SELECT 'x' WHERE false$$,
  '42501', NULL, '8) come applicazione, un INSERT nella madre delle note risponde 42501');
SELECT throws_ok($$INSERT INTO magazzino.note_asset (testo) SELECT 'x' WHERE false$$,
  '42501', NULL, '9) come applicazione, un INSERT in una partizione delle note risponde 42501');

-- ============================================================
-- I builder: un operatore costruito, BLOCCATO ovunque
-- ============================================================
CREATE TEMP TABLE _op AS SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _op)); END $ctx$;

CREATE TEMP TABLE _f AS
SELECT dbops.fn_pgtap_crea_magazzino('PGT-AMS-M1', true, '{"predefinito": true}'::jsonb) AS mag,
       dbops.fn_pgtap_crea_articolo('PGT-AMS-LOTTI',   true, true,  false)              AS art_lotti,
       dbops.fn_pgtap_crea_articolo('PGT-AMS-SERIALE', true, false, true)               AS art_ser;

-- 10
SELECT is(
  (SELECT format('%s|%s|%s', mg.emittente_fiscale_id = o.emittente_fiscale_id, mg.usa_ubicazioni, mg.predefinito)
     FROM _f f JOIN magazzino.magazzini mg ON mg.id = f.mag, _op o),
  't|t|t',
  '10) fn_pgtap_crea_magazzino: il magazzino nasce, dell''emittente dell''operatore, coi campi di p_campi');

-- 11
SELECT is(
  (SELECT count(*)::int FROM config.user_override_aree uoa JOIN _op o ON o.auth_user_id = uoa.auth_user_id),
  0,
  '11) ... e l''operatore torna senza override d''area');

-- 12
SELECT dbops.fn_pgtap_scrivi_override(
           'config.user_override_aree', o.auth_user_id,
           jsonb_build_object('area_id', af.id),
           jsonb_build_object('livello', 'LETTURA', 'motivo', 'pgTAP: livello del test',
                              'valido_dal', DATE '2026-01-01', 'valido_al', DATE '2099-12-31'))
  FROM _op o, config.aree_funzionali af
 WHERE af.schema_db = 'magazzino';

CREATE TEMP TABLE _f2 AS SELECT dbops.fn_pgtap_crea_magazzino('PGT-AMS-M2') AS mag;

SELECT is(
  (SELECT format('%s|%s|%s|%s', (SELECT count(*) FROM _f2 WHERE mag IS NOT NULL),
                 uoa.livello, uoa.valido_dal, uoa.valido_al)
     FROM config.user_override_aree uoa
     JOIN _op o ON o.auth_user_id = uoa.auth_user_id
     JOIN config.aree_funzionali af ON af.id = uoa.area_id AND af.schema_db = 'magazzino'),
  '1|LETTURA|2026-01-01|2099-12-31',
  '12) con un override LETTURA del test: il builder costruisce, e l''override torna com''era');

-- 13
CREATE TEMP TABLE _f3 AS
SELECT dbops.fn_pgtap_crea_ubicazione(f.mag, 'PGT-AMS-U1', '{"corsia": "A"}'::jsonb) AS ubi,
       dbops.fn_pgtap_crea_lotto_di_magazzino(f.art_lotti, 'PGT-AMS-L1')             AS lotto,
       dbops.fn_pgtap_crea_asset(f.art_ser, 'PGT-AMS-SN1')                           AS asset
  FROM _f f;

SELECT is(
  (SELECT format('%s|%s|%s',
                 (SELECT u.corsia FROM magazzino.ubicazioni u WHERE u.id = x.ubi),
                 (SELECT l.data_arrivo = script.fn_data_operativa() FROM magazzino.lotti l WHERE l.id = x.lotto),
                 (SELECT a.emittente_fiscale_id = o.emittente_fiscale_id FROM magazzino.assets a WHERE a.id = x.asset))
     FROM _f3 x, _op o),
  'A|t|t',
  '13) ubicazione, lotto di magazzino e seriale nascono dai loro builder');

-- 14
SELECT is(
  (SELECT string_agg(b.nome, ', ' ORDER BY b.nome)
     FROM (VALUES ('fn_pgtap_crea_magazzino',          'dbops.fn_pgtap_crea_magazzino(character varying, boolean, jsonb)',               'fn_aggiungi_magazzino'),
                  ('fn_pgtap_crea_ubicazione',         'dbops.fn_pgtap_crea_ubicazione(bigint, character varying, jsonb, bigint)',      'fn_aggiungi_ubicazione'),
                  ('fn_pgtap_crea_lotto_di_magazzino', 'dbops.fn_pgtap_crea_lotto_di_magazzino(uuid, character varying, date, jsonb)', 'fn_aggiungi_lotto'),
                  ('fn_pgtap_crea_asset',              'dbops.fn_pgtap_crea_asset(uuid, character varying, jsonb, bigint, bigint)',     'fn_aggiungi_asset'))
          AS b(nome, firma, verbo)
    WHERE pg_temp.corpo(b.firma::regprocedure) !~ ('magazzino\.' || b.verbo || '\(')
       OR pg_temp.corpo(b.firma::regprocedure) ~  'magazzino\.fn_crea_'
       OR pg_temp.corpo(b.firma::regprocedure) ~* 'INSERT\s+INTO\s+magazzino\.'),
  NULL,
  '14) i quattro builder chiamano il verbo fn_aggiungi_*, non il BB e non la tabella');

SELECT * FROM finish();
ROLLBACK;
