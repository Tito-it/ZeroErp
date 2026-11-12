-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: registri delle automazioni — un nome che manca e' NULL, mai ''
-- Riferimento: brief-db-nullvalue-vuoto-cinque-mirror; changeSet
--   90_end/20261112-37 (name_template di dbops.automation_rules_tbl) e
--   90_end/20261112-38 (trigger_name di dbops.automation_delete_block), mirror
--   80_data/20250918-02 e 80_data/20260123-11 (nullValue "NULL").
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - una regola senza template (CLEANUP_*, STORICO_PROVISION) ha name_template
--     NULL: la stringa vuota, anche di soli spazi, e' rifiutata dal vincolo
--     della colonna, non da chk_automation_rules_tbl_regola_valida, che per una
--     CLEANUP_AT non chiede il template;
--   - un blocco di cancellazione che usa il template ha trigger_name NULL: la
--     stringa vuota e' rifiutata; un nome vero passa;
--   - il seed non scrive la stringa vuota su nessuna delle due colonne.
--   Le righe di prova si costruiscono qui, su tabelle bersaglio inventate: il
--   giro delle automazioni non gira, il test resta nella transazione.
--   ⚠️ Il test 8 prova il RISULTATO, non chi lo produce: anche la conversione
--     dei due changeSet porta a NULL le stringhe vuote. Che le scriva il loader
--     col nullValue nuovo si prova col render offline dei mirror (brief, §4).
--
-- Elenco test (plan 8):
--   1) i due vincoli esistono
--   2) name_template '' su una CLEANUP_AT: rifiutato dal vincolo della colonna
--   3) name_template di soli spazi: vale come vuoto
--   4) name_template NULL su una CLEANUP_AT: la regola entra
--   5) trigger_name '': rifiutato dal vincolo della colonna
--   6) trigger_name NULL: il blocco entra
--   7) trigger_name con un nome vero: il blocco entra
--   8) il seed: nessuna stringa vuota sulle due colonne
-- ------------------------------------------------------------

BEGIN;
-- Contesto applicativo (preambolo, guardrail_pgtap_preambolo).
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(8);

-- Una regola di scadenza di prova con il template indicato.
CREATE OR REPLACE FUNCTION pg_temp.regola(p_n integer, p_nome text)
RETURNS text LANGUAGE sql AS $f$
  SELECT format(
    'INSERT INTO dbops.automation_rules_tbl '
    '  (enabled, rule_type, target_schema, target_table, exec_mode, name_template, params, priority, note) '
    'VALUES (true, ''CLEANUP_AT'', ''pgtap_nomi'', %1$L, ''AUTO'', %2$L, ''{"ttl_days": 30}'', 999, ''pgTAP'')',
    'pgtap_t' || p_n, p_nome);
$f$;

-- Un blocco di cancellazione di prova con il nome indicato.
CREATE OR REPLACE FUNCTION pg_temp.blocco(p_n integer, p_nome text)
RETURNS text LANGUAGE sql AS $f$
  SELECT format(
    'INSERT INTO dbops.automation_delete_block (schema_name, table_name, guc_key, enabled, trigger_name) '
    'VALUES (''pgtap_nomi'', %1$L, ''zeroerp.pgtap_nomi'', true, %2$L)',
    'pgtap_t' || p_n, p_nome);
$f$;

SELECT is(
  (SELECT count(*)::int FROM pg_catalog.pg_constraint
    WHERE contype = 'c'
      AND (   (conrelid = 'dbops.automation_rules_tbl'::regclass
               AND conname = 'chk_automation_rules_tbl_name_template_non_vuoto')
           OR (conrelid = 'dbops.automation_delete_block'::regclass
               AND conname = 'chk_automation_delete_block_trigger_name_non_vuoto'))),
  2,
  '1) i due vincoli esistono');

SELECT is(dbops.fn_pgtap_codice_errore(pg_temp.regola(1, '')),
          'chk_automation_rules_tbl_name_template_non_vuoto',
          '2) name_template vuoto su una CLEANUP_AT: rifiutato dal vincolo della colonna');

SELECT is(dbops.fn_pgtap_codice_errore(pg_temp.regola(2, '   ')),
          'chk_automation_rules_tbl_name_template_non_vuoto',
          '3) name_template di soli spazi: vale come vuoto');

SELECT is(dbops.fn_pgtap_codice_errore(pg_temp.regola(3, NULL)),
          NULL,
          '4) name_template NULL su una CLEANUP_AT: la regola entra');

SELECT is(dbops.fn_pgtap_codice_errore(pg_temp.blocco(1, '')),
          'chk_automation_delete_block_trigger_name_non_vuoto',
          '5) trigger_name vuoto: rifiutato dal vincolo della colonna');

SELECT is(dbops.fn_pgtap_codice_errore(pg_temp.blocco(2, NULL)),
          NULL,
          '6) trigger_name NULL: il blocco entra');

SELECT is(dbops.fn_pgtap_codice_errore(pg_temp.blocco(3, 'trg_pgtap_t3_blocco_dlt')),
          NULL,
          '7) trigger_name con un nome vero: il blocco entra');

-- Il seed e' contratto (80_data): lo si legge, non si conta una popolazione.
SELECT is(
  (SELECT count(*) FROM dbops.automation_rules_tbl r WHERE r.name_template = '')::int
  + (SELECT count(*) FROM dbops.automation_delete_block b WHERE b.trigger_name = '')::int,
  0,
  '8) il seed: nessuna stringa vuota su name_template e trigger_name');

SELECT * FROM finish();
ROLLBACK;
