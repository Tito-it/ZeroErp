-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: tutte le funzioni di risoluzione permessi e trigger
--       defense-in-depth guard emittente scope.
--
-- Migrazione Fase 7 Chunk A (2026-04-29):
--   Pre-cutover il test forzava lo stato dell'utente via UPDATE su
--   rau.ruolo_sistema (OPERATIVO/ADMIN/DISABILITATO). Post-cutover
--   §13.3 RAU e' vista non updatable + ruolo_sistema CASE calcolato.
--   Sostituzioni:
--     UPDATE rau SET ruolo_sistema='OPERATIVO' (forzatura iniziale)
--       -> setup pesca identita OPERATORE attiva non-SA (filtro
--          NOT EXISTS, pattern §4.bis): stato gia' "OPERATIVO".
--     UPDATE rau SET ruolo_sistema='ADMIN' (cicli temporanei)
--       -> INSERT binding SUPER_ADMIN (helper pg_temp.set_admin).
--     UPDATE rau SET ruolo_sistema='OPERATIVO' (ripristino post-ADMIN)
--       -> DELETE del binding (helper pg_temp.unset_admin). Filtro
--          vergine garantisce che il nuovo SA non sia l'unico ->
--          guard 384 anti-lockout non scatta.
--     UPDATE rau SET ruolo_sistema='DISABILITATO' (test 29)
--       -> UPDATE id.ruolo_applicativo='DISABILITATO'
--          (helper pg_temp.set_disabilitato).
--     Ripristino post-DISABILITATO -> UPDATE id.ruolo_applicativo
--          ='OPERATORE' (helper pg_temp.unset_disabilitato).
--
-- Funzioni testate:
--   script.fn_is_super_admin (sostituisce fn_get_ruolo_sistema
--     droppata in Fase 7 cleanup 2026-04-29),
--   script.fn_resolve_livello_area,
--   script.fn_resolve_livello_oggetto,
--   script.fn_get_user_object_permissions_map,
--   script.fn_check_azione_processo,
--   script.fn_get_emittenti_scope,
--   script.fn_check_user_emittente_scope,
--   script.fn_get_override_scaduti,
--   script.fn_get_emittenti_scope_sr_ids,
--   script.trgfn_guard_emittente_scope (+ 2 trigger).
--
-- Elenco test:
--  1) fn_is_super_admin: utente OPERATORE non-SA → false
--  2) fn_is_super_admin: utente inesistente → false (fail-closed)
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
-- 31) fn_get_user_object_permissions_map: nessun override → {}
-- 32) fn_get_user_object_permissions_map: override attivo → chiave presente
-- 33) fn_get_user_object_permissions_map: override scaduto → escluso
-- 34) fn_get_user_object_permissions_map: override futuro → escluso
-- ------------------------------------------------------------

BEGIN;

SELECT plan(34);

-- ============================================================
-- Helper pg_temp per il refactor multi-face:
--   set_admin / unset_admin    -> INSERT/DELETE binding SUPER_ADMIN
--   set_disabilitato / unset_disabilitato -> UPDATE id.ruolo_applicativo
-- ============================================================
CREATE OR REPLACE FUNCTION pg_temp.set_admin(p_identita_id bigint)
RETURNS void LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO config.profili_accesso_bindings
        (profilo_accesso_id, identita_digitale_id, attivo)
    VALUES (9100, p_identita_id, true)
    ON CONFLICT DO NOTHING;
END
$$;

CREATE OR REPLACE FUNCTION pg_temp.unset_admin(p_identita_id bigint)
RETURNS void LANGUAGE plpgsql AS $$
BEGIN
    DELETE FROM config.profili_accesso_bindings
     WHERE identita_digitale_id = p_identita_id
       AND profilo_accesso_id = 9100;
END
$$;

CREATE OR REPLACE FUNCTION pg_temp.set_disabilitato(p_identita_id bigint)
RETURNS void LANGUAGE plpgsql AS $$
BEGIN
    UPDATE anagrafiche.identita_digitali
       SET ruolo_applicativo = 'DISABILITATO'::config.ruolo_applicativo
     WHERE id = p_identita_id;
END
$$;

CREATE OR REPLACE FUNCTION pg_temp.unset_disabilitato(p_identita_id bigint)
RETURNS void LANGUAGE plpgsql AS $$
BEGIN
    UPDATE anagrafiche.identita_digitali
       SET ruolo_applicativo = 'OPERATORE'::config.ruolo_applicativo
     WHERE id = p_identita_id;
