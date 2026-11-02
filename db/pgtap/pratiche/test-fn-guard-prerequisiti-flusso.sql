-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: pratiche.fn_guard_prerequisiti_flusso
--       Guard fail-fast: raise su prerequisiti non soddisfatti
--
-- Indice test:
-- 0) Precondizioni (provisioning + verifica)
-- 1) Setup tipo_prestazione, template e prerequisiti
-- 2) Pratica di test
-- 3) Guard con prerequisiti mancanti: throws
-- 4) Completamento prerequisito
-- 5) Guard con prerequisiti soddisfatti: lives
-- 6) Cleanup
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

SELECT plan(4);
-- =========================================================
-- 0) Precondizioni: provisioning config data (idempotente)
-- =========================================================
INSERT INTO config.stati_pratiche (codice, codice_interno, descrizione, attivo)
VALUES ('BOZZA', 'BOZZA', 'Bozza', true) ON CONFLICT (codice_interno) DO NOTHING;
INSERT INTO config.stati_flussi_pratiche (codice, codice_interno, descrizione, attivo)
VALUES ('COMPLETATO', 'COMPLETATO', 'Completato', true) ON CONFLICT (codice_interno) DO NOTHING;
INSERT INTO config.priorita_pratiche (
    codice,
    codice_interno,
    descrizione,
    sequenza,
    attivo
  )
VALUES ('NORMALE', 'NORMALE', 'Normale', 20, true) ON CONFLICT (codice_interno) DO NOTHING;
CREATE TEMP TABLE tmp_guard_refs AS
SELECT script.fn_pgtap_emittente_operatore() AS emittente_id,
  (
    SELECT id
    FROM anagrafiche.soggetti
    ORDER BY id
    LIMIT 1
  ) AS soggetto_id,
  (
    SELECT id
    FROM config.stati_pratiche
    WHERE codice_interno = 'BOZZA'
      AND attivo = true
    LIMIT 1
  ) AS stato_bozza_id,
  (
    SELECT id
    FROM config.stati_flussi_pratiche
    WHERE codice_interno = 'COMPLETATO'
      AND attivo = true
    LIMIT 1
  ) AS stato_completato_id,
  (
    SELECT id
    FROM config.priorita_pratiche
    WHERE codice_interno = 'NORMALE'
      AND attivo = true
    LIMIT 1
  ) AS priorita_normale_id;
SELECT ok(
    (
      SELECT emittente_id IS NOT NULL
        AND soggetto_id IS NOT NULL
        AND stato_bozza_id IS NOT NULL
        AND stato_completato_id IS NOT NULL
        AND priorita_normale_id IS NOT NULL
      FROM tmp_guard_refs
    ),
    '0. Precondizioni soddisfatte'
  );
-- =========================================================
-- 1) Setup
-- =========================================================
CREATE TEMP TABLE tmp_guard_tp AS WITH ins AS (
  INSERT INTO pratiche.tipi_prestazione (codice, codice_interno, descrizione, attivo)
  VALUES (
      'TEST_GUARD_TP',
      'TEST_GUARD_TP',
      'Tipo prestazione test guard',
      true
    ) ON CONFLICT (codice_interno) DO
  UPDATE
  SET descrizione = EXCLUDED.descrizione
  RETURNING id
)
SELECT id AS tp_id
FROM ins;
CREATE TEMP TABLE tmp_guard_tfa AS WITH ins AS (
  INSERT INTO pratiche.template_flussi (tipo_prestazione_id, codice, descrizione, attivo)
  VALUES (
      (
        SELECT tp_id
        FROM tmp_guard_tp
      ),
      'TF_GUARD_A',
      'Template A guard test',
      true
    ) ON CONFLICT (definizione_id, codice) DO
  UPDATE
  SET descrizione = EXCLUDED.descrizione
  RETURNING id
)
SELECT id AS tfa_id
FROM ins;
CREATE TEMP TABLE tmp_guard_tfb AS WITH ins AS (
  INSERT INTO pratiche.template_flussi (tipo_prestazione_id, codice, descrizione, attivo)
  VALUES (
      (
        SELECT tp_id
        FROM tmp_guard_tp
      ),
      'TF_GUARD_B',
      'Template B guard (prerequisito)',
      true
    ) ON CONFLICT (definizione_id, codice) DO
  UPDATE
  SET descrizione = EXCLUDED.descrizione
  RETURNING id
)
SELECT id AS tfb_id
FROM ins;
INSERT INTO pratiche.template_flussi_prerequisiti (template_flusso_id, prerequisito_id)
VALUES (
    (
      SELECT tfa_id
      FROM tmp_guard_tfa
    ),
    (
      SELECT tfb_id
      FROM tmp_guard_tfb
    )
  ) ON CONFLICT (template_flusso_id, prerequisito_id) DO NOTHING;
