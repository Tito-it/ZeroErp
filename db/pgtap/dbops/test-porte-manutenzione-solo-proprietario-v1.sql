-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Copyright (C) 2026 Tid (Michele Carlo Titini)
--
-- Rilasciato sotto GNU AGPLv3 o versione successiva.
-- Vedi LICENSE.md per il testo completo della licenza.
-- ------------------------------------------------------------
--
-- Test: le porte di manutenzione si aprono solo dal proprietario
--   anagrafiche.trgfn_indirizzi_dettaglio_protect_update (porta 14)
--   config.trgfn_toponomastica_protect_update (porta 15)
--   dbops.fn_admin_merge_stradario · maintenance.proc_bump_toponomastica
--
-- ChangeSet: 20_code/anagrafiche/20261123-43, 20_code/config/20261123-44,
--            90_end/20261123-45, -46 (e le voci in v_fn_riservate del loop 20260205-41)
-- Brief: brief-db-porte-aperte-dalla-sola-guc, giro 1 (D-C b)
--
-- ⛔ IL DIFETTO CHE CHIUDE. Le due porte si aprivano con la sola GUC
--   (zeroerp.maintenance_indirizzi_dettaglio, zeroerp.maintenance_toponomastica):
--   l'app le accendeva con set_config e poi cambiava lo stradario_id di un
--   indirizzo, o la descrizione di un toponimo in uso, con un UPDATE diretto.
--   Il caso si COSTRUISCE: toponimo, stradario generale e via nascono qui,
--   l'indirizzo dal building block del dominio.
--
-- ⚠️ GIRA COME L'APPLICAZIONE (runner di default): il soggetto e' zeroerp_app,
--   cioe' chi la porta deve lasciare fuori. Il ramo del proprietario (GUC accesa
--   e proprietario: passa) lo provano i test che girano come owner e che usano
--   gli strumenti: dbops/test-fusioni-comune-stradario-v1 (7-8, la fusione
--   sposta gli indirizzi) e maintenance/test-bump-toponomastica-v1 (2, 5).
--
-- Elenco test (plan 14):
--   LA FORMA
--    1 : le due funzioni trigger sono INVOKER (da DEFINER il BB del
--        proprietario risponderebbe sempre si')
--   LA PORTA 14, GLI INDIRIZZI
--    2 : ⛔ GUC accesa dall'app, cambio di stradario_id: E_COLONNA_NON_MODIFICABILE
--    3 : ... e l'indirizzo resta sulla sua via
--    4 : con la GUC accesa, un UPDATE che non tocca stradario_id passa come prima
--   LA PORTA 15, LA TOPONOMASTICA
--    5 : ⛔ GUC accesa dall'app, descrizione di un toponimo in uso: E_COLONNA_NON_MODIFICABILE
--    6 : ... e la descrizione resta quella di prima
--   GLI STRUMENTI, RISERVATI AL PROPRIETARIO
--    7 : l'app non esegue fn_admin_merge_stradario
--    8 : PUBLIC non la esegue (l'=X di default e' revocato)
--    9 : l'app non esegue proc_bump_toponomastica
--   10 : PUBLIC non la esegue
--   11 : CALL proc_bump_toponomastica come app: 42501
--   12 : SELECT fn_admin_merge_stradario come app: 42501
--   LA GEMELLA (giro 1-bis, 90_end/20261123-46): non apre porte, ma e' uno strumento DBA
--   13 : l'app non esegue fn_admin_merge_comune
--   14 : PUBLIC non la esegue
--
-- Read-only: tutto dentro BEGIN;/ROLLBACK;.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(14);

-- ============================================================
-- Il mondo del test: un toponimo in uso (uno stradario generale lo usa), una
-- via nuova su quello stradario generale, un indirizzo su una via di seed.
-- ============================================================
CREATE TEMP TABLE tmp_fx AS
SELECT 'PGTAP PORTA TOPO ' || to_char(clock_timestamp(), 'YYYYMMDDHH24MISSUS') AS desc_topo,
       NULL::integer AS topo_id,
       NULL::integer AS sg_id,
       NULL::integer AS via_nuova_id,
       NULL::integer AS via_seed_id,
       NULL::bigint  AS indirizzo_id;

WITH ins AS (
    INSERT INTO config.toponomastica (descrizione, stato_id, attivo)
    SELECT f.desc_topo, (SELECT id FROM config.stati ORDER BY id LIMIT 1), true
      FROM tmp_fx f
    RETURNING id
)
UPDATE tmp_fx SET topo_id = (SELECT id FROM ins);

WITH ins AS (
    INSERT INTO config.stradario_generale (toponomastica_id, descrizione, descrizione_breve)
    SELECT f.topo_id, 'PGTAP STRADA PORTA', 'PGTAPPORTA'
      FROM tmp_fx f
    RETURNING id
)
UPDATE tmp_fx SET sg_id = (SELECT id FROM ins);

-- L'indirizzo dal building block delle fixture: nasce sulla prima via viva di seed.
UPDATE tmp_fx SET indirizzo_id = dbops.fn_pgtap_crea_indirizzo_dettaglio('porta 14');
UPDATE tmp_fx f SET via_seed_id = d.stradario_id
  FROM anagrafiche.indirizzi_dettaglio d
 WHERE d.id = f.indirizzo_id;

-- La via di destinazione: nuova, sullo stesso comune e codice postale, quindi
-- diversa per costruzione da quella dell'indirizzo.
WITH ins AS (
    INSERT INTO config.stradario (comune_id, stradario_generale_id, codice_postale_id, storicizza)
    SELECT s.comune_id, f.sg_id, s.codice_postale_id, false
      FROM tmp_fx f
      JOIN config.stradario s ON s.id = f.via_seed_id
    RETURNING id
)
UPDATE tmp_fx SET via_nuova_id = (SELECT id FROM ins);

-- ============================================================
-- LA FORMA
-- ============================================================
SELECT is(
    (SELECT count(*)::int
       FROM pg_proc p
      WHERE p.oid IN ('anagrafiche.trgfn_indirizzi_dettaglio_protect_update()'::regprocedure,
                      'config.trgfn_toponomastica_protect_update()'::regprocedure)
        AND NOT p.prosecdef),
    2,
    '1. le due funzioni trigger delle porte sono INVOKER: il BB del proprietario vede chi scrive');

-- ============================================================
-- LA PORTA 14, GLI INDIRIZZI
-- ============================================================
SELECT set_config('zeroerp.maintenance_indirizzi_dettaglio', 'on', true);

SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        'UPDATE anagrafiche.indirizzi_dettaglio SET stradario_id = %s WHERE id = %s',
        (SELECT via_nuova_id FROM tmp_fx), (SELECT indirizzo_id FROM tmp_fx))),
    'E_COLONNA_NON_MODIFICABILE',
    '2. GUC degli indirizzi accesa dall''app: il cambio di stradario_id e'' rifiutato');

