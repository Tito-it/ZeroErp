-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: chiusura pratica guidata dal workflow
--       (trgfn_flussi_autochiusura_pratica + trgfn_flussi_guard_chiusura_prematura
--        + template_flussi.chiude_pratica + fn_check_pratica_chiudibile).
--
-- Modello misto:
--   A) tipo SENZA flusso di chiusura ma con obbligatori -> auto-chiusura quando
--      non restano obbligatori bloccanti;
--   B) tipo CON flusso di chiusura -> chiude al completamento di quel flusso,
--      ammesso solo a percorso obbligatorio concluso (guard pre-completamento);
--   C) auto-chiusura solo da APERTA (non SOSPESA);
--   D) gate: tipo senza obbligatori e senza flusso di chiusura -> non si chiude.
--
-- Indice test:
-- 0) Precondizioni
-- 1) Setup (4 tipi prestazione + pratiche)
-- 2) [A] completato 1 di 2 obbligatori -> pratica resta APERTA (criterio 2)
-- 3) [A] completato l'ultimo obbligatorio -> pratica CHIUSA (criterio 1)
-- 4) [A] la chiusura automatica e' registrata nel giornale (criterio 5)
-- 5) [B] completamento flusso di chiusura con altro obbligatorio pendente -> throws (criterio 6)
-- 6) [B] completato l'altro obbligatorio (non e' il flusso di chiusura) -> resta APERTA
-- 7) [B] completato il flusso di chiusura -> pratica CHIUSA (criterio 3)
-- 8) [C] pratica SOSPESA: completato l'obbligatorio -> resta SOSPESA (criterio 4)
-- 9) [D] gate: tipo senza obbligatori -> completato un flusso -> resta APERTA
-- 10) Cleanup
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

SELECT plan(11);

-- =========================================================
-- 0) Precondizioni
-- =========================================================
INSERT INTO config.stati_pratiche (codice, codice_interno, descrizione, attivo)
VALUES ('BOZZA','BOZZA','Bozza',true),('APERTA','APERTA','Aperta',true),
       ('SOSPESA','SOSPESA','Sospesa',true),('CHIUSA','CHIUSA','Chiusa',true)
ON CONFLICT (codice_interno) DO NOTHING;
INSERT INTO config.stati_flussi_pratiche (codice, codice_interno, descrizione, attivo)
VALUES ('DA_ESEGUIRE','DA_ESEGUIRE','Da eseguire',true),
       ('IN_CORSO','IN_CORSO','In corso',true),
       ('COMPLETATO','COMPLETATO','Completato',true)
ON CONFLICT (codice_interno) DO NOTHING;
INSERT INTO config.priorita_pratiche (codice, codice_interno, descrizione, sequenza, attivo)
VALUES ('NORMALE','NORMALE','Normale',20,true) ON CONFLICT (codice_interno) DO NOTHING;

CREATE TEMP TABLE tmp_ac_refs AS
SELECT
  script.fn_pgtap_emittente_operatore() AS emittente_id,
  (SELECT id FROM anagrafiche.soggetti ORDER BY id LIMIT 1) AS soggetto_id,
  (SELECT id FROM config.stati_pratiche WHERE codice_interno='APERTA') AS st_aperta,
  (SELECT id FROM config.stati_pratiche WHERE codice_interno='SOSPESA') AS st_sospesa,
  (SELECT id FROM config.stati_pratiche WHERE codice_interno='CHIUSA') AS st_chiusa,
  (SELECT id FROM config.stati_flussi_pratiche WHERE codice_interno='DA_ESEGUIRE') AS sf_da,
  (SELECT id FROM config.stati_flussi_pratiche WHERE codice_interno='IN_CORSO') AS sf_in,
  (SELECT id FROM config.stati_flussi_pratiche WHERE codice_interno='COMPLETATO') AS sf_done,
  (SELECT id FROM config.priorita_pratiche WHERE codice_interno='NORMALE') AS priorita_id;

