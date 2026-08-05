-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: vendite.fn_list_preventivi_da_pushare natura-aware (20260609-09).
--       Il push su commessa deve includere SOLO le righe con natura
--       destinazione_tipo='COMMESSA' (natura NULL = pregresso, inclusa) ed
--       ESCLUDERE la merce (destinazione ORDINE), che va su
--       fn_push_preventivo_a_ordine. Niente doppio routing.
--
-- Indice test (1..4):
--   1) preventivo misto -> la riga SERVIZIO_UNA_TANTUM e' inclusa
--   2) preventivo misto -> la riga MERCE e' esclusa
--   3) riga con natura_vendita_id NULL (pregresso) -> inclusa
--   4) preventivo di sole righe merce -> lista vuota
-- ------------------------------------------------------------

BEGIN;
-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(4);

CREATE TEMP TABLE tmp_refs AS
SELECT
  (SELECT ba.id FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL AND ba.istanza_utility_id IS NOT NULL
      AND ba.soggetto_ruolo_id IS NOT NULL ORDER BY ba.id LIMIT 1) AS billing_account_id,
  (SELECT ba.utility_id FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL AND ba.istanza_utility_id IS NOT NULL
      AND ba.soggetto_ruolo_id IS NOT NULL ORDER BY ba.id LIMIT 1) AS utility_id,
  (SELECT ba.istanza_utility_id FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL AND ba.istanza_utility_id IS NOT NULL
      AND ba.soggetto_ruolo_id IS NOT NULL ORDER BY ba.id LIMIT 1) AS istanza_utility_id,
  (SELECT a.id FROM catalogo.articoli a
    WHERE a.attivo IS TRUE AND a.is_composito = FALSE ORDER BY a.id LIMIT 1 OFFSET 0) AS art_merce_id,
  (SELECT a.id FROM catalogo.articoli a
    WHERE a.attivo IS TRUE AND a.is_composito = FALSE ORDER BY a.id LIMIT 1 OFFSET 1) AS art_serv_id,
  (SELECT s.id FROM config.stati_doc_preventivi s
    WHERE s.codice = 'ACCETTATO' AND s.attivo IS TRUE LIMIT 1) AS stato_accettato_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1) AS valuta_id,
  (SELECT ef.id FROM anagrafiche.emittenti_fiscali ef WHERE ef.attivo IS TRUE
    ORDER BY ef.id LIMIT 1) AS emittente_fiscale_id,
  (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1) AS iva_id,
  (SELECT id FROM config.nature_vendita WHERE codice_interno = 'MERCE') AS natura_merce_id,
  (SELECT id FROM config.nature_vendita WHERE codice_interno = 'SERVIZIO_UNA_TANTUM') AS natura_serv_id;

-- Classifica: art_merce -> MERCE (ORDINE), art_serv -> SERVIZIO_UNA_TANTUM (COMMESSA).
UPDATE catalogo.articoli SET natura_vendita_id = (SELECT natura_merce_id FROM tmp_refs)
 WHERE id = (SELECT art_merce_id FROM tmp_refs);
UPDATE catalogo.articoli SET natura_vendita_id = (SELECT natura_serv_id FROM tmp_refs)
 WHERE id = (SELECT art_serv_id FROM tmp_refs);

-- Preventivo MISTO ACCETTATO: riga servizio + riga merce + riga natura NULL.
CREATE TEMP TABLE tmp_prev AS
WITH ins AS (
  INSERT INTO vendite.preventivi (
    numero, rev, billing_account_id, istanza_utility_id, utility_id,
    validita_dal, validita_al, valuta_id, stato_doc_preventivo_id, data,
    fatturazione_immediata, storicizza, meta, emittente_fiscale_id)
  SELECT 'PGTAP-NATAWARE', 0, r.billing_account_id, r.istanza_utility_id, r.utility_id,
         DATE '2080-01-01', DATE '2080-12-31', r.valuta_id, r.stato_accettato_id,
         DATE '2080-01-01', false, false,
         jsonb_build_object('test_scope','pgtap_list_natura_aware'), r.emittente_fiscale_id
    FROM tmp_refs r
  RETURNING id)
SELECT * FROM ins;

