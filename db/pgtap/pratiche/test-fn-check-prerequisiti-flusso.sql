-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: pratiche.fn_check_prerequisiti_flusso
--       Pure check: verifica prerequisiti template flusso
--
-- Indice test:
-- 0) Precondizioni (provisioning + verifica)
-- 1) Setup tipo_prestazione e template_flussi di test
-- 2) Setup prerequisiti (template B prerequisito di template A)
-- 3) Pratica di test
-- 4) fn_check senza flussi completati: soddisfatto = false
-- 5) Completamento flusso prerequisito
-- 6) fn_check con flusso completato: soddisfatto = true
-- 7) fn_check su template senza prerequisiti: zero righe
-- 8) Cleanup
-- ------------------------------------------------------------

-- ⚠️ Transazione, e non e' una formalita'. Il cleanup di questo file sta in
--   coda: col runner vero (pg_prove gira con ON_ERROR_STOP) un fallimento a
--   meta' non ci arriva mai, e i dati di prova restano nel database a rompere
--   la corsa successiva — che vede un rosso non suo.
--   Brief: brief-db-pgtap-runner-rls-baseline §15.3.
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

SELECT plan(5);

-- =========================================================
-- 0) Precondizioni: provisioning config data (idempotente)
-- =========================================================

INSERT INTO config.stati_pratiche (codice, codice_interno, descrizione, attivo)
VALUES ('BOZZA', 'BOZZA', 'Bozza', true)
ON CONFLICT (codice_interno) DO NOTHING;

INSERT INTO config.stati_flussi_pratiche (codice, codice_interno, descrizione, attivo)
VALUES
  ('DA_ESEGUIRE', 'DA_ESEGUIRE', 'Da eseguire', true),
  ('COMPLETATO',  'COMPLETATO',  'Completato',  true)
ON CONFLICT (codice_interno) DO NOTHING;

INSERT INTO config.priorita_pratiche (codice, codice_interno, descrizione, sequenza, attivo)
VALUES ('NORMALE', 'NORMALE', 'Normale', 20, true)
ON CONFLICT (codice_interno) DO NOTHING;

CREATE TEMP TABLE tmp_test_refs AS
SELECT
  script.fn_pgtap_emittente_operatore() AS emittente_id,
  (SELECT id FROM anagrafiche.soggetti ORDER BY id LIMIT 1) AS soggetto_id,
  (SELECT id FROM config.stati_pratiche WHERE codice_interno = 'BOZZA' AND attivo = true LIMIT 1) AS stato_bozza_id,
  (SELECT id FROM config.stati_flussi_pratiche WHERE codice_interno = 'DA_ESEGUIRE' AND attivo = true LIMIT 1) AS stato_da_eseguire_id,
  (SELECT id FROM config.stati_flussi_pratiche WHERE codice_interno = 'COMPLETATO' AND attivo = true LIMIT 1) AS stato_completato_id,
  (SELECT id FROM config.priorita_pratiche WHERE codice_interno = 'NORMALE' AND attivo = true LIMIT 1) AS priorita_normale_id;

SELECT ok(
    (SELECT emittente_id IS NOT NULL AND soggetto_id IS NOT NULL
        AND stato_bozza_id IS NOT NULL
        AND stato_da_eseguire_id IS NOT NULL AND stato_completato_id IS NOT NULL
        AND priorita_normale_id IS NOT NULL
     FROM tmp_test_refs),
    '0. Precondizioni soddisfatte'
);

-- =========================================================
-- 1) Setup tipo_prestazione e template_flussi
-- =========================================================

CREATE TEMP TABLE tmp_test_tp AS
WITH ins AS (
  INSERT INTO pratiche.tipi_prestazione (codice, codice_interno, descrizione, attivo)
  VALUES ('TEST_PGTAP_TP', 'TEST_PGTAP_TP', 'Tipo prestazione test pgTAP', true)
  ON CONFLICT (codice_interno) DO UPDATE SET descrizione = EXCLUDED.descrizione
  RETURNING id
)
SELECT id AS tp_id FROM ins;

CREATE TEMP TABLE tmp_test_tfa AS
WITH ins AS (
  INSERT INTO pratiche.template_flussi (tipo_prestazione_id, codice, descrizione, attivo)
  VALUES ((SELECT tp_id FROM tmp_test_tp), 'TF_A_PGTAP', 'Template A test', true)
  ON CONFLICT (definizione_id, codice) DO UPDATE SET descrizione = EXCLUDED.descrizione
  RETURNING id
)
SELECT id AS tfa_id FROM ins;

CREATE TEMP TABLE tmp_test_tfb AS
WITH ins AS (
  INSERT INTO pratiche.template_flussi (tipo_prestazione_id, codice, descrizione, attivo)
  VALUES ((SELECT tp_id FROM tmp_test_tp), 'TF_B_PGTAP', 'Template B test (prerequisito)', true)
  ON CONFLICT (definizione_id, codice) DO UPDATE SET descrizione = EXCLUDED.descrizione
  RETURNING id
)
SELECT id AS tfb_id FROM ins;

-- =========================================================
-- 2) Prerequisito: A richiede B
-- =========================================================

INSERT INTO pratiche.template_flussi_prerequisiti (template_flusso_id, prerequisito_id)
VALUES (
  (SELECT tfa_id FROM tmp_test_tfa),
  (SELECT tfb_id FROM tmp_test_tfb)
)
ON CONFLICT (template_flusso_id, prerequisito_id) DO NOTHING;

-- =========================================================
-- 3) Pratica di test
-- =========================================================