-- =========================================================
-- 2) Pratica di test
-- =========================================================
CREATE TEMP TABLE tmp_guard_pratica AS WITH ins AS (
  INSERT INTO pratiche.pratiche (
      emittente_fiscale_id,
      tipo_prestazione_id,
      soggetto_id,
      stato_id,
      priorita_id
    )
  VALUES (
      (
        SELECT emittente_id
        FROM tmp_guard_refs
      ),
      (
        SELECT tp_id
        FROM tmp_guard_tp
      ),
      (
        SELECT soggetto_id
        FROM tmp_guard_refs
      ),
      (
        SELECT stato_bozza_id
        FROM tmp_guard_refs
      ),
      (
        SELECT priorita_normale_id
        FROM tmp_guard_refs
      )
    )
  RETURNING id
)
SELECT id AS pratica_id
FROM ins;
SELECT ok(
    (
      SELECT pratica_id IS NOT NULL
      FROM tmp_guard_pratica
    ),
    '1. Pratica di test creata'
  );
-- =========================================================
-- 3) Guard con prerequisiti mancanti: throws
-- =========================================================
SELECT throws_ok(
    format(
      'SELECT pratiche.fn_guard_prerequisiti_flusso(%s, %s)',
      (
        SELECT pratica_id
        FROM tmp_guard_pratica
      ),
      (
        SELECT tfa_id
        FROM tmp_guard_tfa
      )
    ),
    NULL,
    NULL,
    '2. Guard solleva eccezione con prerequisiti mancanti'
  );
-- =========================================================
-- 4) Completamento prerequisito
-- =========================================================
-- esito obbligatorio per COMPLETATO (guard trg_flussi_a10_guard_esito_completato).
INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id, esito)
VALUES (
    (
      SELECT pratica_id
      FROM tmp_guard_pratica
    ),
    (
      SELECT tfb_id
      FROM tmp_guard_tfb
    ),
    (
      SELECT stato_completato_id
      FROM tmp_guard_refs
    ),
    'POSITIVO'
  );
-- =========================================================
-- 5) Guard con prerequisiti soddisfatti: lives
-- =========================================================
SELECT lives_ok(
    format(
      'SELECT pratiche.fn_guard_prerequisiti_flusso(%s, %s)',
      (
        SELECT pratica_id
        FROM tmp_guard_pratica
      ),
      (
        SELECT tfa_id
        FROM tmp_guard_tfa
      )
    ),
    '3. Guard non solleva eccezione con prerequisiti soddisfatti'
  );
-- =========================================================
-- 6) Cleanup
-- =========================================================
-- Cleanup resiliente (gestisce orfani da run precedenti falliti)
DELETE FROM pratiche.giornale
WHERE pratica_id IN (
    SELECT id
    FROM pratiche.pratiche
    WHERE tipo_prestazione_id = (
        SELECT tp_id
        FROM tmp_guard_tp
      )
  );
DELETE FROM pratiche.flussi
WHERE pratica_id IN (
    SELECT id
    FROM pratiche.pratiche
    WHERE tipo_prestazione_id = (
        SELECT tp_id
        FROM tmp_guard_tp
      )
  );
DELETE FROM pratiche.pratiche
WHERE tipo_prestazione_id = (
    SELECT tp_id
    FROM tmp_guard_tp
  );
DELETE FROM pratiche.template_flussi_prerequisiti
WHERE template_flusso_id IN (
    SELECT id
    FROM pratiche.template_flussi
    WHERE tipo_prestazione_id = (
        SELECT tp_id
        FROM tmp_guard_tp
      )
  );
DELETE FROM pratiche.template_flussi
WHERE tipo_prestazione_id = (
    SELECT tp_id
    FROM tmp_guard_tp
  );
DELETE FROM pratiche.tipi_prestazione
WHERE id = (
    SELECT tp_id
    FROM tmp_guard_tp
  );
SELECT *
FROM finish();

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia nulla dietro di se'. Le DELETE del cleanup restano
-- perche' dove sono un'asserzione devono girare davvero.
ROLLBACK;
