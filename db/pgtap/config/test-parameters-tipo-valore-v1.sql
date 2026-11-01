-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: la forma del valore di un parametro (config.parameters.tipo_valore),
--       il BB che la giudica e i due guard che la fanno rispettare in
--       scrittura; il lettore fail-loud che prende la regola dal BB.
--       Brief: brief-db-liste-datatable-grezze-secondo-giro §4.6.1 (D-5).
--       Migrations:
--         20261031-53 (colonna + CHECK, DEFAULT temporaneo) · 90_end/20261031-59 (via il DEFAULT)
--         20261031-54 (script.fn_valore_parametro_non_conforme)
--         20261031-55 (script.fn_intero_positivo_da_testo dal BB)
--         20261031-56 (guard su config.parameters, a07) · 20261031-57 (guard sugli override, a07)
--         20261101-01, 20261101-02 (il campo sotto 'campo': esce sul canale COLUMN, §7.7.1)
--
-- ⭐ I parametri sono COSTRUITI dal test. L'unico parametro del catalogo che il
--   test nomina e' LISTINI_SCADENZA_PREAVVISO_GIORNI (19), il caso da cui nasce
--   il brief: quel test presidia la DICHIARAZIONE del seed, non una popolazione.
-- ⚠️ Il test 4 prova BB ⊇ CHECK (ogni forma del CHECK ha il suo ramo). Il
--   verso opposto non serve: un ramo del BB fuori dal CHECK non si puo'
--   scrivere su nessuna riga.
--
-- Elenco test (plan 23):
--  1) colonna tipo_valore presente
--  2) NOT NULL
--  3) senza DEFAULT (lo toglie 90_end)
--  4) ogni forma del CHECK chk_parameters_tipo_valore ha un ramo nel BB
--  5) un tipo fuori vocabolario -> E_SCRIPT_CHIAMATA_NON_VALIDA
--  6) il BB sulle forme: nessun caso della tabella dissente
--  7) INSERT di un parametro INTERO_POSITIVO con default '0' -> E_PARAMETER_VALORE_NON_CONFORME
--  8) INSERT con default '15' -> ammesso
--  9) UPDATE del solo default_value verso 'abc' -> rifiutato
-- 10) override '0' -> rifiutato, con la forma attesa nel messaggio
-- 11) override '30' -> ammesso
-- 12) UPDATE del solo overridden_value verso 'abc' -> rifiutato
-- 13) cambio di tipo con un override che non ne ha la forma -> E_PARAMETER_OVERRIDE_NON_CONFORME_AL_TIPO
-- 14) idem con l'override solo spento
-- 15) cambio di tipo che ogni valore rispetta -> passa
-- 16) ordine: su un parametro senza override, con un valore fuori forma, parla a05
-- 17) ordine dei trigger per nome: a05 < a07 < a10 sugli override, a07 < a10 sui parametri
-- 18) il caso del brief: un override '0' di LISTINI_SCADENZA_PREAVVISO_GIORNI -> rifiutato
-- 19) il lettore fail-loud: fn_intero_positivo_da_testo('0') -> E_CONFIG_MANCANTE
-- 20) il lettore: fn_intero_positivo_da_testo('15') = 15
-- 21) il campo esce sul canale COLUMN: override fuori forma -> value
-- 22) idem, default fuori forma -> default_value
-- 23) idem, cambio di tipo con un override fuori forma -> tipo_valore
--
-- Scopo:
--  - il difetto che chiude: un override «0» o «abc» del preavviso si salvava, e
--    l'errore arrivava in lettura (E_CONFIG_MANCANTE, un 500) sulla lista listini.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(23);

-- ============================================================
-- 1-3) La colonna
-- ============================================================
SELECT has_column('config', 'parameters', 'tipo_valore', '1) colonna tipo_valore presente');
SELECT col_not_null('config', 'parameters', 'tipo_valore', '2) tipo_valore NOT NULL');
SELECT col_hasnt_default('config', 'parameters', 'tipo_valore',
    '3) tipo_valore senza DEFAULT: un parametro nuovo dichiara la sua forma');

