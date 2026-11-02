-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: guard runtime di CLASSE ESITO al completamento del flusso.
--       (brief-db-step-dominio-e-definizioni-versionate Parte 1 / D1-2;
--        origine: incidente PRA-0000243 — SMISTAMENTO chiuso con POSITIVO)
--       trg_flussi_a10_guard_esito_classe_ins_upd (20260702-17):
--         step DOMINIO      => esito di ramo (is_verdetto=false)
--         step non-DOMINIO  => verdetto      (is_verdetto=true)
--         -> FLUSSI_ESITO_NON_AMMESSO (504), scoped alla transizione.
--
-- Indice test:
-- 0) Precondizioni (stati, esiti con is_verdetto, priorita, refs)
-- 1) Setup (tipo TEST_GEC: GEC_DOM DOMINIO + GEC_MAN MANUALE + GEC_GUARDIA
--    obbligatorio mai toccato che tiene le pratiche APERTE; 3 pratiche)
-- 2) [DOMINIO] completare con POSITIVO (verdetto) -> throws 504 (il caso PRA-0000243)
-- 3) [DOMINIO] completare con MERCE_PRESENTE -> ammesso
-- 4) [DOMINIO] completare con SOLO_SERVIZI (pratica 2) -> ammesso
-- 5) [MANUALE] completare con MERCE_PRESENTE -> throws 504 (simmetrico)
-- 6) [MANUALE] completare con POSITIVO -> ammesso (non regressione)
-- 7) [legacy] step flippato a DOMINIO con flusso gia' COMPLETATO+verdetto:
--    UPDATE di colonna non di stato -> nessun raise (guard scoped alla transizione)
-- 8) [INSERT diretto] INSERT flusso gia' COMPLETATO con verdetto su step DOMINIO -> throws 504
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

SELECT plan(10);

-- =========================================================
-- 0) Precondizioni (idempotenti; is_verdetto esplicito: il default colonna
--    e' false e su DB vergine POSITIVO nascerebbe come non-verdetto)
-- =========================================================
INSERT INTO config.stati_pratiche (codice, codice_interno, descrizione, attivo)
VALUES ('APERTA','APERTA','Aperta',true),('CHIUSA','CHIUSA','Chiusa',true)
ON CONFLICT (codice_interno) DO NOTHING;
INSERT INTO config.stati_flussi_pratiche (codice, codice_interno, descrizione, attivo)
VALUES ('DA_ESEGUIRE','DA_ESEGUIRE','Da eseguire',true),
       ('IN_CORSO','IN_CORSO','In corso',true),
       ('COMPLETATO','COMPLETATO','Completato',true)
ON CONFLICT (codice_interno) DO NOTHING;
INSERT INTO config.esiti_flussi_pratiche (codice, codice_interno, descrizione, is_verdetto)
VALUES ('POSITIVO','POSITIVO','Esito positivo',true),
       ('MERCE_PRESENTE','MERCE_PRESENTE','Merce presente',false),
       ('SOLO_SERVIZI','SOLO_SERVIZI','Solo servizi',false)
ON CONFLICT (codice_interno) DO NOTHING;
INSERT INTO config.priorita_pratiche (codice, codice_interno, descrizione, sequenza, attivo)
VALUES ('NORMALE','NORMALE','Normale',20,true) ON CONFLICT (codice_interno) DO NOTHING;

CREATE TEMP TABLE tmp_gec_refs AS
SELECT
  script.fn_pgtap_emittente_operatore() AS emittente_id,
  (SELECT id FROM anagrafiche.soggetti ORDER BY id LIMIT 1) AS soggetto_id,
  (SELECT id FROM config.stati_pratiche WHERE codice_interno='APERTA')  AS st_aperta,
  (SELECT id FROM config.stati_flussi_pratiche WHERE codice_interno='DA_ESEGUIRE') AS sf_da,
  (SELECT id FROM config.stati_flussi_pratiche WHERE codice_interno='IN_CORSO')    AS sf_in,
  (SELECT id FROM config.stati_flussi_pratiche WHERE codice_interno='COMPLETATO')  AS sf_done,
  (SELECT id FROM config.priorita_pratiche WHERE codice_interno='NORMALE') AS priorita_id,
  (SELECT is_verdetto FROM config.esiti_flussi_pratiche WHERE codice_interno='POSITIVO') AS positivo_verdetto;

SELECT ok(
  (SELECT emittente_id IS NOT NULL AND st_aperta IS NOT NULL
      AND sf_da IS NOT NULL AND sf_in IS NOT NULL AND sf_done IS NOT NULL
      AND priorita_id IS NOT NULL AND positivo_verdetto
     FROM tmp_gec_refs),
  '0. Precondizioni soddisfatte (stati, esiti con is_verdetto corretto, refs)'
);

-- =========================================================
-- 1) Setup: tipo TEST_GEC + 3 template + 3 pratiche.
--    GEC_GUARDIA (obbligatorio, mai istanziato) evita l'autochiusura delle
--    pratiche quando gli altri step completano.
-- =========================================================
CREATE TEMP TABLE tmp_gec_tp AS WITH ins AS (
  INSERT INTO pratiche.tipi_prestazione (codice, codice_interno, descrizione, attivo)
  VALUES ('TEST_GEC','TEST_GEC','Guard esito classe',true)
  ON CONFLICT (codice_interno) DO UPDATE SET descrizione=EXCLUDED.descrizione RETURNING id)
