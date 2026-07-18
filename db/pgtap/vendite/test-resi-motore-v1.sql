-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: motore resi vendita (vendite.resi / resi_righe / ponte)
--       fn_conferma_reso, fn_genera_ddt_riconsegna, fn_annulla_reso,
--       residuo reso-aware, flip DDT, read-side.
-- Brief: brief-db-resi-vendita §6
-- ------------------------------------------------------------
-- Indice test (27 asserzioni: 1..26 + sub 8b/23a, meno la 21 rimossa):
--  1) oggetti motore resi presenti
--  2) riferimenti minimi disponibili
--  3) reso DRAFT: emittente ereditato dal DDT (normalize)
--  4) reso: billing ereditato dal DDT
--  5) numero NULL in DRAFT
--  6) resi_righe: quantita derivata da qta_operativa (3)
--  7) guard over-return: Sigma qta_resa > consegnato -> E_RESO_QTA_SUPERA_CONSEGNATO
--  8) fn_conferma_reso -> stato CONFERMATO
--  9) numero assegnato alla CONFERMA
-- 10) numero immutabile dopo assegnazione
-- 11) residuo riaperto: fn_ordine_ha_residuo_evasione = true (reso-aware)
-- 12) proiezione stato ordine -> PARZIALMENTE_EVASO
-- 13) coda da_riconsegnare: qta_residua=3, stato DA_RICONSEGNARE
-- 14) fn_genera_ddt_riconsegna parziale (qta 2) -> nuovo ddt non-null
-- 15) ponte: copertura=2, stato_riconsegna=PARZIALE
-- 16) fn_genera_ddt_riconsegna resto (NULL) -> copertura=3
-- 17) stato_riconsegna=COMPLETATA, sparita dalla coda
-- 18) ordine torna EVASO (residuo chiuso dalla ri-spedizione)
-- 19) annullo bloccato se gia' ri-spedito -> E_RESO_ANNULLO_CON_RICONSEGNE
-- 20) flip DDT: reso a credito TOTALE confermato -> DDT CONSEGNATO->RESO
-- 21) RIMOSSA (step 4): la coda accrediti si popola dal conto, non dal tipo reso
--     -> coperta da test-vw-resi-da-accreditare-contatore-v1
-- 22) fn_available_actions_reso: reso CONFERMATO espone azione 'annulla'
-- 23) annullo reso a credito (non ri-spedito) -> ANNULLATO
-- 24) guard: reso da DDT non CONSEGNATO -> E_RESO_DDT_NON_CONSEGNATO
-- 25) flip: bozza 6 + confermato 4 su DDT da 10 -> DDT resta CONSEGNATO
--     (le BOZZE non contano: step 2b, brief-db-fatturazione-ddt-resi §3b)
-- 26) confermata anche la bozza (6+4=10 confermati) -> DDT flippa a RESO
--     (il flip funziona ancora: e' lo STATO a decidere, non l'esistenza)
-- ------------------------------------------------------------

BEGIN;
SELECT plan(27);

-- Contesto (le madri sono SECURITY INVOKER: il pgTAP gira come owner).
SET LOCAL app.ruolo_applicativo = 'OPERATORE';
SET LOCAL app.current_user_id = '1';

-- ============================================================
-- 1) Oggetti motore resi presenti
-- ============================================================
SELECT ok(
  (SELECT count(*) = 4 FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE (n.nspname = 'vendite' AND p.proname IN
             ('fn_conferma_reso','fn_genera_ddt_riconsegna','fn_annulla_reso'))
       OR (n.nspname = 'script' AND p.proname = 'fn_available_actions_reso'))
  AND to_regclass('vendite.resi') IS NOT NULL
  AND to_regclass('vendite.resi_righe') IS NOT NULL
  AND to_regclass('vendite.resi_righe_riconsegne') IS NOT NULL
  AND to_regclass('vendite.vw_resi_da_riconsegnare') IS NOT NULL
  AND to_regclass('vendite.vw_resi_da_accreditare') IS NOT NULL,
  '1) oggetti motore resi presenti');

