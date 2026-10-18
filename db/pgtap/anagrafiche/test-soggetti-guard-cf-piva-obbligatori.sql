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
-- ============================================================================
-- rev 2026-08-18 — bonifica baseline. Qui c'era un blocco di «cleanup
-- iniziale» che cancellava i soggetti di prova delle corse precedenti: non
-- funziona piu' (FK RESTRICT verso istanze_utilities e altro), e il file
-- moriva prima della prima asserzione — ZERO su 10.
-- Il file e' gia' BEGIN ... ROLLBACK, quindi residui suoi non ne fa: quelli in
-- giro sono di prima. Il rimedio e' non collidere invece di cancellare —
-- codici e partite IVA unici per corsa.
-- ============================================================================

BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file diventerebbe verde per sottrazione. Nel DB ce ne sono 365.
--   IMMEDIATE li riporta a scattare a fine di OGNI istruzione — cioe' esatta-
--   mente come si comportavano prima, quando il file girava in autocommit e
--   ogni istruzione era una transazione a se'. Messa in testa e non in coda
--   apposta: in coda scatterebbero tutti insieme DOPO il cleanup, su righe
--   ormai cancellate, e fallirebbero per un motivo che non riguarda il test.
--   Brief: brief-db-pgtap-runner-rls-baseline §17.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(10);

CREATE TEMP TABLE tmp_run_sfx AS
-- ⚠️ Anche il codice fiscale si prende libero: quello che il file aveva
--   inchiodato (TSTNMA80A01H501N) e' bruciato da un soggetto residuo, e
--   uq_soggetto_idstato_id_fiscale_univoco non perdona.
SELECT substr(md5(clock_timestamp()::text), 1, 8) AS sfx,
       dbops.fn_pgtap_piva_libera() AS piva_libera,
       dbops.fn_pgtap_cf_libero()   AS cf_libero;