CREATE TEMP TABLE tmp_test_pratica AS
WITH ins AS (
  INSERT INTO pratiche.pratiche (
    emittente_fiscale_id, tipo_prestazione_id, soggetto_id, stato_id, priorita_id
  )
  VALUES (
    (SELECT emittente_id FROM tmp_test_refs),
    (SELECT tp_id FROM tmp_test_tp),
    (SELECT soggetto_id FROM tmp_test_refs),
    (SELECT stato_bozza_id FROM tmp_test_refs),
    (SELECT priorita_normale_id FROM tmp_test_refs)
  )
  RETURNING id
)
SELECT id AS pratica_id FROM ins;

-- =========================================================
-- 4) fn_check senza flussi completati: soddisfatto = false
-- =========================================================

SELECT is(
    (SELECT soddisfatto
       FROM pratiche.fn_check_prerequisiti_flusso(
              (SELECT pratica_id FROM tmp_test_pratica),
              (SELECT tfa_id FROM tmp_test_tfa)
            )
      -- ⚠️ Si dice QUALE prerequisito, invece di prenderne uno a caso: la
      --   funzione ritorna una riga per prerequisito, e in produzione i
      --   template ne hanno fino a 6. Oggi la fixture ne crea uno solo e il
      --   LIMIT 1 tornava per forza quello — ma il codice del template e'
      --   fisso, non randomizzato, quindi basta un prerequisito in piu' su
      --   TF_A_PGTAP perche' l'asserzione cambi soggetto in silenzio.
      WHERE prerequisito_id = (SELECT tfb_id FROM tmp_test_tfb)),
    false,
    '1. Prerequisito non soddisfatto (nessun flusso completato per template B)'
);

-- =========================================================
-- 5) Completamento flusso prerequisito (template B)
-- =========================================================

-- esito obbligatorio per COMPLETATO (guard trg_flussi_a10_guard_esito_completato).
-- Il prerequisito ha esito_richiesto NULL: 'POSITIVO' soddisfa comunque.
INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id, esito)
VALUES (
  (SELECT pratica_id FROM tmp_test_pratica),
  (SELECT tfb_id FROM tmp_test_tfb),
  (SELECT stato_completato_id FROM tmp_test_refs),
  'POSITIVO'
);

-- =========================================================
-- 6) fn_check con flusso completato: soddisfatto = true
-- =========================================================

SELECT is(
    (SELECT soddisfatto
       FROM pratiche.fn_check_prerequisiti_flusso(
              (SELECT pratica_id FROM tmp_test_pratica),
              (SELECT tfa_id FROM tmp_test_tfa)
            )
      -- ⚠️ Si dice QUALE prerequisito, invece di prenderne uno a caso: la
      --   funzione ritorna una riga per prerequisito, e in produzione i
      --   template ne hanno fino a 6. Oggi la fixture ne crea uno solo e il
      --   LIMIT 1 tornava per forza quello — ma il codice del template e'
      --   fisso, non randomizzato, quindi basta un prerequisito in piu' su
      --   TF_A_PGTAP perche' l'asserzione cambi soggetto in silenzio.
      WHERE prerequisito_id = (SELECT tfb_id FROM tmp_test_tfb)),
    true,
    '2. Prerequisito soddisfatto (flusso B completato)'
);

-- =========================================================
-- 7) fn_check su template senza prerequisiti: zero righe
-- =========================================================

SELECT is(
    (SELECT count(*)::integer
       FROM pratiche.fn_check_prerequisiti_flusso(
              (SELECT pratica_id FROM tmp_test_pratica),
              (SELECT tfb_id FROM tmp_test_tfb)
            )),
    0,
    '3. Template senza prerequisiti: zero righe'
);

-- =========================================================
-- 8) Verifica dettaglio risultato fn_check
-- =========================================================

SELECT ok(
    (SELECT prerequisito_id IS NOT NULL AND codice IS NOT NULL
       FROM pratiche.fn_check_prerequisiti_flusso(
              (SELECT pratica_id FROM tmp_test_pratica),
              (SELECT tfa_id FROM tmp_test_tfa)
            )
      -- ⚠️ Si dice QUALE prerequisito, invece di prenderne uno a caso: la
      --   funzione ritorna una riga per prerequisito, e in produzione i
      --   template ne hanno fino a 6. Oggi la fixture ne crea uno solo e il
      --   LIMIT 1 tornava per forza quello — ma il codice del template e'
      --   fisso, non randomizzato, quindi basta un prerequisito in piu' su
      --   TF_A_PGTAP perche' l'asserzione cambi soggetto in silenzio.
      WHERE prerequisito_id = (SELECT tfb_id FROM tmp_test_tfb)),
    '4. fn_check restituisce prerequisito_id e codice nel risultato'
);

-- =========================================================
-- 9) Cleanup
-- =========================================================

-- Cleanup resiliente (gestisce orfani da run precedenti falliti)
DELETE FROM pratiche.giornale WHERE pratica_id IN (
  SELECT id FROM pratiche.pratiche WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_test_tp)
);
DELETE FROM pratiche.flussi WHERE pratica_id IN (
  SELECT id FROM pratiche.pratiche WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_test_tp)
);
DELETE FROM pratiche.pratiche WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_test_tp);
DELETE FROM pratiche.template_flussi_prerequisiti
 WHERE template_flusso_id IN (
   SELECT id FROM pratiche.template_flussi WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_test_tp)
 );
DELETE FROM pratiche.template_flussi WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_test_tp);
DELETE FROM pratiche.tipi_prestazione WHERE id = (SELECT tp_id FROM tmp_test_tp);

SELECT * FROM finish();

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia nulla dietro di se'. Le DELETE del cleanup restano
-- perche' dove sono un'asserzione devono girare davvero.
ROLLBACK;