SELECT id AS tp_id FROM ins;
CREATE TEMP TABLE tmp_gec_tf AS WITH ins AS (
  INSERT INTO pratiche.template_flussi
         (tipo_prestazione_id, codice, descrizione, sequenza, obbligatorio, attivo, direzione, modalita_esito)
  VALUES ((SELECT tp_id FROM tmp_gec_tp),'GEC_DOM','Step a esito di dominio',10,true,true,'INTERNA','DOMINIO'),
         ((SELECT tp_id FROM tmp_gec_tp),'GEC_MAN','Step manuale',20,true,true,'INTERNA','MANUALE'),
         ((SELECT tp_id FROM tmp_gec_tp),'GEC_GUARDIA','Guardia anti-autochiusura',90,true,true,'INTERNA','MANUALE')
  ON CONFLICT (definizione_id, codice) DO UPDATE
     SET descrizione=EXCLUDED.descrizione, modalita_esito=EXCLUDED.modalita_esito
  RETURNING id, codice)
SELECT max(id) FILTER (WHERE codice='GEC_DOM') AS tf_dom,
       max(id) FILTER (WHERE codice='GEC_MAN') AS tf_man
  FROM ins;

CREATE TEMP TABLE tmp_gec_p1 AS WITH ins AS (
  INSERT INTO pratiche.pratiche (emittente_fiscale_id, tipo_prestazione_id, soggetto_id, stato_id, priorita_id)
  VALUES ((SELECT emittente_id FROM tmp_gec_refs),(SELECT tp_id FROM tmp_gec_tp),
          (SELECT soggetto_id FROM tmp_gec_refs),(SELECT st_aperta FROM tmp_gec_refs),
          (SELECT priorita_id FROM tmp_gec_refs)) RETURNING id)
SELECT id AS pratica_id FROM ins;
CREATE TEMP TABLE tmp_gec_p2 AS WITH ins AS (
  INSERT INTO pratiche.pratiche (emittente_fiscale_id, tipo_prestazione_id, soggetto_id, stato_id, priorita_id)
  VALUES ((SELECT emittente_id FROM tmp_gec_refs),(SELECT tp_id FROM tmp_gec_tp),
          (SELECT soggetto_id FROM tmp_gec_refs),(SELECT st_aperta FROM tmp_gec_refs),
          (SELECT priorita_id FROM tmp_gec_refs)) RETURNING id)
