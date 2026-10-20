-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13, 2e/L2c-1): le chiavi del push col codice della sorgente, composte da script.fn_segment_key dove la forma lo permette (le forme su piu' righe col prefisso lungo); corsia e codice del registro coi codici lunghi.
-- pgTAP test per Zero ERP
-- Test: vendite.fn_resi_da_accreditare — la coda accrediti PER DOCUMENTO
--       (D14 giro 2 — D3; brief-db-partita-merce-per-documento §2.2, §7;
--        changeSet 20260921-28..-31).
--
-- Indice test (plan 12):
--   1) la funzione esiste, e' BEGIN ATOMIC, NON e' SECURITY DEFINER e dipende
--      da fn_partite_merce nel catalogo (la catena RLS passa di li')
--   2) ⭐ pin di D1: la vista e' la PROIEZIONE della funzione — nomina
--      fn_resi_da_accreditare e nessuna tabella, nessuna partita
--   3) ⭐ pin dei tipi: 27 colonne coi CINQUE typmod dei varchar (reso_numero 32,
--      ba_codice 30, descrizione 255, motivo 255, ddt_numero 20) — un SELECT *
--      dalla funzione li perderebbe — e security_invoker=on
--   4) ⭐ LE SORELLE: partita da 10 fatturata 6, DUE resi a credito sulla stessa
--      riga (A 4, poi B 3): capienza 3 → A prende 3 e B resta fuori. Chiesta
--      per DDT la coda ha UNA riga (A, 3, DOVUTA) — senza la sorella A, B si
--      prenderebbe i 3
--   5) ⭐ il guard del ponte attraverso la funzione: fn_resi_riga_tetti_accredito
--      dice 3 per A e 0 per B (il valore fail-closed)
--   6) seme per DDT e per ORDINE: identici alla vista filtrata come la filtra il
--      backend (ddt_id / EXISTS sul fulfillment), nei due versi
--   7) ⭐ riga MULTIPLA (la riga di DDT evade anche un ordine B2): la coda per
--      l'ordine B2 la CONTIENE (predicato del BB), mentre la partita per B2 non
--      esce da fn_partite_merce (ordine_id = riga minima): due semantiche
--      «per ordine», di proposito diverse
--   8) ⭐ il verbo attraverso la funzione: fn_accredita_riga_reso(A) scrive
--      qta_partita 3; emessa la rettifica, la partita pareggia e la coda del
--      DDT e' vuota (gia_accreditato 3)
--   9) FACOLTATIVA: reso PER RI-CONSEGNA con residuo aperto su una partita
--      fatturata per intero → in coda con l'etichetta FACOLTATIVA
--  10) niente in coda: reso su una partita NON fatturata (differenza positiva)
--      da' zero righe per quel DDT, come id inesistente e array VUOTO
--  11) (NULL, NULL) = la vista: stesso numero di righe (vuoto NON e' «tutte»)
--  12) scope: chi non vede il documento non vede la coda — zero righe
--
-- Scopo:
--  - la funzione e' equivalente alla vista per costruzione; questo file
--    COSTRUISCE il caso in cui, senza le sorelle nella finestra, la greedy
--    darebbe a una riga una quota gia' presa (4, 5), e quello in cui il seme
--    per ordine deve seguire il predicato del backend e non quello della
--    partita (7). Un EXCEPT ALL sulle righe di oggi non lo farebbe.
--  - i due VERBI (accredita, guard del ponte) si provano attraverso la
--    funzione: sono i lettori per riga che pagavano la coda di tutti.
--  - ⭐ il mondo (cliente, articolo) e' COSTRUITO dai builder di dbops, non
--    cercato: il file deve girare identico su dbdev e su un database da zero.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

-- Dal 2026-09-28 conferma e annullo del reso sono verbi che applicano
-- l'azione conferma_reso (brief-db-magazzino-lotto-3-bis-carico-da-reso, D-3b-f):
-- l'operatore di fixture non ha azioni, si concede qui.
DO $az$ BEGIN
    PERFORM dbops.fn_pgtap_concedi_azione(
        NULLIF(current_setting('app.current_user_id', true), '')::integer, 'conferma_reso');
END $az$;

SELECT plan(12);

