-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: DDT di solo trasporto — l'intento si dichiara con la CAUSALE
--       (fatturabile) — step 5b, brief-db-fatturazione-ddt-resi §4a / DL-28.
-- (changeset 20260718-03/-04/-05/-06)
-- ------------------------------------------------------------
-- Indice test (1..6):
--   1) Seed del vocabolario: VENDITA fatturabile, le altre sette no
--   2) Gate R1: emissione senza causale -> BLOCCATA (E_DDT_CAUSALE_OBBLIGATORIA)
--   3) Gate R2: causale VENDITA + riga senza prezzo risolvibile (standalone,
--      nessun ordine da cui ereditare) -> BLOCCATA (E_DDT_PREZZO_NON_RISOLVIBILE)
--   4) Gate R2, il caso legittimo: riga da EVASIONE senza prezzo proprio ma con
--      la riga d'ordine che lo fornisce -> emissione PASSA (e' la COALESCE del
--      lister: le righe da evasione senza prezzo restano legittime)
--   5) Causale NON fatturabile (CAMPIONATURA) -> mai eleggibile al push, anche
--      a CONSEGNATO e con prezzi validi: e' la cintura del lister
--   6) Controprova: stessa identica situazione con causale VENDITA -> eleggibile
--      (senza questa, il test 5 passerebbe anche se il lister fosse rotto)
-- ------------------------------------------------------------

BEGIN;
SELECT plan(6);

SET LOCAL app.ruolo_applicativo = 'OPERATORE';
SET LOCAL app.current_user_id = '1';

-- ============================================================
-- Riferimenti + helper
-- ============================================================
CREATE TEMP TABLE tmp_refs AS
SELECT
  (SELECT ba.id FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL AND ba.istanza_utility_id IS NOT NULL
      AND anagrafiche.fn_get_emittente_fiscale_id(ba.id) IS NOT NULL
    ORDER BY ba.id LIMIT 1)                                              AS billing_account_id,
  (SELECT sr.id FROM anagrafiche.soggetti_ruoli sr ORDER BY sr.id LIMIT 1) AS soggetto_ruolo_id,
  (SELECT a.id FROM catalogo.articoli a
    WHERE a.attivo IS TRUE AND COALESCE(a.is_composito, FALSE) IS FALSE
    ORDER BY a.data_insert DESC NULLS LAST LIMIT 1)                      AS articolo_id,
  (SELECT u.id FROM catalogo.unita_misura u WHERE u.attivo IS TRUE ORDER BY u.id LIMIT 1) AS uom_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1)              AS valuta_id,
  (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1) AS iva_id,
  (SELECT ef.id FROM anagrafiche.emittenti_fiscali ef ORDER BY ef.id LIMIT 1)  AS emittente_fiscale_id,
  (SELECT s.id FROM config.stati_doc_ordini s WHERE s.codice_interno='CONFERMATO' AND s.attivo LIMIT 1) AS stato_ord_conf_id,
  (SELECT s.id FROM config.stati_doc_ddt s WHERE s.codice_interno='EMESSO' AND s.attivo LIMIT 1)     AS stato_ddt_emesso_id,
  (SELECT s.id FROM config.stati_doc_ddt s WHERE s.codice_interno='SPEDITO' AND s.attivo LIMIT 1)    AS stato_ddt_spedito_id,
  (SELECT s.id FROM config.stati_doc_ddt s WHERE s.codice_interno='CONSEGNATO' AND s.attivo LIMIT 1) AS stato_ddt_consegnato_id,
  (SELECT c.id FROM config.causali_trasporto c WHERE c.codice='VENDITA' LIMIT 1)      AS causale_vendita_id,
  (SELECT c.id FROM config.causali_trasporto c WHERE c.codice='CAMPIONATURA' LIMIT 1) AS causale_campioni_id,
  (SELECT id FROM config.tipi_indirizzi WHERE codice_interno='CON')     AS tipo_ind_con_id;

