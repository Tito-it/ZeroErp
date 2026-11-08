-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- pgtap-runner: owner
-- pgtap-runner-motivo: DDL (una tabella di prova con vincoli e indici, in uno
--   schema dell'ambito delle automazioni).
--
-- Test: dbops.vw_duplicate_indexes non propone il DROP di un indice che regge un
-- vincolo o la replica identity (D8).
-- Brief: brief-db-revisione-dbops, giro 9, blocco 9b (§24). changeSet 20261109-51.
--
-- Elenco test (plan 5):
--   1) due UNIQUE identici, il secondo di vincolo: il gruppo c'e'
--   2) ... si tiene l'indice del vincolo, anche se e' nato dopo
--   3) ... e si propone il DROP dell'altro
--   4) la replica identity si tiene e non si propone
--   5) due indici di vincolo identici: nessuno proposto per il DROP
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(5);

-- ⚠️ In uno schema dell'ambito (vendite e' '*all'): la vista guarda solo quelli.
CREATE TABLE vendite.pgtap_dup_indici (
    id  bigint PRIMARY KEY,
    a   integer NOT NULL,
    b   integer NOT NULL,
    c   integer NOT NULL
);
-- Prima l'indice libero, poi il vincolo: l'ordine per OID terrebbe il primo.
CREATE UNIQUE INDEX pgtap_dup_a_libero ON vendite.pgtap_dup_indici (a);
ALTER TABLE vendite.pgtap_dup_indici ADD CONSTRAINT pgtap_dup_a_vincolo UNIQUE (a);

SELECT is(
    (SELECT count_of_indexes FROM dbops.vw_duplicate_indexes
      WHERE schema_name = 'vendite' AND table_name = 'pgtap_dup_indici'
        AND index_columns = ARRAY['a']),
    2::bigint,
    '1) due UNIQUE identici: un gruppo di due');

SELECT is(
    (SELECT indice_da_tenere FROM dbops.vw_duplicate_indexes
      WHERE table_name = 'pgtap_dup_indici' AND index_columns = ARRAY['a']),
    'pgtap_dup_a_vincolo',
    '2) si tiene l''indice che regge il vincolo, anche se e'' nato dopo');

SELECT is(
    (SELECT indici_da_droppare FROM dbops.vw_duplicate_indexes
      WHERE table_name = 'pgtap_dup_indici' AND index_columns = ARRAY['a']),
    ARRAY['pgtap_dup_a_libero']::text[],
    '3) ... e si propone il DROP del libero');

-- La replica identity su un indice UNIQUE, con un gemello libero nato prima.
CREATE UNIQUE INDEX pgtap_dup_b_libero ON vendite.pgtap_dup_indici (b);
CREATE UNIQUE INDEX pgtap_dup_b_replica ON vendite.pgtap_dup_indici (b);
ALTER TABLE vendite.pgtap_dup_indici REPLICA IDENTITY USING INDEX pgtap_dup_b_replica;

SELECT is(
    (SELECT format('%s|%s', indice_da_tenere, array_to_string(indici_da_droppare, ','))
       FROM dbops.vw_duplicate_indexes
      WHERE table_name = 'pgtap_dup_indici' AND index_columns = ARRAY['b']),
    'pgtap_dup_b_replica|pgtap_dup_b_libero',
    '4) la replica identity si tiene, il gemello libero si propone');

-- Due vincoli UNIQUE identici: nessuno dei due si puo' togliere da qui.
ALTER TABLE vendite.pgtap_dup_indici ADD CONSTRAINT pgtap_dup_c_uno UNIQUE (c);
ALTER TABLE vendite.pgtap_dup_indici ADD CONSTRAINT pgtap_dup_c_due UNIQUE (c);

SELECT is(
    (SELECT indici_da_droppare FROM dbops.vw_duplicate_indexes
      WHERE table_name = 'pgtap_dup_indici' AND index_columns = ARRAY['c']),
    ARRAY[]::text[],
    '5) due indici di vincolo identici: nessuno proposto per il DROP');

SELECT * FROM finish();

ROLLBACK;
