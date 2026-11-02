-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: chiusura pratica "nessun lavoro pendente" — bivio-per-esito + D1.
--       (brief-db-chiusura-pratica-nessun-lavoro-pendente)
--       - Bivio: 9013/9014-like obbligatori-su-ramo via prerequisito ESITO-aware.
--         Sul ramo merce bloccano la chiusura ANCHE senza istanza (check template-based,
--         niente deferral); sul ramo servizi sono ramo morto e non bloccano.
--       - D1: fn_pratica_flussi_aperti + fn_check_pratica_chiudibile clausola (b) +
--         guard chiusura manuale (err 501) + terminali data-driven.
--       - Fail-safe: creazione flusso su pratica terminale -> err 490 (rete che rende
--         inutile il deferral D2).
--
-- Indice test:
-- 0) Precondizioni (stati, esiti base+ramo, priorita, refs)
-- 1) Setup (tipo BIVIO SMIST/CONFERMA/INVIO esito-aware + tipo D1 OBBL/OPT + pratiche)
-- 2) [bivio merce] SMIST completa MERCE_PRESENTE -> APERTA (CONFERMA blocca senza istanza)
-- 3) [bivio merce] CONFERMA completa POSITIVO -> APERTA (INVIO ora percorribile blocca)
-- 4) [bivio merce] INVIO completa POSITIVO -> CHIUSA (nessun lavoro pendente)
-- 5) [bivio servizi] SMIST completa SOLO_SERVIZI -> CHIUSA (CONFERMA/INVIO ramo morto)
-- 6) [D1] OBBL completato con OPT (opzionale) istanziato aperto -> resta APERTA
-- 7) [D1] chiusura MANUALE con OPT aperto -> throws (501)
-- 8) [D1] OPT -> ANNULLATO poi chiusura manuale -> CHIUSA (via d'uscita)
-- 9) [fail-safe] creazione flusso su pratica CHIUSA -> throws (490)
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
       ('COMPLETATO','COMPLETATO','Completato',true),
       ('ANNULLATO','ANNULLATO','Annullato',true)
ON CONFLICT (codice_interno) DO NOTHING;
-- Esiti: base (POSITIVO, verdetto) + di ramo (MERCE_PRESENTE/SOLO_SERVIZI,
-- is_verdetto=false). Se il seed e' gia' applicato l'ON CONFLICT no-op; qui rende
-- il test auto-contenuto. is_verdetto ESPLICITO: il default colonna e' false e su
-- DB vergine POSITIVO nascerebbe non-verdetto (guard esito classe 504 lo rifiuterebbe).
INSERT INTO config.esiti_flussi_pratiche (codice, codice_interno, descrizione, is_verdetto)
VALUES ('POSITIVO','POSITIVO','Esito positivo',true),
       ('MERCE_PRESENTE','MERCE_PRESENTE','Merce presente',false),
       ('SOLO_SERVIZI','SOLO_SERVIZI','Solo servizi',false)
ON CONFLICT (codice_interno) DO NOTHING;
INSERT INTO config.priorita_pratiche (codice, codice_interno, descrizione, sequenza, attivo)
VALUES ('NORMALE','NORMALE','Normale',20,true) ON CONFLICT (codice_interno) DO NOTHING;

CREATE TEMP TABLE tmp_np_refs AS
SELECT
  script.fn_pgtap_emittente_operatore() AS emittente_id,
  (SELECT id FROM anagrafiche.soggetti ORDER BY id LIMIT 1) AS soggetto_id,
  (SELECT id FROM config.stati_pratiche WHERE codice_interno='APERTA')  AS st_aperta,
  (SELECT id FROM config.stati_pratiche WHERE codice_interno='CHIUSA')  AS st_chiusa,
  (SELECT id FROM config.stati_flussi_pratiche WHERE codice_interno='DA_ESEGUIRE') AS sf_da,
  (SELECT id FROM config.stati_flussi_pratiche WHERE codice_interno='IN_CORSO')    AS sf_in,
  (SELECT id FROM config.stati_flussi_pratiche WHERE codice_interno='COMPLETATO')  AS sf_done,
  (SELECT id FROM config.stati_flussi_pratiche WHERE codice_interno='ANNULLATO')   AS sf_ann,
  (SELECT id FROM config.priorita_pratiche WHERE codice_interno='NORMALE') AS priorita_id;

