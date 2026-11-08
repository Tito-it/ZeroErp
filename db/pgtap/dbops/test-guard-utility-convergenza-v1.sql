-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: CREATE TABLE dbops.tst_gu_*: la convergenza del guard utility/tipo ruolo si
--   collauda su tabelle vere, con i loro trigger scritti a mano e le loro righe del registro, e
--   dbops e' schema di strumenti DBA su cui il ruolo applicativo non ha (giustamente) CREATE.
-- pgTAP test per Zero ERP
--
-- La convergenza del guard utility/tipo ruolo: il trigger VIVO portato a quello ATTESO dal
-- registro dbops.automazione_guard_utility_tipo_ruolo, il runner che si FERMA invece di
-- cancellare un guard che il registro non conosce, e il processo che lo fa girare.
-- Brief: brief-db-revisione-dbops, giro 10c, blocco 10c-2 (D30, D34, Q14 ⑬; Q3).
--
-- Elenco test (plan 14):
--  1)    ⭐ PRESIDIO: su tutto l'ambito nessun guard diverge dal registro
--  2)    ⭐ PRESIDIO: nessun trigger della funzione su una tabella fuori dall'ambito
--  3)    ⭐ una riga con la colonna senza prefisso (soggetto_ruolo_id): CREA (prima il filtro la scartava)
--  4)    dopo il giro: un trigger solo, BEFORE INSERT OR UPDATE OF le due colonne, gli argomenti
--  5)    una riga con una colonna che non esiste: COLONNA_MANCANTE...
--  6)    ...e dopo il giro un WARN COLUMN_MISSING nell'audit, e nessun trigger
--  7)    trigger_name cambiato: il vecchio sparisce, c'e' solo il nuovo
--  8)    riga spenta: dopo il giro il guard non c'e' piu'
--  9)    un trigger della funzione su una tabella senza riga: SCONOSCIUTO
-- 10)    ...e il runner si ferma con E_GUARD_UTILITY, nominandolo
-- 11)    ...senza averlo cancellato
-- 12)    DRY RUN: nessuna DDL
-- 13)    la porta storica (fn_apply_automazione_guard_utility_tipo_ruolo) fa lo stesso lavoro
-- 14)    ⭐ il processo automations_guard_utility e' nella catena, fra delete_block e overlap
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(14);

-- ============================================================
-- ⭐ I presidi, prima che la fixture esista
-- ============================================================
SELECT is(
    (SELECT COALESCE(array_agg(d.schema_name||'.'||d.table_name||' '||d.azione
                               ORDER BY d.schema_name, d.table_name), ARRAY[]::text[])
       FROM dbops.fn_guard_utility_divergenze('CI', NULL) AS d),
    ARRAY[]::text[],
    '1) nessun guard utility/tipo ruolo diverge da dbops.automazione_guard_utility_tipo_ruolo');

SELECT is(
    (SELECT COALESCE(array_agg(n.nspname||'.'||c.relname||' '||tg.tgname ORDER BY 1), ARRAY[]::text[])
       FROM pg_trigger tg
       JOIN pg_class c     ON c.oid = tg.tgrelid
       JOIN pg_namespace n ON n.oid = c.relnamespace
      WHERE NOT tg.tgisinternal
        AND tg.tgfoid = 'script.trgfn_guard_utility_tipo_ruolo_by_cols()'::regprocedure
        AND NOT (    c.relkind = 'r'
                 AND n.nspname = ANY (dbops.fn_resolve_scope(NULL))
                 AND dbops.fn_table_in_scope(n.nspname, c.relname))),
    ARRAY[]::text[],
    '2) nessun guard utility/tipo ruolo su una tabella fuori dall''ambito: il runner non ci arriva');

-- ============================================================
-- Fixture
-- ============================================================
CREATE TABLE dbops.tst_gu_senza_prefisso (id bigint PRIMARY KEY, utility_id integer, soggetto_ruolo_id bigint);
CREATE TABLE dbops.tst_gu_colonna_assente (id bigint PRIMARY KEY, utility_id integer);
CREATE TABLE dbops.tst_gu_ignota (id bigint PRIMARY KEY, utility_id integer, soggetto_ruolo_id bigint);
CREATE TABLE dbops.tst_gu_porta (id bigint PRIMARY KEY, utility_id integer, cliente_soggetto_ruolo_id bigint);

