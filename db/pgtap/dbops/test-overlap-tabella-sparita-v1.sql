-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture scrive in dbops.automazione_overlap, il
--   registro delle automazioni, che a runtime scrivono solo i changeSet.
--
-- Test: una riga del registro overlap su una tabella che non esiste
--   dbops.fn_apply_automazione_overlap · dbops.automazione_overlap
-- ChangeSet: 20261103-59 · Brief: brief-db-revisione-maintenance D6
--
-- Elenco test (plan 2):
--  1) ⭐ il giro non muore su una riga che punta a una tabella sparita
--  2) ⭐ la riga e' un salto dichiarato: audit col motivo TABLE_NOT_FOUND
--
-- ⚠️ La riga del registro si FABBRICA, con un nome che non puo' esistere: il
--   caso nasce quando una tabella viene rinominata o ritirata e il registro
--   resta indietro, e oggi il seed non ne contiene nessuna.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(2);

CREATE TEMP TABLE tmp_fx AS
SELECT 'pgtap_sparita_' || to_char(clock_timestamp(), 'YYYYMMDDHH24MISSUS') AS tabella;

INSERT INTO dbops.automazione_overlap (target_schema, target_table, key_columns, active, exec_mode, note)
SELECT 'dbops', f.tabella, ARRAY['id'], true, 'AUTO', 'Fixture pgTAP: tabella che non esiste'
  FROM tmp_fx f;

SELECT lives_ok(
    $$ SELECT dbops.fn_apply_automazione_overlap('SCHEDULED', true) $$,
    'Il giro overlap non muore su una riga del registro che punta a una tabella sparita'
);

SELECT ok(
    EXISTS (
        SELECT 1
          FROM dbops.audit_log a
          JOIN tmp_fx f ON a.params ->> 'table' = 'dbops.' || f.tabella
         WHERE a.function_name = 'dbops.fn_apply_automazione_overlap'
           AND a.params ->> 'reason' = 'TABLE_NOT_FOUND'),
    'La riga su una tabella sparita lascia un salto dichiarato: TABLE_NOT_FOUND'
);

SELECT * FROM finish();

ROLLBACK;
