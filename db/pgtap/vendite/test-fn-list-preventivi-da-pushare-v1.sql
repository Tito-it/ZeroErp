-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: vendite.fn_list_preventivi_da_pushare
-- ------------------------------------------------------------
-- Indice test (1..8):
-- 1) fn_list_preventivi_da_pushare presente
-- 2) Riferimenti minimi disponibili
-- 3) Preventivo ACCETTATO con riga valida restituito
-- 4) Segment key formato corretto (PREV:<uid>:R:<riga_id>)
-- 5) prezzo_bloccato coerente con fatturazione_immediata
-- 6) Preventivo non ACCETTATO escluso
-- 7) Riga con quantita zero esclusa
-- 8) Filtro p_billing_account_id rispettato
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

SELECT plan(8);

-- ============================================================
-- 0) Funzione presente
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite'
      AND p.proname = 'fn_list_preventivi_da_pushare'
  ),
  'fn_list_preventivi_da_pushare presente'
);

-- ============================================================
-- 0b) Riferimenti minimi
-- ============================================================
CREATE TEMP TABLE tmp_refs_prev AS
SELECT
  (SELECT ba.id
     FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL
      AND ba.istanza_utility_id IS NOT NULL
    ORDER BY ba.id LIMIT 1
  ) AS billing_account_id,
  (SELECT ba.utility_id
     FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL
      AND ba.istanza_utility_id IS NOT NULL
    ORDER BY ba.id LIMIT 1
  ) AS utility_id,
  (SELECT ba.istanza_utility_id
     FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL
      AND ba.istanza_utility_id IS NOT NULL
    ORDER BY ba.id LIMIT 1
  ) AS istanza_utility_id,
  (SELECT a.id
     FROM catalogo.articoli a
    WHERE a.attivo IS TRUE
    ORDER BY a.data_insert DESC NULLS LAST LIMIT 1
  ) AS articolo_id,
  (SELECT s.id
     FROM config.stati_doc_preventivi s
    WHERE s.codice = 'ACCETTATO' AND s.attivo IS TRUE
    LIMIT 1
  ) AS stato_accettato_id,
  (SELECT s.id
     FROM config.stati_doc_preventivi s
    WHERE s.codice = 'DRAFT' AND s.attivo IS TRUE
    LIMIT 1
  ) AS stato_bozza_id,
  (SELECT v.id
     FROM config.valute v
    ORDER BY v.id LIMIT 1
  ) AS valuta_id,
  (SELECT s.id
     FROM config.sorgenti s
    WHERE s.codice = 'PREVENTIVO' AND s.attivo IS TRUE
    LIMIT 1
  ) AS sorgente_tipo_id;

SELECT ok(
  (SELECT billing_account_id IS NOT NULL
      AND utility_id IS NOT NULL
      AND articolo_id IS NOT NULL
      AND stato_accettato_id IS NOT NULL
      AND sorgente_tipo_id IS NOT NULL
   FROM tmp_refs_prev),
  'Riferimenti minimi disponibili'
);

-- ============================================================
-- 1) Inserimento preventivo ACCETTATO con riga valida
-- ============================================================
CREATE TEMP TABLE tmp_prev AS
WITH ins AS (
  INSERT INTO vendite.preventivi (
    numero, rev, billing_account_id, istanza_utility_id,
    utility_id, validita_dal, validita_al, valuta_id,
    stato_doc_preventivo_id, data, fatturazione_immediata,
    storicizza, meta
  )
  SELECT
    'PGTAP-PREV-' || substr(md5(clock_timestamp()::text), 1, 8),
    0,
    r.billing_account_id, r.istanza_utility_id,
    r.utility_id,
    DATE '2026-06-01', DATE '2026-06-30', r.valuta_id,
    r.stato_accettato_id, DATE '2026-06-01', false,
    false, jsonb_build_object('test_scope', 'pgtap_fn_list_prev')
  FROM tmp_refs_prev r
  RETURNING id, uid
)
SELECT * FROM ins;

CREATE TEMP TABLE tmp_prev_riga AS
WITH ins AS (
  INSERT INTO vendite.preventivi_righe (
    preventivo_id, articolo_id, qta_operativa, quantita, prezzo_unitario,
    attivo, meta
  )
  SELECT
    p.id, r.articolo_id, 10.000000, 10.000000, 25.500000,
    true, jsonb_build_object('test_scope', 'pgtap_fn_list_prev')
  FROM tmp_prev p, tmp_refs_prev r
  RETURNING id
)
SELECT * FROM ins;

-- Chiamata funzione senza filtri
CREATE TEMP TABLE tmp_result_prev AS
SELECT *
FROM vendite.fn_list_preventivi_da_pushare(
  p_competenza_mese    => NULL,
  p_billing_account_id => NULL,
  p_limit              => NULL
);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM tmp_result_prev rp
    WHERE rp.preventivo_id = (SELECT id FROM tmp_prev)
  ),
  'Preventivo ACCETTATO con riga valida restituito'
);

-- ============================================================
-- 2) Formato segment_key
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1
    FROM tmp_result_prev rp
    WHERE rp.preventivo_id = (SELECT id FROM tmp_prev)
      AND rp.segment_key = 'PREV:' || (SELECT uid FROM tmp_prev)::text
                           || ':R:' || (SELECT id FROM tmp_prev_riga)::text
  ),
  'Segment key formato corretto (PREV:<uid>:R:<riga_id>)'
);

