-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test trigger guard obbligatorieta' CF/PIVA su anagrafiche.soggetti
-- Funzione: anagrafiche.trgfn_soggetti_guard_cf_piva_obbligatori()
-- Trigger:  trg_soggetti_a10_guard_cf_piva_obbligatori_ins_upd
--
-- Scenario:
--   - PR (Privato, PF): cf_obbligatorio=true, piva_obbligatoria=false
--     - senza CF → FALLISCE
--     - con CF, senza PIVA → OK
--   - DI (Ditta Ind., PF): piva_obbligatoria=true, cf_obbligatorio=true
--     - senza PIVA → FALLISCE
--     - senza CF → FALLISCE
--     - con entrambi → OK
--   - SP (Soc. Persone, PG): piva_obbligatoria=true, cf_obbligatorio=true
--     - senza PIVA → FALLISCE
--     - con entrambi → OK
--   Nota: SP anziche' SC per evitare vincolo dati_societari_policy = REQUIRED
--   - tipo_soggetto_dettaglio_id NULL → nessun vincolo, OK
--
-- Nota: per ogni soggetto viene creato un contatto per i vincoli esistenti.
-- ------------------------------------------------------------

-- =========================================================
-- Cleanup iniziale
-- =========================================================
DO $$
DECLARE
  l_codici text[] := ARRAY[
    'TST-CFPIVA-PR-ERR', 'TST-CFPIVA-PR-OK',
    'TST-CFPIVA-DI-ERR1', 'TST-CFPIVA-DI-ERR2', 'TST-CFPIVA-DI-OK',
    'TST-CFPIVA-SP-ERR', 'TST-CFPIVA-SP-OK',
    'TST-CFPIVA-NULL-OK'
  ];
BEGIN
  DELETE FROM anagrafiche.indirizzi_soggetti i
  WHERE i.soggetto_id IN (
    SELECT s.id FROM anagrafiche.soggetti s WHERE s.codice = ANY(l_codici)
  );
  DELETE FROM anagrafiche.contatti c
  WHERE c.soggetto_id IN (
    SELECT s.id FROM anagrafiche.soggetti s WHERE s.codice = ANY(l_codici)
  );
  DELETE FROM anagrafiche.soggetti s
  WHERE s.codice = ANY(l_codici);
END;
$$;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
-- ⚠️ Questo file non apre una transazione propria: la riga va prima di plan().
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(10);

-- =========================================================
-- 0) Precondizioni
-- =========================================================
CREATE TEMP TABLE tmp_stato_test AS
SELECT id AS stato_id
FROM config.stati ORDER BY id LIMIT 1;

SELECT ok(
    (SELECT count(*) FROM tmp_stato_test) = 1,
    'Esiste almeno uno stato in config.stati'
);

CREATE TEMP TABLE tmp_tipo_contatto_test AS
SELECT id AS tipo_contatto_id
FROM config.tipi_contatti ORDER BY id LIMIT 1;

SELECT ok(
    (SELECT count(*) FROM tmp_tipo_contatto_test) = 1,
    'Esiste almeno un tipo_contatto in config.tipi_contatti'
);

-- Recupero tipi_soggetto_dettaglio
CREATE TEMP TABLE tmp_tipo_pr AS
SELECT id AS tipo_soggetto_dettaglio_id
FROM config.tipi_soggetto_dettaglio WHERE codice_interno = 'PR';

CREATE TEMP TABLE tmp_tipo_di AS
SELECT id AS tipo_soggetto_dettaglio_id
FROM config.tipi_soggetto_dettaglio WHERE codice_interno = 'DI';

CREATE TEMP TABLE tmp_tipo_sp AS
SELECT id AS tipo_soggetto_dettaglio_id
FROM config.tipi_soggetto_dettaglio WHERE codice_interno = 'SP';

-- Tipi indirizzo obbligatori (per guard indirizzi_required deferrable)
CREATE TEMP TABLE tmp_tipo_ind_res AS
SELECT id AS tipo_indirizzo_id
FROM config.tipi_indirizzi WHERE codice_interno = 'RES';

CREATE TEMP TABLE tmp_tipo_ind_domfisc AS
SELECT id AS tipo_indirizzo_id
FROM config.tipi_indirizzi WHERE codice_interno = 'DOMFISC';

CREATE TEMP TABLE tmp_tipo_ind_sedeleg AS
SELECT id AS tipo_indirizzo_id
FROM config.tipi_indirizzi WHERE codice_interno = 'SEDELEG';

