-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test fn_crea_auth_user (building block):
--   1. Creazione auth_user con successo
--   2. Verifica auth_user.email e campi fissi
--   3. Errore: username duplicato
--   4. Errore: email duplicata
--   5. Errore: username NULL
--   6. Errore: email vuota
--   7. Errore: password_hash NULL
-- ------------------------------------------------------------
BEGIN;
SELECT plan(7);

-- =========================================================
-- Setup
-- =========================================================
CREATE TEMP TABLE tmp_auth_ctx (
  auth_user_id   integer,
  test_username  text,
  test_email     text
);

INSERT INTO tmp_auth_ctx (test_username, test_email)
VALUES (
  'test_bb_au_' || floor(random() * 1000000)::text,
  'test_bb_au_' || floor(random() * 1000000)::text || '@test.local'
);

-- =========================================================
-- 1) Creazione con successo
-- =========================================================
SELECT lives_ok(
    format(
      $$SELECT anagrafiche.fn_crea_auth_user(
        p_username := %L,
        p_email := %L,
        p_password_hash := 'pbkdf2_sha256$600000$test$hash_placeholder==',
        p_first_name := 'Mario',
        p_last_name := 'Rossi'
      ) $$,
      (SELECT test_username FROM tmp_auth_ctx),
      (SELECT test_email FROM tmp_auth_ctx)
    ),
    '1. fn_crea_auth_user eseguita senza errori'
  );

-- Salva auth_user_id
UPDATE tmp_auth_ctx
SET auth_user_id = (
    SELECT id FROM django.auth_user
    WHERE username = (SELECT test_username FROM tmp_auth_ctx)
  );

-- =========================================================
-- 2) Verifica campi creati
-- =========================================================
SELECT ok(
    EXISTS (
      SELECT 1 FROM django.auth_user
      WHERE id = (SELECT auth_user_id FROM tmp_auth_ctx)
        AND email = (SELECT test_email FROM tmp_auth_ctx)
        AND first_name = 'Mario'
        AND last_name = 'Rossi'
        AND is_active = true
        AND is_staff = false
        AND is_superuser = false
    ),
    '2. auth_user creato con campi corretti'
  );

-- =========================================================
-- 3) Errore: username duplicato
-- =========================================================
SELECT throws_matching(
    format(
      $$SELECT anagrafiche.fn_crea_auth_user(
        p_username := %L,
        p_email := 'altro_' || %L,
        p_password_hash := 'hash'
      ) $$,
      (SELECT test_username FROM tmp_auth_ctx),
      (SELECT test_email FROM tmp_auth_ctx)
    ),
    'E_ADMIN_USERNAME_DUPLICATO',
    '3. Errore username duplicato'
  );

-- =========================================================
-- 4) Errore: email duplicata
-- =========================================================
SELECT throws_matching(
    format(
      $$SELECT anagrafiche.fn_crea_auth_user(
        p_username := 'altro_' || %L,
        p_email := %L,
        p_password_hash := 'hash'
      ) $$,
      (SELECT test_username FROM tmp_auth_ctx),
      (SELECT test_email FROM tmp_auth_ctx)
    ),
    'E_ADMIN_EMAIL_DUPLICATA',
    '4. Errore email duplicata'
  );

-- =========================================================
-- 5) Errore: username NULL
-- =========================================================
SELECT throws_matching(
    $$SELECT anagrafiche.fn_crea_auth_user(
      p_username := NULL,
      p_email := 'test_null@test.local',
      p_password_hash := 'hash'
    ) $$,
    'Username obbligatorio',
    '5. Errore username NULL'
  );

-- =========================================================
-- 6) Errore: email vuota
-- =========================================================
SELECT throws_matching(
    $$SELECT anagrafiche.fn_crea_auth_user(
      p_username := 'test_email_vuota',
      p_email := '',
      p_password_hash := 'hash'
    ) $$,
    'Email obbligatoria',
    '6. Errore email vuota'
  );

-- =========================================================
-- 7) Errore: password_hash NULL
-- =========================================================
SELECT throws_matching(
    $$SELECT anagrafiche.fn_crea_auth_user(
      p_username := 'test_pwd_null',
      p_email := 'test_pwd_null@test.local',
      p_password_hash := NULL
    ) $$,
    'Password hash obbligatorio',
    '7. Errore password_hash NULL'
  );

SELECT * FROM finish();
ROLLBACK;