SELECT ok(
  (SELECT emittente_id IS NOT NULL AND st_aperta IS NOT NULL AND st_chiusa IS NOT NULL
      AND sf_da IS NOT NULL AND sf_in IS NOT NULL AND sf_done IS NOT NULL AND sf_ann IS NOT NULL
      AND priorita_id IS NOT NULL FROM tmp_np_refs),
  '0. Precondizioni soddisfatte (stati, esiti, priorita, refs)'
);

-- =========================================================
-- 1) Setup: tipo BIVIO + tipo D1 + pratiche
-- =========================================================
-- Tipo BIVIO: SMIST (bivio, obbligatorio) -> CONFERMA (obbl, prereq SMIST=MERCE_PRESENTE)
--             -> INVIO (obbl, prereq CONFERMA=POSITIVO). Nessun flusso di chiusura.
CREATE TEMP TABLE tmp_np_tp_biv AS WITH ins AS (
  INSERT INTO pratiche.tipi_prestazione (codice, codice_interno, descrizione, attivo)
  VALUES ('TEST_NP_BIVIO','TEST_NP_BIVIO','Bivio esito-aware',true)
  ON CONFLICT (codice_interno) DO UPDATE SET descrizione=EXCLUDED.descrizione RETURNING id)
SELECT id AS tp_id FROM ins;
-- NP_SMIST e' modalita_esito=DOMINIO (esito calcolato dal dominio): il guard
-- esito classe (20260702-17) ammette gli esiti di ramo SOLO sugli step DOMINIO.
CREATE TEMP TABLE tmp_np_tf_biv AS WITH ins AS (
  INSERT INTO pratiche.template_flussi (tipo_prestazione_id, codice, descrizione, sequenza, obbligatorio, attivo, modalita_esito)
  VALUES ((SELECT tp_id FROM tmp_np_tp_biv),'NP_SMIST','Smistamento (bivio)',10,true,true,'DOMINIO'),
         ((SELECT tp_id FROM tmp_np_tp_biv),'NP_CONFERMA','Conferma ordine',20,true,true,'MANUALE'),
         ((SELECT tp_id FROM tmp_np_tp_biv),'NP_INVIO','Invio a commessa',30,true,true,'MANUALE')
  ON CONFLICT (definizione_id, codice) DO UPDATE
     SET descrizione=EXCLUDED.descrizione, modalita_esito=EXCLUDED.modalita_esito RETURNING id, codice)
SELECT max(id) FILTER (WHERE codice='NP_SMIST')    AS tf_smist,
       max(id) FILTER (WHERE codice='NP_CONFERMA') AS tf_conf,
       max(id) FILTER (WHERE codice='NP_INVIO')    AS tf_invio
  FROM ins;
-- Prerequisiti esito-aware: CONFERMA <- SMIST(MERCE_PRESENTE); INVIO <- CONFERMA(POSITIVO).
INSERT INTO pratiche.template_flussi_prerequisiti (template_flusso_id, prerequisito_id, esito_richiesto)
VALUES ((SELECT tf_conf  FROM tmp_np_tf_biv),(SELECT tf_smist FROM tmp_np_tf_biv),'MERCE_PRESENTE'),
       ((SELECT tf_invio FROM tmp_np_tf_biv),(SELECT tf_conf  FROM tmp_np_tf_biv),'POSITIVO');

-- Tipo D1: OBBL (obbligatorio) + OPT (opzionale).
CREATE TEMP TABLE tmp_np_tp_d1 AS WITH ins AS (
  INSERT INTO pratiche.tipi_prestazione (codice, codice_interno, descrizione, attivo)
  VALUES ('TEST_NP_D1','TEST_NP_D1','Opzionale aperto (D1)',true)
  ON CONFLICT (codice_interno) DO UPDATE SET descrizione=EXCLUDED.descrizione RETURNING id)
SELECT id AS tp_id FROM ins;
CREATE TEMP TABLE tmp_np_tf_d1 AS WITH ins AS (
  INSERT INTO pratiche.template_flussi (tipo_prestazione_id, codice, descrizione, sequenza, obbligatorio, attivo)
  VALUES ((SELECT tp_id FROM tmp_np_tp_d1),'NP_OBBL','Obbligatorio',10,true,true),
         ((SELECT tp_id FROM tmp_np_tp_d1),'NP_OPT','Opzionale',20,false,true)
  ON CONFLICT (definizione_id, codice) DO UPDATE SET descrizione=EXCLUDED.descrizione RETURNING id, codice)
SELECT max(id) FILTER (WHERE codice='NP_OBBL') AS tf_obbl,
       max(id) FILTER (WHERE codice='NP_OPT')  AS tf_opt
  FROM ins;