-- =========================================================
-- 1) PR senza CF → FALLISCE (cf_obbligatorio = true)
-- =========================================================
SELECT throws_ok(
    $$
      INSERT INTO anagrafiche.soggetti (
          codice, cognome, nome, stato_id,
          codice_fiscale, partita_iva, tipo_soggetto_dettaglio_id
      ) VALUES (
          'TST-CFPIVA-PR-ERR', 'Test', 'NoCF', (SELECT stato_id FROM tmp_stato_test),
          NULL, NULL,
          (SELECT tipo_soggetto_dettaglio_id FROM tmp_tipo_pr)
      );
    $$,
    NULL,
    'PR senza codice_fiscale: FALLISCE (cf_obbligatorio = true)'
);

-- =========================================================
-- 2) PR con CF, senza PIVA → OK (piva_obbligatoria = false)
-- =========================================================
SELECT lives_ok(
    $$
      INSERT INTO anagrafiche.soggetti (
          codice, cognome, nome, stato_id,
          codice_fiscale, partita_iva, tipo_soggetto_dettaglio_id
      ) VALUES (
          'TST-CFPIVA-PR-OK', 'Test', 'ConCF', (SELECT stato_id FROM tmp_stato_test),
          'TSTNMA80A01H501N', NULL,
          (SELECT tipo_soggetto_dettaglio_id FROM tmp_tipo_pr)
      );
      INSERT INTO anagrafiche.contatti (
          tipo_contatto_id, soggetto_id, nominativo, email, is_default
      ) SELECT
          (SELECT tipo_contatto_id FROM tmp_tipo_contatto_test),
          s.id, 'Contatto PR', 'pr@test.com', TRUE
      FROM anagrafiche.soggetti s WHERE s.codice = 'TST-CFPIVA-PR-OK';
      INSERT INTO anagrafiche.indirizzi_soggetti (soggetto_id, tipo_indirizzo_id, indirizzo_libero,
          stato_id, locality, postal_box, administrative_area)
      SELECT s.id, (SELECT tipo_indirizzo_id FROM tmp_tipo_ind_res), 'Via Test PR RES',
          (SELECT stato_id FROM tmp_stato_test), 'Test City', '00100', 'TS'
      FROM anagrafiche.soggetti s WHERE s.codice = 'TST-CFPIVA-PR-OK';
      INSERT INTO anagrafiche.indirizzi_soggetti (soggetto_id, tipo_indirizzo_id, indirizzo_libero,
          stato_id, locality, postal_box, administrative_area)
      SELECT s.id, (SELECT tipo_indirizzo_id FROM tmp_tipo_ind_domfisc), 'Via Test PR DOMFISC',
          (SELECT stato_id FROM tmp_stato_test), 'Test City', '00100', 'TS'
      FROM anagrafiche.soggetti s WHERE s.codice = 'TST-CFPIVA-PR-OK';
    $$,
    'PR con CF, senza PIVA: OK'
);

-- =========================================================
-- 3) DI senza PIVA → FALLISCE (piva_obbligatoria = true)
-- =========================================================
SELECT throws_ok(
    $$
      INSERT INTO anagrafiche.soggetti (
          codice, cognome, nome, stato_id,
          codice_fiscale, partita_iva, tipo_soggetto_dettaglio_id
      ) VALUES (
          'TST-CFPIVA-DI-ERR1', 'Test', 'NoPIVA', (SELECT stato_id FROM tmp_stato_test),
          'TSTNMA80A01H501N', NULL,
          (SELECT tipo_soggetto_dettaglio_id FROM tmp_tipo_di)
      );
    $$,
    NULL,
    'DI senza partita_iva: FALLISCE (piva_obbligatoria = true)'
);

-- =========================================================
-- 4) DI senza CF → FALLISCE (cf_obbligatorio = true)
-- =========================================================
SELECT throws_ok(
    $$
      INSERT INTO anagrafiche.soggetti (
          codice, cognome, nome, stato_id,
          codice_fiscale, partita_iva, tipo_soggetto_dettaglio_id
      ) VALUES (
          'TST-CFPIVA-DI-ERR2', 'Test', 'NoCF', (SELECT stato_id FROM tmp_stato_test),
          NULL, '12345678903',
          (SELECT tipo_soggetto_dettaglio_id FROM tmp_tipo_di)
      );
    $$,
    NULL,
    'DI senza codice_fiscale: FALLISCE (cf_obbligatorio = true)'
);

