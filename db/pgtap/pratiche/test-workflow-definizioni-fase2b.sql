-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: definizioni workflow versionate — Fase 2b (immutabilita' strutturale
--       «Leggera»). (brief-db-step-dominio-e-definizioni-versionate P2 / F2b)
--
--   Strategia «Leggera»: solo le edizioni FORKATE (emittente NOT NULL) e
--   PUBBLICATE si congelano. Il preset di fabbrica (emittente NULL) resta
--   editabile da seed in qualsiasi stato; le BOZZA e le RITIRATA non sono
--   congelate. Su un fork pubblicato:
--     - template_flussi: INSERT/DELETE vietati, UPDATE vietato tranne la sola
--       descrizione (unico campo display correggibile a caldo);
--     - i 6 figli di configurazione: ogni INSERT/UPDATE/DELETE vietato.
--   Errore unico: TEMPLATE_DEFINIZIONE_CONGELATA (514).
--
-- Indice test:
-- 0)  Precondizioni (emittente + preset bootstrap)
-- 1)  Setup: preset v1 + template A,B,C + prereq B<-A + formula A->B; fork; publish
-- 2)  fork ora PUBBLICATA per-emittente (base: e' congelato)
-- 3)  fn_check_definizione_congelata: fork=true, preset=false
-- 4)  fn_check su BOZZA (nuova_versione preset) = false
-- 5)  UPDATE descrizione template del fork -> ammesso (correggibile a caldo)
-- 6)  UPDATE sequenza template del fork -> 514
-- 7)  INSERT nuovo template nel fork -> 514
-- 8)  DELETE template del fork -> 514
-- 9)  INSERT figlio (prereq) nel fork -> 514
-- 10) UPDATE figlio (prereq) del fork -> 514
-- 11) DELETE figlio (formula) del fork -> 514
-- 12) Preset editabile: UPDATE sequenza template del preset -> ammesso
-- 13) Preset editabile: INSERT template nel preset -> ammesso
-- 14) BOZZA editabile: INSERT template nella BOZZA -> ammesso
-- 15) Cleanup (ritira il fork prima di cancellare: e' l'unico modo di smantellarlo)
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
-- PRE-CLEANUP: pg_prove COMMITTA (nessun rollback per-file). Un run precedente
-- morto lascia residui. Il fork puo' essere rimasto PUBBLICATO (congelato): va
-- RITIRATO prima, altrimenti il guard 2b blocca la cancellazione di template e
-- figli. Ordine: ritira fork -> figli -> template -> pratiche -> tipo (cascata
-- workflow_definizioni via ON DELETE CASCADE).
-- =========================================================
UPDATE pratiche.workflow_definizioni SET stato = 'RITIRATA'
 WHERE tipo_prestazione_id IN (
         SELECT id FROM pratiche.tipi_prestazione WHERE codice_interno = 'TEST_WF2B')
   AND emittente_fiscale_id IS NOT NULL
   AND stato = 'PUBBLICATA';

DELETE FROM pratiche.regole_generazione WHERE template_flusso_origine_id IN (
  SELECT id FROM pratiche.template_flussi WHERE tipo_prestazione_id IN (
    SELECT id FROM pratiche.tipi_prestazione WHERE codice_interno = 'TEST_WF2B'));
DELETE FROM pratiche.formule_tempo WHERE tipo_prestazione_id IN (
    SELECT id FROM pratiche.tipi_prestazione WHERE codice_interno = 'TEST_WF2B');
DELETE FROM pratiche.template_flussi_prerequisiti WHERE template_flusso_id IN (
    SELECT id FROM pratiche.template_flussi WHERE tipo_prestazione_id IN (
      SELECT id FROM pratiche.tipi_prestazione WHERE codice_interno = 'TEST_WF2B'));
DELETE FROM pratiche.template_flussi_canali WHERE template_flusso_id IN (
    SELECT id FROM pratiche.template_flussi WHERE tipo_prestazione_id IN (
      SELECT id FROM pratiche.tipi_prestazione WHERE codice_interno = 'TEST_WF2B'));
DELETE FROM pratiche.template_flussi_handler_eventi WHERE template_flusso_id IN (
    SELECT id FROM pratiche.template_flussi WHERE tipo_prestazione_id IN (
      SELECT id FROM pratiche.tipi_prestazione WHERE codice_interno = 'TEST_WF2B'));
DELETE FROM pratiche.competenze_flussi WHERE template_flusso_id IN (
    SELECT id FROM pratiche.template_flussi WHERE tipo_prestazione_id IN (
      SELECT id FROM pratiche.tipi_prestazione WHERE codice_interno = 'TEST_WF2B'));