-- Pratiche: bivio-merce, bivio-servizi, D1 (tutte APERTA).
CREATE TEMP TABLE tmp_np_p_merce AS WITH ins AS (
  INSERT INTO pratiche.pratiche (emittente_fiscale_id, tipo_prestazione_id, soggetto_id, stato_id, priorita_id)
  VALUES ((SELECT emittente_id FROM tmp_np_refs),(SELECT tp_id FROM tmp_np_tp_biv),
          (SELECT soggetto_id FROM tmp_np_refs),(SELECT st_aperta FROM tmp_np_refs),
          (SELECT priorita_id FROM tmp_np_refs)) RETURNING id)
SELECT id AS pratica_id FROM ins;
CREATE TEMP TABLE tmp_np_p_serv AS WITH ins AS (
  INSERT INTO pratiche.pratiche (emittente_fiscale_id, tipo_prestazione_id, soggetto_id, stato_id, priorita_id)
  VALUES ((SELECT emittente_id FROM tmp_np_refs),(SELECT tp_id FROM tmp_np_tp_biv),
          (SELECT soggetto_id FROM tmp_np_refs),(SELECT st_aperta FROM tmp_np_refs),
          (SELECT priorita_id FROM tmp_np_refs)) RETURNING id)
SELECT id AS pratica_id FROM ins;
CREATE TEMP TABLE tmp_np_p_d1 AS WITH ins AS (
  INSERT INTO pratiche.pratiche (emittente_fiscale_id, tipo_prestazione_id, soggetto_id, stato_id, priorita_id)
  VALUES ((SELECT emittente_id FROM tmp_np_refs),(SELECT tp_id FROM tmp_np_tp_d1),
          (SELECT soggetto_id FROM tmp_np_refs),(SELECT st_aperta FROM tmp_np_refs),
          (SELECT priorita_id FROM tmp_np_refs)) RETURNING id)
SELECT id AS pratica_id FROM ins;

SELECT ok(
  (SELECT pratica_id IS NOT NULL FROM tmp_np_p_merce)
  AND (SELECT pratica_id IS NOT NULL FROM tmp_np_p_serv)
  AND (SELECT pratica_id IS NOT NULL FROM tmp_np_p_d1)
  AND (SELECT tf_smist IS NOT NULL AND tf_conf IS NOT NULL AND tf_invio IS NOT NULL FROM tmp_np_tf_biv),
  '1. Setup completato (tipo bivio + tipo D1 + 3 pratiche)'
);

-- =========================================================
-- 2) [bivio merce] SMIST completa MERCE_PRESENTE -> resta APERTA
--    (CONFERMA obbligatorio+percorribile blocca ANCHE senza istanza a valle)
-- =========================================================
INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id, sequenza)
VALUES ((SELECT pratica_id FROM tmp_np_p_merce),(SELECT tf_smist FROM tmp_np_tf_biv),(SELECT sf_da FROM tmp_np_refs),10);
UPDATE pratiche.flussi SET stato_id=(SELECT sf_in FROM tmp_np_refs)
 WHERE pratica_id=(SELECT pratica_id FROM tmp_np_p_merce) AND template_flusso_id=(SELECT tf_smist FROM tmp_np_tf_biv);
UPDATE pratiche.flussi SET stato_id=(SELECT sf_done FROM tmp_np_refs), esito='MERCE_PRESENTE'
 WHERE pratica_id=(SELECT pratica_id FROM tmp_np_p_merce) AND template_flusso_id=(SELECT tf_smist FROM tmp_np_tf_biv);

SELECT is(
  (SELECT sp.codice_interno FROM pratiche.pratiche p JOIN config.stati_pratiche sp ON sp.id=p.stato_id
    WHERE p.id=(SELECT pratica_id FROM tmp_np_p_merce)),
  'APERTA',
  '2. [merce] SMIST=MERCE_PRESENTE: CONFERMA blocca (template-based, senza istanza) -> APERTA'
);

-- =========================================================
-- 3) [bivio merce] CONFERMA completa POSITIVO -> resta APERTA (INVIO ora blocca)
-- =========================================================
INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id, sequenza)
VALUES ((SELECT pratica_id FROM tmp_np_p_merce),(SELECT tf_conf FROM tmp_np_tf_biv),(SELECT sf_da FROM tmp_np_refs),20);
UPDATE pratiche.flussi SET stato_id=(SELECT sf_in FROM tmp_np_refs)
 WHERE pratica_id=(SELECT pratica_id FROM tmp_np_p_merce) AND template_flusso_id=(SELECT tf_conf FROM tmp_np_tf_biv);