END
$$;

-- ============================================================
-- 0. Setup: identita OPERATORE attiva non-SA (filtro vergine)
--    + area_funzionali + azioni_processo + emittente reale.
-- ============================================================

CREATE TEMP TABLE tmp_ctx AS
SELECT
    id.auth_user_id        AS user_id,
    id.id                  AS identita_id,
    af.id                  AS area_id,
    af.schema_db           AS area_schema_db,
    ap.id                  AS azione_id,
    ap.permission_codename,
    ef.id                  AS emittente_id,
    ef.soggetto_ruolo_id   AS emittente_sr_id,
    -1::bigint             AS emittente_ko_id
FROM anagrafiche.identita_digitali id
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
  -- Esclude utenti con profili (AD_HOC/PORTALE/REPARTO) che concedono
  -- accesso a 'vendite': fn_resolve_livello_area step 4 li promuoverebbe
  -- oltre BLOCCATO, rompendo i test 3/6/7 che aspettano il default.
  AND NOT EXISTS (
      SELECT 1
        FROM script.fn_get_profili_accesso_applicabili(id.auth_user_id) h
        JOIN config.profili_accesso_aree paa ON paa.profilo_accesso_id = h.profilo_accesso_id
        JOIN config.aree_funzionali af2 ON af2.id = paa.area_id
       WHERE af2.schema_db = 'vendite'
  )
ORDER BY id.id
LIMIT 1;

-- Rimuovi eventuali override/whitelist preesistenti per utente test
DELETE FROM config.user_override_aree
 WHERE auth_user_id = (SELECT user_id FROM tmp_ctx);

DELETE FROM config.user_override_oggetti
 WHERE auth_user_id = (SELECT user_id FROM tmp_ctx);

DELETE FROM config.user_override_azioni
 WHERE auth_user_id = (SELECT user_id FROM tmp_ctx);

SET LOCAL zeroerp.allow_user_emittente_delete_override = 'on';
DELETE FROM config.user_emittenti_fiscali
 WHERE auth_user_id = (SELECT user_id FROM tmp_ctx);
SET LOCAL zeroerp.allow_user_emittente_delete_override = '';

-- ============================================================
-- A. fn_is_super_admin (sostituisce fn_get_ruolo_sistema droppata
--    in Fase 7 cleanup 2026-04-29)
-- ============================================================

-- 1) Utente OPERATORE non-SA (filtro vergine al setup) → false
SELECT is(
    script.fn_is_super_admin(
        (SELECT user_id FROM tmp_ctx)
    ),
    false,
    '1) fn_is_super_admin: utente OPERATORE non-SA → false'
);

-- 2) Utente inesistente → false (fail-closed)
SELECT is(
    script.fn_is_super_admin(99999999),
    false,
    '2) fn_is_super_admin: utente inesistente → false (fail-closed)'
);

-- ============================================================
-- B. fn_resolve_livello_area
-- ============================================================

-- 3) OPERATIVO senza override/profilo → BLOCCATO (default)
SELECT is(
    script.fn_resolve_livello_area(
        (SELECT user_id FROM tmp_ctx),
        (SELECT area_schema_db FROM tmp_ctx)
    ),
    'BLOCCATO'::config.livello_accesso,
    '3) fn_resolve_livello_area: OPERATIVO default → BLOCCATO'
);

-- 4) ADMIN → TUTTO
SELECT pg_temp.set_admin((SELECT identita_id FROM tmp_ctx));

SELECT is(
    script.fn_resolve_livello_area(
        (SELECT user_id FROM tmp_ctx),
        (SELECT area_schema_db FROM tmp_ctx)
    ),
    'TUTTO'::config.livello_accesso,
    '4) fn_resolve_livello_area: ADMIN → TUTTO'
);

SELECT pg_temp.unset_admin((SELECT identita_id FROM tmp_ctx));

-- 5) Override area LETTURA → LETTURA
INSERT INTO config.user_override_aree
    (auth_user_id, area_id, livello, meta)
SELECT user_id, area_id, 'LETTURA'::config.livello_accesso,
       '{"test_scope":"pgtap_funzioni_risoluzione"}'::jsonb
FROM tmp_ctx;

SELECT is(
    script.fn_resolve_livello_area(
        (SELECT user_id FROM tmp_ctx),
        (SELECT area_schema_db FROM tmp_ctx)
    ),
    'LETTURA'::config.livello_accesso,
    '5) fn_resolve_livello_area: override area LETTURA → LETTURA'
);