DELETE FROM pratiche.template_flussi WHERE tipo_prestazione_id IN (
    SELECT id FROM pratiche.tipi_prestazione WHERE codice_interno = 'TEST_WF2B');
DELETE FROM pratiche.tipi_prestazione WHERE codice_interno = 'TEST_WF2B';

-- =========================================================
-- 0) Precondizioni
-- =========================================================
CREATE TEMP TABLE tmp_wf2b_refs AS
SELECT script.fn_pgtap_emittente_operatore() AS emittente_id;

SELECT ok((SELECT emittente_id IS NOT NULL FROM tmp_wf2b_refs), '0. Precondizioni (emittente attivo)');

-- =========================================================
-- 1) Setup: preset v1 (bootstrap) + template A,B,C + prereq + formula; fork; publish
-- =========================================================
CREATE TEMP TABLE tmp_wf2b_tp AS WITH ins AS (
  INSERT INTO pratiche.tipi_prestazione (codice, codice_interno, descrizione, attivo)
  VALUES ('TEST_WF2B','TEST_WF2B','Immutabilita fork fase2b',true)
  ON CONFLICT (codice_interno) DO UPDATE SET descrizione = EXCLUDED.descrizione RETURNING id)
SELECT id AS tp_id FROM ins;

CREATE TEMP TABLE tmp_wf2b_preset AS
SELECT id AS preset_id FROM pratiche.workflow_definizioni
 WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_wf2b_tp)
   AND emittente_fiscale_id IS NULL AND stato = 'PUBBLICATA';

CREATE TEMP TABLE tmp_wf2b_tf AS WITH ins AS (
  INSERT INTO pratiche.template_flussi (tipo_prestazione_id, codice, descrizione, sequenza, obbligatorio, attivo, definizione_id)
  VALUES ((SELECT tp_id FROM tmp_wf2b_tp),'WF2B_A','Step A',10,true,true,(SELECT preset_id FROM tmp_wf2b_preset)),
         ((SELECT tp_id FROM tmp_wf2b_tp),'WF2B_B','Step B',20,true,true,(SELECT preset_id FROM tmp_wf2b_preset)),
         ((SELECT tp_id FROM tmp_wf2b_tp),'WF2B_C','Step C',30,true,true,(SELECT preset_id FROM tmp_wf2b_preset))
  ON CONFLICT (definizione_id, codice) DO UPDATE SET descrizione = EXCLUDED.descrizione RETURNING id, codice)
SELECT max(id) FILTER (WHERE codice='WF2B_A') AS a_id,
       max(id) FILTER (WHERE codice='WF2B_B') AS b_id,
       max(id) FILTER (WHERE codice='WF2B_C') AS c_id
  FROM ins;

-- prereq: B richiede A (POSITIVO); formula: A -> B
INSERT INTO pratiche.template_flussi_prerequisiti (template_flusso_id, prerequisito_id, esito_richiesto)
VALUES ((SELECT b_id FROM tmp_wf2b_tf),(SELECT a_id FROM tmp_wf2b_tf),'POSITIVO');
INSERT INTO pratiche.formule_tempo
       (tipo_prestazione_id, template_flusso_da_id, template_flusso_a_id,
        giorni_esecuzione, giorni_warning, giorni_critico)
VALUES ((SELECT tp_id FROM tmp_wf2b_tp),(SELECT a_id FROM tmp_wf2b_tf),(SELECT b_id FROM tmp_wf2b_tf),10,8,5);

-- fork(preset, emittente) -> BOZZA con copia integrale, poi publish -> congelato
CREATE TEMP TABLE tmp_wf2b_fork AS
SELECT pratiche.fn_fork_definizione(
         (SELECT preset_id FROM tmp_wf2b_preset),
         (SELECT emittente_id FROM tmp_wf2b_refs)) AS fork_id;
SELECT pratiche.fn_pubblica_definizione((SELECT fork_id FROM tmp_wf2b_fork));

SELECT ok(
  (SELECT preset_id IS NOT NULL FROM tmp_wf2b_preset)
  AND (SELECT a_id IS NOT NULL AND b_id IS NOT NULL AND c_id IS NOT NULL FROM tmp_wf2b_tf)
  AND (SELECT fork_id IS NOT NULL FROM tmp_wf2b_fork),
  '1. Setup: preset v1 + 3 template + prereq + formula + fork pubblicato'
);

