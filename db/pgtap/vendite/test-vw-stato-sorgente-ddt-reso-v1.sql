-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: rami DDT e RESO della proiezione di stato (vw_stato_sorgente_*)
--       — step 6b, brief-db-fatturazione-ddt-resi §4a.
-- (changeset 20260718-09/-10)
-- ------------------------------------------------------------
-- Indice test (1..8):
--   1) ramo DDT: il documento proietta, risolto=true, via union
--   2) 🔑 LA CHIAVE E' `id`, NON l'uid: cercare per uid NON trova nulla.
--      E' l'asserzione che protegge dalla "ripulitura" della convenzione
--      polimorfa (key_selector), che romperebbe il ramo in silenzio
--   3) DDT CONSEGNATO -> esito POSITIVO, terminale true (fase CHIUSO)
--   4) DDT ANNULLATO  -> esito NEGATIVO, terminale true (is_abortito)
--   5) DDT EMESSO     -> esito NULL, terminale false (fase IN_CORSO)
--   6) ramo RESO: reso DRAFT -> esito NULL, terminale false (fase APERTO)
--   7) reso CONFERMATO -> esito POSITIVO, terminale true (correzione catalogo
--      2026-07-18: CONFERMATO ha fase CHIUSO — un reso confermato E' concluso,
--      la ri-consegna e' un altro documento; l'annullo resta come storno)
--   8) reso ANNULLATO -> esito NEGATIVO, terminale true
--   9) unicita': al piu' una riga per (sorgente_tipo_id, sorgente_uid) su
--      entrambi i rami nuovi
-- ------------------------------------------------------------

BEGIN;
SELECT plan(9);

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
  (SELECT s.id FROM config.stati_doc_reso s WHERE s.codice_interno='DRAFT' AND s.attivo LIMIT 1)     AS stato_reso_draft_id,
  (SELECT t.id FROM config.tipi_reso t WHERE t.codice_interno='RESO_A_CREDITO' AND t.attivo LIMIT 1) AS tipo_credito_id,
  (SELECT c.id FROM config.causali_trasporto c WHERE c.codice='VENDITA' LIMIT 1) AS causale_vendita_id,
  (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno='DDT_VENDITA' AND s.attivo LIMIT 1)  AS sorgente_ddt_id,
  (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno='RESO_VENDITA' AND s.attivo LIMIT 1) AS sorgente_reso_id,
  (SELECT id FROM config.tipi_indirizzi WHERE codice_interno='CON')     AS tipo_ind_con_id;

-- Ordine -> DDT portato allo stato richiesto (percorso ammesso dalla matrice:
-- ANNULLATO solo da EMESSO, CONSEGNATO passando da SPEDITO).
CREATE OR REPLACE FUNCTION pg_temp.mk_ddt(p_stato bigint)
RETURNS TABLE(ddt_id bigint, ddt_uid uuid, ddt_riga_id bigint) AS $$
DECLARE r RECORD; v_ord bigint; v_ddt bigint; v_uid uuid; v_riga bigint;
BEGIN
  SELECT * INTO r FROM tmp_refs;
  INSERT INTO vendite.ordini (soggetto_ruolo_id, billing_account_id, stato_doc_ordine_id,
    valuta_id, data, fatturazione_trigger, emittente_fiscale_id, storicizza, meta)
  VALUES (r.soggetto_ruolo_id, r.billing_account_id, r.stato_ord_conf_id, r.valuta_id,
          DATE '2026-07-15', 'CONSEGNATO', r.emittente_fiscale_id, false,
          jsonb_build_object('test_scope','pgtap_stato_sorgente'))
  RETURNING id INTO v_ord;
  UPDATE vendite.ordini SET fatturazione_trigger = 'CONSEGNATO' WHERE id = v_ord;
  INSERT INTO vendite.ordini_righe (ordine_id, riga_nr, articolo_id, descrizione,
    qta_operativa, quantita, prezzo_unitario, iva_id, attivo, storicizza, meta)
  VALUES (v_ord, 1, r.articolo_id, 'Riga proiezione', 10, 10, 25, r.iva_id, true, false,
          jsonb_build_object('test_scope','pgtap_stato_sorgente'));
  v_ddt := vendite.fn_genera_ddt_da_ordine(v_ord);
  INSERT INTO vendite.ddt_indirizzi (ddt_id, tipo_indirizzo_id, snapshot)
  VALUES (v_ddt, r.tipo_ind_con_id, '{"display":"CON"}'::jsonb) ON CONFLICT DO NOTHING;
  -- causale obbligatoria all'emissione (step 5b)
  UPDATE vendite.ddt SET causale_trasporto_id=r.causale_vendita_id WHERE id=v_ddt;
  UPDATE vendite.ddt SET stato_doc_ddt_id=r.stato_ddt_emesso_id WHERE id=v_ddt;
  IF p_stato = r.stato_ddt_annullato_id THEN
    UPDATE vendite.ddt SET stato_doc_ddt_id=r.stato_ddt_annullato_id WHERE id=v_ddt;
  ELSIF p_stato <> r.stato_ddt_emesso_id THEN
    UPDATE vendite.ddt SET stato_doc_ddt_id=r.stato_ddt_spedito_id WHERE id=v_ddt;
    IF p_stato <> r.stato_ddt_spedito_id THEN
      UPDATE vendite.ddt SET stato_doc_ddt_id=p_stato WHERE id=v_ddt;
    END IF;
  END IF;
  SELECT d.uid INTO v_uid FROM vendite.ddt d WHERE d.id=v_ddt;
  SELECT dr.id INTO v_riga FROM vendite.ddt_righe dr WHERE dr.ddt_id=v_ddt LIMIT 1;
  RETURN QUERY SELECT v_ddt, v_uid, v_riga;
