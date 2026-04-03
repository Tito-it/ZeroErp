-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: vendite.fn_crea_revisione_preventivo
-- ------------------------------------------------------------
-- Indice test (1..8):
-- 1) Funzione presente
-- 2) Riferimenti minimi disponibili
-- 3) Setup preventivo EMESSO con righe e indirizzi
-- 4) Revisione da EMESSO ammessa: nuova rev in DRAFT
-- 5) Revisione copia righe attive
-- 6) Revisione copia indirizzi
-- 7) Revisione disattiva precedente (is_revision_attiva = false)
-- 8) Revisione da DRAFT vietata
-- ------------------------------------------------------------

BEGIN;
SELECT plan(8);

-- ============================================================
-- 1) Funzione presente
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite'
      AND p.proname = 'fn_crea_revisione_preventivo'
  ),
  '1. fn_crea_revisione_preventivo presente'
);

-- ============================================================
-- 2) Riferimenti minimi
-- ============================================================
CREATE TEMP TABLE tmp_rv_refs AS
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
  (SELECT s.id FROM config.stati_doc_preventivi s
    WHERE s.codice = 'DRAFT' AND s.attivo IS TRUE LIMIT 1
  ) AS stato_draft_id,
  (SELECT s.id FROM config.stati_doc_preventivi s
    WHERE s.codice = 'EMESSO' AND s.attivo IS TRUE LIMIT 1
  ) AS stato_emesso_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1
  ) AS valuta_id,
  (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE LIMIT 1
  ) AS iva_id,
  (SELECT a.tipo_indirizzo_id
     FROM config.tipi_indirizzi_allowed a
    WHERE a.ambito = 'PREVENTIVI' AND a.attivo IS TRUE
    LIMIT 1
  ) AS tipo_indirizzo_id;

SELECT ok(
  (SELECT billing_account_id IS NOT NULL
      AND articolo_id IS NOT NULL
      AND stato_draft_id IS NOT NULL
      AND stato_emesso_id IS NOT NULL
   FROM tmp_rv_refs),
  '2. Riferimenti minimi disponibili'
);

-- ============================================================
-- 3) Setup preventivo EMESSO con righe e indirizzi
-- ============================================================
CREATE TEMP TABLE tmp_rv_prev AS
WITH ins AS (
  INSERT INTO vendite.preventivi (
    numero, rev, is_revision_attiva,
    billing_account_id, istanza_utility_id, utility_id,
    validita_dal, validita_al, valuta_id,
    stato_doc_preventivo_id, data,
    storicizza, meta
  )
  SELECT
    'PGTAP-RV-' || substr(md5(clock_timestamp()::text), 1, 8),
    0, true,
    r.billing_account_id, r.istanza_utility_id, r.utility_id,
    DATE '2026-06-01', DATE '2026-06-30', r.valuta_id,
    r.stato_emesso_id, DATE '2026-06-01',
    false, jsonb_build_object('test_scope', 'pgtap_revisione')
  FROM tmp_rv_refs r
  RETURNING id, uid, numero
)
SELECT * FROM ins;

-- 2 righe attive + 1 inattiva
INSERT INTO vendite.preventivi_righe (
  preventivo_id, articolo_id, qta_operativa, quantita,
  prezzo_unitario, iva_id, attivo, ordine, meta
)
SELECT p.id, r.articolo_id, 10, 10, 100.00, r.iva_id, true, 1,
       jsonb_build_object('test_scope', 'pgtap_revisione', 'riga', 1)
FROM tmp_rv_prev p, tmp_rv_refs r
UNION ALL
SELECT p.id, r.articolo_id, 5, 5, 50.00, r.iva_id, true, 2,
       jsonb_build_object('test_scope', 'pgtap_revisione', 'riga', 2)
FROM tmp_rv_prev p, tmp_rv_refs r
UNION ALL
SELECT p.id, r.articolo_id, 1, 1, 10.00, r.iva_id, false, 3,
       jsonb_build_object('test_scope', 'pgtap_revisione', 'riga', 3)