-- =========================================================
-- 5) DI con entrambi → OK
-- =========================================================
SELECT lives_ok(
    $$
      INSERT INTO anagrafiche.soggetti (
          codice, cognome, nome, stato_id,
          codice_fiscale, partita_iva, tipo_soggetto_dettaglio_id
      ) VALUES (
          'TST-CFPIVA-DI-OK', 'Test', 'ConTutto', (SELECT stato_id FROM tmp_stato_test),
          'TSTNMA80A01H501N', '12345678903',
          (SELECT tipo_soggetto_dettaglio_id FROM tmp_tipo_di)
      );
      INSERT INTO anagrafiche.contatti (
          tipo_contatto_id, soggetto_id, nominativo, email, is_default
      ) SELECT
          (SELECT tipo_contatto_id FROM tmp_tipo_contatto_test),
          s.id, 'Contatto DI', 'di@test.com', TRUE
      FROM anagrafiche.soggetti s WHERE s.codice = 'TST-CFPIVA-DI-OK';
      INSERT INTO anagrafiche.indirizzi_soggetti (soggetto_id, tipo_indirizzo_id, indirizzo_libero,
          stato_id, locality, postal_box, administrative_area)
      SELECT s.id, (SELECT tipo_indirizzo_id FROM tmp_tipo_ind_domfisc), 'Via Test DI DOMFISC',
          (SELECT stato_id FROM tmp_stato_test), 'Test City', '00100', 'TS'
      FROM anagrafiche.soggetti s WHERE s.codice = 'TST-CFPIVA-DI-OK';
    $$,
    'DI con CF e PIVA: OK'
);

-- =========================================================
-- 6) SP senza PIVA → FALLISCE (piva_obbligatoria = true)
-- =========================================================
SELECT throws_ok(
    $$
      INSERT INTO anagrafiche.soggetti (
          codice, ragione_sociale, stato_id,
          codice_fiscale, partita_iva, tipo_soggetto_dettaglio_id
      ) VALUES (
          'TST-CFPIVA-SP-ERR', 'Azienda NoPIVA', (SELECT stato_id FROM tmp_stato_test),
          '12345678903', NULL,
          (SELECT tipo_soggetto_dettaglio_id FROM tmp_tipo_sp)
      );
    $$,
    NULL,
    'SP senza partita_iva: FALLISCE (piva_obbligatoria = true)'
);

-- =========================================================
-- 7) SP con entrambi → OK
-- =========================================================
SELECT lives_ok(
    $$
      INSERT INTO anagrafiche.soggetti (
          codice, ragione_sociale, stato_id,
          codice_fiscale, partita_iva, tipo_soggetto_dettaglio_id
      ) VALUES (
          'TST-CFPIVA-SP-OK', 'Azienda ConTutto', (SELECT stato_id FROM tmp_stato_test),
          '12345678903', '12345678903',
          (SELECT tipo_soggetto_dettaglio_id FROM tmp_tipo_sp)
      );
      INSERT INTO anagrafiche.contatti (
          tipo_contatto_id, soggetto_id, nominativo, email, is_default
      ) SELECT
          (SELECT tipo_contatto_id FROM tmp_tipo_contatto_test),
          s.id, 'Contatto SP', 'sp@test.com', TRUE
      FROM anagrafiche.soggetti s WHERE s.codice = 'TST-CFPIVA-SP-OK';
      INSERT INTO anagrafiche.indirizzi_soggetti (soggetto_id, tipo_indirizzo_id, indirizzo_libero,
          stato_id, locality, postal_box, administrative_area)
      SELECT s.id, (SELECT tipo_indirizzo_id FROM tmp_tipo_ind_sedeleg), 'Via Test SP SEDELEG',
          (SELECT stato_id FROM tmp_stato_test), 'Test City', '00100', 'TS'
      FROM anagrafiche.soggetti s WHERE s.codice = 'TST-CFPIVA-SP-OK';
    $$,
    'SP con CF e PIVA: OK'
);

-- =========================================================
-- 8) tipo_soggetto_dettaglio_id NULL → nessun vincolo, OK
-- =========================================================
SELECT lives_ok(
    $$
      INSERT INTO anagrafiche.soggetti (
          codice, cognome, nome, stato_id,
          codice_fiscale, partita_iva, tipo_soggetto_dettaglio_id
      ) VALUES (
          'TST-CFPIVA-NULL-OK', 'Test', 'NullTipo', (SELECT stato_id FROM tmp_stato_test),
          NULL, NULL,
          NULL
      );
      INSERT INTO anagrafiche.contatti (
          tipo_contatto_id, soggetto_id, nominativo, email, is_default
      ) SELECT
          (SELECT tipo_contatto_id FROM tmp_tipo_contatto_test),
          s.id, 'Contatto NULL tipo', 'null@test.com', TRUE
      FROM anagrafiche.soggetti s WHERE s.codice = 'TST-CFPIVA-NULL-OK';
    $$,
    'Soggetto con tipo_soggetto_dettaglio_id NULL: OK (nessun vincolo)'
);

-- Fine test
SELECT * FROM finish();