-- ============================================================
-- 4-6) Il BB delle forme
-- ============================================================
SELECT lives_ok(
    $q$DO $do$
      DECLARE v_tipo text;
      BEGIN
        FOR v_tipo IN
          SELECT m[1]
            FROM pg_catalog.pg_constraint c,
                 regexp_matches(pg_get_constraintdef(c.oid), '''([A-Z_]+)''', 'g') AS m
           WHERE c.conrelid = 'config.parameters'::regclass
             AND c.conname  = 'chk_parameters_tipo_valore'
        LOOP
          PERFORM script.fn_valore_parametro_non_conforme(v_tipo, 'x');
        END LOOP;
        IF NOT FOUND THEN
          RAISE EXCEPTION 'nessuna forma letta dal CHECK: il test girerebbe a vuoto';
        END IF;
      END $do$$q$,
    '4) ogni forma del CHECK chk_parameters_tipo_valore ha un ramo nel BB');

SELECT throws_like(
    $$SELECT script.fn_valore_parametro_non_conforme('PIPPO', '1')$$,
    '%tipo del valore sconosciuto: PIPPO%',
    '5) un tipo fuori vocabolario -> E_SCRIPT_CHIAMATA_NON_VALIDA');

-- Ogni caso: (tipo, valore, conforme atteso). Il test elenca i casi che
-- dissentono: NULL = nessuno.
SELECT is(
    (SELECT string_agg(format('%s %L', t.tipo, t.valore), '; ' ORDER BY t.tipo, t.valore)
       FROM (VALUES
         ('BOOLEANO', 'true', true), ('BOOLEANO', 'false', true),
         ('BOOLEANO', 'True', false), ('BOOLEANO', 't', false), ('BOOLEANO', '', false),
         ('INTERO_POSITIVO', '1', true), ('INTERO_POSITIVO', '999999', true),
         ('INTERO_POSITIVO', '0', false), ('INTERO_POSITIVO', '015', false),
         ('INTERO_POSITIVO', '-3', false), ('INTERO_POSITIVO', ' 5', false),
         ('INTERO_POSITIVO', '1000000', false), ('INTERO_POSITIVO', '1.5', false),
         ('INTERO_POSITIVO', 'abc', false), ('INTERO_POSITIVO', '', false),
         ('INTERO_NON_NEGATIVO', '0', true), ('INTERO_NON_NEGATIVO', '12', true),
         ('INTERO_NON_NEGATIVO', '00', false), ('INTERO_NON_NEGATIVO', '-1', false),
         ('DECIMALE_POSITIVO', '0.5', true), ('DECIMALE_POSITIVO', '1', true),
         ('DECIMALE_POSITIVO', '0', false), ('DECIMALE_POSITIVO', '0.000', false),
         ('DECIMALE_POSITIVO', '1,5', false), ('DECIMALE_POSITIVO', '.5', false),
         ('DECIMALE_NON_NEGATIVO', '0', true), ('DECIMALE_NON_NEGATIVO', '12.25', true),
         ('DECIMALE_NON_NEGATIVO', '1.1234567', false), ('DECIMALE_NON_NEGATIVO', '', false),
         ('DECIMALE_NON_NEGATIVO_O_VUOTO', '', true), ('DECIMALE_NON_NEGATIVO_O_VUOTO', '77.47', true),
         ('DECIMALE_NON_NEGATIVO_O_VUOTO', ' ', false), ('DECIMALE_NON_NEGATIVO_O_VUOTO', 'x', false),
         ('DATA', '2020-01-01', true), ('DATA', '2026-02-30', false),
         ('DATA', '01/01/2020', false), ('DATA', '2020-1-1', false),
         ('TESTO', '', true), ('TESTO', 'qualunque cosa', true)
       ) AS t(tipo, valore, conforme)
      WHERE (script.fn_valore_parametro_non_conforme(t.tipo, t.valore) IS NULL) IS DISTINCT FROM t.conforme),
    NULL,
    '6) il BB sulle forme: nessun caso della tabella dissente');

