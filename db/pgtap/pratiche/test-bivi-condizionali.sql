-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: bivi condizionali via prerequisiti esito-aware + semantica
--       di chiusura con ramo morto (D4, analisi-pratiche-workflow-v2).
--       Bivio:  APPROVAZIONE --POSITIVO--> CONFERMA
--                            --NEGATIVO--> NEGOZIAZIONE
--       Tutti gli step obbligatori: la chiusura richiede gli step
--       percorribili, MA il ramo morto (esito opposto) non blocca
--       (fn_check_chiusura_pratica + trg_pratiche_a10_guard_chiusura_flussi_upd).
--
-- Indice test:
-- 0) Precondizioni (provisioning + verifica)
-- 1) Setup: tipo bivio, 3 template obbligatori, 2 prerequisiti esito-aware, 2 pratiche
-- 2) P1 (esito POSITIVO): CONFERMA eseguibile (ramo coerente)
-- 3) P1: NEGOZIAZIONE bloccata dai prerequisiti (ramo opposto)
-- 4) P1: fn_check_chiusura — NEGOZIAZIONE ramo morto (percorribile=false, bloccante=false)
-- 5) P1: chiusura vietata con CONFERMA obbligatoria non completata
-- 6) P1: completata CONFERMA, AUTO-chiusura (ramo morto obbligatorio non blocca)
-- 7) P2 (esito NEGATIVO): NEGOZIAZIONE eseguibile (ramo coerente)
-- 8) P2: CONFERMA bloccata dai prerequisiti (ramo opposto)
-- 9) P2: completata NEGOZIAZIONE, AUTO-chiusura (CONFERMA e' ramo morto)
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

SELECT plan(10);

-- =========================================================
-- 0) Precondizioni: provisioning config data (idempotente)
-- =========================================================
INSERT INTO config.stati_pratiche (codice, codice_interno, descrizione, attivo)
VALUES
  ('BOZZA', 'BOZZA', 'Bozza', true),
  ('APERTA', 'APERTA', 'Aperta', true),
  ('CHIUSA', 'CHIUSA', 'Chiusa', true)
ON CONFLICT (codice_interno) DO NOTHING;
INSERT INTO config.stati_flussi_pratiche (codice, codice_interno, descrizione, attivo)
VALUES
  ('DA_ESEGUIRE', 'DA_ESEGUIRE', 'Da eseguire', true),
  ('IN_CORSO', 'IN_CORSO', 'In corso', true),
  ('COMPLETATO', 'COMPLETATO', 'Completato', true)
ON CONFLICT (codice_interno) DO NOTHING;
INSERT INTO config.priorita_pratiche (codice, codice_interno, descrizione, sequenza, attivo)
VALUES ('NORMALE', 'NORMALE', 'Normale', 20, true) ON CONFLICT (codice_interno) DO NOTHING;

CREATE TEMP TABLE tmp_bv_refs AS
SELECT
  script.fn_pgtap_emittente_operatore() AS emittente_id,
  (SELECT id FROM config.stati_pratiche WHERE codice_interno = 'BOZZA') AS st_bozza,
  (SELECT id FROM config.stati_pratiche WHERE codice_interno = 'APERTA') AS st_aperta,
  (SELECT id FROM config.stati_pratiche WHERE codice_interno = 'CHIUSA') AS st_chiusa,
  (SELECT id FROM config.stati_flussi_pratiche WHERE codice_interno = 'DA_ESEGUIRE') AS sf_da_eseguire,
  (SELECT id FROM config.stati_flussi_pratiche WHERE codice_interno = 'IN_CORSO') AS sf_in_corso,
  (SELECT id FROM config.stati_flussi_pratiche WHERE codice_interno = 'COMPLETATO') AS sf_completato,
  (SELECT id FROM config.priorita_pratiche WHERE codice_interno = 'NORMALE') AS priorita_id;

SELECT ok(
    (SELECT emittente_id IS NOT NULL
        AND st_bozza IS NOT NULL AND st_aperta IS NOT NULL AND st_chiusa IS NOT NULL
        AND sf_da_eseguire IS NOT NULL AND sf_in_corso IS NOT NULL
        AND sf_completato IS NOT NULL AND priorita_id IS NOT NULL
       FROM tmp_bv_refs),
    '0. Precondizioni soddisfatte'
);