-- ============================================================
-- 1-3) Struttura: funzione, pin di D1, pin dei tipi
-- ============================================================
SELECT ok(
  (SELECT p.prosqlbody IS NOT NULL AND NOT p.prosecdef
      AND EXISTS (SELECT 1 FROM pg_depend d
                   WHERE d.classid = 'pg_proc'::regclass AND d.objid = p.oid
                     AND d.refclassid = 'pg_proc'::regclass
                     AND d.refobjid = 'vendite.fn_partite_merce'::regproc)
     FROM pg_proc p
    WHERE p.proname = 'fn_resi_da_accreditare' AND p.pronamespace = 'vendite'::regnamespace),
  '1) fn_resi_da_accreditare esiste, e'' BEGIN ATOMIC, non DEFINER, e dipende da fn_partite_merce in pg_depend');

SELECT ok(
  (SELECT d ~ 'fn_resi_da_accreditare' AND d !~ 'vendite\.resi_righe'
      AND d !~ 'vw_partite_merce' AND d !~ 'fn_partite_merce' AND d !~ 'vw_resi_righe_effettive'
     FROM pg_get_viewdef('vendite.vw_resi_da_accreditare'::regclass, true) AS d),
  '2) la vista e'' la proiezione di fn_resi_da_accreditare: nomina la funzione e nessuna tabella');

SELECT is(
  (SELECT count(*)::int || '|' ||
          string_agg(a.attname || '=' || format_type(a.atttypid, a.atttypmod), ',' ORDER BY a.attnum)
            FILTER (WHERE a.attname IN ('reso_numero','ba_codice','descrizione','motivo','ddt_numero'))
     FROM pg_attribute a
    WHERE a.attrelid = 'vendite.vw_resi_da_accreditare'::regclass AND a.attnum > 0 AND NOT a.attisdropped)
  || '|' || COALESCE((SELECT o.option_value FROM pg_options_to_table(
                        (SELECT c.reloptions FROM pg_class c WHERE c.oid = 'vendite.vw_resi_da_accreditare'::regclass)) o
                       WHERE o.option_name = 'security_invoker'), 'off'),
  '27|reso_numero=character varying(32),ba_codice=character varying(30),descrizione=character varying(255),motivo=character varying(255),ddt_numero=character varying(20)|on',
  '3) la vista ha 27 colonne, i cinque varchar tengono il typmod, security_invoker=on');

-- ============================================================
-- Il mondo si COSTRUISCE, non si cerca (guida pgTAP; D7). Stessa fixture di
-- test-fn-partite-merce-chiusura-v1: cliente e articolo dai builder di dbops,
-- il catalogo per codice_interno.
-- ⚠️ Ordine obbligato: PRIMA il contesto, POI il cliente (il legame BA ->
--    emittente lo scrive il trigger z90 verso chi agisce).
-- ============================================================
CREATE TEMP TABLE tmp_cli_ca AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('pgtap_coda_accrediti');

