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
-- Test: definizioni workflow versionate — Fase 1 (guard).
--       (brief-db-step-dominio-e-definizioni-versionate Parte 2 / Fase 1)
--       - D2-7 guard flusso<->definizione (508)
--       - D2-8 generazione definizione-aware, fail-fast (512)
--       - D2-9a guard header/transizioni definizione (509/510)
--       - D2-9b immutabilita' del pin (513)
--
-- Indice test:
-- 0)  Precondizioni (refs)
-- 1)  Setup: tipi WF1 (+template+pratica pinnata preset), WF1B (+template)
-- 2)  [508] flusso con template della STESSA definizione -> ammesso (flusso-da-CSV coerente)
-- 3)  [508] flusso con template di ALTRA definizione -> rifiutato (flusso-da-CSV incoerente)
-- 4)  [513] UPDATE pratiche.definizione_id su pratica gia' pinnata -> rifiutato
-- 5a) [510] edizione fork BOZZA->PUBBLICATA -> ammesso
-- 5b) [509] cambio versione su edizione PUBBLICATA -> rifiutato
-- 5c) [C4] UPDATE descrizione su PUBBLICATA -> ammesso (display correggibile)
-- 5d) [510] PUBBLICATA->BOZZA -> rifiutato
-- 5e) [510] PUBBLICATA->RITIRATA -> ammesso
-- 6)  [512] generazione verso edizione emittente VUOTA (fork senza lo step) -> rifiutato
-- 7)  Cleanup
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

SELECT plan(12);

-- =========================================================
-- 0) Precondizioni
-- =========================================================
INSERT INTO config.stati_pratiche (codice, codice_interno, descrizione, attivo)
VALUES ('APERTA','APERTA','Aperta',true) ON CONFLICT (codice_interno) DO NOTHING;
INSERT INTO config.stati_flussi_pratiche (codice, codice_interno, descrizione, attivo)
VALUES ('DA_ESEGUIRE','DA_ESEGUIRE','Da eseguire',true)
ON CONFLICT (codice_interno) DO NOTHING;
INSERT INTO config.priorita_pratiche (codice, codice_interno, descrizione, sequenza, attivo)
VALUES ('NORMALE','NORMALE','Normale',20,true) ON CONFLICT (codice_interno) DO NOTHING;

CREATE TEMP TABLE tmp_f1_refs AS
SELECT
  script.fn_pgtap_emittente_operatore() AS emittente_id,
  (SELECT id FROM anagrafiche.soggetti ORDER BY id LIMIT 1) AS soggetto_id,
  (SELECT id FROM config.stati_pratiche WHERE codice_interno='APERTA') AS st_aperta,
  (SELECT id FROM config.stati_flussi_pratiche WHERE codice_interno='DA_ESEGUIRE') AS sf_da,
  (SELECT id FROM config.priorita_pratiche WHERE codice_interno='NORMALE') AS priorita_id;

SELECT ok(
  (SELECT emittente_id IS NOT NULL AND st_aperta IS NOT NULL AND sf_da IS NOT NULL
      AND priorita_id IS NOT NULL FROM tmp_f1_refs),
  '0. Precondizioni soddisfatte'
);

-- =========================================================
-- 1) Setup: WF1 (preset+template+pratica pinnata), WF1B (preset+template)
-- =========================================================
CREATE TEMP TABLE tmp_f1_tp AS WITH ins AS (
  INSERT INTO pratiche.tipi_prestazione (codice, codice_interno, descrizione, attivo)
  VALUES ('TEST_WF1','TEST_WF1','Def versionate fase1 A',true)
  ON CONFLICT (codice_interno) DO UPDATE SET descrizione=EXCLUDED.descrizione RETURNING id)
SELECT id AS tp_id FROM ins;
CREATE TEMP TABLE tmp_f1_tpb AS WITH ins AS (
  INSERT INTO pratiche.tipi_prestazione (codice, codice_interno, descrizione, attivo)
  VALUES ('TEST_WF1B','TEST_WF1B','Def versionate fase1 B',true)
  ON CONFLICT (codice_interno) DO UPDATE SET descrizione=EXCLUDED.descrizione RETURNING id)
