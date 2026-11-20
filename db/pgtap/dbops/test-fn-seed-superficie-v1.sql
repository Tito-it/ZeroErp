-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: dbops.fn_seed_superficie, il segno del seed di primo impianto su una
--   riga (nata_dal_seed, campi_del_software).
--   Brief: brief-db-seed-primo-impianto-non-si-riscrive (§16.15, QU3).
--   ChangeSet: 20261119-06 (il building block), -07 e -08 (le due viste della
--   posta riscritte sopra).
--
-- Gira come l'applicazione (runner di default): e' la veste di chi legge le
--   superfici. I soggetti: la colonna 3 della lista 1 (seed di 80_data,
--   contratto) e una lista creata qui, che e' dell'installazione.
--
-- Elenco test (plan 7):
--   1) una riga di seed: nata_dal_seed, con le colonne del software ricevute
--   2) una riga dell'installazione: non nata dal seed, campi vuoti
--   3) colonne NULL su una riga di seed: vuoto, mai NULL
--   4) una tabella non iscritta: non nata dal seed, campi vuoti
--   5) una riga sola, anche per un id che non esiste
--   6) le due viste della posta leggono il building block
--   7) una firma sola
-- ------------------------------------------------------------
BEGIN;
SET LOCAL lock_timeout = '5s';
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(7);

INSERT INTO ui.lista_definizione (codice, descrizione, schema_dati, attivo, user_insert)
VALUES ('tst.superficie.lista_dell_installazione', 'Lista creata dall''installazione', 'vendite', true, 'pgtap');

SELECT is(
    (SELECT s.nata_dal_seed::text || ':' || array_to_string(s.campi_del_software, ',')
       FROM dbops.fn_seed_superficie('ui.lista_colonna'::regclass, '3',
                                     (SELECT dbops.fn_seed_colonne_del_software('ui.lista_colonna'::regclass))) s),
    'true:' || array_to_string(dbops.fn_seed_colonne_del_software('ui.lista_colonna'::regclass), ','),
    '1) una riga di seed: nata_dal_seed, con le colonne del software ricevute');

SELECT is(
    (SELECT s.nata_dal_seed::text || ':' || cardinality(s.campi_del_software)
       FROM ui.lista_definizione ld
      CROSS JOIN LATERAL dbops.fn_seed_superficie('ui.lista_definizione'::regclass, ld.id::text,
                                     (SELECT dbops.fn_seed_colonne_del_software('ui.lista_definizione'::regclass))) s
      WHERE ld.codice = 'tst.superficie.lista_dell_installazione'),
    'false:0',
    '2) una riga dell''installazione: non nata dal seed, campi vuoti');

SELECT is(
    (SELECT s.campi_del_software
       FROM dbops.fn_seed_superficie('ui.lista_colonna'::regclass, '3', NULL) s),
    ARRAY[]::text[],
    '3) colonne NULL su una riga di seed: vuoto, mai NULL');

SELECT is(
    (SELECT s.nata_dal_seed::text || ':' || cardinality(s.campi_del_software)
       FROM dbops.fn_seed_superficie('config.email_log'::regclass, '1',
                                     (SELECT dbops.fn_seed_colonne_del_software('config.email_log'::regclass))) s),
    'false:0',
    '4) una tabella non iscritta: non nata dal seed, campi vuoti');

SELECT is(
    (SELECT count(*)::int FROM dbops.fn_seed_superficie('ui.lista_colonna'::regclass, '-1', NULL)),
    1,
    '5) una riga sola, anche per un id che non esiste');

SELECT is(
    (SELECT string_agg(c.relname, ',' ORDER BY c.relname)
       FROM pg_depend d
       JOIN pg_rewrite r ON r.oid = d.objid
       JOIN pg_class c ON c.oid = r.ev_class
      WHERE d.classid = 'pg_rewrite'::regclass
        AND d.refobjid = 'dbops.fn_seed_superficie(regclass, text, text[])'::regprocedure
        AND c.relname IN ('vw_email_account_seed', 'vw_email_template_seed')),
    'vw_email_account_seed,vw_email_template_seed',
    '6) le due viste della posta leggono il building block');

SELECT is(
    (SELECT count(*)::int FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'dbops' AND p.proname = 'fn_seed_superficie'),
    1,
    '7) una firma sola');

SELECT * FROM finish();
ROLLBACK;
