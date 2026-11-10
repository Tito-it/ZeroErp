-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: CREATE TABLE dbops.tst_ov_*: l'apply dei vincoli di non sovrapposizione si
--   collauda su tabelle vere con le loro regole, e dbops e' schema di strumenti DBA su cui il
--   ruolo applicativo non ha (giustamente) CREATE.
-- pgTAP test per Zero ERP
--
-- Le regole di dbops.automazione_overlap e i loro vincoli: una regola attiva ha il SUO vincolo, una
-- colonna di chiave assente o dati gia' sovrapposti fermano la regola e non il giro.
-- Brief: brief-db-revisione-dbops, giro 10c, blocco 10c-3 (D59, Q14 ⑫).
--
-- Elenco test (plan 9):
--  1)    ⭐ PRESIDIO: ogni regola attiva su una tabella che c'e' ha il suo vincolo (per nome) o un
--        UNIQUE WITHOUT OVERLAPS sul periodo
--  2)    ⭐ PRESIDIO: nessun vincolo di una regola spenta resta vivo senza che lo si sappia
--  3)    ⭐ un giro con righe gia' sovrapposte su una tabella non si ferma
--  4)    una colonna di chiave che non c'e': WARN KEY_COLUMN_MISSING...
--  5)    ...e nessun vincolo con la chiave piu' corta
--  6)    righe sovrapposte: WARN DATI_SOVRAPPOSTI col dettaglio della coppia, e il vincolo non nasce
--  7)    ...e la regola di un'altra tabella, nello stesso giro, ha il suo vincolo
--  8)    un EXCLUDE estraneo sulla colonna del periodo non conta: il vincolo della regola nasce
--  9)    un secondo giro non cambia niente (il vincolo c'e', per nome)
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(9);

-- ============================================================
-- ⭐ I presidi
-- ============================================================
SELECT is(
    (SELECT COALESCE(array_agg(o.target_schema||'.'||o.target_table ORDER BY 1), ARRAY[]::text[])
       FROM dbops.automazione_overlap o
      WHERE o.active
        AND upper(btrim(o.exec_mode)) = 'AUTO'
        AND to_regclass(format('%I.%I', o.target_schema, o.target_table)) IS NOT NULL
        AND NOT EXISTS (
              SELECT 1 FROM pg_constraint con
               WHERE con.conrelid = to_regclass(format('%I.%I', o.target_schema, o.target_table))
                 AND (   (con.contype = 'x'
                          AND con.conname = dbops.fn_nome_oggetto_dichiarato(
                                  o.constraint_name, 'ex_{table}_no_overlap', o.target_schema, o.target_table))
                      OR (con.contype = 'u'
                          AND pg_get_constraintdef(con.oid) ILIKE '%WITHOUT OVERLAPS%')))),
    ARRAY[]::text[],
    '1) ogni regola overlap attiva ha il suo vincolo');

SELECT is(
    (SELECT COALESCE(array_agg(o.target_schema||'.'||o.target_table ORDER BY 1), ARRAY[]::text[])
       FROM dbops.automazione_overlap o
       JOIN pg_constraint con
         ON con.conrelid = to_regclass(format('%I.%I', o.target_schema, o.target_table))
        AND con.contype = 'x'
        AND con.conname = dbops.fn_nome_oggetto_dichiarato(
                o.constraint_name, 'ex_{table}_no_overlap', o.target_schema, o.target_table)
      WHERE NOT o.active),
    ARRAY[]::text[],
    '2) nessuna regola spenta con il vincolo ancora vivo: togliere il vincolo e'' una decisione da prendere');

-- ============================================================
-- Fixture: quattro tabelle con un periodo nativo
-- ============================================================
CREATE TABLE dbops.tst_ov_chiave (id bigint PRIMARY KEY, articolo_id bigint, validita daterange);
CREATE TABLE dbops.tst_ov_sovrapposte (id bigint PRIMARY KEY, articolo_id bigint, validita daterange);
CREATE TABLE dbops.tst_ov_pulita (id bigint PRIMARY KEY, articolo_id bigint, validita daterange);
CREATE TABLE dbops.tst_ov_estraneo (id bigint PRIMARY KEY, articolo_id bigint, altro_id bigint, validita daterange,
    CONSTRAINT ex_tst_ov_estraneo_altro EXCLUDE USING gist (altro_id WITH =, validita WITH &&));

INSERT INTO dbops.tst_ov_sovrapposte VALUES
    (1, 7, daterange('2026-01-01', '2026-06-30', '[]')),
    (2, 7, daterange('2026-03-01', '2026-12-31', '[]'));