-- ============================================================
-- Riferimenti minimi (dati esistenti)
-- ============================================================
CREATE TEMP TABLE tmp_refs AS
SELECT
  (SELECT ba.id FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL AND ba.istanza_utility_id IS NOT NULL
    ORDER BY ba.id LIMIT 1)                                              AS billing_account_id,
  (SELECT sr.id FROM anagrafiche.soggetti_ruoli sr ORDER BY sr.id LIMIT 1) AS soggetto_ruolo_id,
  (SELECT a.id FROM catalogo.articoli a
    WHERE a.attivo IS TRUE AND COALESCE(a.is_composito, FALSE) IS FALSE
    ORDER BY a.data_insert DESC NULLS LAST LIMIT 1)                      AS articolo_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1)              AS valuta_id,
  (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1) AS iva_id,
  (SELECT ef.id FROM anagrafiche.emittenti_fiscali ef ORDER BY ef.id LIMIT 1)  AS emittente_fiscale_id,
  (SELECT s.id FROM config.stati_doc_ordini s WHERE s.codice_interno='CONFERMATO' AND s.attivo LIMIT 1) AS stato_ord_conf_id,
  (SELECT s.id FROM config.stati_doc_ddt s WHERE s.codice_interno='EMESSO' AND s.attivo LIMIT 1)     AS stato_ddt_emesso_id,
  (SELECT s.id FROM config.stati_doc_ddt s WHERE s.codice_interno='SPEDITO' AND s.attivo LIMIT 1)    AS stato_ddt_spedito_id,
  (SELECT s.id FROM config.stati_doc_ddt s WHERE s.codice_interno='CONSEGNATO' AND s.attivo LIMIT 1) AS stato_ddt_consegnato_id,
  (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno='DDT_VENDITA' AND s.attivo LIMIT 1)     AS sorgente_ddt_id,
  (SELECT s.id FROM config.stati_doc_reso s WHERE s.codice_interno='DRAFT' AND s.attivo LIMIT 1)     AS stato_reso_draft_id,
  (SELECT s.id FROM config.stati_doc_reso s WHERE s.codice_interno='ANNULLATO' AND s.attivo LIMIT 1) AS stato_reso_ann_id,
  (SELECT t.id FROM config.tipi_reso t WHERE t.codice_interno='RESO_PER_RICONSEGNA' AND t.attivo LIMIT 1) AS tipo_riconsegna_id,
  (SELECT t.id FROM config.tipi_reso t WHERE t.codice_interno='RESO_A_CREDITO' AND t.attivo LIMIT 1)      AS tipo_credito_id,
  (SELECT id FROM config.tipi_indirizzi WHERE codice_interno='CON')     AS tipo_ind_con_id,
  -- Dal 2026-07-18 (step 5b / DL-28) la causale di trasporto e' obbligatoria
  -- all'emissione del DDT: VENDITA e' l'unica causale fatturabile.
  (SELECT c.id FROM config.causali_trasporto c WHERE c.codice='VENDITA' LIMIT 1) AS causale_vendita_id;

SELECT ok(
  (SELECT billing_account_id IS NOT NULL AND articolo_id IS NOT NULL
      AND sorgente_ddt_id IS NOT NULL AND stato_reso_draft_id IS NOT NULL
      AND tipo_riconsegna_id IS NOT NULL AND tipo_credito_id IS NOT NULL
      AND stato_ddt_consegnato_id IS NOT NULL FROM tmp_refs),
  '2) riferimenti minimi disponibili');

-- ============================================================
-- FIXTURE A: ordine (qta 10) -> DDT -> CONSEGNATO
-- ============================================================
CREATE TEMP TABLE tmp_ord_a AS
WITH ins AS (
  INSERT INTO vendite.ordini (soggetto_ruolo_id, billing_account_id, stato_doc_ordine_id,
    valuta_id, data, fatturazione_trigger, emittente_fiscale_id, storicizza, meta)
  SELECT r.soggetto_ruolo_id, r.billing_account_id, r.stato_ord_conf_id,
         r.valuta_id, DATE '2026-07-10', 'SPEDITO', r.emittente_fiscale_id, false,
         jsonb_build_object('test_scope','pgtap_resi')
  FROM tmp_refs r RETURNING id, uid, billing_account_id, emittente_fiscale_id)
SELECT * FROM ins;

CREATE TEMP TABLE tmp_ord_a_riga AS
WITH ins AS (
  INSERT INTO vendite.ordini_righe (ordine_id, riga_nr, articolo_id, descrizione,
    qta_operativa, quantita, prezzo_unitario, iva_id, attivo, storicizza, meta)
  SELECT o.id, 1, r.articolo_id, 'Riga reso A', 10, 10, 25, r.iva_id, true, false,
         jsonb_build_object('test_scope','pgtap_resi')
  FROM tmp_ord_a o, tmp_refs r RETURNING id)
