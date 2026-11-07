-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: il registro dei modi dell'emittente non si scrive dall'applicazione.
-- Riferimento: brief-db-revisione-dbops, blocco 4b (D21).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - dbops.emittente_modi lo scrive solo il proprietario della tabella (il
--     migrate, dal seed): dall'applicazione INSERT, UPDATE, DELETE e TRUNCATE
--     sono respinti con E_EMITTENTE_MODI_NON_SCRIVIBILE, anche quando il giro dei
--     grant le ha dato i privilegi sulla tabella.
--
-- Elenco test (plan 4):
--   1) INSERT respinto
--   2) UPDATE respinto
--   3) DELETE respinto
--   4) TRUNCATE respinto (dal guard, o prima dalla FK di dbops.processi_bersagli: 0A000)
--
-- ⚠️ Gira come applicazione: da owner i quattro test sono rossi per
--   costruzione (il proprietario scrive). Se il ruolo che lo lancia non ha il
--   privilegio sulla tabella, PostgreSQL si ferma prima del guard (42501): il
--   test lo dice con uno skip, non lo conta come verde.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

-- pgtap-contesto: escluso — il file scrive (o prova a scrivere) solo una tabella
--   di catalogo di dbops, che non e' sotto RLS: nessuna veste da aprire.

SELECT plan(4);

CREATE FUNCTION pg_temp.codice_di(p_sql text) RETURNS text
LANGUAGE plpgsql AS $$
DECLARE v_c text;
BEGIN
    EXECUTE p_sql;
    RETURN NULL;
EXCEPTION
    WHEN SQLSTATE 'P0001' THEN
        GET STACKED DIAGNOSTICS v_c = CONSTRAINT_NAME;
        RETURN v_c;
    WHEN OTHERS THEN
        RETURN 'SQLSTATE ' || SQLSTATE;
END $$;

SELECT CASE WHEN has_table_privilege('dbops.emittente_modi', 'INSERT')
    THEN is(pg_temp.codice_di($$INSERT INTO dbops.emittente_modi (modo, schema_tabella, nome_tabella, forma, colonna)
                                VALUES ('pgtap_app', 'vendite', 'ddt', 'PK', 'emittente_fiscale_id')$$),
            'E_EMITTENTE_MODI_NON_SCRIVIBILE',
            '1) l''applicazione non aggiunge un modo')
    ELSE skip('chi lancia non ha INSERT su dbops.emittente_modi: il guard non si raggiunge', 1)
END;

SELECT CASE WHEN has_table_privilege('dbops.emittente_modi', 'UPDATE')
    THEN is(pg_temp.codice_di($$UPDATE dbops.emittente_modi SET colonna = colonna WHERE modo = 'ddt'$$),
            'E_EMITTENTE_MODI_NON_SCRIVIBILE',
            '2) l''applicazione non cambia la strada di un modo')
    ELSE skip('chi lancia non ha UPDATE su dbops.emittente_modi: il guard non si raggiunge', 1)
END;

SELECT CASE WHEN has_table_privilege('dbops.emittente_modi', 'DELETE')
    THEN is(pg_temp.codice_di($$DELETE FROM dbops.emittente_modi WHERE modo = 'ddt'$$),
            'E_EMITTENTE_MODI_NON_SCRIVIBILE',
            '3) l''applicazione non toglie un modo')
    ELSE skip('chi lancia non ha DELETE su dbops.emittente_modi: il guard non si raggiunge', 1)
END;

SELECT CASE WHEN has_table_privilege('dbops.emittente_modi', 'TRUNCATE')
    THEN ok(pg_temp.codice_di($$TRUNCATE dbops.emittente_modi$$)
              IN ('E_EMITTENTE_MODI_NON_SCRIVIBILE', 'SQLSTATE 0A000'),
            '4) l''applicazione non svuota il registro (lo ferma il guard, o prima la FK dei bersagli che lo riferiscono)')
    ELSE skip('chi lancia non ha TRUNCATE su dbops.emittente_modi: il guard non si raggiunge', 1)
END;

SELECT * FROM finish();
ROLLBACK;
