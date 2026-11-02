-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: seed config.parameters per Catalogo UoM operativa defaults
-- (Fase 1 brief BE 28-04-2026) + scenario read parametro con cascata
-- override (default -> emittente -> user).
--
-- 5 parametri seedati (id 17-21):
--   CATALOGO_UOM_OP_DEFAULT_FACTOR_TO_BASE   = 1
--   CATALOGO_UOM_OP_DEFAULT_QTY_STEP         = 1
--   CATALOGO_UOM_OP_DEFAULT_ROUNDING_MODE    = HALF_UP
--   CATALOGO_UOM_OP_DEFAULT_MAX_DECIMALS     = 6
--   CATALOGO_UOM_OP_DEFAULT_FORBID_FRACTION  = false
--
-- I rounding_mode restano enum tecnici Python (_ROUNDING_MODE_VALIDI):
-- nessuna tabella di lookup uom_rounding_modes, nessun guard FK-surrogato
-- (decisione BE 28-04-2026). Il test si limita a presenza+default+cascata.
--
-- La meccanica generale di fn_get_parameter_full e' gia' coperta da
-- db/pgtap/script/test-fn-get-parameter-full-emittente.sql; qui validiamo
-- l'integrazione sui code reali del nuovo seed.
--
-- Indice test (1..13):
--    1. CATALOGO_UOM_OP_DEFAULT_FACTOR_TO_BASE   presente
--    2. CATALOGO_UOM_OP_DEFAULT_QTY_STEP         presente
--    3. CATALOGO_UOM_OP_DEFAULT_ROUNDING_MODE    presente
--    4. CATALOGO_UOM_OP_DEFAULT_MAX_DECIMALS     presente
--    5. CATALOGO_UOM_OP_DEFAULT_FORBID_FRACTION  presente
--    6. default_value FACTOR_TO_BASE   = '1'
--    7. default_value QTY_STEP         = '1'
--    8. default_value ROUNDING_MODE    = 'HALF_UP'
--    9. default_value MAX_DECIMALS     = '6'
--   10. default_value FORBID_FRACTION  = 'false'
--   11. fn_get_parameter_full ROUNDING_MODE no-override -> 'HALF_UP'
--   12. cascata: override emittente ROUNDING_MODE -> 'HALF_DOWN' vince su default
--   13. cascata: override user ROUNDING_MODE -> 'HALF_EVEN' vince su emittente
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

SELECT plan(13);

-- =========================================================
-- 1..5) Presenza dei 5 parametri seedati
-- =========================================================
SELECT ok(
    EXISTS(SELECT 1 FROM config.parameters WHERE code = 'CATALOGO_UOM_OP_DEFAULT_FACTOR_TO_BASE'),
    '1) CATALOGO_UOM_OP_DEFAULT_FACTOR_TO_BASE presente in config.parameters'
);
SELECT ok(
    EXISTS(SELECT 1 FROM config.parameters WHERE code = 'CATALOGO_UOM_OP_DEFAULT_QTY_STEP'),
    '2) CATALOGO_UOM_OP_DEFAULT_QTY_STEP presente in config.parameters'
);
SELECT ok(
    EXISTS(SELECT 1 FROM config.parameters WHERE code = 'CATALOGO_UOM_OP_DEFAULT_ROUNDING_MODE'),
    '3) CATALOGO_UOM_OP_DEFAULT_ROUNDING_MODE presente in config.parameters'
);
SELECT ok(
    EXISTS(SELECT 1 FROM config.parameters WHERE code = 'CATALOGO_UOM_OP_DEFAULT_MAX_DECIMALS'),
    '4) CATALOGO_UOM_OP_DEFAULT_MAX_DECIMALS presente in config.parameters'
);
SELECT ok(
    EXISTS(SELECT 1 FROM config.parameters WHERE code = 'CATALOGO_UOM_OP_DEFAULT_FORBID_FRACTION'),
    '5) CATALOGO_UOM_OP_DEFAULT_FORBID_FRACTION presente in config.parameters'
);

-- =========================================================
-- 6..10) Default value coerente con specifica Fase 1
-- =========================================================
SELECT is(
    (SELECT default_value FROM config.parameters WHERE code = 'CATALOGO_UOM_OP_DEFAULT_FACTOR_TO_BASE'),
    '1'::text,
    '6) Default FACTOR_TO_BASE = 1 (UoM operativa = base 1:1)'
);
SELECT is(
    (SELECT default_value FROM config.parameters WHERE code = 'CATALOGO_UOM_OP_DEFAULT_QTY_STEP'),
    '1'::text,
    '7) Default QTY_STEP = 1 (granularita unitaria)'
);
SELECT is(
    (SELECT default_value FROM config.parameters WHERE code = 'CATALOGO_UOM_OP_DEFAULT_ROUNDING_MODE'),
    'HALF_UP'::text,
    '8) Default ROUNDING_MODE = HALF_UP'
);
SELECT is(
    (SELECT default_value FROM config.parameters WHERE code = 'CATALOGO_UOM_OP_DEFAULT_MAX_DECIMALS'),
    '6'::text,
    '9) Default MAX_DECIMALS = 6'
);
SELECT is(
    (SELECT default_value FROM config.parameters WHERE code = 'CATALOGO_UOM_OP_DEFAULT_FORBID_FRACTION'),
    'false'::text,
    '10) Default FORBID_FRACTION = false (UoM frazionabile)'
);