-- Ordine + DDT da evasione, causale parametrica. p_prezzo_riga NULL = la riga
-- DDT non ha prezzo proprio (lo eredita dall'ordine via fulfillment).
CREATE OR REPLACE FUNCTION pg_temp.mk_ddt_da_ordine(p_causale bigint, p_prezzo_ordine numeric)
RETURNS TABLE(ordine_id bigint, ddt_id bigint) AS $$
DECLARE r RECORD; v_ord bigint; v_ddt bigint;
BEGIN
  SELECT * INTO r FROM tmp_refs;
  INSERT INTO vendite.ordini (soggetto_ruolo_id, billing_account_id, stato_doc_ordine_id,
    valuta_id, data, fatturazione_trigger, emittente_fiscale_id, storicizza, meta)
  VALUES (r.soggetto_ruolo_id, r.billing_account_id, r.stato_ord_conf_id, r.valuta_id,
          DATE '2026-07-15', 'CONSEGNATO', r.emittente_fiscale_id, false,
          jsonb_build_object('test_scope','pgtap_causale'))
  RETURNING id INTO v_ord;
  UPDATE vendite.ordini SET fatturazione_trigger = 'CONSEGNATO' WHERE id = v_ord;
  INSERT INTO vendite.ordini_righe (ordine_id, riga_nr, articolo_id, descrizione,
    qta_operativa, quantita, prezzo_unitario, iva_id, attivo, storicizza, meta)
  VALUES (v_ord, 1, r.articolo_id, 'Riga causale', 10, 10, p_prezzo_ordine, r.iva_id, true, false,
          jsonb_build_object('test_scope','pgtap_causale'));
  v_ddt := vendite.fn_genera_ddt_da_ordine(v_ord);
  INSERT INTO vendite.ddt_indirizzi (ddt_id, tipo_indirizzo_id, snapshot)
  VALUES (v_ddt, r.tipo_ind_con_id, '{"display":"CON"}'::jsonb) ON CONFLICT DO NOTHING;
  UPDATE vendite.ddt SET causale_trasporto_id = p_causale WHERE id = v_ddt;
  -- la riga DDT nasce senza prezzo proprio: deve ereditarlo dall'ordine.
  -- Alias obbligatorio: `ddt_id` e' anche un parametro OUT di questa funzione.
  UPDATE vendite.ddt_righe dr SET prezzo_unitario = NULL WHERE dr.ddt_id = v_ddt;
  RETURN QUERY SELECT v_ord, v_ddt;
END $$ LANGUAGE plpgsql;

-- DDT STANDALONE (nessun ordine dietro) con una riga SENZA prezzo: e' l'unico
-- modo per ottenere un prezzo NON risolvibile, visto che ordini_righe.prezzo_unitario
-- e' NOT NULL — da un ordine il prezzo c'e' sempre e la riga DDT lo eredita.
CREATE OR REPLACE FUNCTION pg_temp.mk_ddt_standalone(p_causale bigint)
RETURNS bigint AS $$
DECLARE r RECORD; v_ddt bigint;
BEGIN
  SELECT * INTO r FROM tmp_refs;
  INSERT INTO vendite.ddt (destinatario_soggetto_ruolo_id, stato_doc_ddt_id, data,
    billing_account_id, valuta_id, causale_trasporto_id, emittente_fiscale_id, storicizza, meta)
  VALUES (r.soggetto_ruolo_id,
          (SELECT s.id FROM config.stati_doc_ddt s WHERE s.codice_interno='DRAFT' LIMIT 1),
          DATE '2026-07-15', r.billing_account_id, r.valuta_id, p_causale,
          r.emittente_fiscale_id, false, jsonb_build_object('test_scope','pgtap_causale'))
  RETURNING id INTO v_ddt;
  INSERT INTO vendite.ddt_righe (ddt_id, riga_nr, articolo_id, descrizione,
    qta_operativa, quantita, prezzo_unitario, iva_id, attivo, storicizza, meta)
  VALUES (v_ddt, 1, r.articolo_id, 'Riga senza prezzo', 10, 10, NULL, r.iva_id, true, false,
          jsonb_build_object('test_scope','pgtap_causale'));
  INSERT INTO vendite.ddt_indirizzi (ddt_id, tipo_indirizzo_id, snapshot)
  VALUES (v_ddt, r.tipo_ind_con_id, '{"display":"CON"}'::jsonb) ON CONFLICT DO NOTHING;
  RETURN v_ddt;
END $$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION pg_temp.porta_a(p_ddt bigint, p_stato bigint)
RETURNS void AS $$
DECLARE r RECORD;
BEGIN
  SELECT * INTO r FROM tmp_refs;
  UPDATE vendite.ddt SET stato_doc_ddt_id=r.stato_ddt_emesso_id  WHERE id=p_ddt;
  IF p_stato <> r.stato_ddt_emesso_id THEN
    UPDATE vendite.ddt SET stato_doc_ddt_id=r.stato_ddt_spedito_id WHERE id=p_ddt;
    IF p_stato <> r.stato_ddt_spedito_id THEN
      UPDATE vendite.ddt SET stato_doc_ddt_id=p_stato WHERE id=p_ddt;
    END IF;
  END IF;
END $$ LANGUAGE plpgsql;

-- ============================================================
-- 1) Il vocabolario guida: zero IF hardcoded, una cella di seed
-- ============================================================
SELECT is(
  (SELECT array_agg(c.codice ORDER BY c.codice) FROM config.causali_trasporto c WHERE c.fatturabile),
  ARRAY['VENDITA']::varchar[],
  '1) seed: VENDITA e'' l''unica causale fatturabile (le altre sette sono solo trasporto)');

