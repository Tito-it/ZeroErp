-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: dbops.fn_pgtap_valuta — una sede per «la prima valuta» delle fixture
-- Riferimento: brief-db-revisione-dbops D74 (giro 8, blocco 8c); changeSet
--   20261108-47 (il building block) e -48, -51, -53, -54, -56, -57, -58 (le copie
--   ritirate).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - la valuta delle radici della catena (cliente BA, emittente, gestore) e'
--     la prima di config.valute per id, da una sede sola;
--   - nessun'altra fixture la ricopia: i builder di documento la chiedono alla
--     catena del dominio (vendite.fn_get_valuta_id), le radici al building
--     block. Il presidio legge i corpi delle fixture (struttura, non dati).
--
-- Elenco test (plan 3):
--   1) la funzione esiste, senza argomenti
--   2) restituisce la prima valuta del catalogo per id
--   3) nessuna fixture dbops.fn_pgtap_* legge config.valute da se': c'e' solo la sede
-- ------------------------------------------------------------

BEGIN;
-- Contesto applicativo (preambolo, guardrail_pgtap_preambolo).
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(3);

SELECT has_function('dbops', 'fn_pgtap_valuta', ARRAY[]::text[],
    '1) dbops.fn_pgtap_valuta esiste, senza argomenti');

SELECT is(
    dbops.fn_pgtap_valuta(),
    (SELECT min(v.id) FROM config.valute v),
    '2) la prima valuta del catalogo per id');

SELECT is(
    (SELECT string_agg(p.proname, ', ' ORDER BY p.proname)
       FROM pg_catalog.pg_proc p
       JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'dbops'
        AND p.proname LIKE 'fn\_pgtap\_%'
        AND p.proname <> 'fn_pgtap_valuta'
        AND regexp_replace(p.prosrc, '--[^\n]*', '', 'g') ~* 'from\s+config\.valute'),
    NULL,
    '3) nessuna fixture ricopia la scelta della valuta: la sede e'' una');

SELECT * FROM finish();
ROLLBACK;
