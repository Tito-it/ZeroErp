-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: il test fa DDL — crea uno schema di prova con un padre, due figlie e un trigger ATTIVO montato a mano — e lancia il runner ATTIVO
-- pgTAP test per Zero ERP
--
-- Due FK della stessa figlia verso lo stesso padre hanno due REQUIRE e due
-- BLOCK, con due nomi: il trigger si riconosce dagli argomenti (la FK che
-- difende), e l'hash della FK entra nel nome quando la coppia ha piu' FK.
-- Brief: brief-db-revisione-dbops, giro 10b (D10, N2; D17, N1)
--
-- Elenco test (plan 7):
--  1) ⭐ la figlia con due FK verso il padre ha due REQUIRE
--  2) ⭐ il padre ha tre BLOCK: due per quella figlia, uno per l'altra
--  3) i due REQUIRE hanno nomi diversi
--  4) la figlia con una FK sola tiene il nome senza hash
--  5) un secondo giro non ricrea niente (stessi oid)
--  6) ⭐ il caso di prima: un REQUIRE vivo sulla prima FK col nome che non la
--     distingue; il giro lo rigenera col nome nuovo e crea quello della seconda
--  7) ...e il nome vecchio non c'e' piu'
--
-- Prima {fkhash6_if_long} metteva l'hash solo oltre 63 caratteri: i due nomi
--   coincidevano e il runner (strategia BOTH: nome O argomenti) saltava la
--   seconda FK. I casi si COSTRUISCONO in uno schema di prova.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(7);

CREATE SCHEMA pgtap_att2;
CREATE TABLE pgtap_att2.p (id bigint PRIMARY KEY, attivo boolean NOT NULL DEFAULT true);
CREATE TABLE pgtap_att2.c (
    id bigint PRIMARY KEY, attivo boolean NOT NULL DEFAULT true,
    p_da_id bigint REFERENCES pgtap_att2.p (id),
    p_a_id  bigint REFERENCES pgtap_att2.p (id));
CREATE TABLE pgtap_att2.s (
    id bigint PRIMARY KEY, attivo boolean NOT NULL DEFAULT true,
    p_id bigint REFERENCES pgtap_att2.p (id));

SELECT dbops.fn_run_automations_attivo('SCHEDULED', ARRAY['pgtap_att2'], false);

CREATE FUNCTION pg_temp.trg(p_rel regclass, p_fn regprocedure)
 RETURNS text[]
 LANGUAGE sql
AS $f$
    SELECT COALESCE(array_agg(t.tgname::text ORDER BY t.tgname), ARRAY[]::text[])
      FROM pg_trigger t
     WHERE t.tgrelid = p_rel AND t.tgfoid = p_fn AND NOT t.tgisinternal;
$f$;

SELECT is(cardinality(pg_temp.trg('pgtap_att2.c', 'dbops.trgfn_child_requires_active_parent()')), 2,
    '1) la figlia con due FK verso lo stesso padre ha due REQUIRE');
SELECT is(cardinality(pg_temp.trg('pgtap_att2.p', 'dbops.trgfn_prevent_deactivate_if_children()')), 3,
    '2) il padre ha tre BLOCK: due per la figlia con due FK, uno per l''altra');
SELECT is(
    (SELECT count(DISTINCT x)::int FROM unnest(pg_temp.trg('pgtap_att2.c', 'dbops.trgfn_child_requires_active_parent()')) AS u(x)),
    2,
    '3) i due REQUIRE hanno nomi diversi');
SELECT is(pg_temp.trg('pgtap_att2.s', 'dbops.trgfn_child_requires_active_parent()'),
    ARRAY['trg_s_a10_p_require_attivo_ins_upd'],
    '4) con una FK sola il nome resta senza hash');

CREATE TEMP TABLE _oid ON COMMIT DROP AS
SELECT array_agg(t.oid ORDER BY t.oid) AS oids
  FROM pg_trigger t
 WHERE t.tgrelid IN ('pgtap_att2.p'::regclass, 'pgtap_att2.c'::regclass, 'pgtap_att2.s'::regclass)
   AND NOT t.tgisinternal;

SELECT dbops.fn_run_automations_attivo('SCHEDULED', ARRAY['pgtap_att2'], false);

SELECT is(
    (SELECT array_agg(t.oid ORDER BY t.oid)
       FROM pg_trigger t
      WHERE t.tgrelid IN ('pgtap_att2.p'::regclass, 'pgtap_att2.c'::regclass, 'pgtap_att2.s'::regclass)
        AND NOT t.tgisinternal),
    (SELECT oids FROM _oid),
    '5) un secondo giro non ricrea niente');

-- Il caso di prima: un solo REQUIRE, sulla prima FK, col nome senza hash.
DO $x$
DECLARE r text;
BEGIN
    FOREACH r IN ARRAY pg_temp.trg('pgtap_att2.c', 'dbops.trgfn_child_requires_active_parent()') LOOP
        EXECUTE format('DROP TRIGGER %I ON pgtap_att2.c', r);
    END LOOP;
END
$x$;
CREATE CONSTRAINT TRIGGER trg_c_a10_p_require_attivo_ins_upd
    AFTER INSERT OR UPDATE OF attivo, p_da_id ON pgtap_att2.c
    DEFERRABLE INITIALLY DEFERRED
    FOR EACH ROW
    EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('pgtap_att2', 'p', 'attivo', 'p_da_id', 'id');

SELECT dbops.fn_run_automations_attivo('SCHEDULED', ARRAY['pgtap_att2'], false);

SELECT is(cardinality(pg_temp.trg('pgtap_att2.c', 'dbops.trgfn_child_requires_active_parent()')), 2,
    '6) dal caso di prima (un REQUIRE col nome che non distingue): dopo il giro i REQUIRE sono due');
SELECT ok(NOT ('trg_c_a10_p_require_attivo_ins_upd' = ANY (pg_temp.trg('pgtap_att2.c', 'dbops.trgfn_child_requires_active_parent()'))),
    '7) ...e quello col nome vecchio e'' stato rigenerato col nome nuovo');

SELECT * FROM finish();
ROLLBACK;