END $$ LANGUAGE plpgsql;

-- ============================================================
-- FIXTURE
-- ============================================================
CREATE TEMP TABLE tmp_cons AS SELECT * FROM pg_temp.mk_ddt((SELECT stato_ddt_consegnato_id FROM tmp_refs));
CREATE TEMP TABLE tmp_ann  AS SELECT * FROM pg_temp.mk_ddt((SELECT stato_ddt_annullato_id  FROM tmp_refs));
CREATE TEMP TABLE tmp_eme  AS SELECT * FROM pg_temp.mk_ddt((SELECT stato_ddt_emesso_id     FROM tmp_refs));

-- Reso in DRAFT sul DDT consegnato (il guard pretende il DDT CONSEGNATO)
CREATE TEMP TABLE tmp_reso AS
WITH ins AS (
  INSERT INTO vendite.resi (stato_doc_reso_id, sorgente_tipo_id, sorgente_uid, storicizza, meta)
  SELECT r.stato_reso_draft_id, r.sorgente_ddt_id, (SELECT ddt_uid FROM tmp_cons), false,
         jsonb_build_object('test_scope','pgtap_stato_sorgente')
  FROM tmp_refs r RETURNING id)
SELECT * FROM ins;

INSERT INTO vendite.resi_righe (reso_id, riga_nr, ddt_riga_id, ordine_riga_id,
  articolo_id, descrizione, qta_operativa, uom_operativa_id, factor_to_base, tipo_reso_id, storicizza)
SELECT (SELECT id FROM tmp_reso), 1, dr.id,
       (SELECT f.ordine_riga_id FROM vendite.ordini_righe_fulfillment f WHERE f.ddt_riga_id=dr.id LIMIT 1),
       dr.articolo_id, dr.descrizione, 3, dr.uom_operativa_id, dr.factor_to_base,
       (SELECT tipo_credito_id FROM tmp_refs), false
FROM vendite.ddt_righe dr WHERE dr.id=(SELECT ddt_riga_id FROM tmp_cons);

-- ============================================================
-- ASSERZIONI
-- ============================================================
-- 1) il ramo DDT arriva nella union
SELECT is(
  (SELECT v.risolto FROM script.vw_stato_sorgente v
    WHERE v.sorgente_tipo_id=(SELECT sorgente_ddt_id FROM tmp_refs)
      AND v.sorgente_uid=(SELECT ddt_id FROM tmp_cons)::text),
  true, '1) ramo DDT: il documento proietta in script.vw_stato_sorgente (risolto=true)');

