-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- pgtap-runner: owner
-- pgtap-runner-motivo: il test fa DDL (una madre in config, la sua gemella in
--   storico, un trigger montato a mano) e cambia la strategia della regola
--   STORICO: e' il percorso delle migrazioni e di ci_apply, non
--   dell'applicazione.
--
-- Test: il runner storico riconosce il trigger generico per FUNZIONE
--   dbops.fn_run_automations_storico · script.trgfn_storico_generic
-- ChangeSet: 20261103-57 · Brief: brief-db-revisione-maintenance D3, §10.5 R2
--
-- Elenco test (plan 5):
--  1) la funzione generica di storicizzazione esiste col nome vivo
--  2) ⛔ nessuna funzione PL/pgSQL nomina script.trgfn_upd_dlt_storico_generic,
--     il nome che aveva prima: chi lo cerca non trova mai il trigger
--  3) ⭐ BY_FUNCTION: una madre che ha gia' il trigger generico con un altro
--     nome non ne riceve un secondo
--  4) ⭐ BOTH (la strategia del seed): idem
--  5) ✅ BY_FUNCTION su una madre senza trigger: il trigger nasce (i test 3-4
--     non sono veri perche' la regola non scatta)
--
-- ⭐ IL CASO DI D3. Col nome ritirato il controllo per funzione non trovava
--   mai niente: con BY_FUNCTION, e con BOTH quando il nome non coincide col
--   template, il runner montava un secondo trigger di storico accanto a
--   quello che c'era, e ogni UPDATE scriveva due snapshot. I test 3-4 contano
--   i trigger generici sulla madre: due e' il difetto.
--
-- ⚠️ La gemella e' una copia della FORMA di storico.parameters (LIKE, la sua
--   FK si chiama parameters_id), come in test-storico-automazione-colonna-fk-v1:
--   INCLUDING IDENTITY perche' la forma di `id` diverge fra le macchine.
-- ⚠️ Il runner scorre tutto lo schema config: le altre madri hanno gia' il
--   trigger e vengono saltate.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(5);

-- ============================================================
-- 1-2. Il nome
-- ============================================================
SELECT has_function(
    'script', 'trgfn_storico_generic',
    'La funzione generica di storicizzazione esiste col nome vivo'
);

SELECT is(
    (SELECT string_agg(n.nspname || '.' || p.proname, ', ' ORDER BY 1)
       FROM pg_proc p
       JOIN pg_namespace n ON n.oid = p.pronamespace
       JOIN pg_language l ON l.oid = p.prolang
      WHERE l.lanname = 'plpgsql'
        AND p.prosrc LIKE '%trgfn\_upd\_dlt\_storico\_generic%'),
    NULL,
    'Nessuna funzione nomina il trigger di storico col nome ritirato'
);

-- ============================================================
-- Fixture: una madre col trigger generico montato a mano, con un nome che
-- non e' quello del template
-- ============================================================
CREATE TABLE config.pgtap_sto_byfn (
    id         bigint PRIMARY KEY,
    nota       text,
    storicizza boolean DEFAULT true
);
CREATE TABLE storico.pgtap_sto_byfn
    (LIKE storico.parameters INCLUDING DEFAULTS INCLUDING IDENTITY INCLUDING CONSTRAINTS);
ALTER TABLE storico.pgtap_sto_byfn RENAME COLUMN parameters_id TO pgtap_sto_byfn_id;

CREATE TRIGGER trg_pgtap_sto_byfn_a_mano
BEFORE UPDATE OR DELETE ON config.pgtap_sto_byfn
FOR EACH ROW
EXECUTE FUNCTION script.trgfn_storico_generic('pgtap_sto_byfn_id');

-- ============================================================
-- 3. BY_FUNCTION
-- ============================================================
UPDATE dbops.automation_rules_tbl
   SET existence_strategy = 'BY_FUNCTION'
 WHERE enabled AND upper(btrim(rule_type)) = 'STORICO';

SELECT dbops.fn_run_automations_storico('SCHEDULED', ARRAY['config'], false);

SELECT is(
    (SELECT count(*)::integer
       FROM pg_trigger t
       JOIN pg_proc p ON p.oid = t.tgfoid
      WHERE t.tgrelid = 'config.pgtap_sto_byfn'::regclass
        AND NOT t.tgisinternal
        AND p.proname = 'trgfn_storico_generic'),
    1,
    'BY_FUNCTION: la madre col trigger generico non ne riceve un secondo'
);

-- ============================================================
-- 4. BOTH
-- ============================================================
UPDATE dbops.automation_rules_tbl
   SET existence_strategy = 'BOTH'
 WHERE enabled AND upper(btrim(rule_type)) = 'STORICO';

SELECT dbops.fn_run_automations_storico('SCHEDULED', ARRAY['config'], false);

SELECT is(
    (SELECT count(*)::integer
       FROM pg_trigger t
       JOIN pg_proc p ON p.oid = t.tgfoid
      WHERE t.tgrelid = 'config.pgtap_sto_byfn'::regclass
        AND NOT t.tgisinternal
        AND p.proname = 'trgfn_storico_generic'),
    1,
    'BOTH: la madre col trigger generico non ne riceve un secondo'
);

-- ============================================================
-- 5. Il controllo: senza trigger, la regola BY_FUNCTION lo monta
-- ============================================================
DROP TRIGGER trg_pgtap_sto_byfn_a_mano ON config.pgtap_sto_byfn;

UPDATE dbops.automation_rules_tbl
   SET existence_strategy = 'BY_FUNCTION'
 WHERE enabled AND upper(btrim(rule_type)) = 'STORICO';

SELECT dbops.fn_run_automations_storico('SCHEDULED', ARRAY['config'], false);

SELECT is(
    (SELECT count(*)::integer
       FROM pg_trigger t
       JOIN pg_proc p ON p.oid = t.tgfoid
      WHERE t.tgrelid = 'config.pgtap_sto_byfn'::regclass
        AND NOT t.tgisinternal
        AND p.proname = 'trgfn_storico_generic'),
    1,
    'BY_FUNCTION su una madre senza trigger: il trigger nasce'
);

SELECT * FROM finish();

ROLLBACK;
