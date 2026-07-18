-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: vw_resi_da_accreditare nella forma §3c — popolata dalla differenza
--       NEGATIVA del contatore, tipo reso degradato a etichetta — step 4,
--       brief-db-fatturazione-ddt-resi §3c/§9-4.
-- (changeset 20260718-01)
-- ------------------------------------------------------------
-- Indice test (1..8):
--   1) security_invoker=on sulla vista (regressione V-1: reloption azzerata in
--      silenzio da un CREATE OR REPLACE senza WITH -> bypass RLS)
--   2) P1 reso MAI fatturato -> conto in pari o a credito -> ESCE (chiude 1b:
--      oggi resterebbe in coda per sempre)
--   3) P2 reso su merce fatturata -> accredito dovuto 3
--   4) P2 etichetta DOVUTA (tipo a credito)
--   5) P2 il conto e' esposto (tenuti 7, fatturati 10): la coda dice cosa e'
--      successo, non cosa fare (§7)
--   6) P3 ri-consegna su merce gia' fatturata -> IN CODA, etichetta FACOLTATIVA
--      (oggi invisibile: riapre_residuo=false la tagliava)
--   7-8) P4 distribuzione greedy tra due righe di reso della stessa partita:
--      accredito 1 -> la prima lo prende tutto, alla seconda non resta nulla
-- ------------------------------------------------------------

BEGIN;
SELECT plan(8);

SET LOCAL app.ruolo_applicativo = 'OPERATORE';
SET LOCAL app.current_user_id = '1';

-- ============================================================
-- Riferimenti + helper (stessa fixture di
-- test-fn-list-ddt-da-pushare-contatore-v1)
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
  -- Dal 2026-07-18 (step 5b / DL-28) la causale trasporto e' obbligatoria all'emissione
  -- del DDT: VENDITA e' l'unica fatturabile, quindi e' quella che tiene il DDT
  -- eleggibile al push verso la fatturazione.
  (SELECT c.id FROM config.causali_trasporto c WHERE c.codice='VENDITA' LIMIT 1) AS causale_vendita_id,
  (SELECT id FROM config.tipi_indirizzi WHERE codice_interno='CON')     AS tipo_ind_con_id;

CREATE OR REPLACE FUNCTION pg_temp.mk_partita()
RETURNS TABLE(ordine_id bigint, ordine_uid uuid, ordine_riga_id bigint,
              ddt_id bigint, ddt_uid uuid, ddt_riga_id bigint) AS $$
DECLARE r RECORD; v_ord bigint; v_ord_uid uuid; v_orr bigint; v_ddt bigint; v_ddt_uid uuid; v_ddtr bigint;
BEGIN
  SELECT * INTO r FROM tmp_refs;
  INSERT INTO vendite.ordini (soggetto_ruolo_id, billing_account_id, stato_doc_ordine_id,
    valuta_id, data, fatturazione_trigger, emittente_fiscale_id, storicizza, meta)
  VALUES (r.soggetto_ruolo_id, r.billing_account_id, r.stato_ord_conf_id, r.valuta_id,
          DATE '2026-07-15', 'CONSEGNATO', r.emittente_fiscale_id, false,
          jsonb_build_object('test_scope','pgtap_accrediti'))
  RETURNING id, uid INTO v_ord, v_ord_uid;
  -- trgfn_ordini_normalize eredita fatturazione_trigger dal BA solo su INSERT,
  -- sovrascrivendo il valore passato: va reimpostato con un UPDATE.
  UPDATE vendite.ordini SET fatturazione_trigger = 'CONSEGNATO' WHERE id = v_ord;
  INSERT INTO vendite.ordini_righe (ordine_id, riga_nr, articolo_id, descrizione,
    qta_operativa, quantita, prezzo_unitario, iva_id, attivo, storicizza, meta)
  VALUES (v_ord, 1, r.articolo_id, 'Riga accrediti', 10, 10, 25, r.iva_id, true, false,
          jsonb_build_object('test_scope','pgtap_accrediti'))
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