SELECT is(
    (SELECT d.stradario_id FROM anagrafiche.indirizzi_dettaglio d WHERE d.id = (SELECT indirizzo_id FROM tmp_fx)),
    (SELECT via_seed_id FROM tmp_fx),
    '3. ... e l''indirizzo resta sulla sua via');

SELECT lives_ok(
    format('UPDATE anagrafiche.indirizzi_dettaglio SET altro = %L WHERE id = %s',
           'pgTAP porta 14', (SELECT indirizzo_id FROM tmp_fx)),
    '4. con la GUC accesa, un UPDATE che non tocca stradario_id passa come prima');

SELECT set_config('zeroerp.maintenance_indirizzi_dettaglio', '', true);

-- ============================================================
-- LA PORTA 15, LA TOPONOMASTICA
-- ============================================================
SELECT set_config('zeroerp.maintenance_toponomastica', 'on', true);

SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        'UPDATE config.toponomastica SET descrizione = %L WHERE id = %s',
        (SELECT desc_topo FROM tmp_fx) || ' MOD', (SELECT topo_id FROM tmp_fx))),
    'E_COLONNA_NON_MODIFICABILE',
    '5. GUC della toponomastica accesa dall''app: la descrizione di un toponimo in uso non cambia');

SELECT is(
    (SELECT t.descrizione::text FROM config.toponomastica t WHERE t.id = (SELECT topo_id FROM tmp_fx)),
    (SELECT desc_topo FROM tmp_fx),
    '6. ... e la descrizione resta quella di prima');

SELECT set_config('zeroerp.maintenance_toponomastica', '', true);

-- ============================================================
-- GLI STRUMENTI, RISERVATI AL PROPRIETARIO
-- ============================================================
SELECT is(has_function_privilege('zeroerp_app',
            'dbops.fn_admin_merge_stradario(integer, integer, character, date, text)', 'EXECUTE'), false,
          '7. fn_admin_merge_stradario: EXECUTE negato all''app');

SELECT is(
  EXISTS (
    SELECT 1
      FROM pg_proc p, aclexplode(COALESCE(p.proacl, acldefault('f', p.proowner))) a
     WHERE p.oid = 'dbops.fn_admin_merge_stradario(integer, integer, character, date, text)'::regprocedure
       AND a.grantee = 0 AND a.privilege_type = 'EXECUTE'),
  false,
  '8. fn_admin_merge_stradario: EXECUTE negato a PUBLIC');

SELECT is(has_function_privilege('zeroerp_app',
            'maintenance.proc_bump_toponomastica(integer, text)', 'EXECUTE'), false,
          '9. proc_bump_toponomastica: EXECUTE negato all''app');

SELECT is(
  EXISTS (
    SELECT 1
      FROM pg_proc p, aclexplode(COALESCE(p.proacl, acldefault('f', p.proowner))) a
     WHERE p.oid = 'maintenance.proc_bump_toponomastica(integer, text)'::regprocedure
       AND a.grantee = 0 AND a.privilege_type = 'EXECUTE'),
  false,
  '10. proc_bump_toponomastica: EXECUTE negato a PUBLIC');

SELECT throws_ok(
    format('CALL maintenance.proc_bump_toponomastica(%s, %L)',
           (SELECT topo_id FROM tmp_fx), 'PGTAP PORTA ALTRA'),
    '42501', NULL,
    '11. CALL proc_bump_toponomastica come app: 42501, prima di scrivere');

SELECT throws_ok(
    format('SELECT dbops.fn_admin_merge_stradario(%s, %s)',
           (SELECT via_seed_id FROM tmp_fx), (SELECT via_nuova_id FROM tmp_fx)),
    '42501', NULL,
    '12. fn_admin_merge_stradario come app: 42501, prima di scrivere');

-- ============================================================
-- LA GEMELLA: la fusione dei comuni
-- ============================================================
SELECT is(has_function_privilege('zeroerp_app',
            'dbops.fn_admin_merge_comune(integer, integer, character, date, text)', 'EXECUTE'), false,
          '13. fn_admin_merge_comune: EXECUTE negato all''app');

SELECT is(
  EXISTS (
    SELECT 1
      FROM pg_proc p, aclexplode(COALESCE(p.proacl, acldefault('f', p.proowner))) a
     WHERE p.oid = 'dbops.fn_admin_merge_comune(integer, integer, character, date, text)'::regprocedure
       AND a.grantee = 0 AND a.privilege_type = 'EXECUTE'),
  false,
  '14. fn_admin_merge_comune: EXECUTE negato a PUBLIC');

SELECT * FROM finish();
ROLLBACK;