SELECT ok(
  (SELECT emittente_id IS NOT NULL AND st_aperta IS NOT NULL AND st_sospesa IS NOT NULL
      AND st_chiusa IS NOT NULL AND sf_da IS NOT NULL AND sf_done IS NOT NULL
      AND priorita_id IS NOT NULL FROM tmp_ac_refs),
  '0. Precondizioni soddisfatte'
);

-- =========================================================
-- 1) Setup: 4 tipi prestazione + template + pratiche
-- =========================================================
-- Tipo A (auto): 2 obbligatori, nessun flusso di chiusura.
CREATE TEMP TABLE tmp_ac_tp_a AS WITH ins AS (
  INSERT INTO pratiche.tipi_prestazione (codice, codice_interno, descrizione, attivo)
  VALUES ('TEST_AC_AUTO','TEST_AC_AUTO','Auto-chiusura',true)
  ON CONFLICT (codice_interno) DO UPDATE SET descrizione=EXCLUDED.descrizione RETURNING id)
SELECT id AS tp_id FROM ins;
CREATE TEMP TABLE tmp_ac_tf_a AS WITH ins AS (
  INSERT INTO pratiche.template_flussi (tipo_prestazione_id, codice, descrizione, sequenza, obbligatorio, attivo)
  VALUES ((SELECT tp_id FROM tmp_ac_tp_a),'AC_STEP1','Step 1',10,true,true),
         ((SELECT tp_id FROM tmp_ac_tp_a),'AC_STEP2','Step 2',20,true,true)
  ON CONFLICT (definizione_id, codice) DO UPDATE SET descrizione=EXCLUDED.descrizione RETURNING id, codice)
SELECT max(id) FILTER (WHERE codice='AC_STEP1') AS tf1, max(id) FILTER (WHERE codice='AC_STEP2') AS tf2 FROM ins;

-- Tipo B (flusso di chiusura): WORK obbligatorio + CLOSE chiude_pratica (obbligatorio per D4).
CREATE TEMP TABLE tmp_ac_tp_b AS WITH ins AS (
  INSERT INTO pratiche.tipi_prestazione (codice, codice_interno, descrizione, attivo)
  VALUES ('TEST_AC_CLOSE','TEST_AC_CLOSE','Flusso di chiusura',true)
  ON CONFLICT (codice_interno) DO UPDATE SET descrizione=EXCLUDED.descrizione RETURNING id)
SELECT id AS tp_id FROM ins;
CREATE TEMP TABLE tmp_ac_tf_b AS WITH ins AS (
  INSERT INTO pratiche.template_flussi (tipo_prestazione_id, codice, descrizione, sequenza, obbligatorio, chiude_pratica, attivo)
  VALUES ((SELECT tp_id FROM tmp_ac_tp_b),'AC_WORK','Lavoro',10,true,false,true),
         ((SELECT tp_id FROM tmp_ac_tp_b),'AC_CLOSE','Chiusura',20,true,true,true)
  ON CONFLICT (definizione_id, codice) DO UPDATE SET descrizione=EXCLUDED.descrizione RETURNING id, codice)
SELECT max(id) FILTER (WHERE codice='AC_WORK') AS tf_work, max(id) FILTER (WHERE codice='AC_CLOSE') AS tf_close FROM ins;

-- Tipo C (sospesa): 1 obbligatorio.
CREATE TEMP TABLE tmp_ac_tp_c AS WITH ins AS (
  INSERT INTO pratiche.tipi_prestazione (codice, codice_interno, descrizione, attivo)
  VALUES ('TEST_AC_SOSP','TEST_AC_SOSP','Sospesa',true)
  ON CONFLICT (codice_interno) DO UPDATE SET descrizione=EXCLUDED.descrizione RETURNING id)