-- =========================================================
-- 2) fork ora PUBBLICATA per-emittente (base del congelamento)
-- =========================================================
SELECT is(
  (SELECT stato || '/' || (emittente_fiscale_id IS NOT NULL)::text
     FROM pratiche.workflow_definizioni WHERE id = (SELECT fork_id FROM tmp_wf2b_fork)),
  'PUBBLICATA/true',
  '2. fork pubblicato per-emittente (edizione congelata)'
);

-- =========================================================
-- 3) fn_check_definizione_congelata: fork=true, preset=false
-- =========================================================
SELECT ok(
      pratiche.fn_check_definizione_congelata((SELECT fork_id   FROM tmp_wf2b_fork)) IS TRUE
  AND pratiche.fn_check_definizione_congelata((SELECT preset_id FROM tmp_wf2b_preset)) IS FALSE,
  '3. fn_check: fork PUBBLICATO=congelato, preset (emittente NULL)=non congelato'
);

-- =========================================================
-- 4) fn_check su BOZZA (nuova_versione del preset) = false
-- =========================================================
CREATE TEMP TABLE tmp_wf2b_boz AS
SELECT pratiche.fn_nuova_versione_definizione((SELECT preset_id FROM tmp_wf2b_preset)) AS boz_id;

SELECT ok(
  pratiche.fn_check_definizione_congelata((SELECT boz_id FROM tmp_wf2b_boz)) IS FALSE,
  '4. fn_check: BOZZA (nuova_versione) non congelata'
);

-- =========================================================
-- 5) UPDATE descrizione template del fork -> AMMESSO (correggibile a caldo)
-- =========================================================
SELECT lives_ok(
  $$UPDATE pratiche.template_flussi SET descrizione = 'Step A (etichetta corretta a caldo)'
     WHERE definizione_id = (SELECT fork_id FROM tmp_wf2b_fork) AND codice = 'WF2B_A'$$,
  '5. UPDATE sola descrizione su fork pubblicato -> ammesso'
);

-- =========================================================
-- 6) UPDATE sequenza template del fork -> 514
-- =========================================================
SELECT throws_like(
  $$UPDATE pratiche.template_flussi SET sequenza = 99
     WHERE definizione_id = (SELECT fork_id FROM tmp_wf2b_fork) AND codice = 'WF2B_A'$$,
  '%struttura congelata%',
  '6. UPDATE campo strutturale (sequenza) su fork pubblicato -> 514'
);

-- =========================================================
-- 7) INSERT nuovo template nel fork -> 514
-- =========================================================
SELECT throws_like(
  $$INSERT INTO pratiche.template_flussi (tipo_prestazione_id, codice, descrizione, sequenza, attivo, definizione_id)
    VALUES ((SELECT tp_id FROM tmp_wf2b_tp),'WF2B_NEW','Step nuovo',50,true,(SELECT fork_id FROM tmp_wf2b_fork))$$,
  '%struttura congelata%',
  '7. INSERT nuovo template nel fork pubblicato -> 514'
);

-- =========================================================
-- 8) DELETE template del fork -> 514 (WF2B_C: senza figli, ma il guard fira prima)
-- =========================================================
SELECT throws_like(
  $$DELETE FROM pratiche.template_flussi
     WHERE definizione_id = (SELECT fork_id FROM tmp_wf2b_fork) AND codice = 'WF2B_C'$$,
  '%struttura congelata%',
  '8. DELETE template dal fork pubblicato -> 514'
);

-- =========================================================
-- 9) INSERT figlio (prereq WF2B_C <- WF2B_A) nel fork -> 514
-- =========================================================
SELECT throws_like(
  $$INSERT INTO pratiche.template_flussi_prerequisiti (template_flusso_id, prerequisito_id, esito_richiesto)
    VALUES (
      (SELECT id FROM pratiche.template_flussi WHERE definizione_id=(SELECT fork_id FROM tmp_wf2b_fork) AND codice='WF2B_C'),
      (SELECT id FROM pratiche.template_flussi WHERE definizione_id=(SELECT fork_id FROM tmp_wf2b_fork) AND codice='WF2B_A'),
      'POSITIVO')$$,
  '%struttura congelata%',
  '9. INSERT figlio (prerequisito) nel fork pubblicato -> 514'
);

