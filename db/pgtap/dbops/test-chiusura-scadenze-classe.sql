-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture semina su dbops.automazione_chiusura_scadenze,
--   catalogo che a runtime NON scrive nessuno (lo popola il mirror CSV di
--   80_data), e fa DDL (una tabella di prova, un trigger, il CHECK della classe
--   tolto dentro la transazione per provare la difesa del motore).
--
-- Test: la classe dei bersagli e porta/verbo in dbops.fn_apply_chiusura_scadenze
-- Brief: brief-db-revisione-dbops, giro 9, blocco 9b (§24: D38 con Q5, D39 con N4).
--   Prima stesura: brief-db-processi-automatici-identita-e-perimetro §6.
--
-- Elenco test (plan 11):
--  1) automazione_chiusura_scadenze ha la colonna classe
--  2) il CHECK respinge una classe fuori vocabolario
--  3) il CHECK respinge una classe senza esecutore (MANUTENZIONE)
--  4) la colonna e' NOT NULL: una riga nuova deve dichiararsi
--  5) i bersagli seedati sono tutti DOMINIO
--  6) il motore non ha piu' p_classe: una sola firma, senza argomenti
--  7) la chiamata senza argomenti funziona (handler della coda)
--  8) ⭐ difesa del motore: un bersaglio non DOMINIO (CHECK tolto nella
--     transazione) -> E_AUTOMAZIONE_CHIUSURA_CONFIG_INVALIDA, motivo classe
--  9) ⭐ D39: un verbo dichiarato si usa anche nel ramo VARCHAR (il conteggio e'
--     quello del verbo)
-- 10) ... e l'UPDATE dinamico non e' girato (la riga scaduta e' ancora ATTIVO)
-- 11) ⭐ D39: una testata VARCHAR sotto la porta senza verbo -> motivo
--     porta_senza_verbo_di_chiusura (prima l'UPDATE dinamico la colpiva)
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(11);

-- Codice e frase di un'eccezione P0001 di fn_log_and_raise_error: il codice
-- viaggia su CONSTRAINT_NAME, il motivo nella frase (il VARIADIC).
CREATE OR REPLACE FUNCTION pg_temp.errore(p_sql text) RETURNS text
LANGUAGE plpgsql AS $$
DECLARE v_c text; v_m text;
BEGIN
    EXECUTE p_sql;
    RETURN NULL;
EXCEPTION WHEN SQLSTATE 'P0001' THEN
    GET STACKED DIAGNOSTICS v_c = CONSTRAINT_NAME, v_m = MESSAGE_TEXT;
    RETURN v_c || ' | ' || v_m;
END $$;

-- ============================================================
-- 1..5. La colonna, il vocabolario, il cancello, il seed
-- ============================================================
SELECT has_column('dbops', 'automazione_chiusura_scadenze', 'classe',
                  '1) automazione_chiusura_scadenze ha la colonna classe');

SELECT throws_ok(
    $$INSERT INTO dbops.automazione_chiusura_scadenze
          (id, schema_tabella, nome_tabella, col_stato, tipo_stato,
           stato_attivo_codice, stato_chiuso_codice, classe)
      VALUES (9601, 'vendite', 'pgtap_finto', 'stato', 'VARCHAR',
              'ATTIVO', 'CHIUSO', 'FANTASIA')$$,
    '23514', NULL,
    '2) il CHECK respinge una classe fuori vocabolario');

SELECT throws_ok(
    $$INSERT INTO dbops.automazione_chiusura_scadenze
          (id, schema_tabella, nome_tabella, col_stato, tipo_stato,
           stato_attivo_codice, stato_chiuso_codice, classe)
      VALUES (9601, 'vendite', 'pgtap_finto', 'stato', 'VARCHAR',
              'ATTIVO', 'CHIUSO', 'MANUTENZIONE')$$,
    '23514', NULL,
    '3) il CHECK respinge una classe senza esecutore: solo DOMINIO');

SELECT throws_ok(
    $$INSERT INTO dbops.automazione_chiusura_scadenze
          (id, schema_tabella, nome_tabella, col_stato, tipo_stato,
           stato_attivo_codice, stato_chiuso_codice)
      VALUES (9602, 'vendite', 'pgtap_finto', 'stato', 'VARCHAR',
              'ATTIVO', 'CHIUSO')$$,
    '23502', NULL,
    '4) una riga senza classe non entra');

SELECT is_empty(
    $$SELECT nome_tabella FROM dbops.automazione_chiusura_scadenze
       WHERE attivo AND classe <> 'DOMINIO'$$,
    '5) i bersagli seedati sono tutti DOMINIO');

-- ============================================================
-- 6..7. La firma
-- ============================================================
SELECT is(
    (SELECT string_agg(p.oid::regprocedure::text, ',')
       FROM pg_proc p
      WHERE p.pronamespace = 'dbops'::regnamespace
        AND p.proname = 'fn_apply_chiusura_scadenze'),
    'dbops.fn_apply_chiusura_scadenze()',
    '6) il motore ha una firma sola, senza p_classe');

SELECT lives_ok(
    $$SELECT dbops.fn_apply_chiusura_scadenze()$$,
    '7) la chiamata senza argomenti funziona (handler della coda)');

-- ============================================================
-- 8..11. Il motore, isolato dal seed
-- ============================================================
-- Le righe del seed si spengono: il giro lavora solo i casi costruiti qui.
UPDATE dbops.automazione_chiusura_scadenze SET attivo = false WHERE id < 9000;

-- Una testata di prova VARCHAR, con una riga ATTIVO scaduta.
CREATE TABLE dbops.pgtap_chiusura_testata (
    id        bigint PRIMARY KEY,
    stato     varchar(20) NOT NULL,
    valido_al date
);
INSERT INTO dbops.pgtap_chiusura_testata VALUES (1, 'ATTIVO', DATE '2020-01-01');

-- Un verbo di chiusura di prova: risponde 42 e non tocca la testata.
CREATE FUNCTION dbops.pgtap_verbo_chiusura() RETURNS bigint
LANGUAGE sql AS $$ SELECT 42::bigint $$;

-- 8) La difesa del motore: il CHECK si toglie nella transazione per far
--    entrare una riga che il registro non ammette.
ALTER TABLE dbops.automazione_chiusura_scadenze
    DROP CONSTRAINT chk_automazione_chiusura_scadenze_classe;
