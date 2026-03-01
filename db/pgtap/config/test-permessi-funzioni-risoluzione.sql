-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: tutte le funzioni di risoluzione permessi e trigger
--       defense-in-depth guard emittente scope.
--
-- Funzioni testate:
--   config.fn_get_ruolo_sistema
--   config.fn_resolve_livello_area
--   config.fn_resolve_livello_oggetto
--   config.fn_check_azione_processo
--   config.fn_get_emittenti_scope
--   config.fn_check_user_emittente_scope
--   config.fn_get_override_scaduti
--   config.fn_get_emittenti_scope_sr_ids
--   config.trgfn_guard_emittente_scope (+ 2 trigger)
--
-- Elenco test:
--  1) fn_get_ruolo_sistema: utente OPERATIVO → 'OPERATIVO'
--  2) fn_get_ruolo_sistema: utente inesistente → NULL
--  3) fn_resolve_livello_area: OPERATIVO default → BLOCCATO
--  4) fn_resolve_livello_area: ADMIN → TUTTO
--  5) fn_resolve_livello_area: override area LETTURA → LETTURA
--  6) fn_resolve_livello_area: override scaduto → BLOCCATO
--  7) fn_resolve_livello_oggetto: OPERATIVO default → BLOCCATO
--  8) fn_resolve_livello_oggetto: override oggetto LETTURA → LETTURA
--  9) fn_resolve_livello_oggetto: fallback ad area TUTTO → TUTTO
-- 10) fn_check_azione_processo: OPERATIVO default → false
-- 11) fn_check_azione_processo: ADMIN → true
-- 12) fn_check_azione_processo: override abilitata → true
-- 13) fn_get_emittenti_scope: senza whitelist → NULL
-- 14) fn_check_user_emittente_scope: NULL user → true (batch)
-- 15) fn_check_user_emittente_scope: ADMIN → true
-- 16) fn_check_user_emittente_scope: OPERATIVO senza whitelist → true
-- 17) fn_check_user_emittente_scope: emittente in whitelist → true
-- 18) fn_check_user_emittente_scope: emittente fuori whitelist → false
-- 19) fn_get_emittenti_scope: con whitelist → array contiene emittente
-- 20) fn_get_override_scaduti(0): override scaduto trovato
-- 21) fn_get_override_scaduti(30): override recente escluso da tolleranza
-- 22) Trigger function trgfn_guard_emittente_scope esiste
-- 23) Trigger su vendite.fatture esiste (BEFORE INSERT OR UPDATE)
-- 24) Trigger su pagamenti.vendite_movimenti esiste
-- 25) Integrazione: fn_check blocca emittente fuori scope
-- 26) fn_get_emittenti_scope_sr_ids: OPERATIVO con whitelist → array con sr_id
-- 27) fn_get_emittenti_scope_sr_ids: ADMIN → NULL
-- 28) fn_get_emittenti_scope_sr_ids: OPERATIVO senza whitelist → NULL
-- 29) fn_get_emittenti_scope_sr_ids: DISABILITATO → array vuoto
-- 30) Seed: 3 nuovi codename azioni_processo esistono
-- ------------------------------------------------------------

BEGIN;

SELECT plan(30);

-- ============================================================
-- 0. Setup: raccolta riferimenti e forzatura OPERATIVO
-- ============================================================

CREATE TEMP TABLE tmp_ctx AS
SELECT
    rau.auth_user_id  AS user_id,
    af.id             AS area_id,
    af.schema_db      AS area_schema_db,
    ap.id             AS azione_id,
    ap.permission_codename,
    ef.id                  AS emittente_id,
    ef.soggetto_ruolo_id   AS emittente_sr_id,
    -1::bigint             AS emittente_ko_id
FROM anagrafiche.risorse_umane_auth_user rau
CROSS JOIN (
    SELECT id, schema_db FROM config.aree_funzionali
    WHERE attivo = true AND schema_db = 'vendite'
) af
CROSS JOIN (
    SELECT id, permission_codename FROM config.azioni_processo
    WHERE attivo = true ORDER BY id LIMIT 1
) ap
CROSS JOIN (
    SELECT id, soggetto_ruolo_id FROM anagrafiche.emittenti_fiscali
    WHERE attivo = true ORDER BY id LIMIT 1
) ef
ORDER BY rau.id
LIMIT 1;

