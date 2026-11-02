-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: macchina a stati rigida per pratiche e flussi
--       Ogni transizione ammessa passa, ogni transizione vietata solleva errore.
--
-- Indice test:
-- 0) Precondizioni (provisioning + verifica)
-- 1) Setup pratica in stato BOZZA
-- 2) Pratica: BOZZA → APERTA (ammessa)
-- 3) Pratica: APERTA → CHIUSA (ammessa)
-- 4) Pratica: CHIUSA → APERTA (vietata, terminale)
-- 5) Pratica: BOZZA → CHIUSA (vietata, non configurata)
-- 6) Pratica: BOZZA → ANNULLATA (ammessa)
-- 7) Pratica: APERTA → SOSPESA (ammessa)
-- 8) Pratica: SOSPESA → APERTA (ammessa)
-- 9) Flusso: DA_ESEGUIRE → IN_CORSO (ammessa)
-- 10) Flusso: IN_CORSO → COMPLETATO (ammessa)
-- 11) Flusso: COMPLETATO → DA_ESEGUIRE (vietata, terminale)
-- 12) Flusso: DA_ESEGUIRE → COMPLETATO (vietata, non configurata)
-- 13) Flusso: IN_CORSO → SOSPESO (ammessa)
-- 14) Flusso: SOSPESO → IN_CORSO (ammessa)
-- 15) Flusso: SOSPESO → DA_ESEGUIRE (ammessa)
-- 16) Cleanup
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

SELECT plan(16);

-- =========================================================
-- 0) Precondizioni
-- =========================================================
CREATE TEMP TABLE tmp_tr_refs AS
SELECT
  script.fn_pgtap_emittente_operatore() AS emittente_id,
  (SELECT id FROM anagrafiche.soggetti ORDER BY id LIMIT 1) AS soggetto_id,
  (SELECT id FROM config.stati_pratiche WHERE codice_interno = 'BOZZA') AS st_bozza,
  (SELECT id FROM config.stati_pratiche WHERE codice_interno = 'APERTA') AS st_aperta,
  (SELECT id FROM config.stati_pratiche WHERE codice_interno = 'SOSPESA') AS st_sospesa,
  (SELECT id FROM config.stati_pratiche WHERE codice_interno = 'CHIUSA') AS st_chiusa,
  (SELECT id FROM config.stati_pratiche WHERE codice_interno = 'ANNULLATA') AS st_annullata,
  (SELECT id FROM config.stati_flussi_pratiche WHERE codice_interno = 'DA_ESEGUIRE') AS sf_da_eseguire,
  (SELECT id FROM config.stati_flussi_pratiche WHERE codice_interno = 'IN_CORSO') AS sf_in_corso,
  (SELECT id FROM config.stati_flussi_pratiche WHERE codice_interno = 'COMPLETATO') AS sf_completato,
  (SELECT id FROM config.stati_flussi_pratiche WHERE codice_interno = 'SOSPESO') AS sf_sospeso,
  (SELECT id FROM config.stati_flussi_pratiche WHERE codice_interno = 'ANNULLATO') AS sf_annullato,
  (SELECT id FROM config.priorita_pratiche WHERE codice_interno = 'NORMALE') AS priorita_id;

SELECT ok(
  (SELECT st_bozza IS NOT NULL AND st_aperta IS NOT NULL AND st_chiusa IS NOT NULL
      AND sf_da_eseguire IS NOT NULL AND sf_in_corso IS NOT NULL AND sf_completato IS NOT NULL
      AND emittente_id IS NOT NULL AND priorita_id IS NOT NULL
   FROM tmp_tr_refs),
  '0. Precondizioni soddisfatte'
);

-- =========================================================
-- 1) Setup tipo_prestazione e pratica
-- =========================================================
CREATE TEMP TABLE tmp_tr_tp AS
WITH ins AS (
  INSERT INTO pratiche.tipi_prestazione (codice, codice_interno, descrizione, attivo)
  VALUES ('TEST_TRANS', 'TEST_TRANS', 'Tipo test transizioni', true)
  ON CONFLICT (codice_interno) DO UPDATE SET descrizione = EXCLUDED.descrizione
  RETURNING id
)
SELECT id AS tp_id FROM ins;

