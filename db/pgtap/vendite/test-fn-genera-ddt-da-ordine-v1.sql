-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: vendite.fn_genera_ddt_da_ordine (evasione ordine -> DDT)
--       + macchina a stati DDT + numero a EMESSO + sync stato ordine
-- Brief: brief-db-ddt-vendita-evasione-e-stati §10
-- ------------------------------------------------------------
-- Indice test (1..24):
--  1) fn_genera_ddt_da_ordine presente
--  2) riferimenti minimi disponibili
--  3) genera DDT: ritorna ddt_id non-null
--  4) DDT creato in stato DRAFT
--  5) DDT sorgente = ORDINE_VENDITA (C1, non DDT_VENDITA)
--  6) DDT sorgente_uid = ordini.uid
--  7) billing_account ereditato dall'ordine (trgfn_ddt_normalize)
--  8) numero NULL in DRAFT (C6)
--  9) ddt_righe: 1 riga, prezzo_unitario copiato (A-2)
-- 10) ddt_righe: sconto_percentuale + iva_id copiati (C8)
-- 11) ddt_righe: quantita = qta evasa (10)
-- 12) fulfillment creato con qta_evasa=10 e pair (ordine_riga, ddt_riga)
-- 13) sync stato ordine: full evaso -> EVASO (C5)
-- 14) emissione DRAFT->EMESSO consentita (no componenti pending)
-- 15) numero assegnato a EMESSO (C6)
-- 16) numero immutabile dopo assegnazione (protect bespoke)
-- 17) transizione fuori matrice EMESSO->CONSEGNATO -> errore
-- 18) ri-evasione ordine EVASO -> E_DDT_ORDINE_STATO_NON_EVADIBILE
-- 19) evasione parziale: ordine -> PARZIALMENTE_EVASO (C5)
-- 20) fulfillment parziale qta_evasa=4 (residuo 6)
-- 21) over-shipping -> E_QTA_SUPERA_RESIDUO (guard, C2)
-- 22) multi-DDT: 2a evasione chiude l'ordine (EVASO) e somma a 10 (A-1)
-- 23) ordine inesistente -> E_DDT_ORDINE_NOT_FOUND
-- 24) ordine DRAFT -> E_DDT_ORDINE_STATO_NON_EVADIBILE
-- ------------------------------------------------------------

BEGIN;
SELECT plan(24);

-- ============================================================
-- 1) Funzione presente
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1 FROM pg_proc p
      JOIN pg_namespace n ON n.oid = p.pronamespace
     WHERE n.nspname = 'vendite'
       AND p.proname = 'fn_genera_ddt_da_ordine'
  ),
  '1) fn_genera_ddt_da_ordine presente'
);

-- ============================================================
-- Riferimenti minimi (dati esistenti, no creazione da zero)
-- ============================================================
CREATE TEMP TABLE tmp_refs AS
SELECT
  (SELECT ba.id FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL
      AND ba.istanza_utility_id IS NOT NULL
    ORDER BY ba.id LIMIT 1)                       AS billing_account_id,
  (SELECT sr.id FROM anagrafiche.soggetti_ruoli sr
    ORDER BY sr.id LIMIT 1)                       AS soggetto_ruolo_id,
  (SELECT a.id FROM catalogo.articoli a
    WHERE a.attivo IS TRUE
      AND COALESCE(a.is_composito, FALSE) IS FALSE
    ORDER BY a.data_insert DESC NULLS LAST LIMIT 1) AS articolo_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1) AS valuta_id,
  (SELECT i.id FROM config.iva i
    WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1) AS iva_id,
  (SELECT ef.id FROM anagrafiche.emittenti_fiscali ef
    ORDER BY ef.id LIMIT 1)                       AS emittente_fiscale_id,
  (SELECT s.id FROM config.stati_doc_ordini s
    WHERE s.codice_interno = 'CONFERMATO' AND s.attivo IS TRUE LIMIT 1) AS stato_ord_conf_id,
  (SELECT s.id FROM config.stati_doc_ordini s
    WHERE s.codice_interno = 'DRAFT' AND s.attivo IS TRUE LIMIT 1)      AS stato_ord_draft_id,
  (SELECT s.id FROM config.stati_doc_ddt s
    WHERE s.codice_interno = 'EMESSO' AND s.attivo IS TRUE LIMIT 1)     AS stato_ddt_emesso_id,
  (SELECT s.id FROM config.stati_doc_ddt s
    WHERE s.codice_interno = 'CONSEGNATO' AND s.attivo IS TRUE LIMIT 1) AS stato_ddt_consegnato_id;