-- Forza OPERATIVO (ROLLBACK ripristina)
UPDATE anagrafiche.risorse_umane_auth_user
   SET ruolo_sistema = 'OPERATIVO'
 WHERE auth_user_id = (SELECT user_id FROM tmp_ctx);

-- Rimuovi eventuali override/whitelist preesistenti per utente test
DELETE FROM config.user_override_aree
 WHERE auth_user_id = (SELECT user_id FROM tmp_ctx);

DELETE FROM config.user_override_oggetti
 WHERE auth_user_id = (SELECT user_id FROM tmp_ctx);

DELETE FROM config.user_override_azioni
 WHERE auth_user_id = (SELECT user_id FROM tmp_ctx);

DELETE FROM config.user_emittenti_fiscali
 WHERE auth_user_id = (SELECT user_id FROM tmp_ctx);

-- ============================================================
-- A. fn_get_ruolo_sistema
-- ============================================================

-- 1) Utente OPERATIVO
SELECT is(
    config.fn_get_ruolo_sistema(
        (SELECT user_id FROM tmp_ctx)
    ),
    'OPERATIVO'::config.ruolo_sistema,
    'fn_get_ruolo_sistema: utente forzato OPERATIVO'
);

-- 2) Utente inesistente → NULL
SELECT is(
    config.fn_get_ruolo_sistema(99999999),
    NULL::config.ruolo_sistema,
    'fn_get_ruolo_sistema: utente inesistente → NULL'
);

-- ============================================================
-- B. fn_resolve_livello_area
-- ============================================================

-- 3) OPERATIVO senza override/profilo → BLOCCATO (default)
SELECT is(
    config.fn_resolve_livello_area(
        (SELECT user_id FROM tmp_ctx),
        (SELECT area_schema_db FROM tmp_ctx)
    ),
    'BLOCCATO'::config.livello_accesso,
    'fn_resolve_livello_area: OPERATIVO default → BLOCCATO'
);

-- 4) ADMIN → TUTTO
UPDATE anagrafiche.risorse_umane_auth_user
   SET ruolo_sistema = 'ADMIN'
 WHERE auth_user_id = (SELECT user_id FROM tmp_ctx);

SELECT is(
    config.fn_resolve_livello_area(
        (SELECT user_id FROM tmp_ctx),
        (SELECT area_schema_db FROM tmp_ctx)
    ),
    'TUTTO'::config.livello_accesso,
    'fn_resolve_livello_area: ADMIN → TUTTO'
);

UPDATE anagrafiche.risorse_umane_auth_user
   SET ruolo_sistema = 'OPERATIVO'
 WHERE auth_user_id = (SELECT user_id FROM tmp_ctx);

-- 5) Override area LETTURA → LETTURA
INSERT INTO config.user_override_aree
    (auth_user_id, area_id, livello, meta)
SELECT user_id, area_id, 'LETTURA'::config.livello_accesso,
       '{"test_scope":"pgtap_funzioni_risoluzione"}'::jsonb
FROM tmp_ctx;

SELECT is(
    config.fn_resolve_livello_area(
        (SELECT user_id FROM tmp_ctx),
        (SELECT area_schema_db FROM tmp_ctx)
    ),
    'LETTURA'::config.livello_accesso,
    'fn_resolve_livello_area: override area LETTURA → LETTURA'
);

-- 6) Override scaduto (valido_al = ieri) → ignorato → BLOCCATO
UPDATE config.user_override_aree
   SET valido_dal = CURRENT_DATE - 30,
       valido_al  = CURRENT_DATE - 1
 WHERE auth_user_id = (SELECT user_id FROM tmp_ctx)
   AND area_id = (SELECT area_id FROM tmp_ctx);

SELECT is(
    config.fn_resolve_livello_area(
        (SELECT user_id FROM tmp_ctx),
        (SELECT area_schema_db FROM tmp_ctx)
    ),
    'BLOCCATO'::config.livello_accesso,
    'fn_resolve_livello_area: override scaduto → BLOCCATO'
);

-- Pulizia override area per test successivi
DELETE FROM config.user_override_aree
 WHERE auth_user_id = (SELECT user_id FROM tmp_ctx);

-- ============================================================
-- C. fn_resolve_livello_oggetto
-- ============================================================

