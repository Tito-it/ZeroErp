-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: il test fa DDL — crea uno schema di prova con una tabella e trigger di lock, e scrive nel registro dbops.automation_lock_columns
-- pgTAP test per Zero ERP
--
-- Il form dice cio' che il database rifiuta: dbops.vw_non_editable_fields legge
-- il lock di colonna VIVO (dbops.vw_lock_columns_vivi), non il registro.
-- Brief: brief-db-revisione-dbops, giro 10a (D25, N1)
--
-- Elenco test (plan 9):
--  1)   dbops.vw_lock_columns_vivi esiste
--  2)   le colonne di dbops.vw_non_editable_fields
--  3)   ⭐ codice_interno bloccato dal trigger, e nessuna riga nel registro:
--       il form lo elenca (prima mancava)
--  4)   il codice d'errore e' quello del trigger
--  5)   una riga ATTIVA nel registro senza trigger non e' elencata
--  6)   dbops.fn_non_editable_fields dice lo stesso, ordinato e senza doppi
--  7-8) l'UPDATE conferma la vista: la colonna elencata si rifiuta, quella
--       solo nel registro passa
--  9)   un trigger disabilitato non blocca niente: le sue colonne non sono elencate
--
-- Scopo: i casi si COSTRUISCONO in uno schema di prova; non si cercano fra le
--   tabelle di oggi.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(9);

SELECT has_view('dbops', 'vw_lock_columns_vivi',
    '1) dbops.vw_lock_columns_vivi esiste');

SELECT columns_are('dbops', 'vw_non_editable_fields',
    ARRAY['target_schema', 'target_table', 'column_name', 'error_code', 'trigger_name'],
    '2) vw_non_editable_fields: tabella, colonna, codice e trigger del lock vivo');

-- ============================================================
-- Fixture: una tabella con un lock su codice_interno e su a; b nel solo registro
-- ============================================================
CREATE SCHEMA pgtap_nef;
CREATE TABLE pgtap_nef.t (id bigint PRIMARY KEY, codice_interno text, a int, b int);
INSERT INTO pgtap_nef.t VALUES (1, 'X', 1, 1);

CREATE TRIGGER trg_t_a10_lock_columns_upd
    BEFORE UPDATE OF a, codice_interno ON pgtap_nef.t
    FOR EACH ROW EXECUTE FUNCTION script.trgfn_lock_columns(
        'codice_interno', 'E_CODICE_NON_MODIFICABILE', 'a', 'E_COLONNA_NON_MODIFICABILE');

INSERT INTO dbops.automation_lock_columns
       (target_schema, target_table, column_name, error_code, exec_mode, enabled, note)
VALUES ('pgtap_nef', 't', 'b', 'E_COLONNA_NON_MODIFICABILE', 'AUTO', true, 'pgTAP: nel registro, senza trigger');

SELECT ok(
    'codice_interno' = ANY (ARRAY(SELECT column_name FROM dbops.vw_non_editable_fields
                                   WHERE target_schema = 'pgtap_nef' AND target_table = 't')),
    '3) codice_interno bloccato dal trigger e assente dal registro: il form lo elenca');

SELECT is(
    (SELECT error_code FROM dbops.vw_non_editable_fields
      WHERE target_schema = 'pgtap_nef' AND target_table = 't' AND column_name = 'a'),
    'E_COLONNA_NON_MODIFICABILE',
    '4) il codice d''errore e'' quello che il trigger solleverebbe');

SELECT ok(
    NOT ('b' = ANY (ARRAY(SELECT column_name FROM dbops.vw_non_editable_fields
                           WHERE target_schema = 'pgtap_nef' AND target_table = 't'))),
    '5) b ha una riga attiva nel registro ma nessun trigger la blocca: non e'' elencata');

SELECT is(
    dbops.fn_non_editable_fields('pgtap_nef', 't', '1'),
    ARRAY['a', 'codice_interno'],
    '6) fn_non_editable_fields: le stesse colonne, ordinate e senza doppi');

-- ============================================================
-- La vista dice cio' che l'UPDATE fa
-- ============================================================
SELECT throws_like(
    $$ UPDATE pgtap_nef.t SET a = 2 WHERE id = 1 $$,
    '%Colonna non modificabile%',
    '7) a e'' elencata, e l''UPDATE la rifiuta');

SELECT lives_ok(
    $$ UPDATE pgtap_nef.t SET b = 2 WHERE id = 1 $$,
    '8) b non e'' elencata, e l''UPDATE la accetta');

ALTER TABLE pgtap_nef.t DISABLE TRIGGER trg_t_a10_lock_columns_upd;

SELECT is(
    (SELECT count(*)::int FROM dbops.vw_non_editable_fields
      WHERE target_schema = 'pgtap_nef' AND target_table = 't'),
    0,
    '9) un lock disabilitato non blocca niente: nessuna colonna elencata');

SELECT * FROM finish();
ROLLBACK;