-- =========================================================
-- 1) Setup: tipo bivio, template obbligatori, prerequisiti, pratiche
-- =========================================================
CREATE TEMP TABLE tmp_bv_tp AS WITH ins AS (
  INSERT INTO pratiche.tipi_prestazione (codice, codice_interno, descrizione, attivo)
  VALUES ('TEST_BIVIO', 'TEST_BIVIO', 'Tipo test bivio condizionale', true)
  ON CONFLICT (codice_interno) DO UPDATE SET descrizione = EXCLUDED.descrizione
  RETURNING id
)
SELECT id AS tp_id FROM ins;

-- Tre template OBBLIGATORI: il bivio e' il banco di prova della
-- semantica "obbligatorio blocca solo se percorribile".
CREATE TEMP TABLE tmp_bv_tf AS WITH ins AS (
  INSERT INTO pratiche.template_flussi (tipo_prestazione_id, codice, descrizione, sequenza, obbligatorio, attivo)
  VALUES
    ((SELECT tp_id FROM tmp_bv_tp), 'TF_BV_APPROVAZIONE', 'Approvazione (nodo del bivio)', 10, true, true),
    ((SELECT tp_id FROM tmp_bv_tp), 'TF_BV_CONFERMA', 'Conferma (ramo POSITIVO)', 20, true, true),
    ((SELECT tp_id FROM tmp_bv_tp), 'TF_BV_NEGOZIAZIONE', 'Negoziazione (ramo NEGATIVO)', 30, true, true)
  ON CONFLICT (definizione_id, codice) DO UPDATE SET descrizione = EXCLUDED.descrizione
  RETURNING id, codice
)
SELECT
  max(id) FILTER (WHERE codice = 'TF_BV_APPROVAZIONE') AS tf_appr_id,
  max(id) FILTER (WHERE codice = 'TF_BV_CONFERMA') AS tf_conf_id,
  max(id) FILTER (WHERE codice = 'TF_BV_NEGOZIAZIONE') AS tf_nego_id
FROM ins;

-- Il bivio: CONFERMA richiede APPROVAZIONE POSITIVO,
--           NEGOZIAZIONE richiede APPROVAZIONE NEGATIVO.
INSERT INTO pratiche.template_flussi_prerequisiti (template_flusso_id, prerequisito_id, esito_richiesto)
VALUES
  ((SELECT tf_conf_id FROM tmp_bv_tf), (SELECT tf_appr_id FROM tmp_bv_tf), 'POSITIVO'),
  ((SELECT tf_nego_id FROM tmp_bv_tf), (SELECT tf_appr_id FROM tmp_bv_tf), 'NEGATIVO')
ON CONFLICT (template_flusso_id, prerequisito_id) DO UPDATE SET esito_richiesto = EXCLUDED.esito_richiesto;

-- Due pratiche: P1 percorre il ramo POSITIVO, P2 il ramo NEGATIVO.
CREATE TEMP TABLE tmp_bv_p1 AS WITH ins AS (
  INSERT INTO pratiche.pratiche (emittente_fiscale_id, tipo_prestazione_id, stato_id, priorita_id, descrizione)
  VALUES (
    (SELECT emittente_id FROM tmp_bv_refs), (SELECT tp_id FROM tmp_bv_tp),
    (SELECT st_bozza FROM tmp_bv_refs), (SELECT priorita_id FROM tmp_bv_refs),
    'test bivio: ramo POSITIVO')
  RETURNING id
)
SELECT id AS pratica_id FROM ins;

CREATE TEMP TABLE tmp_bv_p2 AS WITH ins AS (
  INSERT INTO pratiche.pratiche (emittente_fiscale_id, tipo_prestazione_id, stato_id, priorita_id, descrizione)
  VALUES (
    (SELECT emittente_id FROM tmp_bv_refs), (SELECT tp_id FROM tmp_bv_tp),
    (SELECT st_bozza FROM tmp_bv_refs), (SELECT priorita_id FROM tmp_bv_refs),
    'test bivio: ramo NEGATIVO')
  RETURNING id
)
SELECT id AS pratica_id FROM ins;

-- Entrambe APERTE (BOZZA -> APERTA ammessa dalla matrice).
UPDATE pratiche.pratiche
   SET stato_id = (SELECT st_aperta FROM tmp_bv_refs)
 WHERE id IN ((SELECT pratica_id FROM tmp_bv_p1), (SELECT pratica_id FROM tmp_bv_p2));

