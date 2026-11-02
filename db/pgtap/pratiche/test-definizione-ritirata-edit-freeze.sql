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
-- Test: immutabilita' strutturale «Leggera» — strategia C sulle edizioni RITIRATE.
--       (brief-db-accesso-write-editing-bozza §Problema 3)
--
--   Una definizione forkata RITIRATA (emittente NOT NULL) ha ancora pratiche
--   pinnate alla sua versione: la sua STRUTTURA non deve cambiare (INSERT/UPDATE
--   vietati, fn_check_definizione_struttura_bloccata) ma resta CANCELLABILE
--   (DELETE consentito, fn_check_definizione_congelata copre solo la PUBBLICATA)
--   per housekeeping. La descrizione resta correggibile a caldo.
--   (La PUBBLICATA-emittente resta interamente bloccata: coperta da
--    test-workflow-definizioni-fase2b.sql, invariata sotto la strategia C.)
--
-- Indice test:
-- 0)  Precondizioni (emittente)
-- 1)  Setup: preset {A,B,C, prereq B<-A, formula A->B} + fork pubblicato + RITIRATO
-- 2)  fn_check su fork RITIRATO: struttura_bloccata=TRUE, congelata=FALSE
-- 3)  UPDATE descrizione template del fork RITIRATO -> ammesso (display)
-- 4)  UPDATE sequenza (strutturale) del fork RITIRATO -> 514 (edit bloccato)
-- 5)  INSERT nuovo template nel fork RITIRATO -> 514
-- 6)  UPDATE figlio (prereq) del fork RITIRATO -> 514
-- 7)  INSERT figlio (prereq) nel fork RITIRATO -> 514
-- 8)  DELETE figlio (formula) del fork RITIRATO -> ammesso (housekeeping)
-- 9)  DELETE template (C, senza figli) del fork RITIRATO -> ammesso (housekeeping)
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
-- PRE-CLEANUP (pg_prove COMMITTA). Ritira eventuali fork PUBBLICATI residui, poi
-- cancella (sotto strategia C il DELETE su RITIRATA e' consentito).
-- =========================================================
UPDATE pratiche.workflow_definizioni SET stato='RITIRATA'
 WHERE tipo_prestazione_id IN (SELECT id FROM pratiche.tipi_prestazione WHERE codice_interno='TEST_RITC')
   AND emittente_fiscale_id IS NOT NULL AND stato='PUBBLICATA';
DELETE FROM pratiche.formule_tempo WHERE tipo_prestazione_id IN (
  SELECT id FROM pratiche.tipi_prestazione WHERE codice_interno='TEST_RITC');
DELETE FROM pratiche.template_flussi_prerequisiti WHERE template_flusso_id IN (
  SELECT id FROM pratiche.template_flussi WHERE tipo_prestazione_id IN (
    SELECT id FROM pratiche.tipi_prestazione WHERE codice_interno='TEST_RITC'));
DELETE FROM pratiche.template_flussi WHERE tipo_prestazione_id IN (
  SELECT id FROM pratiche.tipi_prestazione WHERE codice_interno='TEST_RITC');
DELETE FROM pratiche.tipi_prestazione WHERE codice_interno='TEST_RITC';

-- =========================================================
-- 0) Precondizioni
-- =========================================================
CREATE TEMP TABLE tmp_ritc_refs AS
SELECT script.fn_pgtap_emittente_operatore() AS emittente_id;
SELECT ok((SELECT emittente_id IS NOT NULL FROM tmp_ritc_refs), '0. Precondizioni (emittente)');

-- =========================================================
-- 1) Setup: preset + template + figli; fork; pubblica; RITIRA
-- =========================================================
CREATE TEMP TABLE tmp_ritc_tp AS WITH ins AS (
  INSERT INTO pratiche.tipi_prestazione (codice, codice_interno, descrizione, attivo)
  VALUES ('TEST_RITC','TEST_RITC','Ritirata strategia C',true)
  ON CONFLICT (codice_interno) DO UPDATE SET descrizione=EXCLUDED.descrizione RETURNING id)
SELECT id AS tp_id FROM ins;