SELECT * FROM ins;

CREATE TEMP TABLE tmp_ddt_a AS
SELECT vendite.fn_genera_ddt_da_ordine((SELECT id FROM tmp_ord_a)) AS ddt_id;

-- Porta il DDT a CONSEGNATO (DRAFT->EMESSO->SPEDITO->CONSEGNATO).
INSERT INTO vendite.ddt_indirizzi (ddt_id, tipo_indirizzo_id, snapshot)
SELECT (SELECT ddt_id FROM tmp_ddt_a), (SELECT tipo_ind_con_id FROM tmp_refs),
       '{"display":"CON test"}'::jsonb ON CONFLICT DO NOTHING;
-- Causale obbligatoria all'emissione (guard causale_emissione, 2026-07-18).
UPDATE vendite.ddt SET causale_trasporto_id=(SELECT causale_vendita_id FROM tmp_refs) WHERE id=(SELECT ddt_id FROM tmp_ddt_a);
UPDATE vendite.ddt SET stato_doc_ddt_id=(SELECT stato_ddt_emesso_id FROM tmp_refs)    WHERE id=(SELECT ddt_id FROM tmp_ddt_a);
UPDATE vendite.ddt SET stato_doc_ddt_id=(SELECT stato_ddt_spedito_id FROM tmp_refs)   WHERE id=(SELECT ddt_id FROM tmp_ddt_a);
UPDATE vendite.ddt SET stato_doc_ddt_id=(SELECT stato_ddt_consegnato_id FROM tmp_refs) WHERE id=(SELECT ddt_id FROM tmp_ddt_a);

CREATE TEMP TABLE tmp_ddt_a_riga AS
SELECT dr.id, dr.articolo_id, dr.descrizione, dr.uom_operativa_id, dr.factor_to_base
  FROM vendite.ddt_righe dr WHERE dr.ddt_id=(SELECT ddt_id FROM tmp_ddt_a) LIMIT 1;

-- Crea reso DRAFT dal DDT (sorgente DDT_VENDITA, uid del DDT).
CREATE TEMP TABLE tmp_reso_a AS
WITH ins AS (
  INSERT INTO vendite.resi (stato_doc_reso_id, sorgente_tipo_id, sorgente_uid, storicizza, meta)
  SELECT r.stato_reso_draft_id, r.sorgente_ddt_id,
         (SELECT d.uid FROM vendite.ddt d WHERE d.id=(SELECT ddt_id FROM tmp_ddt_a)),
         false, jsonb_build_object('test_scope','pgtap_resi')
  FROM tmp_refs r RETURNING id, emittente_fiscale_id, billing_account_id)
SELECT * FROM ins;

-- 3) emittente ereditato dal DDT
SELECT is(
  (SELECT emittente_fiscale_id FROM tmp_reso_a),
  (SELECT emittente_fiscale_id FROM tmp_ord_a),
  '3) reso: emittente ereditato dal DDT (normalize)');

-- 4) billing ereditato dal DDT
SELECT is(
  (SELECT billing_account_id FROM tmp_reso_a),
  (SELECT billing_account_id FROM tmp_ord_a),
  '4) reso: billing ereditato dal DDT');

-- 5) numero NULL in DRAFT
SELECT ok((SELECT numero IS NULL FROM vendite.resi WHERE id=(SELECT id FROM tmp_reso_a)),
  '5) numero NULL in DRAFT');

-- Riga reso: ri-consegna, qta 3
CREATE TEMP TABLE tmp_reso_a_riga AS
WITH ins AS (
  INSERT INTO vendite.resi_righe (reso_id, riga_nr, ddt_riga_id, ordine_riga_id,
    articolo_id, descrizione, qta_operativa, uom_operativa_id, factor_to_base,
    tipo_reso_id, storicizza)
  SELECT (SELECT id FROM tmp_reso_a), 1, dr.id, (SELECT id FROM tmp_ord_a_riga),
         dr.articolo_id, dr.descrizione, 3, dr.uom_operativa_id, dr.factor_to_base,
         (SELECT tipo_riconsegna_id FROM tmp_refs), false
  FROM tmp_ddt_a_riga dr RETURNING id, quantita)
SELECT * FROM ins;

-- 6) quantita derivata da qta_operativa
SELECT is((SELECT quantita FROM tmp_reso_a_riga), 3.000000::numeric,
  '6) resi_righe: quantita derivata da qta_operativa (3)');

