-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: trigger set data_apertura su pratiche.pratiche
--       (trgfn_pratiche_set_data_apertura)
--
-- Indice test:
-- 0) Precondizioni (provisioning + verifica)
-- 1) Setup pratica in BOZZA — data_apertura IS NULL
-- 2) BOZZA → APERTA — data_apertura viene valorizzata
-- 3) APERTA → SOSPESA — data_apertura non cambia (immutabile)
-- 4) SOSPESA → APERTA — data_apertura non cambia (immutabile)
-- 5) Nuova pratica: BOZZA → ANNULLATA — data_apertura resta NULL
-- 6) INSERT diretto in APERTA (senza data_apertura) → data_apertura = script.fn_data_operativa()
-- 7) INSERT diretto in APERTA con data_apertura esplicita → valore chiamante preservato (immutabilita' all'INSERT)
-- 8) INSERT in BOZZA → data_apertura IS NULL (comportamento bozza invariato)
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
-- 0) Precondizioni
-- =========================================================
CREATE TEMP TABLE tmp_da_refs AS
SELECT
  script.fn_pgtap_emittente_operatore() AS emittente_id,
  (SELECT id FROM anagrafiche.soggetti ORDER BY id LIMIT 1) AS soggetto_id,
  (SELECT id FROM config.stati_pratiche WHERE codice_interno = 'BOZZA') AS st_bozza,
  (SELECT id FROM config.stati_pratiche WHERE codice_interno = 'APERTA') AS st_aperta,
  (SELECT id FROM config.stati_pratiche WHERE codice_interno = 'SOSPESA') AS st_sospesa,
  (SELECT id FROM config.stati_pratiche WHERE codice_interno = 'ANNULLATA') AS st_annullata,
  (SELECT id FROM config.priorita_pratiche WHERE codice_interno = 'NORMALE') AS priorita_id;

CREATE TEMP TABLE tmp_da_tp AS
WITH ins AS (
  INSERT INTO pratiche.tipi_prestazione (codice, codice_interno, descrizione, attivo)
  VALUES ('TEST_DA', 'TEST_DA', 'Tipo test data_apertura', true)
  ON CONFLICT (codice_interno) DO UPDATE SET descrizione = EXCLUDED.descrizione
  RETURNING id
)
SELECT id AS tp_id FROM ins;

SELECT ok(
  (SELECT emittente_id IS NOT NULL AND st_bozza IS NOT NULL
      AND st_aperta IS NOT NULL AND priorita_id IS NOT NULL
   FROM tmp_da_refs),
  '0. Precondizioni soddisfatte'
);

-- =========================================================
-- 1) Setup pratica in BOZZA — data_apertura NULL
-- =========================================================
CREATE TEMP TABLE tmp_da_pratica AS
WITH ins AS (
  INSERT INTO pratiche.pratiche (emittente_fiscale_id, tipo_prestazione_id, soggetto_id, stato_id, priorita_id)
  VALUES (
    (SELECT emittente_id FROM tmp_da_refs),
    (SELECT tp_id FROM tmp_da_tp),
    (SELECT soggetto_id FROM tmp_da_refs),
    (SELECT st_bozza FROM tmp_da_refs),
    (SELECT priorita_id FROM tmp_da_refs)
  )
  RETURNING id
)
SELECT id AS pratica_id FROM ins;

SELECT is(
  (SELECT data_apertura FROM pratiche.pratiche WHERE id = (SELECT pratica_id FROM tmp_da_pratica)),
  NULL::DATE,
  '1. Pratica in BOZZA: data_apertura IS NULL'
);

-- =========================================================
-- 2) BOZZA → APERTA — data_apertura valorizzata
-- =========================================================
UPDATE pratiche.pratiche
   SET stato_id = (SELECT st_aperta FROM tmp_da_refs)
 WHERE id = (SELECT pratica_id FROM tmp_da_pratica);

SELECT isnt(
  (SELECT data_apertura FROM pratiche.pratiche WHERE id = (SELECT pratica_id FROM tmp_da_pratica)),
  NULL::DATE,
  '2. BOZZA -> APERTA: data_apertura valorizzata'
);

-- Salva il valore per verifiche successive
CREATE TEMP TABLE tmp_da_valore AS
SELECT data_apertura AS valore
FROM pratiche.pratiche
WHERE id = (SELECT pratica_id FROM tmp_da_pratica);

-- =========================================================
-- 3) APERTA → SOSPESA — data_apertura immutabile
-- =========================================================
UPDATE pratiche.pratiche
   SET stato_id = (SELECT st_sospesa FROM tmp_da_refs)
 WHERE id = (SELECT pratica_id FROM tmp_da_pratica);

SELECT is(
  (SELECT data_apertura FROM pratiche.pratiche WHERE id = (SELECT pratica_id FROM tmp_da_pratica)),
  (SELECT valore FROM tmp_da_valore),
  '3. APERTA -> SOSPESA: data_apertura immutabile'
);

-- =========================================================
-- 4) SOSPESA → APERTA — data_apertura immutabile
-- =========================================================
UPDATE pratiche.pratiche
   SET stato_id = (SELECT st_aperta FROM tmp_da_refs)
 WHERE id = (SELECT pratica_id FROM tmp_da_pratica);

