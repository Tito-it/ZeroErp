-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test fn_crea_risorsa_umana (building block):
--   1. Precondizione: esiste qualifica attiva e UO attiva
--   2. Setup: crea soggetto PF di supporto
--   3. Creazione risorsa umana senza bridge (senza auth_user)
--   4. Verifica risorse_umane creato con ruolo RIS_UMANA
--   5. Creazione risorsa umana con bridge auth_user
--   6. Verifica bridge risorse_umane_auth_user
--   7. Errore: soggetto_id NULL
--   8. Errore: qualifica_id NULL
--   9. Errore: UO inesistente
-- ------------------------------------------------------------
BEGIN;
SELECT plan(9);

-- =========================================================
-- Setup
-- =========================================================
CREATE TEMP TABLE tmp_ru_ctx (
  qualifica_id    integer,
  uo_id           integer,
  soggetto_id_1   uuid,
  soggetto_id_2   uuid,
  auth_user_id    integer,
  ru_id_1         bigint,
  ru_id_2         bigint
);

-- =========================================================
-- 1) Precondizione: qualifica e UO attive
-- =========================================================
INSERT INTO tmp_ru_ctx (qualifica_id, uo_id)
SELECT q.id, uo.id
FROM config.qualifiche q
  CROSS JOIN config.unita_organizzative uo
WHERE q.attivo = true
  AND uo.attivo = true
LIMIT 1;

SELECT ok(
    (SELECT count(*) FROM tmp_ru_ctx WHERE qualifica_id IS NOT NULL AND uo_id IS NOT NULL) = 1,
    '1. Esiste almeno una qualifica attiva e una UO attiva'
  );

-- =========================================================
-- 2) Setup: crea 2 soggetti PF di supporto + 1 auth_user
-- =========================================================

-- Soggetto 1 (senza auth_user)
SELECT lives_ok(
    format(
      $$SELECT anagrafiche.fn_crea_soggetto_pf(
        p_cognome := 'TestRU',
        p_nome := 'SenzaBridge',
        p_codice_fiscale := %L,
        p_email := %L
      ) $$,
      'TSTRUSENZA' || lpad(floor(random() * 1000000)::text, 6, '0'),
      'test_ru_senza_' || floor(random() * 1000000)::text || '@test.local'
    ),
    '2. Soggetto PF 1 creato per test senza bridge'
  );

UPDATE tmp_ru_ctx
SET soggetto_id_1 = (
    SELECT id FROM anagrafiche.soggetti
    WHERE cognome = 'TESTRU' AND nome = 'SENZABRIDGE'
    ORDER BY data_insert DESC LIMIT 1
  );

-- Soggetto 2 (con auth_user)
SELECT lives_ok(
    format(
      $$SELECT anagrafiche.fn_crea_soggetto_pf(
        p_cognome := 'TestRU',
        p_nome := 'ConBridge',
        p_codice_fiscale := %L,
        p_email := %L
      ) $$,
      'TSTRUCONBR' || lpad(floor(random() * 1000000)::text, 6, '0'),
      'test_ru_con_' || floor(random() * 1000000)::text || '@test.local'
    ),
    '3. Soggetto PF 2 creato per test con bridge'
  );

UPDATE tmp_ru_ctx
SET soggetto_id_2 = (
    SELECT id FROM anagrafiche.soggetti
    WHERE cognome = 'TESTRU' AND nome = 'CONBRIDGE'
    ORDER BY data_insert DESC LIMIT 1
  );

-- Auth user per bridge
UPDATE tmp_ru_ctx
SET auth_user_id = (
    SELECT anagrafiche.fn_crea_auth_user(
      p_username := 'test_ru_bridge_' || floor(random() * 1000000)::text,
      p_email := 'test_ru_bridge_' || floor(random() * 1000000)::text || '@test.local',
      p_password_hash := 'pbkdf2_sha256$600000$test$hash=='
    )
  );