-- ============================================================
-- 2) Gate R1: senza causale non si emette
-- ============================================================
CREATE TEMP TABLE tmp_senza AS SELECT * FROM pg_temp.mk_ddt_da_ordine(NULL, 25);
SELECT throws_ok(
  $$ UPDATE vendite.ddt SET stato_doc_ddt_id=(SELECT stato_ddt_emesso_id FROM tmp_refs)
      WHERE id=(SELECT ddt_id FROM tmp_senza) $$,
  'P0001', NULL,
  '2) gate R1: emissione senza causale di trasporto -> bloccata');

-- ============================================================
-- 3) Gate R2: VENDITA + prezzo non risolvibile -> bloccata.
--    DDT standalone: senza ordine dietro non c'e' prezzo da ereditare.
-- ============================================================
CREATE TEMP TABLE tmp_nopr AS
SELECT pg_temp.mk_ddt_standalone((SELECT causale_vendita_id FROM tmp_refs)) AS ddt_id;
SELECT throws_ok(
  $$ UPDATE vendite.ddt SET stato_doc_ddt_id=(SELECT stato_ddt_emesso_id FROM tmp_refs)
      WHERE id=(SELECT ddt_id FROM tmp_nopr) $$,
  'P0001', NULL,
  '3) gate R2: causale VENDITA + riga senza prezzo risolvibile -> emissione bloccata');

-- ============================================================
-- 4) Gate R2, il caso legittimo: prezzo ereditato dall'ordine
-- ============================================================
CREATE TEMP TABLE tmp_eredita AS
SELECT * FROM pg_temp.mk_ddt_da_ordine((SELECT causale_vendita_id FROM tmp_refs), 25);
SELECT lives_ok(
  $$ UPDATE vendite.ddt SET stato_doc_ddt_id=(SELECT stato_ddt_emesso_id FROM tmp_refs)
      WHERE id=(SELECT ddt_id FROM tmp_eredita) $$,
  '4) gate R2: riga da evasione senza prezzo proprio ma ereditabile dall''ordine -> emissione passa');

-- ============================================================
-- 5-6) La cintura del lister: solo trasporto vs vendita
-- ============================================================
CREATE TEMP TABLE tmp_camp AS
SELECT * FROM pg_temp.mk_ddt_da_ordine((SELECT causale_campioni_id FROM tmp_refs), 25);
SELECT pg_temp.porta_a((SELECT ddt_id FROM tmp_camp), (SELECT stato_ddt_consegnato_id FROM tmp_refs));

CREATE TEMP TABLE tmp_vend AS
SELECT * FROM pg_temp.mk_ddt_da_ordine((SELECT causale_vendita_id FROM tmp_refs), 25);
SELECT pg_temp.porta_a((SELECT ddt_id FROM tmp_vend), (SELECT stato_ddt_consegnato_id FROM tmp_refs));

SELECT is(
  (SELECT COUNT(*)::int FROM vendite.fn_list_ddt_da_pushare(NULL,NULL,NULL,(SELECT ddt_id FROM tmp_camp))),
  0, '5) causale CAMPIONATURA: solo trasporto -> mai eleggibile al push, anche a CONSEGNATO');

SELECT is(
  (SELECT COUNT(*)::int FROM vendite.fn_list_ddt_da_pushare(NULL,NULL,NULL,(SELECT ddt_id FROM tmp_vend))),
  1, '6) controprova: stessa situazione con causale VENDITA -> eleggibile');

SELECT * FROM finish();
ROLLBACK;