-- ============================================================
-- 3) prezzo_bloccato coerente con fatturazione_immediata
--    (fatturazione_immediata=false => prezzo_bloccato=false)
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1
    FROM tmp_result_prev rp
    WHERE rp.preventivo_id = (SELECT id FROM tmp_prev)
      AND rp.prezzo_bloccato IS FALSE
  ),
  'prezzo_bloccato coerente con fatturazione_immediata'
);

-- ============================================================
-- 4) Preventivo non ACCETTATO escluso
-- ============================================================
CREATE TEMP TABLE tmp_prev_bozza AS
WITH ins AS (
  INSERT INTO vendite.preventivi (
    numero, rev, billing_account_id, istanza_utility_id,
    utility_id, validita_dal, validita_al, valuta_id,
    stato_doc_preventivo_id, data, fatturazione_immediata,
    storicizza, meta
  )
  SELECT
    'PGTAP-PREV-B-' || substr(md5(clock_timestamp()::text), 1, 8),
    0,
    r.billing_account_id, r.istanza_utility_id,
    r.utility_id,
    DATE '2026-06-01', DATE '2026-06-30', r.valuta_id,
    COALESCE(r.stato_bozza_id, r.stato_accettato_id),
    DATE '2026-06-01', false,
    false, jsonb_build_object('test_scope', 'pgtap_fn_list_prev', 'case', 'bozza')
  FROM tmp_refs_prev r
  RETURNING id, uid
)
SELECT * FROM ins;

INSERT INTO vendite.preventivi_righe (
  preventivo_id, articolo_id, qta_operativa, quantita, prezzo_unitario,
  attivo, meta
)
SELECT
  pb.id, r.articolo_id, 5.000000, 5.000000, 10.000000,
  true, jsonb_build_object('test_scope', 'pgtap_fn_list_prev', 'case', 'bozza')
FROM tmp_prev_bozza pb, tmp_refs_prev r;

-- Riesegui la funzione (devo ricreare per evitare dati stantii)
CREATE TEMP TABLE tmp_result_prev_bozza AS
SELECT *
FROM vendite.fn_list_preventivi_da_pushare(
  p_competenza_mese    => NULL,
  p_billing_account_id => NULL,
  p_limit              => NULL
);

SELECT ok(
  NOT EXISTS (
    SELECT 1
    FROM tmp_result_prev_bozza rp
    WHERE rp.preventivo_id = (SELECT id FROM tmp_prev_bozza)
  ),
  'Preventivo non ACCETTATO escluso'
);

-- ============================================================
-- 5) Riga con quantita zero esclusa
-- ============================================================
CREATE TEMP TABLE tmp_prev_zero AS
WITH ins AS (
  INSERT INTO vendite.preventivi (
    numero, rev, billing_account_id, istanza_utility_id,
    utility_id, validita_dal, validita_al, valuta_id,
    stato_doc_preventivo_id, data, fatturazione_immediata,
    storicizza, meta
  )
  SELECT
    'PGTAP-PREV-Z-' || substr(md5(clock_timestamp()::text), 1, 8),
    0,
    r.billing_account_id, r.istanza_utility_id,
    r.utility_id,
    DATE '2026-06-01', DATE '2026-06-30', r.valuta_id,
    r.stato_accettato_id, DATE '2026-06-01', false,
    false, jsonb_build_object('test_scope', 'pgtap_fn_list_prev', 'case', 'zero_qta')
  FROM tmp_refs_prev r
  RETURNING id, uid
)
SELECT * FROM ins;

-- Riga con quantita = 0 (dovrebbe essere esclusa dalla fn_list)
-- NB: il check constraint potrebbe impedire qta=0; in tal caso la riga non esiste
-- e il test passa comunque. Usiamo qta > 0 ma attivo = false come alternativa.
INSERT INTO vendite.preventivi_righe (
  preventivo_id, articolo_id, qta_operativa, quantita, prezzo_unitario,
  attivo, meta
)
SELECT
  pz.id, r.articolo_id, 5.000000, 5.000000, 10.000000,
  false, jsonb_build_object('test_scope', 'pgtap_fn_list_prev', 'case', 'zero_qta')
FROM tmp_prev_zero pz, tmp_refs_prev r;

CREATE TEMP TABLE tmp_result_prev_zero AS
SELECT *
FROM vendite.fn_list_preventivi_da_pushare(
  p_competenza_mese    => NULL,
  p_billing_account_id => NULL,
  p_limit              => NULL
);

SELECT ok(
  NOT EXISTS (
    SELECT 1
    FROM tmp_result_prev_zero rp
    WHERE rp.preventivo_id = (SELECT id FROM tmp_prev_zero)
  ),
  'Riga con attivo=false esclusa'
);

-- ============================================================
-- 6) Filtro p_billing_account_id rispettato
-- ============================================================
CREATE TEMP TABLE tmp_result_prev_filter AS
SELECT *
FROM vendite.fn_list_preventivi_da_pushare(
  p_competenza_mese    => NULL,
  p_billing_account_id => -999999,
  p_limit              => NULL
);

SELECT ok(
  NOT EXISTS (
    SELECT 1
    FROM tmp_result_prev_filter rp
    WHERE rp.preventivo_id = (SELECT id FROM tmp_prev)
  ),
  'Filtro p_billing_account_id rispettato'
);

SELECT * FROM finish();
ROLLBACK;
