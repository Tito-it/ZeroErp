-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: fn_list_ddt_da_pushare proietta la DIFFERENZA del contatore
--       (vw_contatore_merce), non piu' dr.quantita grezza — step 3,
--       brief-db-fatturazione-ddt-resi §3a/§9-3. Chiude la doppia fatturazione.
-- (changeset 20260717-12)
-- ------------------------------------------------------------
-- Indice test (1..5):
--   1) A: order 10, consegnato, nessun reso -> lister proietta 10 (nessuna riduzione)
--   2) B: order 10, reso 3 -> lister proietta 7 (IL RESO RIDUCE IL PUSH — il fix)
--   3) B: qta_operativa scalata a 7 (coerente con la base, factor 1)
--   4) C: reso 3 + fatturato 7 -> riga DDT EMESSA -> esclusa (frontiera, 0 righe)
--   5) D (caso 8 §3a): ri-consegna di merce GIA' fatturata -> il DDT nuovo
--      proietta 0 -> NON pushato -> niente doppia fattura (chiude bug 1a)
--   6-7) F (§3d): partita 10 spezzata in DUE DDT parziali (6+4) con reso 5 ->
--      differenza 5 distribuita greedy: 1o DDT 5 (cappato), 2o DDT 0.
--      Unico caso che esercita la window del greedy con precedente non vuoto.
-- Nota: standalone (dr.quantita grezza invariata) coperto da
--       test-fn-list-ddt-da-pushare-v1 casi 7-8.
-- ------------------------------------------------------------

BEGIN;
SELECT plan(7);

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
  (SELECT ba.utility_id FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL AND ba.istanza_utility_id IS NOT NULL
      AND anagrafiche.fn_get_emittente_fiscale_id(ba.id) IS NOT NULL
    ORDER BY ba.id LIMIT 1)                                              AS utility_id,
  (SELECT ba.istanza_utility_id FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL AND ba.istanza_utility_id IS NOT NULL
      AND anagrafiche.fn_get_emittente_fiscale_id(ba.id) IS NOT NULL
    ORDER BY ba.id LIMIT 1)                                              AS istanza_utility_id,
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
  (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno='DDT_VENDITA' AND s.attivo LIMIT 1)     AS sorgente_ddt_id,
  (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno='PREVENTIVO' AND s.attivo LIMIT 1)      AS sorgente_root_id,
  (SELECT s.id FROM config.stati_doc_reso s WHERE s.codice_interno='DRAFT' AND s.attivo LIMIT 1)     AS stato_reso_draft_id,
  (SELECT t.id FROM config.tipi_reso t WHERE t.codice_interno='RESO_A_CREDITO' AND t.attivo LIMIT 1) AS tipo_credito_id,
  (SELECT t.id FROM config.tipi_reso t WHERE t.codice_interno='RESO_PER_RICONSEGNA' AND t.attivo LIMIT 1) AS tipo_riconsegna_id,
  (SELECT t.id FROM config.tipi_doc_fiscale t WHERE t.attivo IS TRUE ORDER BY t.id LIMIT 1) AS tipo_doc_fiscale_id,
  (SELECT id FROM config.tipi_indirizzi WHERE codice_interno='CON')     AS tipo_ind_con_id;