-- 7) over-return: aggiungere 8 (3+8>10) -> throws
SELECT throws_ok(
  format($q$INSERT INTO vendite.resi_righe (reso_id, riga_nr, ddt_riga_id, ordine_riga_id,
             articolo_id, descrizione, qta_operativa, factor_to_base, tipo_reso_id, storicizza)
             SELECT %s, 2, %s, %s, %L, 'over', 8, 1, %s, false$q$,
         (SELECT id FROM tmp_reso_a), (SELECT id FROM tmp_ddt_a_riga),
         (SELECT id FROM tmp_ord_a_riga), (SELECT articolo_id FROM tmp_ddt_a_riga),
         (SELECT tipo_riconsegna_id FROM tmp_refs)),
  'P0001', NULL,
  '7) over-return -> E_RESO_QTA_SUPERA_CONSEGNATO');

-- 8) conferma
SELECT lives_ok(
  format($q$SELECT vendite.fn_conferma_reso(%s)$q$, (SELECT id FROM tmp_reso_a)),
  '8) fn_conferma_reso eseguita');
SELECT is(
  (SELECT sdr.codice_interno FROM vendite.resi r
     JOIN config.stati_doc_reso sdr ON sdr.id=r.stato_doc_reso_id
    WHERE r.id=(SELECT id FROM tmp_reso_a)),
  'CONFERMATO', '8b) reso -> CONFERMATO');

-- 9) numero assegnato
SELECT ok(
  (SELECT numero IS NOT NULL AND btrim(numero) <> '' FROM vendite.resi WHERE id=(SELECT id FROM tmp_reso_a)),
  '9) numero assegnato alla CONFERMA');

-- 10) numero immutabile
SELECT throws_ok(
  format($q$UPDATE vendite.resi SET numero='ZZZ' WHERE id=%s$q$, (SELECT id FROM tmp_reso_a)),
  'P0001', NULL, '10) numero immutabile dopo assegnazione');

-- 11) residuo riaperto (reso-aware)
SELECT ok(
  vendite.fn_ordine_ha_residuo_evasione((SELECT id FROM tmp_ord_a)),
  '11) residuo riaperto: fn_ordine_ha_residuo_evasione = true');

-- 12) ordine -> PARZIALMENTE_EVASO
SELECT is(
  (SELECT sdo.codice_interno FROM vendite.ordini o
     JOIN config.stati_doc_ordini sdo ON sdo.id=o.stato_doc_ordine_id
    WHERE o.id=(SELECT id FROM tmp_ord_a)),
  'PARZIALMENTE_EVASO', '12) proiezione stato ordine -> PARZIALMENTE_EVASO');

-- 13) coda da_riconsegnare
SELECT ok(
  (SELECT qta_residua = 3 AND stato_riconsegna = 'DA_RICONSEGNARE'
     FROM vendite.vw_resi_da_riconsegnare WHERE resi_riga_id=(SELECT id FROM tmp_reso_a_riga)),
  '13) coda da_riconsegnare: qta_residua=3, DA_RICONSEGNARE');

-- 14) ri-spedizione parziale (qta 2)
CREATE TEMP TABLE tmp_ddt_ric1 AS
SELECT vendite.fn_genera_ddt_riconsegna(
         (SELECT id FROM tmp_reso_a),
         jsonb_build_array(jsonb_build_object('resi_riga_id',(SELECT id FROM tmp_reso_a_riga),'qta',2))
       ) AS ddt_id;
SELECT ok((SELECT ddt_id IS NOT NULL FROM tmp_ddt_ric1), '14) ri-spedizione parziale -> nuovo ddt');

-- 15) copertura 2 + PARZIALE
SELECT ok(
  (SELECT COALESCE(SUM(qta),0) = 2 FROM vendite.resi_righe_riconsegne WHERE resi_riga_id=(SELECT id FROM tmp_reso_a_riga))
  AND (SELECT stato_riconsegna='PARZIALE' FROM vendite.vw_resi_da_riconsegnare WHERE resi_riga_id=(SELECT id FROM tmp_reso_a_riga)),
  '15) ponte copertura=2, stato_riconsegna=PARZIALE');

-- 16) ri-spedizione del resto (NULL -> tutta la copertura residua = 1)
CREATE TEMP TABLE tmp_ddt_ric2 AS
SELECT vendite.fn_genera_ddt_riconsegna((SELECT id FROM tmp_reso_a)) AS ddt_id;
SELECT is(
  (SELECT COALESCE(SUM(qta),0) FROM vendite.resi_righe_riconsegne WHERE resi_riga_id=(SELECT id FROM tmp_reso_a_riga)),
  3.000000::numeric, '16) ri-spedizione resto -> copertura=3');