SELECT id AS tp_id FROM ins;
CREATE TEMP TABLE tmp_ac_tf_c AS WITH ins AS (
  INSERT INTO pratiche.template_flussi (tipo_prestazione_id, codice, descrizione, sequenza, obbligatorio, attivo)
  VALUES ((SELECT tp_id FROM tmp_ac_tp_c),'AC_SOSP_STEP','Step',10,true,true)
  ON CONFLICT (definizione_id, codice) DO UPDATE SET descrizione=EXCLUDED.descrizione RETURNING id)
SELECT id AS tf_id FROM ins;

-- Tipo D (bare): nessun obbligatorio, nessun flusso di chiusura.
CREATE TEMP TABLE tmp_ac_tp_d AS WITH ins AS (
  INSERT INTO pratiche.tipi_prestazione (codice, codice_interno, descrizione, attivo)
  VALUES ('TEST_AC_BARE','TEST_AC_BARE','Senza obbligatori',true)
  ON CONFLICT (codice_interno) DO UPDATE SET descrizione=EXCLUDED.descrizione RETURNING id)
SELECT id AS tp_id FROM ins;
CREATE TEMP TABLE tmp_ac_tf_d AS WITH ins AS (
  INSERT INTO pratiche.template_flussi (tipo_prestazione_id, codice, descrizione, sequenza, obbligatorio, attivo)
  VALUES ((SELECT tp_id FROM tmp_ac_tp_d),'AC_BARE_STEP','Step',10,false,true)
  ON CONFLICT (definizione_id, codice) DO UPDATE SET descrizione=EXCLUDED.descrizione RETURNING id)
SELECT id AS tf_id FROM ins;

-- Pratiche (tutte create APERTA direttamente)
CREATE TEMP TABLE tmp_ac_pa AS WITH ins AS (
  INSERT INTO pratiche.pratiche (emittente_fiscale_id, tipo_prestazione_id, soggetto_id, stato_id, priorita_id)
  VALUES ((SELECT emittente_id FROM tmp_ac_refs),(SELECT tp_id FROM tmp_ac_tp_a),
          (SELECT soggetto_id FROM tmp_ac_refs),(SELECT st_aperta FROM tmp_ac_refs),
          (SELECT priorita_id FROM tmp_ac_refs)) RETURNING id)
SELECT id AS pratica_id FROM ins;
CREATE TEMP TABLE tmp_ac_pb AS WITH ins AS (
  INSERT INTO pratiche.pratiche (emittente_fiscale_id, tipo_prestazione_id, soggetto_id, stato_id, priorita_id)
  VALUES ((SELECT emittente_id FROM tmp_ac_refs),(SELECT tp_id FROM tmp_ac_tp_b),
          (SELECT soggetto_id FROM tmp_ac_refs),(SELECT st_aperta FROM tmp_ac_refs),
          (SELECT priorita_id FROM tmp_ac_refs)) RETURNING id)
SELECT id AS pratica_id FROM ins;
CREATE TEMP TABLE tmp_ac_pc AS WITH ins AS (
  INSERT INTO pratiche.pratiche (emittente_fiscale_id, tipo_prestazione_id, soggetto_id, stato_id, priorita_id)
  VALUES ((SELECT emittente_id FROM tmp_ac_refs),(SELECT tp_id FROM tmp_ac_tp_c),
          (SELECT soggetto_id FROM tmp_ac_refs),(SELECT st_aperta FROM tmp_ac_refs),
          (SELECT priorita_id FROM tmp_ac_refs)) RETURNING id)
SELECT id AS pratica_id FROM ins;
CREATE TEMP TABLE tmp_ac_pd AS WITH ins AS (
  INSERT INTO pratiche.pratiche (emittente_fiscale_id, tipo_prestazione_id, soggetto_id, stato_id, priorita_id)
  VALUES ((SELECT emittente_id FROM tmp_ac_refs),(SELECT tp_id FROM tmp_ac_tp_d),
          (SELECT soggetto_id FROM tmp_ac_refs),(SELECT st_aperta FROM tmp_ac_refs),
          (SELECT priorita_id FROM tmp_ac_refs)) RETURNING id)
SELECT id AS pratica_id FROM ins;