-- =========================================================
-- 0) Precondizioni
-- =========================================================
CREATE TEMP TABLE tmp_stato_test AS
SELECT id AS stato_id
FROM config.stati ORDER BY id LIMIT 1;
-- rev 2026-10-18: i campi della forma che il guard vuole per questo stato
--   (dbops.fn_pgtap_indirizzo_libero_forma: comune e CAP per l'Italia).
ALTER TABLE tmp_stato_test ADD COLUMN comune_id integer, ADD COLUMN codice_postale_id integer,
                           ADD COLUMN locality varchar, ADD COLUMN postal_code varchar;
UPDATE tmp_stato_test
   SET (comune_id, codice_postale_id, locality, postal_code) =
       (SELECT f.comune_id, f.codice_postale_id, f.locality, f.postal_code
          FROM dbops.fn_pgtap_indirizzo_libero_forma(tmp_stato_test.stato_id) f);

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
          codice, cognome, nome, sesso, stato_id,
          codice_fiscale, partita_iva, tipo_soggetto_dettaglio_id
      ) VALUES (
          -- sesso 'M': per un privato e' obbligatorio, e qui la causa
          --   sotto prova dev'essere una sola (il codice fiscale)
          'TST-CFPIVA-PR-ERR-' || (SELECT sfx FROM tmp_run_sfx), 'Test', 'NoCF', 'M', (SELECT stato_id FROM tmp_stato_test),
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
      -- ⭐ Finestra differita: i guard di completezza su soggetti sono
      --   DEFERRABLE INITIALLY DEFERRED apposta — un soggetto e' una saga.
      --   Il SET CONSTRAINTS ALL IMMEDIATE del preambolo li farebbe scattare
      --   sul PRIMO insert, prima che contatto e indirizzi esistano.
      SET CONSTRAINTS ALL DEFERRED;
      INSERT INTO anagrafiche.soggetti (
          codice, cognome, nome, sesso, stato_id,
          codice_fiscale, partita_iva, tipo_soggetto_dettaglio_id
      ) VALUES (
          -- sesso 'M': per un privato e' obbligatorio, e qui la causa
          --   sotto prova dev'essere una sola (il codice fiscale)
          'TST-CFPIVA-PR-OK-' || (SELECT sfx FROM tmp_run_sfx), 'Test', 'ConCF', 'M', (SELECT stato_id FROM tmp_stato_test),
          (SELECT cf_libero FROM tmp_run_sfx), NULL,
          (SELECT tipo_soggetto_dettaglio_id FROM tmp_tipo_pr)
      );
      INSERT INTO anagrafiche.contatti (
          tipo_contatto_id, soggetto_id, nominativo, email, is_default
      ) SELECT
          (SELECT tipo_contatto_id FROM tmp_tipo_contatto_test),
          s.id, 'Contatto PR', 'pr@test.com', TRUE
      FROM anagrafiche.soggetti s WHERE s.codice = 'TST-CFPIVA-PR-OK-' || (SELECT sfx FROM tmp_run_sfx);
      INSERT INTO anagrafiche.indirizzi_soggetti (soggetto_id, tipo_indirizzo_id, indirizzo_libero,
          stato_id, comune_id, codice_postale_id, locality, postal_code)
      SELECT s.id, (SELECT tipo_indirizzo_id FROM tmp_tipo_ind_res), 'Via Test PR RES',
          (SELECT stato_id FROM tmp_stato_test), (SELECT comune_id FROM tmp_stato_test), (SELECT codice_postale_id FROM tmp_stato_test), (SELECT locality FROM tmp_stato_test), (SELECT postal_code FROM tmp_stato_test)
      FROM anagrafiche.soggetti s WHERE s.codice = 'TST-CFPIVA-PR-OK-' || (SELECT sfx FROM tmp_run_sfx);
      INSERT INTO anagrafiche.indirizzi_soggetti (soggetto_id, tipo_indirizzo_id, indirizzo_libero,
          stato_id, comune_id, codice_postale_id, locality, postal_code)
      SELECT s.id, (SELECT tipo_indirizzo_id FROM tmp_tipo_ind_domfisc), 'Via Test PR DOMFISC',
          (SELECT stato_id FROM tmp_stato_test), (SELECT comune_id FROM tmp_stato_test), (SELECT codice_postale_id FROM tmp_stato_test), (SELECT locality FROM tmp_stato_test), (SELECT postal_code FROM tmp_stato_test)
      FROM anagrafiche.soggetti s WHERE s.codice = 'TST-CFPIVA-PR-OK-' || (SELECT sfx FROM tmp_run_sfx);
      -- Saga completa: qui i guard verificano davvero.
      SET CONSTRAINTS ALL IMMEDIATE;
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
          'TST-CFPIVA-DI-ERR1-' || (SELECT sfx FROM tmp_run_sfx), 'Test', 'NoPIVA', (SELECT stato_id FROM tmp_stato_test),
          (SELECT cf_libero FROM tmp_run_sfx), NULL,
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
          'TST-CFPIVA-DI-ERR2-' || (SELECT sfx FROM tmp_run_sfx), 'Test', 'NoCF', (SELECT stato_id FROM tmp_stato_test),
          NULL, (SELECT piva_libera FROM tmp_run_sfx),
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
      -- ⭐ Finestra differita: i guard di completezza su soggetti sono
      --   DEFERRABLE INITIALLY DEFERRED apposta — un soggetto e' una saga.
      --   Il SET CONSTRAINTS ALL IMMEDIATE del preambolo li farebbe scattare
      --   sul PRIMO insert, prima che contatto e indirizzi esistano.
      SET CONSTRAINTS ALL DEFERRED;
      INSERT INTO anagrafiche.soggetti (
          codice, cognome, nome, stato_id,
          codice_fiscale, partita_iva, tipo_soggetto_dettaglio_id
      ) VALUES (
          'TST-CFPIVA-DI-OK-' || (SELECT sfx FROM tmp_run_sfx), 'Test', 'ConTutto', (SELECT stato_id FROM tmp_stato_test),
          (SELECT cf_libero FROM tmp_run_sfx), (SELECT piva_libera FROM tmp_run_sfx),
          (SELECT tipo_soggetto_dettaglio_id FROM tmp_tipo_di)
      );
      INSERT INTO anagrafiche.contatti (
          tipo_contatto_id, soggetto_id, nominativo, email, is_default
      ) SELECT
          (SELECT tipo_contatto_id FROM tmp_tipo_contatto_test),
          s.id, 'Contatto DI', 'di@test.com', TRUE
      FROM anagrafiche.soggetti s WHERE s.codice = 'TST-CFPIVA-DI-OK-' || (SELECT sfx FROM tmp_run_sfx);
      INSERT INTO anagrafiche.indirizzi_soggetti (soggetto_id, tipo_indirizzo_id, indirizzo_libero,
          stato_id, comune_id, codice_postale_id, locality, postal_code)
      SELECT s.id, (SELECT tipo_indirizzo_id FROM tmp_tipo_ind_domfisc), 'Via Test DI DOMFISC',
          (SELECT stato_id FROM tmp_stato_test), (SELECT comune_id FROM tmp_stato_test), (SELECT codice_postale_id FROM tmp_stato_test), (SELECT locality FROM tmp_stato_test), (SELECT postal_code FROM tmp_stato_test)
      FROM anagrafiche.soggetti s WHERE s.codice = 'TST-CFPIVA-DI-OK-' || (SELECT sfx FROM tmp_run_sfx);
      -- Saga completa: qui i guard verificano davvero.
      SET CONSTRAINTS ALL IMMEDIATE;
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
          'TST-CFPIVA-SP-ERR-' || (SELECT sfx FROM tmp_run_sfx), 'Azienda NoPIVA', (SELECT stato_id FROM tmp_stato_test),
          (SELECT piva_libera FROM tmp_run_sfx), NULL,
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
      -- ⭐ Finestra differita: i guard di completezza su soggetti sono
      --   DEFERRABLE INITIALLY DEFERRED apposta — un soggetto e' una saga.
      --   Il SET CONSTRAINTS ALL IMMEDIATE del preambolo li farebbe scattare
      --   sul PRIMO insert, prima che contatto e indirizzi esistano.
      SET CONSTRAINTS ALL DEFERRED;
      INSERT INTO anagrafiche.soggetti (
          codice, ragione_sociale, stato_id,
          codice_fiscale, partita_iva, tipo_soggetto_dettaglio_id
      ) VALUES (
          'TST-CFPIVA-SP-OK-' || (SELECT sfx FROM tmp_run_sfx), 'Azienda ConTutto', (SELECT stato_id FROM tmp_stato_test),
          (SELECT piva_libera FROM tmp_run_sfx), (SELECT piva_libera FROM tmp_run_sfx),
          (SELECT tipo_soggetto_dettaglio_id FROM tmp_tipo_sp)
      );
      INSERT INTO anagrafiche.contatti (
          tipo_contatto_id, soggetto_id, nominativo, email, is_default
      ) SELECT
          (SELECT tipo_contatto_id FROM tmp_tipo_contatto_test),
          s.id, 'Contatto SP', 'sp@test.com', TRUE
      FROM anagrafiche.soggetti s WHERE s.codice = 'TST-CFPIVA-SP-OK-' || (SELECT sfx FROM tmp_run_sfx);
      INSERT INTO anagrafiche.indirizzi_soggetti (soggetto_id, tipo_indirizzo_id, indirizzo_libero,
          stato_id, comune_id, codice_postale_id, locality, postal_code)
      SELECT s.id, (SELECT tipo_indirizzo_id FROM tmp_tipo_ind_sedeleg), 'Via Test SP SEDELEG',
          (SELECT stato_id FROM tmp_stato_test), (SELECT comune_id FROM tmp_stato_test), (SELECT codice_postale_id FROM tmp_stato_test), (SELECT locality FROM tmp_stato_test), (SELECT postal_code FROM tmp_stato_test)
      FROM anagrafiche.soggetti s WHERE s.codice = 'TST-CFPIVA-SP-OK-' || (SELECT sfx FROM tmp_run_sfx);
      -- Saga completa: qui i guard verificano davvero.
      SET CONSTRAINTS ALL IMMEDIATE;
    $$,
    'SP con CF e PIVA: OK'
);

