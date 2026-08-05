-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: fn_list_ddt_da_pushare — eleggibilita' DALLO stato-trigger IN POI,
--       senza aprire il DDT annullato — step 5,
--       brief-db-fatturazione-ddt-resi §3e/§9-5.
-- (changeset 20260718-02)
-- ------------------------------------------------------------
-- Indice test (1..5):
--   1) ORFANO (il fix): ordine trigger SPEDITO, DDT gia' CONSEGNATO (ha
--      superato lo stato-trigger senza essere pushato) -> ORA eleggibile.
--      Prima dell'uguaglianza secca non fatturava mai.
--   2) A-STATO: ordine trigger SPEDITO, DDT SPEDITO -> eleggibile (non
--      regredito dal passaggio al confronto di rank)
--   3) ANNULLATO (§3e.2, il rischio del rank puro): 70 >= 40 lo renderebbe
--      eleggibile -> NOT is_abortito lo esclude. Un DDT annullato non ha resi,
--      i tenuti non si azzerano: senza questo VERREBBE FATTURATO
--   4) RESO: escluso esplicitamente (merce tornata tutta indietro)
--   5) CINTURA XOR (§3e.1): ordine trigger CONFERMATO -> il suo DDT NON e'
--      eleggibile nemmeno ora. E' l'ordine a fatturare: senza questa clausola
--      doppia fatturazione su TUTTI gli ordini in configurazione di default
-- ------------------------------------------------------------

BEGIN;
-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(5);

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
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1)              AS valuta_id,
  (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1) AS iva_id,
  (SELECT ef.id FROM anagrafiche.emittenti_fiscali ef ORDER BY ef.id LIMIT 1)  AS emittente_fiscale_id,
  (SELECT s.id FROM config.stati_doc_ordini s WHERE s.codice_interno='CONFERMATO' AND s.attivo LIMIT 1) AS stato_ord_conf_id,
  (SELECT s.id FROM config.stati_doc_ddt s WHERE s.codice_interno='EMESSO' AND s.attivo LIMIT 1)     AS stato_ddt_emesso_id,
  (SELECT s.id FROM config.stati_doc_ddt s WHERE s.codice_interno='SPEDITO' AND s.attivo LIMIT 1)    AS stato_ddt_spedito_id,
  (SELECT s.id FROM config.stati_doc_ddt s WHERE s.codice_interno='CONSEGNATO' AND s.attivo LIMIT 1) AS stato_ddt_consegnato_id,
  (SELECT s.id FROM config.stati_doc_ddt s WHERE s.codice_interno='ANNULLATO' AND s.attivo LIMIT 1)  AS stato_ddt_annullato_id,
  (SELECT s.id FROM config.stati_doc_ddt s WHERE s.codice_interno='RESO' AND s.attivo LIMIT 1)       AS stato_ddt_reso_id,
  -- causale obbligatoria all'emissione dal 2026-07-18 (step 5b, DL-28);
  -- VENDITA e' l'unica fatturabile, quindi e' quella che tiene il DDT eleggibile
  (SELECT c.id FROM config.causali_trasporto c WHERE c.codice='VENDITA' LIMIT 1) AS causale_vendita_id,
  (SELECT id FROM config.tipi_indirizzi WHERE codice_interno='CON')     AS tipo_ind_con_id;

