-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: pratiche.fn_log_evento_dominio (B-NEW) + chk_giornale_azione DOMINIO_*
--       Canale append-only per eventi di dominio sul giornale pratiche.
--
-- Indice test:
-- 0) Precondizioni (provisioning + pratica)
-- 1) fn_log_evento_dominio(DOMINIO_COMMESSA_CREATA): ritorna id giornale
-- 2) Riga giornale: azione/origine HANDLER/dettaglio/tx_id valorizzati
-- 3) Evento a livello pratica (flusso_id NULL): consentito
-- 4) Nome arbitrario non DOMINIO_* via fn: rifiutato dal CHECK
-- 5) Nome DOMINIO_* minuscolo: rifiutato dal CHECK (regex [A-Z])
-- 6) Guard parametro: pratica_id non positivo -> throws
-- 7) Cleanup
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

SELECT plan(6);

-- =========================================================
-- 0) Precondizioni: provisioning + pratica di test
-- =========================================================

INSERT INTO config.stati_pratiche (codice, codice_interno, descrizione, attivo)
VALUES ('BOZZA', 'BOZZA', 'Bozza', true)
ON CONFLICT (codice_interno) DO NOTHING;

INSERT INTO config.priorita_pratiche (codice, codice_interno, descrizione, sequenza, attivo)
VALUES ('NORMALE', 'NORMALE', 'Normale', 20, true)
ON CONFLICT (codice_interno) DO NOTHING;

CREATE TEMP TABLE tmp_ld_refs AS
SELECT
  script.fn_pgtap_emittente_operatore() AS emittente_id,
  (SELECT id FROM anagrafiche.soggetti ORDER BY id LIMIT 1) AS soggetto_id,
  (SELECT id FROM config.stati_pratiche WHERE codice_interno = 'BOZZA' AND attivo = true LIMIT 1) AS stato_bozza_id,
  (SELECT id FROM config.priorita_pratiche WHERE codice_interno = 'NORMALE' AND attivo = true LIMIT 1) AS priorita_normale_id;

CREATE TEMP TABLE tmp_ld_tp AS
WITH ins AS (
  INSERT INTO pratiche.tipi_prestazione (codice, codice_interno, descrizione, attivo)
  VALUES ('TEST_DOMINIO_TP', 'TEST_DOMINIO_TP', 'Tipo prestazione test giornale dominio', true)
  ON CONFLICT (codice_interno) DO UPDATE SET descrizione = EXCLUDED.descrizione
  RETURNING id
)
SELECT id AS tp_id FROM ins;

CREATE TEMP TABLE tmp_ld_pratica AS
WITH ins AS (
  INSERT INTO pratiche.pratiche (
    emittente_fiscale_id, tipo_prestazione_id, soggetto_id, stato_id, priorita_id
  )
  VALUES (
    (SELECT emittente_id FROM tmp_ld_refs),
    (SELECT tp_id FROM tmp_ld_tp),
    (SELECT soggetto_id FROM tmp_ld_refs),
    (SELECT stato_bozza_id FROM tmp_ld_refs),
    (SELECT priorita_normale_id FROM tmp_ld_refs)
  )
  RETURNING id
)
SELECT id AS pratica_id FROM ins;

-- =========================================================
-- 1) fn_log_evento_dominio(DOMINIO_COMMESSA_CREATA): ritorna id
-- =========================================================

CREATE TEMP TABLE tmp_ld_giornale AS
SELECT pratiche.fn_log_evento_dominio(
         (SELECT pratica_id FROM tmp_ld_pratica),
         NULL,
         'DOMINIO_COMMESSA_CREATA',
         jsonb_build_object('commessa_id', 12345, 'preventivo_uid', 'abc')
       ) AS giornale_id;

SELECT ok(
    (SELECT giornale_id IS NOT NULL AND giornale_id > 0 FROM tmp_ld_giornale),
    '1. fn_log_evento_dominio ritorna id giornale valido'
);

-- =========================================================
-- 2) Riga giornale: azione, origine HANDLER, dettaglio, tx_id
-- =========================================================

SELECT ok(
    (SELECT g.azione = 'DOMINIO_COMMESSA_CREATA'
        AND g.origine = 'HANDLER'
        AND g.flusso_id IS NULL
        AND g.dettaglio ? 'commessa_id'
        AND g.tx_id IS NOT NULL
       FROM pratiche.giornale g
      WHERE g.id = (SELECT giornale_id FROM tmp_ld_giornale)),
    '2. Riga giornale: azione/origine HANDLER/dettaglio/tx_id corretti'
);

-- =========================================================
-- 3) Evento DOMINIO_* (un secondo evento di dominio): consentito
-- =========================================================

SELECT lives_ok(
    format(
      'SELECT pratiche.fn_log_evento_dominio(%s, NULL, %L, ''{}''::jsonb)',
      (SELECT pratica_id FROM tmp_ld_pratica),
      'DOMINIO_PREVENTIVO_EVASO'),
    '3. Evento DOMINIO_PREVENTIVO_EVASO consentito'
);

-- =========================================================
-- 4) Nome arbitrario non DOMINIO_* via fn: rifiutato dal CHECK
-- =========================================================

SELECT throws_ok(
    format(
      'SELECT pratiche.fn_log_evento_dominio(%s, NULL, %L, ''{}''::jsonb)',
      (SELECT pratica_id FROM tmp_ld_pratica),
      'EVENTO_ARBITRARIO'),
    NULL, NULL,
    '4. Nome arbitrario non DOMINIO_* rifiutato dal CHECK giornale'
);

-- =========================================================
-- 5) Nome DOMINIO_* minuscolo: rifiutato dalla regex ([A-Z])
-- =========================================================

SELECT throws_ok(
    format(
      'SELECT pratiche.fn_log_evento_dominio(%s, NULL, %L, ''{}''::jsonb)',
      (SELECT pratica_id FROM tmp_ld_pratica),
      'DOMINIO_minuscolo'),
    NULL, NULL,
    '5. DOMINIO_ minuscolo rifiutato (regex richiede [A-Z])'
);

-- =========================================================
-- 6) Guard parametro: pratica_id non positivo -> throws
-- =========================================================

SELECT throws_ok(
    'SELECT pratiche.fn_log_evento_dominio(0, NULL, ''DOMINIO_TEST'', ''{}''::jsonb)',
    NULL, NULL,
    '6. Guard: pratica_id non positivo bloccato'
);

-- =========================================================
-- 7) Cleanup
-- =========================================================

DELETE FROM pratiche.giornale WHERE pratica_id IN (
  SELECT id FROM pratiche.pratiche WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_ld_tp)
);
DELETE FROM pratiche.flussi WHERE pratica_id IN (
  SELECT id FROM pratiche.pratiche WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_ld_tp)
);
DELETE FROM pratiche.pratiche WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_ld_tp);
DELETE FROM pratiche.tipi_prestazione WHERE id = (SELECT tp_id FROM tmp_ld_tp);

SELECT * FROM finish();

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia nulla dietro di se'. Le DELETE del cleanup restano
-- perche' dove sono un'asserzione devono girare davvero.
ROLLBACK;