SELECT id AS tp_id FROM ins;

CREATE TEMP TABLE tmp_f1_tf AS WITH ins AS (
  INSERT INTO pratiche.template_flussi (tipo_prestazione_id, codice, descrizione, sequenza, obbligatorio, attivo)
  VALUES ((SELECT tp_id FROM tmp_f1_tp),'WF1_STEP','Step WF1',10,true,true)
  ON CONFLICT (definizione_id, codice) DO UPDATE SET descrizione=EXCLUDED.descrizione RETURNING id)
SELECT id AS tf_id FROM ins;
CREATE TEMP TABLE tmp_f1_tfb AS WITH ins AS (
  INSERT INTO pratiche.template_flussi (tipo_prestazione_id, codice, descrizione, sequenza, obbligatorio, attivo)
  VALUES ((SELECT tp_id FROM tmp_f1_tpb),'WF1B_STEP','Step WF1B',10,true,true)
  ON CONFLICT (definizione_id, codice) DO UPDATE SET descrizione=EXCLUDED.descrizione RETURNING id)
SELECT id AS tf_id FROM ins;

CREATE TEMP TABLE tmp_f1_p AS WITH ins AS (
  INSERT INTO pratiche.pratiche (emittente_fiscale_id, tipo_prestazione_id, soggetto_id, stato_id, priorita_id)
  VALUES ((SELECT emittente_id FROM tmp_f1_refs),(SELECT tp_id FROM tmp_f1_tp),
          (SELECT soggetto_id FROM tmp_f1_refs),(SELECT st_aperta FROM tmp_f1_refs),
          (SELECT priorita_id FROM tmp_f1_refs))
  RETURNING id, definizione_id)
SELECT id AS pratica_id, definizione_id FROM ins;

-- preset di WF1B (per il test 4: bersaglio di un cambio-pin vietato)
CREATE TEMP TABLE tmp_f1_defb AS
SELECT id AS def_id FROM pratiche.workflow_definizioni
 WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_f1_tpb)
   AND emittente_fiscale_id IS NULL AND stato = 'PUBBLICATA';

SELECT ok(
  (SELECT definizione_id IS NOT NULL FROM tmp_f1_p)
  AND (SELECT def_id IS NOT NULL FROM tmp_f1_defb),
  '1. Setup: pratica WF1 pinnata al preset; preset WF1B disponibile'
);

-- =========================================================
-- 2) [508] flusso con template della stessa definizione -> ammesso
--    (simula un flusso seedato da CSV coerente: pratica+template stesso tipo)
-- =========================================================
SELECT lives_ok(
  format($q$INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id, sequenza)
            VALUES (%s, %s, %s, 10)$q$,
    (SELECT pratica_id FROM tmp_f1_p),
    (SELECT tf_id FROM tmp_f1_tf),
    (SELECT sf_da FROM tmp_f1_refs)),
  '2. [508] flusso con template della definizione pinnata -> ammesso (CSV coerente)'
);

-- =========================================================
-- 3) [508] flusso con template di un'ALTRA definizione -> rifiutato
--    (simula un flusso seedato da CSV incoerente)
-- =========================================================
SELECT throws_like(
  format($q$INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id, sequenza)
            VALUES (%s, %s, %s, 20)$q$,
    (SELECT pratica_id FROM tmp_f1_p),
    (SELECT tf_id FROM tmp_f1_tfb),
    (SELECT sf_da FROM tmp_f1_refs)),
  '%non appartiene alla definizione%',
  '3. [508] flusso con template di altra definizione -> rifiutato (CSV incoerente)'
);

-- =========================================================
-- 4) [513] cambio del pin su pratica gia' pinnata -> rifiutato
-- =========================================================
SELECT throws_like(
  format($q$UPDATE pratiche.pratiche SET definizione_id = %s WHERE id = %s$q$,
    (SELECT def_id FROM tmp_f1_defb),
    (SELECT pratica_id FROM tmp_f1_p)),
  '%pin dell''edizione di workflow%',
  '4. [513] cambio di definizione_id su pratica pinnata -> rifiutato'
);

