-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: vendite.vw_contatore_merce — il contatore (brief-db-fatturazione-ddt-resi
--       §3a, step 1). Per riga d'ordine (partita order-backed, non composita):
--       tenuti (Σ evaso − Σ reso) e fatturati (Σ AF NORMALE sui segmenti ORD+DDT),
--       differenza = tenuti − fatturati.
-- (changeset 20260717-11)
-- ------------------------------------------------------------
-- Indice test (1..10):
--   1) la vista esiste
--   2) e' security_invoker=on (RLS — regressione V-1)
--   3) espone le colonne del contratto
--   4) P1 prima del push: tenuti 7, nessuna AF -> differenza +7 (capitolato §3a #1)
--   5) P1 dopo push DDT (AF DDT=10) + un ONERE sullo stesso ordine: fatturati=10
--      (l'ONERE NON conta: filtro tipo_movimento='NORMALE')
--   6) P1: differenza = 7 − 10 = −3 (accredita 3 — capitolato #3)
--   7) P2: AF su segmento ORD (trigger CONFERMATO) attribuita alla riga d'ordine
--   8) P2: differenza −3 (capitolato #10, misura sull'ordine)
--   9) P3: reso TOTALE -> tenuti 0, nessuna AF -> differenza 0 (capitolato #4)
--  10) P4: articolo COMPOSITO -> riga d'ordine ESCLUSA dalla vista (follow-up)
-- ------------------------------------------------------------

BEGIN;
SELECT plan(10);

-- Le madri sono SECURITY INVOKER: il pgTAP gira come owner.
SET LOCAL app.ruolo_applicativo = 'OPERATORE';
SET LOCAL app.current_user_id = '1';

-- ============================================================
-- 1-3) Struttura della vista
-- ============================================================
SELECT has_view('vendite', 'vw_contatore_merce', '1) la vista esiste');

SELECT ok(
  (SELECT 'security_invoker=on' = ANY(c.reloptions)
     FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'vendite' AND c.relname = 'vw_contatore_merce'),
  '2) vw_contatore_merce e'' security_invoker=on');

SELECT columns_are('vendite', 'vw_contatore_merce',
  ARRAY['ordine_riga_id','ordine_id','articolo_id','tenuti','fatturati','differenza'],
  '3) espone ordine_riga_id/ordine_id/articolo_id/tenuti/fatturati/differenza');

-- ============================================================
-- Riferimenti minimi
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
  (SELECT a.id FROM catalogo.articoli a
    WHERE a.attivo IS TRUE AND a.is_composito IS TRUE
    ORDER BY a.data_insert DESC NULLS LAST LIMIT 1)                      AS articolo_composito_id,
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
  (SELECT t.id FROM config.tipi_doc_fiscale t WHERE t.attivo IS TRUE ORDER BY t.id LIMIT 1) AS tipo_doc_fiscale_id,
  -- Dal 2026-07-18 (step 5b / DL-28) la causale trasporto e' obbligatoria all'emissione
  -- del DDT: VENDITA e' l'unica fatturabile, quindi e' quella che tiene il DDT
  -- eleggibile al push verso la fatturazione.
  (SELECT c.id FROM config.causali_trasporto c WHERE c.codice='VENDITA' LIMIT 1) AS causale_vendita_id,
  (SELECT id FROM config.tipi_indirizzi WHERE codice_interno='CON')     AS tipo_ind_con_id;

-- Helper: crea ordine (qta 10) -> DDT -> CONSEGNATO. Ritorna gli id.
-- (inline via funzione temporanea per non ripetere 15 righe per partita)
CREATE OR REPLACE FUNCTION pg_temp.mk_partita(p_articolo uuid)
RETURNS TABLE(ordine_id bigint, ordine_uid uuid, ordine_riga_id bigint,
              ddt_id bigint, ddt_uid uuid, ddt_riga_id bigint) AS $$
