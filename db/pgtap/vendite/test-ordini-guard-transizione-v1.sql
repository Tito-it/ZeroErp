-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: vendite.trgfn_ordini_guard_transizione (+ trigger)
-- ------------------------------------------------------------
-- Brief: docs/it/dev/work-in-progress/brief-ordini-azioni-data-driven.md
-- Enforcement DB-first del grafo transizioni stato ordine letto da
-- config.transizioni_stati_ordini.
-- Indice test (1..6):
-- 1) trg_ordini_a10_guard_transizione_upd esiste
-- 2) DRAFT->CONFERMATO con riga -> ok (lives)
-- 3) DRAFT->CONFERMATO senza righe -> throws E_ORDINE_CONFERMA_SENZA_RIGHE
-- 4) DRAFT->ANNULLATO -> ok (transizione manuale attiva)
-- 5) DRAFT->SPEDITO (fuori matrice) -> throws E_ORDINE_TRANSIZIONE_NON_AMMESSA
-- 6) CONFERMATO->ANNULLATO (attivo=false) -> throws E_ORDINE_TRANSIZIONE_NON_AMMESSA
-- ------------------------------------------------------------

-- Nota emittente: gli ordini passano emittente_fiscale_id esplicito e
--   billing_account_id=NULL (GUC vuota in pgTAP); cosi' bypassano sia
--   trgfn_ordini_default_emittente sia il guard di coerenza BA. Le transizioni
--   di stato testate non dipendono dal billing_account.

BEGIN;
SELECT plan(6);

-- Contesto non-API: GUC vuota.
SELECT set_config('app.current_user_id', '', true);

-- ============================================================
-- Riferimenti minimi
-- ============================================================
CREATE TEMP TABLE tmp_refs_gt AS
SELECT
  (SELECT ef.id FROM anagrafiche.emittenti_fiscali ef
    WHERE ef.attivo IS TRUE ORDER BY ef.id LIMIT 1
  ) AS emittente_fiscale_id,
  (SELECT sr.id FROM anagrafiche.soggetti_ruoli sr ORDER BY sr.id LIMIT 1
  ) AS soggetto_ruolo_id,
  (SELECT a.id FROM catalogo.articoli a WHERE a.attivo IS TRUE
    ORDER BY a.data_insert DESC NULLS LAST, a.id LIMIT 1
  ) AS articolo_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1) AS valuta_id,
  (SELECT id FROM config.stati_doc_ordini WHERE codice_interno = 'DRAFT'      LIMIT 1) AS stato_draft_id,
  (SELECT id FROM config.stati_doc_ordini WHERE codice_interno = 'CONFERMATO' LIMIT 1) AS stato_conf_id,
  (SELECT id FROM config.stati_doc_ordini WHERE codice_interno = 'ANNULLATO'  LIMIT 1) AS stato_ann_id,
  (SELECT id FROM config.stati_doc_ordini WHERE codice_interno = 'SPEDITO'    LIMIT 1) AS stato_sped_id;

-- Helper: crea ordine DRAFT e ritorna id. Slot via meta.
-- Slot A: DRAFT con riga (test 2)
CREATE TEMP TABLE tmp_gt_a AS
WITH ins AS (
  INSERT INTO vendite.ordini (soggetto_ruolo_id, billing_account_id, emittente_fiscale_id,
      stato_doc_ordine_id, valuta_id, data, storicizza, meta)
  SELECT r.soggetto_ruolo_id, NULL::bigint, r.emittente_fiscale_id,r.stato_draft_id, r.valuta_id,
         DATE '2026-06-15', false, '{"test_scope":"pgtap_guard_transizione","slot":"A"}'::jsonb
  FROM tmp_refs_gt r RETURNING id
) SELECT id FROM ins;
INSERT INTO vendite.ordini_righe (ordine_id, riga_nr, articolo_id, descrizione,
    qta_operativa, quantita, prezzo_unitario, attivo, storicizza, meta)
SELECT o.id, 1, r.articolo_id, 'riga A', 3.0, 3.0, 10.0, true, false, '{}'::jsonb
FROM tmp_gt_a o, tmp_refs_gt r;

-- Slot B: DRAFT senza righe (test 3)
CREATE TEMP TABLE tmp_gt_b AS
WITH ins AS (
  INSERT INTO vendite.ordini (soggetto_ruolo_id, billing_account_id, emittente_fiscale_id,
      stato_doc_ordine_id, valuta_id, data, storicizza, meta)
  SELECT r.soggetto_ruolo_id, NULL::bigint, r.emittente_fiscale_id,r.stato_draft_id, r.valuta_id,
         DATE '2026-06-15', false, '{"test_scope":"pgtap_guard_transizione","slot":"B"}'::jsonb
  FROM tmp_refs_gt r RETURNING id
) SELECT id FROM ins;

-- Slot C: DRAFT con riga (test 4 annulla)
CREATE TEMP TABLE tmp_gt_c AS
WITH ins AS (
  INSERT INTO vendite.ordini (soggetto_ruolo_id, billing_account_id, emittente_fiscale_id,
      stato_doc_ordine_id, valuta_id, data, storicizza, meta)
  SELECT r.soggetto_ruolo_id, NULL::bigint, r.emittente_fiscale_id,r.stato_draft_id, r.valuta_id,
         DATE '2026-06-15', false, '{"test_scope":"pgtap_guard_transizione","slot":"C"}'::jsonb
  FROM tmp_refs_gt r RETURNING id
) SELECT id FROM ins;
INSERT INTO vendite.ordini_righe (ordine_id, riga_nr, articolo_id, descrizione,
    qta_operativa, quantita, prezzo_unitario, attivo, storicizza, meta)
