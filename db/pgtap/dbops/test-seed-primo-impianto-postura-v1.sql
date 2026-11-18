-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: la POSTURA del seed di primo impianto e delle porte di manutenzione.
--   Brief: brief-db-seed-primo-impianto-non-si-riscrive (§16.11).
--   ChangeSet: 90_end/20261117-21 (forward), 90_end/ci_apply/20260205-41
--   (v_tabelle_sola_lettura_app), scripts/sql/provision_zeroerp.sql (fase post).
--
-- ⭐ E' il presidio che tiene allineate le TRE sedi della postura (linee-guida
--   §11.8): verde su dev col solo forward, rosso su un database ricostruito se
--   una delle altre due manca. Postura letta con has_*_privilege(ruolo, …), e
--   accanto il COMPORTAMENTO come app su una colonna che esiste.
--
-- Elenco test (plan 9):
--   1-3) dbops.seed_righe, dbops.porte_manutenzione_passaggi,
--        dbops.automazione_seed_primo_impianto: all'app SELECT si', nessuna scrittura
--   4-6) come app, UPDATE delle tre tabelle -> 42501
--     7) la funzione trigger e il building block della porta sono DEFINER, col
--        search_path bloccato
--     8) … e il loro proprietario e' quello delle tabelle che scrivono
--     9) le letture (argomenti, divergenze, ruolo e sessione del migratore) sono INVOKER
--
-- ⚠️ 4-6 provano l'APP: da owner sono rossi per costruzione.
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(9);

-- ============================================================
-- 1-6 Le tre tabelle in sola lettura per l'app
-- ============================================================
SELECT is(
    format('%s|%s', has_table_privilege('zeroerp_app', 'dbops.seed_righe', 'SELECT')::text,
                    has_table_privilege('zeroerp_app', 'dbops.seed_righe', 'INSERT, UPDATE, DELETE')::text),
    'true|false',
    '1) dbops.seed_righe: all''app SELECT si'', nessuna scrittura');

SELECT is(
    format('%s|%s', has_table_privilege('zeroerp_app', 'dbops.porte_manutenzione_passaggi', 'SELECT')::text,
                    has_table_privilege('zeroerp_app', 'dbops.porte_manutenzione_passaggi', 'INSERT, UPDATE, DELETE')::text),
    'true|false',
    '2) dbops.porte_manutenzione_passaggi: all''app SELECT si'', nessuna scrittura');

SELECT is(
    format('%s|%s', has_table_privilege('zeroerp_app', 'dbops.automazione_seed_primo_impianto', 'SELECT')::text,
                    has_table_privilege('zeroerp_app', 'dbops.automazione_seed_primo_impianto', 'INSERT, UPDATE, DELETE')::text),
    'true|false',
    '3) dbops.automazione_seed_primo_impianto: all''app SELECT si'', nessuna scrittura');

SELECT throws_ok(
    $$ UPDATE dbops.seed_righe SET riga_id = riga_id WHERE false $$,
    '42501', NULL,
    '4) come app, UPDATE di dbops.seed_righe: permesso negato');

SELECT throws_ok(
    $$ UPDATE dbops.porte_manutenzione_passaggi SET chiave = chiave WHERE false $$,
    '42501', NULL,
    '5) come app, UPDATE di dbops.porte_manutenzione_passaggi: permesso negato');

SELECT throws_ok(
    $$ UPDATE dbops.automazione_seed_primo_impianto SET enabled = enabled WHERE false $$,
    '42501', NULL,
    '6) come app, UPDATE di dbops.automazione_seed_primo_impianto: permesso negato');

-- ============================================================
-- 7-9 Chi scrive e' DEFINER, chi legge INVOKER
-- ============================================================
SELECT is(
    (SELECT string_agg(format('%s=%s:%s', p.proname, p.prosecdef::text, array_to_string(p.proconfig, ';')), ','
                       ORDER BY p.proname COLLATE "C")
       FROM pg_proc p
      WHERE p.oid IN ('script.trgfn_seed_primo_impianto()'::regprocedure,
                      'script.fn_porta_manutenzione_aperta(text,regclass,text,text)'::regprocedure)),
    'fn_porta_manutenzione_aperta=true:search_path=pg_catalog, pg_temp,'
    || 'trgfn_seed_primo_impianto=true:search_path=pg_catalog, pg_temp',
    '7) la funzione trigger e la porta sono DEFINER, col search_path bloccato');

SELECT is(
    (SELECT count(DISTINCT p.proowner)::int
       FROM pg_proc p
      WHERE p.oid IN ('script.trgfn_seed_primo_impianto()'::regprocedure,
                      'script.fn_porta_manutenzione_aperta(text,regclass,text,text)'::regprocedure)
        AND p.proowner = (SELECT c.relowner FROM pg_class c WHERE c.oid = 'dbops.seed_righe'::regclass)
        AND p.proowner = (SELECT c.relowner FROM pg_class c WHERE c.oid = 'dbops.porte_manutenzione_passaggi'::regclass)),
    1,
    '8) … e il loro proprietario e'' quello delle tabelle che scrivono');

SELECT is(
    (SELECT bool_or(p.prosecdef)
       FROM pg_proc p
      WHERE p.oid IN ('dbops.fn_seed_primo_impianto_argomenti(text[])'::regprocedure,
                      'dbops.fn_seed_primo_impianto_divergenze(text[])'::regprocedure,
                      'dbops.fn_ruolo_del_migratore(text)'::regprocedure,
                      'dbops.fn_sessione_del_migratore()'::regprocedure)),
    false,
    '9) le letture sono INVOKER');

SELECT * FROM finish();
ROLLBACK;