-- 17) COMPLETATA + fuori dalla coda
SELECT ok(
  NOT EXISTS (SELECT 1 FROM vendite.vw_resi_da_riconsegnare WHERE resi_riga_id=(SELECT id FROM tmp_reso_a_riga)),
  '17) copertura completa -> sparita dalla coda da_riconsegnare');

-- 18) ordine torna EVASO
SELECT is(
  (SELECT sdo.codice_interno FROM vendite.ordini o
     JOIN config.stati_doc_ordini sdo ON sdo.id=o.stato_doc_ordine_id
    WHERE o.id=(SELECT id FROM tmp_ord_a)),
  'EVASO', '18) ordine torna EVASO (residuo chiuso)');

-- 19) annullo bloccato se gia' ri-spedito
SELECT throws_ok(
  format($q$SELECT vendite.fn_annulla_reso(%s)$q$, (SELECT id FROM tmp_reso_a)),
  'P0001', NULL, '19) annullo bloccato con riconsegne -> E_RESO_ANNULLO_CON_RICONSEGNE');

-- ============================================================
-- FIXTURE B: reso a credito TOTALE -> flip DDT + coda accrediti
-- ============================================================
CREATE TEMP TABLE tmp_ord_b AS
WITH ins AS (
  INSERT INTO vendite.ordini (soggetto_ruolo_id, billing_account_id, stato_doc_ordine_id,
    valuta_id, data, fatturazione_trigger, emittente_fiscale_id, storicizza, meta)
  SELECT r.soggetto_ruolo_id, r.billing_account_id, r.stato_ord_conf_id,
         r.valuta_id, DATE '2026-07-11', 'SPEDITO', r.emittente_fiscale_id, false,
         jsonb_build_object('test_scope','pgtap_resi')
  FROM tmp_refs r RETURNING id, uid)
SELECT * FROM ins;
INSERT INTO vendite.ordini_righe (ordine_id, riga_nr, articolo_id, descrizione,
  qta_operativa, quantita, prezzo_unitario, iva_id, attivo, storicizza, meta)
SELECT (SELECT id FROM tmp_ord_b), 1, r.articolo_id, 'Riga reso B', 5, 5, 25, r.iva_id, true, false,
       jsonb_build_object('test_scope','pgtap_resi') FROM tmp_refs r;
CREATE TEMP TABLE tmp_ddt_b AS
SELECT vendite.fn_genera_ddt_da_ordine((SELECT id FROM tmp_ord_b)) AS ddt_id;
INSERT INTO vendite.ddt_indirizzi (ddt_id, tipo_indirizzo_id, snapshot)
SELECT (SELECT ddt_id FROM tmp_ddt_b), (SELECT tipo_ind_con_id FROM tmp_refs), '{"display":"CON"}'::jsonb ON CONFLICT DO NOTHING;
-- Causale obbligatoria all'emissione (guard causale_emissione, 2026-07-18).
UPDATE vendite.ddt SET causale_trasporto_id=(SELECT causale_vendita_id FROM tmp_refs) WHERE id=(SELECT ddt_id FROM tmp_ddt_b);
UPDATE vendite.ddt SET stato_doc_ddt_id=(SELECT stato_ddt_emesso_id FROM tmp_refs)     WHERE id=(SELECT ddt_id FROM tmp_ddt_b);
UPDATE vendite.ddt SET stato_doc_ddt_id=(SELECT stato_ddt_spedito_id FROM tmp_refs)    WHERE id=(SELECT ddt_id FROM tmp_ddt_b);
UPDATE vendite.ddt SET stato_doc_ddt_id=(SELECT stato_ddt_consegnato_id FROM tmp_refs) WHERE id=(SELECT ddt_id FROM tmp_ddt_b);

CREATE TEMP TABLE tmp_reso_b AS
WITH ins AS (
  INSERT INTO vendite.resi (stato_doc_reso_id, sorgente_tipo_id, sorgente_uid, storicizza, meta)
  SELECT r.stato_reso_draft_id, r.sorgente_ddt_id,
         (SELECT d.uid FROM vendite.ddt d WHERE d.id=(SELECT ddt_id FROM tmp_ddt_b)),
         false, jsonb_build_object('test_scope','pgtap_resi')
  FROM tmp_refs r RETURNING id)
