-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: il test collauda i guard su pratiche.workflow_definizioni, che difendono da chi
--   scrive DIRETTAMENTE sulla tabella. Il ruolo applicativo ha solo SELECT, e ha
--   ragione di averlo: le scritture dell'applicazione passano tutte da entry point
--   SECURITY DEFINER (fn_pubblica_definizione, fn_fork_definizione,
--   fn_nuova_versione_definizione, trgfn_tipi_prestazione_bootstrap_definizione).
--   E le transizioni che questi guard vietano — «PUBBLICATA -> BOZZA», cambio di
--   versione su una pubblicata — nessun entry point le offre: l'applicazione non
--   puo' nemmeno tentarle. Il soggetto del test sta fuori dal percorso applicativo
--   (terza forma del criterio, brief §29.3-bis).
-- pgTAP test per Zero ERP
--
-- Test: isolamento fork-aware di chiusura e auto-chiusura pratica.
--       (brief-db-gap-fork-fase1-chiusura-per-definizione)
--
--   Con la Fase 2 (fork/versioni) esistono PIU' definizioni per lo stesso tipo.
--   fn_check_chiusura_pratica e trgfn_flussi_autochiusura_pratica devono scopare
--   i template della DEFINIZIONE pinnata della pratica (definizione_id), non del
--   tipo. Questo test incrocia due definizioni dello stesso tipo con set di
--   obbligatori/chiusura DIVERSI e una pratica per definizione: fallirebbe con la
--   versione per-tipo (una pratica vedrebbe gli step dell'altra edizione).
--
-- Indice test:
-- 0)  Precondizioni
-- --- MODELLO AUTO (gate obbligatori + fn_check_chiusura_pratica) ---
-- 1)  Setup A: preset {S1} + fork {S1,S2} pubblicato; pratica preset + pratica fork
-- 2)  [preset] completa S1 -> CHIUSA (preset ha solo S1; il bug la terrebbe aperta per S2 del fork)
-- 3)  [fork]   completa S1 -> APERTA (S2 del fork ancora pendente)
-- 4)  [fork]   completa S2 -> CHIUSA
-- --- MODELLO FLUSSO-DI-CHIUSURA (select template chiusura + guard pre-completamento) ---
-- 5)  Setup B: preset {PW, PC(chiude)} + fork {PW, PC(chiude), PX} pubblicato; pratica preset
-- 6)  [preset] completa PW -> APERTA (PC di chiusura pendente)
-- 7)  [preset] completa PC -> CHIUSA (il bug vedrebbe PX del fork come bloccante -> blocco pre-completamento)
-- 8)  Cleanup (ritira i fork prima di cancellare)
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

SELECT plan(9);

-- =========================================================
-- PRE-CLEANUP (pg_prove COMMITTA): ritira i fork pubblicati (congelati) e rimuovi.
-- =========================================================
UPDATE pratiche.workflow_definizioni SET stato='RITIRATA'
 WHERE tipo_prestazione_id IN (SELECT id FROM pratiche.tipi_prestazione
                                WHERE codice_interno IN ('TEST_FKGAP_A','TEST_FKGAP_B'))
   AND emittente_fiscale_id IS NOT NULL AND stato='PUBBLICATA';
DELETE FROM pratiche.giornale WHERE pratica_id IN (
  SELECT id FROM pratiche.pratiche WHERE tipo_prestazione_id IN (
    SELECT id FROM pratiche.tipi_prestazione WHERE codice_interno IN ('TEST_FKGAP_A','TEST_FKGAP_B')));
DELETE FROM pratiche.flussi WHERE pratica_id IN (
  SELECT id FROM pratiche.pratiche WHERE tipo_prestazione_id IN (
    SELECT id FROM pratiche.tipi_prestazione WHERE codice_interno IN ('TEST_FKGAP_A','TEST_FKGAP_B')));
DELETE FROM pratiche.pratiche WHERE tipo_prestazione_id IN (
    SELECT id FROM pratiche.tipi_prestazione WHERE codice_interno IN ('TEST_FKGAP_A','TEST_FKGAP_B'));
DELETE FROM pratiche.formule_tempo WHERE tipo_prestazione_id IN (
    SELECT id FROM pratiche.tipi_prestazione WHERE codice_interno IN ('TEST_FKGAP_A','TEST_FKGAP_B'));
