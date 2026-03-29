-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: script.fn_check_operatore_invitabile
--       Verifica le 7 condizioni di invitabilita' di un operatore.
--
-- Elenco test:
--  1) auth_user_id NULL → invitabile=false
--  2) auth_user_id <= 0 → invitabile=false
--  3) auth_user_id inesistente → invitabile=false, motivo 'Utente non trovato'
--  4) auth_user is_active=false → invitabile=false
--  5) risorse_umane_auth_user.attivo=false → invitabile=false
--  6) ruolo_sistema DISABILITATO → invitabile=false
--  7) auth_user senza email → invitabile=false
--  8) auth_user con last_login NOT NULL → invitabile=false
--  9) Operatore valido (tutte condizioni OK) → invitabile=true con email
-- ------------------------------------------------------------

BEGIN;

SELECT plan(9);

-- ============================================================
-- 0. Setup: recupero un operatore esistente per i test
-- ============================================================

CREATE TEMP TABLE tmp_invito_ctx AS
SELECT
    rau.auth_user_id AS user_id,
    rau.id           AS rau_id,
    au.email         AS original_email,
    au.is_active     AS original_active,
    au.last_login    AS original_last_login,
    rau.ruolo_sistema AS original_ruolo,
    rau.attivo       AS original_rau_attivo
FROM anagrafiche.risorse_umane_auth_user rau
JOIN django.auth_user au ON au.id = rau.auth_user_id
WHERE rau.attivo = true
  AND rau.ruolo_sistema <> 'DISABILITATO'
ORDER BY rau.id
LIMIT 1;

-- Preparo l'operatore come invitabile:
-- email presente, is_active=true, last_login=NULL, ruolo OPERATIVO, rau.attivo=true
UPDATE django.auth_user
   SET email = 'test.invito@pgtap.local',
       is_active = true,
       last_login = NULL
 WHERE id = (SELECT user_id FROM tmp_invito_ctx);

UPDATE anagrafiche.risorse_umane_auth_user
   SET ruolo_sistema = 'OPERATIVO',
       attivo = true
 WHERE auth_user_id = (SELECT user_id FROM tmp_invito_ctx);

-- ============================================================
-- 1) auth_user_id NULL → invitabile=false
-- ============================================================
SELECT is(
    (script.fn_check_operatore_invitabile(NULL))->>'invitabile',
    'false',
    'fn_check_operatore_invitabile(NULL) → invitabile=false'
);

-- ============================================================
-- 2) auth_user_id <= 0 → invitabile=false
-- ============================================================
SELECT is(
    (script.fn_check_operatore_invitabile(-1))->>'invitabile',
    'false',
    'fn_check_operatore_invitabile(-1) → invitabile=false'
);

-- ============================================================
-- 3) auth_user_id inesistente → invitabile=false
-- ============================================================
SELECT is(
    (script.fn_check_operatore_invitabile(99999999))->>'motivo',
    'Utente non trovato',
    'fn_check_operatore_invitabile(99999999) → Utente non trovato'
);

-- ============================================================
-- 4) is_active=false → invitabile=false
-- ============================================================
UPDATE django.auth_user
   SET is_active = false
 WHERE id = (SELECT user_id FROM tmp_invito_ctx);

SELECT ok(
    (script.fn_check_operatore_invitabile(
        (SELECT user_id FROM tmp_invito_ctx)
    ))->>'motivo' LIKE '%is_active%',
    'is_active=false → invitabile=false con motivo is_active'
);

UPDATE django.auth_user
   SET is_active = true
 WHERE id = (SELECT user_id FROM tmp_invito_ctx);

-- ============================================================
-- 5) rau.attivo=false → invitabile=false
-- ============================================================
UPDATE anagrafiche.risorse_umane_auth_user
   SET attivo = false
 WHERE auth_user_id = (SELECT user_id FROM tmp_invito_ctx);

SELECT ok(
    (script.fn_check_operatore_invitabile(
        (SELECT user_id FROM tmp_invito_ctx)
    ))->>'motivo' LIKE '%non attivo%',
    'rau.attivo=false → invitabile=false'
);

UPDATE anagrafiche.risorse_umane_auth_user
   SET attivo = true
 WHERE auth_user_id = (SELECT user_id FROM tmp_invito_ctx);

-- ============================================================
-- 6) ruolo_sistema DISABILITATO → invitabile=false
-- ============================================================
UPDATE anagrafiche.risorse_umane_auth_user
   SET ruolo_sistema = 'DISABILITATO'
 WHERE auth_user_id = (SELECT user_id FROM tmp_invito_ctx);

SELECT ok(
    (script.fn_check_operatore_invitabile(
        (SELECT user_id FROM tmp_invito_ctx)
    ))->>'motivo' LIKE '%DISABILITATO%',
    'ruolo_sistema=DISABILITATO → invitabile=false'
);

UPDATE anagrafiche.risorse_umane_auth_user
   SET ruolo_sistema = 'OPERATIVO'
 WHERE auth_user_id = (SELECT user_id FROM tmp_invito_ctx);

-- ============================================================
-- 7) Senza email → invitabile=false
-- ============================================================
UPDATE django.auth_user
   SET email = ''
 WHERE id = (SELECT user_id FROM tmp_invito_ctx);

SELECT ok(
    (script.fn_check_operatore_invitabile(
        (SELECT user_id FROM tmp_invito_ctx)
    ))->>'motivo' LIKE '%email%',
    'email vuota → invitabile=false'
);

UPDATE django.auth_user
   SET email = 'test.invito@pgtap.local'
 WHERE id = (SELECT user_id FROM tmp_invito_ctx);

-- ============================================================
-- 8) last_login NOT NULL → invitabile=false
-- ============================================================
UPDATE django.auth_user
   SET last_login = now()
 WHERE id = (SELECT user_id FROM tmp_invito_ctx);

SELECT ok(
    (script.fn_check_operatore_invitabile(
        (SELECT user_id FROM tmp_invito_ctx)
    ))->>'motivo' LIKE '%login%',
    'last_login NOT NULL → invitabile=false (gia'' loggato)'
);

UPDATE django.auth_user
   SET last_login = NULL
 WHERE id = (SELECT user_id FROM tmp_invito_ctx);

-- ============================================================
-- 9) Tutte le condizioni OK → invitabile=true con email
-- ============================================================
SELECT ok(
    (script.fn_check_operatore_invitabile(
        (SELECT user_id FROM tmp_invito_ctx)
    ))->>'invitabile' = 'true'
    AND
    (script.fn_check_operatore_invitabile(
        (SELECT user_id FROM tmp_invito_ctx)
    ))->>'email' = 'test.invito@pgtap.local',
    'Tutte condizioni OK → invitabile=true, email corretta'
);

SELECT * FROM finish();
ROLLBACK;
