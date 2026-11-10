-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: il test crea due schemi di prova, li mette nell'ambito delle automazioni e
--   scrive nel registro dbops.fk_index_policy (configurazione delle migrazioni).
-- pgTAP test per Zero ERP
--
-- La politica degli indici delle FK: la decisione al posto del flag.
-- Brief: brief-db-revisione-dbops, giro 10d (§29).
--
-- I casi si fabbricano qui (schema pgtap_fkpol nell'ambito, pgtap_fkfuori fuori), non si leggono
-- dalla popolazione: passano anche su un database da zero.
--
-- Elenco test (plan 22):
--  1-3)  forma: decisione col CHECK, motivo mai vuoto, indice_nome generato dal comando
--  4-5)  i ritiri: fn_seed_fk_index_policy e vw_fk_con_indice_missing_policy non ci sono, ne' consentito
--  6)    una FK scoperta senza riga e' nel fatto con decisione NULL
--  7-8)  la scoperta la registra DA_DECIDERE, e il presidio la mostra
--  9-10) ⭐ Q14 ②: decisa SENZA_INDICE resta nel fatto ed esce dal presidio
-- 11)    una CON_INDICE ancora scoperta e' nel presidio come CON_INDICE_NON_APPLICATA
-- 12)    ⭐ l'apply non tocca l'indice di una DA_DECIDERE (prima una riga false lo toglieva)
-- 13)    l'apply toglie l'indice di una SENZA_INDICE
-- 14-15) l'apply crea l'indice della CON_INDICE, e la FK esce dal presidio
-- 16)    la scoperta toglie una DA_DECIDERE la cui FK non c'e' piu'...
-- 17)    ...⛔ e non tocca una riga decisa la cui FK non c'e' (il ponte verso django.auth_user)
-- 18)    una riga fuori ambito e' nel presidio come FUORI_AMBITO...
-- 19)    ...e l'apply non toglie il suo indice
-- 20)    ⭐ D23: vw_indici_ridondanti_prefisso aggancia la riga per nome esatto (suffisso e `_` jolly)
-- 21)    fn_indici_schema_nell_ambito: vero nell'ambito, falso fuori e su NULL
-- 22)    ⭐ PRESIDIO: nessuna riga vera della politica e' fuori ambito
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(22);

-- ============================================================
-- Il presidio 22 legge i dati veri: prima di ogni fixture.
-- ============================================================
CREATE TEMP TABLE pgtap_fuori_ambito_vero ON COMMIT DROP AS
SELECT d.schema_name || '.' || d.table_name || '.' || d.constraint_name AS chiave
  FROM dbops.vw_fk_da_decidere d
 WHERE d.caso = 'FUORI_AMBITO';

-- ============================================================
-- 1-5) Forma e ritiri
-- ============================================================
SELECT throws_ok(
    $$ INSERT INTO dbops.fk_index_policy (schema_name, table_name, constraint_name, decisione, dll_command)
       VALUES ('pgtap_fkpol', 'x', 'fk_x', 'FORSE', 'CREATE INDEX IF NOT EXISTS ix_x ON pgtap_fkpol.x(a);') $$,
    '23514', NULL,
    '1) decisione ammette solo DA_DECIDERE, CON_INDICE, SENZA_INDICE (chk_fk_index_policy_decisione)');

SELECT throws_ok(
    $$ INSERT INTO dbops.fk_index_policy (schema_name, table_name, constraint_name, motivo, dll_command)
       VALUES ('pgtap_fkpol', 'x', 'fk_x', '  ', 'CREATE INDEX IF NOT EXISTS ix_x ON pgtap_fkpol.x(a);') $$,
    '23514', NULL,
    '2) motivo non e'' mai una stringa vuota (chk_fk_index_policy_motivo_non_vuoto)');

SELECT is(
    (SELECT count(*)::int
       FROM dbops.fk_index_policy p
      WHERE p.indice_nome IS DISTINCT FROM split_part(p.dll_command, ' ', 6)),
    0,
    '3) indice_nome e'' il nome che dll_command crea, su ogni riga');

SELECT ok(
    NOT EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'fn_seed_fk_index_policy'
                   AND pronamespace = 'dbops'::regnamespace)
    AND to_regclass('dbops.vw_fk_con_indice_missing_policy') IS NULL,
    '4) ritirate dbops.fn_seed_fk_index_policy e dbops.vw_fk_con_indice_missing_policy');

SELECT hasnt_column('dbops', 'fk_index_policy', 'consentito',
    '5) consentito non c''e'' piu'': lo sostituisce decisione');

-- ============================================================
-- Fixture: due schemi, uno nell'ambito
-- ============================================================
CREATE SCHEMA pgtap_fkpol;
CREATE SCHEMA pgtap_fkfuori;
INSERT INTO dbops.automation_scope (schema_name, table_like) VALUES ('pgtap_fkpol', '*all');

