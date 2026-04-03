-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: script.fn_list_parameters_for_user
--
-- Elenco test:
--  1) Funzione presente
--  2) Riferimenti minimi (tabelle)
--  3) Setup: parametro test + emittente + override a 3 livelli
--  4) Lista restituisce almeno il parametro di test
--  5) resolved_value = user_value quando presente (user > group > emittente)
--  6) resolved_value = group_value quando user assente
--  7) resolved_value = emittente_value quando user e group assenti
--  8) resolved_value = default_value quando nessun override
-- ------------------------------------------------------------

BEGIN;

SELECT plan(8);

-- ============================================================
-- 1) Funzione presente
-- ============================================================
SELECT has_function(
    'script', 'fn_list_parameters_for_user',
    ARRAY['integer', 'integer[]', 'bigint'],
    '1) fn_list_parameters_for_user presente con firma (integer, integer[], bigint)'
);

-- ============================================================
-- 2) Riferimenti minimi
-- ============================================================
SELECT ok(
    EXISTS(SELECT 1 FROM information_schema.tables
           WHERE table_schema = 'config' AND table_name = 'parameters')
    AND EXISTS(SELECT 1 FROM information_schema.tables
               WHERE table_schema = 'config' AND table_name = 'parameter_overrides'),
    '2) tabelle parameters e parameter_overrides esistono'
);

-- ============================================================
-- 0. Setup dati test
-- ============================================================

-- Garantisce che esista almeno un gruppo di test (ROLLBACK ripristina)
INSERT INTO django.auth_group (name)
SELECT '_test_group_list_'
WHERE NOT EXISTS (SELECT 1 FROM django.auth_group LIMIT 1);

-- Riferimenti reali: emittente, auth_user, auth_group
CREATE TEMP TABLE tmp_refs_list AS
SELECT
    ef.id  AS emittente_id,
    au.id  AS user_id,
    ag.id  AS group_id
FROM anagrafiche.emittenti_fiscali ef
CROSS JOIN (SELECT id FROM django.auth_user ORDER BY id LIMIT 1) au
CROSS JOIN (SELECT id FROM django.auth_group ORDER BY id LIMIT 1) ag
WHERE ef.attivo = true
ORDER BY ef.id
LIMIT 1;

-- Parametri di test (2: uno con override, uno senza)
INSERT INTO config.parameters (id, code, default_value, description)
VALUES
    (99980, '_TEST_LIST_A_', 'DEF_A', 'Test list parametro A'),
    (99981, '_TEST_LIST_B_', 'DEF_B', 'Test list parametro B')
ON CONFLICT (id) DO NOTHING;

-- Override emittente su parametro A
INSERT INTO config.parameter_overrides (id, parameter_id, overridden_value, emittente_fiscale_id)
VALUES (99980, 99980, 'EMIT_A', (SELECT emittente_id FROM tmp_refs_list));

-- Override gruppo su parametro A
INSERT INTO config.parameter_overrides (id, parameter_id, overridden_value, django_group_id)
VALUES (99981, 99980, 'GROUP_A', (SELECT group_id FROM tmp_refs_list));

-- Override utente su parametro A
INSERT INTO config.parameter_overrides (id, parameter_id, overridden_value, django_user_id)
VALUES (99982, 99980, 'USER_A', (SELECT user_id FROM tmp_refs_list));

-- ============================================================
-- 3) Setup OK
-- ============================================================
SELECT ok(
    (SELECT emittente_id FROM tmp_refs_list) IS NOT NULL
    AND (SELECT user_id FROM tmp_refs_list) IS NOT NULL
    AND (SELECT group_id FROM tmp_refs_list) IS NOT NULL,
    '3) setup: emittente, user e group di riferimento trovati'
);

-- ============================================================
-- 4) Lista restituisce almeno il parametro di test
-- ============================================================
SELECT ok(
    EXISTS(
        SELECT 1
        FROM script.fn_list_parameters_for_user(
            (SELECT user_id FROM tmp_refs_list),
            ARRAY[(SELECT group_id FROM tmp_refs_list)],
            (SELECT emittente_id FROM tmp_refs_list)
        ) r
        WHERE r.code = '_TEST_LIST_A_'
    ),
    '4) lista restituisce parametro _TEST_LIST_A_'
);

-- ============================================================
-- 5) resolved_value = user_value (user > group > emittente)
-- ============================================================
SELECT is(
    (SELECT r.resolved_value
     FROM script.fn_list_parameters_for_user(
         (SELECT user_id FROM tmp_refs_list),
         ARRAY[(SELECT group_id FROM tmp_refs_list)],
         (SELECT emittente_id FROM tmp_refs_list)
     ) r
     WHERE r.code = '_TEST_LIST_A_'),
    'USER_A',
    '5) resolved_value = user_value quando tutti i livelli presenti'
);

-- ============================================================
-- 6) resolved_value = group_value quando user assente
-- ============================================================
-- Usa user_id inesistente: l'override utente non matcha, vince il gruppo
SELECT is(
    (SELECT r.resolved_value
     FROM script.fn_list_parameters_for_user(
         -999,
         ARRAY[(SELECT group_id FROM tmp_refs_list)],
         (SELECT emittente_id FROM tmp_refs_list)
     ) r
     WHERE r.code = '_TEST_LIST_A_'),
    'GROUP_A',
    '6) resolved_value = group_value quando user assente'
);

-- ============================================================
-- 7) resolved_value = emittente_value quando user e group assenti
-- ============================================================
SELECT is(
    (SELECT r.resolved_value
     FROM script.fn_list_parameters_for_user(
         -999, NULL, (SELECT emittente_id FROM tmp_refs_list)
     ) r
     WHERE r.code = '_TEST_LIST_A_'),
    'EMIT_A',
    '7) resolved_value = emittente_value quando user e group assenti'
);

-- ============================================================
-- 8) resolved_value = default_value quando nessun override
-- ============================================================
SELECT is(
    (SELECT r.resolved_value
     FROM script.fn_list_parameters_for_user(
         -999, NULL, (SELECT emittente_id FROM tmp_refs_list)
     ) r
     WHERE r.code = '_TEST_LIST_B_'),
    'DEF_B',
    '8) resolved_value = default_value quando nessun override'
);

-- ============================================================
SELECT * FROM finish();
ROLLBACK;