-- Ordine (qta 10, trigger CONSEGNATO) -> DDT -> CONSEGNATO (stato = trigger, cosi'
-- il lister lo lista E il reso-guard passa).
-- Ordine solo (qta 10, trigger CONSEGNATO), senza DDT: base sia della partita
-- monolitica (mk_partita) sia di quella spezzata in DDT parziali (caso F).
CREATE OR REPLACE FUNCTION pg_temp.mk_partita_ordine()
RETURNS TABLE(ordine_id bigint, ordine_uid uuid, ordine_riga_id bigint) AS $$
DECLARE r RECORD; v_ord bigint; v_ord_uid uuid; v_orr bigint;
BEGIN
  SELECT * INTO r FROM tmp_refs;
  INSERT INTO vendite.ordini (soggetto_ruolo_id, billing_account_id, stato_doc_ordine_id,
    valuta_id, data, fatturazione_trigger, emittente_fiscale_id, storicizza, meta)
  VALUES (r.soggetto_ruolo_id, r.billing_account_id, r.stato_ord_conf_id, r.valuta_id,
          DATE '2026-07-15', 'CONSEGNATO', r.emittente_fiscale_id, false,
          jsonb_build_object('test_scope','pgtap_lister'))
  RETURNING id, uid INTO v_ord, v_ord_uid;
  -- trgfn_ordini_normalize eredita fatturazione_trigger da
  -- billing_account.fatturazione_ordini SOLO su INSERT, sovrascrivendo il valore
  -- passato: va reimpostato con un UPDATE (stesso pattern di
  -- test-fn-list-ddt-da-pushare-v1). Serve CONSEGNATO per superare la cintura XOR.
  UPDATE vendite.ordini SET fatturazione_trigger = 'CONSEGNATO' WHERE id = v_ord;
  INSERT INTO vendite.ordini_righe (ordine_id, riga_nr, articolo_id, descrizione,
    qta_operativa, quantita, prezzo_unitario, iva_id, attivo, storicizza, meta)
  VALUES (v_ord, 1, r.articolo_id, 'Riga lister', 10, 10, 25, r.iva_id, true, false,
          jsonb_build_object('test_scope','pgtap_lister'))
  RETURNING id INTO v_orr;
  RETURN QUERY SELECT v_ord, v_ord_uid, v_orr;
END $$ LANGUAGE plpgsql;

-- Porta un DDT a CONSEGNATO passando per la scala degli stati (il lister lo lista
-- E il reso-guard passa).
CREATE OR REPLACE FUNCTION pg_temp.mk_ddt_consegnato(p_ddt bigint)
RETURNS void AS $$
DECLARE r RECORD;
BEGIN
  SELECT * INTO r FROM tmp_refs;
  INSERT INTO vendite.ddt_indirizzi (ddt_id, tipo_indirizzo_id, snapshot)
  VALUES (p_ddt, r.tipo_ind_con_id, '{"display":"CON"}'::jsonb) ON CONFLICT DO NOTHING;
  UPDATE vendite.ddt SET stato_doc_ddt_id=r.stato_ddt_emesso_id     WHERE id=p_ddt;
  UPDATE vendite.ddt SET stato_doc_ddt_id=r.stato_ddt_spedito_id    WHERE id=p_ddt;
  UPDATE vendite.ddt SET stato_doc_ddt_id=r.stato_ddt_consegnato_id WHERE id=p_ddt;
END $$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION pg_temp.mk_partita()
RETURNS TABLE(ordine_id bigint, ordine_uid uuid, ordine_riga_id bigint,
              ddt_id bigint, ddt_uid uuid, ddt_riga_id bigint) AS $$
DECLARE o RECORD; v_ddt bigint; v_ddt_uid uuid; v_ddtr bigint;
BEGIN
  SELECT * INTO o FROM pg_temp.mk_partita_ordine();
  v_ddt := vendite.fn_genera_ddt_da_ordine(o.ordine_id);
  PERFORM pg_temp.mk_ddt_consegnato(v_ddt);
  SELECT d.uid INTO v_ddt_uid FROM vendite.ddt d WHERE d.id=v_ddt;
  SELECT dr.id INTO v_ddtr FROM vendite.ddt_righe dr WHERE dr.ddt_id=v_ddt LIMIT 1;
  RETURN QUERY SELECT o.ordine_id, o.ordine_uid, o.ordine_riga_id, v_ddt, v_ddt_uid, v_ddtr;
END $$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION pg_temp.mk_reso(p_ddt_riga bigint, p_ddt_uid uuid, p_qta numeric, p_tipo bigint)
RETURNS bigint AS $$
DECLARE r RECORD; v_reso bigint;
BEGIN
  SELECT * INTO r FROM tmp_refs;
  INSERT INTO vendite.resi (stato_doc_reso_id, sorgente_tipo_id, sorgente_uid, storicizza, meta)
  VALUES (r.stato_reso_draft_id, r.sorgente_ddt_id, p_ddt_uid, false, jsonb_build_object('test_scope','pgtap_lister'))
  RETURNING id INTO v_reso;
  INSERT INTO vendite.resi_righe (reso_id, riga_nr, ddt_riga_id, ordine_riga_id,
    articolo_id, descrizione, qta_operativa, uom_operativa_id, factor_to_base, tipo_reso_id, storicizza)
  SELECT v_reso, 1, dr.id,
         (SELECT f.ordine_riga_id FROM vendite.ordini_righe_fulfillment f WHERE f.ddt_riga_id=dr.id LIMIT 1),
         dr.articolo_id, dr.descrizione, p_qta, dr.uom_operativa_id, dr.factor_to_base, p_tipo, false
  FROM vendite.ddt_righe dr WHERE dr.id=p_ddt_riga;
  PERFORM vendite.fn_conferma_reso(v_reso);
  RETURN v_reso;
