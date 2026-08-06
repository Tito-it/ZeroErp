-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: script.fn_list_parameters_for_user
--
-- Elenco test:
--   1) Funzione presente con firma 4-arg (integer, integer[], bigint, smallint)
--   2) Riferimenti minimi (tabelle config.parameters, config.parameter_overrides)
--   3) Setup dati OK (emittente, user, group trovati)
--   4) Lista restituisce almeno il parametro di test _TEST_LIST_A_
--   5) resolved_value = user_value quando tutti i livelli presenti (user vince)
--   6) resolved_value = group_value quando user assente
--   7) resolved_value = emittente_value quando user e group assenti
--   8) resolved_value = default_value quando nessun override
--   9) Setup categoria_cliente di test inserita
--  10) p_categoria_cliente_id = NULL -> colonne categoria NULL (retro-compatibile)
--  11) Solo override categoria (no user, no group) -> resolved_value = categoria_cliente_value
--  12) Override user + categoria -> resolved_value = user_value (user vince)
--  13) Override categoria + group (no user) -> resolved_value = categoria_cliente_value (categoria vince su group)
--  14) Override categoria + emittente (no user, no group) -> resolved_value = categoria_cliente_value (categoria vince su emittente)
-- ------------------------------------------------------------

BEGIN;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(14);

-- ============================================================
-- 1) Funzione presente con firma 4-arg
-- ============================================================
SELECT has_function(
    'script', 'fn_list_parameters_for_user',
    ARRAY['integer', 'integer[]', 'bigint', 'smallint'],
    '1) fn_list_parameters_for_user presente con firma 4-arg (integer, integer[], bigint, smallint)'
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
-- Setup dati test — parte 1: parametri e override base
-- ============================================================

-- Garantisce almeno un gruppo di test (ROLLBACK ripristina)
INSERT INTO django.auth_group (name)
SELECT '_test_group_list_'
WHERE NOT EXISTS (SELECT 1 FROM django.auth_group LIMIT 1);

-- Riferimenti reali: emittente attivo, primo user, primo group
CREATE TEMP TABLE tmp_refs_list AS
SELECT
    ef.id  AS emittente_id,
    au.id  AS user_id,
    ag.id  AS group_id
FROM anagrafiche.emittenti_fiscali ef
CROSS JOIN (SELECT id FROM django.auth_user  ORDER BY id LIMIT 1) au
CROSS JOIN (SELECT id FROM django.auth_group ORDER BY id LIMIT 1) ag
WHERE ef.attivo = true
ORDER BY ef.id
LIMIT 1;

-- Parametri di test (2: uno con override a tutti i livelli, uno senza)
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
    AND (SELECT user_id   FROM tmp_refs_list) IS NOT NULL
    AND (SELECT group_id  FROM tmp_refs_list) IS NOT NULL,
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
-- Setup dati test — parte 2: categoria_cliente e override categoria
-- ============================================================

-- Categoria di test (id 9999, smallint; attivo=true per trigger req-active-parent)
INSERT INTO anagrafiche.categorie_clienti (id, codice, codice_interno, descrizione)
VALUES (9999, '_TEST_CAT_LIST_', '_TEST_CAT_LIST_', 'Categoria test fn_list_parameters_for_user')
ON CONFLICT (id) DO NOTHING;

-- Override categoria su parametro A (scope puro: no user/group/emittente/session/function)
INSERT INTO config.parameter_overrides (id, parameter_id, overridden_value, categoria_cliente_id)
VALUES (99983, 99980, 'CAT_A', 9999);

-- ============================================================
-- 9) Setup categoria_cliente di test OK
-- ============================================================
SELECT ok(
    EXISTS(SELECT 1 FROM anagrafiche.categorie_clienti WHERE id = 9999)
    AND EXISTS(SELECT 1 FROM config.parameter_overrides WHERE id = 99983),
    '9) setup: categoria_cliente 9999 e override categoria inseriti'
);

-- ============================================================
-- 10) p_categoria_cliente_id = NULL -> colonne categoria NULL (retro-compatibile)
-- ============================================================
SELECT ok(
    (SELECT r.categoria_cliente_value IS NULL
         AND r.categoria_cliente_override_id IS NULL
       FROM script.fn_list_parameters_for_user(
           (SELECT user_id FROM tmp_refs_list),
           ARRAY[(SELECT group_id FROM tmp_refs_list)],
           (SELECT emittente_id FROM tmp_refs_list),
           NULL
       ) r
      WHERE r.code = '_TEST_LIST_A_'),
    '10) p_categoria_cliente_id = NULL -> categoria_cliente_value e _override_id NULL (retro-compatibile)'
);

-- ============================================================
-- 11) Solo override categoria (no user, no group) -> resolved = CAT_A
-- ============================================================
SELECT is(
    (SELECT r.resolved_value
       FROM script.fn_list_parameters_for_user(
           -999, NULL, NULL, 9999::smallint
       ) r
      WHERE r.code = '_TEST_LIST_A_'),
    'CAT_A',
    '11) solo override categoria -> resolved_value = categoria_cliente_value'
);

-- ============================================================
-- 12) Override user + categoria -> resolved = USER_A (user vince)
-- ============================================================
SELECT is(
    (SELECT r.resolved_value
       FROM script.fn_list_parameters_for_user(
           (SELECT user_id FROM tmp_refs_list),
           NULL,
           NULL,
           9999::smallint
       ) r
      WHERE r.code = '_TEST_LIST_A_'),
    'USER_A',
    '12) override user + categoria -> resolved_value = user_value (user vince su categoria)'
);

-- ============================================================
-- 13) Override categoria + group (no user) -> resolved = CAT_A (categoria vince su group)
-- ============================================================
SELECT is(
    (SELECT r.resolved_value
       FROM script.fn_list_parameters_for_user(
           -999,
           ARRAY[(SELECT group_id FROM tmp_refs_list)],
           NULL,
           9999::smallint
       ) r
      WHERE r.code = '_TEST_LIST_A_'),
    'CAT_A',
    '13) override categoria + group -> resolved_value = categoria_cliente_value (categoria vince su group, §3-bis-C)'
);

-- ============================================================
-- 14) Override categoria + emittente (no user, no group) -> resolved = CAT_A (categoria vince)
-- ============================================================
SELECT is(
    (SELECT r.resolved_value
       FROM script.fn_list_parameters_for_user(
           -999,
           NULL,
           (SELECT emittente_id FROM tmp_refs_list),
           9999::smallint
       ) r
      WHERE r.code = '_TEST_LIST_A_'),
    'CAT_A',
    '14) override categoria + emittente -> resolved_value = categoria_cliente_value (categoria vince su emittente)'
);

-- ============================================================
SELECT * FROM finish();
ROLLBACK;