DECLARE r RECORD; v_ord bigint; v_ord_uid uuid; v_orr bigint; v_ddt bigint; v_ddt_uid uuid; v_ddtr bigint;
BEGIN
  SELECT * INTO r FROM tmp_refs;
  INSERT INTO vendite.ordini (soggetto_ruolo_id, billing_account_id, stato_doc_ordine_id,
    valuta_id, data, fatturazione_trigger, emittente_fiscale_id, storicizza, meta)
  VALUES (r.soggetto_ruolo_id, r.billing_account_id, r.stato_ord_conf_id, r.valuta_id,
          DATE '2026-07-15', 'SPEDITO', r.emittente_fiscale_id, false,
          jsonb_build_object('test_scope','pgtap_contatore'))
  RETURNING id, uid INTO v_ord, v_ord_uid;
  INSERT INTO vendite.ordini_righe (ordine_id, riga_nr, articolo_id, descrizione,
    qta_operativa, quantita, prezzo_unitario, iva_id, attivo, storicizza, meta)
  VALUES (v_ord, 1, p_articolo, 'Riga contatore', 10, 10, 25, r.iva_id, true, false,
          jsonb_build_object('test_scope','pgtap_contatore'))
  RETURNING id INTO v_orr;
  v_ddt := vendite.fn_genera_ddt_da_ordine(v_ord);
  INSERT INTO vendite.ddt_indirizzi (ddt_id, tipo_indirizzo_id, snapshot)
  VALUES (v_ddt, r.tipo_ind_con_id, '{"display":"CON"}'::jsonb) ON CONFLICT DO NOTHING;
  UPDATE vendite.ddt SET causale_trasporto_id=r.causale_vendita_id  WHERE id=v_ddt;
  UPDATE vendite.ddt SET stato_doc_ddt_id=r.stato_ddt_emesso_id     WHERE id=v_ddt;
  UPDATE vendite.ddt SET stato_doc_ddt_id=r.stato_ddt_spedito_id    WHERE id=v_ddt;
  UPDATE vendite.ddt SET stato_doc_ddt_id=r.stato_ddt_consegnato_id WHERE id=v_ddt;
  SELECT d.uid INTO v_ddt_uid FROM vendite.ddt d WHERE d.id=v_ddt;
  SELECT dr.id INTO v_ddtr FROM vendite.ddt_righe dr WHERE dr.ddt_id=v_ddt LIMIT 1;
  RETURN QUERY SELECT v_ord, v_ord_uid, v_orr, v_ddt, v_ddt_uid, v_ddtr;
END $$ LANGUAGE plpgsql;

-- Helper: conferma un reso a credito di qta X sulla riga DDT data.
CREATE OR REPLACE FUNCTION pg_temp.mk_reso(p_ddt_riga bigint, p_ddt_uid uuid, p_qta numeric)
RETURNS void AS $$
DECLARE r RECORD; v_reso bigint;
BEGIN
  SELECT * INTO r FROM tmp_refs;
  INSERT INTO vendite.resi (stato_doc_reso_id, sorgente_tipo_id, sorgente_uid, storicizza, meta)
  VALUES (r.stato_reso_draft_id, r.sorgente_ddt_id, p_ddt_uid, false,
          jsonb_build_object('test_scope','pgtap_contatore'))
  RETURNING id INTO v_reso;
  INSERT INTO vendite.resi_righe (reso_id, riga_nr, ddt_riga_id, ordine_riga_id,
    articolo_id, descrizione, qta_operativa, uom_operativa_id, factor_to_base, tipo_reso_id, storicizza)
  SELECT v_reso, 1, dr.id,
         (SELECT f.ordine_riga_id FROM vendite.ordini_righe_fulfillment f WHERE f.ddt_riga_id=dr.id LIMIT 1),
         dr.articolo_id, dr.descrizione, p_qta, dr.uom_operativa_id, dr.factor_to_base,
         r.tipo_credito_id, false
  FROM vendite.ddt_righe dr WHERE dr.id=p_ddt_riga;
  PERFORM vendite.fn_conferma_reso(v_reso);
END $$ LANGUAGE plpgsql;

-- Commessa unica per gli AF di test + ROOT source (richiesta da emit).
CREATE TEMP TABLE tmp_com AS
SELECT vendite.fn_get_or_create_commessa(
  p_billing_account_id => (SELECT billing_account_id FROM tmp_refs),
  p_utility_id => (SELECT utility_id FROM tmp_refs),
  p_tipo_commessa => 'AUTO', p_policy_fatturazione => 'DA_DOCUMENTO',
  p_fatturazione_immediata => false, p_priorita_operativa => 'NORMALE',
  p_competenza_dal => DATE '2026-07-01', p_competenza_al => DATE '2026-07-31',
  p_meta => jsonb_build_object('test_scope','pgtap_contatore'), p_force_new => true
) AS commessa_id;
SELECT vendite.fn_link_commessa_sorgente(
  p_commessa_id => (SELECT commessa_id FROM tmp_com),
  p_sorgente_tipo_id => (SELECT sorgente_root_id FROM tmp_refs),
  p_sorgente_uid => ('SRC-CM-' || substr(md5(clock_timestamp()::text),1,12))::text,
  p_sorgente_riga => 1, p_meta => '{}'::jsonb);

