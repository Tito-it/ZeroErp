-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: seed config.parameters per Catalogo UoM operativa defaults
-- (Fase 1 brief BE 28-04-2026) + scenario read parametro con cascata
-- override (default -> emittente -> user).
--
-- 4 parametri seedati (id 17, 18, 20, 21; il 19, il default di rounding_mode,
-- e' ritirato con la colonna il 2026-11-09, brief-db-revisione-catalogo giro 2):
--   CATALOGO_UOM_OP_DEFAULT_FACTOR_TO_BASE   = 1
--   CATALOGO_UOM_OP_DEFAULT_QTY_STEP         = 1
--   CATALOGO_UOM_OP_DEFAULT_MAX_DECIMALS     = 6
--   CATALOGO_UOM_OP_DEFAULT_FORBID_FRACTION  = false
--
-- Il test si limita a presenza, default e cascata degli override.
--
-- La meccanica generale di fn_get_parameter_full e' gia' coperta da
-- db/pgtap/script/test-fn-get-parameter-full-emittente.sql; qui validiamo
-- l'integrazione sui code reali del nuovo seed.
--
-- Indice test (1..13):
--    1. CATALOGO_UOM_OP_DEFAULT_FACTOR_TO_BASE   presente
--    2. CATALOGO_UOM_OP_DEFAULT_QTY_STEP         presente
--    3. CATALOGO_UOM_OP_DEFAULT_ROUNDING_MODE    ritirato
--    4. CATALOGO_UOM_OP_DEFAULT_MAX_DECIMALS     presente
--    5. CATALOGO_UOM_OP_DEFAULT_FORBID_FRACTION  presente
--    6. default_value FACTOR_TO_BASE   = '1'
--    7. default_value QTY_STEP         = '1'
--    8. la colonna rounding_mode non c'e' piu'
--    9. default_value MAX_DECIMALS     = '6'
--   10. default_value FORBID_FRACTION  = 'false'
--   11. fn_get_parameter_full MAX_DECIMALS no-override -> '6'
--   12. cascata: override emittente MAX_DECIMALS -> '2' vince su default
--   13. cascata: override user MAX_DECIMALS -> '0' vince su emittente
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
    NOT EXISTS(SELECT 1 FROM config.parameters WHERE code = 'CATALOGO_UOM_OP_DEFAULT_ROUNDING_MODE'),
    '3) CATALOGO_UOM_OP_DEFAULT_ROUNDING_MODE ritirato con la colonna rounding_mode'
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
SELECT ok(
    NOT EXISTS(SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'catalogo' AND table_name = 'articoli_uom_operativa'
                  AND column_name = 'rounding_mode'),
    '8) la colonna di cui ROUNDING_MODE era il default non c''e'' piu'''
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
    script.fn_get_parameter_full('CATALOGO_UOM_OP_DEFAULT_MAX_DECIMALS'),
    '6'::text,
    '11) fn_get_parameter_full MAX_DECIMALS no-override = 6 (default)'
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
-- 12) Override emittente MAX_DECIMALS = '2' vince su default
-- =========================================================
INSERT INTO config.parameter_overrides (
    parameter_id,
    overridden_value,
    emittente_fiscale_id
)
SELECT
    (SELECT id FROM config.parameters WHERE code = 'CATALOGO_UOM_OP_DEFAULT_MAX_DECIMALS'),
    '2',
    r.emittente_id
FROM _t_uom_refs r
WHERE r.emittente_id IS NOT NULL
-- Col vincolo v5 NULLS NOT DISTINCT (20261007-70) l'ambito e' uno: se sul DB
-- esiste gia' un override puro per questo parametro e questo ambito, lo si
-- riscrive invece di aggiungerne un secondo (prima nasceva un doppione e la
-- cascata ne sceglieva uno a caso). ROLLBACK in coda ripristina il valore.
ON CONFLICT ON CONSTRAINT uq_overrides_full_scope_v6
DO UPDATE SET overridden_value = EXCLUDED.overridden_value, attivo = true;

SELECT is(
    script.fn_get_parameter_full(
        'CATALOGO_UOM_OP_DEFAULT_MAX_DECIMALS',
        p_emittente_fiscale_id := (SELECT emittente_id FROM _t_uom_refs)
    ),
    '2'::text,
    '12) Cascata: override emittente 2 vince su default 6'
);

-- =========================================================
-- 13) Override user MAX_DECIMALS = '0' vince su emittente
-- (priorita' user > group > emittente > default)
-- =========================================================
INSERT INTO config.parameter_overrides (
    parameter_id,
    overridden_value,
    django_user_id
)
SELECT
    (SELECT id FROM config.parameters WHERE code = 'CATALOGO_UOM_OP_DEFAULT_MAX_DECIMALS'),
    '0',
    r.user_id
FROM _t_uom_refs r
WHERE r.user_id IS NOT NULL
-- Col vincolo v5 NULLS NOT DISTINCT (20261007-70) l'ambito e' uno: se sul DB
-- esiste gia' un override puro per questo parametro e questo ambito, lo si
-- riscrive invece di aggiungerne un secondo (prima nasceva un doppione e la
-- cascata ne sceglieva uno a caso). ROLLBACK in coda ripristina il valore.
ON CONFLICT ON CONSTRAINT uq_overrides_full_scope_v6
DO UPDATE SET overridden_value = EXCLUDED.overridden_value, attivo = true;

SELECT is(
    script.fn_get_parameter_full(
        'CATALOGO_UOM_OP_DEFAULT_MAX_DECIMALS',
        p_emittente_fiscale_id := (SELECT emittente_id FROM _t_uom_refs),
        p_django_user_id := (SELECT user_id FROM _t_uom_refs)::integer
    ),
    '0'::text,
    '13) Cascata: override user 0 vince su emittente 2'
);

SELECT * FROM finish();
ROLLBACK;