SELECT is(
  (SELECT data_apertura FROM pratiche.pratiche WHERE id = (SELECT pratica_id FROM tmp_da_pratica)),
  (SELECT valore FROM tmp_da_valore),
  '4. SOSPESA -> APERTA: data_apertura immutabile (non sovrascritta)'
);

-- =========================================================
-- 5) Nuova pratica: BOZZA → ANNULLATA — data_apertura resta NULL
-- =========================================================
CREATE TEMP TABLE tmp_da_pratica2 AS
WITH ins AS (
  INSERT INTO pratiche.pratiche (emittente_fiscale_id, tipo_prestazione_id, soggetto_id, stato_id, priorita_id)
  VALUES (
    (SELECT emittente_id FROM tmp_da_refs),
    (SELECT tp_id FROM tmp_da_tp),
    (SELECT soggetto_id FROM tmp_da_refs),
    (SELECT st_bozza FROM tmp_da_refs),
    (SELECT priorita_id FROM tmp_da_refs)
  )
  RETURNING id
)
SELECT id AS pratica_id FROM ins;

UPDATE pratiche.pratiche
   SET stato_id = (SELECT st_annullata FROM tmp_da_refs)
 WHERE id = (SELECT pratica_id FROM tmp_da_pratica2);

SELECT is(
  (SELECT data_apertura FROM pratiche.pratiche WHERE id = (SELECT pratica_id FROM tmp_da_pratica2)),
  NULL::DATE,
  '5. BOZZA -> ANNULLATA: data_apertura resta NULL'
);

-- =========================================================
-- 6) INSERT diretto in APERTA (senza data_apertura) → script.fn_data_operativa()
-- =========================================================
CREATE TEMP TABLE tmp_da_pratica3 AS
WITH ins AS (
  INSERT INTO pratiche.pratiche (emittente_fiscale_id, tipo_prestazione_id, soggetto_id, stato_id, priorita_id)
  VALUES (
    (SELECT emittente_id FROM tmp_da_refs),
    (SELECT tp_id FROM tmp_da_tp),
    (SELECT soggetto_id FROM tmp_da_refs),
    (SELECT st_aperta FROM tmp_da_refs),
    (SELECT priorita_id FROM tmp_da_refs)
  )
  RETURNING id
)
SELECT id AS pratica_id FROM ins;

SELECT is(
  (SELECT data_apertura FROM pratiche.pratiche WHERE id = (SELECT pratica_id FROM tmp_da_pratica3)),
  script.fn_data_operativa(),
  '6. INSERT in APERTA senza data_apertura: data_apertura = script.fn_data_operativa()'
);

-- =========================================================
-- 7) INSERT diretto in APERTA con data_apertura esplicita → preservata
-- =========================================================
CREATE TEMP TABLE tmp_da_pratica4 AS
WITH ins AS (
  INSERT INTO pratiche.pratiche (emittente_fiscale_id, tipo_prestazione_id, soggetto_id, stato_id, priorita_id, data_apertura)
  VALUES (
    (SELECT emittente_id FROM tmp_da_refs),
    (SELECT tp_id FROM tmp_da_tp),
    (SELECT soggetto_id FROM tmp_da_refs),
    (SELECT st_aperta FROM tmp_da_refs),
    (SELECT priorita_id FROM tmp_da_refs),
    DATE '2020-01-15'
  )
  RETURNING id
)
SELECT id AS pratica_id FROM ins;

SELECT is(
  (SELECT data_apertura FROM pratiche.pratiche WHERE id = (SELECT pratica_id FROM tmp_da_pratica4)),
  DATE '2020-01-15',
  '7. INSERT in APERTA con data_apertura esplicita: valore chiamante preservato'
);

-- =========================================================
-- 8) INSERT diretto in BOZZA → data_apertura IS NULL
-- =========================================================
CREATE TEMP TABLE tmp_da_pratica5 AS
WITH ins AS (
  INSERT INTO pratiche.pratiche (emittente_fiscale_id, tipo_prestazione_id, soggetto_id, stato_id, priorita_id)
  VALUES (
    (SELECT emittente_id FROM tmp_da_refs),
    (SELECT tp_id FROM tmp_da_tp),
    (SELECT soggetto_id FROM tmp_da_refs),
    (SELECT st_bozza FROM tmp_da_refs),
    (SELECT priorita_id FROM tmp_da_refs)
  )
  RETURNING id
)
SELECT id AS pratica_id FROM ins;

SELECT is(
  (SELECT data_apertura FROM pratiche.pratiche WHERE id = (SELECT pratica_id FROM tmp_da_pratica5)),
  NULL::DATE,
  '8. INSERT in BOZZA: data_apertura IS NULL (comportamento bozza invariato)'
);

-- =========================================================
-- 9) Cleanup
-- =========================================================
-- Cancella prima giornale (FK verso pratiche), poi pratiche, poi tipo prestazione
DELETE FROM pratiche.giornale WHERE pratica_id IN (SELECT id FROM pratiche.pratiche WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_da_tp));
DELETE FROM pratiche.pratiche WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_da_tp);
DELETE FROM pratiche.tipi_prestazione WHERE codice_interno = 'TEST_DA';

SELECT pass('9. Cleanup completato');

SELECT * FROM finish();

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia nulla dietro di se'. Le DELETE del cleanup restano
-- perche' dove sono un'asserzione devono girare davvero.
ROLLBACK;