-- P1: APPROVAZIONE completata POSITIVO (DA_ESEGUIRE -> IN_CORSO -> COMPLETATO).
INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id, sequenza)
VALUES ((SELECT pratica_id FROM tmp_bv_p1), (SELECT tf_appr_id FROM tmp_bv_tf),
        (SELECT sf_da_eseguire FROM tmp_bv_refs), 10);
UPDATE pratiche.flussi SET stato_id = (SELECT sf_in_corso FROM tmp_bv_refs)
 WHERE pratica_id = (SELECT pratica_id FROM tmp_bv_p1)
   AND template_flusso_id = (SELECT tf_appr_id FROM tmp_bv_tf);
UPDATE pratiche.flussi SET stato_id = (SELECT sf_completato FROM tmp_bv_refs), esito = 'POSITIVO'
 WHERE pratica_id = (SELECT pratica_id FROM tmp_bv_p1)
   AND template_flusso_id = (SELECT tf_appr_id FROM tmp_bv_tf);

-- P2: APPROVAZIONE completata NEGATIVO.
INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id, sequenza)
VALUES ((SELECT pratica_id FROM tmp_bv_p2), (SELECT tf_appr_id FROM tmp_bv_tf),
        (SELECT sf_da_eseguire FROM tmp_bv_refs), 10);
UPDATE pratiche.flussi SET stato_id = (SELECT sf_in_corso FROM tmp_bv_refs)
 WHERE pratica_id = (SELECT pratica_id FROM tmp_bv_p2)
   AND template_flusso_id = (SELECT tf_appr_id FROM tmp_bv_tf);
UPDATE pratiche.flussi SET stato_id = (SELECT sf_completato FROM tmp_bv_refs), esito = 'NEGATIVO'
 WHERE pratica_id = (SELECT pratica_id FROM tmp_bv_p2)
   AND template_flusso_id = (SELECT tf_appr_id FROM tmp_bv_tf);

SELECT ok(
    (SELECT pratica_id IS NOT NULL FROM tmp_bv_p1)
    AND (SELECT pratica_id IS NOT NULL FROM tmp_bv_p2),
    '1. Setup completato: bivio seedato, P1 POSITIVO e P2 NEGATIVO pronte'
);

-- =========================================================
-- 2) P1: CONFERMA eseguibile (ramo coerente con POSITIVO)
-- =========================================================
SELECT lives_ok(
  format('INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id, sequenza) VALUES (%s, %s, %s, 20)',
    (SELECT pratica_id FROM tmp_bv_p1),
    (SELECT tf_conf_id FROM tmp_bv_tf),
    (SELECT sf_da_eseguire FROM tmp_bv_refs)),
  '2. P1 (POSITIVO): ramo CONFERMA eseguibile'
);

-- =========================================================
-- 3) P1: NEGOZIAZIONE bloccata (ramo opposto)
-- =========================================================
SELECT throws_ok(
  format('INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id, sequenza) VALUES (%s, %s, %s, 30)',
    (SELECT pratica_id FROM tmp_bv_p1),
    (SELECT tf_nego_id FROM tmp_bv_tf),
    (SELECT sf_da_eseguire FROM tmp_bv_refs)),
  NULL, NULL,
  '3. P1 (POSITIVO): ramo NEGOZIAZIONE bloccato dai prerequisiti esito-aware'
);

-- =========================================================
-- 4) P1: fn_check_chiusura — NEGOZIAZIONE e' ramo morto
-- =========================================================
SELECT ok(
    (SELECT NOT c.percorribile AND NOT c.bloccante
       FROM pratiche.fn_check_chiusura_pratica((SELECT pratica_id FROM tmp_bv_p1)) c
      WHERE c.template_flusso_id = (SELECT tf_nego_id FROM tmp_bv_tf)),
    '4. P1: NEGOZIAZIONE obbligatoria ma ramo morto (percorribile=false, bloccante=false)'
);

-- =========================================================
-- 5) P1: chiusura vietata con CONFERMA non completata
-- =========================================================
SELECT throws_ok(
  format('UPDATE pratiche.pratiche SET stato_id = %s WHERE id = %s',
    (SELECT st_chiusa FROM tmp_bv_refs),
    (SELECT pratica_id FROM tmp_bv_p1)),
  NULL, NULL,
  '5. P1: chiusura vietata (CONFERMA obbligatoria, percorribile, non completata)'
);

