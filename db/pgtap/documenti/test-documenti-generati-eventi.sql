-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: documenti.documenti_generati_eventi
--   - INSERT eventi ammessi (GENERATO/SCARICATO/STORAGE_ORPHAN/RISTAMPA_FEDELE)
--   - CHECK evento_tipo (set chiuso v1: ANTEPRIMA, RENDER_KO rifiutati)
--   - CHECK esito (OK/KO/WARN)
--   - CHECK messaggio non-vuoto / detail jsonb object
--   - guard append-only: block UPDATE / block DELETE
--   - FK documento_generato_id
--   - storico OFF (no provisioning automatico)
--   - default audit popolati su INSERT minimo
-- ------------------------------------------------------------
-- Indice test (1..15):
--  1) Setup: documento generato di riferimento creato
--  2) INSERT evento GENERATO esito=OK passa
--  3) INSERT evento SCARICATO con messaggio passa
--  4) INSERT evento STORAGE_ORPHAN user_id=NULL esito=KO passa
--  5) CHECK evento_tipo: ANTEPRIMA non ammesso in v1 (Decisione 30)
--  6) CHECK evento_tipo: RENDER_KO non ammesso (set chiuso)
--  7) CHECK esito: valore non in (OK,KO,WARN) rifiutato
--  8) CHECK messaggio: stringa solo whitespace rifiutata
--  9) CHECK detail: jsonb non-object (array) rifiutato
-- 10) Guard block UPDATE: UPDATE messaggio bloccato
-- 11) Guard block DELETE: DELETE evento bloccato
-- 12) FK: documento_generato_id inesistente -> 23503
-- 13) Storico OFF: storico.documenti_generati_eventi NON esiste
-- 14) Default audit: data_insert e user_insert popolati su INSERT minimo
-- 15) CHECK evento_tipo: RISTAMPA_FEDELE ammesso, con esito WARN
-- ------------------------------------------------------------

BEGIN;
SELECT plan(15);

-- ============================================================
-- Setup contesto: emittente + template + versione + documento generato
-- ============================================================
CREATE TEMP TABLE tmp_dge_ctx AS
SELECT
  (SELECT ef.id FROM anagrafiche.emittenti_fiscali ef
    WHERE ef.attivo = true ORDER BY ef.id LIMIT 1)               AS emittente_id,
  (SELECT s.id FROM config.sorgenti s
    WHERE s.codice_interno = 'PREVENTIVO')                       AS sorgente_id,
  (SELECT t.id FROM documenti.tipi_documento_output t
    WHERE t.codice_interno = 'PREVENTIVO')                       AS tipo_output_id,
  (SELECT r.id FROM documenti.render_engine_documento r
    WHERE r.codice_interno = 'WEASYPRINT')                       AS render_id;

WITH ins_t AS (
  INSERT INTO documenti.template_documenti (
    tipo_documento_output_id, codice, codice_interno, descrizione,
    sorgente_tipo_id, context_builder_code, emittente_fiscale_id,
    is_default, attivo
  )
  SELECT tipo_output_id, 'PGTAP-DGE', 'PGTAP_DGE', 'Template per eventi',
         sorgente_id, 'pgtap.builder', emittente_id, false, true
    FROM tmp_dge_ctx
   WHERE emittente_id IS NOT NULL
  RETURNING id
)
SELECT id INTO TEMP TABLE tmp_dge_template FROM ins_t;

WITH ins_v AS (
  INSERT INTO documenti.template_documenti_versioni (
    template_documento_id, versione, stato, titolo, html_template,
    render_engine_id, valido_dal, valido_al
  )
  SELECT (SELECT id FROM tmp_dge_template),
         1, 'PUBBLICATA', 'v1', '<html>v1</html>',
         (SELECT render_id FROM tmp_dge_ctx),
         DATE '2026-01-01', DATE '2026-12-31'
  RETURNING id
)
SELECT id INTO TEMP TABLE tmp_dge_versione FROM ins_v;

WITH ins_dg AS (
  INSERT INTO documenti.documenti_generati (
    tipo_documento_output_id, template_documento_id, template_versione_id,
    sorgente_tipo_id, sorgente_uid, sorgente_riga, progressivo_sorgente,
    titolo, nome_file, context_json, context_hash, template_hash, pdf_hash,
    emittente_fiscale_id
  )
  SELECT
    (SELECT tipo_output_id FROM tmp_dge_ctx),
    (SELECT id FROM tmp_dge_template),
    (SELECT id FROM tmp_dge_versione),
    (SELECT sorgente_id FROM tmp_dge_ctx),
    'PGTAP-EVT-001', NULL, 1,
    'Doc per eventi', 'doc-evt.pdf',
    '{"tot": 100}'::jsonb,
    repeat('1', 64), repeat('2', 64), repeat('3', 64),
    (SELECT emittente_id FROM tmp_dge_ctx)
  RETURNING id
)
SELECT id INTO TEMP TABLE tmp_dge_doc FROM ins_dg;