SELECT * FROM ins;
-- Riga credito, qta piena (5) -> reso totale
CREATE TEMP TABLE tmp_reso_b_riga AS
WITH ins AS (
  INSERT INTO vendite.resi_righe (reso_id, riga_nr, ddt_riga_id, ordine_riga_id,
    articolo_id, descrizione, qta_operativa, uom_operativa_id, factor_to_base, tipo_reso_id, storicizza)
  SELECT (SELECT id FROM tmp_reso_b), 1, dr.id,
         (SELECT f.ordine_riga_id FROM vendite.ordini_righe_fulfillment f WHERE f.ddt_riga_id=dr.id LIMIT 1),
         dr.articolo_id, dr.descrizione, 5, dr.uom_operativa_id, dr.factor_to_base,
         (SELECT tipo_credito_id FROM tmp_refs), false
  FROM vendite.ddt_righe dr WHERE dr.ddt_id=(SELECT ddt_id FROM tmp_ddt_b) LIMIT 1
  RETURNING id)
SELECT * FROM ins;
SELECT vendite.fn_conferma_reso((SELECT id FROM tmp_reso_b));

-- 20) flip DDT -> RESO
SELECT is(
  (SELECT sdd.codice_interno FROM vendite.ddt d
     JOIN config.stati_doc_ddt sdd ON sdd.id=d.stato_doc_ddt_id
    WHERE d.id=(SELECT ddt_id FROM tmp_ddt_b)),
  'RESO', '20) reso a credito totale -> DDT CONSEGNATO->RESO (flip automatico)');

-- 21) RIMOSSA (2026-07-18, step 4): verificava "riga a credito confermata =>
--     presente in coda", cioe' la popolazione PER TIPO DI RESO. Dal changeset
--     20260718-01 vw_resi_da_accreditare si popola dal CONTO (differenza
--     negativa del contatore): la fixture B rende 5 su 5 senza aver mai
--     fatturato nulla, quindi non c'e' niente da accreditare e la vista
--     giustamente la esclude. La coda ha ora il suo test dedicato,
--     test-vw-resi-da-accreditare-contatore-v1 (plan(8)), che copre anche
--     questo caso (P1). Qui resta il motore dei resi, che e' l'oggetto del file.

-- 22) available_actions su reso CONFERMATO espone 'annulla'
SELECT ok(
  (SELECT (script.fn_available_actions_reso((SELECT id FROM tmp_reso_b))->'available_actions')
          @> '[{"key":"annulla"}]'::jsonb),
  '22) fn_available_actions_reso: reso CONFERMATO espone azione annulla');

-- ============================================================
-- 23) annullo reso a credito (non ri-spedito) -> ANNULLATO
-- ============================================================
SELECT lives_ok(
  format($q$SELECT vendite.fn_annulla_reso(%s)$q$, (SELECT id FROM tmp_reso_b)),
  '23a) fn_annulla_reso credito eseguita');
SELECT is(
  (SELECT sdr.codice_interno FROM vendite.resi r
     JOIN config.stati_doc_reso sdr ON sdr.id=r.stato_doc_reso_id
    WHERE r.id=(SELECT id FROM tmp_reso_b)),
  'ANNULLATO', '23) annullo reso a credito -> ANNULLATO');

-- ============================================================
-- 24) guard: reso da DDT NON CONSEGNATO -> throws
-- ============================================================
CREATE TEMP TABLE tmp_ord_c AS
WITH ins AS (
  INSERT INTO vendite.ordini (soggetto_ruolo_id, billing_account_id, stato_doc_ordine_id,
    valuta_id, data, fatturazione_trigger, emittente_fiscale_id, storicizza, meta)
  SELECT r.soggetto_ruolo_id, r.billing_account_id, r.stato_ord_conf_id, r.valuta_id,
         DATE '2026-07-12', 'SPEDITO', r.emittente_fiscale_id, false,
         jsonb_build_object('test_scope','pgtap_resi')
  FROM tmp_refs r RETURNING id)
SELECT * FROM ins;
INSERT INTO vendite.ordini_righe (ordine_id, riga_nr, articolo_id, descrizione,
  qta_operativa, quantita, prezzo_unitario, iva_id, attivo, storicizza, meta)
SELECT (SELECT id FROM tmp_ord_c), 1, r.articolo_id, 'Riga C', 5, 5, 25, r.iva_id, true, false,
       jsonb_build_object('test_scope','pgtap_resi') FROM tmp_refs r;