CREATE TEMP TABLE tmp_refs_ca AS
SELECT
  c.billing_account_id,
  c.utility_id,
  c.istanza_utility_id,
  script.fn_pgtap_emittente_operatore()    AS emittente_fiscale_id,
  script.fn_pgtap_emittente_sr_operatore() AS emittente_sr_id,
  c.soggetto_ruolo_id,
  dbops.fn_pgtap_crea_articolo('PGT-CA-ART', false)                                                  AS articolo_id,
  (SELECT u.id FROM catalogo.unita_misura u WHERE u.attivo IS TRUE ORDER BY u.id LIMIT 1)             AS uom_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1)                                            AS valuta_id,
  (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1)                        AS iva_id,
  -- ⚠️ rev 2026-10-08 (brief-db-righe-e-componenti-debiti-residui, D-1): la testata d'ordine nasce DRAFT,
  --   prende le righe, poi passa a CONFERMATO con dbops.fn_pgtap_porta_a_stato — fuori bozza le
  --   righe non si scrivono piu' (20261008-90).
  (SELECT s.id FROM config.stati_doc_ordini s WHERE s.codice_interno='DRAFT'      AND s.attivo ORDER BY s.id LIMIT 1) AS stato_ord_draft_id,
  (SELECT s.id FROM config.stati_doc_ddt s WHERE s.codice_interno='EMESSO'     AND s.attivo ORDER BY s.id LIMIT 1)    AS stato_ddt_emesso_id,
  (SELECT s.id FROM config.stati_doc_ddt s WHERE s.codice_interno='SPEDITO'    AND s.attivo ORDER BY s.id LIMIT 1)    AS stato_ddt_spedito_id,
  (SELECT s.id FROM config.stati_doc_ddt s WHERE s.codice_interno='CONSEGNATO' AND s.attivo ORDER BY s.id LIMIT 1)    AS stato_ddt_consegnato_id,
  (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno='DDT_VENDITA' AND s.attivo ORDER BY s.id LIMIT 1)        AS sorgente_ddt_id,
  (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno='COMMESSA'    AND s.attivo ORDER BY s.id LIMIT 1)        AS sorgente_root_id,
  (SELECT s.id FROM config.stati_doc_reso s WHERE s.codice_interno='DRAFT' AND s.attivo ORDER BY s.id LIMIT 1)        AS stato_reso_draft_id,
  (SELECT t.id FROM config.tipi_reso t WHERE t.codice_interno='RESO_A_CREDITO'      AND t.attivo ORDER BY t.id LIMIT 1) AS tipo_credito_id,
  (SELECT t.id FROM config.tipi_reso t WHERE t.codice_interno='RESO_PER_RICONSEGNA' AND t.attivo ORDER BY t.id LIMIT 1) AS tipo_riconsegna_id,
  (SELECT t.id FROM config.tipi_doc_fiscale t WHERE t.attivo IS TRUE ORDER BY t.id LIMIT 1)                           AS tipo_doc_fiscale_id,
  (SELECT s.id FROM config.stati_doc_fiscale s WHERE s.codice_interno='DRAFT' AND s.attivo IS TRUE ORDER BY s.id LIMIT 1) AS stato_fatt_draft_id,
  script.fn_pgtap_registro_fattura()                     AS registro_id,
  (SELECT c.id FROM config.causali_trasporto c WHERE c.codice='VENDITA' ORDER BY c.id LIMIT 1)                        AS causale_vendita_id,
  (SELECT id FROM config.tipi_indirizzi WHERE codice_interno='CON')                                                   AS tipo_ind_con_id
FROM tmp_cli_ca c;

-- Commessa + ROOT: serve alle attivita' fatturabili (corsia DDT).
CREATE TEMP TABLE tmp_com_ca AS
SELECT vendite.fn_get_or_create_commessa(
  p_billing_account_id     => (SELECT billing_account_id FROM tmp_refs_ca),
  p_utility_id             => (SELECT utility_id FROM tmp_refs_ca),
  p_tipo_commessa          => 'AUTO',
  p_policy_fatturazione    => 'DA_DOCUMENTO',
  p_fatturazione_immediata => false,
  p_priorita_operativa     => 'NORMALE',
  p_competenza_dal         => DATE '2026-08-01',
  p_competenza_al          => DATE '2026-08-31',
  p_meta                   => jsonb_build_object('test_scope','pgtap_coda_accrediti'),
  p_force_new              => true) AS commessa_id;

SELECT vendite.fn_link_commessa_sorgente(
  p_commessa_id      => (SELECT commessa_id FROM tmp_com_ca),
  p_sorgente_tipo_id => (SELECT sorgente_root_id FROM tmp_refs_ca),
  p_sorgente_uid     => (SELECT commessa_id FROM tmp_com_ca)::text,
  p_sorgente_riga    => 1,
  p_meta             => '{}'::jsonb);

-- ============================================================
-- Helper (padre e figlio in due istruzioni: le CTE che scrivono condividono
-- la snapshot e le policy negano fail-closed)
-- ============================================================

-- Un ordine CONFERMATO con una riga da p_qta.
CREATE OR REPLACE FUNCTION pg_temp.ca_mk_ordine(p_qta numeric)
RETURNS TABLE(ordine_id bigint, ordine_uid uuid, ordine_riga_id bigint) AS $$
DECLARE r RECORD; v_ord bigint; v_uid uuid; v_orr bigint;
BEGIN
  SELECT * INTO r FROM tmp_refs_ca;
  INSERT INTO vendite.ordini (soggetto_ruolo_id, billing_account_id, stato_doc_ordine_id,
    valuta_id, data, fatturazione_trigger, emittente_fiscale_id, storicizza, meta)
  VALUES (r.soggetto_ruolo_id, r.billing_account_id, r.stato_ord_draft_id, r.valuta_id,
          DATE '2026-08-05', 'CONSEGNATO', r.emittente_fiscale_id, false,
          jsonb_build_object('test_scope','pgtap_coda_accrediti'))
  RETURNING id, uid INTO v_ord, v_uid;
  INSERT INTO vendite.ordini_righe (ordine_id, riga_nr, articolo_id, descrizione,
    qta_operativa, quantita, prezzo_unitario, iva_id, attivo, storicizza, meta)
  VALUES (v_ord, 1, r.articolo_id, 'Riga coda accrediti pgTAP', p_qta, p_qta, 20, r.iva_id,
          true, false, jsonb_build_object('test_scope','pgtap_coda_accrediti'))
  RETURNING id INTO v_orr;
  -- ⚠️ rev 2026-10-08 (D-1): righe scritte in bozza, ora la conferma vera (20261008-90).
  PERFORM dbops.fn_pgtap_porta_a_stato('vendite.ordini', v_ord, 'CONFERMATO');
  RETURN QUERY SELECT v_ord, v_uid, v_orr;
