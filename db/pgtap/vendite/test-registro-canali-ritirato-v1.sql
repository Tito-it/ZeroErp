-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: il registro dei canali di fatturazione e' ritirato, e il ritiro tiene
--   anche dopo ci_apply (le automazioni lavorano per pattern: una madre
--   sopravvissuta si vedrebbe ricreare la shadow).
-- ChangeSet: 00_schema/vendite/20261106-61, 80_data/changelog/20261106-62
-- Brief: brief-db-sorgente-documento-e-riga §7.2 lotto T, giro T.1 (D-10)
-- ------------------------------------------------------------
-- Indice test (plan 8):
--   1) vendite.documenti_fatturazione_canali non esiste
--   2) la sua shadow di storico non esiste e non e' rinata
--   3) vendite.trgfn_documenti_sync_canali non esiste
--   4) vendite.fn_set_documento_canale_stato non esiste
--   5) nessun trigger sulle quattro testate si chiama ancora *_sync_canali_*
--   6) nessuna funzione nomina piu' la tabella (nessuno ricomincia a scriverla)
--   7) nessuna riga per la tabella in dbops.storico_scope_policy
--   8) nessuna registrazione in config.storico_set_storicizza
--
-- ⭐ Perche' un test per un DROP: un IF EXISTS che non trova niente lascia il
--   changeSet verde e l'oggetto vivo. E il test gira in CI dopo ci_apply, cioe'
--   dopo il giro che potrebbe far rinascere la shadow.
-- ------------------------------------------------------------

BEGIN;

-- Il test legge solo il catalogo e due registri senza RLS: la veste
-- applicativa si dichiara comunque, e' il contratto del runner.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

-- Nessuna scrittura: la riga e' obbligatoria (guardrail_pgtap_preambolo) e innocua.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(8);

SELECT hasnt_table('vendite', 'documenti_fatturazione_canali',
    '1) vendite.documenti_fatturazione_canali non esiste');

SELECT hasnt_table('storico', 'documenti_fatturazione_canali',
    '2) storico.documenti_fatturazione_canali non esiste e non e'' rinata a ci_apply');

SELECT hasnt_function('vendite', 'trgfn_documenti_sync_canali', ARRAY[]::text[],
    '3) vendite.trgfn_documenti_sync_canali non esiste');

SELECT hasnt_function('vendite', 'fn_set_documento_canale_stato',
    '4) vendite.fn_set_documento_canale_stato non esiste, in nessuna firma');

SELECT is_empty(
    $$SELECT t.tgrelid::regclass::text || '.' || t.tgname
        FROM pg_trigger t
       WHERE NOT t.tgisinternal
         AND t.tgrelid IN ('vendite.preventivi'::regclass, 'vendite.ordini'::regclass,
                           'vendite.ddt'::regclass, 'vendite.contratti'::regclass)
         AND t.tgname ~ '_sync_canali_'$$,
    '5) nessun trigger sync_canali resta su preventivi, ordini, bolle e contratti');

SELECT is_empty(
    $$SELECT p.oid::regprocedure::text
        FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
       WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
         AND n.nspname !~ '^pg_temp'
         AND p.prokind IN ('f', 'p')
         AND pg_get_functiondef(p.oid) ~ 'documenti_fatturazione_canali'$$,
    '6) nessuna funzione nomina documenti_fatturazione_canali');

SELECT is(
    (SELECT count(*)::int FROM dbops.storico_scope_policy
      WHERE schema_tabella = 'vendite' AND nome_tabella = 'documenti_fatturazione_canali'),
    0,
    '7) nessuna riga per il registro in dbops.storico_scope_policy');

SELECT is(
    (SELECT count(*)::int FROM config.storico_set_storicizza
      WHERE table_name = 'vendite.documenti_fatturazione_canali'),
    0,
    '8) nessuna registrazione del registro in config.storico_set_storicizza');

SELECT * FROM finish();
ROLLBACK;