DELETE FROM pratiche.template_flussi_prerequisiti WHERE template_flusso_id IN (
    SELECT id FROM pratiche.template_flussi WHERE tipo_prestazione_id IN (
      SELECT id FROM pratiche.tipi_prestazione WHERE codice_interno IN ('TEST_FKGAP_A','TEST_FKGAP_B')));
DELETE FROM pratiche.template_flussi WHERE tipo_prestazione_id IN (
    SELECT id FROM pratiche.tipi_prestazione WHERE codice_interno IN ('TEST_FKGAP_A','TEST_FKGAP_B'));
DELETE FROM pratiche.tipi_prestazione WHERE codice_interno IN ('TEST_FKGAP_A','TEST_FKGAP_B');

-- =========================================================
-- 0) Precondizioni (stati + refs)
-- =========================================================
INSERT INTO config.stati_pratiche (codice, codice_interno, descrizione, attivo)
VALUES ('APERTA','APERTA','Aperta',true),('CHIUSA','CHIUSA','Chiusa',true)
ON CONFLICT (codice_interno) DO NOTHING;
INSERT INTO config.stati_flussi_pratiche (codice, codice_interno, descrizione, attivo)
VALUES ('DA_ESEGUIRE','DA_ESEGUIRE','Da eseguire',true),
       ('IN_CORSO','IN_CORSO','In corso',true),
       ('COMPLETATO','COMPLETATO','Completato',true)
ON CONFLICT (codice_interno) DO NOTHING;
INSERT INTO config.priorita_pratiche (codice, codice_interno, descrizione, sequenza, attivo)
VALUES ('NORMALE','NORMALE','Normale',20,true) ON CONFLICT (codice_interno) DO NOTHING;

CREATE TEMP TABLE tmp_fg_refs AS
SELECT
  script.fn_pgtap_emittente_operatore() AS emittente_id,
  (SELECT id FROM anagrafiche.soggetti ORDER BY id LIMIT 1) AS soggetto_id,
  (SELECT id FROM config.stati_pratiche WHERE codice_interno='APERTA') AS st_aperta,
  (SELECT id FROM config.stati_pratiche WHERE codice_interno='CHIUSA') AS st_chiusa,
  (SELECT id FROM config.stati_flussi_pratiche WHERE codice_interno='DA_ESEGUIRE') AS sf_da,
  (SELECT id FROM config.stati_flussi_pratiche WHERE codice_interno='IN_CORSO') AS sf_in,
  (SELECT id FROM config.stati_flussi_pratiche WHERE codice_interno='COMPLETATO') AS sf_done,
  (SELECT id FROM config.priorita_pratiche WHERE codice_interno='NORMALE') AS priorita_id;

SELECT ok(
  (SELECT emittente_id IS NOT NULL AND soggetto_id IS NOT NULL AND st_aperta IS NOT NULL
      AND st_chiusa IS NOT NULL AND sf_da IS NOT NULL AND sf_done IS NOT NULL
      AND priorita_id IS NOT NULL FROM tmp_fg_refs),
  '0. Precondizioni soddisfatte'
);

-- =========================================================
-- 1) Setup MODELLO AUTO: preset {S1} + fork {S1,S2} pubblicato
-- =========================================================
CREATE TEMP TABLE tmp_fg_a_tp AS WITH ins AS (
  INSERT INTO pratiche.tipi_prestazione (codice, codice_interno, descrizione, attivo)
  VALUES ('TEST_FKGAP_A','TEST_FKGAP_A','Gap fork AUTO',true)
  ON CONFLICT (codice_interno) DO UPDATE SET descrizione=EXCLUDED.descrizione RETURNING id)
SELECT id AS tp_id FROM ins;

CREATE TEMP TABLE tmp_fg_a_preset AS
SELECT id AS preset_id FROM pratiche.workflow_definizioni
 WHERE tipo_prestazione_id=(SELECT tp_id FROM tmp_fg_a_tp)
   AND emittente_fiscale_id IS NULL AND stato='PUBBLICATA';

-- Preset: solo S1 (obbligatorio).
INSERT INTO pratiche.template_flussi (tipo_prestazione_id, codice, descrizione, sequenza, obbligatorio, attivo, definizione_id)
VALUES ((SELECT tp_id FROM tmp_fg_a_tp),'FGA_S1','Step 1',10,true,true,(SELECT preset_id FROM tmp_fg_a_preset));