-- Ordine + DDT con trigger e stato finale parametrici (p_stato_finale = ID
-- dello stato, risolto una volta in tmp_refs). Il percorso NON e' una scala
-- fissa: config.transizioni_stati_ddt ammette solo DRAFT->EMESSO->SPEDITO->
-- CONSEGNATO, con ANNULLATO raggiungibile da DRAFT/EMESSO (da CONSEGNATO
-- esiste ma e' attivo=f) e RESO da SPEDITO o CONSEGNATO. Ogni destinazione ha
-- quindi la sua strada.
CREATE OR REPLACE FUNCTION pg_temp.mk_caso(p_trigger varchar, p_stato_finale bigint)
RETURNS TABLE(ordine_id bigint, ordine_riga_id bigint, ddt_id bigint) AS $$
DECLARE r RECORD; v_ord bigint; v_orr bigint; v_ddt bigint;
BEGIN
  SELECT * INTO r FROM tmp_refs;
  INSERT INTO vendite.ordini (soggetto_ruolo_id, billing_account_id, stato_doc_ordine_id,
    valuta_id, data, fatturazione_trigger, emittente_fiscale_id, storicizza, meta)
  VALUES (r.soggetto_ruolo_id, r.billing_account_id, r.stato_ord_conf_id, r.valuta_id,
          DATE '2026-07-15', p_trigger, r.emittente_fiscale_id, false,
          jsonb_build_object('test_scope','pgtap_orfano'))
  RETURNING id INTO v_ord;
  -- trgfn_ordini_normalize eredita il trigger dal BA solo su INSERT,
  -- sovrascrivendo il valore passato: va reimpostato con un UPDATE.
  UPDATE vendite.ordini SET fatturazione_trigger = p_trigger WHERE id = v_ord;
  INSERT INTO vendite.ordini_righe (ordine_id, riga_nr, articolo_id, descrizione,
    qta_operativa, quantita, prezzo_unitario, iva_id, attivo, storicizza, meta)
  VALUES (v_ord, 1, r.articolo_id, 'Riga orfano', 10, 10, 25, r.iva_id, true, false,
          jsonb_build_object('test_scope','pgtap_orfano'))
  RETURNING id INTO v_orr;
  v_ddt := vendite.fn_genera_ddt_da_ordine(v_ord);
  INSERT INTO vendite.ddt_indirizzi (ddt_id, tipo_indirizzo_id, snapshot)
  VALUES (v_ddt, r.tipo_ind_con_id, '{"display":"CON"}'::jsonb) ON CONFLICT DO NOTHING;
  UPDATE vendite.ddt SET causale_trasporto_id=r.causale_vendita_id WHERE id=v_ddt;
  -- DRAFT -> EMESSO: comune a tutti i percorsi.
  UPDATE vendite.ddt SET stato_doc_ddt_id=r.stato_ddt_emesso_id WHERE id=v_ddt;
  IF p_stato_finale = r.stato_ddt_annullato_id THEN
    -- unica via viva: EMESSO -> ANNULLATO (da SPEDITO non esiste,
    -- da CONSEGNATO e' attivo=f)
    UPDATE vendite.ddt SET stato_doc_ddt_id=r.stato_ddt_annullato_id WHERE id=v_ddt;
  ELSIF p_stato_finale <> r.stato_ddt_emesso_id THEN
    UPDATE vendite.ddt SET stato_doc_ddt_id=r.stato_ddt_spedito_id WHERE id=v_ddt;
    IF p_stato_finale <> r.stato_ddt_spedito_id THEN
      -- RESO e CONSEGNATO sono entrambi raggiungibili da SPEDITO
      UPDATE vendite.ddt SET stato_doc_ddt_id=p_stato_finale WHERE id=v_ddt;
    END IF;
  END IF;
  RETURN QUERY SELECT v_ord, v_orr, v_ddt;
END $$ LANGUAGE plpgsql;

-- ============================================================
-- FIXTURE
-- ============================================================
-- A: trigger SPEDITO, DDT CONSEGNATO -> l'ORFANO che il fix recupera
CREATE TEMP TABLE tmp_a AS
SELECT * FROM pg_temp.mk_caso('SPEDITO', (SELECT stato_ddt_consegnato_id FROM tmp_refs));
-- B: trigger SPEDITO, DDT SPEDITO -> il caso "a stato", non deve regredire
CREATE TEMP TABLE tmp_b AS
SELECT * FROM pg_temp.mk_caso('SPEDITO', (SELECT stato_ddt_spedito_id FROM tmp_refs));
-- C: trigger SPEDITO, DDT ANNULLATO -> rank 70 >= 40, ma documento morto.
--    NB: annullato da EMESSO (unica transizione viva) -> non e' mai stato
--    spedito, ma il rank resta 70 e il predicato lo pescherebbe comunque.
CREATE TEMP TABLE tmp_c AS
SELECT * FROM pg_temp.mk_caso('SPEDITO', (SELECT stato_ddt_annullato_id FROM tmp_refs));
-- D: trigger SPEDITO, DDT RESO -> merce tornata tutta indietro
CREATE TEMP TABLE tmp_d AS
SELECT * FROM pg_temp.mk_caso('SPEDITO', (SELECT stato_ddt_reso_id FROM tmp_refs));
-- E: trigger CONFERMATO, DDT CONSEGNATO -> fattura l'ORDINE, non il DDT
CREATE TEMP TABLE tmp_e AS
SELECT * FROM pg_temp.mk_caso('CONFERMATO', (SELECT stato_ddt_consegnato_id FROM tmp_refs));

-- ============================================================
-- ASSERZIONI
-- ============================================================
-- 1) IL FIX: il DDT che ha superato lo stato-trigger torna eleggibile
SELECT is(
  (SELECT COUNT(*)::int FROM vendite.fn_list_ddt_da_pushare(NULL,NULL,NULL,(SELECT ddt_id FROM tmp_a))),
  1, '1) ORFANO: trigger SPEDITO + DDT CONSEGNATO -> eleggibile (prima non fatturava mai)');

-- 2) Nessuna regressione sul caso che gia' funzionava
SELECT is(
  (SELECT COUNT(*)::int FROM vendite.fn_list_ddt_da_pushare(NULL,NULL,NULL,(SELECT ddt_id FROM tmp_b))),
  1, '2) A-STATO: trigger SPEDITO + DDT SPEDITO -> ancora eleggibile (no regressione)');

-- 3) Il rischio del rank puro, chiuso da NOT is_abortito
SELECT is(
  (SELECT COUNT(*)::int FROM vendite.fn_list_ddt_da_pushare(NULL,NULL,NULL,(SELECT ddt_id FROM tmp_c))),
  0, '3) ANNULLATO: rank 70 >= 40 ma is_abortito -> NON eleggibile (senza, verrebbe fatturato)');

-- 4) RESO escluso esplicitamente
SELECT is(
  (SELECT COUNT(*)::int FROM vendite.fn_list_ddt_da_pushare(NULL,NULL,NULL,(SELECT ddt_id FROM tmp_d))),
  0, '4) RESO: merce tornata tutta indietro -> NON eleggibile');

-- 5) La cintura XOR regge: l'ordine CONFERMATO fattura per conto suo
SELECT is(
  (SELECT COUNT(*)::int FROM vendite.fn_list_ddt_da_pushare(NULL,NULL,NULL,(SELECT ddt_id FROM tmp_e))),
  0, '5) CINTURA XOR: trigger CONFERMATO -> DDT mai eleggibile (fattura l''ordine)');

SELECT * FROM finish();
ROLLBACK;
