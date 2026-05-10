-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: drop uq_commesse_attivita_src_uid_partial
-- ------------------------------------------------------------
-- Indice test (1..4):
-- 1) Indice uq_commesse_attivita_src_uid_partial non esiste piu`
-- 2) Indice uq_commesse_attivita_commessa_segment esiste (constraint corretto rimasto)
-- 3) Smoke multi-riga: 2 commesse_attivita con stessa sorgente ma segment_key diversi → accettati
-- 4) uq_commesse_sorgenti_src_uid_ruolo ancora attivo (semantica 1-doc → 1-commessa ROOT)
-- ------------------------------------------------------------

BEGIN;
SELECT plan(4);

-- ============================================================
-- Setup riferimenti minimi
-- ============================================================
CREATE TEMP TABLE tmp_refs_srcuid AS
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
  (SELECT u.id
     FROM catalogo.unita_misura u
    WHERE u.attivo IS TRUE
    ORDER BY u.id LIMIT 1
  ) AS uom_id,
  (SELECT t.id
     FROM config.tipi_doc_fiscale t
    WHERE t.attivo IS TRUE
    ORDER BY t.id LIMIT 1
  ) AS tipo_doc_fiscale_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1) AS valuta_id,
  (SELECT sc.id FROM vendite.stati_commessa sc WHERE sc.attivo IS TRUE ORDER BY sc.id LIMIT 1) AS stato_commessa_id,
  (SELECT s.id FROM config.sorgenti s WHERE s.codice = 'PREVENTIVO' AND s.attivo IS TRUE LIMIT 1) AS sorgente_tipo_id,
  -- uid sorgente fisso deterministico per il test (no collision con dati reali)
  '00000000-0000-0000-0001-000000000099'::uuid AS sorgente_uid_test;

-- ============================================================
-- TEST 1) Indice ridondante non esiste piu`
-- ============================================================
SELECT ok(
  NOT EXISTS (
    SELECT 1
    FROM pg_indexes
    WHERE schemaname = 'vendite'
      AND tablename  = 'commesse_attivita'
      AND indexname  = 'uq_commesse_attivita_src_uid_partial'
  ),
  'uq_commesse_attivita_src_uid_partial non esiste (drop eseguito)'
);

-- ============================================================
-- TEST 2) Indice corretto (commessa_id, segment_key) ancora presente
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1
    FROM pg_indexes
    WHERE schemaname = 'vendite'
      AND tablename  = 'commesse_attivita'
      AND indexname  = 'uq_commesse_attivita_commessa_segment'
  ),
  'uq_commesse_attivita_commessa_segment esiste (constraint corretto rimasto)'
);

-- ============================================================
-- TEST 3) Multi-riga: 2 righe con stessa sorgente ma segment_key diversi
-- Verifica che il drop abiliti il pattern 1 documento → N righe commessa.
-- ============================================================
CREATE TEMP TABLE tmp_commessa_srcuid AS
WITH ins AS (
  INSERT INTO vendite.commesse (
    codice, billing_account_id, utility_id, stato_commessa_id
  )
  SELECT
    'PGTAP-SRCUID-' || substr(md5(clock_timestamp()::text), 1, 8),
    r.billing_account_id, r.utility_id, r.stato_commessa_id
  FROM tmp_refs_srcuid r
  RETURNING id
)
SELECT id FROM ins;

SELECT lives_ok(
  $$
    INSERT INTO vendite.commesse_attivita (
      commessa_id, segment_key,
      articolo_id, istanza_utility_id, data_attivita, uom_id, quantita,
      competenza_mese, competenza_dal, competenza_al,
      tipo_doc_fiscale_id, valuta_id, prezzo_snapshot,
      pricing_mode, stato_approvazione, stato_emissione,
      sorgente_tipo_id, sorgente_uid
    )
    SELECT
      (SELECT id FROM tmp_commessa_srcuid),
      'PREV:' || r.sorgente_uid_test::text || ':R:' || v.riga::text,
      r.articolo_id, r.istanza_utility_id, DATE '2026-06-01', r.uom_id, 1,
      DATE '2026-06-01', DATE '2026-06-01', DATE '2026-06-30',
      r.tipo_doc_fiscale_id, r.valuta_id, 10.00,
      'FIXED', 'BOZZA', 'NON_EMESSA',
      r.sorgente_tipo_id, r.sorgente_uid_test::text
    FROM tmp_refs_srcuid r
    CROSS JOIN (VALUES (1),(2)) AS v(riga);
  $$,
  'Multi-riga: 2 righe con stessa sorgente_uid ma segment_key diversi → inserimento accettato'
);

-- ============================================================
-- TEST 4) uq_commesse_sorgenti_src_uid_ruolo ancora attivo
-- Verifica che la semantica "1 documento → 1 commessa ROOT" sia preservata.
-- ============================================================
SELECT throws_ok(
  $$
    WITH ids AS (SELECT id FROM tmp_commessa_srcuid),
         refs AS (SELECT sorgente_tipo_id, sorgente_uid_test FROM tmp_refs_srcuid)
    INSERT INTO vendite.commesse_sorgenti (commessa_id, sorgente_tipo_id, sorgente_uid, ruolo_link)
    SELECT ids.id, refs.sorgente_tipo_id, refs.sorgente_uid_test::text, 'ROOT'
    FROM ids, refs
    UNION ALL
    SELECT ids.id, refs.sorgente_tipo_id, refs.sorgente_uid_test::text, 'ROOT'
    FROM ids, refs;
  $$,
  '23505',
  NULL,
  'uq_commesse_sorgenti_src_uid_ruolo ancora attivo: duplicato ROOT bloccato'
);

SELECT * FROM finish();
ROLLBACK;