-- Pratica per test transizioni pratiche
CREATE TEMP TABLE tmp_tr_pratica AS
WITH ins AS (
  INSERT INTO pratiche.pratiche (emittente_fiscale_id, tipo_prestazione_id, soggetto_id, stato_id, priorita_id)
  VALUES (
    (SELECT emittente_id FROM tmp_tr_refs),
    (SELECT tp_id FROM tmp_tr_tp),
    (SELECT soggetto_id FROM tmp_tr_refs),
    (SELECT st_bozza FROM tmp_tr_refs),
    (SELECT priorita_id FROM tmp_tr_refs)
  )
  RETURNING id
)
SELECT id AS pratica_id FROM ins;

SELECT ok(
  (SELECT pratica_id IS NOT NULL FROM tmp_tr_pratica),
  '1. Setup completato: pratica in stato BOZZA'
);

-- =========================================================
-- 2) Pratica: BOZZA → APERTA (ammessa)
-- =========================================================
SELECT lives_ok(
  format('UPDATE pratiche.pratiche SET stato_id = %s WHERE id = %s',
    (SELECT st_aperta FROM tmp_tr_refs),
    (SELECT pratica_id FROM tmp_tr_pratica)),
  '2. Pratica: BOZZA -> APERTA ammessa'
);

-- =========================================================
-- 3) Pratica: APERTA → CHIUSA (ammessa)
-- =========================================================
SELECT lives_ok(
  format('UPDATE pratiche.pratiche SET stato_id = %s WHERE id = %s',
    (SELECT st_chiusa FROM tmp_tr_refs),
    (SELECT pratica_id FROM tmp_tr_pratica)),
  '3. Pratica: APERTA -> CHIUSA ammessa'
);

-- =========================================================
-- 4) Pratica: CHIUSA → APERTA (vietata, terminale)
-- =========================================================
SELECT throws_ok(
  format('UPDATE pratiche.pratiche SET stato_id = %s WHERE id = %s',
    (SELECT st_aperta FROM tmp_tr_refs),
    (SELECT pratica_id FROM tmp_tr_pratica)),
  NULL, NULL,
  '4. Pratica: CHIUSA -> APERTA vietata (terminale)'
);

-- =========================================================
-- 5) Nuova pratica per test BOZZA → CHIUSA (vietata)
-- =========================================================
CREATE TEMP TABLE tmp_tr_pratica2 AS
WITH ins AS (
  INSERT INTO pratiche.pratiche (emittente_fiscale_id, tipo_prestazione_id, soggetto_id, stato_id, priorita_id)
  VALUES (
    (SELECT emittente_id FROM tmp_tr_refs),
    (SELECT tp_id FROM tmp_tr_tp),
    (SELECT soggetto_id FROM tmp_tr_refs),
    (SELECT st_bozza FROM tmp_tr_refs),
    (SELECT priorita_id FROM tmp_tr_refs)
  )
  RETURNING id
)
SELECT id AS pratica_id FROM ins;

SELECT throws_ok(
  format('UPDATE pratiche.pratiche SET stato_id = %s WHERE id = %s',
    (SELECT st_chiusa FROM tmp_tr_refs),
    (SELECT pratica_id FROM tmp_tr_pratica2)),
  NULL, NULL,
  '5. Pratica: BOZZA -> CHIUSA vietata (non configurata)'
);

-- =========================================================
-- 6) Pratica: BOZZA → ANNULLATA (ammessa)
-- =========================================================
SELECT lives_ok(
  format('UPDATE pratiche.pratiche SET stato_id = %s WHERE id = %s',
    (SELECT st_annullata FROM tmp_tr_refs),
    (SELECT pratica_id FROM tmp_tr_pratica2)),
  '6. Pratica: BOZZA -> ANNULLATA ammessa'
);

-- =========================================================
-- 7-8) Pratica: APERTA → SOSPESA → APERTA
-- =========================================================
CREATE TEMP TABLE tmp_tr_pratica3 AS
WITH ins AS (
  INSERT INTO pratiche.pratiche (emittente_fiscale_id, tipo_prestazione_id, soggetto_id, stato_id, priorita_id)
  VALUES (
    (SELECT emittente_id FROM tmp_tr_refs),
    (SELECT tp_id FROM tmp_tr_tp),
    (SELECT soggetto_id FROM tmp_tr_refs),
    (SELECT st_bozza FROM tmp_tr_refs),
    (SELECT priorita_id FROM tmp_tr_refs)
  )
  RETURNING id
)
SELECT id AS pratica_id FROM ins;