END $$ LANGUAGE plpgsql;

-- Commessa unica per gli AF di test + ROOT source.
CREATE TEMP TABLE tmp_com AS
SELECT vendite.fn_get_or_create_commessa(
  p_billing_account_id => (SELECT billing_account_id FROM tmp_refs),
  p_utility_id => (SELECT utility_id FROM tmp_refs),
  p_tipo_commessa => 'AUTO', p_policy_fatturazione => 'DA_DOCUMENTO',
  p_fatturazione_immediata => false, p_priorita_operativa => 'NORMALE',
  p_competenza_dal => DATE '2026-07-01', p_competenza_al => DATE '2026-07-31',
  p_meta => '{}'::jsonb, p_force_new => true) AS commessa_id;
SELECT vendite.fn_link_commessa_sorgente(
  p_commessa_id => (SELECT commessa_id FROM tmp_com),
  p_sorgente_tipo_id => (SELECT sorgente_root_id FROM tmp_refs),
  p_sorgente_uid => ('SRC-LS-' || substr(md5(clock_timestamp()::text),1,12))::text,
  p_sorgente_riga => 1, p_meta => '{}'::jsonb);

CREATE OR REPLACE FUNCTION pg_temp.mk_af(p_segment varchar, p_qta numeric)
RETURNS void AS $$
DECLARE r RECORD;
BEGIN
  SELECT * INTO r FROM tmp_refs;
  PERFORM vendite.fn_upsert_commessa_attivita(
    p_commessa_id => (SELECT commessa_id FROM tmp_com), p_segment_key => p_segment,
    p_articolo_id => r.articolo_id, p_istanza_utility_id => r.istanza_utility_id,
    p_data_attivita => DATE '2026-07-15', p_uom_id => r.uom_id, p_quantita => p_qta,
    p_competenza_mese => DATE '2026-07-01', p_competenza_dal => DATE '2026-07-01', p_competenza_al => DATE '2026-07-31',
    p_prezzo_snapshot => 10.0, p_prezzo_base_snapshot => NULL, p_origine_prezzo => NULL,
    p_tipo_variazione_applicata => NULL, p_valore_variazione_applicata => NULL,
    p_promo_id => NULL, p_contratto_id => NULL, p_categoria_cliente_id_snapshot => NULL, p_classe_utenza_id_snapshot => NULL,
    p_tipo_doc_fiscale_id => r.tipo_doc_fiscale_id, p_stato_approvazione => 'APPROVATA', p_stato_emissione => 'NON_EMESSA',
    p_tipo_movimento => 'NORMALE', p_tipo_consumo => 'CONGUAGLIO', p_meta => '{}'::jsonb);
END $$ LANGUAGE plpgsql;

-- ============================================================
-- FIXTURE: A (no reso), B (reso 3), C (reso 3 + fatt 7), D (caso 8), E (standalone)
-- ============================================================
CREATE TEMP TABLE tmp_a AS SELECT * FROM pg_temp.mk_partita();

CREATE TEMP TABLE tmp_b AS SELECT * FROM pg_temp.mk_partita();
SELECT pg_temp.mk_reso((SELECT ddt_riga_id FROM tmp_b), (SELECT ddt_uid FROM tmp_b), 3, (SELECT tipo_credito_id FROM tmp_refs));

CREATE TEMP TABLE tmp_c AS SELECT * FROM pg_temp.mk_partita();
SELECT pg_temp.mk_reso((SELECT ddt_riga_id FROM tmp_c), (SELECT ddt_uid FROM tmp_c), 3, (SELECT tipo_credito_id FROM tmp_refs));