CREATE TEMP TABLE tmp_ritc_preset AS
SELECT id AS preset_id FROM pratiche.workflow_definizioni
 WHERE tipo_prestazione_id=(SELECT tp_id FROM tmp_ritc_tp)
   AND emittente_fiscale_id IS NULL AND stato='PUBBLICATA';

INSERT INTO pratiche.template_flussi (tipo_prestazione_id, codice, descrizione, sequenza, obbligatorio, attivo, definizione_id)
VALUES ((SELECT tp_id FROM tmp_ritc_tp),'RC_A','Step A',10,true,true,(SELECT preset_id FROM tmp_ritc_preset)),
       ((SELECT tp_id FROM tmp_ritc_tp),'RC_B','Step B',20,true,true,(SELECT preset_id FROM tmp_ritc_preset)),
       ((SELECT tp_id FROM tmp_ritc_tp),'RC_C','Step C',30,false,true,(SELECT preset_id FROM tmp_ritc_preset));
INSERT INTO pratiche.template_flussi_prerequisiti (template_flusso_id, prerequisito_id, esito_richiesto)
VALUES ((SELECT id FROM pratiche.template_flussi WHERE definizione_id=(SELECT preset_id FROM tmp_ritc_preset) AND codice='RC_B'),
        (SELECT id FROM pratiche.template_flussi WHERE definizione_id=(SELECT preset_id FROM tmp_ritc_preset) AND codice='RC_A'),
        'POSITIVO');
INSERT INTO pratiche.formule_tempo (tipo_prestazione_id, template_flusso_da_id, template_flusso_a_id, giorni_esecuzione, giorni_warning, giorni_critico)
VALUES ((SELECT tp_id FROM tmp_ritc_tp),
        (SELECT id FROM pratiche.template_flussi WHERE definizione_id=(SELECT preset_id FROM tmp_ritc_preset) AND codice='RC_A'),
        (SELECT id FROM pratiche.template_flussi WHERE definizione_id=(SELECT preset_id FROM tmp_ritc_preset) AND codice='RC_B'),
        10,8,5);

CREATE TEMP TABLE tmp_ritc_fork AS
SELECT pratiche.fn_fork_definizione(
         (SELECT preset_id FROM tmp_ritc_preset),
         (SELECT emittente_id FROM tmp_ritc_refs)) AS fork_id;
SELECT pratiche.fn_pubblica_definizione((SELECT fork_id FROM tmp_ritc_fork));
-- RITIRA il fork (PUBBLICATA -> RITIRATA, ammessa dal guard workflow_definizioni).
UPDATE pratiche.workflow_definizioni SET stato='RITIRATA' WHERE id=(SELECT fork_id FROM tmp_ritc_fork);

SELECT is(
  (SELECT stato FROM pratiche.workflow_definizioni WHERE id=(SELECT fork_id FROM tmp_ritc_fork)),
  'RITIRATA'::varchar,
  '1. Setup: fork pubblicato e poi RITIRATO'
);

-- =========================================================
-- 2) fn_check sul fork RITIRATO: struttura_bloccata=TRUE, congelata=FALSE
-- =========================================================
SELECT ok(
      pratiche.fn_check_definizione_struttura_bloccata((SELECT fork_id FROM tmp_ritc_fork)) IS TRUE
  AND pratiche.fn_check_definizione_congelata((SELECT fork_id FROM tmp_ritc_fork)) IS FALSE,
  '2. fork RITIRATO: struttura bloccata (no edit) ma non congelata (delete ok)'
);

-- =========================================================
-- 3) UPDATE descrizione -> ammesso (display, correggibile a caldo)
-- =========================================================
SELECT lives_ok(
  $$UPDATE pratiche.template_flussi SET descrizione='Step A (etichetta a caldo su ritirata)'
     WHERE definizione_id=(SELECT fork_id FROM tmp_ritc_fork) AND codice='RC_A'$$,
  '3. UPDATE sola descrizione su fork RITIRATO -> ammesso'
);

-- =========================================================
-- 4) UPDATE sequenza (strutturale) -> 514
-- =========================================================
SELECT throws_like(
  $$UPDATE pratiche.template_flussi SET sequenza=99
     WHERE definizione_id=(SELECT fork_id FROM tmp_ritc_fork) AND codice='RC_A'$$,
  '%struttura congelata%',
  '4. UPDATE strutturale (sequenza) su fork RITIRATO -> 514 (edit bloccato)'
);

