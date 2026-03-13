-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test fn_crea_indirizzo_soggetto (building block):
--   1. Precondizioni: stradario e tipo indirizzo RESID esistono
--   2. Setup: crea soggetto PF di supporto + indirizzo_dettaglio
--   3. Creazione indirizzo normalizzato (RESID) con successo
--   4. Verifica record creato in indirizzi_soggetti
--   5. Errore: duplicato (stesso soggetto + stesso tipo)
--   6. Creazione secondo tipo (DOMFISC) con successo
--   7. Errore: XOR violation (entrambi specificati)
--   8. Errore: nessun indirizzo (ne' dettaglio ne' libero)
--   9. Errore: p_soggetto_id NULL
--  10. Errore: p_tipo_indirizzo_codice vuoto
--  11. Errore: tipo indirizzo inesistente
-- ------------------------------------------------------------
BEGIN;
SELECT plan(11);

-- =========================================================
-- Setup
-- =========================================================
CREATE TEMP TABLE tmp_ind_sogg_ctx (
    stradario_id          integer,
    indirizzo_dettaglio_id bigint,
    soggetto_id           uuid,
    indirizzo_soggetto_id bigint
);

-- Trova uno stradario attivo
INSERT INTO tmp_ind_sogg_ctx (stradario_id)
SELECT id FROM config.stradario ORDER BY id LIMIT 1;

-- =========================================================
-- 1) Precondizioni: stradario e tipo indirizzo RESID esistono
-- =========================================================
SELECT ok(
    (SELECT stradario_id FROM tmp_ind_sogg_ctx) IS NOT NULL
    AND EXISTS (SELECT 1 FROM config.tipi_indirizzi WHERE codice_interno = 'RES'),
    '1. Stradario e tipo indirizzo RESID esistono'
  );

-- =========================================================
-- 2) Setup: crea soggetto PF e indirizzo_dettaglio
-- =========================================================

-- Crea indirizzo_dettaglio via building block
UPDATE tmp_ind_sogg_ctx
SET indirizzo_dettaglio_id = (
    SELECT anagrafiche.fn_get_or_create_indirizzo_dettaglio(
        p_stradario_id := (SELECT stradario_id FROM tmp_ind_sogg_ctx),
        p_civico := 88880
    )
  );

-- Crea soggetto PF di supporto
SELECT lives_ok(
    format(
      $$SELECT anagrafiche.fn_crea_soggetto_pf(
        p_cognome := 'TestIndSogg',
        p_nome := 'Primo',
        p_codice_fiscale := %L,
        p_email := %L
      ) $$,
      'PNZFDN78A01L219Y',
      'test_ind_sogg_' || floor(random() * 1000000)::text || '@test.local'
    ),
    '2. Soggetto PF di supporto creato'
  );

UPDATE tmp_ind_sogg_ctx
SET soggetto_id = (
    SELECT id FROM anagrafiche.soggetti
    WHERE cognome = 'TestIndSogg' AND nome = 'Primo'
    ORDER BY data_insert DESC LIMIT 1
  );

-- =========================================================
-- 3) Creazione indirizzo normalizzato (RESID) con successo
-- =========================================================
SELECT lives_ok(
    format(
      $$SELECT anagrafiche.fn_crea_indirizzo_soggetto(
        p_soggetto_id            := %L::uuid,
        p_tipo_indirizzo_codice  := 'RES',
        p_indirizzo_dettaglio_id := %s
      ) $$,
      (SELECT soggetto_id FROM tmp_ind_sogg_ctx),
      (SELECT indirizzo_dettaglio_id FROM tmp_ind_sogg_ctx)
    ),
    '3. Creazione indirizzo RESID normalizzato senza errori'
  );

-- Salva id creato
UPDATE tmp_ind_sogg_ctx
SET indirizzo_soggetto_id = (
    SELECT id FROM anagrafiche.indirizzi_soggetti
    WHERE soggetto_id = (SELECT soggetto_id FROM tmp_ind_sogg_ctx)
      AND tipo_indirizzo_id = (SELECT id FROM config.tipi_indirizzi WHERE codice_interno = 'RES')
  );

-- =========================================================
-- 4) Verifica record creato in indirizzi_soggetti
-- =========================================================
SELECT ok(
    EXISTS (
      SELECT 1 FROM anagrafiche.indirizzi_soggetti
      WHERE id = (SELECT indirizzo_soggetto_id FROM tmp_ind_sogg_ctx)
        AND soggetto_id = (SELECT soggetto_id FROM tmp_ind_sogg_ctx)
        AND indirizzo_dettaglio_id = (SELECT indirizzo_dettaglio_id FROM tmp_ind_sogg_ctx)
        AND indirizzo_libero IS NULL
    ),
    '4. Record indirizzi_soggetti creato correttamente'
  );

