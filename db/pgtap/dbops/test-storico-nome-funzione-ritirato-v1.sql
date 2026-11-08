-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- pgtap-runner: owner
-- pgtap-runner-motivo: il test fa DDL (una madre in config, la sua gemella in
--   storico, un trigger montato a mano): e' il percorso delle migrazioni e di
--   ci_apply, non dell'applicazione.
--
-- Test: il runner storico riconosce il trigger generico per FUNZIONE
--   dbops.fn_run_automations_storico · script.trgfn_storico_generic
-- ChangeSet: 20261103-57 · Brief: brief-db-revisione-maintenance D3, §10.5 R2
--
-- Elenco test (plan 5):
--  1) la funzione generica di storicizzazione esiste col nome vivo
--  2) ⛔ nessuna funzione PL/pgSQL nomina script.trgfn_upd_dlt_storico_generic,
--     il nome che aveva prima: chi lo cerca non trova mai il trigger
--  3) ⭐ una madre che ha gia' il trigger generico con un altro nome non ne
--     riceve un secondo: il trigger si riconosce dalla funzione
--  4) ⭐ la regola non ha piu' una strategia d'esistenza: la colonna
--     existence_strategy non c'e' (brief-db-revisione-dbops giro 10b, N1)
--  5) ✅ su una madre senza trigger il trigger nasce (il 3 non e' vero perche'
--     la regola non scatta)
--
-- ⭐ IL CASO DI D3. Col nome ritirato il controllo per funzione non trovava
--   mai niente: il runner montava un secondo trigger di storico accanto a
--   quello che c'era, e ogni UPDATE scriveva due snapshot. Il test 3 conta i
--   trigger generici sulla madre: due e' il difetto.
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
-- 3. Il trigger si riconosce dalla funzione
-- ============================================================
SELECT dbops.fn_run_automations_storico('SCHEDULED', ARRAY['config'], false);

SELECT is(
    (SELECT count(*)::integer
       FROM pg_trigger t
       JOIN pg_proc p ON p.oid = t.tgfoid
      WHERE t.tgrelid = 'config.pgtap_sto_byfn'::regclass
        AND NOT t.tgisinternal
        AND p.proname = 'trgfn_storico_generic'),
    1,
    'la madre col trigger generico (con un altro nome) non ne riceve un secondo'
);

-- ============================================================
-- 4. Non c'e' piu' una strategia da scegliere
-- ============================================================
SELECT hasnt_column('dbops', 'automation_rules_tbl', 'existence_strategy',
    'la regola non ha una strategia d''esistenza: il trigger si riconosce sempre dalla funzione');

-- ============================================================
-- 5. Il controllo: senza trigger, la regola BY_FUNCTION lo monta
-- ============================================================
DROP TRIGGER trg_pgtap_sto_byfn_a_mano ON config.pgtap_sto_byfn;

SELECT dbops.fn_run_automations_storico('SCHEDULED', ARRAY['config'], false);

SELECT is(
    (SELECT count(*)::integer
       FROM pg_trigger t
       JOIN pg_proc p ON p.oid = t.tgfoid
      WHERE t.tgrelid = 'config.pgtap_sto_byfn'::regclass
        AND NOT t.tgisinternal
        AND p.proname = 'trgfn_storico_generic'),
    1,
    'su una madre senza trigger il trigger nasce'
);

SELECT * FROM finish();

ROLLBACK;