-- 1) Pre-condizione setup
SELECT ok(
  (SELECT COUNT(*) FROM tmp_dge_doc) = 1,
  'Setup: documento generato di riferimento creato'
);

-- ============================================================
-- 2) INSERT evento GENERATO esito=OK
-- ============================================================
INSERT INTO documenti.documenti_generati_eventi (
  documento_generato_id, evento_tipo, esito, detail
)
SELECT (SELECT id FROM tmp_dge_doc), 'GENERATO', 'OK',
       jsonb_build_object('size_bytes', 1024);

SELECT is(
  (SELECT COUNT(*)::int FROM documenti.documenti_generati_eventi
    WHERE documento_generato_id = (SELECT id FROM tmp_dge_doc)
      AND evento_tipo = 'GENERATO'),
  1,
  'INSERT evento GENERATO esito=OK passa'
);

-- ============================================================
-- 3) INSERT evento SCARICATO con messaggio
-- ============================================================
INSERT INTO documenti.documenti_generati_eventi (
  documento_generato_id, evento_tipo, esito, messaggio
)
SELECT (SELECT id FROM tmp_dge_doc), 'SCARICATO', 'OK',
       'Download da utente API';

SELECT is(
  (SELECT messaggio FROM documenti.documenti_generati_eventi
    WHERE documento_generato_id = (SELECT id FROM tmp_dge_doc)
      AND evento_tipo = 'SCARICATO'),
  'Download da utente API',
  'INSERT evento SCARICATO con messaggio passa'
);

-- ============================================================
-- 4) INSERT evento STORAGE_ORPHAN user_id NULL esito=KO
-- ============================================================
INSERT INTO documenti.documenti_generati_eventi (
  documento_generato_id, evento_tipo, esito, user_id, messaggio, detail
)
SELECT (SELECT id FROM tmp_dge_doc), 'STORAGE_ORPHAN', 'KO',
       NULL, 'File orfano post-fail commit',
       jsonb_build_object('storage_key', 's3://bucket/orphan.pdf');

SELECT is(
  (SELECT COUNT(*)::int FROM documenti.documenti_generati_eventi
    WHERE documento_generato_id = (SELECT id FROM tmp_dge_doc)
      AND evento_tipo = 'STORAGE_ORPHAN'
      AND esito = 'KO'
      AND user_id IS NULL),
  1,
  'INSERT evento STORAGE_ORPHAN user_id=NULL esito=KO passa'
);

-- ============================================================
-- 5) CHECK evento_tipo: ANTEPRIMA non ammesso (Decisione 30)
-- ============================================================
SELECT throws_ok(
  $$INSERT INTO documenti.documenti_generati_eventi (
      documento_generato_id, evento_tipo, esito
    )
    SELECT (SELECT id FROM tmp_dge_doc), 'ANTEPRIMA', 'OK'$$,
  '23514',
  NULL,
  'CHECK evento_tipo: ANTEPRIMA non ammesso in v1'
);

-- ============================================================
-- 6) CHECK evento_tipo: RENDER_KO non ammesso
-- ============================================================
SELECT throws_ok(
  $$INSERT INTO documenti.documenti_generati_eventi (
      documento_generato_id, evento_tipo, esito
    )
    SELECT (SELECT id FROM tmp_dge_doc), 'RENDER_KO', 'KO'$$,
  '23514',
  NULL,
  'CHECK evento_tipo: RENDER_KO non ammesso (set chiuso v1)'
);

-- ============================================================
-- 7) CHECK esito: valore non in (OK,KO,WARN)
-- ============================================================
SELECT throws_ok(
  $$INSERT INTO documenti.documenti_generati_eventi (
      documento_generato_id, evento_tipo, esito
    )
    SELECT (SELECT id FROM tmp_dge_doc), 'GENERATO', 'INVALID'$$,
  '23514',
  NULL,
  'CHECK esito: valore non in (OK,KO,WARN) rifiutato'
);