-- Fork BOZZA (copia S1) + aggiunta S2 (obbligatorio) SOLO nel fork; poi pubblica -> congelato.
CREATE TEMP TABLE tmp_fg_a_fork AS
SELECT pratiche.fn_fork_definizione(
         (SELECT preset_id FROM tmp_fg_a_preset),
         (SELECT emittente_id FROM tmp_fg_refs)) AS fork_id;
INSERT INTO pratiche.template_flussi (tipo_prestazione_id, codice, descrizione, sequenza, obbligatorio, attivo, definizione_id)
VALUES ((SELECT tp_id FROM tmp_fg_a_tp),'FGA_S2','Step 2',20,true,true,(SELECT fork_id FROM tmp_fg_a_fork));
SELECT pratiche.fn_pubblica_definizione((SELECT fork_id FROM tmp_fg_a_fork));

-- Pratiche: una pinnata sul preset, una sul fork (pin esplicito).
CREATE TEMP TABLE tmp_fg_a_pp AS WITH ins AS (
  INSERT INTO pratiche.pratiche (emittente_fiscale_id, tipo_prestazione_id, soggetto_id, stato_id, priorita_id, definizione_id)
  VALUES ((SELECT emittente_id FROM tmp_fg_refs),(SELECT tp_id FROM tmp_fg_a_tp),
          (SELECT soggetto_id FROM tmp_fg_refs),(SELECT st_aperta FROM tmp_fg_refs),
          (SELECT priorita_id FROM tmp_fg_refs),(SELECT preset_id FROM tmp_fg_a_preset)) RETURNING id)
SELECT id AS pratica_id FROM ins;
CREATE TEMP TABLE tmp_fg_a_pf AS WITH ins AS (
  INSERT INTO pratiche.pratiche (emittente_fiscale_id, tipo_prestazione_id, soggetto_id, stato_id, priorita_id, definizione_id)
  VALUES ((SELECT emittente_id FROM tmp_fg_refs),(SELECT tp_id FROM tmp_fg_a_tp),
          (SELECT soggetto_id FROM tmp_fg_refs),(SELECT st_aperta FROM tmp_fg_refs),
          (SELECT priorita_id FROM tmp_fg_refs),(SELECT fork_id FROM tmp_fg_a_fork)) RETURNING id)
SELECT id AS pratica_id FROM ins;

-- Flussi: pratica preset -> S1 del preset; pratica fork -> S1 e S2 del fork.
INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id, sequenza)
VALUES ((SELECT pratica_id FROM tmp_fg_a_pp),
        (SELECT id FROM pratiche.template_flussi WHERE definizione_id=(SELECT preset_id FROM tmp_fg_a_preset) AND codice='FGA_S1'),
        (SELECT sf_da FROM tmp_fg_refs),10);
INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id, sequenza)
VALUES ((SELECT pratica_id FROM tmp_fg_a_pf),
        (SELECT id FROM pratiche.template_flussi WHERE definizione_id=(SELECT fork_id FROM tmp_fg_a_fork) AND codice='FGA_S1'),
        (SELECT sf_da FROM tmp_fg_refs),10),
       ((SELECT pratica_id FROM tmp_fg_a_pf),
        (SELECT id FROM pratiche.template_flussi WHERE definizione_id=(SELECT fork_id FROM tmp_fg_a_fork) AND codice='FGA_S2'),
        (SELECT sf_da FROM tmp_fg_refs),20);

SELECT ok(
  (SELECT preset_id IS NOT NULL FROM tmp_fg_a_preset)
  AND (SELECT fork_id IS NOT NULL FROM tmp_fg_a_fork)
  AND (SELECT stato='PUBBLICATA' FROM pratiche.workflow_definizioni WHERE id=(SELECT fork_id FROM tmp_fg_a_fork))
  AND (SELECT pratica_id IS NOT NULL FROM tmp_fg_a_pp)
  AND (SELECT pratica_id IS NOT NULL FROM tmp_fg_a_pf),
  '1. Setup AUTO: preset {S1} + fork {S1,S2} pubblicato + 2 pratiche'
);

