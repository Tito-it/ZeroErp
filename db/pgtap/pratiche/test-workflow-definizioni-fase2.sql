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
-- Test: definizioni workflow versionate — Fase 2 (fork/versione/pubblica/drift).
--       (brief-db-step-dominio-e-definizioni-versionate Parte 2 / Fase 2)
--       - DROP uq per-tipo: due definizioni dello stesso tipo con gli stessi
--         codici coesistono.
--       - fn_copia_definizione via fn_fork_definizione: header + template + figli
--         con remap per codice (doppio remap su prerequisiti e formule_tempo).
--       - fn_pubblica_definizione: pubblica atomica (ritira la precedente) +
--         validazioni (511: non-BOZZA, ciclo prerequisiti).
--       - fn_nuova_versione_definizione + drift.
--
-- Indice test:
-- 0)  Precondizioni (refs)
-- 1)  Setup WF2: preset v1 (bootstrap) + template A,B,C + prereq B<-A + formula A->B
-- 2)  fork(preset, emittente) -> nuova edizione BOZZA con provenance
-- 3)  fork: template copiati (stessi codici, id DIVERSI, stesso conteggio)
-- 4)  fork: prereq con DOPPIO remap (fork-B <- fork-A, esito preservato)
-- 5)  fork: formula con DOPPIO remap (fork-A -> fork-B)
-- 6)  coesistenza post-drop: preset-A e fork-A stesso codice, definizioni diverse
-- 7)  pubblica(fork BOZZA) -> PUBBLICATA (nessuna precedente da ritirare)
-- 8)  pubblica di una BOZZA con CICLO prerequisiti -> 511
-- 9)  pubblica di una definizione gia' PUBBLICATA (non-BOZZA) -> 511
-- 10) nuova_versione(preset) + pubblica -> v1 RITIRATA, v2 PUBBLICATA (ritira)
-- 11) drift: il fork (versione_origine=1) compare in vw_definizioni_drift
-- 12) Cleanup
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

SELECT plan(14);

-- =========================================================
-- PRE-CLEANUP: pg_prove COMMITTA (nessun rollback per-file); un run precedente
-- morto a meta' (prima del cleanup finale) lascia residui. Si rimuovono qui in
-- testa cosi' il test e' auto-guarente e ripetibile. Ordine: figli -> template
-- -> pratiche -> tipi (cascata workflow_definizioni via ON DELETE CASCADE).
-- Nota (Fase 2b): un fork PUBBLICATO e' congelato (guard immutabilita' 2b) e i
-- suoi template/figli non sono cancellabili finche' resta PUBBLICATO -> va
-- prima RITIRATO (PUBBLICATA->RITIRATA, che lo scongela).
-- =========================================================
UPDATE pratiche.workflow_definizioni SET stato = 'RITIRATA'
 WHERE tipo_prestazione_id IN (
         SELECT id FROM pratiche.tipi_prestazione WHERE codice_interno IN ('TEST_WF2','TEST_WF2CY'))
   AND emittente_fiscale_id IS NOT NULL
   AND stato = 'PUBBLICATA';
DELETE FROM pratiche.regole_generazione WHERE template_flusso_origine_id IN (
  SELECT id FROM pratiche.template_flussi WHERE tipo_prestazione_id IN (
    SELECT id FROM pratiche.tipi_prestazione WHERE codice_interno IN ('TEST_WF2','TEST_WF2CY')));
DELETE FROM pratiche.formule_tempo WHERE tipo_prestazione_id IN (
    SELECT id FROM pratiche.tipi_prestazione WHERE codice_interno IN ('TEST_WF2','TEST_WF2CY'));
DELETE FROM pratiche.template_flussi_prerequisiti WHERE template_flusso_id IN (
    SELECT id FROM pratiche.template_flussi WHERE tipo_prestazione_id IN (
      SELECT id FROM pratiche.tipi_prestazione WHERE codice_interno IN ('TEST_WF2','TEST_WF2CY')));
