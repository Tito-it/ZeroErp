-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test fn_crea_operatore (orchestratore) e building block:
--   1. Precondizione: esiste UO attiva e qualifica attiva
--   2. Creazione operatore con successo
--   3. Verifica auth_user creato
--   4. Verifica catena soggetto -> ruolo -> risorsa_umana -> bridge
--   5. Verifica soggetto ha tipo_soggetto_dettaglio_id (PR)
--   6. Verifica contatto default creato
--   7. Errore: username duplicato
--   8. Errore: email duplicata
--   9. Errore: codice fiscale duplicato
--  10. Errore: UO inesistente
--  11. Errore: cognome vuoto
--  12. Errore: qualifica mancante
--  13. Cleanup
-- ------------------------------------------------------------
BEGIN;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(12);

-- =========================================================
-- Setup: variabili temporanee
-- =========================================================
CREATE TEMP TABLE tmp_crea_op_ctx (
  uo_id          integer,
  qualifica_id   integer,
  auth_user_id   integer,
  test_username  text,
  test_email     text,
  test_cf        text
);

-- =========================================================
-- 1) Precondizione: esiste almeno una UO attiva e qualifica attiva
-- =========================================================
INSERT INTO tmp_crea_op_ctx (uo_id, qualifica_id, test_username, test_email, test_cf)
SELECT
  uo.id,
  q.id,
  'test_op_' || floor(random() * 1000000)::text,
  'test_op_' || floor(random() * 1000000)::text || '@test.local',
  'LCCRLD80A01L736X'
FROM config.unita_organizzative uo
  CROSS JOIN config.qualifiche q
WHERE uo.attivo = true
  AND q.attivo = true
LIMIT 1;

SELECT ok(
    (SELECT count(*) FROM tmp_crea_op_ctx WHERE uo_id IS NOT NULL AND qualifica_id IS NOT NULL) = 1,
    '1. Esiste almeno una UO attiva e una qualifica attiva per il test'
  );

-- =========================================================
-- 2) Creazione operatore con successo
-- =========================================================
SELECT lives_ok(
    format(
      $$SELECT anagrafiche.fn_crea_operatore(
        p_cognome := 'Rossi',
        p_nome := 'Mario',
        p_codice_fiscale := %L,
        p_data_nascita := '1990-01-15',
        p_sesso := 'M',
        p_username := %L,
        p_email := %L,
        p_password_hash := 'pbkdf2_sha256$600000$test$hash_placeholder==',
        p_qualifica_id := %s,
        p_ruolo_sistema := 'OPERATIVO'::config.ruolo_sistema,
        p_unita_organizzativa_id := %s
      ) $$,
      (SELECT test_cf FROM tmp_crea_op_ctx),
      (SELECT test_username FROM tmp_crea_op_ctx),
      (SELECT test_email FROM tmp_crea_op_ctx),
      (SELECT qualifica_id FROM tmp_crea_op_ctx),
      (SELECT uo_id FROM tmp_crea_op_ctx)
    ),
    '2. fn_crea_operatore eseguita senza errori'
  );

-- Salva auth_user_id per verifiche successive
UPDATE tmp_crea_op_ctx
SET auth_user_id = (
    SELECT id FROM django.auth_user
    WHERE username = (SELECT test_username FROM tmp_crea_op_ctx)
  );

-- =========================================================
-- 3) Verifica auth_user creato
-- =========================================================
SELECT ok(
    (SELECT auth_user_id FROM tmp_crea_op_ctx) IS NOT NULL,
    '3. auth_user creato con username corretto'
  );

SELECT is(
    (SELECT email::text FROM django.auth_user
     WHERE id = (SELECT auth_user_id FROM tmp_crea_op_ctx)),
    (SELECT test_email FROM tmp_crea_op_ctx),
    '4. auth_user.email corretta'
  );

-- =========================================================
-- 4) Verifica catena: soggetto + ruolo + risorsa umana + bridge
-- =========================================================
SELECT ok(
    EXISTS (
      SELECT 1
      FROM anagrafiche.risorse_umane_auth_user rua
        JOIN anagrafiche.risorse_umane ru ON ru.id = rua.risorsa_umana_id
        JOIN anagrafiche.soggetti_ruoli sr ON sr.id = ru.soggetto_ruolo_id
        JOIN anagrafiche.soggetti s ON s.id = sr.soggetto_id
      WHERE rua.auth_user_id = (SELECT auth_user_id FROM tmp_crea_op_ctx)
        AND s.cognome = 'Rossi'
        AND s.nome = 'Mario'
        AND rua.ruolo_sistema = 'OPERATIVO'::config.ruolo_sistema
    ),
    '5. Catena soggetto -> ruolo -> risorsa_umana -> bridge verificata'
  );

-- =========================================================
-- 5) Verifica tipo_soggetto_dettaglio_id impostato (PR)
-- =========================================================
SELECT ok(
    EXISTS (
      SELECT 1
      FROM anagrafiche.soggetti s
        JOIN anagrafiche.soggetti_ruoli sr ON sr.soggetto_id = s.id
        JOIN anagrafiche.risorse_umane ru ON ru.soggetto_ruolo_id = sr.id
        JOIN anagrafiche.risorse_umane_auth_user rua ON rua.risorsa_umana_id = ru.id
        JOIN config.tipi_soggetto_dettaglio tsd ON tsd.id = s.tipo_soggetto_dettaglio_id
      WHERE rua.auth_user_id = (SELECT auth_user_id FROM tmp_crea_op_ctx)
        AND tsd.codice_interno = 'PR'
    ),
    '6. Soggetto ha tipo_soggetto_dettaglio_id = PR (Privato PF)'
  );

