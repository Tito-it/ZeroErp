-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: seed config.parameters per emittente fiscale form-defaults
-- (Fase 3 P1 2026-04-29) + scenario read parametro con cascata
-- override (default -> emittente -> user).
--
-- 3 parametri seedati (id 27-29):
--   EMITTENTE_DEFAULT_BOLLO_AUTO         = 'false'
--   EMITTENTE_DEFAULT_BOLLO_SOGLIA       = '' (stringa vuota = NULL applicativo)
--   EMITTENTE_DEFAULT_ROUNDING_POLICY    = 'HALF_UP'
--
-- Nota architetturale: ATTIVO non e' tra i parametri (ridondante con
-- DEFAULT true della colonna emittenti_fiscali.attivo). I valori di
-- rounding_policy sono validati lato BE (Python _ROUNDING_MODE_VALIDI
-- subset 4: UP, DOWN, HALF_UP, HALF_DOWN) E dal CHECK constraint
-- chk_emittenti_fiscali_rounding_policy a livello tabella; il parametro
-- pero' non ha guard DB dedicato (typo nel CSV bloccato solo all'INSERT
-- emittente).
--
-- La meccanica generale di fn_get_parameter_full e' gia' coperta da
-- db/pgtap/script/test-fn-get-parameter-full-emittente.sql; qui
-- validiamo l'integrazione sui code reali del nuovo seed +
-- la convenzione "stringa vuota = NULL applicativo" su BOLLO_SOGLIA.
--
-- Indice test (1..10):
--    1. EMITTENTE_DEFAULT_BOLLO_AUTO         presente
--    2. EMITTENTE_DEFAULT_BOLLO_SOGLIA       presente
--    3. EMITTENTE_DEFAULT_ROUNDING_POLICY    presente
--    4. default_value BOLLO_AUTO        = 'false'
--    5. default_value BOLLO_SOGLIA      = '' (stringa vuota letterale)
--    6. default_value ROUNDING_POLICY   = 'HALF_UP'
--    7. fn_get_parameter_full ROUNDING_POLICY no-override -> 'HALF_UP'
--    8. fn_get_parameter_full BOLLO_SOGLIA   no-override -> '' (stringa vuota)
--    9. cascata: override emittente ROUNDING_POLICY -> 'HALF_DOWN' vince su default
--   10. cascata: override user ROUNDING_POLICY -> 'UP' vince su emittente
-- ------------------------------------------------------------

BEGIN;
SELECT plan(10);

-- =========================================================
-- 1..3) Presenza dei 3 parametri seedati
-- =========================================================
SELECT ok(
    EXISTS(SELECT 1 FROM config.parameters WHERE code = 'EMITTENTE_DEFAULT_BOLLO_AUTO'),
    '1) EMITTENTE_DEFAULT_BOLLO_AUTO presente in config.parameters'
);
SELECT ok(
    EXISTS(SELECT 1 FROM config.parameters WHERE code = 'EMITTENTE_DEFAULT_BOLLO_SOGLIA'),
    '2) EMITTENTE_DEFAULT_BOLLO_SOGLIA presente in config.parameters'
);
SELECT ok(
    EXISTS(SELECT 1 FROM config.parameters WHERE code = 'EMITTENTE_DEFAULT_ROUNDING_POLICY'),
    '3) EMITTENTE_DEFAULT_ROUNDING_POLICY presente in config.parameters'
);

-- =========================================================
-- 4..6) Default value coerente con specifica Fase 3
-- =========================================================
SELECT is(
    (SELECT default_value FROM config.parameters WHERE code = 'EMITTENTE_DEFAULT_BOLLO_AUTO'),
    'false'::text,
    '4) Default BOLLO_AUTO = false (form pre-flagga bollo auto-calcolato spento)'
);
SELECT is(
    (SELECT default_value FROM config.parameters WHERE code = 'EMITTENTE_DEFAULT_BOLLO_SOGLIA'),
    ''::text,
    '5) Default BOLLO_SOGLIA = '''' (stringa vuota; convenzione: BE casta a NULL)'
);
SELECT is(
    (SELECT default_value FROM config.parameters WHERE code = 'EMITTENTE_DEFAULT_ROUNDING_POLICY'),
    'HALF_UP'::text,
    '6) Default ROUNDING_POLICY = HALF_UP (compatibile con CHECK chk_emittenti_fiscali_rounding_policy)'
);

-- =========================================================
-- 7) fn_get_parameter_full senza override -> default puro (ROUNDING_POLICY)
-- =========================================================
SELECT is(
    script.fn_get_parameter_full('EMITTENTE_DEFAULT_ROUNDING_POLICY'),
    'HALF_UP'::text,
    '7) fn_get_parameter_full ROUNDING_POLICY no-override = HALF_UP (default)'
);

-- =========================================================
-- 8) fn_get_parameter_full senza override -> '' letterale (BOLLO_SOGLIA)
--    Valida la convenzione "stringa vuota in default_value" non viene
--    convertita silenziosamente in NULL dalla cascata.
-- =========================================================
SELECT is(
    script.fn_get_parameter_full('EMITTENTE_DEFAULT_BOLLO_SOGLIA'),
    ''::text,
    '8) fn_get_parameter_full BOLLO_SOGLIA no-override = '''' (la cascata preserva la stringa vuota)'
);

-- =========================================================
-- Setup cascata override (emittente + user reali)
-- =========================================================
CREATE TEMP TABLE _t_em_refs AS
SELECT
    ef.id AS emittente_id,
    au.id AS user_id
FROM anagrafiche.emittenti_fiscali ef
CROSS JOIN (SELECT id FROM django.auth_user ORDER BY id LIMIT 1) au
WHERE ef.attivo = true
ORDER BY ef.id
LIMIT 1;

-- =========================================================
-- 9) Override emittente ROUNDING_POLICY = 'HALF_DOWN' vince su default
-- =========================================================
INSERT INTO config.parameter_overrides (
    parameter_id,
    overridden_value,
    emittente_fiscale_id
)
SELECT
    (SELECT id FROM config.parameters WHERE code = 'EMITTENTE_DEFAULT_ROUNDING_POLICY'),
    'HALF_DOWN',
    r.emittente_id
FROM _t_em_refs r
WHERE r.emittente_id IS NOT NULL;

SELECT is(
    script.fn_get_parameter_full(
        'EMITTENTE_DEFAULT_ROUNDING_POLICY',
        p_emittente_fiscale_id := (SELECT emittente_id FROM _t_em_refs)
    ),
    'HALF_DOWN'::text,
    '9) Cascata: override emittente HALF_DOWN vince su default HALF_UP'
);

-- =========================================================
-- 10) Override user ROUNDING_POLICY = 'UP' vince su emittente
--     (priorita' user > group > emittente > default)
-- =========================================================
INSERT INTO config.parameter_overrides (
    parameter_id,
    overridden_value,
    django_user_id
)
SELECT
    (SELECT id FROM config.parameters WHERE code = 'EMITTENTE_DEFAULT_ROUNDING_POLICY'),
    'UP',
    r.user_id
FROM _t_em_refs r
WHERE r.user_id IS NOT NULL;

SELECT is(
    script.fn_get_parameter_full(
        'EMITTENTE_DEFAULT_ROUNDING_POLICY',
        p_emittente_fiscale_id := (SELECT emittente_id FROM _t_em_refs),
        p_django_user_id := (SELECT user_id FROM _t_em_refs)::integer
    ),
    'UP'::text,
    '10) Cascata: override user UP vince su override emittente HALF_DOWN'
);

SELECT * FROM finish();
ROLLBACK;