DELETE FROM pratiche.giornale WHERE pratica_id IN (
    SELECT id FROM pratiche.pratiche WHERE tipo_prestazione_id IN (
      SELECT id FROM pratiche.tipi_prestazione WHERE codice_interno IN ('TEST_WF2','TEST_WF2CY')));
DELETE FROM pratiche.flussi WHERE pratica_id IN (
    SELECT id FROM pratiche.pratiche WHERE tipo_prestazione_id IN (
      SELECT id FROM pratiche.tipi_prestazione WHERE codice_interno IN ('TEST_WF2','TEST_WF2CY')));
DELETE FROM pratiche.pratiche WHERE tipo_prestazione_id IN (
    SELECT id FROM pratiche.tipi_prestazione WHERE codice_interno IN ('TEST_WF2','TEST_WF2CY'));
DELETE FROM pratiche.template_flussi WHERE tipo_prestazione_id IN (
    SELECT id FROM pratiche.tipi_prestazione WHERE codice_interno IN ('TEST_WF2','TEST_WF2CY'));
DELETE FROM pratiche.tipi_prestazione WHERE codice_interno IN ('TEST_WF2','TEST_WF2CY');

-- =========================================================
-- 0) Precondizioni
-- =========================================================
INSERT INTO config.priorita_pratiche (codice, codice_interno, descrizione, sequenza, attivo)
VALUES ('NORMALE','NORMALE','Normale',20,true) ON CONFLICT (codice_interno) DO NOTHING;

CREATE TEMP TABLE tmp_wf2_refs AS
SELECT script.fn_pgtap_emittente_operatore() AS emittente_id;

SELECT ok((SELECT emittente_id IS NOT NULL FROM tmp_wf2_refs), '0. Precondizioni (emittente)');

-- =========================================================
-- 1) Setup WF2: preset v1 PUBBLICATA (bootstrap) + template A,B,C + figli
-- =========================================================
CREATE TEMP TABLE tmp_wf2_tp AS WITH ins AS (
  INSERT INTO pratiche.tipi_prestazione (codice, codice_interno, descrizione, attivo)
  VALUES ('TEST_WF2','TEST_WF2','Fork/versione fase2',true)
  ON CONFLICT (codice_interno) DO UPDATE SET descrizione=EXCLUDED.descrizione RETURNING id)
SELECT id AS tp_id FROM ins;

CREATE TEMP TABLE tmp_wf2_preset AS
SELECT id AS preset_id FROM pratiche.workflow_definizioni
 WHERE tipo_prestazione_id=(SELECT tp_id FROM tmp_wf2_tp)
   AND emittente_fiscale_id IS NULL AND stato='PUBBLICATA';

CREATE TEMP TABLE tmp_wf2_tf AS WITH ins AS (
  INSERT INTO pratiche.template_flussi (tipo_prestazione_id, codice, descrizione, sequenza, obbligatorio, attivo)
  VALUES ((SELECT tp_id FROM tmp_wf2_tp),'WF2_A','Step A',10,true,true),
         ((SELECT tp_id FROM tmp_wf2_tp),'WF2_B','Step B',20,true,true),
         ((SELECT tp_id FROM tmp_wf2_tp),'WF2_C','Step C',30,true,true)
  ON CONFLICT (definizione_id, codice) DO UPDATE SET descrizione=EXCLUDED.descrizione RETURNING id, codice)
SELECT max(id) FILTER (WHERE codice='WF2_A') AS a_id,
       max(id) FILTER (WHERE codice='WF2_B') AS b_id,
       max(id) FILTER (WHERE codice='WF2_C') AS c_id
  FROM ins;