END $$ LANGUAGE plpgsql;

-- Un DDT CONSEGNATO che evade p_qta della riga d'ordine.
CREATE OR REPLACE FUNCTION pg_temp.ca_mk_ddt(p_ordine_id bigint, p_ordine_riga_id bigint,
                                             p_qta numeric, p_data date,
                                             p_lega_anche bigint DEFAULT NULL)
RETURNS TABLE(ddt_id bigint, ddt_uid uuid, ddt_riga_id bigint) AS $$
DECLARE r RECORD; v_ddt bigint; v_uid uuid; v_ddtr bigint;
BEGIN
  SELECT * INTO r FROM tmp_refs_ca;
  v_ddt := vendite.fn_genera_ddt_da_ordine(
      p_ordine_id,
      jsonb_build_array(jsonb_build_object('ordine_riga_id', p_ordine_riga_id, 'qta_da_evadere', p_qta)),
      p_data);
  -- ⭐ rev 2026-10-11 (brief-db-ddt-righe-evase-dall-ordine, D-6): un legame
  --   nasce solo con la bolla in bozza. La riga MULTIPLA si lega qui, prima
  --   delle transizioni: dopo la consegna l'INSERT e' E_RIGA_DOC_NON_BOZZA.
  IF p_lega_anche IS NOT NULL THEN
    INSERT INTO vendite.ordini_righe_fulfillment (ordine_riga_id, ddt_riga_id, qta_evasa, storicizza)
    SELECT p_lega_anche, dr.id, dr.quantita, false
      FROM vendite.ddt_righe dr WHERE dr.ddt_id = v_ddt ORDER BY dr.id LIMIT 1;
  END IF;
  INSERT INTO vendite.ddt_indirizzi (ddt_id, tipo_indirizzo_id, snapshot)
  VALUES (v_ddt, r.tipo_ind_con_id, '{"display":"CON"}'::jsonb) ON CONFLICT DO NOTHING;
  UPDATE vendite.ddt SET causale_trasporto_id = r.causale_vendita_id      WHERE id = v_ddt;
  UPDATE vendite.ddt SET stato_doc_ddt_id     = r.stato_ddt_emesso_id     WHERE id = v_ddt;
  UPDATE vendite.ddt SET stato_doc_ddt_id     = r.stato_ddt_spedito_id    WHERE id = v_ddt;
  UPDATE vendite.ddt SET stato_doc_ddt_id     = r.stato_ddt_consegnato_id WHERE id = v_ddt;
  SELECT d.uid INTO v_uid  FROM vendite.ddt d        WHERE d.id = v_ddt;
  SELECT dr.id INTO v_ddtr FROM vendite.ddt_righe dr WHERE dr.ddt_id = v_ddt ORDER BY dr.id LIMIT 1;
  RETURN QUERY SELECT v_ddt, v_uid, v_ddtr;
END $$ LANGUAGE plpgsql;

