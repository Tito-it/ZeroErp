-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
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

-- Prepara contesto: pesco un'identita OPERATORE attiva NON super-admin
-- (filtro NOT EXISTS binding SUPER_ADMIN, pattern §4.bis pgTAP).
-- Pre-Fase 7: il setup leggeva da rau e forzava ruolo_sistema='OPERATIVO'
-- via UPDATE (rotto post-cutover §13.3, vista non updatable).
-- Post-Fase 7: il filtro garantisce gia' lo stato "OPERATIVO" semantico
-- (identita OPERATORE attiva senza binding SA), nessun UPDATE forzato.
-- emittente_ko_id = -1 (fittizio): la funzione verifica solo la whitelist,
-- non che l'emittente esista in anagrafiche.emittenti_fiscali.
CREATE TEMP TABLE tmp_guard_ctx AS
SELECT
    id.auth_user_id  AS user_id,
    ef.id            AS emittente_ok_id,
    -1::bigint       AS emittente_ko_id
FROM anagrafiche.identita_digitali id
CROSS JOIN (
    SELECT id FROM anagrafiche.emittenti_fiscali
    WHERE attivo = true ORDER BY id LIMIT 1
) ef
WHERE id.ruolo_applicativo = 'OPERATORE'::config.ruolo_applicativo
  AND id.attivo = true
  AND NOT EXISTS (
      SELECT 1
        FROM config.profili_accesso_bindings pab
        JOIN config.profili_accesso pa ON pa.id = pab.profilo_accesso_id
       WHERE pab.identita_digitale_id = id.id
         AND pab.attivo = true
         AND pa.tipo = 'SUPER_ADMIN'::config.tipo_profilo_accesso
  )
ORDER BY id.id
LIMIT 1;

-- Pulisce whitelist preesistenti per l'utente di test (guard_delete override).
SET LOCAL zeroerp.allow_user_emittente_delete_override = 'on';
DELETE FROM config.user_emittenti_fiscali
 WHERE auth_user_id = (SELECT user_id FROM tmp_guard_ctx);
SET LOCAL zeroerp.allow_user_emittente_delete_override = '';

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