SELECT id AS pratica_id FROM ins;
CREATE TEMP TABLE tmp_gec_p3 AS WITH ins AS (
  INSERT INTO pratiche.pratiche (emittente_fiscale_id, tipo_prestazione_id, soggetto_id, stato_id, priorita_id)
  VALUES ((SELECT emittente_id FROM tmp_gec_refs),(SELECT tp_id FROM tmp_gec_tp),
          (SELECT soggetto_id FROM tmp_gec_refs),(SELECT st_aperta FROM tmp_gec_refs),
          (SELECT priorita_id FROM tmp_gec_refs)) RETURNING id)
SELECT id AS pratica_id FROM ins;

-- Flussi: GEC_DOM in P1 e P2, GEC_MAN in P3 — tutti portati a IN_CORSO.
INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id, sequenza)
VALUES ((SELECT pratica_id FROM tmp_gec_p1),(SELECT tf_dom FROM tmp_gec_tf),(SELECT sf_da FROM tmp_gec_refs),10),
       ((SELECT pratica_id FROM tmp_gec_p2),(SELECT tf_dom FROM tmp_gec_tf),(SELECT sf_da FROM tmp_gec_refs),10),
       ((SELECT pratica_id FROM tmp_gec_p3),(SELECT tf_man FROM tmp_gec_tf),(SELECT sf_da FROM tmp_gec_refs),20);
UPDATE pratiche.flussi SET stato_id=(SELECT sf_in FROM tmp_gec_refs)
 WHERE pratica_id IN ((SELECT pratica_id FROM tmp_gec_p1),(SELECT pratica_id FROM tmp_gec_p2),
                      (SELECT pratica_id FROM tmp_gec_p3));

SELECT ok(
  (SELECT tf_dom IS NOT NULL AND tf_man IS NOT NULL FROM tmp_gec_tf)
  AND (SELECT count(*) = 3 FROM pratiche.flussi f
        WHERE f.pratica_id IN ((SELECT pratica_id FROM tmp_gec_p1),(SELECT pratica_id FROM tmp_gec_p2),
                               (SELECT pratica_id FROM tmp_gec_p3))
          AND f.stato_id = (SELECT sf_in FROM tmp_gec_refs)),
  '1. Setup completato (template DOMINIO/MANUALE + 3 pratiche, flussi IN_CORSO)'
);

-- =========================================================
-- 2) [DOMINIO] completare con POSITIVO (verdetto) -> throws 504.
--    E' esattamente il caso PRA-0000243.
-- =========================================================
SELECT throws_like(
  format($q$UPDATE pratiche.flussi SET stato_id=%s, esito='POSITIVO'
             WHERE pratica_id=%s AND template_flusso_id=%s$q$,
    (SELECT sf_done FROM tmp_gec_refs),
    (SELECT pratica_id FROM tmp_gec_p1),
    (SELECT tf_dom FROM tmp_gec_tf)),
  '%non ammesso per lo step%',
  '2. [DOMINIO] verdetto POSITIVO al completamento -> rifiutato (504, caso PRA-0000243)'
);

-- =========================================================
-- 3) [DOMINIO] completare con MERCE_PRESENTE -> ammesso
-- =========================================================
SELECT lives_ok(
  format($q$UPDATE pratiche.flussi SET stato_id=%s, esito='MERCE_PRESENTE'
             WHERE pratica_id=%s AND template_flusso_id=%s$q$,
    (SELECT sf_done FROM tmp_gec_refs),
    (SELECT pratica_id FROM tmp_gec_p1),
    (SELECT tf_dom FROM tmp_gec_tf)),
  '3. [DOMINIO] esito di ramo MERCE_PRESENTE -> ammesso'
);

-- =========================================================
-- 4) [DOMINIO] completare con SOLO_SERVIZI (pratica 2) -> ammesso
-- =========================================================
SELECT lives_ok(
  format($q$UPDATE pratiche.flussi SET stato_id=%s, esito='SOLO_SERVIZI'
             WHERE pratica_id=%s AND template_flusso_id=%s$q$,
    (SELECT sf_done FROM tmp_gec_refs),
    (SELECT pratica_id FROM tmp_gec_p2),
    (SELECT tf_dom FROM tmp_gec_tf)),
  '4. [DOMINIO] esito di ramo SOLO_SERVIZI -> ammesso'
);

