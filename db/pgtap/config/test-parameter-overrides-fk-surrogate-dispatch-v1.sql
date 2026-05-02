-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: framework FK-surrogata - dispatcher su config.parameter_overrides.
--       Migrations:
--         20260502-06 (config.trgfn_parameter_overrides_fk_surrogate_dispatch + trigger)
--
-- Why: chiude la lacuna del guard precedente (DEFAULT_TIPO_SOGGETTO_DETTAGLIO,
-- droppato in 20260502-07) che NON scattava sugli override. Il dispatcher
-- speculare applica gli stessi vincoli del default ai valori override.
--
-- Indice test (1..7):
--   1) INSERT override su parametro DEFAULT_UTILITY con codice_interno valido
--      (utility seed) -> ammesso.
--   2) INSERT override su DEFAULT_UTILITY con valore inesistente -> raise
--      E_PARAMETER_OVERRIDE_VALUE_INVALID (P0001).
--   3) INSERT override su parametro fuori registry (es. login_max_tentativi_falliti)
--      con valore arbitrario -> ammesso (dispatcher no-op via lookup runtime).
--   4) INSERT override su DEFAULT_TIPO_SOGGETTO_DETTAGLIO_CL con
--      codice_interno valido -> ammesso (pattern LIKE).
--   5) INSERT override su DEFAULT_TIPO_SOGGETTO_DETTAGLIO_CL con valore
--      inesistente -> raise.
--   6) UPDATE overridden_value verso valore valido (sul record creato in 1)
--      -> ammesso.
--   7) UPDATE overridden_value verso valore invalido -> raise.
-- ------------------------------------------------------------

BEGIN;
SELECT plan(7);

-- =========================================================
-- Setup: id parametri esistenti + valori validi.
-- =========================================================
CREATE TEMP TABLE tmp_ctx_param AS
SELECT
    (SELECT id FROM config.parameters WHERE code = 'DEFAULT_UTILITY')                       AS pid_utility,
    (SELECT id FROM config.parameters WHERE code = 'DEFAULT_TIPO_SOGGETTO_DETTAGLIO_CL')    AS pid_tsd_cl,
    (SELECT id FROM config.parameters WHERE code = 'login_max_tentativi_falliti')           AS pid_login,
    (SELECT codice_interno FROM config.utilities ORDER BY id LIMIT 1)                       AS util_ok,
    (SELECT codice_interno FROM config.tipi_soggetto_dettaglio ORDER BY id LIMIT 1)         AS tsd_ok;

-- ============================================================
-- 1) INSERT override valido su DEFAULT_UTILITY -> ammesso
-- ============================================================
SELECT lives_ok(
    $$INSERT INTO config.parameter_overrides
        (parameter_id, overridden_value, function_name)
      SELECT pid_utility, util_ok, 'pgtap_test_override_v1_caso1'
        FROM tmp_ctx_param$$,
    'INSERT override DEFAULT_UTILITY con codice_interno utility valido ammesso'
);

-- ============================================================
-- 2) INSERT override invalido su DEFAULT_UTILITY -> raise
-- ============================================================
SELECT throws_ok(
    $$INSERT INTO config.parameter_overrides
        (parameter_id, overridden_value, function_name)
      SELECT pid_utility, 'XYZ_INESISTENTE', 'pgtap_test_override_v1_caso2'
        FROM tmp_ctx_param$$,
    'P0001',
    NULL,
    'INSERT override DEFAULT_UTILITY con valore inesistente -> P0001 (E_PARAMETER_OVERRIDE_VALUE_INVALID)'
);

-- ============================================================
-- 3) INSERT override su parametro fuori registry -> ammesso
-- ============================================================
SELECT lives_ok(
    $$INSERT INTO config.parameter_overrides
        (parameter_id, overridden_value, function_name)
      SELECT pid_login, '99', 'pgtap_test_override_v1_caso3'
        FROM tmp_ctx_param$$,
    'INSERT override su parametro fuori registry con valore arbitrario ammesso'
);

-- ============================================================
-- 4) INSERT override su DEFAULT_TIPO_SOGGETTO_DETTAGLIO_CL valido (LIKE)
-- ============================================================
SELECT lives_ok(
    $$INSERT INTO config.parameter_overrides
        (parameter_id, overridden_value, function_name)
      SELECT pid_tsd_cl, tsd_ok, 'pgtap_test_override_v1_caso4'
        FROM tmp_ctx_param$$,
    'INSERT override DEFAULT_TIPO_SOGGETTO_DETTAGLIO_CL con valore valido ammesso'
);

-- ============================================================
-- 5) INSERT override su DEFAULT_TIPO_SOGGETTO_DETTAGLIO_CL invalido -> raise
-- ============================================================
SELECT throws_ok(
    $$INSERT INTO config.parameter_overrides
        (parameter_id, overridden_value, function_name)
      SELECT pid_tsd_cl, 'XYZ_INESISTENTE', 'pgtap_test_override_v1_caso5'
        FROM tmp_ctx_param$$,
    'P0001',
    NULL,
    'INSERT override DEFAULT_TIPO_SOGGETTO_DETTAGLIO_CL invalido -> P0001'
);

-- ============================================================
-- 6) UPDATE overridden_value verso valido -> ammesso
--    Lavora sull'override creato in caso 1 (function_name unique).
-- ============================================================
SELECT lives_ok(
    $$UPDATE config.parameter_overrides
         SET overridden_value = (SELECT util_ok FROM tmp_ctx_param)
       WHERE function_name = 'pgtap_test_override_v1_caso1'$$,
    'UPDATE overridden_value verso valido ammesso'
);

-- ============================================================
-- 7) UPDATE overridden_value verso invalido -> raise
-- ============================================================
SELECT throws_ok(
    $$UPDATE config.parameter_overrides
         SET overridden_value = 'XYZ_INESISTENTE'
       WHERE function_name = 'pgtap_test_override_v1_caso1'$$,
    'P0001',
    NULL,
    'UPDATE overridden_value verso valore inesistente -> P0001'
);

SELECT * FROM finish();
ROLLBACK;