-- 2) LA CHIAVE E' id, NON uid (key_selector='id' per DDT_VENDITA).
--    Se qualcuno "ripulisse" la convenzione passando all'uid, il ramo
--    smetterebbe di agganciare in silenzio: questa asserzione lo impedisce.
SELECT is(
  (SELECT COUNT(*)::int FROM script.vw_stato_sorgente v
    WHERE v.sorgente_tipo_id=(SELECT sorgente_ddt_id FROM tmp_refs)
      AND v.sorgente_uid=(SELECT ddt_uid FROM tmp_cons)::text),
  0, '2) la chiave del DDT e'' id::text, NON l''uid (convenzione polimorfa key_selector)');

-- 3-5) esito/terminale derivati da fase + is_abortito
SELECT is(
  (SELECT (v.esito, v.terminale) FROM script.vw_stato_sorgente v
    WHERE v.sorgente_tipo_id=(SELECT sorgente_ddt_id FROM tmp_refs)
      AND v.sorgente_uid=(SELECT ddt_id FROM tmp_cons)::text),
  ('POSITIVO'::text, true), '3) DDT CONSEGNATO (fase CHIUSO, non abortito) -> POSITIVO / terminale');

SELECT is(
  (SELECT (v.esito, v.terminale) FROM script.vw_stato_sorgente v
    WHERE v.sorgente_tipo_id=(SELECT sorgente_ddt_id FROM tmp_refs)
      AND v.sorgente_uid=(SELECT ddt_id FROM tmp_ann)::text),
  ('NEGATIVO'::text, true), '4) DDT ANNULLATO (is_abortito) -> NEGATIVO / terminale');

SELECT is(
  (SELECT (v.esito, v.terminale) FROM script.vw_stato_sorgente v
    WHERE v.sorgente_tipo_id=(SELECT sorgente_ddt_id FROM tmp_refs)
      AND v.sorgente_uid=(SELECT ddt_id FROM tmp_eme)::text),
  (NULL::text, false), '5) DDT EMESSO (fase IN_CORSO) -> esito NULL / non terminale');

-- 6-7) ramo RESO
SELECT is(
  (SELECT (v.esito, v.terminale) FROM script.vw_stato_sorgente v
    WHERE v.sorgente_tipo_id=(SELECT sorgente_reso_id FROM tmp_refs)
      AND v.sorgente_uid=(SELECT id FROM tmp_reso)::text),
  (NULL::text, false), '6) ramo RESO: reso DRAFT (fase APERTO) -> esito NULL / non terminale');

-- 7) conferma -> CONFERMATO ha fase CHIUSO (correzione catalogo 2026-07-18):
--    il reso confermato E' concluso -> POSITIVO / terminale
SELECT vendite.fn_conferma_reso((SELECT id FROM tmp_reso));
SELECT is(
  (SELECT (v.esito, v.terminale) FROM script.vw_stato_sorgente v
    WHERE v.sorgente_tipo_id=(SELECT sorgente_reso_id FROM tmp_refs)
      AND v.sorgente_uid=(SELECT id FROM tmp_reso)::text),
  ('POSITIVO'::text, true), '7) reso CONFERMATO (fase CHIUSO da correzione catalogo) -> POSITIVO / terminale');

-- 8) annullo (storno guardato, ammesso da CONFERMATO senza ri-consegne)
SELECT vendite.fn_annulla_reso((SELECT id FROM tmp_reso));
SELECT is(
  (SELECT (v.esito, v.terminale) FROM script.vw_stato_sorgente v
    WHERE v.sorgente_tipo_id=(SELECT sorgente_reso_id FROM tmp_refs)
      AND v.sorgente_uid=(SELECT id FROM tmp_reso)::text),
  ('NEGATIVO'::text, true), '8) reso ANNULLATO (is_abortito) -> NEGATIVO / terminale');

-- 9) unicita' della chiave sui due rami nuovi
SELECT is(
  (SELECT COUNT(*)::int FROM (
      SELECT v.sorgente_tipo_id, v.sorgente_uid
        FROM script.vw_stato_sorgente v
       WHERE v.sorgente_tipo_id IN ((SELECT sorgente_ddt_id FROM tmp_refs),
                                    (SELECT sorgente_reso_id FROM tmp_refs))
       GROUP BY 1,2 HAVING COUNT(*) > 1) dup),
  0, '9) al piu'' una riga per (sorgente_tipo_id, sorgente_uid) sui rami DDT e RESO');

SELECT * FROM finish();
ROLLBACK;