INSERT INTO dbops.automation_scope (schema_name, table_like)
VALUES ('dbops', 'tst_gu_senza_prefisso'), ('dbops', 'tst_gu_colonna_assente'),
       ('dbops', 'tst_gu_ignota'), ('dbops', 'tst_gu_porta')
ON CONFLICT DO NOTHING;

INSERT INTO dbops.automazione_guard_utility_tipo_ruolo
       (schema_name, table_name, utility_column, soggetto_ruolo_column, enabled, exec_mode)
VALUES ('dbops', 'tst_gu_senza_prefisso',  'utility_id', 'soggetto_ruolo_id', true, 'AUTO'),
       ('dbops', 'tst_gu_colonna_assente', 'utility_id', 'soggetto_ruolo_id', true, 'AUTO');

-- ============================================================
-- 3-4) La forma senza prefisso (D30)
-- ============================================================
SELECT is(
    (SELECT d.azione FROM dbops.fn_guard_utility_divergenze('CI', ARRAY['dbops']) d
      WHERE d.table_name = 'tst_gu_senza_prefisso'),
    'CREA',
    '3) una riga con soggetto_ruolo_id (senza prefisso): CREA, il registro decide la colonna');

CREATE TEMP TABLE _prima AS SELECT COALESCE(max(id), 0) AS ultimo_id FROM dbops.audit_log;

SELECT dbops.fn_run_automations_guard_utility('CI', ARRAY['dbops'], false);

-- string_agg e non results_eq: tgname e' di tipo name, e il confronto col testo non sa quale
--   collation usare.
SELECT is(
    (SELECT string_agg(tg.tgtype::text || ' '
                       || array_to_string(dbops.fn_trigger_argomenti(tg.tgargs), ','), '; ')
       FROM pg_trigger tg
      WHERE tg.tgrelid = 'dbops.tst_gu_senza_prefisso'::regclass
        AND tg.tgfoid = 'script.trgfn_guard_utility_tipo_ruolo_by_cols()'::regprocedure),
    '23 utility_id,soggetto_ruolo_id',
    '4) dopo il giro: un trigger solo, BEFORE INSERT OR UPDATE (tgtype 23), argomenti utility_id e soggetto_ruolo_id');

-- ============================================================
-- 5-6) Una colonna che non esiste
-- ============================================================
SELECT is(
    (SELECT d.azione FROM dbops.fn_guard_utility_divergenze('CI', ARRAY['dbops']) d
      WHERE d.table_name = 'tst_gu_colonna_assente'),
    'COLONNA_MANCANTE',
    '5) una riga con una colonna che la tabella non ha: COLONNA_MANCANTE');

SELECT ok(
    EXISTS (SELECT 1 FROM dbops.audit_log a
             WHERE a.id > (SELECT ultimo_id FROM _prima)
               AND a.function_name = 'dbops.fn_run_automations_guard_utility'
               AND a.status = 'WARN'
               AND a.params ->> 'table'  = 'dbops.tst_gu_colonna_assente'
               AND a.params ->> 'reason' = 'COLUMN_MISSING')
    AND NOT EXISTS (SELECT 1 FROM pg_trigger tg
                     WHERE tg.tgrelid = 'dbops.tst_gu_colonna_assente'::regclass
                       AND tg.tgfoid = 'script.trgfn_guard_utility_tipo_ruolo_by_cols()'::regprocedure),
    '6) il giro lascia WARN COLUMN_MISSING e non monta niente (prima il salto era muto)');

-- ============================================================
-- 7-8) Il nome cambia, la riga si spegne (D34)
-- ============================================================
UPDATE dbops.automazione_guard_utility_tipo_ruolo SET trigger_name = 'trg_tst_gu_senza_prefisso_a10_guard_nuovo_ins_upd'
 WHERE schema_name = 'dbops' AND table_name = 'tst_gu_senza_prefisso';
SELECT dbops.fn_run_automations_guard_utility('CI', ARRAY['dbops'], false);

SELECT is(
    (SELECT array_agg(tg.tgname::text ORDER BY tg.tgname)
       FROM pg_trigger tg
      WHERE tg.tgrelid = 'dbops.tst_gu_senza_prefisso'::regclass
        AND tg.tgfoid = 'script.trgfn_guard_utility_tipo_ruolo_by_cols()'::regprocedure),
    ARRAY['trg_tst_gu_senza_prefisso_a10_guard_nuovo_ins_upd'],
    '7) trigger_name cambiato: il vecchio sparisce, c''e'' solo il nuovo');

