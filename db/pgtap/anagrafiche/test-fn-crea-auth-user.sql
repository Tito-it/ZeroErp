-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
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
-- ⚠️ TEST 3 e 4 — perche' NON si asserisce sul codice errore
--
-- Fino al 2026-08-04 questi due test facevano
--     throws_matching(..., 'E_ADMIN_USERNAME_DUPLICATO')
-- e passavano. Passavano **per il motivo sbagliato**: il codice non
-- compare mai nel messaggio sollevato. `script.fn_log_and_raise_error`
-- fa `RAISE EXCEPTION '%', v_msg USING DETAIL/HINT` — senza ERRCODE — e
-- `v_msg` e' il testo localizzato preso da `config.messaggi_errore`.
-- Il codice finiva nel messaggio **solo** quando la riga mancava dal
-- seed, perche' allora `script.fn_get_messaggio` ritorna il segnaposto
-- '[MESSAGGIO NON DEFINITO: <codice>]'.
--
-- Il 2026-08-04 il loader dei messaggi ha ripescato il CSV, la riga e'
-- comparsa, e i due test sono diventati rossi. Erano verdi perche'
-- mancava un dato: un test che verde-ggia per l'assenza di qualcosa non
-- misura quello che dice di misurare.
--
-- Si asserisce quindi sul messaggio, ma **espresso tramite il codice**:
-- si chiede a `fn_get_messaggio` lo stesso testo che il raiser
-- sollevera'. Il test resta leggibile in termini di dominio, non si
-- rompe se cambia la traduzione, e regge anche se la riga sparisse di
-- nuovo dal seed (in quel caso entrambi i lati diventano il segnaposto).
-- Si asserisce anche lo SQLSTATE: e' P0001 per ogni RAISE senza ERRCODE.
--
-- 🔴 Il vero problema non e' questo test: e' che il codice di dominio
-- **non e' recuperabile dall'eccezione** — non e' in ERRCODE, non e' in
-- DETAIL (= `causa`), non e' in HINT (= `soluzione`). Zero dei 635
-- messaggi 'it' contiene il proprio codice. Il backend lo cerca con una
-- regex nel testo (`ErrorTranslator._extract_app_error_code`), quindi
-- non lo trova mai per un errore correttamente seedato.
-- Vedi brief-be-bonifica-riferimenti-morti.md §6.
-- =========================================================

-- =========================================================
-- 3) Errore: username duplicato
-- =========================================================
SELECT throws_ok(
    format(
      $$SELECT anagrafiche.fn_crea_auth_user(
        p_username := %L,
        p_email := 'altro_' || %L,
        p_password_hash := 'hash'
      ) $$,
      (SELECT test_username FROM tmp_auth_ctx),
      (SELECT test_email FROM tmp_auth_ctx)
    ),
    'P0001',
    script.fn_get_messaggio('E_ADMIN_USERNAME_DUPLICATO'),
    '3. Errore username duplicato (E_ADMIN_USERNAME_DUPLICATO)'
  );

-- =========================================================
-- 4) Errore: email duplicata
-- =========================================================
SELECT throws_ok(
    format(
      $$SELECT anagrafiche.fn_crea_auth_user(
        p_username := 'altro_' || %L,
        p_email := %L,
        p_password_hash := 'hash'
      ) $$,
      (SELECT test_username FROM tmp_auth_ctx),
      (SELECT test_email FROM tmp_auth_ctx)
    ),
    'P0001',
    script.fn_get_messaggio('E_ADMIN_EMAIL_DUPLICATA'),
    '4. Errore email duplicata (E_ADMIN_EMAIL_DUPLICATA)'
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