-- Un'attivita' fatturabile NORMALE sul segmento dato.
CREATE OR REPLACE FUNCTION pg_temp.ca_mk_af(p_segment varchar, p_qta numeric)
RETURNS void AS $$
DECLARE r RECORD;
BEGIN
  SELECT * INTO r FROM tmp_refs_ca;
  PERFORM vendite.fn_upsert_commessa_attivita(
    p_commessa_id => (SELECT commessa_id FROM tmp_com_ca),
    -- La riga NORMALE ha la sua sorgente (vincolo 20261012-27).
    p_sorgente_tipo_id => (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'COMMESSA'),
    p_sorgente_uid => ((SELECT commessa_id FROM tmp_com_ca))::text,
    p_segment_key => p_segment, p_articolo_id => r.articolo_id,
    p_istanza_utility_id => r.istanza_utility_id, p_data_attivita => DATE '2026-08-15',
    p_uom_id => r.uom_id, p_quantita => p_qta,
    p_competenza_mese => DATE '2026-08-01',
    p_competenza_dal => DATE '2026-08-01', p_competenza_al => DATE '2026-08-31',
    p_prezzo_snapshot => 20, p_prezzo_base_snapshot => NULL, p_origine_prezzo => NULL,
    p_tipo_variazione_applicata => NULL, p_valore_variazione_applicata => NULL,
    p_promo_id => NULL, p_contratto_id => NULL,
    p_categoria_cliente_id_snapshot => NULL, p_classe_utenza_id_snapshot => NULL,
    p_tipo_doc_fiscale_id => r.tipo_doc_fiscale_id, p_valuta_id => r.valuta_id,
    p_stato_approvazione => 'APPROVATA', p_stato_emissione => 'NON_EMESSA',
    p_tipo_movimento => 'NORMALE');
  PERFORM vendite.fn_emit_attivita_fatturabili_da_commessa((SELECT commessa_id FROM tmp_com_ca), true, false);
END $$ LANGUAGE plpgsql;

