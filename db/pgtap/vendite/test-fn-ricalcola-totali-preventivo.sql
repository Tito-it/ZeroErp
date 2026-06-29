-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: vendite.fn_ricalcola_totali_preventivo
--       + trigger trgfn_preventivi_righe_ricalcola_totali
-- ------------------------------------------------------------
-- Indice test (1..8):
-- 1) Funzione presente
-- 2) Trigger STATEMENT presenti su preventivi_righe (ins/upd/dlt)
-- 3) Riferimenti minimi disponibili
-- 4) Setup preventivo DRAFT
-- 5) Insert riga: trigger aggiorna totali testata
-- 6) Ricalcolo corretto con sconto
-- 7) Ricalcolo corretto con IVA
-- 8) Delete riga: totali tornano a 0
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
      AND p.proname = 'fn_ricalcola_totali_preventivo'
  ),
  '1. fn_ricalcola_totali_preventivo presente'
);

-- ============================================================
-- 2) Trigger STATEMENT presenti su preventivi_righe
-- ============================================================
SELECT ok(
  (SELECT COUNT(*) = 3
   FROM pg_trigger t
   JOIN pg_class c ON c.oid = t.tgrelid
   JOIN pg_namespace n ON n.oid = c.relnamespace
   WHERE n.nspname = 'vendite'
     AND c.relname = 'preventivi_righe'
     AND t.tgname IN (
       'trg_preventivi_righe_z90_ricalcola_totali_ins',
       'trg_preventivi_righe_z90_ricalcola_totali_upd',
       'trg_preventivi_righe_z90_ricalcola_totali_dlt'
     )
  ),
  '2. Trigger STATEMENT ricalcolo presenti (ins/upd/dlt)'
);

-- ============================================================
-- 3) Riferimenti minimi
-- ============================================================
CREATE TEMP TABLE tmp_rc_refs AS
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
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1
  ) AS valuta_id,
  -- emittente fiscale (richiesto da trigger BEFORE INSERT preventivi
  -- quando GUC app.current_user_id e' vuota - contesto pgTAP).
  (SELECT ef.id FROM anagrafiche.emittenti_fiscali ef
    WHERE ef.attivo IS TRUE
    ORDER BY ef.id LIMIT 1
  ) AS emittente_fiscale_id,
  (SELECT i.id FROM config.iva i
    WHERE i.attivo IS TRUE AND i.aliquota_iva > 0
    LIMIT 1
  ) AS iva_id,
  (SELECT i.aliquota_iva FROM config.iva i
    WHERE i.attivo IS TRUE AND i.aliquota_iva > 0
    LIMIT 1
  ) AS iva_aliquota;

SELECT ok(
  (SELECT billing_account_id IS NOT NULL
      AND articolo_id IS NOT NULL
      AND stato_draft_id IS NOT NULL
      AND emittente_fiscale_id IS NOT NULL
      AND iva_id IS NOT NULL
      AND iva_aliquota > 0
   FROM tmp_rc_refs),
  '3. Riferimenti minimi disponibili (con IVA > 0 + emittente fiscale)'
);

-- ============================================================
-- 4) Setup preventivo DRAFT (totali iniziali = 0)
-- ============================================================
CREATE TEMP TABLE tmp_rc_prev AS
WITH ins AS (
  INSERT INTO vendite.preventivi (
    numero, rev,
    billing_account_id, istanza_utility_id, utility_id,
    validita_dal, validita_al, valuta_id,
    stato_doc_preventivo_id, data,
    emittente_fiscale_id,
    storicizza, meta
  )
  SELECT
    'PGTAP-RC-' || substr(md5(clock_timestamp()::text), 1, 8),
    0,
    r.billing_account_id, r.istanza_utility_id, r.utility_id,
    DATE '2026-06-01', DATE '2026-06-30', r.valuta_id,
    r.stato_draft_id, DATE '2026-06-01',
    r.emittente_fiscale_id,
    false, jsonb_build_object('test_scope', 'pgtap_ricalcola')
  FROM tmp_rc_refs r
  RETURNING id, uid, numero
)
SELECT * FROM ins;

SELECT ok(
  (SELECT totale_imponibile = 0 AND totale_iva = 0 AND totale_documento = 0
   FROM vendite.preventivi
   WHERE id = (SELECT id FROM tmp_rc_prev)),
  '4. Setup preventivo DRAFT con totali = 0'
);

-- ============================================================
-- 5) Insert riga senza sconto: trigger aggiorna totali
--    qta=10, prezzo=100, sconto=0, IVA da refs
--    imponibile atteso: 10 * 100 = 1000
-- ============================================================
CREATE TEMP TABLE tmp_rc_riga1 AS
WITH ins AS (
  INSERT INTO vendite.preventivi_righe (
    preventivo_id, articolo_id, qta_operativa, quantita,
    prezzo_unitario, sconto_percentuale, iva_id,
    attivo, ordine, meta
  )
  SELECT
    p.id, r.articolo_id, 10, 10, 100.00, 0, r.iva_id,
    true, 1, jsonb_build_object('test_scope', 'pgtap_ricalcola')
  FROM tmp_rc_prev p, tmp_rc_refs r
  RETURNING id
)
SELECT * FROM ins;

SELECT ok(
  (SELECT totale_imponibile = 1000.00
   FROM vendite.preventivi
   WHERE id = (SELECT id FROM tmp_rc_prev)),
  '5. Trigger ricalcolo: imponibile = 1000 dopo insert riga (qta=10 * prezzo=100)'
);

-- ============================================================
-- 6) Insert riga con sconto 20%: ricalcolo corretto
--    qta=5, prezzo=200, sconto=20% -> importo_riga = 5*200*0.8 = 800
--    totale imponibile atteso: 1000 + 800 = 1800
-- ============================================================
INSERT INTO vendite.preventivi_righe (
  preventivo_id, articolo_id, qta_operativa, quantita,
  prezzo_unitario, sconto_percentuale, iva_id,
  attivo, ordine, meta
)
SELECT
  p.id, r.articolo_id, 5, 5, 200.00, 20, r.iva_id,
  true, 2, jsonb_build_object('test_scope', 'pgtap_ricalcola')
FROM tmp_rc_prev p, tmp_rc_refs r;

SELECT ok(
  (SELECT totale_imponibile = 1800.00
   FROM vendite.preventivi
   WHERE id = (SELECT id FROM tmp_rc_prev)),
  '6. Ricalcolo con sconto 20%: imponibile = 1800 (1000 + 800)'
);

-- ============================================================
-- 7) Verifica IVA calcolata
--    totale_iva = 1800 * aliquota_iva / 100
-- ============================================================
SELECT ok(
  (SELECT totale_iva = ROUND(1800.00 * r.iva_aliquota / 100, 2)
   FROM vendite.preventivi p2, tmp_rc_refs r
   WHERE p2.id = (SELECT id FROM tmp_rc_prev)),
  '7. IVA calcolata correttamente su imponibile 1800'
);

-- ============================================================
-- 8) Delete riga1: totali ricalcolati (solo riga2 rimane)
--    imponibile atteso: 800 (solo riga con sconto)
-- ============================================================
DELETE FROM vendite.preventivi_righe
WHERE id = (SELECT id FROM tmp_rc_riga1);

SELECT ok(
  (SELECT totale_imponibile = 800.00
   FROM vendite.preventivi
   WHERE id = (SELECT id FROM tmp_rc_prev)),
  '8. Delete riga: imponibile ricalcolato a 800 (solo riga2)'
);

-- ============================================================
SELECT * FROM finish();
ROLLBACK;
