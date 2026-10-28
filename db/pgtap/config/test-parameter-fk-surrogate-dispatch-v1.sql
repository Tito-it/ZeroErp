-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: framework FK-surrogata - dispatcher su config.parameters.
--       Migrations:
--         20260502-03 (registry parameter_fk_surrogate)
--         20260502-04 (script.fn_check_parameter_fk_surrogate)
--         20260502-05 (config.trgfn_parameters_fk_surrogate_dispatch + trigger)
--         20260502-07 (DROP guard ad-hoc legacy DEFAULT_TIPO_SOGGETTO_DETTAGLIO)
--
-- Indice test (1..14):
--   1)  Registry seedato: pattern DEFAULT_TIPO_SOGGETTO_DETTAGLIO_% (LIKE)
--       presente e abilitato.
--   2)  Registry seedato: pattern DEFAULT_UTILITY (EXACT) presente e abilitato.
--   3)  Lookup applicativo DEFAULT_TIPO_SOGGETTO_DETTAGLIO_CL via
--       fn_get_parameter_full ritorna valore non NULL (continuita' v1).
--   4)  fn_check_parameter_fk_surrogate: NULL passa.
--   5)  fn_check_parameter_fk_surrogate: code fuori registry passa.
--   6)  fn_check_parameter_fk_surrogate: pattern EXACT, valore valido -> true.
--   7)  fn_check_parameter_fk_surrogate: pattern EXACT, valore invalido -> false.
--   8)  fn_check_parameter_fk_surrogate: pattern LIKE, valore valido -> true.
--   9)  fn_check_parameter_fk_surrogate: pattern LIKE, valore invalido -> false.
--   10) INSERT parameters con code DEFAULT_TIPO_SOGGETTO_DETTAGLIO_<X> e
--       default_value valido -> ammesso.
--   11) INSERT parameters con code DEFAULT_TIPO_SOGGETTO_DETTAGLIO_<X> e
--       default_value invalido -> raise E_PARAMETER_DEFAULT_VALUE_INVALID.
--   12) UPDATE default_value su record CL pre-seedato verso valore invalido
--       -> raise.
--   13) INSERT con code FUORI registry (code arbitrario) e default_value
--       arbitrario -> ammesso (dispatcher no-op via lookup runtime).
--   14) UPDATE solo description su CL pre-seedato -> dispatcher non scatta
--       (clausola OF code, default_value).
--
-- Note: il guard legacy ad-hoc DEFAULT_TIPO_SOGGETTO_DETTAGLIO_INVALID
-- (codice errore E_PARAMETER_DEFAULT_TIPO_SOGGETTO_INVALID, id 399) e'
-- stato sostituito dal codice generico E_PARAMETER_DEFAULT_VALUE_INVALID
-- (id 422). I test 11/12 verificano SQLSTATE P0001 (raise generico).
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file sarebbe verde per sottrazione. IMMEDIATE li riporta a scattare a fine
--   di ogni istruzione. In testa e non in coda: in coda scatterebbero dopo il
--   cleanup, su righe ormai cancellate.
--   Brief: brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(14);

-- =========================================================
-- Setup: prendi un codice_interno valido da tipi_soggetto_dettaglio
-- e da utilities per i test "valore valido".
-- =========================================================
CREATE TEMP TABLE tmp_ctx_tsd AS
SELECT codice_interno
  FROM config.tipi_soggetto_dettaglio
 ORDER BY id
 LIMIT 1;

CREATE TEMP TABLE tmp_ctx_util AS
SELECT codice_interno
  FROM config.utilities
 ORDER BY id
 LIMIT 1;

-- ============================================================
-- 1) Registry: pattern LIKE DEFAULT_TIPO_SOGGETTO_DETTAGLIO_%
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM config.parameter_fk_surrogate
         WHERE code_pattern = 'DEFAULT_TIPO_SOGGETTO_DETTAGLIO_%'
           AND match_mode   = 'LIKE'
           AND target_schema = 'config'
           AND target_table  = 'tipi_soggetto_dettaglio'
           AND target_column = 'codice_interno'
           AND enabled
    ),
    'Registry seedato: pattern DEFAULT_TIPO_SOGGETTO_DETTAGLIO_% (LIKE) abilitato'
);

-- ============================================================
-- 2) Registry: pattern EXACT DEFAULT_UTILITY
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM config.parameter_fk_surrogate
         WHERE code_pattern = 'DEFAULT_UTILITY'
           AND match_mode   = 'EXACT'
           AND target_schema = 'config'
           AND target_table  = 'utilities'
           AND target_column = 'codice_interno'
           AND enabled
    ),
    'Registry seedato: pattern DEFAULT_UTILITY (EXACT) abilitato'
);

-- ============================================================
-- 3) Lookup applicativo continuita' v1
-- ============================================================
SELECT ok(
    (SELECT script.fn_get_parameter_full('DEFAULT_TIPO_SOGGETTO_DETTAGLIO_CL'))
        IS NOT NULL,
    'fn_get_parameter_full(DEFAULT_TIPO_SOGGETTO_DETTAGLIO_CL) ritorna valore non NULL'
);