-- =========================================================
-- 5) Header + transizioni su un'edizione fork (emittente-scoped) dedicata
-- =========================================================
CREATE TEMP TABLE tmp_f1_fork AS WITH ins AS (
  INSERT INTO pratiche.workflow_definizioni
         (tipo_prestazione_id, emittente_fiscale_id, versione, stato, descrizione)
  VALUES ((SELECT tp_id FROM tmp_f1_tp),(SELECT emittente_id FROM tmp_f1_refs),1,'BOZZA',
          'Edizione fork di test (transizioni)')
  RETURNING id)
SELECT id AS def_id FROM ins;

-- 5a) BOZZA -> PUBBLICATA (transizione ammessa)
SELECT lives_ok(
  format($q$UPDATE pratiche.workflow_definizioni SET stato='PUBBLICATA' WHERE id=%s$q$,
    (SELECT def_id FROM tmp_f1_fork)),
  '5a. [510] edizione fork BOZZA->PUBBLICATA -> ammesso'
);

-- 5b) cambio versione su PUBBLICATA (header immutabile) -> rifiutato
SELECT throws_like(
  format($q$UPDATE pratiche.workflow_definizioni SET versione=2 WHERE id=%s$q$,
    (SELECT def_id FROM tmp_f1_fork)),
  '%non modificabile%',
  '5b. [509] cambio versione su edizione PUBBLICATA -> rifiutato'
);

-- 5c) descrizione editabile anche su PUBBLICATA (display correggibile, C4)
SELECT lives_ok(
  format($q$UPDATE pratiche.workflow_definizioni SET descrizione='rietichettata' WHERE id=%s$q$,
    (SELECT def_id FROM tmp_f1_fork)),
  '5c. [C4] descrizione correggibile su PUBBLICATA -> ammesso'
);

-- 5d) PUBBLICATA -> BOZZA (transizione vietata)
SELECT throws_like(
  format($q$UPDATE pratiche.workflow_definizioni SET stato='BOZZA' WHERE id=%s$q$,
    (SELECT def_id FROM tmp_f1_fork)),
  '%Transizione di stato definizione workflow non ammessa%',
  '5d. [510] PUBBLICATA->BOZZA -> rifiutato'
);

-- 5e) PUBBLICATA -> RITIRATA (transizione ammessa)
SELECT lives_ok(
  format($q$UPDATE pratiche.workflow_definizioni SET stato='RITIRATA' WHERE id=%s$q$,
    (SELECT def_id FROM tmp_f1_fork)),
  '5e. [510] PUBBLICATA->RITIRATA -> ammesso'
);

-- =========================================================
-- 6) [512] generazione verso un'edizione emittente VUOTA (fork senza lo step):
--    la figlia si pinna all'edizione emittente (fn_risolvi_definizione preferisce
--    l'emittente al preset); il template destinazione della regola (per codice)
--    non esiste in quell'edizione -> fail-fast 512.
-- =========================================================
-- Tipo destinazione WF1C con preset (bootstrap) + un suo template.
CREATE TEMP TABLE tmp_f1_tpc AS WITH ins AS (
  INSERT INTO pratiche.tipi_prestazione (codice, codice_interno, descrizione, attivo)
  VALUES ('TEST_WF1C','TEST_WF1C','Def versionate fase1 C (dest)',true)
  ON CONFLICT (codice_interno) DO UPDATE SET descrizione=EXCLUDED.descrizione RETURNING id)
SELECT id AS tp_id FROM ins;
CREATE TEMP TABLE tmp_f1_tfc AS WITH ins AS (
  INSERT INTO pratiche.template_flussi (tipo_prestazione_id, codice, descrizione, sequenza, attivo)
  VALUES ((SELECT tp_id FROM tmp_f1_tpc),'WF1C_STEP','Step iniziale WF1C',10,true)
  ON CONFLICT (definizione_id, codice) DO UPDATE SET descrizione=EXCLUDED.descrizione RETURNING id)