-- Pratica C -> SOSPESA (APERTA -> SOSPESA ammessa dalla matrice)
UPDATE pratiche.pratiche SET stato_id=(SELECT st_sospesa FROM tmp_ac_refs)
 WHERE id=(SELECT pratica_id FROM tmp_ac_pc);

SELECT ok(
  (SELECT pratica_id IS NOT NULL FROM tmp_ac_pa)
  AND (SELECT pratica_id IS NOT NULL FROM tmp_ac_pb)
  AND (SELECT pratica_id IS NOT NULL FROM tmp_ac_pc)
  AND (SELECT pratica_id IS NOT NULL FROM tmp_ac_pd),
  '1. Setup completato: 4 tipi + 4 pratiche'
);

-- =========================================================
-- 2) [A] completa STEP1 (1 di 2 obbligatori) -> pratica resta APERTA
-- =========================================================
INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id, sequenza)
VALUES ((SELECT pratica_id FROM tmp_ac_pa),(SELECT tf1 FROM tmp_ac_tf_a),(SELECT sf_da FROM tmp_ac_refs),10),
       ((SELECT pratica_id FROM tmp_ac_pa),(SELECT tf2 FROM tmp_ac_tf_a),(SELECT sf_da FROM tmp_ac_refs),20);

UPDATE pratiche.flussi SET stato_id=(SELECT sf_in FROM tmp_ac_refs)
 WHERE pratica_id=(SELECT pratica_id FROM tmp_ac_pa) AND template_flusso_id=(SELECT tf1 FROM tmp_ac_tf_a);
UPDATE pratiche.flussi SET stato_id=(SELECT sf_done FROM tmp_ac_refs), esito='POSITIVO'
 WHERE pratica_id=(SELECT pratica_id FROM tmp_ac_pa) AND template_flusso_id=(SELECT tf1 FROM tmp_ac_tf_a);

SELECT is(
  (SELECT sp.codice_interno FROM pratiche.pratiche p JOIN config.stati_pratiche sp ON sp.id=p.stato_id
    WHERE p.id=(SELECT pratica_id FROM tmp_ac_pa)),
  'APERTA',
  '2. [A] completato 1 di 2 obbligatori: pratica resta APERTA'
);

-- =========================================================
-- 3) [A] completa STEP2 (ultimo obbligatorio) -> pratica CHIUSA
-- =========================================================
UPDATE pratiche.flussi SET stato_id=(SELECT sf_in FROM tmp_ac_refs)
 WHERE pratica_id=(SELECT pratica_id FROM tmp_ac_pa) AND template_flusso_id=(SELECT tf2 FROM tmp_ac_tf_a);
UPDATE pratiche.flussi SET stato_id=(SELECT sf_done FROM tmp_ac_refs), esito='POSITIVO'
 WHERE pratica_id=(SELECT pratica_id FROM tmp_ac_pa) AND template_flusso_id=(SELECT tf2 FROM tmp_ac_tf_a);

SELECT is(
  (SELECT sp.codice_interno FROM pratiche.pratiche p JOIN config.stati_pratiche sp ON sp.id=p.stato_id
    WHERE p.id=(SELECT pratica_id FROM tmp_ac_pa)),
  'CHIUSA',
  '3. [A] completato l''ultimo obbligatorio: auto-chiusura -> CHIUSA'
);

-- =========================================================
-- 4) [A] la chiusura automatica e' registrata nel giornale
-- =========================================================
SELECT ok(
  EXISTS (
    SELECT 1 FROM pratiche.giornale g
     WHERE g.pratica_id=(SELECT pratica_id FROM tmp_ac_pa)
       AND g.azione='STATO_CAMBIATO'
       AND (g.dettaglio->>'stato_nuovo_id')::int = (SELECT st_chiusa FROM tmp_ac_refs)
  ),
  '4. [A] chiusura automatica registrata nel giornale (STATO_CAMBIATO -> CHIUSA)'
);

