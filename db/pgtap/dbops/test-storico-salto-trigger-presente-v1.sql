-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- pgtap-runner: owner
-- pgtap-runner-motivo: il test fa DDL (una madre in config, la sua gemella in
--   storico, una funzione trigger e un trigger montati a mano): e' il percorso
--   delle migrazioni e di ci_apply, non dell'applicazione.
--
-- Test: il runner storico salta un trigger gia' presente senza fermarsi
--   dbops.fn_run_automations_storico (ramo duplicate_object) · dbops.audit_log
-- ChangeSet: 20261103-70 · Brief: brief-db-revisione-maintenance R4
--
-- Elenco test (plan 3):
--  1) ⭐ nome del template gia' preso da un trigger su un'altra funzione (il
--     runner riconosce il trigger dalla funzione, quindi lo da' per assente):
--     il runner vive (prima moriva con 23514 su chk_audit_status)
--  2) ⭐ ... e il salto e' nell'audit: status WARN, azione SKIP_EXISTS, la
--     tabella nominata
--  3) ✅ ... e sulla madre non e' nato nessun trigger di storico
--
-- ⭐ IL CASO SI COSTRUISCE. Il controllo per funzione dice «assente» (il
--   trigger c'e' ma esegue un'altra funzione), il CREATE TRIGGER trova il nome
--   preso e solleva duplicate_object: e' l'unica strada per quel ramo. Il nome
--   si calcola con dbops.fn_name_from_template dal template della regola,
--   come fa il runner, invece di scriverlo qui.
-- ⚠️ La gemella e' una copia della FORMA di storico.parameters, come in
--   test-storico-automazione-colonna-fk-v1 (INCLUDING IDENTITY: la forma di
--   `id` diverge fra le macchine).
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(3);

-- ============================================================
-- Fixture
-- ============================================================
CREATE TABLE config.pgtap_sto_skip (
    id         bigint PRIMARY KEY,
    nota       text,
    storicizza boolean DEFAULT true
);
CREATE TABLE storico.pgtap_sto_skip
    (LIKE storico.parameters INCLUDING DEFAULTS INCLUDING IDENTITY INCLUDING CONSTRAINTS);
ALTER TABLE storico.pgtap_sto_skip RENAME COLUMN parameters_id TO pgtap_sto_skip_id;

CREATE FUNCTION dbops.pgtap_trgfn_altra()
RETURNS trigger
LANGUAGE plpgsql
AS $f$
BEGIN
    RETURN NEW;
END
$f$;

-- Il trigger col nome del template, su un'altra funzione.
DO $fx$
DECLARE
    v_nome text;
BEGIN
    SELECT dbops.fn_name_from_template(
               r.name_template,
               'config', 'pgtap_sto_skip', NULL, NULL, NULL, 'upd_dlt')
      INTO v_nome
      FROM dbops.automation_rules_tbl r
     WHERE r.enabled AND upper(btrim(r.rule_type)) = 'STORICO'
     ORDER BY r.priority, r.id
     LIMIT 1;

    EXECUTE format(
        'CREATE TRIGGER %I BEFORE UPDATE OR DELETE ON config.pgtap_sto_skip '
        'FOR EACH ROW EXECUTE FUNCTION dbops.pgtap_trgfn_altra()', v_nome);
END
$fx$;

-- ============================================================
-- 1-3. Il salto
-- ============================================================
SELECT lives_ok(
    $$ SELECT dbops.fn_run_automations_storico('SCHEDULED', ARRAY['config'], false) $$,
    'Nome del template gia'' preso: il runner salta il trigger e vive'
);

SELECT ok(
    EXISTS (
        SELECT 1
          FROM dbops.audit_log a
         WHERE a.function_name     = 'dbops.fn_run_automations_storico'
           AND a.status            = 'WARN'
           AND a.params ->> 'action' = 'SKIP_EXISTS'
           AND a.params ->> 'table'  = 'config.pgtap_sto_skip'),
    'Il salto e'' nell''audit: WARN, azione SKIP_EXISTS, la tabella nominata'
);

SELECT is(
    (SELECT count(*)::integer
       FROM pg_trigger t
       JOIN pg_proc p ON p.oid = t.tgfoid
      WHERE t.tgrelid = 'config.pgtap_sto_skip'::regclass
        AND NOT t.tgisinternal
        AND p.proname = 'trgfn_storico_generic'),
    0,
    'Sulla madre non e'' nato nessun trigger di storico'
);

SELECT * FROM finish();

ROLLBACK;