-- =========================================================
-- 5) [MANUALE] completare con MERCE_PRESENTE -> throws 504 (simmetrico:
--    prima questo caso era fermato solo dal guard BE lato operatore)
-- =========================================================
SELECT throws_like(
  format($q$UPDATE pratiche.flussi SET stato_id=%s, esito='MERCE_PRESENTE'
             WHERE pratica_id=%s AND template_flusso_id=%s$q$,
    (SELECT sf_done FROM tmp_gec_refs),
    (SELECT pratica_id FROM tmp_gec_p3),
    (SELECT tf_man FROM tmp_gec_tf)),
  '%non ammesso per lo step%',
  '5. [MANUALE] esito di ramo MERCE_PRESENTE -> rifiutato (504, difesa simmetrica)'
);

-- =========================================================
-- 6) [MANUALE] completare con POSITIVO -> ammesso (non regressione)
-- =========================================================
SELECT lives_ok(
  format($q$UPDATE pratiche.flussi SET stato_id=%s, esito='POSITIVO'
             WHERE pratica_id=%s AND template_flusso_id=%s$q$,
    (SELECT sf_done FROM tmp_gec_refs),
    (SELECT pratica_id FROM tmp_gec_p3),
    (SELECT tf_man FROM tmp_gec_tf)),
  '6. [MANUALE] verdetto POSITIVO -> ammesso (non regressione)'
);

-- =========================================================
-- 7) [legacy] GEC_MAN flippato a DOMINIO: il flusso di P3 (COMPLETATO con
--    POSITIVO) diventa una riga "storicamente sbagliata" come il flusso 543
--    di PRA-0000243. Toccare colonne non di stato NON deve sollevare
--    (guard scoped alla transizione).
-- =========================================================
UPDATE pratiche.template_flussi
   SET modalita_esito = 'DOMINIO'
 WHERE id = (SELECT tf_man FROM tmp_gec_tf);

SELECT lives_ok(
  format($q$UPDATE pratiche.flussi SET note_esito='nota post-completamento'
             WHERE pratica_id=%s AND template_flusso_id=%s$q$,
    (SELECT pratica_id FROM tmp_gec_p3),
    (SELECT tf_man FROM tmp_gec_tf)),
  '7. [legacy] riga gia'' COMPLETATA con verdetto su step ora DOMINIO resta toccabile'
);

-- =========================================================
-- 8) [INSERT diretto] INSERT flusso gia' COMPLETATO con verdetto su step
--    DOMINIO -> throws 504 (copre il ramo TG_OP=INSERT; ripetibilita
--    SE_NON_POSITIVO ammette la ripetizione: l'istanza precedente di GEC_DOM
--    in P1 e' MERCE_PRESENTE, non POSITIVO).
-- =========================================================
SELECT throws_like(
  format($q$INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id, sequenza, esito)
            VALUES (%s, %s, %s, 11, 'POSITIVO')$q$,
    (SELECT pratica_id FROM tmp_gec_p1),
    (SELECT tf_dom FROM tmp_gec_tf),
    (SELECT sf_done FROM tmp_gec_refs)),
  '%non ammesso per lo step%',
  '8. [INSERT diretto] COMPLETATO+verdetto su step DOMINIO -> rifiutato (504)'
);

-- =========================================================
-- 9) Cleanup
-- =========================================================
DELETE FROM pratiche.giornale WHERE pratica_id IN (
  SELECT id FROM pratiche.pratiche WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_gec_tp));
DELETE FROM pratiche.flussi WHERE pratica_id IN (
  SELECT id FROM pratiche.pratiche WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_gec_tp));
DELETE FROM pratiche.pratiche WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_gec_tp);
DELETE FROM pratiche.template_flussi WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_gec_tp);
DELETE FROM pratiche.tipi_prestazione WHERE codice_interno = 'TEST_GEC';

SELECT pass('9. Cleanup completato');

SELECT * FROM finish();

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia nulla dietro di se'. Le DELETE del cleanup restano
-- perche' dove sono un'asserzione devono girare davvero.
ROLLBACK;