CREATE TABLE pgtap_fkpol.padre (id int PRIMARY KEY);
CREATE TABLE pgtap_fkpol.figlia (
    id       int PRIMARY KEY,
    padre_id int CONSTRAINT fk_figlia_padre REFERENCES pgtap_fkpol.padre (id),
    altro_id int CONSTRAINT fk_figlia_altro REFERENCES pgtap_fkpol.padre (id),
    terzo_id int CONSTRAINT fk_figlia_terzo REFERENCES pgtap_fkpol.padre (id),
    nota     text
);
-- un indice che non copre nessuna FK: la spia del test 12
CREATE INDEX ix_pgtap_spia ON pgtap_fkpol.figlia (nota);

CREATE TABLE pgtap_fkfuori.t (id int PRIMARY KEY, nota text);
CREATE INDEX ix_pgtap_fuori ON pgtap_fkfuori.t (nota);

-- ============================================================
-- 6-10) Il fatto, la scoperta, il presidio
-- ============================================================
SELECT is(
    (SELECT count(*)::int FROM dbops.vw_fk_senza_indice
      WHERE schema_name = 'pgtap_fkpol' AND constraint_name = 'fk_figlia_padre' AND decisione IS NULL),
    1,
    '6) una FK scoperta senza riga e'' nel fatto (vw_fk_senza_indice) con decisione NULL');

SELECT dbops.fn_populate_fk_index_policy();

SELECT is(
    (SELECT array_agg(constraint_name || '=' || decisione ORDER BY constraint_name)
       FROM dbops.fk_index_policy WHERE schema_name = 'pgtap_fkpol'),
    ARRAY['fk_figlia_altro=DA_DECIDERE', 'fk_figlia_padre=DA_DECIDERE', 'fk_figlia_terzo=DA_DECIDERE'],
    '7) la scoperta registra le FK scoperte come DA_DECIDERE');

SELECT is(
    (SELECT caso FROM dbops.vw_fk_da_decidere
      WHERE schema_name = 'pgtap_fkpol' AND constraint_name = 'fk_figlia_padre'),
    'DA_DECIDERE',
    '8) il presidio vw_fk_da_decidere mostra la FK da decidere');

UPDATE dbops.fk_index_policy SET decisione = 'SENZA_INDICE'
 WHERE schema_name = 'pgtap_fkpol' AND constraint_name = 'fk_figlia_padre';

SELECT is(
    (SELECT decisione FROM dbops.vw_fk_senza_indice
      WHERE schema_name = 'pgtap_fkpol' AND constraint_name = 'fk_figlia_padre'),
    'SENZA_INDICE',
    '9) Q14 ②: una FK decisa SENZA_INDICE resta nel fatto, con la sua decisione');

SELECT is(
    (SELECT count(*)::int FROM dbops.vw_fk_da_decidere
      WHERE schema_name = 'pgtap_fkpol' AND constraint_name = 'fk_figlia_padre'),
    0,
    '10) ...ed esce dal presidio: e'' decisa');

-- ============================================================
-- 11-15) L'apply sui tre valori
-- ============================================================
-- La DA_DECIDERE di fk_figlia_altro nomina la spia (test 12): prima, a false, l'apply l'avrebbe tolta.
UPDATE dbops.fk_index_policy
   SET dll_command = 'CREATE INDEX IF NOT EXISTS ix_pgtap_spia ON pgtap_fkpol.figlia(nota);'
 WHERE schema_name = 'pgtap_fkpol' AND constraint_name = 'fk_figlia_altro';
-- La SENZA_INDICE di fk_figlia_padre: l'indice col suo nome c'e', e va tolto.
CREATE INDEX ix_figlia_padre_id ON pgtap_fkpol.figlia (padre_id);
-- La CON_INDICE di fk_figlia_terzo: ancora scoperta.
UPDATE dbops.fk_index_policy SET decisione = 'CON_INDICE'
 WHERE schema_name = 'pgtap_fkpol' AND constraint_name = 'fk_figlia_terzo';

SELECT is(
    (SELECT caso FROM dbops.vw_fk_da_decidere
      WHERE schema_name = 'pgtap_fkpol' AND constraint_name = 'fk_figlia_terzo'),
    'CON_INDICE_NON_APPLICATA',
    '11) una CON_INDICE ancora scoperta e'' nel presidio come CON_INDICE_NON_APPLICATA');

CALL dbops.apply_fk_index_policy();

SELECT has_index('pgtap_fkpol', 'figlia', 'ix_pgtap_spia',
    '12) l''apply non tocca l''indice nominato da una riga DA_DECIDERE');

SELECT hasnt_index('pgtap_fkpol', 'figlia', 'ix_figlia_padre_id',
    '13) l''apply toglie l''indice di una riga SENZA_INDICE');