-- DDT resta in DRAFT (non consegnato).
CREATE TEMP TABLE tmp_ddt_c AS
SELECT vendite.fn_genera_ddt_da_ordine((SELECT id FROM tmp_ord_c)) AS ddt_id;

SELECT throws_ok(
  format($q$INSERT INTO vendite.resi (stato_doc_reso_id, sorgente_tipo_id, sorgente_uid, storicizza, meta)
             SELECT %s, %s, (SELECT uid FROM vendite.ddt WHERE id=%s), false, '{}'::jsonb$q$,
         (SELECT stato_reso_draft_id FROM tmp_refs), (SELECT sorgente_ddt_id FROM tmp_refs),
         (SELECT ddt_id FROM tmp_ddt_c)),
  'P0001', NULL, '24) reso da DDT non CONSEGNATO -> E_RESO_DDT_NON_CONSEGNATO');

-- ============================================================
-- FIXTURE D: il caso-bozza del flip (step 2b — il test che dimostra il fix)
--   DDT da 10 pz CONSEGNATO, due resi a credito sulla stessa riga:
--     - reso D1: 6 pz, lasciato in BOZZA (il reso "di un altro operatore")
--     - reso D2: 4 pz, CONFERMATO
--   Somma dei NON-ANNULLATI = 10 = qta del DDT -> col vecchio calcolo
--   (`<> 'ANNULLATO'`) il DDT veniva dichiarato RESO, ma il cliente tiene 6 pz
--   e quei 6 pz non si sarebbero fatturati mai (DDT in RESO = non piu'
--   eleggibile al push), senza nessuna segnalazione.
--   Nota: il guard over-return conta anch'esso i non-annullati, quindi il reso
--   D2 da 4 passa per un pelo (residuo 10-6=4, il guard blocca solo se >).
-- ============================================================
CREATE TEMP TABLE tmp_ord_d AS
WITH ins AS (
  INSERT INTO vendite.ordini (soggetto_ruolo_id, billing_account_id, stato_doc_ordine_id,
    valuta_id, data, fatturazione_trigger, emittente_fiscale_id, storicizza, meta)
  SELECT r.soggetto_ruolo_id, r.billing_account_id, r.stato_ord_conf_id,
         r.valuta_id, DATE '2026-07-13', 'SPEDITO', r.emittente_fiscale_id, false,
         jsonb_build_object('test_scope','pgtap_resi')
  FROM tmp_refs r RETURNING id)
SELECT * FROM ins;
INSERT INTO vendite.ordini_righe (ordine_id, riga_nr, articolo_id, descrizione,
  qta_operativa, quantita, prezzo_unitario, iva_id, attivo, storicizza, meta)
SELECT (SELECT id FROM tmp_ord_d), 1, r.articolo_id, 'Riga reso D', 10, 10, 25, r.iva_id, true, false,
       jsonb_build_object('test_scope','pgtap_resi') FROM tmp_refs r;

CREATE TEMP TABLE tmp_ddt_d AS
SELECT vendite.fn_genera_ddt_da_ordine((SELECT id FROM tmp_ord_d)) AS ddt_id;
INSERT INTO vendite.ddt_indirizzi (ddt_id, tipo_indirizzo_id, snapshot)
SELECT (SELECT ddt_id FROM tmp_ddt_d), (SELECT tipo_ind_con_id FROM tmp_refs),
       '{"display":"CON"}'::jsonb ON CONFLICT DO NOTHING;
-- Causale obbligatoria all'emissione (guard causale_emissione, 2026-07-18).
UPDATE vendite.ddt SET causale_trasporto_id=(SELECT causale_vendita_id FROM tmp_refs) WHERE id=(SELECT ddt_id FROM tmp_ddt_d);
UPDATE vendite.ddt SET stato_doc_ddt_id=(SELECT stato_ddt_emesso_id FROM tmp_refs)     WHERE id=(SELECT ddt_id FROM tmp_ddt_d);
UPDATE vendite.ddt SET stato_doc_ddt_id=(SELECT stato_ddt_spedito_id FROM tmp_refs)    WHERE id=(SELECT ddt_id FROM tmp_ddt_d);
UPDATE vendite.ddt SET stato_doc_ddt_id=(SELECT stato_ddt_consegnato_id FROM tmp_refs) WHERE id=(SELECT ddt_id FROM tmp_ddt_d);