-- =========================================================
-- 5) INSERT nuovo template -> 514
-- =========================================================
SELECT throws_like(
  $$INSERT INTO pratiche.template_flussi (tipo_prestazione_id, codice, descrizione, sequenza, attivo, definizione_id)
    VALUES ((SELECT tp_id FROM tmp_ritc_tp),'RC_NEW','Nuovo',40,true,(SELECT fork_id FROM tmp_ritc_fork))$$,
  '%struttura congelata%',
  '5. INSERT template nel fork RITIRATO -> 514'
);

-- =========================================================
-- 6) UPDATE figlio (prereq) -> 514
-- =========================================================
SELECT throws_like(
  $$UPDATE pratiche.template_flussi_prerequisiti SET esito_richiesto='NEGATIVO'
     WHERE template_flusso_id=(SELECT id FROM pratiche.template_flussi WHERE definizione_id=(SELECT fork_id FROM tmp_ritc_fork) AND codice='RC_B')$$,
  '%struttura congelata%',
  '6. UPDATE figlio (prerequisito) del fork RITIRATO -> 514'
);

-- =========================================================
-- 7) INSERT figlio (prereq RC_C<-RC_A) -> 514
-- =========================================================
SELECT throws_like(
  $$INSERT INTO pratiche.template_flussi_prerequisiti (template_flusso_id, prerequisito_id, esito_richiesto)
    VALUES (
      (SELECT id FROM pratiche.template_flussi WHERE definizione_id=(SELECT fork_id FROM tmp_ritc_fork) AND codice='RC_C'),
      (SELECT id FROM pratiche.template_flussi WHERE definizione_id=(SELECT fork_id FROM tmp_ritc_fork) AND codice='RC_A'),
      'POSITIVO')$$,
  '%struttura congelata%',
  '7. INSERT figlio (prerequisito) nel fork RITIRATO -> 514'
);

-- =========================================================
-- 8) DELETE figlio (formula) -> ammesso (housekeeping)
-- =========================================================
SELECT lives_ok(
  $$DELETE FROM pratiche.formule_tempo
     WHERE template_flusso_da_id=(SELECT id FROM pratiche.template_flussi WHERE definizione_id=(SELECT fork_id FROM tmp_ritc_fork) AND codice='RC_A')
       AND template_flusso_a_id =(SELECT id FROM pratiche.template_flussi WHERE definizione_id=(SELECT fork_id FROM tmp_ritc_fork) AND codice='RC_B')$$,
  '8. DELETE figlio (formula) del fork RITIRATO -> ammesso (housekeeping)'
);

-- =========================================================
-- 9) DELETE template (RC_C, senza figli) -> ammesso (housekeeping)
-- =========================================================
SELECT lives_ok(
  $$DELETE FROM pratiche.template_flussi
     WHERE definizione_id=(SELECT fork_id FROM tmp_ritc_fork) AND codice='RC_C'$$,
  '9. DELETE template del fork RITIRATO -> ammesso (housekeeping)'
);

-- =========================================================
-- 10) Cleanup (fork gia' RITIRATO: DELETE consentito)
-- =========================================================
DELETE FROM pratiche.formule_tempo WHERE tipo_prestazione_id=(SELECT tp_id FROM tmp_ritc_tp);
DELETE FROM pratiche.template_flussi_prerequisiti WHERE template_flusso_id IN (
  SELECT id FROM pratiche.template_flussi WHERE tipo_prestazione_id=(SELECT tp_id FROM tmp_ritc_tp));
DELETE FROM pratiche.template_flussi WHERE tipo_prestazione_id=(SELECT tp_id FROM tmp_ritc_tp);
DELETE FROM pratiche.tipi_prestazione WHERE codice_interno='TEST_RITC';

SELECT pass('10. Cleanup completato');

SELECT * FROM finish();

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia nulla dietro di se'. Le DELETE del cleanup restano
-- perche' dove sono un'asserzione devono girare davvero.
ROLLBACK;
