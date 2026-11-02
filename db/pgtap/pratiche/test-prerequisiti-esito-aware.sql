-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: motore prerequisiti esito-aware (B-PREREQ)
--       - pratiche.fn_check_prerequisiti_flusso filtra sull'esito
--         (template_flussi_prerequisiti.esito_richiesto)
--       - guard pratiche.trgfn_flussi_guard_esito_completato:
--         COMPLETATO => esito NOT NULL
--
-- Indice test:
-- 0) Precondizioni (provisioning + verifica)
-- 1) Setup tipo_prestazione e template_flussi (A<-B con esito POSITIVO,
--    C<-D con esito_richiesto NULL = retro-compatibile)
-- 2) Pratica di test
-- 3) Prereq B COMPLETATO esito NEGATIVO: A non soddisfatto (esito sbagliato)
-- 4) Prereq B COMPLETATO esito POSITIVO: A soddisfatto
-- 5) Retro-compat: D COMPLETATO esito NEGATIVO, esito_richiesto NULL: C soddisfatto
-- 6) Guard: INSERT flusso COMPLETATO senza esito -> throws
-- 7) Guard: UPDATE flusso a COMPLETATO senza esito -> throws
-- 8) Guard: UPDATE flusso a COMPLETATO con esito -> lives
-- 9) Cleanup
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

SELECT plan(7);

-- =========================================================
-- 0) Precondizioni: provisioning config data (idempotente)
-- =========================================================

INSERT INTO config.stati_pratiche (codice, codice_interno, descrizione, attivo)
VALUES ('BOZZA', 'BOZZA', 'Bozza', true)
ON CONFLICT (codice_interno) DO NOTHING;

INSERT INTO config.stati_flussi_pratiche (codice, codice_interno, descrizione, attivo)
VALUES
  ('DA_ESEGUIRE', 'DA_ESEGUIRE', 'Da eseguire', true),
  ('IN_CORSO',    'IN_CORSO',    'In corso',    true),
  ('COMPLETATO',  'COMPLETATO',  'Completato',  true)
ON CONFLICT (codice_interno) DO NOTHING;

INSERT INTO config.priorita_pratiche (codice, codice_interno, descrizione, sequenza, attivo)
VALUES ('NORMALE', 'NORMALE', 'Normale', 20, true)
ON CONFLICT (codice_interno) DO NOTHING;

CREATE TEMP TABLE tmp_ea_refs AS
SELECT
  script.fn_pgtap_emittente_operatore() AS emittente_id,
  (SELECT id FROM anagrafiche.soggetti ORDER BY id LIMIT 1) AS soggetto_id,
  (SELECT id FROM config.stati_pratiche WHERE codice_interno = 'BOZZA' AND attivo = true LIMIT 1) AS stato_bozza_id,
  (SELECT id FROM config.stati_flussi_pratiche WHERE codice_interno = 'DA_ESEGUIRE' AND attivo = true LIMIT 1) AS sf_da_eseguire,
  (SELECT id FROM config.stati_flussi_pratiche WHERE codice_interno = 'IN_CORSO' AND attivo = true LIMIT 1) AS sf_in_corso,
  (SELECT id FROM config.stati_flussi_pratiche WHERE codice_interno = 'COMPLETATO' AND attivo = true LIMIT 1) AS sf_completato,
  (SELECT id FROM config.priorita_pratiche WHERE codice_interno = 'NORMALE' AND attivo = true LIMIT 1) AS priorita_normale_id;

SELECT ok(
    (SELECT emittente_id IS NOT NULL AND soggetto_id IS NOT NULL
        AND stato_bozza_id IS NOT NULL AND sf_da_eseguire IS NOT NULL
        AND sf_in_corso IS NOT NULL AND sf_completato IS NOT NULL
        AND priorita_normale_id IS NOT NULL
     FROM tmp_ea_refs),
    '0. Precondizioni soddisfatte'
);

-- =========================================================
-- 1) Setup tipo_prestazione e template_flussi
-- =========================================================

CREATE TEMP TABLE tmp_ea_tp AS
WITH ins AS (
  INSERT INTO pratiche.tipi_prestazione (codice, codice_interno, descrizione, attivo)
  VALUES ('TEST_ESITO_TP', 'TEST_ESITO_TP', 'Tipo prestazione test esito-aware', true)
  ON CONFLICT (codice_interno) DO UPDATE SET descrizione = EXCLUDED.descrizione
  RETURNING id
)
SELECT id AS tp_id FROM ins;