-- Ritorna la RIGA di reso creata (la coda ha grana riga-di-reso).
CREATE OR REPLACE FUNCTION pg_temp.mk_reso(p_ddt_riga bigint, p_ddt_uid uuid, p_qta numeric, p_tipo bigint)
RETURNS bigint AS $$
DECLARE r RECORD; v_reso bigint; v_riga bigint;
BEGIN
  SELECT * INTO r FROM tmp_refs;
  INSERT INTO vendite.resi (stato_doc_reso_id, sorgente_tipo_id, sorgente_uid, storicizza, meta)
  VALUES (r.stato_reso_draft_id, r.sorgente_ddt_id, p_ddt_uid, false, jsonb_build_object('test_scope','pgtap_accrediti'))
  RETURNING id INTO v_reso;
  INSERT INTO vendite.resi_righe (reso_id, riga_nr, ddt_riga_id, ordine_riga_id,
    articolo_id, descrizione, qta_operativa, uom_operativa_id, factor_to_base, tipo_reso_id, storicizza)
  SELECT v_reso, 1, dr.id,
         (SELECT f.ordine_riga_id FROM vendite.ordini_righe_fulfillment f WHERE f.ddt_riga_id=dr.id LIMIT 1),
         dr.articolo_id, dr.descrizione, p_qta, dr.uom_operativa_id, dr.factor_to_base, p_tipo, false
  FROM vendite.ddt_righe dr WHERE dr.id=p_ddt_riga
  RETURNING id INTO v_riga;
  PERFORM vendite.fn_conferma_reso(v_reso);
  RETURN v_riga;
END $$ LANGUAGE plpgsql;

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
  p_sorgente_uid => ('SRC-ACC-' || substr(md5(clock_timestamp()::text),1,12))::text,
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
-- FIXTURE (il contatore e' set-based: l'ordine di creazione non conta,
-- contano le somme)
--   P1  reso 3, NESSUNA fattura      -> tenuti 7, fatt 0  -> diff +7 -> esce
--   P2  reso 3 a credito, fattura 10 -> tenuti 7, fatt 10 -> accredito 3, DOVUTA
--   P3  reso 3 riconsegna, fattura 10-> tenuti 7, fatt 10 -> accredito 3, FACOLTATIVA
--   P4  resi 2+2 a credito, fattura 7-> tenuti 6, fatt 7  -> accredito 1: greedy
-- ============================================================
CREATE TEMP TABLE tmp_p1 AS SELECT * FROM pg_temp.mk_partita();
CREATE TEMP TABLE tmp_p1_riga AS
SELECT pg_temp.mk_reso((SELECT ddt_riga_id FROM tmp_p1), (SELECT ddt_uid FROM tmp_p1), 3,
                       (SELECT tipo_credito_id FROM tmp_refs)) AS resi_riga_id;

CREATE TEMP TABLE tmp_p2 AS SELECT * FROM pg_temp.mk_partita();
CREATE TEMP TABLE tmp_p2_riga AS
SELECT pg_temp.mk_reso((SELECT ddt_riga_id FROM tmp_p2), (SELECT ddt_uid FROM tmp_p2), 3,
                       (SELECT tipo_credito_id FROM tmp_refs)) AS resi_riga_id;

CREATE TEMP TABLE tmp_p3 AS SELECT * FROM pg_temp.mk_partita();
CREATE TEMP TABLE tmp_p3_riga AS
SELECT pg_temp.mk_reso((SELECT ddt_riga_id FROM tmp_p3), (SELECT ddt_uid FROM tmp_p3), 3,
                       (SELECT tipo_riconsegna_id FROM tmp_refs)) AS resi_riga_id;

CREATE TEMP TABLE tmp_p4 AS SELECT * FROM pg_temp.mk_partita();
CREATE TEMP TABLE tmp_p4_riga1 AS
SELECT pg_temp.mk_reso((SELECT ddt_riga_id FROM tmp_p4), (SELECT ddt_uid FROM tmp_p4), 2,
                       (SELECT tipo_credito_id FROM tmp_refs)) AS resi_riga_id;
CREATE TEMP TABLE tmp_p4_riga2 AS
SELECT pg_temp.mk_reso((SELECT ddt_riga_id FROM tmp_p4), (SELECT ddt_uid FROM tmp_p4), 2,
                       (SELECT tipo_credito_id FROM tmp_refs)) AS resi_riga_id;