UPDATE pratiche.flussi SET stato_id=(SELECT sf_done FROM tmp_np_refs), esito='POSITIVO'
 WHERE pratica_id=(SELECT pratica_id FROM tmp_np_p_merce) AND template_flusso_id=(SELECT tf_conf FROM tmp_np_tf_biv);

SELECT is(
  (SELECT sp.codice_interno FROM pratiche.pratiche p JOIN config.stati_pratiche sp ON sp.id=p.stato_id
    WHERE p.id=(SELECT pratica_id FROM tmp_np_p_merce)),
  'APERTA',
  '3. [merce] CONFERMA=POSITIVO: INVIO diventa percorribile e blocca -> APERTA'
);

-- =========================================================
-- 4) [bivio merce] INVIO completa POSITIVO -> CHIUSA
-- =========================================================
INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id, sequenza)
VALUES ((SELECT pratica_id FROM tmp_np_p_merce),(SELECT tf_invio FROM tmp_np_tf_biv),(SELECT sf_da FROM tmp_np_refs),30);
UPDATE pratiche.flussi SET stato_id=(SELECT sf_in FROM tmp_np_refs)
 WHERE pratica_id=(SELECT pratica_id FROM tmp_np_p_merce) AND template_flusso_id=(SELECT tf_invio FROM tmp_np_tf_biv);
UPDATE pratiche.flussi SET stato_id=(SELECT sf_done FROM tmp_np_refs), esito='POSITIVO'
 WHERE pratica_id=(SELECT pratica_id FROM tmp_np_p_merce) AND template_flusso_id=(SELECT tf_invio FROM tmp_np_tf_biv);

SELECT is(
  (SELECT sp.codice_interno FROM pratiche.pratiche p JOIN config.stati_pratiche sp ON sp.id=p.stato_id
    WHERE p.id=(SELECT pratica_id FROM tmp_np_p_merce)),
  'CHIUSA',
  '4. [merce] INVIO=POSITIVO: tutti gli obbligatori fatti, nessun flusso aperto -> CHIUSA'
);

-- =========================================================
-- 5) [bivio servizi] SMIST completa SOLO_SERVIZI -> CHIUSA (CONFERMA/INVIO ramo morto)
-- =========================================================
INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id, sequenza)
VALUES ((SELECT pratica_id FROM tmp_np_p_serv),(SELECT tf_smist FROM tmp_np_tf_biv),(SELECT sf_da FROM tmp_np_refs),10);
UPDATE pratiche.flussi SET stato_id=(SELECT sf_in FROM tmp_np_refs)
 WHERE pratica_id=(SELECT pratica_id FROM tmp_np_p_serv) AND template_flusso_id=(SELECT tf_smist FROM tmp_np_tf_biv);
UPDATE pratiche.flussi SET stato_id=(SELECT sf_done FROM tmp_np_refs), esito='SOLO_SERVIZI'
 WHERE pratica_id=(SELECT pratica_id FROM tmp_np_p_serv) AND template_flusso_id=(SELECT tf_smist FROM tmp_np_tf_biv);

SELECT is(
  (SELECT sp.codice_interno FROM pratiche.pratiche p JOIN config.stati_pratiche sp ON sp.id=p.stato_id
    WHERE p.id=(SELECT pratica_id FROM tmp_np_p_serv)),
  'CHIUSA',
  '5. [servizi] SMIST=SOLO_SERVIZI: CONFERMA/INVIO ramo morto (prereq esito non matcha) -> CHIUSA'
);

-- =========================================================
-- 6) [D1] OBBL completato con OPT (opzionale) istanziato APERTO -> resta APERTA
--    (senza D1 la pratica si chiuderebbe: OPT e' obbligatorio=false)
-- =========================================================
INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id, sequenza)
VALUES ((SELECT pratica_id FROM tmp_np_p_d1),(SELECT tf_opt  FROM tmp_np_tf_d1),(SELECT sf_da FROM tmp_np_refs),20),
       ((SELECT pratica_id FROM tmp_np_p_d1),(SELECT tf_obbl FROM tmp_np_tf_d1),(SELECT sf_da FROM tmp_np_refs),10);
-- OPT resta DA_ESEGUIRE (aperto). Completa OBBL.
UPDATE pratiche.flussi SET stato_id=(SELECT sf_in FROM tmp_np_refs)
 WHERE pratica_id=(SELECT pratica_id FROM tmp_np_p_d1) AND template_flusso_id=(SELECT tf_obbl FROM tmp_np_tf_d1);