-- ============================================================
-- 8) CHECK messaggio: stringa solo whitespace
-- ============================================================
SELECT throws_ok(
  $$INSERT INTO documenti.documenti_generati_eventi (
      documento_generato_id, evento_tipo, esito, messaggio
    )
    SELECT (SELECT id FROM tmp_dge_doc), 'GENERATO', 'OK', '   '$$,
  '23514',
  NULL,
  'CHECK messaggio: stringa solo whitespace rifiutata'
);

-- ============================================================
-- 9) CHECK detail: jsonb non-object (array)
-- ============================================================
SELECT throws_ok(
  $$INSERT INTO documenti.documenti_generati_eventi (
      documento_generato_id, evento_tipo, esito, detail
    )
    SELECT (SELECT id FROM tmp_dge_doc), 'GENERATO', 'OK', '[]'::jsonb$$,
  '23514',
  NULL,
  'CHECK detail: jsonb non-object (array) rifiutato'
);

-- ============================================================
-- 10) Guard block UPDATE: UPDATE messaggio bloccato
-- ============================================================
SELECT throws_ok(
  $$UPDATE documenti.documenti_generati_eventi
       SET messaggio = 'modificato'
     WHERE documento_generato_id = (SELECT id FROM tmp_dge_doc)
       AND evento_tipo = 'SCARICATO'$$,
  NULL,
  NULL,
  'Guard block UPDATE: UPDATE messaggio bloccato'
);

-- ============================================================
-- 11) Guard block DELETE: DELETE evento bloccato
-- ============================================================
SELECT throws_ok(
  $$DELETE FROM documenti.documenti_generati_eventi
     WHERE documento_generato_id = (SELECT id FROM tmp_dge_doc)
       AND evento_tipo = 'GENERATO'$$,
  NULL,
  NULL,
  'Guard block DELETE: DELETE evento bloccato'
);

-- ============================================================
-- 12) FK violata: documento_generato_id inesistente
-- ============================================================
SELECT throws_ok(
  $$INSERT INTO documenti.documenti_generati_eventi (
      documento_generato_id, evento_tipo, esito
    )
    VALUES (999999999, 'GENERATO', 'OK')$$,
  '23503',
  NULL,
  'FK: documento_generato_id inesistente -> 23503'
);

-- ============================================================
-- 13) Storico OFF: storico.documenti_generati_eventi NON esiste
-- ============================================================
SELECT is(
  to_regclass('storico.documenti_generati_eventi'),
  NULL,
  'Storico OFF: storico.documenti_generati_eventi non provisionato'
);

-- ============================================================
-- 14) Default audit popolati su INSERT minimo
-- ============================================================
SELECT ok(
  (SELECT data_insert IS NOT NULL AND user_insert IS NOT NULL
     FROM documenti.documenti_generati_eventi
    WHERE documento_generato_id = (SELECT id FROM tmp_dge_doc)
      AND evento_tipo = 'GENERATO'),
  'Default audit: data_insert e user_insert popolati su INSERT minimo'
);

-- ============================================================
-- 15) RISTAMPA_FEDELE ammesso, con esito WARN
--
-- La ristampa fedele ri-produce un documento dallo snapshot congelato e NON
-- crea righe in `documenti_generati`: l'evento e' la sua UNICA scrittura
-- (20260803-04). Va presidiato che il valore sia ammesso, altrimenti il CHECK
-- lo rifiuta e il servizio si limita a loggare — un rosso che si vede solo nei
-- log, cioe' uno che si smette di guardare.
--
-- `WARN` e' il caso normale, non l'eccezione: significa «fedele nel contenuto,
-- non nei byte» (decisione Tid, brief ristampa fedele §8.2) e capita ogni volta
-- che il motore di render cambia fra l'emissione e la ristampa.
-- ============================================================
INSERT INTO documenti.documenti_generati_eventi (
  documento_generato_id, evento_tipo, esito, messaggio, detail
)
SELECT (SELECT id FROM tmp_dge_doc), 'RISTAMPA_FEDELE', 'WARN',
       'Ristampa fedele: contenuto identico, byte diversi',
       jsonb_build_object('pdf_hash_match', false);

SELECT is(
  (SELECT COUNT(*)::int FROM documenti.documenti_generati_eventi
    WHERE documento_generato_id = (SELECT id FROM tmp_dge_doc)
      AND evento_tipo = 'RISTAMPA_FEDELE'
      AND esito = 'WARN'
      AND (detail->>'pdf_hash_match')::boolean IS FALSE),
  1,
  'CHECK evento_tipo: RISTAMPA_FEDELE ammesso, con esito WARN'
);

SELECT * FROM finish();
ROLLBACK;
