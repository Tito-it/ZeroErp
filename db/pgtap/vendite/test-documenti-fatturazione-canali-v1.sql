-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: documenti_fatturazione_canali + fn_set_documento_canale_stato
-- ------------------------------------------------------------
-- Indice test (1..11):
-- 1) tabella documenti_fatturazione_canali presente
-- 2) funzione fn_set_documento_canale_stato presente
-- 3) riferimenti sorgenti minimi disponibili
-- 4) apertura canale PREVENTIVO
-- 5) apertura canale ORDINE_VENDITA sulla stessa sorgente
-- 6) canale PREVENTIVO auto-bloccato
-- 7) un solo canale APERTO per sorgente
-- 8) transizione ORDINE_VENDITA -> CONSUMATO con target
-- 9) target_sorgente_* valorizzati
-- 10) BLOCCATO senza motivo -> errore
-- 11) target pair incompleta -> errore
-- ------------------------------------------------------------

BEGIN;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file sarebbe verde per sottrazione. IMMEDIATE li riporta a scattare a fine
--   di ogni istruzione. In testa e non in coda: in coda scatterebbero dopo il
--   cleanup, su righe ormai cancellate.
--   Brief: brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(11);

SELECT ok(
  to_regclass('vendite.documenti_fatturazione_canali') IS NOT NULL,
  'tabella documenti_fatturazione_canali presente'
);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite'
      AND p.proname = 'fn_set_documento_canale_stato'
  ),
  'funzione fn_set_documento_canale_stato presente'
);

CREATE TEMP TABLE tmp_refs_doc_canali AS
SELECT
  (SELECT id FROM config.sorgenti WHERE codice = 'PREVENTIVO' LIMIT 1) AS src_preventivo_id,
  (SELECT id FROM config.sorgenti WHERE codice = 'ORDINE_VENDITA' LIMIT 1) AS src_ordine_id,
  (SELECT id FROM config.sorgenti WHERE codice = 'COMMESSA' LIMIT 1) AS src_commessa_id,
  ('DOC-' || substr(md5(clock_timestamp()::text), 1, 16))::text AS src_uid;

SELECT ok(
  (
    SELECT src_preventivo_id IS NOT NULL
       AND src_ordine_id IS NOT NULL
       AND src_commessa_id IS NOT NULL
       AND src_uid IS NOT NULL
    FROM tmp_refs_doc_canali
  ),
  'riferimenti sorgenti minimi disponibili'
);

CREATE TEMP TABLE tmp_open_prev AS
SELECT vendite.fn_set_documento_canale_stato(
  p_sorgente_tipo_id => (SELECT src_preventivo_id FROM tmp_refs_doc_canali),
  p_sorgente_uid => (SELECT src_uid FROM tmp_refs_doc_canali),
  p_canale_codice => 'PREVENTIVO',
  p_stato_canale => 'APERTO',
  p_meta => jsonb_build_object('test_case', 'open_prev')
) AS id;

SELECT ok(
  (SELECT id IS NOT NULL FROM tmp_open_prev),
  'apertura canale PREVENTIVO'
);

CREATE TEMP TABLE tmp_open_ord AS
SELECT vendite.fn_set_documento_canale_stato(
  p_sorgente_tipo_id => (SELECT src_preventivo_id FROM tmp_refs_doc_canali),
  p_sorgente_uid => (SELECT src_uid FROM tmp_refs_doc_canali),
  p_canale_codice => 'ORDINE_VENDITA',
  p_stato_canale => 'APERTO',
  p_meta => jsonb_build_object('test_case', 'open_ord')
) AS id;

SELECT ok(
  (SELECT id IS NOT NULL FROM tmp_open_ord),
  'apertura canale ORDINE_VENDITA sulla stessa sorgente'
);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM vendite.documenti_fatturazione_canali c
    WHERE c.sorgente_tipo_id = (SELECT src_preventivo_id FROM tmp_refs_doc_canali)
      AND c.sorgente_uid = (SELECT src_uid FROM tmp_refs_doc_canali)
      AND c.canale_codice = 'PREVENTIVO'
      AND c.stato_canale = 'BLOCCATO'
  ),
  'canale PREVENTIVO auto-bloccato'
);

SELECT is(
  (
    SELECT count(*)::text
    FROM vendite.documenti_fatturazione_canali c
    WHERE c.sorgente_tipo_id = (SELECT src_preventivo_id FROM tmp_refs_doc_canali)
      AND c.sorgente_uid = (SELECT src_uid FROM tmp_refs_doc_canali)
      AND c.stato_canale = 'APERTO'
  ),
  '1',
  'un solo canale APERTO per sorgente'
);

CREATE TEMP TABLE tmp_consume_ord AS
SELECT vendite.fn_set_documento_canale_stato(
  p_sorgente_tipo_id => (SELECT src_preventivo_id FROM tmp_refs_doc_canali),
  p_sorgente_uid => (SELECT src_uid FROM tmp_refs_doc_canali),
  p_canale_codice => 'ORDINE_VENDITA',
  p_stato_canale => 'CONSUMATO',
  p_target_sorgente_tipo_id => (SELECT src_commessa_id FROM tmp_refs_doc_canali),
  p_target_sorgente_uid => ('CMM-' || substr(md5(clock_timestamp()::text), 1, 12))::text,
  p_meta => jsonb_build_object('test_case', 'consume_ord')
) AS id;

SELECT ok(
  (
    SELECT EXISTS (
      SELECT 1
      FROM vendite.documenti_fatturazione_canali c
      WHERE c.id = (SELECT id FROM tmp_consume_ord)
        AND c.stato_canale = 'CONSUMATO'
    )
  ),
  'transizione ORDINE_VENDITA -> CONSUMATO con target'
);

SELECT ok(
  (
    SELECT EXISTS (
      SELECT 1
      FROM vendite.documenti_fatturazione_canali c
      WHERE c.id = (SELECT id FROM tmp_consume_ord)
        AND c.target_sorgente_tipo_id = (SELECT src_commessa_id FROM tmp_refs_doc_canali)
        AND c.target_sorgente_uid IS NOT NULL
    )
  ),
  'target_sorgente_* valorizzati'
);

SELECT throws_ok(
  $$
    SELECT vendite.fn_set_documento_canale_stato(
      p_sorgente_tipo_id => (SELECT src_preventivo_id FROM tmp_refs_doc_canali),
      p_sorgente_uid => (SELECT src_uid FROM tmp_refs_doc_canali),
      p_canale_codice => 'DDT_VENDITA',
      p_stato_canale => 'BLOCCATO',
      p_meta => '{}'::jsonb
    );
  $$,
  'P0001',
  NULL,
  'BLOCCATO senza motivo -> errore'
);

SELECT throws_ok(
  $$
    SELECT vendite.fn_set_documento_canale_stato(
      p_sorgente_tipo_id => (SELECT src_preventivo_id FROM tmp_refs_doc_canali),
      p_sorgente_uid => (SELECT src_uid FROM tmp_refs_doc_canali),
      p_canale_codice => 'DDT_VENDITA',
      p_stato_canale => 'CONSUMATO',
      p_target_sorgente_tipo_id => (SELECT src_ordine_id FROM tmp_refs_doc_canali),
      p_target_sorgente_uid => NULL,
      p_meta => '{}'::jsonb
    );
  $$,
  'P0001',
  NULL,
  'target pair incompleta -> errore'
);

SELECT * FROM finish();
ROLLBACK;
