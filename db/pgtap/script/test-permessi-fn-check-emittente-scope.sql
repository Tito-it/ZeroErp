-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: funzioni scope emittente e flag SUPER_ADMIN
--       script.fn_is_super_admin (sostituisce fn_get_ruolo_sistema
--         droppata in Fase 7 cleanup 2026-04-29),
--       script.fn_get_emittenti_scope,
--       script.fn_check_user_emittente_scope
--
-- Migrazione Fase 7 Chunk A (2026-04-29):
--   Pre-cutover il test scriveva su rau.ruolo_sistema (UPDATE diretti).
--   Post-cutover §13.3 rau e' vista non updatable + ruolo_sistema CASE
--   calcolato. Sostituzioni:
--     UPDATE rau SET ruolo_sistema='OPERATIVO' (forzatura iniziale)
--       -> il setup pesca identita OPERATORE attiva senza binding SA
--          (filtro NOT EXISTS, pattern §4.bis): stato gia' "OPERATIVO".
--     UPDATE rau SET ruolo_sistema='ADMIN' (test 7 promotion temporanea)
--       -> INSERT binding SUPER_ADMIN su identita_digitali esistente.
--          Il filtro vergine garantisce che il nuovo SA non sia l'unico:
--          esistono altri SA preesistenti (es. seed tid), il guard 384
--          anti-lockout non scatta su DELETE successiva.
--     UPDATE rau SET ruolo_sistema='OPERATIVO' (ripristino post-7)
--       -> DELETE del binding SA appena creato.
--
-- Elenco test:
--  1) Riferimento utente OPERATORE non-SA presente
--  2) Riferimento emittenti_fiscali (1) presente
--  3) Emittente fittizio (2) diverso da emittente reale (1)
--  4) fn_is_super_admin: utente OPERATORE non-SA → false
--  5) fn_is_super_admin: utente inesistente → false (fail-closed)
--  6) fn_check_user_emittente_scope: NULL user → true (batch)
--  7) fn_check_user_emittente_scope: ADMIN → true qualunque emittente
--  8) fn_check_user_emittente_scope: OPERATIVO senza whitelist → true
--  9) fn_get_emittenti_scope: senza whitelist → NULL
-- 10) Aggiunta whitelist per emittente_1
-- 11) fn_check_user_emittente_scope: emittente_1 in whitelist → true
-- 12) fn_check_user_emittente_scope: emittente_2 non in whitelist → false
-- 13) fn_get_emittenti_scope: con whitelist → array contenente emittente_1
-- ------------------------------------------------------------

BEGIN;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(13);

-- ============================================================
-- 0. Setup: identita OPERATORE attiva senza binding SUPER_ADMIN
--    (filtro vergine non-SA, pattern §4.bis pgTAP).
-- ============================================================

CREATE TEMP TABLE tmp_refs_scope AS
SELECT
    id.auth_user_id  AS user_id,
    id.id            AS identita_id
FROM anagrafiche.identita_digitali id
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

-- Pulisce eventuali whitelist pre-esistenti per l'utente di test.
-- Override del guard_delete (trgfn_user_emittenti_fiscali_guard_delete)
-- necessario: l'utente Django associato e' ancora attivo. Reset
-- difensivo subito dopo per non lasciar leakare la GUC nel resto del
-- test.
SET LOCAL zeroerp.allow_user_emittente_delete_override = 'on';
DELETE FROM config.user_emittenti_fiscali
 WHERE auth_user_id = (SELECT user_id FROM tmp_refs_scope);
SET LOCAL zeroerp.allow_user_emittente_delete_override = '';

CREATE TEMP TABLE tmp_emittenti AS
SELECT
    ef.id       AS emittente_id_1,
    -1::bigint  AS emittente_id_2   -- fittizio: fn_check verifica solo whitelist
FROM anagrafiche.emittenti_fiscali ef
WHERE ef.attivo = true
ORDER BY ef.id
LIMIT 1;

-- 1) Setup: utente OPERATORE non-SA trovato
SELECT ok(
    (SELECT user_id FROM tmp_refs_scope) IS NOT NULL,
    '1) Setup: identita OPERATORE attiva non-SA presente'
);

SELECT ok(
    (SELECT emittente_id_1 FROM tmp_emittenti) IS NOT NULL,
    '2) Riferimento emittenti_fiscali (1) presente'
);

SELECT ok(
    (SELECT emittente_id_2 FROM tmp_emittenti) IS NOT NULL
    AND (SELECT emittente_id_2 FROM tmp_emittenti) <>
        (SELECT emittente_id_1 FROM tmp_emittenti),
    '3) Emittente fittizio (2) diverso da emittente reale (1)'
);

