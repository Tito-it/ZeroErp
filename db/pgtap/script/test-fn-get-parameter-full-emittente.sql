-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: script.fn_get_parameter_full (firma con emittente_fiscale_id)
--
-- Elenco test:
--  1) Funzione presente (nuova firma bigint)
--  2) Vecchia firma (integer) non esiste piu'
--  3) Riferimenti minimi: tabelle parameters e parameter_overrides
--  4) Setup parametro test e emittente fiscale di riferimento
--  5) Risoluzione default senza override
--  6) Override emittente restituito
--  7) Priorita': user > emittente
--  8) Priorita': group > emittente
-- ------------------------------------------------------------

BEGIN;

SELECT plan(8);

-- ============================================================
-- 1) Funzione presente (nuova firma con bigint)
-- ============================================================
SELECT has_function(
    'script', 'fn_get_parameter_full',
    ARRAY['text', 'bigint', 'integer', 'integer[]', 'text', 'text'],
    '1) fn_get_parameter_full presente con firma (text, bigint, integer, integer[], text, text)'
);

-- ============================================================
-- 2) Vecchia firma (integer come secondo parametro) non esiste piu'
-- ============================================================
SELECT hasnt_function(
    'script', 'fn_get_parameter_full',
    ARRAY['text', 'integer', 'integer', 'integer[]', 'text', 'text'],
    '2) vecchia firma (text, integer, ...) rimossa'
);

-- ============================================================
-- 3) Riferimenti minimi
-- ============================================================
SELECT ok(
    EXISTS(SELECT 1 FROM config.parameters LIMIT 1)
    AND EXISTS(
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'config' AND table_name = 'parameter_overrides'
    ),
    '3) tabelle parameters e parameter_overrides esistono'
);

-- ============================================================
-- 0. Setup dati test
-- ============================================================

-- Parametro di test
INSERT INTO config.parameters (id, code, default_value, description)
VALUES (99990, '_TEST_PARAM_EMIT_', 'DEFAULT_VAL', 'Parametro test emittente')
ON CONFLICT (id) DO NOTHING;

-- Garantisce che esista almeno un gruppo di test (ROLLBACK ripristina)
INSERT INTO django.auth_group (name)
SELECT '_test_group_param_'
WHERE NOT EXISTS (SELECT 1 FROM django.auth_group LIMIT 1);

-- Riferimenti reali: emittente, auth_user, auth_group
CREATE TEMP TABLE tmp_refs_param AS
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

-- ============================================================
-- 4) Setup OK
-- ============================================================
SELECT ok(
    (SELECT emittente_id FROM tmp_refs_param) IS NOT NULL
    AND (SELECT user_id FROM tmp_refs_param) IS NOT NULL
    AND (SELECT group_id FROM tmp_refs_param) IS NOT NULL,
    '4) setup: emittente, user e group di riferimento trovati'
);

-- ============================================================
-- 5) Risoluzione default senza override
-- ============================================================
SELECT is(
    script.fn_get_parameter_full('_TEST_PARAM_EMIT_'),
    'DEFAULT_VAL',
    '5) senza override restituisce default_value'
);

-- ============================================================
-- 6) Override emittente restituito
-- ============================================================
INSERT INTO config.parameter_overrides (id, parameter_id, overridden_value, emittente_fiscale_id)
VALUES (99990, 99990, 'EMIT_VAL', (SELECT emittente_id FROM tmp_refs_param));

SELECT is(
    script.fn_get_parameter_full(
        '_TEST_PARAM_EMIT_',
        p_emittente_fiscale_id := (SELECT emittente_id FROM tmp_refs_param)
    ),
    'EMIT_VAL',
    '6) override emittente restituito correttamente'
);

-- ============================================================
-- 7) Priorita': user > emittente
-- ============================================================
INSERT INTO config.parameter_overrides (id, parameter_id, overridden_value, django_user_id)
VALUES (99991, 99990, 'USER_VAL', (SELECT user_id FROM tmp_refs_param));

SELECT is(
    script.fn_get_parameter_full(
        '_TEST_PARAM_EMIT_',
        p_emittente_fiscale_id := (SELECT emittente_id FROM tmp_refs_param),
        p_django_user_id := (SELECT user_id FROM tmp_refs_param)
    ),
    'USER_VAL',
    '7) priorita: user override vince su emittente'
);

-- ============================================================
-- 8) Priorita': group > emittente
-- ============================================================
INSERT INTO config.parameter_overrides (id, parameter_id, overridden_value, django_group_id)
VALUES (99992, 99990, 'GROUP_VAL', (SELECT group_id FROM tmp_refs_param));

SELECT is(
    script.fn_get_parameter_full(
        '_TEST_PARAM_EMIT_',
        p_emittente_fiscale_id := (SELECT emittente_id FROM tmp_refs_param),
        p_group_ids := ARRAY[(SELECT group_id FROM tmp_refs_param)]
    ),
    'GROUP_VAL',
    '8) priorita: group override vince su emittente'
);

-- ============================================================
SELECT * FROM finish();
ROLLBACK;