-- D (caso 8): consegnato + fatturato 10, reso 3 PER RICONSEGNA, ri-spedito.
CREATE TEMP TABLE tmp_d AS SELECT * FROM pg_temp.mk_partita();
CREATE TEMP TABLE tmp_d_reso AS
SELECT pg_temp.mk_reso((SELECT ddt_riga_id FROM tmp_d), (SELECT ddt_uid FROM tmp_d), 3, (SELECT tipo_riconsegna_id FROM tmp_refs)) AS reso_id;
-- ri-spedizione dei 3 (p_righe NULL = copertura residua) -> nuovo DDT
CREATE TEMP TABLE tmp_d_ric AS
SELECT vendite.fn_genera_ddt_riconsegna((SELECT reso_id FROM tmp_d_reso)) AS ddt_id;
-- porta il DDT di ri-consegna a CONSEGNATO (per essere eleggibile al lister)
INSERT INTO vendite.ddt_indirizzi (ddt_id, tipo_indirizzo_id, snapshot)
SELECT (SELECT ddt_id FROM tmp_d_ric), (SELECT tipo_ind_con_id FROM tmp_refs), '{"display":"CON"}'::jsonb ON CONFLICT DO NOTHING;
UPDATE vendite.ddt SET stato_doc_ddt_id=(SELECT stato_ddt_emesso_id FROM tmp_refs)     WHERE id=(SELECT ddt_id FROM tmp_d_ric);
UPDATE vendite.ddt SET stato_doc_ddt_id=(SELECT stato_ddt_spedito_id FROM tmp_refs)    WHERE id=(SELECT ddt_id FROM tmp_d_ric);
UPDATE vendite.ddt SET stato_doc_ddt_id=(SELECT stato_ddt_consegnato_id FROM tmp_refs) WHERE id=(SELECT ddt_id FROM tmp_d_ric);

-- F (§3d, distribuzione greedy): UNA partita da 10 spezzata in DUE DDT parziali
-- (6 + 4), entrambi CONSEGNATO ed eleggibili, con reso 5 -> differenza 5.
-- E' l'unico caso che esercita la window del greedy con un precedente NON vuoto:
-- il 1o DDT assorbe 5 (cappato dalla differenza), al 2o non resta nulla -> 0.
-- Senza il termine ROWS ... 1 PRECEDING il 2o proietterebbe 4 = merce gia'
-- coperta dal 1o -> doppia fatturazione.
CREATE TEMP TABLE tmp_f AS
WITH ord AS (
  SELECT vendite.fn_genera_ddt_da_ordine(o.ordine_id,
           jsonb_build_array(jsonb_build_object('ordine_riga_id', o.ordine_riga_id, 'qta_da_evadere', 6))) AS ddt1_id,
         o.ordine_id, o.ordine_riga_id
  FROM pg_temp.mk_partita_ordine() o
)
SELECT ord.ordine_id, ord.ordine_riga_id, ord.ddt1_id,
       vendite.fn_genera_ddt_da_ordine(ord.ordine_id,
         jsonb_build_array(jsonb_build_object('ordine_riga_id', ord.ordine_riga_id, 'qta_da_evadere', 4))) AS ddt2_id
FROM ord;

SELECT pg_temp.mk_ddt_consegnato(ddt1_id) FROM tmp_f;
SELECT pg_temp.mk_ddt_consegnato(ddt2_id) FROM tmp_f;

-- reso 5 sul PRIMO DDT (riga da 6) -> tenuti 5 sulla partita
SELECT pg_temp.mk_reso(
  (SELECT dr.id FROM vendite.ddt_righe dr WHERE dr.ddt_id=(SELECT ddt1_id FROM tmp_f) LIMIT 1),
  (SELECT d.uid FROM vendite.ddt d WHERE d.id=(SELECT ddt1_id FROM tmp_f)),
  5, (SELECT tipo_credito_id FROM tmp_refs));

-- Nota: lo standalone (ramo ELSE = dr.quantita grezza, invariato) e' gia' coperto
-- da test-fn-list-ddt-da-pushare-v1 (casi 7-8, "DDT autonomo"): non ripetuto qui.