-- 7) OPERATIVO senza override → BLOCCATO (fallback area = BLOCCATO)
SELECT is(
    config.fn_resolve_livello_oggetto(
        (SELECT user_id FROM tmp_ctx),
        'vendite', 'fatture',
        (SELECT area_schema_db FROM tmp_ctx)
    ),
    'BLOCCATO'::config.livello_accesso,
    'fn_resolve_livello_oggetto: OPERATIVO default → BLOCCATO'
);

-- 8) Override oggetto LETTURA → LETTURA
INSERT INTO config.user_override_oggetti
    (auth_user_id, app_label, model_name, livello, meta)
SELECT user_id, 'vendite', 'fatture', 'LETTURA'::config.livello_accesso,
       '{"test_scope":"pgtap_funzioni_risoluzione"}'::jsonb
FROM tmp_ctx;

SELECT is(
    config.fn_resolve_livello_oggetto(
        (SELECT user_id FROM tmp_ctx),
        'vendite', 'fatture',
        (SELECT area_schema_db FROM tmp_ctx)
    ),
    'LETTURA'::config.livello_accesso,
    'fn_resolve_livello_oggetto: override oggetto LETTURA → LETTURA'
);

DELETE FROM config.user_override_oggetti
 WHERE auth_user_id = (SELECT user_id FROM tmp_ctx);

-- 9) Fallback ad area: override area TUTTO, nessun override oggetto → TUTTO
INSERT INTO config.user_override_aree
    (auth_user_id, area_id, livello, meta)
SELECT user_id, area_id, 'TUTTO'::config.livello_accesso,
       '{"test_scope":"pgtap_funzioni_risoluzione"}'::jsonb
FROM tmp_ctx;

SELECT is(
    config.fn_resolve_livello_oggetto(
        (SELECT user_id FROM tmp_ctx),
        'vendite', 'fatture',
        (SELECT area_schema_db FROM tmp_ctx)
    ),
    'TUTTO'::config.livello_accesso,
    'fn_resolve_livello_oggetto: fallback ad area TUTTO → TUTTO'
);

DELETE FROM config.user_override_aree
 WHERE auth_user_id = (SELECT user_id FROM tmp_ctx);

-- ============================================================
-- D. fn_check_azione_processo
-- ============================================================

-- 10) OPERATIVO senza override/profilo → false (default)
SELECT is(
    config.fn_check_azione_processo(
        (SELECT user_id FROM tmp_ctx),
        (SELECT permission_codename FROM tmp_ctx)
    ),
    false,
    'fn_check_azione_processo: OPERATIVO default → false'
);

-- 11) ADMIN → true
UPDATE anagrafiche.risorse_umane_auth_user
   SET ruolo_sistema = 'ADMIN'
 WHERE auth_user_id = (SELECT user_id FROM tmp_ctx);

SELECT is(
    config.fn_check_azione_processo(
        (SELECT user_id FROM tmp_ctx),
        (SELECT permission_codename FROM tmp_ctx)
    ),
    true,
    'fn_check_azione_processo: ADMIN → true'
);

UPDATE anagrafiche.risorse_umane_auth_user
   SET ruolo_sistema = 'OPERATIVO'
 WHERE auth_user_id = (SELECT user_id FROM tmp_ctx);

-- 12) Override azione abilitata → true
INSERT INTO config.user_override_azioni
    (auth_user_id, azione_id, abilitata, meta)
SELECT user_id, azione_id, true,
       '{"test_scope":"pgtap_funzioni_risoluzione"}'::jsonb
FROM tmp_ctx;

SELECT is(
    config.fn_check_azione_processo(
        (SELECT user_id FROM tmp_ctx),
        (SELECT permission_codename FROM tmp_ctx)
    ),
    true,
    'fn_check_azione_processo: override abilitata → true'
);

DELETE FROM config.user_override_azioni
 WHERE auth_user_id = (SELECT user_id FROM tmp_ctx);

-- ============================================================
-- E. fn_get_emittenti_scope + fn_check_user_emittente_scope
-- ============================================================

-- 13) fn_get_emittenti_scope: senza whitelist → NULL
SELECT is(
    config.fn_get_emittenti_scope(
        (SELECT user_id FROM tmp_ctx)
    ),
    NULL::bigint[],
    'fn_get_emittenti_scope: senza whitelist → NULL'
);