CREATE TEMP TABLE tmp_ddt_d_riga AS
SELECT dr.id, dr.articolo_id, dr.descrizione, dr.uom_operativa_id, dr.factor_to_base
  FROM vendite.ddt_righe dr WHERE dr.ddt_id=(SELECT ddt_id FROM tmp_ddt_d) LIMIT 1;

-- Reso D1: 6 pz, resta in BOZZA (mai confermato).
CREATE TEMP TABLE tmp_reso_d1 AS
WITH ins AS (
  INSERT INTO vendite.resi (stato_doc_reso_id, sorgente_tipo_id, sorgente_uid, storicizza, meta)
  SELECT r.stato_reso_draft_id, r.sorgente_ddt_id,
         (SELECT d.uid FROM vendite.ddt d WHERE d.id=(SELECT ddt_id FROM tmp_ddt_d)),
         false, jsonb_build_object('test_scope','pgtap_resi')
  FROM tmp_refs r RETURNING id)
SELECT * FROM ins;
INSERT INTO vendite.resi_righe (reso_id, riga_nr, ddt_riga_id, ordine_riga_id,
  articolo_id, descrizione, qta_operativa, uom_operativa_id, factor_to_base, tipo_reso_id, storicizza)
SELECT (SELECT id FROM tmp_reso_d1), 1, dr.id,
       (SELECT f.ordine_riga_id FROM vendite.ordini_righe_fulfillment f WHERE f.ddt_riga_id=dr.id LIMIT 1),
       dr.articolo_id, dr.descrizione, 6, dr.uom_operativa_id, dr.factor_to_base,
       (SELECT tipo_credito_id FROM tmp_refs), false
FROM tmp_ddt_d_riga dr;

-- Reso D2: 4 pz, confermato.
CREATE TEMP TABLE tmp_reso_d2 AS
WITH ins AS (
  INSERT INTO vendite.resi (stato_doc_reso_id, sorgente_tipo_id, sorgente_uid, storicizza, meta)
  SELECT r.stato_reso_draft_id, r.sorgente_ddt_id,
         (SELECT d.uid FROM vendite.ddt d WHERE d.id=(SELECT ddt_id FROM tmp_ddt_d)),
         false, jsonb_build_object('test_scope','pgtap_resi')
  FROM tmp_refs r RETURNING id)
SELECT * FROM ins;
INSERT INTO vendite.resi_righe (reso_id, riga_nr, ddt_riga_id, ordine_riga_id,
  articolo_id, descrizione, qta_operativa, uom_operativa_id, factor_to_base, tipo_reso_id, storicizza)
SELECT (SELECT id FROM tmp_reso_d2), 1, dr.id,
       (SELECT f.ordine_riga_id FROM vendite.ordini_righe_fulfillment f WHERE f.ddt_riga_id=dr.id LIMIT 1),
       dr.articolo_id, dr.descrizione, 4, dr.uom_operativa_id, dr.factor_to_base,
       (SELECT tipo_credito_id FROM tmp_refs), false
FROM tmp_ddt_d_riga dr;

SELECT vendite.fn_conferma_reso((SELECT id FROM tmp_reso_d2));

-- 25) IL FIX: la bozza da 6 non conta -> confermati 4 < 10 -> niente flip.
--     Col vecchio `<> 'ANNULLATO'` qui il DDT sarebbe gia' RESO (6+4=10).
SELECT is(
  (SELECT sdd.codice_interno FROM vendite.ddt d
     JOIN config.stati_doc_ddt sdd ON sdd.id=d.stato_doc_ddt_id
    WHERE d.id=(SELECT ddt_id FROM tmp_ddt_d)),
  'CONSEGNATO',
  '25) bozza 6 + confermato 4 su DDT da 10 -> DDT resta CONSEGNATO (le bozze non contano)');

-- 26) Confermata anche la bozza: 6+4=10 CONFERMATI -> il flip scatta.
--     Prova che il fix non ha rotto il flip: e' lo stato a decidere.
SELECT vendite.fn_conferma_reso((SELECT id FROM tmp_reso_d1));
SELECT is(
  (SELECT sdd.codice_interno FROM vendite.ddt d
     JOIN config.stati_doc_ddt sdd ON sdd.id=d.stato_doc_ddt_id
    WHERE d.id=(SELECT ddt_id FROM tmp_ddt_d)),
  'RESO',
  '26) confermata anche la bozza (6+4=10 confermati) -> DDT CONSEGNATO->RESO');

SELECT * FROM finish();
ROLLBACK;