-- Fatturazione: CA per C (DDT_C, 7) e D (DDT_orig_D, 10) -> emit.
SELECT pg_temp.mk_af('DDT:' || (SELECT ddt_uid FROM tmp_c)::text || ':R:' || (SELECT ddt_riga_id FROM tmp_c)::text, 7);
SELECT pg_temp.mk_af('DDT:' || (SELECT ddt_uid FROM tmp_d)::text || ':R:' || (SELECT ddt_riga_id FROM tmp_d)::text, 10);
SELECT vendite.fn_cambia_stato_commessa((SELECT commessa_id FROM tmp_com), 'PRONTA_FATTURAZIONE');
SELECT vendite.fn_emit_attivita_fatturabili_da_commessa((SELECT commessa_id FROM tmp_com));

-- ============================================================
-- ASSERZIONI
-- ============================================================
-- 1) A: nessun reso -> proietta 10
SELECT is(
  (SELECT quantita FROM vendite.fn_list_ddt_da_pushare(NULL,NULL,NULL,(SELECT ddt_id FROM tmp_a)) LIMIT 1),
  10::numeric, '1) A senza reso: lister proietta la quantita piena (10)');

-- 2) B: reso 3 -> proietta 7 (IL FIX)
SELECT is(
  (SELECT quantita FROM vendite.fn_list_ddt_da_pushare(NULL,NULL,NULL,(SELECT ddt_id FROM tmp_b)) LIMIT 1),
  7::numeric, '2) B reso 3: lister proietta la DIFFERENZA (7), non dr.quantita (il fix)');

-- 3) B: qta_operativa scalata a 7
SELECT is(
  (SELECT qta_operativa FROM vendite.fn_list_ddt_da_pushare(NULL,NULL,NULL,(SELECT ddt_id FROM tmp_b)) LIMIT 1),
  7::numeric, '3) B: qta_operativa scalata proporzionalmente (7)');

-- 4) C: fatturato 7 -> riga DDT EMESSA -> esclusa
SELECT is(
  (SELECT COUNT(*)::int FROM vendite.fn_list_ddt_da_pushare(NULL,NULL,NULL,(SELECT ddt_id FROM tmp_c))),
  0, '4) C fatturato: riga DDT EMESSA esclusa (frontiera)');

-- 5) D (caso 8): il DDT di ri-consegna proietta 0 -> non pushato (chiude 1a)
SELECT is(
  (SELECT COUNT(*)::int FROM vendite.fn_list_ddt_da_pushare(NULL,NULL,NULL,(SELECT ddt_id FROM tmp_d_ric))),
  0, '5) D caso 8: ri-consegna di merce gia'' fatturata -> DDT nuovo proietta 0, non pushato (chiude bug 1a)');

-- 6-7) F (§3d): distribuzione greedy su DUE righe DDT della STESSA partita.
-- Differenza 5 (10 consegnati − 5 resi) contro DDT1=6 e DDT2=4: il 1o e' cappato
-- dalla differenza (5), al 2o non resta nulla (0 -> non listato).
-- IN BATCH (p_ddt_id NULL): e' l'unica modalita' in cui la window vede piu' di un
-- candidato per partita. Col push MIRATO (p_ddt_id valorizzato) il filtro e' dentro
-- la CTE cand, quindi il DDT2 da solo proietta min(4, differenza)=4 — corretto e
-- convergente (la AF creata abbassa la differenza per il giro dopo), non e' una
-- doppia fatturazione. Vedi §CONVERGENZA del changeset 20260717-12.
CREATE TEMP TABLE tmp_batch AS
SELECT ddt_id, riga_id, quantita FROM vendite.fn_list_ddt_da_pushare(NULL,NULL,NULL,NULL);

SELECT is(
  (SELECT quantita FROM tmp_batch WHERE ddt_id=(SELECT ddt1_id FROM tmp_f)),
  5::numeric, '6) F batch: il 1o DDT della partita assorbe la differenza, cappato (5 di 6)');

SELECT is(
  (SELECT COUNT(*)::int FROM tmp_batch WHERE ddt_id=(SELECT ddt2_id FROM tmp_f)),
  0, '7) F batch: al 2o DDT non resta differenza -> 0, non pushato (la window del greedy non doppia-fattura)');

SELECT * FROM finish();
ROLLBACK;
