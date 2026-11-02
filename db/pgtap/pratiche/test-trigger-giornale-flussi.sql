-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: trigger giornale su pratiche.flussi
--       INSERT → FLUSSO_CREATO, UPDATE stato → FLUSSO_STATO_CAMBIATO
--
-- Indice test:
-- 0) Precondizioni (provisioning + verifica)
-- 1) Setup tipo_prestazione, template_flusso, pratica
-- 2) INSERT flusso → entry FLUSSO_CREATO nel giornale
-- 3) UPDATE stato flusso → entry FLUSSO_STATO_CAMBIATO nel giornale
-- 4) Verifica dettaglio jsonb su FLUSSO_CREATO
-- 5) Verifica dettaglio jsonb su FLUSSO_STATO_CAMBIATO
-- 6) Verifica tx_id propagato nel giornale
-- 7) Cleanup
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

SELECT plan(6);
-- =========================================================
-- 0) Precondizioni: provisioning config data (idempotente)
-- =========================================================
INSERT INTO config.stati_pratiche (codice, codice_interno, descrizione, attivo)
VALUES ('BOZZA', 'BOZZA', 'Bozza', true) ON CONFLICT (codice_interno) DO NOTHING;
INSERT INTO config.stati_flussi_pratiche (codice, codice_interno, descrizione, attivo)
VALUES (
    'DA_ESEGUIRE',
    'DA_ESEGUIRE',
    'Da eseguire',
    true
  ),
  (
    'IN_CORSO',
    'IN_CORSO',
    'In corso',
    true
  ) ON CONFLICT (codice_interno) DO NOTHING;
INSERT INTO config.priorita_pratiche (
    codice,
    codice_interno,
    descrizione,
    sequenza,
    attivo
  )
VALUES ('NORMALE', 'NORMALE', 'Normale', 20, true) ON CONFLICT (codice_interno) DO NOTHING;
CREATE TEMP TABLE tmp_gf_refs AS
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
    WHERE codice_interno = 'DA_ESEGUIRE'
      AND attivo = true
    LIMIT 1
  ) AS stato_da_eseguire_id,
  (
    SELECT id
    FROM config.stati_flussi_pratiche
    WHERE codice_interno = 'IN_CORSO'
      AND attivo = true
    LIMIT 1
  ) AS stato_in_corso_id,
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
        AND stato_da_eseguire_id IS NOT NULL
        AND stato_in_corso_id IS NOT NULL
        AND priorita_normale_id IS NOT NULL
      FROM tmp_gf_refs
    ),
    '0. Precondizioni soddisfatte'
  );
-- =========================================================
-- 1) Setup tipo_prestazione, template_flusso, pratica
-- =========================================================
CREATE TEMP TABLE tmp_gf_tp AS WITH ins AS (
  INSERT INTO pratiche.tipi_prestazione (codice, codice_interno, descrizione, attivo)
  VALUES (
      'TEST_GIORN_FL',
      'TEST_GIORN_FL',
      'Tipo test giornale flussi',
      true
    ) ON CONFLICT (codice_interno) DO
  UPDATE
  SET descrizione = EXCLUDED.descrizione
  RETURNING id
)
SELECT id AS tp_id
FROM ins;
CREATE TEMP TABLE tmp_gf_tf AS WITH ins AS (
  INSERT INTO pratiche.template_flussi (tipo_prestazione_id, codice, descrizione, attivo)
  VALUES (
      (
        SELECT tp_id
        FROM tmp_gf_tp
      ),
      'TF_GIORN_FL',
      'Template test giornale flussi',
      true
    ) ON CONFLICT (definizione_id, codice) DO
  UPDATE
  SET descrizione = EXCLUDED.descrizione
  RETURNING id
)
SELECT id AS tf_id
FROM ins;
CREATE TEMP TABLE tmp_gf_pratica AS WITH ins AS (
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
        FROM tmp_gf_refs
      ),
      (
        SELECT tp_id
        FROM tmp_gf_tp
      ),
      (
        SELECT soggetto_id
        FROM tmp_gf_refs
      ),
      (
        SELECT stato_bozza_id
        FROM tmp_gf_refs
      ),
      (
        SELECT priorita_normale_id
        FROM tmp_gf_refs
      )
    )
  RETURNING id
)
SELECT id AS pratica_id
FROM ins;
-- =========================================================
-- 2) INSERT flusso → FLUSSO_CREATO
-- =========================================================
CREATE TEMP TABLE tmp_gf_flusso AS WITH ins AS (
  INSERT INTO pratiche.flussi (
      pratica_id,
      template_flusso_id,
      stato_id,
      sequenza
    )
  VALUES (
      (
        SELECT pratica_id
        FROM tmp_gf_pratica
      ),
      (
        SELECT tf_id
        FROM tmp_gf_tf
      ),
      (
        SELECT stato_da_eseguire_id
        FROM tmp_gf_refs
      ),
      1
    )
  RETURNING id
)
SELECT id AS flusso_id
FROM ins;
SELECT is(
    (
      SELECT count(*)::integer
      FROM pratiche.giornale
      WHERE pratica_id = (
          SELECT pratica_id
          FROM tmp_gf_pratica
        )
        AND flusso_id = (
          SELECT flusso_id
          FROM tmp_gf_flusso
        )
        AND azione = 'FLUSSO_CREATO'
    ),
    1,
    '1. FLUSSO_CREATO registrato nel giornale su INSERT flusso'
  );