-- =========================================================
-- 4) Creazione risorsa umana SENZA bridge
-- =========================================================
SELECT lives_ok(
    format(
      $$SELECT anagrafiche.fn_crea_risorsa_umana(
        p_soggetto_id := %L::uuid,
        p_qualifica_id := %s,
        p_unita_organizzativa_id := %s
      ) $$,
      (SELECT soggetto_id_1 FROM tmp_ru_ctx),
      (SELECT qualifica_id FROM tmp_ru_ctx),
      (SELECT uo_id FROM tmp_ru_ctx)
    ),
    '4. fn_crea_risorsa_umana senza bridge eseguita'
  );

-- =========================================================
-- 5) Verifica risorse_umane con ruolo RIS_UMANA
-- =========================================================
SELECT ok(
    EXISTS (
      SELECT 1
      FROM anagrafiche.risorse_umane ru
        JOIN anagrafiche.soggetti_ruoli sr ON sr.id = ru.soggetto_ruolo_id
        JOIN config.tipi_ruoli tr ON tr.id = sr.tipo_ruolo_id
      WHERE ru.soggetto_id = (SELECT soggetto_id_1 FROM tmp_ru_ctx)
        AND tr.codice_interno = 'RIS_UMANA'
        AND ru.attivo = true
    ),
    '5. Risorsa umana creata con ruolo RIS_UMANA'
  );

-- =========================================================
-- 6) Creazione risorsa umana CON bridge auth_user
-- =========================================================
SELECT lives_ok(
    format(
      $$SELECT anagrafiche.fn_crea_risorsa_umana(
        p_soggetto_id := %L::uuid,
        p_qualifica_id := %s,
        p_unita_organizzativa_id := %s,
        p_auth_user_id := %s,
        p_ruolo_sistema := 'OPERATIVO'::config.ruolo_sistema
      ) $$,
      (SELECT soggetto_id_2 FROM tmp_ru_ctx),
      (SELECT qualifica_id FROM tmp_ru_ctx),
      (SELECT uo_id FROM tmp_ru_ctx),
      (SELECT auth_user_id FROM tmp_ru_ctx)
    ),
    '6. fn_crea_risorsa_umana con bridge eseguita'
  );

-- =========================================================
-- 7) Verifica bridge risorse_umane_auth_user
-- =========================================================
SELECT ok(
    EXISTS (
      SELECT 1
      FROM anagrafiche.risorse_umane_auth_user rua
        JOIN anagrafiche.risorse_umane ru ON ru.id = rua.risorsa_umana_id
      WHERE rua.auth_user_id = (SELECT auth_user_id FROM tmp_ru_ctx)
        AND ru.soggetto_id = (SELECT soggetto_id_2 FROM tmp_ru_ctx)
        AND rua.ruolo_sistema = 'OPERATIVO'::config.ruolo_sistema
        AND rua.attivo = true
    ),
    '7. Bridge risorse_umane_auth_user creato correttamente'
  );

-- =========================================================
-- 8) Errore: soggetto_id NULL
-- =========================================================
SELECT throws_matching(
    format(
      $$SELECT anagrafiche.fn_crea_risorsa_umana(
        p_soggetto_id := NULL,
        p_qualifica_id := %s
      ) $$,
      (SELECT qualifica_id FROM tmp_ru_ctx)
    ),
    'Soggetto obbligatorio',
    '8. Errore soggetto_id NULL'
  );

-- =========================================================
-- 9) Errore: UO inesistente
-- =========================================================
SELECT throws_matching(
    format(
      $$SELECT anagrafiche.fn_crea_risorsa_umana(
        p_soggetto_id := %L::uuid,
        p_qualifica_id := %s,
        p_unita_organizzativa_id := -999
      ) $$,
      (SELECT soggetto_id_1 FROM tmp_ru_ctx),
      (SELECT qualifica_id FROM tmp_ru_ctx)
    ),
    'E_ADMIN_UO_NON_TROVATA',
    '9. Errore UO inesistente'
  );

SELECT * FROM finish();
ROLLBACK;