CREATE TEMP TABLE tmp_ea_tf AS
WITH ins AS (
  -- ripetibilita='SEMPRE': il test crea piu' istanze degli stessi template
  -- nella stessa pratica (esiti diversi); il default SE_NON_POSITIVO le vieterebbe.
  INSERT INTO pratiche.template_flussi (tipo_prestazione_id, codice, descrizione, attivo, ripetibilita)
  VALUES
    ((SELECT tp_id FROM tmp_ea_tp), 'TF_EA_A', 'Template A (richiede B esito POSITIVO)', true, 'SEMPRE'),
    ((SELECT tp_id FROM tmp_ea_tp), 'TF_EA_B', 'Template B (prerequisito esito-aware)', true, 'SEMPRE'),
    ((SELECT tp_id FROM tmp_ea_tp), 'TF_EA_C', 'Template C (richiede D, esito qualsiasi)', true, 'SEMPRE'),
    ((SELECT tp_id FROM tmp_ea_tp), 'TF_EA_D', 'Template D (prerequisito retro-compat)', true, 'SEMPRE')
  ON CONFLICT (definizione_id, codice) DO UPDATE SET descrizione = EXCLUDED.descrizione, ripetibilita = EXCLUDED.ripetibilita
  RETURNING id, codice
)
SELECT
  max(id) FILTER (WHERE codice = 'TF_EA_A') AS tfa_id,
  max(id) FILTER (WHERE codice = 'TF_EA_B') AS tfb_id,
  max(id) FILTER (WHERE codice = 'TF_EA_C') AS tfc_id,
  max(id) FILTER (WHERE codice = 'TF_EA_D') AS tfd_id
FROM ins;

-- A richiede B con esito POSITIVO; C richiede D con esito_richiesto NULL (qualsiasi).
INSERT INTO pratiche.template_flussi_prerequisiti (template_flusso_id, prerequisito_id, esito_richiesto)
VALUES
  ((SELECT tfa_id FROM tmp_ea_tf), (SELECT tfb_id FROM tmp_ea_tf), 'POSITIVO'),
  ((SELECT tfc_id FROM tmp_ea_tf), (SELECT tfd_id FROM tmp_ea_tf), NULL)
ON CONFLICT (template_flusso_id, prerequisito_id) DO NOTHING;

-- =========================================================
-- 2) Pratica di test
-- =========================================================

CREATE TEMP TABLE tmp_ea_pratica AS
WITH ins AS (
  INSERT INTO pratiche.pratiche (
    emittente_fiscale_id, tipo_prestazione_id, soggetto_id, stato_id, priorita_id
  )
  VALUES (
    (SELECT emittente_id FROM tmp_ea_refs),
    (SELECT tp_id FROM tmp_ea_tp),
    (SELECT soggetto_id FROM tmp_ea_refs),
    (SELECT stato_bozza_id FROM tmp_ea_refs),
    (SELECT priorita_normale_id FROM tmp_ea_refs)
  )
  RETURNING id
)
SELECT id AS pratica_id FROM ins;

-- =========================================================
-- 3) Prereq B COMPLETATO con esito NEGATIVO: A NON soddisfatto
--    (esito_richiesto = POSITIVO)
-- =========================================================

INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id, esito)
VALUES (
  (SELECT pratica_id FROM tmp_ea_pratica),
  (SELECT tfb_id FROM tmp_ea_tf),
  (SELECT sf_completato FROM tmp_ea_refs),
  'NEGATIVO'
);

SELECT is(
    (SELECT soddisfatto
       FROM pratiche.fn_check_prerequisiti_flusso(
              (SELECT pratica_id FROM tmp_ea_pratica),
              (SELECT tfa_id FROM tmp_ea_tf)
            )
      -- ⚠️ Si dice QUALE prerequisito: la funzione ritorna una riga per
      --   prerequisito, e questo file ne configura DUE coppie
      --   (tfa->tfb con esito POSITIVO, tfc->tfd con esito NULL).
      --   Un LIMIT 1 su una riga qualsiasi poteva leggere la coppia
      --   sbagliata e asserire su un esito che non e' quello in prova.
      WHERE prerequisito_id = (SELECT tfb_id FROM tmp_ea_tf)),
    false,
    '1. Prereq COMPLETATO con esito sbagliato (NEGATIVO vs POSITIVO): non soddisfatto'
);

-- =========================================================
-- 4) Prereq B COMPLETATO con esito POSITIVO: A soddisfatto
-- =========================================================

INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id, esito)
VALUES (
  (SELECT pratica_id FROM tmp_ea_pratica),
  (SELECT tfb_id FROM tmp_ea_tf),
  (SELECT sf_completato FROM tmp_ea_refs),
  'POSITIVO'
);

SELECT is(
    (SELECT soddisfatto
       FROM pratiche.fn_check_prerequisiti_flusso(
              (SELECT pratica_id FROM tmp_ea_pratica),
              (SELECT tfa_id FROM tmp_ea_tf)
            )
      -- ⚠️ Si dice QUALE prerequisito: la funzione ritorna una riga per
      --   prerequisito, e questo file ne configura DUE coppie
      --   (tfa->tfb con esito POSITIVO, tfc->tfd con esito NULL).
      --   Un LIMIT 1 su una riga qualsiasi poteva leggere la coppia
      --   sbagliata e asserire su un esito che non e' quello in prova.
      WHERE prerequisito_id = (SELECT tfb_id FROM tmp_ea_tf)),
    true,
    '2. Prereq COMPLETATO con esito POSITIVO: soddisfatto'
);