-- =========================================================
-- 8) tipo_soggetto_dettaglio_id NULL → nessun vincolo, OK
-- =========================================================
SELECT lives_ok(
    $$
      -- ⭐ Finestra differita: i guard di completezza su soggetti sono
      --   DEFERRABLE INITIALLY DEFERRED apposta — un soggetto e' una saga.
      --   Il SET CONSTRAINTS ALL IMMEDIATE del preambolo li farebbe scattare
      --   sul PRIMO insert, prima che contatto e indirizzi esistano.
      SET CONSTRAINTS ALL DEFERRED;
      INSERT INTO anagrafiche.soggetti (
          codice, cognome, nome, stato_id,
          codice_fiscale, partita_iva, tipo_soggetto_dettaglio_id
      ) VALUES (
          'TST-CFPIVA-NULL-OK-' || (SELECT sfx FROM tmp_run_sfx), 'Test', 'NullTipo', (SELECT stato_id FROM tmp_stato_test),
          NULL, NULL,
          NULL
      );
      INSERT INTO anagrafiche.contatti (
          tipo_contatto_id, soggetto_id, nominativo, email, is_default
      ) SELECT
          (SELECT tipo_contatto_id FROM tmp_tipo_contatto_test),
          s.id, 'Contatto NULL tipo', 'null@test.com', TRUE
      FROM anagrafiche.soggetti s WHERE s.codice = 'TST-CFPIVA-NULL-OK-' || (SELECT sfx FROM tmp_run_sfx);
      -- Saga completa: qui i guard verificano davvero.
      SET CONSTRAINTS ALL IMMEDIATE;
    $$,
    'Soggetto con tipo_soggetto_dettaglio_id NULL: OK (nessun vincolo)'
);

-- Fine test
SELECT * FROM finish();

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia nulla dietro di se'. Le DELETE del cleanup restano
-- perche' dove sono un'asserzione devono girare davvero.
ROLLBACK;