-- riga servizio (natura COMMESSA)
CREATE TEMP TABLE tmp_riga_serv AS
WITH ins AS (
  INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, qta_operativa, prezzo_unitario, iva_id, attivo)
  SELECT p.id, r.art_serv_id, 2.000000, 30.000000, r.iva_id, true
    FROM tmp_prev p, tmp_refs r
  RETURNING id)
SELECT * FROM ins;

-- riga merce (natura ORDINE)
CREATE TEMP TABLE tmp_riga_merce AS
WITH ins AS (
  INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, qta_operativa, prezzo_unitario, iva_id, attivo)
  SELECT p.id, r.art_merce_id, 2.000000, 30.000000, r.iva_id, true
    FROM tmp_prev p, tmp_refs r
  RETURNING id)
SELECT * FROM ins;

-- riga "legacy": parte servizio, poi forziamo natura NULL (il trigger di
-- derivazione fira solo su INSERT/cambio articolo_id, non su UPDATE della natura).
CREATE TEMP TABLE tmp_riga_null AS
WITH ins AS (
  INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, qta_operativa, prezzo_unitario, iva_id, attivo)
  SELECT p.id, r.art_serv_id, 1.000000, 15.000000, r.iva_id, true
    FROM tmp_prev p, tmp_refs r
  RETURNING id)
SELECT * FROM ins;
UPDATE vendite.preventivi_righe SET natura_vendita_id = NULL
 WHERE id = (SELECT id FROM tmp_riga_null);

-- Preventivo di SOLE merci (per test 4).
CREATE TEMP TABLE tmp_prev_merce AS
WITH ins AS (
  INSERT INTO vendite.preventivi (
    numero, rev, billing_account_id, istanza_utility_id, utility_id,
    validita_dal, validita_al, valuta_id, stato_doc_preventivo_id, data,
    fatturazione_immediata, storicizza, meta, emittente_fiscale_id)
  SELECT 'PGTAP-NATAWARE-MERCE', 0, r.billing_account_id, r.istanza_utility_id, r.utility_id,
         DATE '2080-01-01', DATE '2080-12-31', r.valuta_id, r.stato_accettato_id,
         DATE '2080-01-01', false, false,
         jsonb_build_object('test_scope','pgtap_list_natura_aware_merce'), r.emittente_fiscale_id
    FROM tmp_refs r
  RETURNING id)
SELECT * FROM ins;

INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, qta_operativa, prezzo_unitario, iva_id, attivo)
SELECT p.id, r.art_merce_id, 2.000000, 30.000000, r.iva_id, true
  FROM tmp_prev_merce p, tmp_refs r;

-- ============================================================
-- 1) riga SERVIZIO_UNA_TANTUM inclusa
-- ============================================================
SELECT ok(
  EXISTS(SELECT 1 FROM vendite.fn_list_preventivi_da_pushare(NULL, NULL, NULL, (SELECT id FROM tmp_prev)) f
          WHERE f.riga_id = (SELECT id FROM tmp_riga_serv)),
  '1) preventivo misto -> riga SERVIZIO_UNA_TANTUM inclusa'
);

-- ============================================================
-- 2) riga MERCE esclusa
-- ============================================================
SELECT ok(
  NOT EXISTS(SELECT 1 FROM vendite.fn_list_preventivi_da_pushare(NULL, NULL, NULL, (SELECT id FROM tmp_prev)) f
              WHERE f.riga_id = (SELECT id FROM tmp_riga_merce)),
  '2) preventivo misto -> riga MERCE esclusa (va su ordine)'
);

-- ============================================================
-- 3) riga natura NULL (pregresso) inclusa
-- ============================================================
SELECT ok(
  EXISTS(SELECT 1 FROM vendite.fn_list_preventivi_da_pushare(NULL, NULL, NULL, (SELECT id FROM tmp_prev)) f
          WHERE f.riga_id = (SELECT id FROM tmp_riga_null)),
  '3) riga natura NULL -> inclusa (pregresso = COMMESSA)'
);

-- ============================================================
-- 4) preventivo di sole merci -> lista vuota
-- ============================================================
SELECT is(
  (SELECT count(*) FROM vendite.fn_list_preventivi_da_pushare(NULL, NULL, NULL, (SELECT id FROM tmp_prev_merce))),
  0::bigint,
  '4) preventivo di sole merci -> lista push commessa vuota'
);

SELECT * FROM finish();
ROLLBACK;