-- prereq: B richiede A (POSITIVO)
INSERT INTO pratiche.template_flussi_prerequisiti (template_flusso_id, prerequisito_id, esito_richiesto)
VALUES ((SELECT b_id FROM tmp_wf2_tf),(SELECT a_id FROM tmp_wf2_tf),'POSITIVO');
-- formula: A -> B
INSERT INTO pratiche.formule_tempo
       (tipo_prestazione_id, template_flusso_da_id, template_flusso_a_id,
        giorni_esecuzione, giorni_warning, giorni_critico)
VALUES ((SELECT tp_id FROM tmp_wf2_tp),(SELECT a_id FROM tmp_wf2_tf),(SELECT b_id FROM tmp_wf2_tf),10,8,5);

SELECT ok(
  (SELECT preset_id IS NOT NULL FROM tmp_wf2_preset)
  AND (SELECT a_id IS NOT NULL AND b_id IS NOT NULL AND c_id IS NOT NULL FROM tmp_wf2_tf),
  '1. Setup WF2: preset v1 + 3 template + prereq + formula'
);

-- =========================================================
-- 2) fork(preset, emittente) -> BOZZA con provenance
-- =========================================================
CREATE TEMP TABLE tmp_wf2_fork AS
SELECT pratiche.fn_fork_definizione(
         (SELECT preset_id FROM tmp_wf2_preset),
         (SELECT emittente_id FROM tmp_wf2_refs)) AS fork_id;

SELECT ok(
  (SELECT wd.stato='BOZZA'
       AND wd.emittente_fiscale_id=(SELECT emittente_id FROM tmp_wf2_refs)
       AND wd.preset_origine_id=(SELECT preset_id FROM tmp_wf2_preset)
       AND wd.versione_origine=1
     FROM pratiche.workflow_definizioni wd WHERE wd.id=(SELECT fork_id FROM tmp_wf2_fork)),
  '2. fork -> edizione BOZZA emittente con provenance (preset_origine + versione_origine=1)'
);

-- =========================================================
-- 3) fork: template copiati (stessi codici, id diversi, stesso conteggio)
-- =========================================================
SELECT is(
  (SELECT count(*) FROM pratiche.template_flussi WHERE definizione_id=(SELECT fork_id FROM tmp_wf2_fork)),
  (SELECT count(*) FROM pratiche.template_flussi WHERE definizione_id=(SELECT preset_id FROM tmp_wf2_preset)),
  '3. fork: stesso numero di template del preset'
);

-- =========================================================
-- 4) fork: prereq con DOPPIO remap (fork-B <- fork-A, esito preservato)
-- =========================================================
SELECT is(
  (SELECT count(*)
     FROM pratiche.template_flussi_prerequisiti p
     JOIN pratiche.template_flussi tb
          ON tb.id=p.template_flusso_id AND tb.definizione_id=(SELECT fork_id FROM tmp_wf2_fork) AND tb.codice='WF2_B'
     JOIN pratiche.template_flussi ta
          ON ta.id=p.prerequisito_id AND ta.definizione_id=(SELECT fork_id FROM tmp_wf2_fork) AND ta.codice='WF2_A'
    WHERE p.esito_richiesto='POSITIVO'),
  1::bigint,
  '4. fork: prereq doppio-remappato (fork-B <- fork-A, POSITIVO) dentro la definizione forkata'
);

-- =========================================================
-- 5) fork: formula con DOPPIO remap (fork-A -> fork-B)
-- =========================================================
SELECT is(
  (SELECT count(*)
     FROM pratiche.formule_tempo ft
     JOIN pratiche.template_flussi tda
          ON tda.id=ft.template_flusso_da_id AND tda.definizione_id=(SELECT fork_id FROM tmp_wf2_fork) AND tda.codice='WF2_A'
     JOIN pratiche.template_flussi ta
          ON ta.id=ft.template_flusso_a_id AND ta.definizione_id=(SELECT fork_id FROM tmp_wf2_fork) AND ta.codice='WF2_B'),
  1::bigint,
  '5. fork: formula doppio-remappata (fork-A -> fork-B)'
);

