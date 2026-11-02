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
-- Test: definizioni workflow versionate — Fase 0 (fondazione).
--       (brief-db-step-dominio-e-definizioni-versionate Parte 2 / Fase 0)
--       workflow_definizioni + bootstrap preset per-tipo + auto-default
--       template + auto-pin pratiche + fn_risolvi_definizione + vincoli.
--
-- Indice test:
-- 0) Precondizioni (refs)
-- 1) Bootstrap: nuovo tipo TEST_WDF -> preset v1 PUBBLICATA creato dal trigger
-- 2) Auto-default: template inserito senza definizione_id -> preset del tipo
-- 3) Auto-pin: pratica inserita senza definizione_id -> preset del tipo
-- 4) fn_risolvi_definizione(tipo, emittente senza fork) -> preset
-- 5) 507: tipo senza preset (cancellato) -> INSERT template fallisce parlante
-- 6) Una sola PUBBLICATA per scope -> seconda PUBBLICATA preset rifiutata (23505)
-- 7) uq (definizione_id, codice): codice duplicato nella stessa definizione (23505)
-- 8) FK composita: template con definizione di un ALTRO tipo -> rifiutato (23503)
-- 9) NOT NULL attivo su template_flussi.definizione_id e pratiche.definizione_id
-- 10) Cleanup (tipi cancellabili: cascata definizioni)
-- ------------------------------------------------------------

-- =========================================================
-- Pulizia d'ingresso — FUORI dalla transazione, ed e' il punto
-- =========================================================
-- ⚠️ Questo file lasciava detriti quando falliva a meta'. Il cleanup «vero» sta
--   alla sezione 10, in fondo: se il test muore prima — e col runner reale,
--   che gira con ON_ERROR_STOP, muore alla PRIMA istruzione che fallisce — non
--   ci arriva mai, e i tipi TEST_WDF* restano nel database. La corsa successiva
--   ci inciampa sopra («valore chiave duplicato su uq_template_flussi_definizione_codice»)
--   e da li' in poi il rosso non e' piu' del codice, e' della corsa precedente.
--   Osservato il 2026-08-06 fra una misura da utente applicativo e una da owner.
--
-- Questa pulizia sta PRIMA di BEGIN apposta: in autocommit, quindi rimuove
--   davvero i detriti di una corsa morta a meta'. Dentro la transazione verrebbe
--   annullata insieme al resto e non servirebbe a niente.
-- Brief: brief-db-pgtap-runner-rls-baseline §15.
DELETE FROM pratiche.giornale WHERE pratica_id IN (
  SELECT p.id FROM pratiche.pratiche p JOIN pratiche.tipi_prestazione tp ON tp.id = p.tipo_prestazione_id
   WHERE tp.codice_interno IN ('TEST_WDF','TEST_WDF2','TEST_WDF3'));
DELETE FROM pratiche.flussi WHERE pratica_id IN (
  SELECT p.id FROM pratiche.pratiche p JOIN pratiche.tipi_prestazione tp ON tp.id = p.tipo_prestazione_id
   WHERE tp.codice_interno IN ('TEST_WDF','TEST_WDF2','TEST_WDF3'));
DELETE FROM pratiche.pratiche WHERE tipo_prestazione_id IN (
  SELECT id FROM pratiche.tipi_prestazione WHERE codice_interno IN ('TEST_WDF','TEST_WDF2','TEST_WDF3'));
DELETE FROM pratiche.template_flussi WHERE tipo_prestazione_id IN (
  SELECT id FROM pratiche.tipi_prestazione WHERE codice_interno IN ('TEST_WDF','TEST_WDF2','TEST_WDF3'));
DELETE FROM pratiche.tipi_prestazione
 WHERE codice_interno IN ('TEST_WDF','TEST_WDF2','TEST_WDF3');

-- Da qui in poi tutto e' reversibile: ROLLBACK in fondo al file.
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
VALUES ('APERTA','APERTA','Aperta',true)
ON CONFLICT (codice_interno) DO NOTHING;
INSERT INTO config.priorita_pratiche (codice, codice_interno, descrizione, sequenza, attivo)
VALUES ('NORMALE','NORMALE','Normale',20,true) ON CONFLICT (codice_interno) DO NOTHING;

CREATE TEMP TABLE tmp_wdf_refs AS
SELECT
  script.fn_pgtap_emittente_operatore() AS emittente_id,
  (SELECT id FROM config.stati_pratiche WHERE codice_interno='APERTA') AS st_aperta,
  (SELECT id FROM config.priorita_pratiche WHERE codice_interno='NORMALE') AS priorita_id;

SELECT ok(
  (SELECT emittente_id IS NOT NULL AND st_aperta IS NOT NULL AND priorita_id IS NOT NULL
     FROM tmp_wdf_refs),
  '0. Precondizioni soddisfatte (emittente, stato, priorita)'
);