SELECT ok(
  (SELECT billing_account_id IS NOT NULL
      AND soggetto_ruolo_id IS NOT NULL
      AND articolo_id IS NOT NULL
      AND iva_id IS NOT NULL
      AND stato_ord_conf_id IS NOT NULL
      AND stato_ddt_emesso_id IS NOT NULL
   FROM tmp_refs),
  '2) riferimenti minimi disponibili'
);

-- ============================================================
-- FIXTURE A: ordine CONFERMATO (full evasion)
-- ============================================================
CREATE TEMP TABLE tmp_ord_a AS
WITH ins AS (
  INSERT INTO vendite.ordini (
    soggetto_ruolo_id, billing_account_id, stato_doc_ordine_id,
    valuta_id, data, fatturazione_trigger, emittente_fiscale_id, storicizza, meta)
  SELECT r.soggetto_ruolo_id, r.billing_account_id, r.stato_ord_conf_id,
         r.valuta_id, DATE '2026-07-01', 'SPEDITO', r.emittente_fiscale_id, false,
         jsonb_build_object('test_scope','pgtap_genera_ddt')
  FROM tmp_refs r
  RETURNING id, uid, billing_account_id)
SELECT * FROM ins;

CREATE TEMP TABLE tmp_ord_a_riga AS
WITH ins AS (
  INSERT INTO vendite.ordini_righe (
    ordine_id, riga_nr, articolo_id, descrizione,
    qta_operativa, quantita, prezzo_unitario, sconto_percentuale, iva_id,
    attivo, storicizza, meta)
  SELECT o.id, 1, r.articolo_id, 'Riga evasione A',
         10.000000, 10.000000, 30.000000, 5.000000, r.iva_id,
         true, false, jsonb_build_object('test_scope','pgtap_genera_ddt')
  FROM tmp_ord_a o, tmp_refs r
  RETURNING id)
SELECT * FROM ins;

-- Chiamata madre: evade tutto il residuo
CREATE TEMP TABLE tmp_ddt_a AS
SELECT vendite.fn_genera_ddt_da_ordine((SELECT id FROM tmp_ord_a)) AS ddt_id;

-- 3) ritorna ddt_id
SELECT ok((SELECT ddt_id IS NOT NULL FROM tmp_ddt_a), '3) genera DDT: ddt_id non-null');

-- 4) DRAFT
SELECT is(
  (SELECT sdd.codice_interno FROM vendite.ddt d
     JOIN config.stati_doc_ddt sdd ON sdd.id = d.stato_doc_ddt_id
    WHERE d.id = (SELECT ddt_id FROM tmp_ddt_a)),
  'DRAFT', '4) DDT creato in DRAFT');

-- 5) sorgente = ORDINE_VENDITA (C1)
SELECT is(
  (SELECT s.codice_interno FROM vendite.ddt d
     JOIN config.sorgenti s ON s.id = d.sorgente_tipo_id
    WHERE d.id = (SELECT ddt_id FROM tmp_ddt_a)),
  'ORDINE_VENDITA', '5) DDT sorgente = ORDINE_VENDITA (C1)');

-- 6) sorgente_uid = ordine uid
SELECT is(
  (SELECT d.sorgente_uid FROM vendite.ddt d WHERE d.id = (SELECT ddt_id FROM tmp_ddt_a)),
  (SELECT uid FROM tmp_ord_a),
  '6) DDT sorgente_uid = ordini.uid');

-- 7) billing ereditato (normalize)
SELECT is(
  (SELECT d.billing_account_id FROM vendite.ddt d WHERE d.id = (SELECT ddt_id FROM tmp_ddt_a)),
  (SELECT billing_account_id FROM tmp_ord_a),
  '7) billing_account ereditato dall''ordine (normalize)');

-- 8) numero NULL in DRAFT (C6)
SELECT ok(
  (SELECT d.numero IS NULL FROM vendite.ddt d WHERE d.id = (SELECT ddt_id FROM tmp_ddt_a)),
  '8) numero NULL in DRAFT (C6)');

-- 9) 1 riga + prezzo copiato (A-2)
SELECT ok(
  (SELECT count(*) = 1 FROM vendite.ddt_righe dr WHERE dr.ddt_id = (SELECT ddt_id FROM tmp_ddt_a))
  AND (SELECT dr.prezzo_unitario = 30.000000 FROM vendite.ddt_righe dr
        WHERE dr.ddt_id = (SELECT ddt_id FROM tmp_ddt_a) LIMIT 1),
  '9) ddt_righe: 1 riga con prezzo_unitario copiato (A-2)');

-- 10) sconto + iva copiati (C8)
SELECT ok(
  (SELECT dr.sconto_percentuale = 5.000000 AND dr.iva_id = (SELECT iva_id FROM tmp_refs)
     FROM vendite.ddt_righe dr WHERE dr.ddt_id = (SELECT ddt_id FROM tmp_ddt_a) LIMIT 1),
  '10) ddt_righe: sconto_percentuale + iva_id copiati (C8)');