SELECT id AS tf_id FROM ins;
-- Edizione emittente VUOTA e PUBBLICATA per (WF1C, emittente di test).
CREATE TEMP TABLE tmp_f1_defc_emit AS WITH ins AS (
  INSERT INTO pratiche.workflow_definizioni
         (tipo_prestazione_id, emittente_fiscale_id, versione, stato, descrizione)
  VALUES ((SELECT tp_id FROM tmp_f1_tpc),(SELECT emittente_id FROM tmp_f1_refs),1,'PUBBLICATA',
          'Edizione emittente vuota (fork senza WF1C_STEP)')
  RETURNING id)
SELECT id AS def_id FROM ins;
-- Regola: origine=WF1_STEP, dest tipo=WF1C, dest template=WF1C_STEP (del preset).
CREATE TEMP TABLE tmp_f1_regola AS WITH ins AS (
  INSERT INTO pratiche.regole_generazione
         (template_flusso_origine_id, tipo_prestazione_dest_id, template_flusso_dest_id,
          auto, attivo, descrizione)
  VALUES ((SELECT tf_id FROM tmp_f1_tf),(SELECT tp_id FROM tmp_f1_tpc),
          (SELECT tf_id FROM tmp_f1_tfc), false, true, 'Regola test 512')
  RETURNING id)
SELECT id AS regola_id FROM ins;

-- Flusso sorgente = quello inserito al test 2 (pratica WF1, emittente di test).
-- La figlia (WF1C, emittente di test) si pinna all'edizione emittente VUOTA:
-- WF1C_STEP non c'e' -> 512.
SELECT throws_like(
  format($q$SELECT pratiche.fn_genera_pratica_da_flusso(
              (SELECT id FROM pratiche.flussi
                WHERE pratica_id=%s AND template_flusso_id=%s LIMIT 1),
              %s)$q$,
    (SELECT pratica_id FROM tmp_f1_p),
    (SELECT tf_id FROM tmp_f1_tf),
    (SELECT regola_id FROM tmp_f1_regola)),
  '%non esiste nella definizione%',
  '6. [512] generazione verso edizione emittente vuota -> fail-fast'
);

-- =========================================================
-- 7) Cleanup (delete tipi -> cascata workflow_definizioni)
-- =========================================================
DELETE FROM pratiche.regole_generazione
 WHERE template_flusso_origine_id IN (
   SELECT id FROM pratiche.template_flussi
    WHERE tipo_prestazione_id IN ((SELECT tp_id FROM tmp_f1_tp),(SELECT tp_id FROM tmp_f1_tpb),
                                  (SELECT tp_id FROM tmp_f1_tpc)));
DELETE FROM pratiche.giornale WHERE pratica_id IN (
  SELECT id FROM pratiche.pratiche WHERE tipo_prestazione_id IN (
    (SELECT tp_id FROM tmp_f1_tp),(SELECT tp_id FROM tmp_f1_tpb),(SELECT tp_id FROM tmp_f1_tpc)));
DELETE FROM pratiche.flussi WHERE pratica_id IN (
  SELECT id FROM pratiche.pratiche WHERE tipo_prestazione_id IN (
    (SELECT tp_id FROM tmp_f1_tp),(SELECT tp_id FROM tmp_f1_tpb),(SELECT tp_id FROM tmp_f1_tpc)));
DELETE FROM pratiche.pratiche WHERE tipo_prestazione_id IN (
    (SELECT tp_id FROM tmp_f1_tp),(SELECT tp_id FROM tmp_f1_tpb),(SELECT tp_id FROM tmp_f1_tpc));
DELETE FROM pratiche.template_flussi WHERE tipo_prestazione_id IN (
    (SELECT tp_id FROM tmp_f1_tp),(SELECT tp_id FROM tmp_f1_tpb),(SELECT tp_id FROM tmp_f1_tpc));
DELETE FROM pratiche.tipi_prestazione
 WHERE codice_interno IN ('TEST_WF1','TEST_WF1B','TEST_WF1C');

SELECT pass('7. Cleanup completato');

SELECT * FROM finish();

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia nulla dietro di se'. Le DELETE del cleanup restano
-- perche' dove sono un'asserzione devono girare davvero.
ROLLBACK;