-- =========================================================
-- 1) Bootstrap: nuovo tipo -> preset v1 PUBBLICATA
-- =========================================================
CREATE TEMP TABLE tmp_wdf_tp AS WITH ins AS (
  INSERT INTO pratiche.tipi_prestazione (codice, codice_interno, descrizione, attivo)
  VALUES ('TEST_WDF','TEST_WDF','Workflow definizioni fase 0',true)
  ON CONFLICT (codice_interno) DO UPDATE SET descrizione=EXCLUDED.descrizione RETURNING id)
SELECT id AS tp_id FROM ins;

CREATE TEMP TABLE tmp_wdf_preset AS
SELECT wd.id AS preset_id
  FROM pratiche.workflow_definizioni wd
 WHERE wd.tipo_prestazione_id = (SELECT tp_id FROM tmp_wdf_tp)
   AND wd.emittente_fiscale_id IS NULL
   AND wd.stato = 'PUBBLICATA';

SELECT is(
  (SELECT count(*) FROM pratiche.workflow_definizioni wd
    WHERE wd.tipo_prestazione_id = (SELECT tp_id FROM tmp_wdf_tp)
      AND wd.emittente_fiscale_id IS NULL AND wd.stato = 'PUBBLICATA'
      AND wd.versione = 1),
  1::bigint,
  '1. Bootstrap: il nuovo tipo ha il preset v1 PUBBLICATA (trigger z90)'
);

-- =========================================================
-- 2) Auto-default: template senza definizione_id -> preset del tipo
-- =========================================================
INSERT INTO pratiche.template_flussi (tipo_prestazione_id, codice, descrizione, sequenza, obbligatorio, attivo)
VALUES ((SELECT tp_id FROM tmp_wdf_tp),'WDF_STEP','Step di test',10,true,true);

SELECT is(
  (SELECT tf.definizione_id FROM pratiche.template_flussi tf
    WHERE tf.tipo_prestazione_id = (SELECT tp_id FROM tmp_wdf_tp) AND tf.codice='WDF_STEP'),
  (SELECT preset_id FROM tmp_wdf_preset),
  '2. Auto-default: template senza definizione_id agganciato al preset del tipo'
);

-- =========================================================
-- 3) Auto-pin: pratica senza definizione_id -> preset del tipo
-- =========================================================
CREATE TEMP TABLE tmp_wdf_p AS WITH ins AS (
  INSERT INTO pratiche.pratiche (emittente_fiscale_id, tipo_prestazione_id, stato_id, priorita_id)
  VALUES ((SELECT emittente_id FROM tmp_wdf_refs),(SELECT tp_id FROM tmp_wdf_tp),
          (SELECT st_aperta FROM tmp_wdf_refs),(SELECT priorita_id FROM tmp_wdf_refs))
  RETURNING id, definizione_id)
SELECT id AS pratica_id, definizione_id FROM ins;

SELECT is(
  (SELECT definizione_id FROM tmp_wdf_p),
  (SELECT preset_id FROM tmp_wdf_preset),
  '3. Auto-pin: pratica senza definizione_id pinnata al preset del tipo'
);

-- =========================================================
-- 4) fn_risolvi_definizione: emittente senza fork -> preset
-- =========================================================
SELECT is(
  pratiche.fn_risolvi_definizione(
    (SELECT tp_id FROM tmp_wdf_tp),
    (SELECT emittente_id FROM tmp_wdf_refs)),
  (SELECT preset_id FROM tmp_wdf_preset),
  '4. fn_risolvi_definizione: emittente senza edizione propria -> preset'
);

-- =========================================================
-- 5) 507: tipo senza alcuna PUBBLICATA -> errore parlante
--    (preset cancellato a mano; nessun figlio ancora agganciato)
-- =========================================================
CREATE TEMP TABLE tmp_wdf_tp2 AS WITH ins AS (
  INSERT INTO pratiche.tipi_prestazione (codice, codice_interno, descrizione, attivo)
  VALUES ('TEST_WDF2','TEST_WDF2','Workflow definizioni senza preset',true)
  ON CONFLICT (codice_interno) DO UPDATE SET descrizione=EXCLUDED.descrizione RETURNING id)
SELECT id AS tp_id FROM ins;
DELETE FROM pratiche.workflow_definizioni
 WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_wdf_tp2);

SELECT throws_like(
  format($q$INSERT INTO pratiche.template_flussi
              (tipo_prestazione_id, codice, descrizione, sequenza, attivo)
            VALUES (%s, 'WDF2_STEP', 'Step orfano', 10, true)$q$,
    (SELECT tp_id FROM tmp_wdf_tp2)),
  '%Nessuna definizione workflow pubblicata%',
  '5. Tipo senza preset PUBBLICATA: auto-default fallisce con 507 parlante'
);