-- 11) quantita = 10
SELECT is(
  (SELECT dr.quantita FROM vendite.ddt_righe dr WHERE dr.ddt_id = (SELECT ddt_id FROM tmp_ddt_a) LIMIT 1),
  10.000000::numeric, '11) ddt_righe: quantita = qta evasa (10)');

-- 12) fulfillment qta_evasa=10 + pair
SELECT ok(
  (SELECT f.qta_evasa = 10.000000
     FROM vendite.ordini_righe_fulfillment f
     JOIN vendite.ddt_righe dr ON dr.id = f.ddt_riga_id
    WHERE dr.ddt_id = (SELECT ddt_id FROM tmp_ddt_a)
      AND f.ordine_riga_id = (SELECT id FROM tmp_ord_a_riga)),
  '12) fulfillment con qta_evasa=10 e pair (ordine_riga, ddt_riga)');

-- 13) ordine A -> EVASO (C5)
SELECT is(
  (SELECT sdo.codice_interno FROM vendite.ordini o
     JOIN config.stati_doc_ordini sdo ON sdo.id = o.stato_doc_ordine_id
    WHERE o.id = (SELECT id FROM tmp_ord_a)),
  'EVASO', '13) sync stato ordine: full evaso -> EVASO (C5)');

-- 14) emissione DRAFT->EMESSO consentita
-- Setup guard indirizzi obbligatori (DDT): CON obbligatorio all'emissione
-- (trg_ddt_a10_guard_indirizzi_obbligatori_upd).
INSERT INTO vendite.ddt_indirizzi (ddt_id, tipo_indirizzo_id, snapshot)
SELECT (SELECT ddt_id FROM tmp_ddt_a),
       (SELECT id FROM config.tipi_indirizzi WHERE codice_interno = 'CON'),
       '{"display":"CON test"}'::jsonb
ON CONFLICT DO NOTHING;

SELECT lives_ok(
  format($q$UPDATE vendite.ddt SET stato_doc_ddt_id =
             (SELECT stato_ddt_emesso_id FROM tmp_refs) WHERE id = %s$q$,
         (SELECT ddt_id FROM tmp_ddt_a)),
  '14) emissione DRAFT->EMESSO consentita (no componenti pending)');

-- 15) numero assegnato a EMESSO (C6)
SELECT ok(
  (SELECT d.numero IS NOT NULL AND btrim(d.numero) <> ''
     FROM vendite.ddt d WHERE d.id = (SELECT ddt_id FROM tmp_ddt_a)),
  '15) numero assegnato a EMESSO (C6)');

-- 16) numero immutabile dopo assegnazione
SELECT throws_ok(
  format($q$UPDATE vendite.ddt SET numero = 'HACK-999' WHERE id = %s$q$,
         (SELECT ddt_id FROM tmp_ddt_a)),
  'P0001', NULL,
  '16) numero immutabile dopo assegnazione (protect bespoke)');

-- 17) transizione fuori matrice EMESSO->CONSEGNATO
SELECT throws_ok(
  format($q$UPDATE vendite.ddt SET stato_doc_ddt_id =
             (SELECT stato_ddt_consegnato_id FROM tmp_refs) WHERE id = %s$q$,
         (SELECT ddt_id FROM tmp_ddt_a)),
  'P0001', NULL,
  '17) transizione fuori matrice EMESSO->CONSEGNATO -> errore');

-- 18) ri-evasione ordine EVASO -> stato non evadibile
SELECT throws_ok(
  format($q$SELECT vendite.fn_genera_ddt_da_ordine(%s)$q$, (SELECT id FROM tmp_ord_a)),
  'P0001', NULL,
  '18) ri-evasione ordine EVASO -> E_DDT_ORDINE_STATO_NON_EVADIBILE');

-- ============================================================
-- FIXTURE B: ordine CONFERMATO (evasione parziale + multi-DDT)
-- ============================================================
CREATE TEMP TABLE tmp_ord_b AS
WITH ins AS (
  INSERT INTO vendite.ordini (
    soggetto_ruolo_id, billing_account_id, stato_doc_ordine_id,
    valuta_id, data, fatturazione_trigger, emittente_fiscale_id, storicizza, meta)
  SELECT r.soggetto_ruolo_id, r.billing_account_id, r.stato_ord_conf_id,
         r.valuta_id, DATE '2026-07-02', 'SPEDITO', r.emittente_fiscale_id, false,
         jsonb_build_object('test_scope','pgtap_genera_ddt')
  FROM tmp_refs r
  RETURNING id, uid)
SELECT * FROM ins;