-- 14) fn_check NULL user → true (batch job)
SELECT is(
    config.fn_check_user_emittente_scope(
        NULL,
        (SELECT emittente_id FROM tmp_ctx)
    ),
    true,
    'fn_check_user_emittente_scope: NULL user → true (batch)'
);

-- 15) fn_check ADMIN → true
UPDATE anagrafiche.risorse_umane_auth_user
   SET ruolo_sistema = 'ADMIN'
 WHERE auth_user_id = (SELECT user_id FROM tmp_ctx);

SELECT is(
    config.fn_check_user_emittente_scope(
        (SELECT user_id FROM tmp_ctx),
        (SELECT emittente_id FROM tmp_ctx)
    ),
    true,
    'fn_check_user_emittente_scope: ADMIN → true'
);

UPDATE anagrafiche.risorse_umane_auth_user
   SET ruolo_sistema = 'OPERATIVO'
 WHERE auth_user_id = (SELECT user_id FROM tmp_ctx);

-- 16) OPERATIVO senza whitelist → true (nessuna restrizione)
SELECT is(
    config.fn_check_user_emittente_scope(
        (SELECT user_id FROM tmp_ctx),
        (SELECT emittente_id FROM tmp_ctx)
    ),
    true,
    'fn_check_user_emittente_scope: OPERATIVO senza whitelist → true'
);

-- Inserisce whitelist per emittente_id (reale)
INSERT INTO config.user_emittenti_fiscali
    (auth_user_id, emittente_fiscale_id, meta)
SELECT user_id, emittente_id,
       '{"test_scope":"pgtap_funzioni_risoluzione"}'::jsonb
FROM tmp_ctx;

-- 17) Emittente in whitelist → true
SELECT is(
    config.fn_check_user_emittente_scope(
        (SELECT user_id FROM tmp_ctx),
        (SELECT emittente_id FROM tmp_ctx)
    ),
    true,
    'fn_check_user_emittente_scope: emittente in whitelist → true'
);

-- 18) Emittente fuori whitelist → false
SELECT is(
    config.fn_check_user_emittente_scope(
        (SELECT user_id FROM tmp_ctx),
        (SELECT emittente_ko_id FROM tmp_ctx)
    ),
    false,
    'fn_check_user_emittente_scope: emittente fuori whitelist → false'
);

-- 19) fn_get_emittenti_scope: array contiene emittente
SELECT ok(
    (SELECT emittente_id FROM tmp_ctx) = ANY(
        config.fn_get_emittenti_scope(
            (SELECT user_id FROM tmp_ctx)
        )
    ),
    'fn_get_emittenti_scope: con whitelist → array contiene emittente'
);

-- ============================================================
-- F. fn_get_override_scaduti
-- ============================================================

-- Inserisce override scaduto (valido_dal = 30 gg fa, valido_al = 10 gg fa)
INSERT INTO config.user_override_aree
    (auth_user_id, area_id, livello, valido_dal, valido_al, meta)
SELECT user_id, area_id, 'LETTURA'::config.livello_accesso,
       CURRENT_DATE - 30, CURRENT_DATE - 10,
       '{"test_scope":"pgtap_funzioni_risoluzione"}'::jsonb
FROM tmp_ctx;

-- 20) Tolleranza 0 → trova override scaduto
SELECT ok(
    EXISTS (
        SELECT 1 FROM config.fn_get_override_scaduti(0)
        WHERE auth_user_id = (SELECT user_id FROM tmp_ctx)
          AND tipo_override = 'user_override_aree'
    ),
    'fn_get_override_scaduti(0): override scaduto trovato'
);

-- 21) Tolleranza 30 → non trova (scaduto solo da 10 giorni)
SELECT ok(
    NOT EXISTS (
        SELECT 1 FROM config.fn_get_override_scaduti(30)
        WHERE auth_user_id = (SELECT user_id FROM tmp_ctx)
          AND tipo_override = 'user_override_aree'
    ),
    'fn_get_override_scaduti(30): override recente escluso da tolleranza'
);

-- ============================================================
-- G. trgfn_guard_emittente_scope + trigger
-- ============================================================

-- 22) Trigger function esiste
SELECT ok(
    EXISTS (
        SELECT 1
        FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'config'
          AND p.proname = 'trgfn_guard_emittente_scope'
    ),
    'Trigger function config.trgfn_guard_emittente_scope esiste'
);