-- =========================================================
-- 6) Una sola PUBBLICATA per scope (indice unico parziale, NULLS NOT DISTINCT)
-- =========================================================
SELECT throws_ok(
  format($q$INSERT INTO pratiche.workflow_definizioni
              (tipo_prestazione_id, emittente_fiscale_id, versione, stato, descrizione)
            VALUES (%s, NULL, 2, 'PUBBLICATA', 'seconda pubblicata (vietata)')$q$,
    (SELECT tp_id FROM tmp_wdf_tp)),
  '23505', NULL,
  '6. Seconda PUBBLICATA sullo stesso scope preset -> rifiutata (unique parziale)'
);

-- =========================================================
-- 7) uq (definizione_id, codice): codice duplicato nella stessa definizione
-- =========================================================
SELECT throws_ok(
  format($q$INSERT INTO pratiche.template_flussi
              (tipo_prestazione_id, codice, descrizione, sequenza, attivo)
            VALUES (%s, 'WDF_STEP', 'Duplicato di codice', 20, true)$q$,
    (SELECT tp_id FROM tmp_wdf_tp)),
  '23505', NULL,
  '7. Codice step duplicato nella stessa definizione -> rifiutato (unique per-definizione)'
);

-- =========================================================
-- 8) FK composita: template con definizione di un ALTRO tipo
-- =========================================================
CREATE TEMP TABLE tmp_wdf_tp3 AS WITH ins AS (
  INSERT INTO pratiche.tipi_prestazione (codice, codice_interno, descrizione, attivo)
  VALUES ('TEST_WDF3','TEST_WDF3','Tipo terzo per FK composita',true)
  ON CONFLICT (codice_interno) DO UPDATE SET descrizione=EXCLUDED.descrizione RETURNING id)
SELECT id AS tp_id FROM ins;

SELECT throws_ok(
  format($q$INSERT INTO pratiche.template_flussi
              (tipo_prestazione_id, codice, descrizione, sequenza, attivo, definizione_id)
            VALUES (%s, 'WDF_CROSS', 'Definizione di altro tipo', 30, true,
                    (SELECT wd.id FROM pratiche.workflow_definizioni wd
                      WHERE wd.tipo_prestazione_id = %s
                        AND wd.emittente_fiscale_id IS NULL AND wd.stato='PUBBLICATA'))$q$,
    (SELECT tp_id FROM tmp_wdf_tp),
    (SELECT tp_id FROM tmp_wdf_tp3)),
  '23503', NULL,
  '8. FK composita: definizione di un altro tipo -> rifiutata (coerenza tipo per costruzione)'
);

-- =========================================================
-- 9) NOT NULL attivo su entrambe le colonne (backfill 20260702-25)
-- =========================================================
SELECT ok(
  (SELECT bool_and(a.attnotnull)
     FROM pg_attribute a
    WHERE (a.attrelid, a.attname) IN (
            ('pratiche.template_flussi'::regclass, 'definizione_id'),
            ('pratiche.pratiche'::regclass,        'definizione_id'))),
  '9. definizione_id NOT NULL su template_flussi e pratiche (post backfill)'
);

-- =========================================================
-- 10) Cleanup (l'ordine dimostra la cascata: figli -> tipi -> definizioni)
-- =========================================================
DELETE FROM pratiche.giornale WHERE pratica_id IN (
  SELECT id FROM pratiche.pratiche WHERE tipo_prestazione_id IN (
    (SELECT tp_id FROM tmp_wdf_tp),(SELECT tp_id FROM tmp_wdf_tp2),(SELECT tp_id FROM tmp_wdf_tp3)));
DELETE FROM pratiche.flussi WHERE pratica_id IN (
  SELECT id FROM pratiche.pratiche WHERE tipo_prestazione_id IN (
    (SELECT tp_id FROM tmp_wdf_tp),(SELECT tp_id FROM tmp_wdf_tp2),(SELECT tp_id FROM tmp_wdf_tp3)));
DELETE FROM pratiche.pratiche WHERE tipo_prestazione_id IN (
    (SELECT tp_id FROM tmp_wdf_tp),(SELECT tp_id FROM tmp_wdf_tp2),(SELECT tp_id FROM tmp_wdf_tp3));
DELETE FROM pratiche.template_flussi WHERE tipo_prestazione_id IN (
    (SELECT tp_id FROM tmp_wdf_tp),(SELECT tp_id FROM tmp_wdf_tp2),(SELECT tp_id FROM tmp_wdf_tp3));
DELETE FROM pratiche.tipi_prestazione
 WHERE codice_interno IN ('TEST_WDF','TEST_WDF2','TEST_WDF3');

SELECT pass('10. Cleanup completato (delete tipo -> cascata definizioni ok)');

SELECT * FROM finish();

-- Le DELETE della sezione 10 restano: sono l'asserzione sulla cascata, e vanno
-- eseguite. Ma non devono nemmeno loro lasciare traccia — il ROLLBACK annulla
-- tutto quanto e' successo dopo BEGIN, compreso cio' che il test ha creato per
-- misurarsi. Se il file muore prima di arrivare qui, la transazione viene
-- comunque abbandonata alla chiusura della sessione: e' il senso della modifica.
ROLLBACK;