-- =========================================================
-- 11) fn_get_parameter_full senza override -> default puro
-- =========================================================
SELECT is(
    script.fn_get_parameter_full('CATALOGO_UOM_OP_DEFAULT_ROUNDING_MODE'),
    'HALF_UP'::text,
    '11) fn_get_parameter_full ROUNDING_MODE no-override = HALF_UP (default)'
);

-- =========================================================
-- Setup cascata override (emittente + user reali)
-- Coerente con pattern test-fn-get-parameter-full-emittente.sql:
-- emittente fiscale attivo + auth_user qualunque.
-- =========================================================
CREATE TEMP TABLE _t_uom_refs AS
SELECT
    ef.id AS emittente_id,
    au.id AS user_id
FROM anagrafiche.emittenti_fiscali ef
CROSS JOIN (SELECT id FROM django.auth_user ORDER BY id LIMIT 1) au
WHERE ef.attivo = true
ORDER BY ef.id
LIMIT 1;

-- =========================================================
-- 12) Override emittente ROUNDING_MODE = 'HALF_DOWN' vince su default
-- =========================================================
INSERT INTO config.parameter_overrides (
    parameter_id,
    overridden_value,
    emittente_fiscale_id
)
SELECT
    (SELECT id FROM config.parameters WHERE code = 'CATALOGO_UOM_OP_DEFAULT_ROUNDING_MODE'),
    'HALF_DOWN',
    r.emittente_id
FROM _t_uom_refs r
WHERE r.emittente_id IS NOT NULL
-- Col vincolo v5 NULLS NOT DISTINCT (20261007-70) l'ambito e' uno: se sul DB
-- esiste gia' un override puro per questo parametro e questo ambito, lo si
-- riscrive invece di aggiungerne un secondo (prima nasceva un doppione e la
-- cascata ne sceglieva uno a caso). ROLLBACK in coda ripristina il valore.
ON CONFLICT ON CONSTRAINT uq_overrides_full_scope_v5
DO UPDATE SET overridden_value = EXCLUDED.overridden_value, attivo = true;

SELECT is(
    script.fn_get_parameter_full(
        'CATALOGO_UOM_OP_DEFAULT_ROUNDING_MODE',
        p_emittente_fiscale_id := (SELECT emittente_id FROM _t_uom_refs)
    ),
    'HALF_DOWN'::text,
    '12) Cascata: override emittente HALF_DOWN vince su default HALF_UP'
);

-- =========================================================
-- 13) Override user ROUNDING_MODE = 'HALF_EVEN' vince su emittente
-- (priorita' user > group > emittente > default)
-- =========================================================
INSERT INTO config.parameter_overrides (
    parameter_id,
    overridden_value,
    django_user_id
)
SELECT
    (SELECT id FROM config.parameters WHERE code = 'CATALOGO_UOM_OP_DEFAULT_ROUNDING_MODE'),
    'HALF_EVEN',
    r.user_id
FROM _t_uom_refs r
WHERE r.user_id IS NOT NULL
-- Col vincolo v5 NULLS NOT DISTINCT (20261007-70) l'ambito e' uno: se sul DB
-- esiste gia' un override puro per questo parametro e questo ambito, lo si
-- riscrive invece di aggiungerne un secondo (prima nasceva un doppione e la
-- cascata ne sceglieva uno a caso). ROLLBACK in coda ripristina il valore.
ON CONFLICT ON CONSTRAINT uq_overrides_full_scope_v5
DO UPDATE SET overridden_value = EXCLUDED.overridden_value, attivo = true;

SELECT is(
    script.fn_get_parameter_full(
        'CATALOGO_UOM_OP_DEFAULT_ROUNDING_MODE',
        p_emittente_fiscale_id := (SELECT emittente_id FROM _t_uom_refs),
        p_django_user_id := (SELECT user_id FROM _t_uom_refs)::integer
    ),
    'HALF_EVEN'::text,
    '13) Cascata: override user HALF_EVEN vince su emittente HALF_DOWN'
);

SELECT * FROM finish();
ROLLBACK;