-- =========================================================
-- 5) [B] completamento flusso di chiusura con WORK pendente -> throws
-- =========================================================
INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id, sequenza)
VALUES ((SELECT pratica_id FROM tmp_ac_pb),(SELECT tf_work FROM tmp_ac_tf_b),(SELECT sf_da FROM tmp_ac_refs),10),
       ((SELECT pratica_id FROM tmp_ac_pb),(SELECT tf_close FROM tmp_ac_tf_b),(SELECT sf_da FROM tmp_ac_refs),20);

-- Porta CLOSE a IN_CORSO (consentito: il guard scatta solo verso COMPLETATO)
UPDATE pratiche.flussi SET stato_id=(SELECT sf_in FROM tmp_ac_refs)
 WHERE pratica_id=(SELECT pratica_id FROM tmp_ac_pb) AND template_flusso_id=(SELECT tf_close FROM tmp_ac_tf_b);

SELECT throws_ok(
  format('UPDATE pratiche.flussi SET stato_id=%s, esito=''POSITIVO'' WHERE pratica_id=%s AND template_flusso_id=%s',
    (SELECT sf_done FROM tmp_ac_refs),
    (SELECT pratica_id FROM tmp_ac_pb),
    (SELECT tf_close FROM tmp_ac_tf_b)),
  NULL, NULL,
  '5. [B] flusso di chiusura completato con altro obbligatorio pendente: bloccato'
);

-- =========================================================
-- 6) [B] completa WORK (non e' il flusso di chiusura) -> resta APERTA
-- =========================================================
UPDATE pratiche.flussi SET stato_id=(SELECT sf_in FROM tmp_ac_refs)
 WHERE pratica_id=(SELECT pratica_id FROM tmp_ac_pb) AND template_flusso_id=(SELECT tf_work FROM tmp_ac_tf_b);
UPDATE pratiche.flussi SET stato_id=(SELECT sf_done FROM tmp_ac_refs), esito='POSITIVO'
 WHERE pratica_id=(SELECT pratica_id FROM tmp_ac_pb) AND template_flusso_id=(SELECT tf_work FROM tmp_ac_tf_b);

SELECT is(
  (SELECT sp.codice_interno FROM pratiche.pratiche p JOIN config.stati_pratiche sp ON sp.id=p.stato_id
    WHERE p.id=(SELECT pratica_id FROM tmp_ac_pb)),
  'APERTA',
  '6. [B] completato WORK (non chiusura): pratica resta APERTA'
);

-- =========================================================
-- 7) [B] completa CLOSE (WORK ora concluso) -> pratica CHIUSA
-- =========================================================
-- CLOSE e' gia' IN_CORSO (dal test 5); ora il completamento e' ammesso.
UPDATE pratiche.flussi SET stato_id=(SELECT sf_done FROM tmp_ac_refs), esito='POSITIVO'
 WHERE pratica_id=(SELECT pratica_id FROM tmp_ac_pb) AND template_flusso_id=(SELECT tf_close FROM tmp_ac_tf_b);

SELECT is(
  (SELECT sp.codice_interno FROM pratiche.pratiche p JOIN config.stati_pratiche sp ON sp.id=p.stato_id
    WHERE p.id=(SELECT pratica_id FROM tmp_ac_pb)),
  'CHIUSA',
  '7. [B] completato il flusso di chiusura: auto-chiusura -> CHIUSA'
);

-- =========================================================
-- 8) [C] pratica SOSPESA: completa l'obbligatorio -> resta SOSPESA
-- =========================================================
INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id, sequenza)
VALUES ((SELECT pratica_id FROM tmp_ac_pc),(SELECT tf_id FROM tmp_ac_tf_c),(SELECT sf_da FROM tmp_ac_refs),10);
UPDATE pratiche.flussi SET stato_id=(SELECT sf_in FROM tmp_ac_refs)
 WHERE pratica_id=(SELECT pratica_id FROM tmp_ac_pc) AND template_flusso_id=(SELECT tf_id FROM tmp_ac_tf_c);