CREATE TEMP TABLE tmp_ord_b_riga AS
WITH ins AS (
  INSERT INTO vendite.ordini_righe (
    ordine_id, riga_nr, articolo_id, descrizione,
    qta_operativa, quantita, prezzo_unitario, iva_id,
    attivo, storicizza, meta)
  SELECT o.id, 1, r.articolo_id, 'Riga evasione B',
         10.000000, 10.000000, 20.000000, r.iva_id,
         true, false, jsonb_build_object('test_scope','pgtap_genera_ddt')
  FROM tmp_ord_b o, tmp_refs r
  RETURNING id)
SELECT * FROM ins;

-- Evasione parziale: 4 su 10
CREATE TEMP TABLE tmp_ddt_b1 AS
SELECT vendite.fn_genera_ddt_da_ordine(
         (SELECT id FROM tmp_ord_b),
         jsonb_build_array(jsonb_build_object(
             'ordine_riga_id', (SELECT id FROM tmp_ord_b_riga),
             'qta_da_evadere', 4))
       ) AS ddt_id;

-- 19) ordine B -> PARZIALMENTE_EVASO
SELECT is(
  (SELECT sdo.codice_interno FROM vendite.ordini o
     JOIN config.stati_doc_ordini sdo ON sdo.id = o.stato_doc_ordine_id
    WHERE o.id = (SELECT id FROM tmp_ord_b)),
  'PARZIALMENTE_EVASO', '19) evasione parziale -> ordine PARZIALMENTE_EVASO (C5)');

-- 20) fulfillment parziale qta=4
SELECT is(
  (SELECT SUM(f.qta_evasa) FROM vendite.ordini_righe_fulfillment f
    WHERE f.ordine_riga_id = (SELECT id FROM tmp_ord_b_riga)),
  4.000000::numeric, '20) fulfillment parziale qta_evasa=4 (residuo 6)');

-- 21) over-shipping -> E_QTA_SUPERA_RESIDUO
SELECT throws_ok(
  format($q$SELECT vendite.fn_genera_ddt_da_ordine(%s,
             jsonb_build_array(jsonb_build_object('ordine_riga_id', %s, 'qta_da_evadere', 100)))$q$,
         (SELECT id FROM tmp_ord_b), (SELECT id FROM tmp_ord_b_riga)),
  'P0001', NULL,
  '21) over-shipping -> E_QTA_SUPERA_RESIDUO (guard, C2)');

-- 22) multi-DDT: 2a evasione (residuo 6) chiude l'ordine
CREATE TEMP TABLE tmp_ddt_b2 AS
SELECT vendite.fn_genera_ddt_da_ordine((SELECT id FROM tmp_ord_b)) AS ddt_id;

SELECT ok(
  (SELECT sdo.codice_interno FROM vendite.ordini o
     JOIN config.stati_doc_ordini sdo ON sdo.id = o.stato_doc_ordine_id
    WHERE o.id = (SELECT id FROM tmp_ord_b)) = 'EVASO'
  AND (SELECT SUM(f.qta_evasa) FROM vendite.ordini_righe_fulfillment f
        WHERE f.ordine_riga_id = (SELECT id FROM tmp_ord_b_riga)) = 10.000000
  AND (SELECT (SELECT ddt_id FROM tmp_ddt_b1) <> (SELECT ddt_id FROM tmp_ddt_b2)),
  '22) multi-DDT: 2a evasione -> ordine EVASO e somma qta=10 (A-1)');

-- ============================================================
-- 23) ordine inesistente
-- ============================================================
SELECT throws_ok(
  $q$SELECT vendite.fn_genera_ddt_da_ordine(999999999)$q$,
  'P0001', NULL,
  '23) ordine inesistente -> E_DDT_ORDINE_NOT_FOUND');

-- ============================================================
-- 24) ordine DRAFT (non evadibile)
-- ============================================================
CREATE TEMP TABLE tmp_ord_draft AS
WITH ins AS (
  INSERT INTO vendite.ordini (
    soggetto_ruolo_id, billing_account_id, stato_doc_ordine_id,
    valuta_id, data, emittente_fiscale_id, storicizza, meta)
  SELECT r.soggetto_ruolo_id, r.billing_account_id, r.stato_ord_draft_id,
         r.valuta_id, DATE '2026-07-03', r.emittente_fiscale_id, false,
         jsonb_build_object('test_scope','pgtap_genera_ddt')
  FROM tmp_refs r
  RETURNING id)
SELECT * FROM ins;

SELECT throws_ok(
  format($q$SELECT vendite.fn_genera_ddt_da_ordine(%s)$q$, (SELECT id FROM tmp_ord_draft)),
  'P0001', NULL,
  '24) ordine DRAFT -> E_DDT_ORDINE_STATO_NON_EVADIBILE');

SELECT * FROM finish();
ROLLBACK;
