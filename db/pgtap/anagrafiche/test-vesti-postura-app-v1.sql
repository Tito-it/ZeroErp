-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: la postura dell'applicazione sulle vesti — legge e inserisce, non
--       aggiorna e non cancella: lo stato della veste lo cambiano i verbi
-- ChangeSet: 90_end/20261127-09 (il forward), la lista v_tabelle_app_solo_insert
--            del loop 90_end/ci_apply/20260205-41, il blocco «LE VESTI SI CAMBIANO
--            DAI VERBI» di scripts/sql/provision_zeroerp.sql
-- Brief: brief-db-accessi-area-clienti, passo 3c
--
-- ⭐ È il presidio delle TRE sedi (linee-guida-sql §11.8): sul database ricostruito
--   da zero il provisioning gira per ultimo, e senza la sua riga riaprirebbe
--   UPDATE e DELETE in silenzio.
-- Gira come l'applicazione (runner di default): 3 e 4 provano il rifiuto vero.
--   Da proprietario i privilegi dell'app si leggono lo stesso (1, 2), ma 3 e 4
--   passerebbero la scrittura: sono rossi per costruzione con PGTAP_RUNNER=owner.
--
-- Elenco test (plan 4):
--    1) l'app ha SELECT e INSERT sulla tabella
--    2) l'app non ha UPDATE ne' DELETE, nemmeno su una colonna
--    3) un UPDATE diretto dell'app si ferma col permesso negato (42501)
--    4) un DELETE diretto dell'app si ferma col permesso negato (42501)
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(4);

-- Esegue un'istruzione e ne restituisce lo SQLSTATE, 'ok' se passa.
CREATE OR REPLACE FUNCTION pg_temp.sqlstate(p_sql text) RETURNS text
LANGUAGE plpgsql AS $$
BEGIN
    EXECUTE p_sql;
    RETURN 'ok';
EXCEPTION WHEN OTHERS THEN
    RETURN SQLSTATE;
END $$;

SELECT is(
    format('%s|%s',
           has_table_privilege('zeroerp_app', 'anagrafiche.identita_digitali', 'SELECT'),
           has_table_privilege('zeroerp_app', 'anagrafiche.identita_digitali', 'INSERT')),
    't|t',
    '1) l''app legge e inserisce le vesti');

SELECT is(
    format('%s|%s|%s',
           has_table_privilege('zeroerp_app', 'anagrafiche.identita_digitali', 'UPDATE'),
           has_table_privilege('zeroerp_app', 'anagrafiche.identita_digitali', 'DELETE'),
           has_any_column_privilege('zeroerp_app', 'anagrafiche.identita_digitali', 'UPDATE')),
    'f|f|f',
    '2) l''app non aggiorna e non cancella le vesti, nemmeno una colonna');

SELECT is(
    pg_temp.sqlstate('UPDATE anagrafiche.identita_digitali SET invito_inviato_at = invito_inviato_at WHERE false'),
    '42501',
    '3) un UPDATE diretto dell''app: permesso negato');

SELECT is(
    pg_temp.sqlstate('DELETE FROM anagrafiche.identita_digitali WHERE false'),
    '42501',
    '4) un DELETE diretto dell''app: permesso negato');

SELECT * FROM finish();
ROLLBACK;