SELECT o.id, 1, r.articolo_id, 'riga C', 3.0, 3.0, 10.0, true, false, '{}'::jsonb
FROM tmp_gt_c o, tmp_refs_gt r;

-- Slot D: DRAFT con riga (test 5 transizione fuori matrice)
CREATE TEMP TABLE tmp_gt_d AS
WITH ins AS (
  INSERT INTO vendite.ordini (soggetto_ruolo_id, billing_account_id, emittente_fiscale_id,
      stato_doc_ordine_id, valuta_id, data, storicizza, meta)
  SELECT r.soggetto_ruolo_id, NULL::bigint, r.emittente_fiscale_id,r.stato_draft_id, r.valuta_id,
         DATE '2026-06-15', false, '{"test_scope":"pgtap_guard_transizione","slot":"D"}'::jsonb
  FROM tmp_refs_gt r RETURNING id
) SELECT id FROM ins;
INSERT INTO vendite.ordini_righe (ordine_id, riga_nr, articolo_id, descrizione,
    qta_operativa, quantita, prezzo_unitario, attivo, storicizza, meta)
SELECT o.id, 1, r.articolo_id, 'riga D', 3.0, 3.0, 10.0, true, false, '{}'::jsonb
FROM tmp_gt_d o, tmp_refs_gt r;

-- Slot E: CONFERMATO con riga (test 6 CONFERMATO->ANNULLATO disabilitata)
CREATE TEMP TABLE tmp_gt_e AS
WITH ins AS (
  INSERT INTO vendite.ordini (soggetto_ruolo_id, billing_account_id, emittente_fiscale_id,
      stato_doc_ordine_id, valuta_id, data, storicizza, meta)
  SELECT r.soggetto_ruolo_id, NULL::bigint, r.emittente_fiscale_id,r.stato_conf_id, r.valuta_id,
         DATE '2026-06-15', false, '{"test_scope":"pgtap_guard_transizione","slot":"E"}'::jsonb
  FROM tmp_refs_gt r RETURNING id
) SELECT id FROM ins;
INSERT INTO vendite.ordini_righe (ordine_id, riga_nr, articolo_id, descrizione,
    qta_operativa, quantita, prezzo_unitario, attivo, storicizza, meta)
SELECT o.id, 1, r.articolo_id, 'riga E', 3.0, 3.0, 10.0, true, false, '{}'::jsonb
FROM tmp_gt_e o, tmp_refs_gt r;

-- ============================================================
-- 1) trigger esiste
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1 FROM pg_trigger
     WHERE tgname = 'trg_ordini_a10_guard_transizione_upd'
       AND NOT tgisinternal
  ),
  '1) trg_ordini_a10_guard_transizione_upd esiste'
);

-- ============================================================
-- 2) DRAFT->CONFERMATO con riga -> ok
-- ============================================================
SELECT lives_ok(
  format($q$UPDATE vendite.ordini SET stato_doc_ordine_id =
              (SELECT stato_conf_id FROM tmp_refs_gt) WHERE id = %s$q$,
         (SELECT id FROM tmp_gt_a)),
  '2) DRAFT->CONFERMATO con riga -> ok'
);

-- ============================================================
-- 3) DRAFT->CONFERMATO senza righe -> throws E_ORDINE_CONFERMA_SENZA_RIGHE
-- ============================================================
SELECT throws_ok(
  format($q$UPDATE vendite.ordini SET stato_doc_ordine_id =
              (SELECT stato_conf_id FROM tmp_refs_gt) WHERE id = %s$q$,
         (SELECT id FROM tmp_gt_b)),
  'P0001', NULL,
  '3) DRAFT->CONFERMATO senza righe -> throws E_ORDINE_CONFERMA_SENZA_RIGHE'
);

-- ============================================================
-- 4) DRAFT->ANNULLATO -> ok
-- ============================================================
SELECT lives_ok(
  format($q$UPDATE vendite.ordini SET stato_doc_ordine_id =
              (SELECT stato_ann_id FROM tmp_refs_gt) WHERE id = %s$q$,
         (SELECT id FROM tmp_gt_c)),
  '4) DRAFT->ANNULLATO -> ok (transizione manuale attiva)'
);

-- ============================================================
-- 5) DRAFT->SPEDITO (fuori matrice) -> throws E_ORDINE_TRANSIZIONE_NON_AMMESSA
-- ============================================================
SELECT throws_ok(
  format($q$UPDATE vendite.ordini SET stato_doc_ordine_id =
              (SELECT stato_sped_id FROM tmp_refs_gt) WHERE id = %s$q$,
         (SELECT id FROM tmp_gt_d)),
  'P0001', NULL,
  '5) DRAFT->SPEDITO (fuori matrice) -> throws E_ORDINE_TRANSIZIONE_NON_AMMESSA'
);

-- ============================================================
-- 6) CONFERMATO->ANNULLATO (attivo=false) -> throws E_ORDINE_TRANSIZIONE_NON_AMMESSA
-- ============================================================
SELECT throws_ok(
  format($q$UPDATE vendite.ordini SET stato_doc_ordine_id =
              (SELECT stato_ann_id FROM tmp_refs_gt) WHERE id = %s$q$,
         (SELECT id FROM tmp_gt_e)),
  'P0001', NULL,
  '6) CONFERMATO->ANNULLATO (attivo=false) -> throws E_ORDINE_TRANSIZIONE_NON_AMMESSA'
);

SELECT * FROM finish();
ROLLBACK;