FROM tmp_rv_prev p, tmp_rv_refs r;

-- 1 indirizzo
INSERT INTO vendite.preventivi_indirizzi (
  preventivo_id, tipo_indirizzo_id, snapshot
)
SELECT p.id, r.tipo_indirizzo_id,
       jsonb_build_object('test', true)
FROM tmp_rv_prev p, tmp_rv_refs r
WHERE r.tipo_indirizzo_id IS NOT NULL;

SELECT ok(
  (SELECT id IS NOT NULL FROM tmp_rv_prev),
  '3. Setup preventivo EMESSO con righe e indirizzi'
);

-- ============================================================
-- 4) Revisione da EMESSO: nuova rev in DRAFT
-- ============================================================
CREATE TEMP TABLE tmp_rv_result AS
SELECT * FROM vendite.fn_crea_revisione_preventivo(
  (SELECT id FROM tmp_rv_prev),
  'pgtap'
);

SELECT ok(
  (SELECT nuova_rev = 1
      AND nuovo_preventivo_id IS NOT NULL
      AND numero = (SELECT numero FROM tmp_rv_prev)
   FROM tmp_rv_result),
  '4. Revisione da EMESSO: rev=1, stesso numero, nuovo id'
);

-- ============================================================
-- 5) Righe copiate: solo le 2 attive (non la inattiva)
-- ============================================================
SELECT ok(
  (SELECT COUNT(*) = 2
   FROM vendite.preventivi_righe pr
   WHERE pr.preventivo_id = (SELECT nuovo_preventivo_id FROM tmp_rv_result)
     AND pr.attivo IS TRUE),
  '5. Revisione copia solo righe attive (2 su 3)'
);

-- ============================================================
-- 6) Indirizzi copiati (stessa quantita' dell'originale)
-- ============================================================
SELECT ok(
  (SELECT COUNT(*) FROM vendite.preventivi_indirizzi
    WHERE preventivo_id = (SELECT nuovo_preventivo_id FROM tmp_rv_result))
  =
  (SELECT COUNT(*) FROM vendite.preventivi_indirizzi
    WHERE preventivo_id = (SELECT id FROM tmp_rv_prev)),
  '6. Revisione copia indirizzi (stesso numero dell''originale)'
);

-- ============================================================
-- 7) Revisione precedente disattivata
-- ============================================================
SELECT ok(
  (SELECT is_revision_attiva = false
   FROM vendite.preventivi
   WHERE id = (SELECT id FROM tmp_rv_prev)),
  '7. Revisione precedente disattivata (is_revision_attiva = false)'
);

-- ============================================================
-- 8) Revisione da DRAFT vietata
-- ============================================================
CREATE TEMP TABLE tmp_rv_prev_draft AS
WITH ins AS (
  INSERT INTO vendite.preventivi (
    numero, rev, is_revision_attiva,
    billing_account_id, istanza_utility_id, utility_id,
    validita_dal, validita_al, valuta_id,
    stato_doc_preventivo_id, data,
    storicizza, meta
  )
  SELECT
    'PGTAP-RVD-' || substr(md5(clock_timestamp()::text), 1, 8),
    0, true,
    r.billing_account_id, r.istanza_utility_id, r.utility_id,
    DATE '2026-06-01', DATE '2026-06-30', r.valuta_id,
    r.stato_draft_id, DATE '2026-06-01',
    false, jsonb_build_object('test_scope', 'pgtap_revisione')
  FROM tmp_rv_refs r
  RETURNING id, uid, numero
)
SELECT * FROM ins;

SELECT throws_ok(
  format(
    'SELECT * FROM vendite.fn_crea_revisione_preventivo(%s, ''pgtap'')',
    (SELECT id FROM tmp_rv_prev_draft)
  ),
  NULL, NULL,
  '8. Revisione da DRAFT vietata'
);

-- ============================================================
SELECT * FROM finish();
ROLLBACK;