INSERT INTO dbops.automazione_chiusura_scadenze
      (id, schema_tabella, nome_tabella, col_stato, col_valido_al, tipo_stato,
       stato_attivo_codice, stato_chiuso_codice, classe, attivo)
VALUES (9603, 'dbops', 'pgtap_chiusura_testata', 'stato', 'valido_al', 'VARCHAR',
        'ATTIVO', 'CHIUSO', 'MANUTENZIONE', true);

SELECT matches(pg_temp.errore($$SELECT dbops.fn_apply_chiusura_scadenze()$$),
    '^E_AUTOMAZIONE_CHIUSURA_CONFIG_INVALIDA \| .*classe DOMINIO',
    '8) un bersaglio non DOMINIO: il motore lo rifiuta (non ha un esecutore)');

DELETE FROM dbops.automazione_chiusura_scadenze WHERE id = 9603;

-- 9-10) Ramo VARCHAR con un verbo dichiarato.
INSERT INTO dbops.automazione_chiusura_scadenze
      (id, schema_tabella, nome_tabella, col_stato, col_valido_al, tipo_stato,
       stato_attivo_codice, stato_chiuso_codice, classe, attivo, verbo_chiusura)
VALUES (9604, 'dbops', 'pgtap_chiusura_testata', 'stato', 'valido_al', 'VARCHAR',
        'ATTIVO', 'CHIUSO', 'DOMINIO', true, 'dbops.pgtap_verbo_chiusura');

SELECT is((dbops.fn_apply_chiusura_scadenze() ->> 'dbops.pgtap_chiusura_testata')::int, 42,
    '9) ramo VARCHAR: il verbo dichiarato si usa, e il conteggio e'' il suo');

SELECT is((SELECT stato FROM dbops.pgtap_chiusura_testata WHERE id = 1)::text, 'ATTIVO',
    '10) ... e l''UPDATE dinamico non e'' girato');

-- 11) Ramo VARCHAR sotto la porta, senza verbo.
UPDATE dbops.automazione_chiusura_scadenze SET verbo_chiusura = NULL WHERE id = 9604;
CREATE TRIGGER trg_pgtap_porta BEFORE UPDATE ON dbops.pgtap_chiusura_testata
    FOR EACH ROW EXECUTE FUNCTION script.trgfn_doc_stato_solo_dal_verbo();

SELECT matches(pg_temp.errore($$SELECT dbops.fn_apply_chiusura_scadenze()$$),
    '^E_AUTOMAZIONE_CHIUSURA_CONFIG_INVALIDA \| .*non ha il verbo di chiusura',
    '11) ramo VARCHAR sotto la porta senza verbo: configurazione non valida, non un UPDATE rifiutato');

SELECT * FROM finish();

ROLLBACK;