-- =========================================================
-- 2) [preset] completa S1 -> CHIUSA (isolamento: preset ha SOLO S1)
-- =========================================================
UPDATE pratiche.flussi SET stato_id=(SELECT sf_in FROM tmp_fg_refs)
 WHERE pratica_id=(SELECT pratica_id FROM tmp_fg_a_pp);
UPDATE pratiche.flussi SET stato_id=(SELECT sf_done FROM tmp_fg_refs), esito='POSITIVO'
 WHERE pratica_id=(SELECT pratica_id FROM tmp_fg_a_pp);

SELECT is(
  (SELECT sp.codice_interno FROM pratiche.pratiche p JOIN config.stati_pratiche sp ON sp.id=p.stato_id
    WHERE p.id=(SELECT pratica_id FROM tmp_fg_a_pp)),
  'CHIUSA',
  '2. [preset] completato S1 (unico obbligatorio della SUA definizione): auto-chiusura -> CHIUSA'
);

-- =========================================================
-- 3) [fork] completa S1 -> APERTA (S2 del fork ancora pendente)
-- =========================================================
UPDATE pratiche.flussi SET stato_id=(SELECT sf_in FROM tmp_fg_refs)
 WHERE pratica_id=(SELECT pratica_id FROM tmp_fg_a_pf)
   AND template_flusso_id=(SELECT id FROM pratiche.template_flussi WHERE definizione_id=(SELECT fork_id FROM tmp_fg_a_fork) AND codice='FGA_S1');
UPDATE pratiche.flussi SET stato_id=(SELECT sf_done FROM tmp_fg_refs), esito='POSITIVO'
 WHERE pratica_id=(SELECT pratica_id FROM tmp_fg_a_pf)
   AND template_flusso_id=(SELECT id FROM pratiche.template_flussi WHERE definizione_id=(SELECT fork_id FROM tmp_fg_a_fork) AND codice='FGA_S1');

SELECT is(
  (SELECT sp.codice_interno FROM pratiche.pratiche p JOIN config.stati_pratiche sp ON sp.id=p.stato_id
    WHERE p.id=(SELECT pratica_id FROM tmp_fg_a_pf)),
  'APERTA',
  '3. [fork] completato S1 ma S2 (obbligatorio SOLO del fork) pendente: resta APERTA'
);

-- =========================================================
-- 4) [fork] completa S2 -> CHIUSA
-- =========================================================
UPDATE pratiche.flussi SET stato_id=(SELECT sf_in FROM tmp_fg_refs)
 WHERE pratica_id=(SELECT pratica_id FROM tmp_fg_a_pf)
   AND template_flusso_id=(SELECT id FROM pratiche.template_flussi WHERE definizione_id=(SELECT fork_id FROM tmp_fg_a_fork) AND codice='FGA_S2');
UPDATE pratiche.flussi SET stato_id=(SELECT sf_done FROM tmp_fg_refs), esito='POSITIVO'
 WHERE pratica_id=(SELECT pratica_id FROM tmp_fg_a_pf)
   AND template_flusso_id=(SELECT id FROM pratiche.template_flussi WHERE definizione_id=(SELECT fork_id FROM tmp_fg_a_fork) AND codice='FGA_S2');

SELECT is(
  (SELECT sp.codice_interno FROM pratiche.pratiche p JOIN config.stati_pratiche sp ON sp.id=p.stato_id
    WHERE p.id=(SELECT pratica_id FROM tmp_fg_a_pf)),
  'CHIUSA',
  '4. [fork] completati entrambi gli obbligatori del fork: auto-chiusura -> CHIUSA'
);

-- =========================================================
-- 5) Setup MODELLO FLUSSO-DI-CHIUSURA: preset {PW,PC(chiude)} + fork {PW,PC(chiude),PX}
-- =========================================================
CREATE TEMP TABLE tmp_fg_b_tp AS WITH ins AS (
  INSERT INTO pratiche.tipi_prestazione (codice, codice_interno, descrizione, attivo)
  VALUES ('TEST_FKGAP_B','TEST_FKGAP_B','Gap fork CLOSE',true)
  ON CONFLICT (codice_interno) DO UPDATE SET descrizione=EXCLUDED.descrizione RETURNING id)
SELECT id AS tp_id FROM ins;

CREATE TEMP TABLE tmp_fg_b_preset AS
SELECT id AS preset_id FROM pratiche.workflow_definizioni
 WHERE tipo_prestazione_id=(SELECT tp_id FROM tmp_fg_b_tp)
   AND emittente_fiscale_id IS NULL AND stato='PUBBLICATA';