-- 6) Override scaduto (valido_al = ieri) → ignorato → BLOCCATO
UPDATE config.user_override_aree
   SET valido_dal = CURRENT_DATE - 30,
       valido_al  = CURRENT_DATE - 1
 WHERE auth_user_id = (SELECT user_id FROM tmp_ctx)
   AND area_id = (SELECT area_id FROM tmp_ctx);

SELECT is(
    script.fn_resolve_livello_area(
        (SELECT user_id FROM tmp_ctx),
        (SELECT area_schema_db FROM tmp_ctx)
    ),
    'BLOCCATO'::config.livello_accesso,
    '6) fn_resolve_livello_area: override scaduto → BLOCCATO'
);

-- Pulizia override area per test successivi
DELETE FROM config.user_override_aree
 WHERE auth_user_id = (SELECT user_id FROM tmp_ctx);

-- ============================================================
-- C. fn_resolve_livello_oggetto
-- ============================================================

-- 7) OPERATIVO senza override → BLOCCATO (fallback area = BLOCCATO)
SELECT is(
    script.fn_resolve_livello_oggetto(
        (SELECT user_id FROM tmp_ctx),
        'vendite', 'fatture',
        (SELECT area_schema_db FROM tmp_ctx)
    ),
    'BLOCCATO'::config.livello_accesso,
    '7) fn_resolve_livello_oggetto: OPERATIVO default → BLOCCATO'
);

-- 8) Override oggetto LETTURA → LETTURA
INSERT INTO config.user_override_oggetti
    (auth_user_id, app_label, model_name, livello, meta)
SELECT user_id, 'vendite', 'fatture', 'LETTURA'::config.livello_accesso,
       '{"test_scope":"pgtap_funzioni_risoluzione"}'::jsonb
FROM tmp_ctx;

SELECT is(
    script.fn_resolve_livello_oggetto(
        (SELECT user_id FROM tmp_ctx),
        'vendite', 'fatture',
        (SELECT area_schema_db FROM tmp_ctx)
    ),
    'LETTURA'::config.livello_accesso,
    '8) fn_resolve_livello_oggetto: override oggetto LETTURA → LETTURA'
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
    script.fn_resolve_livello_oggetto(
        (SELECT user_id FROM tmp_ctx),
        'vendite', 'fatture',
        (SELECT area_schema_db FROM tmp_ctx)
    ),
    'TUTTO'::config.livello_accesso,
    '9) fn_resolve_livello_oggetto: fallback ad area TUTTO → TUTTO'
);

DELETE FROM config.user_override_aree
 WHERE auth_user_id = (SELECT user_id FROM tmp_ctx);

-- ============================================================
-- D. fn_check_azione_processo
-- ============================================================

-- 10) OPERATIVO senza override/profilo → false (default)
SELECT is(
    script.fn_check_azione_processo(
        (SELECT user_id FROM tmp_ctx),
        (SELECT permission_codename FROM tmp_ctx)
    ),
    false,
    '10) fn_check_azione_processo: OPERATIVO default → false'
);

-- 11) ADMIN → true
SELECT pg_temp.set_admin((SELECT identita_id FROM tmp_ctx));

SELECT is(
    script.fn_check_azione_processo(
        (SELECT user_id FROM tmp_ctx),
        (SELECT permission_codename FROM tmp_ctx)
    ),
    true,
    '11) fn_check_azione_processo: ADMIN → true'
);

SELECT pg_temp.unset_admin((SELECT identita_id FROM tmp_ctx));

-- 12) Override azione abilitata → true
INSERT INTO config.user_override_azioni
    (auth_user_id, azione_id, abilitata, meta)
SELECT user_id, azione_id, true,
       '{"test_scope":"pgtap_funzioni_risoluzione"}'::jsonb
FROM tmp_ctx;

SELECT is(
    script.fn_check_azione_processo(
        (SELECT user_id FROM tmp_ctx),
        (SELECT permission_codename FROM tmp_ctx)
    ),
    true,
    '12) fn_check_azione_processo: override abilitata → true'
);

DELETE FROM config.user_override_azioni
 WHERE auth_user_id = (SELECT user_id FROM tmp_ctx);

-- ============================================================
-- E. fn_get_emittenti_scope + fn_check_user_emittente_scope
-- ============================================================

-- 13) fn_get_emittenti_scope: senza whitelist → NULL
SELECT is(
    script.fn_get_emittenti_scope(
        (SELECT user_id FROM tmp_ctx)
    ),
    NULL::bigint[],
    '13) fn_get_emittenti_scope: senza whitelist → NULL'
);