-- Helper: aggiunge una CA con segment_key esplicito + tipo_movimento e la emette.
CREATE OR REPLACE FUNCTION pg_temp.mk_af(p_segment varchar, p_qta numeric, p_tipo_mov varchar)
RETURNS void AS $$
DECLARE r RECORD;
BEGIN
  SELECT * INTO r FROM tmp_refs;
  PERFORM vendite.fn_upsert_commessa_attivita(
    p_commessa_id => (SELECT commessa_id FROM tmp_com),
    p_segment_key => p_segment,
    p_articolo_id => r.articolo_id,
    p_istanza_utility_id => r.istanza_utility_id,
    p_data_attivita => DATE '2026-07-15',
    p_uom_id => r.uom_id, p_quantita => p_qta,
    p_competenza_mese => DATE '2026-07-01', p_competenza_dal => DATE '2026-07-01', p_competenza_al => DATE '2026-07-31',
    p_prezzo_snapshot => 10.0, p_prezzo_base_snapshot => NULL, p_origine_prezzo => NULL,
    p_tipo_variazione_applicata => NULL, p_valore_variazione_applicata => NULL,
    p_promo_id => NULL, p_contratto_id => NULL, p_categoria_cliente_id_snapshot => NULL, p_classe_utenza_id_snapshot => NULL,
    p_tipo_doc_fiscale_id => r.tipo_doc_fiscale_id,
    p_stato_approvazione => 'APPROVATA', p_stato_emissione => 'NON_EMESSA',
    p_tipo_movimento => p_tipo_mov, p_tipo_consumo => 'CONGUAGLIO', p_meta => '{}'::jsonb);
END $$ LANGUAGE plpgsql;

-- ============================================================
-- P1: order 10 -> ship 10 -> reso 3 -> tenuti 7
-- ============================================================
CREATE TEMP TABLE tmp_p1 AS SELECT * FROM pg_temp.mk_partita((SELECT articolo_id FROM tmp_refs));
SELECT pg_temp.mk_reso((SELECT ddt_riga_id FROM tmp_p1), (SELECT ddt_uid FROM tmp_p1), 3);

-- 4) P1 prima del push (nessuna AF): differenza +7 (capitolato #1)
SELECT is(
  (SELECT differenza FROM vendite.vw_contatore_merce WHERE ordine_riga_id=(SELECT ordine_riga_id FROM tmp_p1)),
  7::numeric,
  '4) P1 prima del push: tenuti 7 − fatturati 0 = differenza +7 (capitolato #1)');

-- ============================================================
-- P2: order 10 -> ship 10 -> reso 3 -> tenuti 7 (per il ramo ORD)
-- P3: order 10 -> ship 10 -> reso 10 -> tenuti 0 (reso totale)
-- ============================================================
CREATE TEMP TABLE tmp_p2 AS SELECT * FROM pg_temp.mk_partita((SELECT articolo_id FROM tmp_refs));
SELECT pg_temp.mk_reso((SELECT ddt_riga_id FROM tmp_p2), (SELECT ddt_uid FROM tmp_p2), 3);
CREATE TEMP TABLE tmp_p3 AS SELECT * FROM pg_temp.mk_partita((SELECT articolo_id FROM tmp_refs));
SELECT pg_temp.mk_reso((SELECT ddt_riga_id FROM tmp_p3), (SELECT ddt_uid FROM tmp_p3), 10);

-- AF: P1 fattura via DDT (NORMALE, 10) + un ONERE sullo stesso ordine (5, deve
--     essere ignorato); P2 fattura via ORD (NORMALE, 10).
SELECT pg_temp.mk_af('DDT:' || (SELECT ddt_uid FROM tmp_p1)::text || ':R:' || (SELECT ddt_riga_id FROM tmp_p1)::text, 10, 'NORMALE');
SELECT pg_temp.mk_af('ORD:' || (SELECT ordine_uid FROM tmp_p1)::text || ':R:' || (SELECT ordine_riga_id FROM tmp_p1)::text, 5, 'ONERE');
SELECT pg_temp.mk_af('ORD:' || (SELECT ordine_uid FROM tmp_p2)::text || ':R:' || (SELECT ordine_riga_id FROM tmp_p2)::text, 10, 'NORMALE');

-- Emissione: PRONTA_FATTURAZIONE + pull -> crea le AF.
SELECT vendite.fn_cambia_stato_commessa((SELECT commessa_id FROM tmp_com), 'PRONTA_FATTURAZIONE');
SELECT vendite.fn_emit_attivita_fatturabili_da_commessa((SELECT commessa_id FROM tmp_com));

-- 5) P1 fatturati = 10: la AF DDT conta, l'ONERE (5) NO (filtro tipo_movimento)
SELECT is(
  (SELECT fatturati FROM vendite.vw_contatore_merce WHERE ordine_riga_id=(SELECT ordine_riga_id FROM tmp_p1)),
  10::numeric,
  '5) P1 fatturati=10: AF DDT contata, ONERE escluso (filtro tipo_movimento=NORMALE)');