-- 23) Trigger su vendite.fatture esiste (BEFORE INSERT OR UPDATE)
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
          AND (t.tgtype::int & 2)  > 0  -- BEFORE
          AND (t.tgtype::int & 4)  > 0  -- INSERT
          AND (t.tgtype::int & 16) > 0  -- UPDATE
    ),
    'Trigger vendite.fatture: BEFORE INSERT OR UPDATE esiste'
);

-- 24) Trigger su pagamenti.vendite_movimenti esiste
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
    'Trigger pagamenti.vendite_movimenti esiste'
);

-- 25) Integrazione: fn_check blocca emittente fuori scope
--     La whitelist e gia inserita (emittente_id in scope).
--     Setta sessione e verifica che emittente_ko sia bloccato.
SELECT set_config('app.current_user_id',
    (SELECT user_id::text FROM tmp_ctx), true);

SELECT is(
    config.fn_check_user_emittente_scope(
        (SELECT user_id FROM tmp_ctx),
        (SELECT emittente_ko_id FROM tmp_ctx)
    ),
    false,
    'Integrazione: fn_check blocca emittente fuori scope (catena trigger)'
);

-- ============================================================
-- H. fn_get_emittenti_scope_sr_ids
--    (whitelist presente da sezione E, utente OPERATIVO)
-- ============================================================

-- 26) OPERATIVO con whitelist → array contiene soggetto_ruolo_id
SELECT ok(
    (SELECT emittente_sr_id FROM tmp_ctx) = ANY(
        config.fn_get_emittenti_scope_sr_ids(
            (SELECT user_id FROM tmp_ctx)
        )
    ),
    'fn_get_emittenti_scope_sr_ids: OPERATIVO con whitelist → array con sr_id'
);

-- 27) ADMIN → NULL (nessuna restrizione)
UPDATE anagrafiche.risorse_umane_auth_user
   SET ruolo_sistema = 'ADMIN'
 WHERE auth_user_id = (SELECT user_id FROM tmp_ctx);

SELECT is(
    config.fn_get_emittenti_scope_sr_ids(
        (SELECT user_id FROM tmp_ctx)
    ),
    NULL::bigint[],
    'fn_get_emittenti_scope_sr_ids: ADMIN → NULL'
);

UPDATE anagrafiche.risorse_umane_auth_user
   SET ruolo_sistema = 'OPERATIVO'
 WHERE auth_user_id = (SELECT user_id FROM tmp_ctx);

-- Rimuovi whitelist per test "senza whitelist"
DELETE FROM config.user_emittenti_fiscali
 WHERE auth_user_id = (SELECT user_id FROM tmp_ctx);

-- 28) OPERATIVO senza whitelist → NULL (nessuna restrizione)
SELECT is(
    config.fn_get_emittenti_scope_sr_ids(
        (SELECT user_id FROM tmp_ctx)
    ),
    NULL::bigint[],
    'fn_get_emittenti_scope_sr_ids: OPERATIVO senza whitelist → NULL'
);

-- 29) DISABILITATO → array vuoto (nessun accesso)
UPDATE anagrafiche.risorse_umane_auth_user
   SET ruolo_sistema = 'DISABILITATO'
 WHERE auth_user_id = (SELECT user_id FROM tmp_ctx);

SELECT is(
    config.fn_get_emittenti_scope_sr_ids(
        (SELECT user_id FROM tmp_ctx)
    ),
    '{}'::bigint[],
    'fn_get_emittenti_scope_sr_ids: DISABILITATO → array vuoto'
);

UPDATE anagrafiche.risorse_umane_auth_user
   SET ruolo_sistema = 'OPERATIVO'
 WHERE auth_user_id = (SELECT user_id FROM tmp_ctx);

-- ============================================================
-- I. Seed azioni_processo — nuovi codename
-- ============================================================

-- 30) Verifica che i 3 nuovi codename esistano
SELECT is(
    (SELECT count(*)::integer
       FROM config.azioni_processo
      WHERE permission_codename IN (
              'reset_lotto_draft',
              'reset_lotto_fattura_draft',
              'run_commesse_push'
            )
        AND attivo = true
    ),
    3,
    'Seed: 3 nuovi codename azioni_processo presenti e attivi'
);

SELECT * FROM finish();

ROLLBACK;