-- 14) fn_check NULL user → true (batch job)
SELECT is(
    script.fn_check_user_emittente_scope(
        NULL,
        (SELECT emittente_id FROM tmp_ctx)
    ),
    true,
    '14) fn_check_user_emittente_scope: NULL user → true (batch)'
);

-- 15) fn_check ADMIN → true
SELECT pg_temp.set_admin((SELECT identita_id FROM tmp_ctx));

SELECT is(
    script.fn_check_user_emittente_scope(
        (SELECT user_id FROM tmp_ctx),
        (SELECT emittente_id FROM tmp_ctx)
    ),
    true,
    '15) fn_check_user_emittente_scope: ADMIN → true'
);

SELECT pg_temp.unset_admin((SELECT identita_id FROM tmp_ctx));

-- 16) OPERATIVO senza whitelist → true (nessuna restrizione)
SELECT is(
    script.fn_check_user_emittente_scope(
        (SELECT user_id FROM tmp_ctx),
        (SELECT emittente_id FROM tmp_ctx)
    ),
    true,
    '16) fn_check_user_emittente_scope: OPERATIVO senza whitelist → true'
);

-- Inserisce whitelist per emittente_id (reale)
INSERT INTO config.user_emittenti_fiscali
    (auth_user_id, emittente_fiscale_id, meta)
SELECT user_id, emittente_id,
       '{"test_scope":"pgtap_funzioni_risoluzione"}'::jsonb
FROM tmp_ctx;

-- 17) Emittente in whitelist → true
SELECT is(
    script.fn_check_user_emittente_scope(
        (SELECT user_id FROM tmp_ctx),
        (SELECT emittente_id FROM tmp_ctx)
    ),
    true,
    '17) fn_check_user_emittente_scope: emittente in whitelist → true'
);

-- 18) Emittente fuori whitelist → false
SELECT is(
    script.fn_check_user_emittente_scope(
        (SELECT user_id FROM tmp_ctx),
        (SELECT emittente_ko_id FROM tmp_ctx)
    ),
    false,
    '18) fn_check_user_emittente_scope: emittente fuori whitelist → false'
);

-- 19) fn_get_emittenti_scope: array contiene emittente
SELECT ok(
    (SELECT emittente_id FROM tmp_ctx) = ANY(
        script.fn_get_emittenti_scope(
            (SELECT user_id FROM tmp_ctx)
        )
    ),
    '19) fn_get_emittenti_scope: con whitelist → array contiene emittente'
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
        SELECT 1 FROM script.fn_get_override_scaduti(0)
        WHERE auth_user_id = (SELECT user_id FROM tmp_ctx)
          AND tipo_override = 'user_override_aree'
    ),
    '20) fn_get_override_scaduti(0): override scaduto trovato'
);

-- 21) Tolleranza 30 → non trova (scaduto solo da 10 giorni)
SELECT ok(
    NOT EXISTS (
        SELECT 1 FROM script.fn_get_override_scaduti(30)
        WHERE auth_user_id = (SELECT user_id FROM tmp_ctx)
          AND tipo_override = 'user_override_aree'
    ),
    '21) fn_get_override_scaduti(30): override recente escluso da tolleranza'
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
        WHERE n.nspname = 'script'
          AND p.proname = 'trgfn_guard_emittente_scope'
    ),
    '22) Trigger function script.trgfn_guard_emittente_scope esiste'
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
    '23) Trigger vendite.fatture: BEFORE INSERT OR UPDATE esiste'
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
    '24) Trigger pagamenti.vendite_movimenti esiste'
);

-- 25) Integrazione: fn_check blocca emittente fuori scope
--     La whitelist e' gia inserita (emittente_id in scope).
SELECT set_config('app.current_user_id',
    (SELECT user_id::text FROM tmp_ctx), true);

SELECT is(
    script.fn_check_user_emittente_scope(
        (SELECT user_id FROM tmp_ctx),
        (SELECT emittente_ko_id FROM tmp_ctx)
    ),
    false,
    '25) Integrazione: fn_check blocca emittente fuori scope (catena trigger)'
);

-- ============================================================
-- H. fn_get_emittenti_scope_sr_ids
--    (whitelist presente da sezione E, utente OPERATIVO)
-- ============================================================