-- BOZZA → APERTA
UPDATE pratiche.pratiche
SET stato_id = (SELECT st_aperta FROM tmp_tr_refs)
WHERE id = (SELECT pratica_id FROM tmp_tr_pratica3);

SELECT lives_ok(
  format('UPDATE pratiche.pratiche SET stato_id = %s WHERE id = %s',
    (SELECT st_sospesa FROM tmp_tr_refs),
    (SELECT pratica_id FROM tmp_tr_pratica3)),
  '7. Pratica: APERTA -> SOSPESA ammessa'
);

SELECT lives_ok(
  format('UPDATE pratiche.pratiche SET stato_id = %s WHERE id = %s',
    (SELECT st_aperta FROM tmp_tr_refs),
    (SELECT pratica_id FROM tmp_tr_pratica3)),
  '8. Pratica: SOSPESA -> APERTA ammessa'
);

-- =========================================================
-- 9-15) Test transizioni flussi
-- =========================================================
-- Crea una pratica APERTA con un flusso per testare le transizioni flussi
CREATE TEMP TABLE tmp_tr_pratica4 AS
WITH ins AS (
  INSERT INTO pratiche.pratiche (emittente_fiscale_id, tipo_prestazione_id, soggetto_id, stato_id, priorita_id)
  VALUES (
    (SELECT emittente_id FROM tmp_tr_refs),
    (SELECT tp_id FROM tmp_tr_tp),
    (SELECT soggetto_id FROM tmp_tr_refs),
    (SELECT st_bozza FROM tmp_tr_refs),
    (SELECT priorita_id FROM tmp_tr_refs)
  )
  RETURNING id
)
SELECT id AS pratica_id FROM ins;

UPDATE pratiche.pratiche
SET stato_id = (SELECT st_aperta FROM tmp_tr_refs)
WHERE id = (SELECT pratica_id FROM tmp_tr_pratica4);

-- Template per i flussi di test (template_flusso_id e' NOT NULL dal 20260614-09;
-- ripetibilita SEMPRE perche' il test crea due istanze nella stessa pratica).
CREATE TEMP TABLE tmp_tr_tf AS
WITH ins AS (
  INSERT INTO pratiche.template_flussi (tipo_prestazione_id, codice, descrizione, sequenza, obbligatorio, attivo, ripetibilita)
  VALUES ((SELECT tp_id FROM tmp_tr_tp), 'TR_STEP', 'Step transizioni', 1, false, true, 'SEMPRE')
  ON CONFLICT (definizione_id, codice) DO UPDATE SET ripetibilita = EXCLUDED.ripetibilita
  RETURNING id
)
SELECT id AS tf_id FROM ins;

-- Flusso in DA_ESEGUIRE
CREATE TEMP TABLE tmp_tr_flusso1 AS
WITH ins AS (
  INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id)
  VALUES (
    (SELECT pratica_id FROM tmp_tr_pratica4),
    (SELECT tf_id FROM tmp_tr_tf),
    (SELECT sf_da_eseguire FROM tmp_tr_refs)
  )
  RETURNING id
)
SELECT id AS flusso_id FROM ins;

-- 9) DA_ESEGUIRE → IN_CORSO (ammessa)
SELECT lives_ok(
  format('UPDATE pratiche.flussi SET stato_id = %s WHERE id = %s',
    (SELECT sf_in_corso FROM tmp_tr_refs),
    (SELECT flusso_id FROM tmp_tr_flusso1)),
  '9. Flusso: DA_ESEGUIRE -> IN_CORSO ammessa'
);

-- 10) IN_CORSO → COMPLETATO (ammessa) — esito obbligatorio per COMPLETATO
SELECT lives_ok(
  format('UPDATE pratiche.flussi SET stato_id = %s, esito = ''POSITIVO'', data_fine = now() WHERE id = %s',
    (SELECT sf_completato FROM tmp_tr_refs),
    (SELECT flusso_id FROM tmp_tr_flusso1)),
  '10. Flusso: IN_CORSO -> COMPLETATO ammessa'
);