-- =========================================================
-- 5) Errore: duplicato (stesso soggetto + stesso tipo RESID)
-- =========================================================
SELECT throws_matching(
    format(
      $$SELECT anagrafiche.fn_crea_indirizzo_soggetto(
        p_soggetto_id            := %L::uuid,
        p_tipo_indirizzo_codice  := 'RES',
        p_indirizzo_dettaglio_id := %s
      ) $$,
      (SELECT soggetto_id FROM tmp_ind_sogg_ctx),
      (SELECT indirizzo_dettaglio_id FROM tmp_ind_sogg_ctx)
    ),
    'uq_indirizzi_soggetti_soggetto_tipo',
    '5. Errore duplicato soggetto + tipo indirizzo'
  );

-- =========================================================
-- 6) Creazione secondo tipo (DOMFISC) con successo
-- =========================================================
SELECT lives_ok(
    format(
      $$SELECT anagrafiche.fn_crea_indirizzo_soggetto(
        p_soggetto_id            := %L::uuid,
        p_tipo_indirizzo_codice  := 'DOMFISC',
        p_indirizzo_dettaglio_id := %s
      ) $$,
      (SELECT soggetto_id FROM tmp_ind_sogg_ctx),
      (SELECT indirizzo_dettaglio_id FROM tmp_ind_sogg_ctx)
    ),
    '6. Creazione indirizzo DOMFISC senza errori'
  );

-- =========================================================
-- 7) Errore: XOR violation (entrambi specificati)
-- =========================================================
SELECT throws_matching(
    format(
      $$SELECT anagrafiche.fn_crea_indirizzo_soggetto(
        p_soggetto_id            := %L::uuid,
        p_tipo_indirizzo_codice  := 'SEDEOP',
        p_indirizzo_dettaglio_id := %s,
        p_indirizzo_libero       := 'Via Test 1'
      ) $$,
      (SELECT soggetto_id FROM tmp_ind_sogg_ctx),
      (SELECT indirizzo_dettaglio_id FROM tmp_ind_sogg_ctx)
    ),
    'non entrambi',
    '7. Errore XOR: dettaglio e libero specificati insieme'
  );

-- =========================================================
-- 8) Errore: nessun indirizzo (ne' dettaglio ne' libero)
-- =========================================================
SELECT throws_matching(
    format(
      $$SELECT anagrafiche.fn_crea_indirizzo_soggetto(
        p_soggetto_id            := %L::uuid,
        p_tipo_indirizzo_codice  := 'SEDEOP'
      ) $$,
      (SELECT soggetto_id FROM tmp_ind_sogg_ctx)
    ),
    'almeno',
    '8. Errore nessun indirizzo specificato'
  );

-- =========================================================
-- 9) Errore: p_soggetto_id NULL
-- =========================================================
SELECT throws_matching(
    $$SELECT anagrafiche.fn_crea_indirizzo_soggetto(
      p_soggetto_id            := NULL,
      p_tipo_indirizzo_codice  := 'RES',
      p_indirizzo_dettaglio_id := 1
    ) $$,
    'p_soggetto_id obbligatorio',
    '9. Errore p_soggetto_id NULL'
  );

-- =========================================================
-- 10) Errore: p_tipo_indirizzo_codice vuoto
-- =========================================================
SELECT throws_matching(
    format(
      $$SELECT anagrafiche.fn_crea_indirizzo_soggetto(
        p_soggetto_id            := %L::uuid,
        p_tipo_indirizzo_codice  := '',
        p_indirizzo_dettaglio_id := 1
      ) $$,
      (SELECT soggetto_id FROM tmp_ind_sogg_ctx)
    ),
    'p_tipo_indirizzo_codice obbligatorio',
    '10. Errore tipo indirizzo codice vuoto'
  );

-- =========================================================
-- 11) Errore: tipo indirizzo inesistente
-- =========================================================
SELECT throws_matching(
    format(
      $$SELECT anagrafiche.fn_crea_indirizzo_soggetto(
        p_soggetto_id            := %L::uuid,
        p_tipo_indirizzo_codice  := 'ZZZZINESISTENTE',
        p_indirizzo_dettaglio_id := 1
      ) $$,
      (SELECT soggetto_id FROM tmp_ind_sogg_ctx)
    ),
    'Tipo indirizzo non trovato',
    '11. Errore tipo indirizzo inesistente'
  );

SELECT * FROM finish();
ROLLBACK;