-- Preset: PW (obbligatorio) + PC (obbligatorio + chiude_pratica).
INSERT INTO pratiche.template_flussi (tipo_prestazione_id, codice, descrizione, sequenza, obbligatorio, chiude_pratica, attivo, definizione_id)
VALUES ((SELECT tp_id FROM tmp_fg_b_tp),'FGB_PW','Lavoro',10,true,false,true,(SELECT preset_id FROM tmp_fg_b_preset)),
       ((SELECT tp_id FROM tmp_fg_b_tp),'FGB_PC','Chiusura',20,true,true,true,(SELECT preset_id FROM tmp_fg_b_preset));

-- Fork BOZZA (copia PW,PC) + aggiunta PX (obbligatorio) SOLO nel fork; poi pubblica.
CREATE TEMP TABLE tmp_fg_b_fork AS
SELECT pratiche.fn_fork_definizione(
         (SELECT preset_id FROM tmp_fg_b_preset),
         (SELECT emittente_id FROM tmp_fg_refs)) AS fork_id;
INSERT INTO pratiche.template_flussi (tipo_prestazione_id, codice, descrizione, sequenza, obbligatorio, attivo, definizione_id)
VALUES ((SELECT tp_id FROM tmp_fg_b_tp),'FGB_PX','Extra fork',30,true,true,(SELECT fork_id FROM tmp_fg_b_fork));
SELECT pratiche.fn_pubblica_definizione((SELECT fork_id FROM tmp_fg_b_fork));

-- Pratica pinnata sul PRESET (non ha PX). Flussi: PW + PC del preset.
CREATE TEMP TABLE tmp_fg_b_pp AS WITH ins AS (
  INSERT INTO pratiche.pratiche (emittente_fiscale_id, tipo_prestazione_id, soggetto_id, stato_id, priorita_id, definizione_id)
  VALUES ((SELECT emittente_id FROM tmp_fg_refs),(SELECT tp_id FROM tmp_fg_b_tp),
          (SELECT soggetto_id FROM tmp_fg_refs),(SELECT st_aperta FROM tmp_fg_refs),
          (SELECT priorita_id FROM tmp_fg_refs),(SELECT preset_id FROM tmp_fg_b_preset)) RETURNING id)
SELECT id AS pratica_id FROM ins;
INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id, sequenza)
VALUES ((SELECT pratica_id FROM tmp_fg_b_pp),
        (SELECT id FROM pratiche.template_flussi WHERE definizione_id=(SELECT preset_id FROM tmp_fg_b_preset) AND codice='FGB_PW'),
        (SELECT sf_da FROM tmp_fg_refs),10),
       ((SELECT pratica_id FROM tmp_fg_b_pp),
        (SELECT id FROM pratiche.template_flussi WHERE definizione_id=(SELECT preset_id FROM tmp_fg_b_preset) AND codice='FGB_PC'),
        (SELECT sf_da FROM tmp_fg_refs),20);

SELECT ok(
  (SELECT stato='PUBBLICATA' FROM pratiche.workflow_definizioni WHERE id=(SELECT fork_id FROM tmp_fg_b_fork))
  AND (SELECT pratica_id IS NOT NULL FROM tmp_fg_b_pp),
  '5. Setup CLOSE: preset {PW,PC} + fork {PW,PC,PX} pubblicato + pratica preset'
);

-- =========================================================
-- 6) [preset] completa PW -> APERTA (PC di chiusura pendente)
-- =========================================================
UPDATE pratiche.flussi SET stato_id=(SELECT sf_in FROM tmp_fg_refs)
 WHERE pratica_id=(SELECT pratica_id FROM tmp_fg_b_pp)
   AND template_flusso_id=(SELECT id FROM pratiche.template_flussi WHERE definizione_id=(SELECT preset_id FROM tmp_fg_b_preset) AND codice='FGB_PW');
UPDATE pratiche.flussi SET stato_id=(SELECT sf_done FROM tmp_fg_refs), esito='POSITIVO'
 WHERE pratica_id=(SELECT pratica_id FROM tmp_fg_b_pp)
   AND template_flusso_id=(SELECT id FROM pratiche.template_flussi WHERE definizione_id=(SELECT preset_id FROM tmp_fg_b_preset) AND codice='FGB_PW');

