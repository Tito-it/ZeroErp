-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: guard FK-surrogata su config.parameters per i parametri
--       DEFAULT_TIPO_SOGGETTO_DETTAGLIO_<RUOLO>.
--       Migration:
--         20260427-04-create-trgfn-parameters-guard-default-tipo-soggetto-dettaglio.
--
-- Indice test (1..7):
--   1) Lookup DEFAULT_TIPO_SOGGETTO_DETTAGLIO_CL via fn_get_parameter_full
--      ritorna il valore seedato.
--   2) Lookup DEFAULT_TIPO_SOGGETTO_DETTAGLIO_FO ritorna il valore seedato.
--   3) INSERT in parameters con code DEFAULT_TIPO_SOGGETTO_DETTAGLIO_<X>
--      e default_value esistente in tipi_soggetto_dettaglio -> ammesso.
--   4) INSERT con code DEFAULT_TIPO_SOGGETTO_DETTAGLIO_<X> e default_value
--      NON esistente -> raise E_PARAMETER_DEFAULT_TIPO_SOGGETTO_INVALID.
--   5) UPDATE del default_value sul record CL pre-seedato verso valore
--      non esistente -> raise.
--   6) INSERT con code che NON inizia per DEFAULT_TIPO_SOGGETTO_DETTAGLIO_
--      e default_value arbitrario -> ammesso (guard non scatta, clausola
--      WHEN del trigger).
--   7) UPDATE che tocca solo `description` (no code, no default_value)
--      su record CL pre-seedato -> guard non scatta (clausola `OF code,
--      default_value`).
-- ------------------------------------------------------------

BEGIN;
SELECT plan(7);

-- =========================================================
-- Setup: prendi un codice_interno valido da tipi_soggetto_dettaglio
-- per usarlo come default_value "buono" nei test.
-- =========================================================
CREATE TEMP TABLE tmp_ctx_tsd AS
SELECT codice_interno
  FROM config.tipi_soggetto_dettaglio
 ORDER BY id
 LIMIT 1;

-- ============================================================
-- 1) Lookup DEFAULT_TIPO_SOGGETTO_DETTAGLIO_CL
-- ============================================================
SELECT ok(
    (SELECT script.fn_get_parameter_full('DEFAULT_TIPO_SOGGETTO_DETTAGLIO_CL'))
        IS NOT NULL,
    'fn_get_parameter_full(DEFAULT_TIPO_SOGGETTO_DETTAGLIO_CL) ritorna valore non NULL'
);

-- ============================================================
-- 2) Lookup DEFAULT_TIPO_SOGGETTO_DETTAGLIO_FO
-- ============================================================
SELECT ok(
    (SELECT script.fn_get_parameter_full('DEFAULT_TIPO_SOGGETTO_DETTAGLIO_FO'))
        IS NOT NULL,
    'fn_get_parameter_full(DEFAULT_TIPO_SOGGETTO_DETTAGLIO_FO) ritorna valore non NULL'
);

-- ============================================================
-- 3) INSERT con default_value valido -> ammesso
-- ============================================================
SELECT lives_ok(
    $$INSERT INTO config.parameters(id, code, default_value, description)
      SELECT 99001, 'DEFAULT_TIPO_SOGGETTO_DETTAGLIO_TEST_OK',
             tsd.codice_interno, 'pgTAP test row OK'
        FROM tmp_ctx_tsd tsd$$,
    'INSERT con default_value esistente in tipi_soggetto_dettaglio ammesso'
);

-- ============================================================
-- 4) INSERT con default_value invalido -> raise
-- ============================================================
SELECT throws_ok(
    $$INSERT INTO config.parameters(id, code, default_value, description)
      VALUES (99002, 'DEFAULT_TIPO_SOGGETTO_DETTAGLIO_TEST_BAD',
              'CODICE_INESISTENTE_XYZ', 'pgTAP test row BAD')$$,
    'P0001',
    NULL,
    'INSERT con default_value non esistente -> E_PARAMETER_DEFAULT_TIPO_SOGGETTO_INVALID'
);

-- ============================================================
-- 5) UPDATE su record CL pre-seedato verso valore non esistente
-- ============================================================
SELECT throws_ok(
    $$UPDATE config.parameters
         SET default_value = 'CODICE_INESISTENTE_XYZ'
       WHERE code = 'DEFAULT_TIPO_SOGGETTO_DETTAGLIO_CL'$$,
    'P0001',
    NULL,
    'UPDATE default_value su DEFAULT_TIPO_SOGGETTO_DETTAGLIO_CL verso valore invalido -> raise'
);

-- ============================================================
-- 6) INSERT con code fuori prefisso -> guard non scatta
--    (prova: default_value chiaramente non esistente in tsd, il guard
--    NON dovrebbe interferire perche' la clausola WHEN del trigger
--    limita lo scope al prefisso DEFAULT_TIPO_SOGGETTO_DETTAGLIO_)
-- ============================================================
SELECT lives_ok(
    $$INSERT INTO config.parameters(id, code, default_value, description)
      VALUES (99003, 'PGTAP_NON_DEFAULT_PARAM',
              'VALORE_LIBERO_XYZ', 'pgTAP test guard scope')$$,
    'INSERT con code fuori prefisso DEFAULT_TIPO_SOGGETTO_DETTAGLIO_ ammesso'
);

-- ============================================================
-- 7) UPDATE solo description su CL pre-seedato -> guard non scatta
--    Il trigger ha `OF code, default_value`: l'UPDATE che tocca solo
--    altre colonne non lo invoca, anche se code matcha il prefisso.
-- ============================================================
SELECT lives_ok(
    $$UPDATE config.parameters
         SET description = 'pgTAP UPDATE solo description'
       WHERE code = 'DEFAULT_TIPO_SOGGETTO_DETTAGLIO_CL'$$,
    'UPDATE solo description su CL ammesso (trigger OF code/default_value)'
);

SELECT * FROM finish();
ROLLBACK;