UPDATE dbops.automazione_guard_utility_tipo_ruolo SET enabled = false
 WHERE schema_name = 'dbops' AND table_name = 'tst_gu_senza_prefisso';
SELECT dbops.fn_run_automations_guard_utility('CI', ARRAY['dbops'], false);

SELECT is(
    (SELECT count(*)::int FROM pg_trigger tg
      WHERE tg.tgrelid = 'dbops.tst_gu_senza_prefisso'::regclass
        AND tg.tgfoid = 'script.trgfn_guard_utility_tipo_ruolo_by_cols()'::regprocedure),
    0,
    '8) riga spenta: dopo il giro il guard non c''e'' piu'' (prima restava)');

-- ============================================================
-- 9-12) Un guard che il registro non conosce, e il dry run
-- ============================================================
CREATE TRIGGER trg_tst_gu_ignota_a10_guard_utility_tipo_ruolo_ins_upd
    BEFORE INSERT OR UPDATE OF utility_id, soggetto_ruolo_id ON dbops.tst_gu_ignota
    FOR EACH ROW EXECUTE FUNCTION script.trgfn_guard_utility_tipo_ruolo_by_cols('utility_id', 'soggetto_ruolo_id');

SELECT is(
    (SELECT d.azione FROM dbops.fn_guard_utility_divergenze('CI', ARRAY['dbops']) d
      WHERE d.table_name = 'tst_gu_ignota'),
    'SCONOSCIUTO',
    '9) un trigger della funzione su una tabella senza riga del registro: SCONOSCIUTO');

SELECT throws_like(
    $$ SELECT dbops.fn_run_automations_guard_utility('CI', ARRAY['dbops'], false) $$,
    '%dbops.tst_gu_ignota%',
    '10) il runner si ferma con E_GUARD_UTILITY e nomina la tabella');

SELECT is(
    (SELECT count(*)::int FROM pg_trigger tg
      WHERE tg.tgrelid = 'dbops.tst_gu_ignota'::regclass
        AND tg.tgfoid = 'script.trgfn_guard_utility_tipo_ruolo_by_cols()'::regprocedure),
    1,
    '11) ...senza averlo cancellato');

DROP TRIGGER trg_tst_gu_ignota_a10_guard_utility_tipo_ruolo_ins_upd ON dbops.tst_gu_ignota;

INSERT INTO dbops.automazione_guard_utility_tipo_ruolo
       (schema_name, table_name, utility_column, soggetto_ruolo_column, enabled, exec_mode)
VALUES ('dbops', 'tst_gu_porta', 'utility_id', 'cliente_soggetto_ruolo_id', true, 'AUTO');
SELECT dbops.fn_run_automations_guard_utility('CI', ARRAY['dbops'], true);

SELECT is(
    (SELECT count(*)::int FROM pg_trigger tg
      WHERE tg.tgrelid = 'dbops.tst_gu_porta'::regclass
        AND tg.tgfoid = 'script.trgfn_guard_utility_tipo_ruolo_by_cols()'::regprocedure),
    0,
    '12) il dry run non crea il trigger');

-- ============================================================
-- 13-14) La porta storica e il processo (⑬)
-- ============================================================
SELECT dbops.fn_apply_automazione_guard_utility_tipo_ruolo('CI', false);

SELECT is(
    (SELECT count(*)::int FROM pg_trigger tg
      WHERE tg.tgrelid = 'dbops.tst_gu_porta'::regclass
        AND tg.tgfoid = 'script.trgfn_guard_utility_tipo_ruolo_by_cols()'::regprocedure),
    1,
    '13) la porta storica, che il primo giro di ci_apply chiama ancora, fa lo stesso lavoro del runner');

SELECT ok(
    (SELECT p.attivo
            AND p.ci_ordine > (SELECT q.ci_ordine FROM dbops.processi q WHERE q.codice = 'automations_delete_block')
            AND p.ci_ordine < (SELECT q.ci_ordine FROM dbops.processi q WHERE q.codice = 'automations_overlap')
            AND to_regprocedure(p.ci_procedura) = 'maintenance.proc_automations_guard_utility_job()'::regprocedure
       FROM dbops.processi p
      WHERE p.codice = 'automations_guard_utility'),
    '14) il processo automations_guard_utility e'' attivo, nella catena fra delete_block e overlap, con la sua procedura');

SELECT * FROM finish();
ROLLBACK;