-- =========================================================
-- 10) UPDATE figlio (prereq B<-A copiato dal fork) -> 514
-- =========================================================
SELECT throws_like(
  $$UPDATE pratiche.template_flussi_prerequisiti SET esito_richiesto = 'NEGATIVO'
     WHERE template_flusso_id = (SELECT id FROM pratiche.template_flussi WHERE definizione_id=(SELECT fork_id FROM tmp_wf2b_fork) AND codice='WF2B_B')
       AND prerequisito_id   = (SELECT id FROM pratiche.template_flussi WHERE definizione_id=(SELECT fork_id FROM tmp_wf2b_fork) AND codice='WF2B_A')$$,
  '%struttura congelata%',
  '10. UPDATE figlio (prerequisito) del fork pubblicato -> 514'
);

-- =========================================================
-- 11) DELETE figlio (formula A->B copiata dal fork) -> 514
-- =========================================================
SELECT throws_like(
  $$DELETE FROM pratiche.formule_tempo
     WHERE template_flusso_da_id = (SELECT id FROM pratiche.template_flussi WHERE definizione_id=(SELECT fork_id FROM tmp_wf2b_fork) AND codice='WF2B_A')
       AND template_flusso_a_id  = (SELECT id FROM pratiche.template_flussi WHERE definizione_id=(SELECT fork_id FROM tmp_wf2b_fork) AND codice='WF2B_B')$$,
  '%struttura congelata%',
  '11. DELETE figlio (formula) del fork pubblicato -> 514'
);

-- =========================================================
-- 12) Preset editabile (PUBBLICATO ma emittente NULL): UPDATE strutturale ammesso
-- =========================================================
SELECT lives_ok(
  $$UPDATE pratiche.template_flussi SET sequenza = 15
     WHERE definizione_id = (SELECT preset_id FROM tmp_wf2b_preset) AND codice = 'WF2B_A'$$,
  '12. UPDATE strutturale sul preset (emittente NULL) -> ammesso («Leggera»)'
);

-- =========================================================
-- 13) Preset editabile: INSERT template nel preset ammesso
-- =========================================================
SELECT lives_ok(
  $$INSERT INTO pratiche.template_flussi (tipo_prestazione_id, codice, descrizione, sequenza, attivo, definizione_id)
    VALUES ((SELECT tp_id FROM tmp_wf2b_tp),'WF2B_P','Step preset nuovo',40,true,(SELECT preset_id FROM tmp_wf2b_preset))$$,
  '13. INSERT template nel preset -> ammesso'
);

-- =========================================================
-- 14) BOZZA editabile: INSERT template nella BOZZA ammesso
-- =========================================================
SELECT lives_ok(
  $$INSERT INTO pratiche.template_flussi (tipo_prestazione_id, codice, descrizione, sequenza, attivo, definizione_id)
    VALUES ((SELECT tp_id FROM tmp_wf2b_tp),'WF2B_Z','Step bozza nuovo',60,true,(SELECT boz_id FROM tmp_wf2b_boz))$$,
  '14. INSERT template nella BOZZA -> ammesso'
);

-- =========================================================
-- 15) Cleanup: ritira il fork (unico modo di smantellarlo), poi cancella
-- =========================================================
UPDATE pratiche.workflow_definizioni SET stato = 'RITIRATA'
 WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_wf2b_tp)
   AND emittente_fiscale_id IS NOT NULL
   AND stato = 'PUBBLICATA';

DELETE FROM pratiche.regole_generazione WHERE template_flusso_origine_id IN (
  SELECT id FROM pratiche.template_flussi WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_wf2b_tp));
DELETE FROM pratiche.formule_tempo WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_wf2b_tp);
DELETE FROM pratiche.template_flussi_prerequisiti WHERE template_flusso_id IN (
  SELECT id FROM pratiche.template_flussi WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_wf2b_tp));
DELETE FROM pratiche.template_flussi_canali WHERE template_flusso_id IN (
  SELECT id FROM pratiche.template_flussi WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_wf2b_tp));
DELETE FROM pratiche.template_flussi_handler_eventi WHERE template_flusso_id IN (
  SELECT id FROM pratiche.template_flussi WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_wf2b_tp));
DELETE FROM pratiche.competenze_flussi WHERE template_flusso_id IN (
  SELECT id FROM pratiche.template_flussi WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_wf2b_tp));
DELETE FROM pratiche.template_flussi WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_wf2b_tp);
DELETE FROM pratiche.tipi_prestazione WHERE codice_interno = 'TEST_WF2B';

SELECT pass('15. Cleanup completato (fork ritirato e smantellato)');

SELECT * FROM finish();

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia nulla dietro di se'. Le DELETE del cleanup restano
-- perche' dove sono un'asserzione devono girare davvero.
ROLLBACK;