-- 6) P1 differenza = 7 − 10 = −3 (accredita 3 — capitolato #3)
SELECT is(
  (SELECT differenza FROM vendite.vw_contatore_merce WHERE ordine_riga_id=(SELECT ordine_riga_id FROM tmp_p1)),
  -3::numeric,
  '6) P1 differenza −3: attribuzione via segmento DDT + fulfillment (capitolato #3)');

-- 7) P2 fatturati = 10 via segmento ORD (attribuzione diretta alla riga d'ordine)
SELECT is(
  (SELECT fatturati FROM vendite.vw_contatore_merce WHERE ordine_riga_id=(SELECT ordine_riga_id FROM tmp_p2)),
  10::numeric,
  '7) P2 fatturati=10 via segmento ORD (trigger CONFERMATO, capitolato #10)');

-- 8) P2 differenza −3
SELECT is(
  (SELECT differenza FROM vendite.vw_contatore_merce WHERE ordine_riga_id=(SELECT ordine_riga_id FROM tmp_p2)),
  -3::numeric,
  '8) P2 differenza −3 (misura sull''ordine, capitolato #10)');

-- 9) P3 reso totale: tenuti 0, nessuna AF -> differenza 0 (capitolato #4)
SELECT is(
  (SELECT differenza FROM vendite.vw_contatore_merce WHERE ordine_riga_id=(SELECT ordine_riga_id FROM tmp_p3)),
  0::numeric,
  '9) P3 reso totale -> tenuti 0, differenza 0 (capitolato #4, chiude 1b)');

-- ============================================================
-- 10) P4: articolo COMPOSITO -> riga d'ordine ESCLUSA dalla vista.
--     Conditional skip se nel DB dev non esiste un articolo composito.
--     tmp_p4 creata SEMPRE (vuota se manca il composito), cosi' la CASE
--     finale referenzia una tabella esistente anche nel ramo skip.
-- ============================================================
CREATE TEMP TABLE tmp_p4 (ordine_id bigint, ordine_uid uuid, ordine_riga_id bigint,
                          ddt_id bigint, ddt_uid uuid, ddt_riga_id bigint);
DO $$
DECLARE v_comp uuid;
BEGIN
  SELECT articolo_composito_id INTO v_comp FROM tmp_refs;
  IF v_comp IS NOT NULL THEN
    INSERT INTO tmp_p4 SELECT * FROM pg_temp.mk_partita(v_comp);
  END IF;
END $$;

SELECT CASE
  WHEN (SELECT articolo_composito_id FROM tmp_refs) IS NULL
    THEN skip('nessun articolo composito nel DB dev', 1)
  ELSE is(
    (SELECT COUNT(*)::int FROM vendite.vw_contatore_merce
      WHERE ordine_riga_id=(SELECT ordine_riga_id FROM tmp_p4)),
    0,
    '10) riga d''ordine con articolo COMPOSITO esclusa dalla vista (follow-up)')
  END;

SELECT * FROM finish();
ROLLBACK;