UPDATE pratiche.flussi SET stato_id=(SELECT sf_done FROM tmp_np_refs), esito='POSITIVO'
 WHERE pratica_id=(SELECT pratica_id FROM tmp_np_p_d1) AND template_flusso_id=(SELECT tf_obbl FROM tmp_np_tf_d1);

SELECT is(
  (SELECT sp.codice_interno FROM pratiche.pratiche p JOIN config.stati_pratiche sp ON sp.id=p.stato_id
    WHERE p.id=(SELECT pratica_id FROM tmp_np_p_d1)),
  'APERTA',
  '6. [D1] OBBL completato ma OPT (opzionale) istanziato aperto -> non si auto-chiude'
);

-- =========================================================
-- 7) [D1] chiusura MANUALE con OPT aperto -> throws (501)
-- =========================================================
SELECT throws_like(
  format('UPDATE pratiche.pratiche SET stato_id=%s WHERE id=%s',
    (SELECT st_chiusa FROM tmp_np_refs),
    (SELECT pratica_id FROM tmp_np_p_d1)),
  '%flussi ancora aperti%',
  '7. [D1] chiusura manuale con flusso opzionale aperto -> errore 501 (stesso predicato dell''auto)'
);

-- =========================================================
-- 8) [D1] OPT -> ANNULLATO poi chiusura manuale -> CHIUSA (via d'uscita)
-- =========================================================
UPDATE pratiche.flussi SET stato_id=(SELECT sf_ann FROM tmp_np_refs)
 WHERE pratica_id=(SELECT pratica_id FROM tmp_np_p_d1) AND template_flusso_id=(SELECT tf_opt FROM tmp_np_tf_d1);
UPDATE pratiche.pratiche SET stato_id=(SELECT st_chiusa FROM tmp_np_refs)
 WHERE id=(SELECT pratica_id FROM tmp_np_p_d1);

SELECT is(
  (SELECT sp.codice_interno FROM pratiche.pratiche p JOIN config.stati_pratiche sp ON sp.id=p.stato_id
    WHERE p.id=(SELECT pratica_id FROM tmp_np_p_d1)),
  'CHIUSA',
  '8. [D1] annullato OPT (->ANNULLATO), la chiusura manuale ora passa -> CHIUSA'
);

-- =========================================================
-- 9) [fail-safe] creazione flusso su pratica CHIUSA (terminale) -> throws (490)
--    E' la rete che rende inutile il deferral D2: il fallimento e' rumoroso.
-- =========================================================
SELECT throws_like(
  format('INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id, sequenza) VALUES (%s, %s, %s, 99)',
    (SELECT pratica_id FROM tmp_np_p_d1),
    (SELECT tf_opt FROM tmp_np_tf_d1),
    (SELECT sf_da FROM tmp_np_refs)),
  '%stato terminale%',
  '9. [fail-safe] nuovo flusso su pratica CHIUSA -> errore 490 (guard pratica-terminale)'
);

-- =========================================================
-- 10) Cleanup
-- =========================================================
DELETE FROM pratiche.giornale WHERE pratica_id IN (
  SELECT id FROM pratiche.pratiche WHERE tipo_prestazione_id IN (
    (SELECT tp_id FROM tmp_np_tp_biv),(SELECT tp_id FROM tmp_np_tp_d1)));
DELETE FROM pratiche.flussi WHERE pratica_id IN (
  SELECT id FROM pratiche.pratiche WHERE tipo_prestazione_id IN (
    (SELECT tp_id FROM tmp_np_tp_biv),(SELECT tp_id FROM tmp_np_tp_d1)));
DELETE FROM pratiche.pratiche WHERE tipo_prestazione_id IN (
    (SELECT tp_id FROM tmp_np_tp_biv),(SELECT tp_id FROM tmp_np_tp_d1));
DELETE FROM pratiche.template_flussi_prerequisiti WHERE template_flusso_id IN (
  SELECT id FROM pratiche.template_flussi WHERE tipo_prestazione_id IN (
    (SELECT tp_id FROM tmp_np_tp_biv),(SELECT tp_id FROM tmp_np_tp_d1)));
DELETE FROM pratiche.template_flussi WHERE tipo_prestazione_id IN (
    (SELECT tp_id FROM tmp_np_tp_biv),(SELECT tp_id FROM tmp_np_tp_d1));
DELETE FROM pratiche.tipi_prestazione WHERE codice_interno IN ('TEST_NP_BIVIO','TEST_NP_D1');

SELECT pass('10. Cleanup completato');

SELECT * FROM finish();

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia nulla dietro di se'. Le DELETE del cleanup restano
-- perche' dove sono un'asserzione devono girare davvero.
ROLLBACK;