-- 11) COMPLETATO → DA_ESEGUIRE (vietata, terminale)
SELECT throws_ok(
  format('UPDATE pratiche.flussi SET stato_id = %s WHERE id = %s',
    (SELECT sf_da_eseguire FROM tmp_tr_refs),
    (SELECT flusso_id FROM tmp_tr_flusso1)),
  NULL, NULL,
  '11. Flusso: COMPLETATO -> DA_ESEGUIRE vietata (terminale)'
);

-- Nuovo flusso per test DA_ESEGUIRE → COMPLETATO
CREATE TEMP TABLE tmp_tr_flusso2 AS
WITH ins AS (
  INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id)
  VALUES (
    (SELECT pratica_id FROM tmp_tr_pratica4),
    (SELECT tf_id FROM tmp_tr_tf),
    (SELECT sf_da_eseguire FROM tmp_tr_refs)
  )
  RETURNING id
)
SELECT id AS flusso_id FROM ins;

-- 12) DA_ESEGUIRE → COMPLETATO (vietata) — esito valorizzato cosi' a fallire
--     e' il guard di transizione (intento del test), non quello di esito.
SELECT throws_ok(
  format('UPDATE pratiche.flussi SET stato_id = %s, esito = ''POSITIVO'' WHERE id = %s',
    (SELECT sf_completato FROM tmp_tr_refs),
    (SELECT flusso_id FROM tmp_tr_flusso2)),
  NULL, NULL,
  '12. Flusso: DA_ESEGUIRE -> COMPLETATO vietata (non configurata)'
);

-- 13) IN_CORSO → SOSPESO (ammessa)
UPDATE pratiche.flussi
SET stato_id = (SELECT sf_in_corso FROM tmp_tr_refs)
WHERE id = (SELECT flusso_id FROM tmp_tr_flusso2);

SELECT lives_ok(
  format('UPDATE pratiche.flussi SET stato_id = %s WHERE id = %s',
    (SELECT sf_sospeso FROM tmp_tr_refs),
    (SELECT flusso_id FROM tmp_tr_flusso2)),
  '13. Flusso: IN_CORSO -> SOSPESO ammessa'
);

-- 14) SOSPESO → IN_CORSO (ammessa)
SELECT lives_ok(
  format('UPDATE pratiche.flussi SET stato_id = %s WHERE id = %s',
    (SELECT sf_in_corso FROM tmp_tr_refs),
    (SELECT flusso_id FROM tmp_tr_flusso2)),
  '14. Flusso: SOSPESO -> IN_CORSO ammessa'
);

-- Rimetti in SOSPESO per testare SOSPESO → DA_ESEGUIRE
UPDATE pratiche.flussi
SET stato_id = (SELECT sf_sospeso FROM tmp_tr_refs)
WHERE id = (SELECT flusso_id FROM tmp_tr_flusso2);

-- 15) SOSPESO → DA_ESEGUIRE (ammessa)
SELECT lives_ok(
  format('UPDATE pratiche.flussi SET stato_id = %s WHERE id = %s',
    (SELECT sf_da_eseguire FROM tmp_tr_refs),
    (SELECT flusso_id FROM tmp_tr_flusso2)),
  '15. Flusso: SOSPESO -> DA_ESEGUIRE ammessa'
);

-- =========================================================
-- 16) Cleanup
-- =========================================================
DELETE FROM pratiche.giornale
WHERE pratica_id IN (
  SELECT id FROM pratiche.pratiche
  WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_tr_tp)
);
DELETE FROM pratiche.flussi
WHERE pratica_id IN (
  SELECT id FROM pratiche.pratiche
  WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_tr_tp)
);
DELETE FROM pratiche.pratiche
WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_tr_tp);
DELETE FROM pratiche.template_flussi
WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_tr_tp);
DELETE FROM pratiche.tipi_prestazione
WHERE id = (SELECT tp_id FROM tmp_tr_tp);

SELECT * FROM finish();

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia nulla dietro di se'. Le DELETE del cleanup restano
-- perche' dove sono un'asserzione devono girare davvero.
ROLLBACK;