-- =========================================================
-- 6) P1: completata CONFERMA -> AUTO-chiusura (ramo morto non blocca)
--    Completato l'ultimo obbligatorio percorribile, l'auto-chiusura
--    (trg_flussi_z90_autochiusura_pratica) porta la pratica a CHIUSA:
--    il ramo morto NEGOZIAZIONE (non percorribile) non blocca (D4).
-- =========================================================
UPDATE pratiche.flussi SET stato_id = (SELECT sf_in_corso FROM tmp_bv_refs)
 WHERE pratica_id = (SELECT pratica_id FROM tmp_bv_p1)
   AND template_flusso_id = (SELECT tf_conf_id FROM tmp_bv_tf);
UPDATE pratiche.flussi SET stato_id = (SELECT sf_completato FROM tmp_bv_refs), esito = 'POSITIVO'
 WHERE pratica_id = (SELECT pratica_id FROM tmp_bv_p1)
   AND template_flusso_id = (SELECT tf_conf_id FROM tmp_bv_tf);

SELECT is(
  (SELECT sp.codice_interno
     FROM pratiche.pratiche p
     JOIN config.stati_pratiche sp ON sp.id = p.stato_id
    WHERE p.id = (SELECT pratica_id FROM tmp_bv_p1)),
  'CHIUSA',
  '6. P1: auto-chiusura al completamento di CONFERMA (ramo morto obbligatorio non blocca, D4)'
);

-- =========================================================
-- 7) P2: NEGOZIAZIONE eseguibile (ramo coerente con NEGATIVO)
-- =========================================================
SELECT lives_ok(
  format('INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id, sequenza) VALUES (%s, %s, %s, 30)',
    (SELECT pratica_id FROM tmp_bv_p2),
    (SELECT tf_nego_id FROM tmp_bv_tf),
    (SELECT sf_da_eseguire FROM tmp_bv_refs)),
  '7. P2 (NEGATIVO): ramo NEGOZIAZIONE eseguibile'
);

-- =========================================================
-- 8) P2: CONFERMA bloccata (ramo opposto)
-- =========================================================
SELECT throws_ok(
  format('INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id, sequenza) VALUES (%s, %s, %s, 20)',
    (SELECT pratica_id FROM tmp_bv_p2),
    (SELECT tf_conf_id FROM tmp_bv_tf),
    (SELECT sf_da_eseguire FROM tmp_bv_refs)),
  NULL, NULL,
  '8. P2 (NEGATIVO): ramo CONFERMA bloccato dai prerequisiti esito-aware'
);

-- =========================================================
-- 9) P2: completata NEGOZIAZIONE -> AUTO-chiusura (CONFERMA ramo morto)
-- =========================================================
UPDATE pratiche.flussi SET stato_id = (SELECT sf_in_corso FROM tmp_bv_refs)
 WHERE pratica_id = (SELECT pratica_id FROM tmp_bv_p2)
   AND template_flusso_id = (SELECT tf_nego_id FROM tmp_bv_tf);
UPDATE pratiche.flussi SET stato_id = (SELECT sf_completato FROM tmp_bv_refs), esito = 'POSITIVO'
 WHERE pratica_id = (SELECT pratica_id FROM tmp_bv_p2)
   AND template_flusso_id = (SELECT tf_nego_id FROM tmp_bv_tf);

SELECT is(
  (SELECT sp.codice_interno
     FROM pratiche.pratiche p
     JOIN config.stati_pratiche sp ON sp.id = p.stato_id
    WHERE p.id = (SELECT pratica_id FROM tmp_bv_p2)),
  'CHIUSA',
  '9. P2: auto-chiusura percorrendo il ramo opposto (CONFERMA e'' ramo morto)'
);

-- =========================================================
-- 10) Cleanup (resiliente)
-- =========================================================
DELETE FROM pratiche.giornale
WHERE pratica_id IN (
    SELECT id FROM pratiche.pratiche
    WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_bv_tp)
);
DELETE FROM pratiche.flussi
WHERE pratica_id IN (
    SELECT id FROM pratiche.pratiche
    WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_bv_tp)
);
DELETE FROM pratiche.pratiche
WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_bv_tp);
DELETE FROM pratiche.template_flussi_prerequisiti
WHERE template_flusso_id IN (
    SELECT id FROM pratiche.template_flussi
    WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_bv_tp)
);
DELETE FROM pratiche.template_flussi
WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_bv_tp);
DELETE FROM pratiche.tipi_prestazione
WHERE id = (SELECT tp_id FROM tmp_bv_tp);

SELECT * FROM finish();

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia nulla dietro di se'. Le DELETE del cleanup restano
-- perche' dove sono un'asserzione devono girare davvero.
ROLLBACK;