-- ============================================================
-- 7-9) Il guard sul default (config.parameters, a07)
-- ============================================================
SELECT throws_like(
    $$INSERT INTO config.parameters (id, code, default_value, description, ammette_override, tipo_valore)
      VALUES (99940, '_TEST_TIPO_INT_', '0', 'pgTAP tipo_valore', true, 'INTERO_POSITIVO')$$,
    '%«0» del parametro _TEST_TIPO_INT_ non va bene%',
    '7) INSERT INTERO_POSITIVO con default ''0'' -> E_PARAMETER_VALORE_NON_CONFORME');

SELECT lives_ok(
    $$INSERT INTO config.parameters (id, code, default_value, description, ammette_override, tipo_valore)
      VALUES (99940, '_TEST_TIPO_INT_', '15', 'pgTAP tipo_valore', true, 'INTERO_POSITIVO'),
             (99941, '_TEST_TIPO_SENZA_OVR_', '15', 'pgTAP tipo_valore: vale per tutti', false, 'INTERO_POSITIVO')$$,
    '8) INSERT con default ''15'' -> ammesso');

SELECT throws_like(
    $$UPDATE config.parameters SET default_value = 'abc' WHERE id = 99940$$,
    '%«abc» del parametro _TEST_TIPO_INT_ non va bene%',
    '9) UPDATE del solo default_value verso ''abc'' -> rifiutato');

-- ============================================================
-- 10-12) Il guard sugli override (a07). Ambito: la funzione.
-- ============================================================
SELECT throws_like(
    $$INSERT INTO config.parameter_overrides (parameter_id, overridden_value, function_name)
      VALUES (99940, '0', 'pgtap_tipo_valore_10')$$,
    '%«0» del parametro _TEST_TIPO_INT_ non va bene: serve un numero intero da 1 a 999999%',
    '10) override ''0'' -> rifiutato, con la forma attesa nel messaggio');

SELECT lives_ok(
    $$INSERT INTO config.parameter_overrides (id, parameter_id, overridden_value, function_name)
      VALUES (99945, 99940, '30', 'pgtap_tipo_valore_11')$$,
    '11) override ''30'' -> ammesso');

SELECT throws_like(
    $$UPDATE config.parameter_overrides SET overridden_value = 'abc' WHERE id = 99945$$,
    '%«abc» del parametro _TEST_TIPO_INT_ non va bene%',
    '12) UPDATE del solo overridden_value verso ''abc'' -> rifiutato');

-- ============================================================
-- 13-15) Il cambio di tipo (guard su config.parameters, ramo 2)
-- ============================================================
SELECT throws_like(
    $$UPDATE config.parameters SET tipo_valore = 'BOOLEANO', default_value = 'true' WHERE id = 99940$$,
    '%_TEST_TIPO_INT_ ha una personalizzazione con il valore «30»%',
    '13) cambio di tipo con un override fuori forma -> E_PARAMETER_OVERRIDE_NON_CONFORME_AL_TIPO');

UPDATE config.parameter_overrides SET attivo = false WHERE id = 99945;

SELECT throws_like(
    $$UPDATE config.parameters SET tipo_valore = 'BOOLEANO', default_value = 'true' WHERE id = 99940$$,
    '%_TEST_TIPO_INT_ ha una personalizzazione con il valore «30»%',
    '14) idem con l''override solo spento (si riaccenderebbe senza passare dal guard)');

SELECT lives_ok(
    $$UPDATE config.parameters SET tipo_valore = 'INTERO_NON_NEGATIVO' WHERE id = 99940$$,
    '15) cambio di tipo che default e override rispettano -> passa');

-- ============================================================
-- 16-17) Le fasi
-- ============================================================
SELECT throws_like(
    $$INSERT INTO config.parameter_overrides (parameter_id, overridden_value, function_name)
      VALUES (99941, 'abc', 'pgtap_tipo_valore_16')$$,
    '%vale per tutti e non si personalizza%',
    '16) parametro senza override + valore fuori forma: parla a05 (non si personalizza)');