-- Una FATTURA sul segmento DDT (l'accredito copia il prezzo da fatture_righe).
CREATE OR REPLACE FUNCTION pg_temp.ca_fattura(p_segment varchar, p_qta numeric)
RETURNS bigint AS $$
DECLARE r RECORD; v_af bigint; v_fatt bigint; v_riga bigint;
BEGIN
  SELECT * INTO r FROM tmp_refs_ca;
  PERFORM pg_temp.ca_mk_af(p_segment, p_qta);
  SELECT af.id INTO v_af
    FROM vendite.attivita_fatturabili af
    JOIN vendite.commesse_attivita ca ON ca.id = af.commessa_attivita_id
   WHERE ca.segment_key = p_segment ORDER BY af.id DESC LIMIT 1;
  INSERT INTO vendite.fatture (registro_id, data, tipo_doc_fiscale_id, stato_doc_fiscale_id,
      emittente_soggetto_ruolo_id, billing_account_id, utility_id, valuta_id, tasso_cambio, meta)
  VALUES (r.registro_id, DATE '2026-08-31', r.tipo_doc_fiscale_id, r.stato_fatt_draft_id,
      r.emittente_sr_id, r.billing_account_id, r.utility_id, r.valuta_id, 1,
      jsonb_build_object('test_scope','pgtap_coda_accrediti'))
  RETURNING id INTO v_fatt;
  INSERT INTO vendite.fatture_righe (fattura_id, riga_nr, articolo_id, descrizione,
      uom_id, qta, prezzo_unitario, iva_id, imponibile_riga, competenza_dal, competenza_al)
  VALUES (v_fatt, 1, r.articolo_id, 'Riga fattura pgTAP', r.uom_id, p_qta, 20,
      r.iva_id, p_qta * 20, script.fn_data_operativa(), script.fn_data_operativa())
  RETURNING id INTO v_riga;
  UPDATE vendite.attivita_fatturabili SET fattura_riga_id = v_riga WHERE id = v_af;
  RETURN v_riga;
END $$ LANGUAGE plpgsql;

-- Un reso del tipo dato, confermato.
CREATE OR REPLACE FUNCTION pg_temp.ca_mk_reso(p_ddt_riga bigint, p_ddt_uid uuid, p_qta numeric, p_tipo_id bigint)
RETURNS TABLE(reso_id bigint, resi_riga_id bigint) AS $$
DECLARE r RECORD; v_reso bigint; v_riga bigint;
BEGIN
  SELECT * INTO r FROM tmp_refs_ca;
  INSERT INTO vendite.resi (stato_doc_reso_id, sorgente_tipo_id, sorgente_uid, storicizza, meta)
  VALUES (r.stato_reso_draft_id, r.sorgente_ddt_id, p_ddt_uid, false,
          jsonb_build_object('test_scope','pgtap_coda_accrediti'))
  RETURNING id INTO v_reso;
  INSERT INTO vendite.resi_righe (reso_id, riga_nr, ddt_riga_id, ordine_riga_id,
      articolo_id, descrizione, qta_operativa, uom_operativa_id, factor_to_base,
      tipo_reso_id, storicizza)
  SELECT v_reso, 1, dr.id,
         (SELECT f.ordine_riga_id FROM vendite.ordini_righe_fulfillment f
           WHERE f.ddt_riga_id = dr.id ORDER BY f.id LIMIT 1),
         dr.articolo_id, dr.descrizione, p_qta, dr.uom_operativa_id, dr.factor_to_base,
         p_tipo_id, false
    FROM vendite.ddt_righe dr WHERE dr.id = p_ddt_riga
  RETURNING id INTO v_riga;
  PERFORM vendite.fn_conferma_reso(v_reso);
  RETURN QUERY SELECT v_reso, v_riga;
END $$ LANGUAGE plpgsql;

-- Il confronto fn(seme) = vista filtrata COME LA FILTRA IL BACKEND (il BB
-- filtro_coda_per_documento), nei DUE versi.
CREATE OR REPLACE FUNCTION pg_temp.ca_diff_ddt(p_ddt bigint) RETURNS bigint AS $$
  SELECT (SELECT count(*) FROM (SELECT * FROM vendite.fn_resi_da_accreditare(ARRAY[p_ddt], NULL)
                                 EXCEPT ALL
                                SELECT * FROM vendite.vw_resi_da_accreditare v WHERE v.ddt_id = p_ddt) a)
       + (SELECT count(*) FROM (SELECT * FROM vendite.vw_resi_da_accreditare v WHERE v.ddt_id = p_ddt
                                 EXCEPT ALL
                                SELECT * FROM vendite.fn_resi_da_accreditare(ARRAY[p_ddt], NULL)) b);
$$ LANGUAGE sql;

CREATE OR REPLACE FUNCTION pg_temp.ca_diff_ordine(p_ord bigint) RETURNS bigint AS $$
  WITH v AS (
    SELECT q.* FROM vendite.vw_resi_da_accreditare q
     WHERE EXISTS (SELECT 1 FROM vendite.ordini_righe_fulfillment f
                     JOIN vendite.ordini_righe orr ON orr.id = f.ordine_riga_id
                    WHERE f.ddt_riga_id = q.ddt_riga_id AND orr.ordine_id = p_ord))
  SELECT (SELECT count(*) FROM (SELECT * FROM vendite.fn_resi_da_accreditare(NULL, ARRAY[p_ord])
                                 EXCEPT ALL SELECT * FROM v) a)
       + (SELECT count(*) FROM (SELECT * FROM v
                                 EXCEPT ALL SELECT * FROM vendite.fn_resi_da_accreditare(NULL, ARRAY[p_ord])) b);
$$ LANGUAGE sql;

-- ============================================================
-- CASO 1 — LE SORELLE. Partita da 10 fatturata 6 (corsia DDT); due resi A
--          CREDITO sulla stessa riga: A 4, poi B 3. tenuti 3, fatturati 6:
--          capienza 3. La greedy per resi_riga_id da' 3 ad A e 0 a B.
-- ============================================================
CREATE TEMP TABLE tmp_o1 AS SELECT * FROM pg_temp.ca_mk_ordine(10);
CREATE TEMP TABLE tmp_ob AS SELECT * FROM pg_temp.ca_mk_ordine(10);
CREATE TEMP TABLE tmp_p AS SELECT * FROM pg_temp.ca_mk_ddt((SELECT ordine_id FROM tmp_o1), (SELECT ordine_riga_id FROM tmp_o1), 10, DATE '2026-08-13',
                                                       (SELECT ordine_riga_id FROM tmp_ob));
CREATE TEMP TABLE tmp_fr AS SELECT pg_temp.ca_fattura(script.fn_segment_key('DDT_VENDITA', (SELECT ddt_uid FROM tmp_p)::text, (SELECT ddt_riga_id FROM tmp_p)), 6) AS fattura_riga_id;
CREATE TEMP TABLE tmp_ra AS SELECT * FROM pg_temp.ca_mk_reso((SELECT ddt_riga_id FROM tmp_p), (SELECT ddt_uid FROM tmp_p), 4, (SELECT tipo_credito_id FROM tmp_refs_ca));
CREATE TEMP TABLE tmp_rb AS SELECT * FROM pg_temp.ca_mk_reso((SELECT ddt_riga_id FROM tmp_p), (SELECT ddt_uid FROM tmp_p), 3, (SELECT tipo_credito_id FROM tmp_refs_ca));

SELECT results_eq(
  $q$SELECT q.resi_riga_id = (SELECT resi_riga_id FROM tmp_ra), q.accredito_dovuto, q.etichetta::text, q.tenuti, q.fatturati
       FROM vendite.fn_resi_da_accreditare(ARRAY[(SELECT ddt_id FROM tmp_p)], NULL) q$q$,
  $q$VALUES (true, 3::numeric, 'DOVUTA', 3::numeric, 6::numeric)$q$,
  '4) le sorelle: per il DDT la coda ha UNA riga — A con 3 (DOVUTA); B resta fuori perche'' A ha preso la capienza');

-- ⭐ Il guard del ponte legge la coda attraverso la funzione: 3 per A, 0 per B.
--    Senza la sorella A nella finestra, B da sola leggerebbe 3.
SELECT results_eq(
  $q$SELECT (SELECT t.accredito_dovuto FROM vendite.fn_resi_riga_tetti_accredito((SELECT resi_riga_id FROM tmp_ra), (SELECT fattura_riga_id FROM tmp_fr)) t),
            (SELECT t.accredito_dovuto FROM vendite.fn_resi_riga_tetti_accredito((SELECT resi_riga_id FROM tmp_rb), (SELECT fattura_riga_id FROM tmp_fr)) t),
            (SELECT t.qta_riga_fattura   FROM vendite.fn_resi_riga_tetti_accredito((SELECT resi_riga_id FROM tmp_ra), (SELECT fattura_riga_id FROM tmp_fr)) t)$q$,
  $q$VALUES (3::numeric, 0::numeric, 6::numeric)$q$,
  '5) il tetto attraverso la funzione: 3 per A, 0 per B (fail-closed), 6 sulla riga di fattura');

SELECT is(
  pg_temp.ca_diff_ddt((SELECT ddt_id FROM tmp_p)) + pg_temp.ca_diff_ordine((SELECT ordine_id FROM tmp_o1)),
  0::bigint,
  '6) per DDT e per ordine la coda e'' identica alla vista filtrata come la filtra il backend, nei due versi');

-- ============================================================
-- CASO 2 — la riga MULTIPLA: la riga di DDT evade ANCHE un ordine B2 (id
--          maggiore). Nella coda di B2 c'e' (fulfillment); nella partita per
--          B2 no (ordine_id = riga minima). Due semantiche, di proposito.
-- ============================================================
-- (il legame con B2 nasce con la bolla in bozza: pg_temp.ca_mk_ddt, D-6 del 2026-10-11)

SELECT results_eq(
  $q$SELECT (SELECT count(*)::int FROM vendite.fn_resi_da_accreditare(NULL, ARRAY[(SELECT ordine_id FROM tmp_ob)])),
            (SELECT count(*)::int FROM vendite.fn_partite_merce(NULL, ARRAY[(SELECT ordine_id FROM tmp_ob)])),
            pg_temp.ca_diff_ordine((SELECT ordine_id FROM tmp_ob))$q$,
  $q$VALUES (1, 0, 0::bigint)$q$,
  '7) riga MULTIPLA: la coda per l''ordine B2 la contiene (predicato del backend), la partita per B2 no (riga minima); identica alla vista');

-- ============================================================
-- CASO 3 — il verbo attraverso la funzione: accredita A, e A esce dalla coda.
-- ============================================================
CREATE TEMP TABLE tmp_acc AS SELECT * FROM vendite.fn_accredita_riga_reso((SELECT resi_riga_id FROM tmp_ra));
-- La RETTIFICA scritta in commessa entra nel conto quando diventa attivita'
-- fatturabile (come nel flusso: l'emissione segue il verbo).
SELECT vendite.fn_emit_attivita_fatturabili_da_commessa((SELECT commessa_id FROM tmp_com_ca), true, false);

SELECT results_eq(
  $q$SELECT (SELECT sum(a.qta_partita) FROM tmp_acc a),
            (SELECT count(*)::int FROM vendite.fn_resi_da_accreditare(ARRAY[(SELECT ddt_id FROM tmp_p)], NULL)),
            (SELECT count(*)::int FROM vendite.vw_resi_da_accreditare v WHERE v.ddt_id = (SELECT ddt_id FROM tmp_p)),
            vendite.fn_resi_riga_accreditato_partita((SELECT resi_riga_id FROM tmp_ra))$q$,
  $q$VALUES (3::numeric, 0, 0, 3::numeric)$q$,
  '8) il verbo: accredita A per 3 (qta_partita); con la rettifica emessa la partita pareggia e la coda del DDT e'' vuota — per la funzione come per la vista');

-- ============================================================
-- CASO 4 — FACOLTATIVA: partita da 5 fatturata 5, reso PER RI-CONSEGNA 2 con
--          residuo aperto: tenuti 3, fatturati 5 → 2 in coda, FACOLTATIVA.
-- ============================================================
CREATE TEMP TABLE tmp_o3 AS SELECT * FROM pg_temp.ca_mk_ordine(5);
CREATE TEMP TABLE tmp_p3 AS SELECT * FROM pg_temp.ca_mk_ddt((SELECT ordine_id FROM tmp_o3), (SELECT ordine_riga_id FROM tmp_o3), 5, DATE '2026-08-14');
SELECT pg_temp.ca_fattura(script.fn_segment_key('DDT_VENDITA', (SELECT ddt_uid FROM tmp_p3)::text, (SELECT ddt_riga_id FROM tmp_p3)), 5);
CREATE TEMP TABLE tmp_rc AS SELECT * FROM pg_temp.ca_mk_reso((SELECT ddt_riga_id FROM tmp_p3), (SELECT ddt_uid FROM tmp_p3), 2, (SELECT tipo_riconsegna_id FROM tmp_refs_ca));

SELECT results_eq(
  $q$SELECT q.accredito_dovuto, q.etichetta::text, q.blocco_codice IS NULL, pg_temp.ca_diff_ddt((SELECT ddt_id FROM tmp_p3))
       FROM vendite.fn_resi_da_accreditare(ARRAY[(SELECT ddt_id FROM tmp_p3)], NULL) q$q$,
  $q$VALUES (2::numeric, 'FACOLTATIVA', true, 0::bigint)$q$,
  '9) reso per ri-consegna con residuo aperto su partita fatturata: 2 in coda, FACOLTATIVA, identica alla vista');

-- ============================================================
-- CASO 5 — niente in coda: reso su una partita NON fatturata (differenza
--          positiva), id inesistente, array vuoto.
-- ============================================================
CREATE TEMP TABLE tmp_o4 AS SELECT * FROM pg_temp.ca_mk_ordine(5);
CREATE TEMP TABLE tmp_p4 AS SELECT * FROM pg_temp.ca_mk_ddt((SELECT ordine_id FROM tmp_o4), (SELECT ordine_riga_id FROM tmp_o4), 5, DATE '2026-08-15');
CREATE TEMP TABLE tmp_rd AS SELECT * FROM pg_temp.ca_mk_reso((SELECT ddt_riga_id FROM tmp_p4), (SELECT ddt_uid FROM tmp_p4), 2, (SELECT tipo_credito_id FROM tmp_refs_ca));

SELECT is(
  (SELECT count(*) FROM vendite.fn_resi_da_accreditare(ARRAY[(SELECT ddt_id FROM tmp_p4)], NULL))::text
  || '|' || (SELECT count(*) FROM vendite.fn_resi_da_accreditare(ARRAY[-1], NULL))::text
  || '|' || (SELECT count(*) FROM vendite.fn_resi_da_accreditare(NULL, ARRAY[-1]))::text
  || '|' || (SELECT count(*) FROM vendite.fn_resi_da_accreditare(ARRAY[]::bigint[], ARRAY[]::bigint[]))::text,
  '0|0|0|0',
  '10) reso su partita non fatturata, id inesistente, array VUOTO: zero righe — vuoto non e'' «tutte»');

SELECT is(
  (SELECT count(*) FROM vendite.fn_resi_da_accreditare(NULL, NULL)),
  (SELECT count(*) FROM vendite.vw_resi_da_accreditare),
  '11) (NULL, NULL) e'' la vista: lo stesso numero di righe');

-- ============================================================
-- 12) Scope: chi non vede il documento non vede la coda.
-- ⚠️ Con la veste OPERATORE e un utente senza whitelist la RLS non fa vedere
--    il DDT, e la funzione — INVOKER — risponde ZERO righe.
-- ============================================================
SELECT set_config('app.current_user_id', '999999999', true);

SELECT is(
  (SELECT count(*) FROM vendite.fn_resi_da_accreditare(ARRAY[(SELECT ddt_id FROM tmp_p3)], NULL)),
  0::bigint,
  '12) scope che non vede il DDT: la coda sparisce, non esce con dei conti a zero');

SELECT * FROM finish();
ROLLBACK;