-- =========================================================
-- 3) UPDATE stato flusso → FLUSSO_STATO_CAMBIATO
-- =========================================================
UPDATE pratiche.flussi
SET stato_id = (
    SELECT stato_in_corso_id
    FROM tmp_gf_refs
  )
WHERE id = (
    SELECT flusso_id
    FROM tmp_gf_flusso
  );
SELECT is(
    (
      SELECT count(*)::integer
      FROM pratiche.giornale
      WHERE pratica_id = (
          SELECT pratica_id
          FROM tmp_gf_pratica
        )
        AND flusso_id = (
          SELECT flusso_id
          FROM tmp_gf_flusso
        )
        AND azione = 'FLUSSO_STATO_CAMBIATO'
    ),
    1,
    '2. FLUSSO_STATO_CAMBIATO registrato nel giornale su UPDATE stato_id'
  );
-- =========================================================
-- 4) Verifica dettaglio jsonb su FLUSSO_CREATO
-- =========================================================
SELECT ok(
    (
      SELECT dettaglio ? 'template_flusso_id'
        AND dettaglio ? 'stato_id'
        AND dettaglio ? 'sequenza'
      FROM pratiche.giornale
      WHERE pratica_id = (
          SELECT pratica_id
          FROM tmp_gf_pratica
        )
        AND flusso_id = (
          SELECT flusso_id
          FROM tmp_gf_flusso
        )
        AND azione = 'FLUSSO_CREATO'
      LIMIT 1
    ), '3. Dettaglio FLUSSO_CREATO contiene template_flusso_id, stato_id, sequenza'
  );
-- =========================================================
-- 5) Verifica dettaglio jsonb su FLUSSO_STATO_CAMBIATO
-- =========================================================
SELECT ok(
    (
      SELECT dettaglio ? 'stato_precedente_id'
        AND dettaglio ? 'stato_nuovo_id'
        AND dettaglio ? 'esito'
      FROM pratiche.giornale
      WHERE pratica_id = (
          SELECT pratica_id
          FROM tmp_gf_pratica
        )
        AND flusso_id = (
          SELECT flusso_id
          FROM tmp_gf_flusso
        )
        AND azione = 'FLUSSO_STATO_CAMBIATO'
      LIMIT 1
    ), '4. Dettaglio FLUSSO_STATO_CAMBIATO contiene stato_precedente_id, stato_nuovo_id, esito'
  );
-- =========================================================
-- 6) Verifica tx_id propagato
-- =========================================================
SELECT ok(
    (
      SELECT tx_id IS NOT NULL
      FROM pratiche.giornale
      WHERE pratica_id = (
          SELECT pratica_id
          FROM tmp_gf_pratica
        )
        AND flusso_id = (
          SELECT flusso_id
          FROM tmp_gf_flusso
        )
        AND azione = 'FLUSSO_CREATO'
      LIMIT 1
    ), '5. tx_id propagato nel giornale dal flusso'
  );
-- =========================================================
-- 7) Cleanup
-- =========================================================
-- Cleanup resiliente (gestisce orfani da run precedenti falliti)
DELETE FROM pratiche.giornale
WHERE pratica_id IN (
    SELECT id
    FROM pratiche.pratiche
    WHERE tipo_prestazione_id = (
        SELECT tp_id
        FROM tmp_gf_tp
      )
  );
DELETE FROM pratiche.flussi
WHERE pratica_id IN (
    SELECT id
    FROM pratiche.pratiche
    WHERE tipo_prestazione_id = (
        SELECT tp_id
        FROM tmp_gf_tp
      )
  );
DELETE FROM pratiche.pratiche
WHERE tipo_prestazione_id = (
    SELECT tp_id
    FROM tmp_gf_tp
  );
DELETE FROM pratiche.template_flussi
WHERE tipo_prestazione_id = (
    SELECT tp_id
    FROM tmp_gf_tp
  );
DELETE FROM pratiche.tipi_prestazione
WHERE id = (
    SELECT tp_id
    FROM tmp_gf_tp
  );
SELECT *
FROM finish();

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia nulla dietro di se'. Le DELETE del cleanup restano
-- perche' dove sono un'asserzione devono girare davvero.
ROLLBACK;