SELECT ok(
    (SELECT f.tgname < t.tgname AND t.tgname < d.tgname
       FROM pg_catalog.pg_trigger f, pg_catalog.pg_trigger t, pg_catalog.pg_trigger d
      WHERE f.tgfoid = 'config.trgfn_parameter_overrides_guard_ammette_override'::regproc
        AND t.tgfoid = 'config.trgfn_parameter_overrides_guard_tipo_valore'::regproc
        AND d.tgfoid = 'config.trgfn_parameter_overrides_fk_surrogate_dispatch'::regproc
        AND f.tgrelid = t.tgrelid AND t.tgrelid = d.tgrelid)
    AND
    (SELECT t.tgname < d.tgname
       FROM pg_catalog.pg_trigger t, pg_catalog.pg_trigger d
      WHERE t.tgfoid = 'config.trgfn_parameters_guard_tipo_valore'::regproc
        AND d.tgfoid = 'config.trgfn_parameters_fk_surrogate_dispatch'::regproc
        AND t.tgrelid = d.tgrelid),
    '17) la forma parla dopo la famiglia e prima del catalogo FK-surrogata');

-- ============================================================
-- 18) Il caso del brief, sulla dichiarazione del seed
-- ============================================================
SELECT throws_like(
    $$INSERT INTO config.parameter_overrides (parameter_id, overridden_value, function_name)
      SELECT p.id, '0', 'pgtap_tipo_valore_18'
        FROM config.parameters p
       WHERE p.code = 'LISTINI_SCADENZA_PREAVVISO_GIORNI'$$,
    '%«0» del parametro LISTINI_SCADENZA_PREAVVISO_GIORNI non va bene%',
    '18) override ''0'' del preavviso delle scadenze -> rifiutato quando si scrive');

-- ============================================================
-- 19-20) Il lettore fail-loud prende la regola dal BB
-- ============================================================
SELECT throws_like(
    $$SELECT script.fn_intero_positivo_da_testo('0', '_TEST_TIPO_INT_')$$,
    '%Configurazione mancante: parametro _TEST_TIPO_INT_ (intero positivo)%',
    '19) fn_intero_positivo_da_testo(''0'') -> E_CONFIG_MANCANTE');

SELECT is(script.fn_intero_positivo_da_testo('15', '_TEST_TIPO_INT_'), 15,
    '20) fn_intero_positivo_da_testo(''15'') = 15');

-- ============================================================
-- 21-23) Il campo da correggere esce sul canale COLUMN (§7.7.1)
-- ============================================================
-- ⭐ Il messaggio dei test 9, 12 e 13 c'era anche quando il campo non
--   arrivava: fino al 2026-11-01 i due guard lo mettevano sotto 'field', e
--   fn_log_and_raise_error porta su COLUMN solo 'campo'. Qui si legge il
--   canale, insieme al codice (CONSTRAINT), come fa il BE.
-- Stato di partenza: 99940 e' INTERO_NON_NEGATIVO con default '15' (test 15),
--   l'override 99945 vale '30' ed e' spento (test 14).
CREATE OR REPLACE FUNCTION pg_temp.codice_e_campo(p_sql text) RETURNS text
LANGUAGE plpgsql AS $$
DECLARE v_codice text; v_campo text;
BEGIN
    EXECUTE p_sql;
    RETURN NULL;
EXCEPTION WHEN SQLSTATE 'P0001' THEN
    GET STACKED DIAGNOSTICS v_codice = CONSTRAINT_NAME, v_campo = COLUMN_NAME;
    RETURN v_codice || ' / ' || v_campo;
END $$;

SELECT is(
    pg_temp.codice_e_campo($$UPDATE config.parameter_overrides SET overridden_value = 'abc' WHERE id = 99945$$),
    'E_PARAMETER_VALORE_NON_CONFORME / value',
    '21) override fuori forma: il campo value esce sul canale COLUMN');

SELECT is(
    pg_temp.codice_e_campo($$UPDATE config.parameters SET default_value = 'abc' WHERE id = 99940$$),
    'E_PARAMETER_VALORE_NON_CONFORME / default_value',
    '22) default fuori forma: il campo default_value esce sul canale COLUMN');

SELECT is(
    pg_temp.codice_e_campo($$UPDATE config.parameters SET tipo_valore = 'BOOLEANO', default_value = 'true' WHERE id = 99940$$),
    'E_PARAMETER_OVERRIDE_NON_CONFORME_AL_TIPO / tipo_valore',
    '23) cambio di tipo con un override fuori forma: il campo tipo_valore esce sul canale COLUMN');

SELECT * FROM finish();
ROLLBACK;