-- 26) OPERATIVO con whitelist → array contiene soggetto_ruolo_id
SELECT ok(
    (SELECT emittente_sr_id FROM tmp_ctx) = ANY(
        script.fn_get_emittenti_scope_sr_ids(
            (SELECT user_id FROM tmp_ctx)
        )
    ),
    '26) fn_get_emittenti_scope_sr_ids: OPERATIVO con whitelist → array con sr_id'
);

-- 27) ADMIN → NULL (nessuna restrizione)
SELECT pg_temp.set_admin((SELECT identita_id FROM tmp_ctx));

SELECT is(
    script.fn_get_emittenti_scope_sr_ids(
        (SELECT user_id FROM tmp_ctx)
    ),
    NULL::bigint[],
    '27) fn_get_emittenti_scope_sr_ids: ADMIN → NULL'
);

SELECT pg_temp.unset_admin((SELECT identita_id FROM tmp_ctx));

-- Rimuovi whitelist per test "senza whitelist"
SET LOCAL zeroerp.allow_user_emittente_delete_override = 'on';
DELETE FROM config.user_emittenti_fiscali
 WHERE auth_user_id = (SELECT user_id FROM tmp_ctx);
SET LOCAL zeroerp.allow_user_emittente_delete_override = '';

-- 28) OPERATIVO senza whitelist → NULL (nessuna restrizione)
SELECT is(
    script.fn_get_emittenti_scope_sr_ids(
        (SELECT user_id FROM tmp_ctx)
    ),
    NULL::bigint[],
    '28) fn_get_emittenti_scope_sr_ids: OPERATIVO senza whitelist → NULL'
);

-- 29) DISABILITATO → array vuoto (nessun accesso)
SELECT pg_temp.set_disabilitato((SELECT identita_id FROM tmp_ctx));

SELECT is(
    script.fn_get_emittenti_scope_sr_ids(
        (SELECT user_id FROM tmp_ctx)
    ),
    '{}'::bigint[],
    '29) fn_get_emittenti_scope_sr_ids: DISABILITATO → array vuoto'
);

SELECT pg_temp.unset_disabilitato((SELECT identita_id FROM tmp_ctx));

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
    '30) Seed: 3 nuovi codename azioni_processo presenti e attivi'
);

-- ============================================================
-- J. fn_get_user_object_permissions_map
-- ============================================================

-- 31) Nessun override attivo → {}
DELETE FROM config.user_override_oggetti
 WHERE auth_user_id = (SELECT user_id FROM tmp_ctx);

SELECT is(
    script.fn_get_user_object_permissions_map(
        (SELECT user_id FROM tmp_ctx)
    ),
    '{}'::jsonb,
    '31) fn_get_user_object_permissions_map: nessun override → {}'
);

-- 32) Override attivo → chiave presente
INSERT INTO config.user_override_oggetti
    (auth_user_id, app_label, model_name, livello, meta)
SELECT user_id, 'vendite', 'fattura', 'LETTURA'::config.livello_accesso,
       '{"test_scope":"pgtap_funzioni_risoluzione"}'::jsonb
FROM tmp_ctx;

SELECT is(
    script.fn_get_user_object_permissions_map(
        (SELECT user_id FROM tmp_ctx)
    ) ->> 'vendite.fattura',
    'LETTURA',
    '32) fn_get_user_object_permissions_map: override attivo → chiave presente'
);

-- 33) Override scaduto → escluso
UPDATE config.user_override_oggetti
   SET valido_dal = CURRENT_DATE - 30,
       valido_al  = CURRENT_DATE - 1
 WHERE auth_user_id = (SELECT user_id FROM tmp_ctx)
   AND app_label = 'vendite'
   AND model_name = 'fattura';

SELECT is(
    script.fn_get_user_object_permissions_map(
        (SELECT user_id FROM tmp_ctx)
    ),
    '{}'::jsonb,
    '33) fn_get_user_object_permissions_map: override scaduto → escluso'
);

-- 34) Override futuro → escluso
UPDATE config.user_override_oggetti
   SET valido_dal = CURRENT_DATE + 1,
       valido_al  = CURRENT_DATE + 30
 WHERE auth_user_id = (SELECT user_id FROM tmp_ctx)
   AND app_label = 'vendite'
   AND model_name = 'fattura';

SELECT is(
    script.fn_get_user_object_permissions_map(
        (SELECT user_id FROM tmp_ctx)
    ),
    '{}'::jsonb,
    '34) fn_get_user_object_permissions_map: override futuro → escluso'
);

SELECT * FROM finish();

ROLLBACK;