-- =========================================================
-- 6) Verifica contatto default creato
-- =========================================================
SELECT ok(
    EXISTS (
      SELECT 1
      FROM anagrafiche.contatti c
        JOIN anagrafiche.soggetti s ON s.id = c.soggetto_id
        JOIN anagrafiche.soggetti_ruoli sr ON sr.soggetto_id = s.id
        JOIN anagrafiche.risorse_umane ru ON ru.soggetto_ruolo_id = sr.id
        JOIN anagrafiche.risorse_umane_auth_user rua ON rua.risorsa_umana_id = ru.id
      WHERE rua.auth_user_id = (SELECT auth_user_id FROM tmp_crea_op_ctx)
        AND c.is_default = true
        AND c.email = (SELECT test_email FROM tmp_crea_op_ctx)
    ),
    '7. Contatto default creato con email corretta'
  );

-- =========================================================
-- 7) Errore: username duplicato
-- =========================================================
SELECT throws_matching(
    format(
      $$SELECT anagrafiche.fn_crea_operatore(
        p_cognome := 'Bianchi',
        p_nome := 'Luca',
        p_codice_fiscale := 'TSTDUP' || lpad(floor(random() * 10000000)::text, 10, '0'),
        p_username := %L,
        p_email := 'altro_' || %L,
        p_password_hash := 'pbkdf2_sha256$600000$test$hash==',
        p_qualifica_id := %s,
        p_unita_organizzativa_id := %s
      ) $$,
      (SELECT test_username FROM tmp_crea_op_ctx),
      (SELECT test_email FROM tmp_crea_op_ctx),
      (SELECT qualifica_id FROM tmp_crea_op_ctx),
      (SELECT uo_id FROM tmp_crea_op_ctx)
    ),
    'E_ADMIN_USERNAME_DUPLICATO',
    '8. Errore username duplicato'
  );

-- =========================================================
-- 8) Errore: email duplicata
-- =========================================================
SELECT throws_matching(
    format(
      $$SELECT anagrafiche.fn_crea_operatore(
        p_cognome := 'Verdi',
        p_nome := 'Anna',
        p_codice_fiscale := 'TSTDUP' || lpad(floor(random() * 10000000)::text, 10, '0'),
        p_username := 'altro_user_unico_' || floor(random() * 1000000)::text,
        p_email := %L,
        p_password_hash := 'pbkdf2_sha256$600000$test$hash==',
        p_qualifica_id := %s,
        p_unita_organizzativa_id := %s
      ) $$,
      (SELECT test_email FROM tmp_crea_op_ctx),
      (SELECT qualifica_id FROM tmp_crea_op_ctx),
      (SELECT uo_id FROM tmp_crea_op_ctx)
    ),
    'E_ADMIN_EMAIL_DUPLICATA',
    '9. Errore email duplicata'
  );

-- =========================================================
-- 9) Errore: codice fiscale duplicato
-- =========================================================
SELECT throws_matching(
    format(
      $$SELECT anagrafiche.fn_crea_operatore(
        p_cognome := 'Neri',
        p_nome := 'Paolo',
        p_codice_fiscale := %L,
        p_username := 'user_cf_dup_' || floor(random() * 1000000)::text,
        p_email := 'cf_dup_' || floor(random() * 1000000)::text || '@test.local',
        p_password_hash := 'pbkdf2_sha256$600000$test$hash==',
        p_qualifica_id := %s,
        p_unita_organizzativa_id := %s
      ) $$,
      (SELECT test_cf FROM tmp_crea_op_ctx),
      (SELECT qualifica_id FROM tmp_crea_op_ctx),
      (SELECT uo_id FROM tmp_crea_op_ctx)
    ),
    'Codice fiscale gia',
    '10. Errore codice fiscale duplicato'
  );

-- =========================================================
-- 10) Errore: UO inesistente
-- =========================================================
SELECT throws_matching(
    format(
      $$SELECT anagrafiche.fn_crea_operatore(
        p_cognome := 'Test',
        p_nome := 'UO',
        p_codice_fiscale := 'PNZFDN78A01L219Y',
        p_username := 'user_uo_ines_' || floor(random() * 1000000)::text,
        p_email := 'uo_ines_' || floor(random() * 1000000)::text || '@test.local',
        p_password_hash := 'pbkdf2_sha256$600000$test$hash==',
        p_qualifica_id := %s,
        p_unita_organizzativa_id := -999
      ) $$,
      (SELECT qualifica_id FROM tmp_crea_op_ctx)
    ),
    'non trovata o non attiva',
    '11. Errore UO inesistente'
  );

-- =========================================================
-- 11) Errore: cognome vuoto
-- =========================================================
SELECT throws_matching(
    format(
      $$SELECT anagrafiche.fn_crea_operatore(
        p_cognome := '',
        p_nome := 'Test',
        p_username := 'user_cognome_vuoto',
        p_email := 'cognome_vuoto@test.local',
        p_password_hash := 'pbkdf2_sha256$600000$test$hash==',
        p_qualifica_id := %s,
        p_unita_organizzativa_id := %s
      ) $$,
      (SELECT qualifica_id FROM tmp_crea_op_ctx),
      (SELECT uo_id FROM tmp_crea_op_ctx)
    ),
    'Cognome obbligatorio',
    '12. Errore cognome vuoto'
  );

SELECT * FROM finish();
ROLLBACK;