-- ============================================================
-- 1. fn_is_super_admin (sostituisce fn_get_ruolo_sistema droppata
--    in Fase 7 cleanup 2026-04-29)
-- ============================================================

-- 4) Utente OPERATORE non-SA → fn_is_super_admin = false
--    (filtro vergine al setup: nessun binding SA per definizione).
SELECT is(
    script.fn_is_super_admin(
        (SELECT user_id FROM tmp_refs_scope)
    ),
    false,
    '4) fn_is_super_admin: utente OPERATORE non-SA → false'
);

-- 5) Utente inesistente → fn_is_super_admin = false (fail-closed)
SELECT is(
    script.fn_is_super_admin(99999999),
    false,
    '5) fn_is_super_admin: utente inesistente → false (fail-closed)'
);

-- ============================================================
-- 2. fn_check_user_emittente_scope — casi base
-- ============================================================

-- 6) NULL user_id → true (batch job)
SELECT is(
    script.fn_check_user_emittente_scope(
        NULL,
        (SELECT emittente_id_1 FROM tmp_emittenti)
    ),
    true,
    '6) fn_check_user_emittente_scope: NULL user → true (batch job)'
);

-- 7) ADMIN → true per qualunque emittente.
-- Pre-Fase 7: UPDATE rau SET ruolo_sistema='ADMIN'.
-- Post-Fase 7: INSERT binding SUPER_ADMIN su identita esistente.
INSERT INTO config.profili_accesso_bindings
    (profilo_accesso_id, identita_digitale_id, attivo)
SELECT 9100, ctx.identita_id, true
  FROM tmp_refs_scope ctx;

SELECT is(
    script.fn_check_user_emittente_scope(
        (SELECT user_id FROM tmp_refs_scope),
        (SELECT emittente_id_1 FROM tmp_emittenti)
    ),
    true,
    '7) fn_check_user_emittente_scope: ADMIN (binding SA) → true qualunque emittente'
);

-- Ripristina stato non-SA: DELETE del binding appena creato.
-- Il guard 384 anti-lockout non scatta perche' esistono altri SA
-- preesistenti (seed tid + eventuali altri).
DELETE FROM config.profili_accesso_bindings
 WHERE identita_digitale_id = (SELECT identita_id FROM tmp_refs_scope)
   AND profilo_accesso_id = 9100;

-- 8) OPERATIVO senza whitelist → true (nessuna restrizione)
SELECT is(
    script.fn_check_user_emittente_scope(
        (SELECT user_id FROM tmp_refs_scope),
        (SELECT emittente_id_1 FROM tmp_emittenti)
    ),
    true,
    '8) fn_check_user_emittente_scope: OPERATIVO senza whitelist → true'
);

-- ============================================================
-- 3. fn_get_emittenti_scope — senza whitelist
-- ============================================================

-- 9) Senza whitelist → NULL
SELECT is(
    script.fn_get_emittenti_scope(
        (SELECT user_id FROM tmp_refs_scope)
    ),
    NULL::bigint[],
    '9) fn_get_emittenti_scope: senza whitelist → NULL'
);

-- ============================================================
-- 4. Aggiunta whitelist e verifica scope
-- ============================================================

-- 10) Aggiunta whitelist per emittente_1
SELECT lives_ok(
    format(
        $$INSERT INTO config.user_emittenti_fiscali
              (auth_user_id, emittente_fiscale_id, meta)
          VALUES (%s, %s,
                  '{"test_scope":"pgtap_fn_check_emittente_scope"}'::jsonb)$$,
        (SELECT user_id FROM tmp_refs_scope),
        (SELECT emittente_id_1 FROM tmp_emittenti)
    ),
    '10) Whitelist: aggiunta emittente_1 per utente test'
);

-- 11) Emittente_1 in whitelist → true
SELECT is(
    script.fn_check_user_emittente_scope(
        (SELECT user_id FROM tmp_refs_scope),
        (SELECT emittente_id_1 FROM tmp_emittenti)
    ),
    true,
    '11) fn_check_user_emittente_scope: emittente in whitelist → true'
);

-- 12) Emittente_2 NON in whitelist → false
SELECT is(
    script.fn_check_user_emittente_scope(
        (SELECT user_id FROM tmp_refs_scope),
        (SELECT emittente_id_2 FROM tmp_emittenti)
    ),
    false,
    '12) fn_check_user_emittente_scope: emittente NON in whitelist → false'
);

-- 13) fn_get_emittenti_scope: array contenente emittente_1
SELECT ok(
    (SELECT emittente_id_1 FROM tmp_emittenti) = ANY(
        script.fn_get_emittenti_scope(
            (SELECT user_id FROM tmp_refs_scope)
        )
    ),
    '13) fn_get_emittenti_scope: con whitelist → array contiene emittente_1'
);

SELECT * FROM finish();

ROLLBACK;