SELECT has_index('pgtap_fkpol', 'figlia', 'ix_figlia_terzo_id', ARRAY['terzo_id'],
    '14) l''apply crea l''indice di una riga CON_INDICE scoperta');

SELECT is(
    (SELECT count(*)::int FROM dbops.vw_fk_da_decidere
      WHERE schema_name = 'pgtap_fkpol' AND constraint_name = 'fk_figlia_terzo'),
    0,
    '15) ...e la FK esce dal presidio');

-- ============================================================
-- 16-17) La scoperta toglie solo le sue righe
-- ============================================================
ALTER TABLE pgtap_fkpol.figlia DROP CONSTRAINT fk_figlia_altro;
ALTER TABLE pgtap_fkpol.figlia DROP CONSTRAINT fk_figlia_padre;

SELECT dbops.fn_populate_fk_index_policy();

SELECT is(
    (SELECT count(*)::int FROM dbops.fk_index_policy
      WHERE schema_name = 'pgtap_fkpol' AND constraint_name = 'fk_figlia_altro'),
    0,
    '16) la scoperta toglie una DA_DECIDERE la cui FK non c''e'' piu''');

SELECT is(
    (SELECT decisione FROM dbops.fk_index_policy
      WHERE schema_name = 'pgtap_fkpol' AND constraint_name = 'fk_figlia_padre'),
    'SENZA_INDICE',
    '17) ...e non tocca una riga decisa la cui FK non c''e'' (una FK del ponte django nasce dopo Liquibase)');

-- ============================================================
-- 18-19) Fuori ambito
-- ============================================================
INSERT INTO dbops.fk_index_policy (schema_name, table_name, constraint_name, decisione, dll_command)
VALUES ('pgtap_fkfuori', 't', 'fk_t_qualcosa', 'SENZA_INDICE',
        'CREATE INDEX IF NOT EXISTS ix_pgtap_fuori ON pgtap_fkfuori.t(nota);');

SELECT is(
    (SELECT caso FROM dbops.vw_fk_da_decidere
      WHERE schema_name = 'pgtap_fkfuori' AND constraint_name = 'fk_t_qualcosa'),
    'FUORI_AMBITO',
    '18) una riga su uno schema fuori ambito e'' nel presidio come FUORI_AMBITO');

CALL dbops.apply_fk_index_policy();

SELECT has_index('pgtap_fkfuori', 't', 'ix_pgtap_fuori',
    '19) ...e l''apply non toglie il suo indice (prima il DROP passava, la CREATE mai)');

-- ============================================================
-- 20) D23: il nome dell'indice per uguaglianza
-- ============================================================
CREATE TABLE pgtap_fkpol.t (x int, y int);
CREATE INDEX ix_t_x   ON pgtap_fkpol.t (x);       -- ridondante: prefisso del secondo
CREATE INDEX ix_t_x_y ON pgtap_fkpol.t (x, y);
-- due righe che col LIKE di prima agganciavano ix_t_x: un suffisso, e il `_` jolly
INSERT INTO dbops.fk_index_policy (schema_name, table_name, constraint_name, decisione, dll_command)
VALUES ('pgtap_fkpol', 't', 'fk_t_suffisso', 'SENZA_INDICE', 'CREATE INDEX IF NOT EXISTS ix_zt_x ON pgtap_fkpol.t(x);'),
       ('pgtap_fkpol', 't', 'fk_t_jolly',    'SENZA_INDICE', 'CREATE INDEX IF NOT EXISTS ixqt_x ON pgtap_fkpol.t(x);');

SELECT is(
    (SELECT origine || ' ' || COALESCE(policy_constraint_name, '-')
       FROM dbops.vw_indici_ridondanti_prefisso
      WHERE schema_name = 'pgtap_fkpol' AND indice_ridondante = 'ix_t_x'),
    'MANUALE -',
    '20) D23: nessuna riga nomina ix_t_x, quindi MANUALE (prima il LIKE agganciava ix_zt_x e ixqt_x)');

-- ============================================================
-- 21-22) Il perimetro
-- ============================================================
SELECT is(
    ARRAY[dbops.fn_indici_schema_nell_ambito('pgtap_fkpol'),
          dbops.fn_indici_schema_nell_ambito('pgtap_fkfuori'),
          dbops.fn_indici_schema_nell_ambito(NULL)],
    ARRAY[true, false, false],
    '21) fn_indici_schema_nell_ambito: vero nell''ambito, falso fuori e su NULL');

SELECT is(
    (SELECT COALESCE(array_agg(chiave ORDER BY chiave), ARRAY[]::text[]) FROM pgtap_fuori_ambito_vero),
    ARRAY[]::text[],
    '22) PRESIDIO: nessuna riga vera della politica e'' su uno schema fuori ambito');

SELECT * FROM finish();
ROLLBACK;