-- ============================================================
-- 4) fn_check con NULL passa
-- ============================================================
SELECT is(
    script.fn_check_parameter_fk_surrogate('DEFAULT_UTILITY', NULL),
    true,
    'fn_check_parameter_fk_surrogate(*, NULL) ritorna true (short-circuit)'
);

-- ============================================================
-- 5) fn_check su code fuori registry passa
-- ============================================================
SELECT is(
    script.fn_check_parameter_fk_surrogate('PGTAP_NESSUN_PATTERN', 'qualunque'),
    true,
    'fn_check_parameter_fk_surrogate(code fuori registry, *) ritorna true'
);

-- ============================================================
-- 6) fn_check pattern EXACT, valore valido
-- ============================================================
SELECT is(
    (SELECT script.fn_check_parameter_fk_surrogate('DEFAULT_UTILITY', codice_interno)
       FROM tmp_ctx_util),
    true,
    'fn_check(DEFAULT_UTILITY, valore esistente in utilities) ritorna true'
);

-- ============================================================
-- 7) fn_check pattern EXACT, valore invalido
-- ============================================================
SELECT is(
    script.fn_check_parameter_fk_surrogate('DEFAULT_UTILITY', 'XYZ_INESISTENTE'),
    false,
    'fn_check(DEFAULT_UTILITY, valore inesistente) ritorna false'
);

-- ============================================================
-- 8) fn_check pattern LIKE, valore valido
-- ============================================================
SELECT is(
    (SELECT script.fn_check_parameter_fk_surrogate('DEFAULT_TIPO_SOGGETTO_DETTAGLIO_CL', codice_interno)
       FROM tmp_ctx_tsd),
    true,
    'fn_check(DEFAULT_TIPO_SOGGETTO_DETTAGLIO_CL, valore esistente) ritorna true'
);

-- ============================================================
-- 9) fn_check pattern LIKE, valore invalido
-- ============================================================
SELECT is(
    script.fn_check_parameter_fk_surrogate('DEFAULT_TIPO_SOGGETTO_DETTAGLIO_CL', 'XYZ_INESISTENTE'),
    false,
    'fn_check(DEFAULT_TIPO_SOGGETTO_DETTAGLIO_CL, valore inesistente) ritorna false'
);

-- ============================================================
-- 10) INSERT con default_value valido (pattern LIKE) -> ammesso
-- ============================================================
SELECT lives_ok(
    $$INSERT INTO config.parameters(id, code, default_value, description, ammette_override)
      SELECT 99001, 'DEFAULT_TIPO_SOGGETTO_DETTAGLIO_TEST_OK',
             tsd.codice_interno, 'pgTAP test row OK', true
        FROM tmp_ctx_tsd tsd$$,
    'INSERT con default_value esistente in tipi_soggetto_dettaglio ammesso'
);

-- ============================================================
-- 11) INSERT con default_value invalido (pattern LIKE) -> raise
-- ============================================================
SELECT throws_ok(
    $$INSERT INTO config.parameters(id, code, default_value, description, ammette_override)
      VALUES (99002, 'DEFAULT_TIPO_SOGGETTO_DETTAGLIO_TEST_BAD',
              'CODICE_INESISTENTE_XYZ', 'pgTAP test row BAD', true)$$,
    'P0001',
    NULL,
    'INSERT con default_value inesistente -> P0001 (E_PARAMETER_DEFAULT_VALUE_INVALID)'
);

-- ============================================================
-- 12) UPDATE su record CL pre-seedato verso valore invalido -> raise
-- ============================================================
SELECT throws_ok(
    $$UPDATE config.parameters
         SET default_value = 'CODICE_INESISTENTE_XYZ'
       WHERE code = 'DEFAULT_TIPO_SOGGETTO_DETTAGLIO_CL'$$,
    'P0001',
    NULL,
    'UPDATE default_value su CL verso valore invalido -> P0001'
);

-- ============================================================
-- 13) INSERT con code FUORI registry -> ammesso (dispatcher no-op)
--     Nota: il dispatcher non ha clausola WHEN. Il filtro e' runtime
--     via lookup nel registry. Code 'PGTAP_FUORI_REGISTRY' non matcha
--     nessun pattern -> fn_check ritorna true -> passa.
-- ============================================================
SELECT lives_ok(
    $$INSERT INTO config.parameters(id, code, default_value, description, ammette_override)
      VALUES (99003, 'PGTAP_FUORI_REGISTRY', 'VALORE_LIBERO_XYZ',
              'pgTAP test code fuori registry', true)$$,
    'INSERT con code fuori registry e default_value arbitrario ammesso'
);

-- ============================================================
-- 14) UPDATE solo description -> dispatcher non scatta (OF clause)
-- ============================================================
SELECT lives_ok(
    $$UPDATE config.parameters
         SET description = 'pgTAP UPDATE solo description'
       WHERE code = 'DEFAULT_TIPO_SOGGETTO_DETTAGLIO_CL'$$,
    'UPDATE solo description su CL ammesso (trigger OF code/default_value)'
);

SELECT * FROM finish();
ROLLBACK;