-- Fatturazione: P2 e P3 per 10 (tutto), P4 per 7 (parziale). P1 nessuna.
SELECT pg_temp.mk_af('DDT:' || (SELECT ddt_uid FROM tmp_p2)::text || ':R:' || (SELECT ddt_riga_id FROM tmp_p2)::text, 10);
SELECT pg_temp.mk_af('DDT:' || (SELECT ddt_uid FROM tmp_p3)::text || ':R:' || (SELECT ddt_riga_id FROM tmp_p3)::text, 10);
SELECT pg_temp.mk_af('DDT:' || (SELECT ddt_uid FROM tmp_p4)::text || ':R:' || (SELECT ddt_riga_id FROM tmp_p4)::text, 7);
SELECT vendite.fn_cambia_stato_commessa((SELECT commessa_id FROM tmp_com), 'PRONTA_FATTURAZIONE');
SELECT vendite.fn_emit_attivita_fatturabili_da_commessa((SELECT commessa_id FROM tmp_com));

-- ============================================================
-- ASSERZIONI
-- ============================================================
-- 1) security_invoker: la reloption sopravvive al changeset (regressione V-1)
SELECT ok(
  (SELECT 'security_invoker=on' = ANY(c.reloptions)
     FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
    WHERE n.nspname='vendite' AND c.relname='vw_resi_da_accreditare'),
  '1) security_invoker=on ri-specificato sulla vista (no bypass RLS)');

-- 2) P1: merce resa MAI fatturata -> niente da accreditare -> ESCE (chiude 1b)
SELECT is(
  (SELECT COUNT(*)::int FROM vendite.vw_resi_da_accreditare
    WHERE resi_riga_id=(SELECT resi_riga_id FROM tmp_p1_riga)),
  0, '2) P1 reso mai fatturato: conto in pari -> fuori dalla coda (chiude 1b)');

-- 3-5) P2: reso su merce fatturata -> accredito 3, DOVUTA, conto esposto
SELECT is(
  (SELECT accredito_dovuto FROM vendite.vw_resi_da_accreditare
    WHERE resi_riga_id=(SELECT resi_riga_id FROM tmp_p2_riga)),
  3::numeric, '3) P2 reso su merce fatturata: accredito dovuto 3 (10 fatturati - 7 tenuti)');

SELECT is(
  (SELECT etichetta FROM vendite.vw_resi_da_accreditare
    WHERE resi_riga_id=(SELECT resi_riga_id FROM tmp_p2_riga)),
  'DOVUTA'::varchar, '4) P2 tipo a credito -> etichetta DOVUTA (la merce non torna piu'')');

SELECT is(
  (SELECT (tenuti, fatturati) FROM vendite.vw_resi_da_accreditare
    WHERE resi_riga_id=(SELECT resi_riga_id FROM tmp_p2_riga)),
  (7::numeric, 10::numeric), '5) P2 il conto e'' esposto: tenuti 7, fatturati 10 (cosa e'' successo, non cosa fare)');

-- 6) P3: ri-consegna su merce gia' fatturata -> IN CODA come FACOLTATIVA
--    (oggi invisibile: la forma vecchia filtrava riapre_residuo=false)
SELECT is(
  (SELECT etichetta FROM vendite.vw_resi_da_accreditare
    WHERE resi_riga_id=(SELECT resi_riga_id FROM tmp_p3_riga)),
  'FACOLTATIVA'::varchar, '6) P3 ri-consegna su merce fatturata: in coda, etichetta FACOLTATIVA (oggi invisibile)');

-- 7-8) P4: accredito 1 su due righe di reso da 2 -> la prima lo prende tutto
SELECT is(
  (SELECT accredito_dovuto FROM vendite.vw_resi_da_accreditare
    WHERE resi_riga_id=(SELECT resi_riga_id FROM tmp_p4_riga1)),
  1::numeric, '7) P4 greedy: la 1a riga di reso assorbe l''accredito, cappato (1 di 2)');

SELECT is(
  (SELECT COUNT(*)::int FROM vendite.vw_resi_da_accreditare
    WHERE resi_riga_id=(SELECT resi_riga_id FROM tmp_p4_riga2)),
  0, '8) P4 greedy: alla 2a riga non resta accredito -> fuori dalla coda');

SELECT * FROM finish();
ROLLBACK;