-- =========================================================
-- 6) coesistenza post-drop uq per-tipo: preset-A e fork-A stesso codice, def diverse
-- =========================================================
SELECT is(
  (SELECT count(DISTINCT definizione_id)
     FROM pratiche.template_flussi
    WHERE tipo_prestazione_id=(SELECT tp_id FROM tmp_wf2_tp) AND codice='WF2_A'),
  2::bigint,
  '6. coesistenza: due template WF2_A (preset + fork) stesso tipo/codice, definizioni diverse (uq per-tipo rimosso)'
);

-- =========================================================
-- 7) pubblica(fork) -> PUBBLICATA (nessuna precedente PUBBLICATA nello scope emittente)
-- =========================================================
SELECT lives_ok(
  format('SELECT pratiche.fn_pubblica_definizione(%s)', (SELECT fork_id FROM tmp_wf2_fork)),
  '7a. pubblica(fork) non solleva'
);
SELECT is(
  (SELECT stato FROM pratiche.workflow_definizioni WHERE id=(SELECT fork_id FROM tmp_wf2_fork)),
  'PUBBLICATA'::varchar,
  '7b. fork ora PUBBLICATA'
);

-- =========================================================
-- 8) pubblica di una BOZZA con CICLO prerequisiti -> 511
--    Tipo dedicato WF2CY: nuova_versione(preset) -> BOZZA vuota, poi 2 step + ciclo.
-- =========================================================
CREATE TEMP TABLE tmp_wf2cy_tp AS WITH ins AS (
  INSERT INTO pratiche.tipi_prestazione (codice, codice_interno, descrizione, attivo)
  VALUES ('TEST_WF2CY','TEST_WF2CY','Ciclo prereq fase2',true)
  ON CONFLICT (codice_interno) DO UPDATE SET descrizione=EXCLUDED.descrizione RETURNING id)
SELECT id AS tp_id FROM ins;
CREATE TEMP TABLE tmp_wf2cy_boz AS
SELECT pratiche.fn_nuova_versione_definizione(
         (SELECT id FROM pratiche.workflow_definizioni
           WHERE tipo_prestazione_id=(SELECT tp_id FROM tmp_wf2cy_tp)
             AND emittente_fiscale_id IS NULL AND stato='PUBBLICATA')) AS boz_id;
CREATE TEMP TABLE tmp_wf2cy_tf AS WITH ins AS (
  INSERT INTO pratiche.template_flussi (tipo_prestazione_id, codice, descrizione, sequenza, attivo, definizione_id)
  VALUES ((SELECT tp_id FROM tmp_wf2cy_tp),'CY_X','X',10,true,(SELECT boz_id FROM tmp_wf2cy_boz)),
         ((SELECT tp_id FROM tmp_wf2cy_tp),'CY_Y','Y',20,true,(SELECT boz_id FROM tmp_wf2cy_boz))
  RETURNING id, codice)
SELECT max(id) FILTER (WHERE codice='CY_X') AS x_id, max(id) FILTER (WHERE codice='CY_Y') AS y_id FROM ins;
-- ciclo: X richiede Y, Y richiede X
INSERT INTO pratiche.template_flussi_prerequisiti (template_flusso_id, prerequisito_id)
VALUES ((SELECT x_id FROM tmp_wf2cy_tf),(SELECT y_id FROM tmp_wf2cy_tf)),
       ((SELECT y_id FROM tmp_wf2cy_tf),(SELECT x_id FROM tmp_wf2cy_tf));

SELECT throws_like(
  format('SELECT pratiche.fn_pubblica_definizione(%s)', (SELECT boz_id FROM tmp_wf2cy_boz)),
  '%ciclo nel grafo dei prerequisiti%',
  '8. pubblica di BOZZA con ciclo prerequisiti -> 511'
);

