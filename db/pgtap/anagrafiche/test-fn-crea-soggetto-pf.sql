-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test fn_crea_soggetto_pf (building block):
--   1. Creazione soggetto PF con successo
--   2. Verifica tipo_soggetto_dettaglio_id = PR
--   3. Verifica ragione_sociale_completa normalizzata
--   4. Verifica contatto default creato
--   5. Errore: codice fiscale duplicato
--   6. Errore: cognome vuoto
--   7. Errore: email NULL
-- ------------------------------------------------------------
BEGIN;
SELECT plan(7);

-- =========================================================
-- Setup
-- =========================================================
CREATE TEMP TABLE tmp_sogg_pf_ctx (
  soggetto_id  uuid,
  test_cf      text,
  test_email   text
);

INSERT INTO tmp_sogg_pf_ctx (test_cf, test_email)
VALUES (
  'TSTSOGGPF' || lpad(floor(random() * 1000000)::text, 7, '0'),
  'test_sogg_pf_' || floor(random() * 1000000)::text || '@test.local'
);

-- =========================================================
-- 1) Creazione soggetto PF con successo
-- =========================================================
SELECT lives_ok(
    format(
      $$SELECT anagrafiche.fn_crea_soggetto_pf(
        p_cognome := 'Verdi',
        p_nome := 'Luigi',
        p_codice_fiscale := %L,
        p_email := %L,
        p_data_nascita := '1985-06-20',
        p_sesso := 'M'
      ) $$,
      (SELECT test_cf FROM tmp_sogg_pf_ctx),
      (SELECT test_email FROM tmp_sogg_pf_ctx)
    ),
    '1. fn_crea_soggetto_pf eseguita senza errori'
  );

-- Salva soggetto_id
UPDATE tmp_sogg_pf_ctx
SET soggetto_id = (
    SELECT id FROM anagrafiche.soggetti
    WHERE id_fiscale_univoco_cf_piva = UPPER((SELECT test_cf FROM tmp_sogg_pf_ctx))
  );

-- =========================================================
-- 2) Verifica tipo_soggetto_dettaglio_id = PR
-- =========================================================
SELECT ok(
    EXISTS (
      SELECT 1 FROM anagrafiche.soggetti s
        JOIN config.tipi_soggetto_dettaglio tsd ON tsd.id = s.tipo_soggetto_dettaglio_id
      WHERE s.id = (SELECT soggetto_id FROM tmp_sogg_pf_ctx)
        AND tsd.codice_interno = 'PR'
    ),
    '2. Soggetto ha tipo_soggetto_dettaglio = PR'
  );

-- =========================================================
-- 3) Verifica ragione_sociale_completa normalizzata
-- =========================================================
SELECT ok(
    (SELECT ragione_sociale_completa FROM anagrafiche.soggetti
     WHERE id = (SELECT soggetto_id FROM tmp_sogg_pf_ctx)
    ) IS NOT NULL,
    '3. ragione_sociale_completa calcolata dal trigger'
  );

-- =========================================================
-- 4) Verifica contatto default creato
-- =========================================================
SELECT ok(
    EXISTS (
      SELECT 1 FROM anagrafiche.contatti
      WHERE soggetto_id = (SELECT soggetto_id FROM tmp_sogg_pf_ctx)
        AND is_default = true
        AND email = (SELECT test_email FROM tmp_sogg_pf_ctx)
    ),
    '4. Contatto default creato con email corretta'
  );

-- =========================================================
-- 5) Errore: codice fiscale duplicato
-- =========================================================
SELECT throws_matching(
    format(
      $$SELECT anagrafiche.fn_crea_soggetto_pf(
        p_cognome := 'Bianchi',
        p_nome := 'Anna',
        p_codice_fiscale := %L,
        p_email := 'altro_' || %L
      ) $$,
      (SELECT test_cf FROM tmp_sogg_pf_ctx),
      (SELECT test_email FROM tmp_sogg_pf_ctx)
    ),
    'E_ADMIN_CF_DUPLICATO',
    '5. Errore codice fiscale duplicato'
  );

-- =========================================================
-- 6) Errore: cognome vuoto
-- =========================================================
SELECT throws_matching(
    $$SELECT anagrafiche.fn_crea_soggetto_pf(
      p_cognome := '',
      p_nome := 'Test',
      p_codice_fiscale := 'TSTCOGNVUOTO00000',
      p_email := 'cognome_vuoto@test.local'
    ) $$,
    'Cognome obbligatorio',
    '6. Errore cognome vuoto'
  );

-- =========================================================
-- 7) Errore: email NULL
-- =========================================================
SELECT throws_matching(
    $$SELECT anagrafiche.fn_crea_soggetto_pf(
      p_cognome := 'Test',
      p_nome := 'EmailNull',
      p_codice_fiscale := 'TSTEMAILNULL00000',
      p_email := NULL
    ) $$,
    'Email obbligatoria',
    '7. Errore email NULL'
  );

SELECT * FROM finish();
ROLLBACK;