INSERT INTO dbops.automazione_overlap (target_schema, target_table, key_columns, range_col, active, exec_mode, note)
VALUES ('dbops', 'tst_ov_chiave',      '["articolo_id", "colonna_che_non_ce"]'::jsonb, 'validita', true, 'AUTO', 'pgTAP'),
       ('dbops', 'tst_ov_sovrapposte', '["articolo_id"]'::jsonb,                    'validita', true, 'AUTO', 'pgTAP'),
       ('dbops', 'tst_ov_pulita',      '["articolo_id"]'::jsonb,                    'validita', true, 'AUTO', 'pgTAP'),
       ('dbops', 'tst_ov_estraneo',    '["articolo_id"]'::jsonb,                    'validita', true, 'AUTO', 'pgTAP');

CREATE TEMP TABLE _prima AS SELECT COALESCE(max(id), 0) AS ultimo_id FROM dbops.audit_log;

-- ============================================================
-- 3-8) Un giro
-- ============================================================
SELECT lives_ok(
    $$ SELECT dbops.fn_apply_automazione_overlap('AUTO', false) $$,
    '3) righe gia'' sovrapposte su una tabella: il giro non si ferma');

SELECT ok(
    EXISTS (SELECT 1 FROM dbops.audit_log a
             WHERE a.id > (SELECT ultimo_id FROM _prima)
               AND a.function_name = 'dbops.fn_apply_automazione_overlap'
               AND a.status = 'WARN'
               AND a.params ->> 'table'  = 'dbops.tst_ov_chiave'
               AND a.params ->> 'reason' = 'KEY_COLUMN_MISSING'),
    '4) una colonna di chiave che non c''e'': WARN KEY_COLUMN_MISSING');

SELECT is(
    (SELECT count(*)::int FROM pg_constraint
      WHERE conrelid = 'dbops.tst_ov_chiave'::regclass AND contype = 'x'),
    0,
    '5) ...e nessun vincolo con la chiave piu'' corta (prima nasceva sul solo articolo_id)');

SELECT ok(
    EXISTS (SELECT 1 FROM dbops.audit_log a
             WHERE a.id > (SELECT ultimo_id FROM _prima)
               AND a.function_name = 'dbops.fn_apply_automazione_overlap'
               AND a.status = 'WARN'
               AND a.sqlstate = '23P01'
               AND a.params ->> 'table'  = 'dbops.tst_ov_sovrapposte'
               AND a.params ->> 'reason' = 'DATI_SOVRAPPOSTI'
               AND a.params ->> 'dettaglio' IS NOT NULL)
    AND NOT EXISTS (SELECT 1 FROM pg_constraint
                     WHERE conrelid = 'dbops.tst_ov_sovrapposte'::regclass AND contype = 'x'),
    '6) WARN DATI_SOVRAPPOSTI con lo SQLSTATE e il dettaglio della coppia, e il vincolo non nasce');

SELECT ok(
    EXISTS (SELECT 1 FROM pg_constraint
             WHERE conrelid = 'dbops.tst_ov_pulita'::regclass AND contype = 'x'
               AND conname = 'ex_tst_ov_pulita_no_overlap'),
    '7) la regola di un''altra tabella, nello stesso giro, ha il suo vincolo');

SELECT ok(
    EXISTS (SELECT 1 FROM pg_constraint
             WHERE conrelid = 'dbops.tst_ov_estraneo'::regclass AND contype = 'x'
               AND conname = 'ex_tst_ov_estraneo_no_overlap'),
    '8) un EXCLUDE estraneo sulla colonna del periodo non conta: il vincolo della regola nasce (prima la regola si dava per applicata)');

-- ============================================================
-- 9) Idempotenza
-- ============================================================
CREATE TEMP TABLE _vincoli AS
SELECT conrelid, conname FROM pg_constraint
 WHERE conrelid IN ('dbops.tst_ov_pulita'::regclass, 'dbops.tst_ov_estraneo'::regclass) AND contype = 'x';

SELECT dbops.fn_apply_automazione_overlap('AUTO', false);

SELECT is(
    (SELECT count(*)::int FROM pg_constraint
      WHERE conrelid IN ('dbops.tst_ov_pulita'::regclass, 'dbops.tst_ov_estraneo'::regclass) AND contype = 'x'),
    (SELECT count(*)::int FROM _vincoli),
    '9) un secondo giro non crea niente: il vincolo della regola c''e'', per nome');

SELECT * FROM finish();
ROLLBACK;