-- =========================================================
-- 9) pubblica di una definizione gia' PUBBLICATA (non-BOZZA) -> 511
-- =========================================================
SELECT throws_like(
  format('SELECT pratiche.fn_pubblica_definizione(%s)', (SELECT fork_id FROM tmp_wf2_fork)),
  '%non e'' in BOZZA%',
  '9. pubblica di definizione gia'' PUBBLICATA -> 511'
);

-- =========================================================
-- 10) nuova_versione(preset WF2) + pubblica -> v1 RITIRATA, v2 PUBBLICATA
-- =========================================================
CREATE TEMP TABLE tmp_wf2_v2 AS
SELECT pratiche.fn_nuova_versione_definizione((SELECT preset_id FROM tmp_wf2_preset)) AS v2_id;
SELECT pratiche.fn_pubblica_definizione((SELECT v2_id FROM tmp_wf2_v2));

SELECT is(
  (SELECT stato FROM pratiche.workflow_definizioni WHERE id=(SELECT preset_id FROM tmp_wf2_preset))
    || '/' ||
  (SELECT stato FROM pratiche.workflow_definizioni WHERE id=(SELECT v2_id FROM tmp_wf2_v2)),
  'RITIRATA/PUBBLICATA',
  '10. nuova_versione + pubblica: preset v1 RITIRATA, v2 PUBBLICATA (ritira atomico)'
);

-- =========================================================
-- 11) drift: il fork (versione_origine=1) compare, preset ora a v2
-- =========================================================
SELECT ok(
  EXISTS (SELECT 1 FROM pratiche.vw_definizioni_drift
           WHERE definizione_id=(SELECT fork_id FROM tmp_wf2_fork)
             AND versione_preset_corrente=2 AND versioni_indietro=1),
  '11. drift: il fork risulta 1 versione indietro rispetto al preset (ora v2)'
);

-- =========================================================
-- 12) Cleanup (delete tipi -> cascata workflow_definizioni)
--     Il fork del test 7 e' PUBBLICATO (congelato dall'immutabilita' 2b): va
--     RITIRATO prima, altrimenti il guard blocca la cancellazione dei suoi
--     template/figli.
-- =========================================================
UPDATE pratiche.workflow_definizioni SET stato = 'RITIRATA'
 WHERE tipo_prestazione_id IN ((SELECT tp_id FROM tmp_wf2_tp),(SELECT tp_id FROM tmp_wf2cy_tp))
   AND emittente_fiscale_id IS NOT NULL
   AND stato = 'PUBBLICATA';
DELETE FROM pratiche.regole_generazione WHERE template_flusso_origine_id IN (
  SELECT id FROM pratiche.template_flussi WHERE tipo_prestazione_id IN (
    (SELECT tp_id FROM tmp_wf2_tp),(SELECT tp_id FROM tmp_wf2cy_tp)));
DELETE FROM pratiche.formule_tempo WHERE tipo_prestazione_id IN (
    (SELECT tp_id FROM tmp_wf2_tp),(SELECT tp_id FROM tmp_wf2cy_tp));
DELETE FROM pratiche.template_flussi_prerequisiti WHERE template_flusso_id IN (
  SELECT id FROM pratiche.template_flussi WHERE tipo_prestazione_id IN (
    (SELECT tp_id FROM tmp_wf2_tp),(SELECT tp_id FROM tmp_wf2cy_tp)));
DELETE FROM pratiche.template_flussi WHERE tipo_prestazione_id IN (
    (SELECT tp_id FROM tmp_wf2_tp),(SELECT tp_id FROM tmp_wf2cy_tp));
DELETE FROM pratiche.tipi_prestazione WHERE codice_interno IN ('TEST_WF2','TEST_WF2CY');

SELECT pass('12. Cleanup completato');

SELECT * FROM finish();

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia nulla dietro di se'. Le DELETE del cleanup restano
-- perche' dove sono un'asserzione devono girare davvero.
ROLLBACK;
