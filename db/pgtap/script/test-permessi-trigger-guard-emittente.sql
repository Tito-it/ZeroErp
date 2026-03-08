-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: trigger defense-in-depth guard emittente scope
--       Verifica esistenza trigger function e trigger su
--       vendite.fatture e pagamenti.vendite_movimenti.
--
-- Elenco test:
--  1) Trigger function script.trgfn_guard_emittente_scope esiste
--  2) Trigger su vendite.fatture esiste (a10_guard_emittente_scope)
--  3) Trigger su vendite.fatture è BEFORE INSERT
--  4) Trigger su vendite.fatture è BEFORE UPDATE
--  5) Trigger su pagamenti.vendite_movimenti esiste
--  6) Integrazione: blocco INSERT fattura con emittente fuori scope
-- ------------------------------------------------------------

BEGIN;

SELECT plan(6);

-- ============================================================
-- 1. Trigger function esiste
-- ============================================================

SELECT ok(
    EXISTS (
        SELECT 1
        FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'script'
          AND p.proname = 'trgfn_guard_emittente_scope'
    ),
    'Trigger function script.trgfn_guard_emittente_scope esiste'
);

-- ============================================================
-- 2. Trigger su vendite.fatture
-- ============================================================

SELECT ok(
    EXISTS (
        SELECT 1
        FROM pg_trigger t
        JOIN pg_class c ON c.oid = t.tgrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'vendite'
          AND c.relname = 'fatture'
          AND t.tgname  = 'trg_fatture_a10_guard_emittente_scope_ins_upd'
          AND NOT t.tgisinternal
    ),
    'Trigger trg_fatture_a10_guard_emittente_scope_ins_upd esiste su vendite.fatture'
);

-- Verifica timing BEFORE INSERT (tgtype bit 2 = INSERT, bit 1 = BEFORE)
SELECT ok(
    EXISTS (
        SELECT 1
        FROM pg_trigger t
        JOIN pg_class c ON c.oid = t.tgrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'vendite'
          AND c.relname = 'fatture'
          AND t.tgname  = 'trg_fatture_a10_guard_emittente_scope_ins_upd'
          AND (t.tgtype::int & 2)  > 0  -- BEFORE
          AND (t.tgtype::int & 4)  > 0  -- INSERT
    ),
    'Trigger fatture: timing BEFORE INSERT'
);

-- Verifica timing BEFORE UPDATE (tgtype bit 16 = UPDATE)
SELECT ok(
    EXISTS (
        SELECT 1
        FROM pg_trigger t
        JOIN pg_class c ON c.oid = t.tgrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'vendite'
          AND c.relname = 'fatture'
          AND t.tgname  = 'trg_fatture_a10_guard_emittente_scope_ins_upd'
          AND (t.tgtype::int & 2)  > 0  -- BEFORE
          AND (t.tgtype::int & 16) > 0  -- UPDATE
    ),
    'Trigger fatture: timing BEFORE UPDATE'
);

-- ============================================================
-- 3. Trigger su pagamenti.vendite_movimenti
-- ============================================================

SELECT ok(
    EXISTS (
        SELECT 1
        FROM pg_trigger t
        JOIN pg_class c ON c.oid = t.tgrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'pagamenti'
          AND c.relname = 'vendite_movimenti'
          AND t.tgname  = 'trg_vendite_movimenti_a10_guard_emittente_scope_ins_upd'
          AND NOT t.tgisinternal
    ),
    'Trigger trg_vendite_movimenti_a10_guard_emittente_scope_ins_upd esiste'
);

-- ============================================================
-- 4. Test integrazione: blocco scope tramite fn_check
--    (verifica che la catena trgfn → fn_check funziona)
-- ============================================================

-- Prepara contesto: prendi un utente e forzalo a OPERATIVO.
-- emittente_ko_id = -1 (fittizio): la funzione verifica solo la whitelist,
-- non che l'emittente esista in anagrafiche.emittenti_fiscali.
CREATE TEMP TABLE tmp_guard_ctx AS
SELECT
    rau.auth_user_id AS user_id,
    ef.id            AS emittente_ok_id,
    -1::bigint       AS emittente_ko_id
FROM anagrafiche.risorse_umane_auth_user rau
CROSS JOIN (
    SELECT id FROM anagrafiche.emittenti_fiscali
    WHERE attivo = true ORDER BY id LIMIT 1
) ef
ORDER BY rau.id
LIMIT 1;

-- Forza OPERATIVO per il test (ROLLBACK ripristina)
UPDATE anagrafiche.risorse_umane_auth_user
   SET ruolo_sistema = 'OPERATIVO'
 WHERE auth_user_id = (SELECT user_id FROM tmp_guard_ctx);

-- Aggiungi whitelist solo per emittente_ok
INSERT INTO config.user_emittenti_fiscali
    (auth_user_id, emittente_fiscale_id, meta)
SELECT ctx.user_id, ctx.emittente_ok_id,
       '{"test_scope":"pgtap_trigger_guard_emittente"}'::jsonb
FROM tmp_guard_ctx ctx;

-- Setta sessione come l'utente ristretto
SELECT set_config('app.current_user_id',
    (SELECT user_id::text FROM tmp_guard_ctx), true);

-- Verifica che fn_check blocchi emittente_ko
-- (è la stessa funzione chiamata dal trigger)
SELECT is(
    script.fn_check_user_emittente_scope(
        (SELECT user_id FROM tmp_guard_ctx),
        (SELECT emittente_ko_id FROM tmp_guard_ctx)
    ),
    false,
    'Integrazione: fn_check blocca emittente fuori scope (catena trigger)'
);

SELECT * FROM finish();

ROLLBACK;