SELECT is(
  (SELECT sp.codice_interno FROM pratiche.pratiche p JOIN config.stati_pratiche sp ON sp.id=p.stato_id
    WHERE p.id=(SELECT pratica_id FROM tmp_fg_b_pp)),
  'APERTA',
  '6. [preset] completato PW: il flusso di chiusura PC e'' pendente -> resta APERTA'
);

-- =========================================================
-- 7) [preset] completa PC -> CHIUSA
--    Il guard pre-completamento verifica i bloccanti della SUA definizione (solo PW,
--    gia' concluso). Col bug per-tipo vedrebbe PX del fork come bloccante -> blocco.
-- =========================================================
UPDATE pratiche.flussi SET stato_id=(SELECT sf_in FROM tmp_fg_refs)
 WHERE pratica_id=(SELECT pratica_id FROM tmp_fg_b_pp)
   AND template_flusso_id=(SELECT id FROM pratiche.template_flussi WHERE definizione_id=(SELECT preset_id FROM tmp_fg_b_preset) AND codice='FGB_PC');
UPDATE pratiche.flussi SET stato_id=(SELECT sf_done FROM tmp_fg_refs), esito='POSITIVO'
 WHERE pratica_id=(SELECT pratica_id FROM tmp_fg_b_pp)
   AND template_flusso_id=(SELECT id FROM pratiche.template_flussi WHERE definizione_id=(SELECT preset_id FROM tmp_fg_b_preset) AND codice='FGB_PC');

SELECT is(
  (SELECT sp.codice_interno FROM pratiche.pratiche p JOIN config.stati_pratiche sp ON sp.id=p.stato_id
    WHERE p.id=(SELECT pratica_id FROM tmp_fg_b_pp)),
  'CHIUSA',
  '7. [preset] completato PC (flusso di chiusura del preset): auto-chiusura -> CHIUSA (PX del fork non blocca)'
);

-- =========================================================
-- 8) Cleanup (ritira i fork prima di cancellare)
-- =========================================================
UPDATE pratiche.workflow_definizioni SET stato='RITIRATA'
 WHERE tipo_prestazione_id IN ((SELECT tp_id FROM tmp_fg_a_tp),(SELECT tp_id FROM tmp_fg_b_tp))
   AND emittente_fiscale_id IS NOT NULL AND stato='PUBBLICATA';
DELETE FROM pratiche.giornale WHERE pratica_id IN (
  SELECT id FROM pratiche.pratiche WHERE tipo_prestazione_id IN ((SELECT tp_id FROM tmp_fg_a_tp),(SELECT tp_id FROM tmp_fg_b_tp)));
DELETE FROM pratiche.flussi WHERE pratica_id IN (
  SELECT id FROM pratiche.pratiche WHERE tipo_prestazione_id IN ((SELECT tp_id FROM tmp_fg_a_tp),(SELECT tp_id FROM tmp_fg_b_tp)));
DELETE FROM pratiche.pratiche WHERE tipo_prestazione_id IN ((SELECT tp_id FROM tmp_fg_a_tp),(SELECT tp_id FROM tmp_fg_b_tp));
DELETE FROM pratiche.formule_tempo WHERE tipo_prestazione_id IN ((SELECT tp_id FROM tmp_fg_a_tp),(SELECT tp_id FROM tmp_fg_b_tp));
DELETE FROM pratiche.template_flussi_prerequisiti WHERE template_flusso_id IN (
  SELECT id FROM pratiche.template_flussi WHERE tipo_prestazione_id IN ((SELECT tp_id FROM tmp_fg_a_tp),(SELECT tp_id FROM tmp_fg_b_tp)));
DELETE FROM pratiche.template_flussi WHERE tipo_prestazione_id IN ((SELECT tp_id FROM tmp_fg_a_tp),(SELECT tp_id FROM tmp_fg_b_tp));
DELETE FROM pratiche.tipi_prestazione WHERE codice_interno IN ('TEST_FKGAP_A','TEST_FKGAP_B');

SELECT pass('8. Cleanup completato');

SELECT * FROM finish();

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia nulla dietro di se'. Le DELETE del cleanup restano
-- perche' dove sono un'asserzione devono girare davvero.
ROLLBACK;