UPDATE pratiche.flussi SET stato_id=(SELECT sf_done FROM tmp_ac_refs), esito='POSITIVO'
 WHERE pratica_id=(SELECT pratica_id FROM tmp_ac_pc) AND template_flusso_id=(SELECT tf_id FROM tmp_ac_tf_c);

SELECT is(
  (SELECT sp.codice_interno FROM pratiche.pratiche p JOIN config.stati_pratiche sp ON sp.id=p.stato_id
    WHERE p.id=(SELECT pratica_id FROM tmp_ac_pc)),
  'SOSPESA',
  '8. [C] pratica SOSPESA: completato l''obbligatorio non si auto-chiude'
);

-- =========================================================
-- 9) [D] gate: tipo senza obbligatori -> completa un flusso -> resta APERTA
-- =========================================================
INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id, sequenza)
VALUES ((SELECT pratica_id FROM tmp_ac_pd),(SELECT tf_id FROM tmp_ac_tf_d),(SELECT sf_da FROM tmp_ac_refs),10);
UPDATE pratiche.flussi SET stato_id=(SELECT sf_in FROM tmp_ac_refs)
 WHERE pratica_id=(SELECT pratica_id FROM tmp_ac_pd) AND template_flusso_id=(SELECT tf_id FROM tmp_ac_tf_d);
UPDATE pratiche.flussi SET stato_id=(SELECT sf_done FROM tmp_ac_refs), esito='POSITIVO'
 WHERE pratica_id=(SELECT pratica_id FROM tmp_ac_pd) AND template_flusso_id=(SELECT tf_id FROM tmp_ac_tf_d);

SELECT is(
  (SELECT sp.codice_interno FROM pratiche.pratiche p JOIN config.stati_pratiche sp ON sp.id=p.stato_id
    WHERE p.id=(SELECT pratica_id FROM tmp_ac_pd)),
  'APERTA',
  '9. [D] tipo senza obbligatori ne'' flusso di chiusura: non si auto-chiude'
);

-- =========================================================
-- 10) Cleanup
-- =========================================================
DELETE FROM pratiche.giornale WHERE pratica_id IN (
  SELECT id FROM pratiche.pratiche WHERE tipo_prestazione_id IN (
    (SELECT tp_id FROM tmp_ac_tp_a),(SELECT tp_id FROM tmp_ac_tp_b),
    (SELECT tp_id FROM tmp_ac_tp_c),(SELECT tp_id FROM tmp_ac_tp_d)));
DELETE FROM pratiche.flussi WHERE pratica_id IN (
  SELECT id FROM pratiche.pratiche WHERE tipo_prestazione_id IN (
    (SELECT tp_id FROM tmp_ac_tp_a),(SELECT tp_id FROM tmp_ac_tp_b),
    (SELECT tp_id FROM tmp_ac_tp_c),(SELECT tp_id FROM tmp_ac_tp_d)));
DELETE FROM pratiche.pratiche WHERE tipo_prestazione_id IN (
    (SELECT tp_id FROM tmp_ac_tp_a),(SELECT tp_id FROM tmp_ac_tp_b),
    (SELECT tp_id FROM tmp_ac_tp_c),(SELECT tp_id FROM tmp_ac_tp_d));
DELETE FROM pratiche.template_flussi WHERE tipo_prestazione_id IN (
    (SELECT tp_id FROM tmp_ac_tp_a),(SELECT tp_id FROM tmp_ac_tp_b),
    (SELECT tp_id FROM tmp_ac_tp_c),(SELECT tp_id FROM tmp_ac_tp_d));
DELETE FROM pratiche.tipi_prestazione WHERE codice_interno IN
    ('TEST_AC_AUTO','TEST_AC_CLOSE','TEST_AC_SOSP','TEST_AC_BARE');

SELECT pass('10. Cleanup completato');

SELECT * FROM finish();

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia nulla dietro di se'. Le DELETE del cleanup restano
-- perche' dove sono un'asserzione devono girare davvero.
ROLLBACK;