-- =========================================================
-- 5) Retro-compat: D COMPLETATO esito NEGATIVO, esito_richiesto NULL:
--    C soddisfatto (NULL = qualsiasi esito)
-- =========================================================

INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id, esito)
VALUES (
  (SELECT pratica_id FROM tmp_ea_pratica),
  (SELECT tfd_id FROM tmp_ea_tf),
  (SELECT sf_completato FROM tmp_ea_refs),
  'NEGATIVO'
);

SELECT is(
    (SELECT soddisfatto
       FROM pratiche.fn_check_prerequisiti_flusso(
              (SELECT pratica_id FROM tmp_ea_pratica),
              (SELECT tfc_id FROM tmp_ea_tf)
            )
      -- ⚠️ Si dice QUALE prerequisito: la funzione ritorna una riga per
      --   prerequisito, e questo file ne configura DUE coppie
      --   (tfa->tfb con esito POSITIVO, tfc->tfd con esito NULL).
      --   Un LIMIT 1 su una riga qualsiasi poteva leggere la coppia
      --   sbagliata e asserire su un esito che non e' quello in prova.
      WHERE prerequisito_id = (SELECT tfd_id FROM tmp_ea_tf)),
    true,
    '3. Retro-compat: esito_richiesto NULL soddisfatto con qualsiasi esito'
);

-- =========================================================
-- 6) Guard: INSERT flusso COMPLETATO senza esito -> throws
-- =========================================================

SELECT throws_ok(
    format(
      'INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id)
       VALUES (%s, %s, %s)',
      (SELECT pratica_id FROM tmp_ea_pratica),
      (SELECT tfb_id FROM tmp_ea_tf),
      (SELECT sf_completato FROM tmp_ea_refs)),
    NULL, NULL,
    '4. Guard: INSERT flusso COMPLETATO senza esito bloccato'
);

-- =========================================================
-- 7) Guard: UPDATE flusso a COMPLETATO senza esito -> throws
--    (percorso DA_ESEGUIRE -> IN_CORSO -> COMPLETATO)
-- =========================================================

CREATE TEMP TABLE tmp_ea_flusso_upd AS
WITH ins AS (
  INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id)
  VALUES (
    (SELECT pratica_id FROM tmp_ea_pratica),
    (SELECT tfb_id FROM tmp_ea_tf),
    (SELECT sf_da_eseguire FROM tmp_ea_refs)
  )
  RETURNING id
)
SELECT id AS flusso_id FROM ins;

UPDATE pratiche.flussi
   SET stato_id = (SELECT sf_in_corso FROM tmp_ea_refs)
 WHERE id = (SELECT flusso_id FROM tmp_ea_flusso_upd);

SELECT throws_ok(
    format(
      'UPDATE pratiche.flussi SET stato_id = %s WHERE id = %s',
      (SELECT sf_completato FROM tmp_ea_refs),
      (SELECT flusso_id FROM tmp_ea_flusso_upd)),
    NULL, NULL,
    '5. Guard: UPDATE flusso a COMPLETATO senza esito bloccato'
);

-- =========================================================
-- 8) Guard: UPDATE flusso a COMPLETATO con esito -> lives
-- =========================================================

SELECT lives_ok(
    format(
      'UPDATE pratiche.flussi SET stato_id = %s, esito = ''POSITIVO'' WHERE id = %s',
      (SELECT sf_completato FROM tmp_ea_refs),
      (SELECT flusso_id FROM tmp_ea_flusso_upd)),
    '6. Guard: UPDATE flusso a COMPLETATO con esito consentito'
);

-- =========================================================
-- 9) Cleanup
-- =========================================================

DELETE FROM pratiche.giornale WHERE pratica_id IN (
  SELECT id FROM pratiche.pratiche WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_ea_tp)
);
DELETE FROM pratiche.flussi WHERE pratica_id IN (
  SELECT id FROM pratiche.pratiche WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_ea_tp)
);
DELETE FROM pratiche.pratiche WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_ea_tp);
DELETE FROM pratiche.template_flussi_prerequisiti
 WHERE template_flusso_id IN (
   SELECT id FROM pratiche.template_flussi WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_ea_tp)
 );
DELETE FROM pratiche.template_flussi WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_ea_tp);
DELETE FROM pratiche.tipi_prestazione WHERE id = (SELECT tp_id FROM tmp_ea_tp);

SELECT * FROM finish();

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia nulla dietro di se'. Le DELETE del cleanup restano
-- perche' dove sono un'asserzione devono girare davvero.
ROLLBACK;
