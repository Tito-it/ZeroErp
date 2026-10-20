-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: vendite.fn_partite_merce — la partita di merce PER DOCUMENTO
--       (D14 quarta leva; brief-db-partita-merce-per-documento §2, §2-bis, §3;
--        changeSet 20260921-21..-24).
--
-- Indice test (plan 16):
--   1) la funzione esiste, e' BEGIN ATOMIC (dipendenze nel catalogo) e NON e'
--      SECURITY DEFINER (la RLS resta di chi legge)
--   2) ⭐ pin di D1: la vista e' la PROIEZIONE della funzione — nomina
--      fn_partite_merce e nessuna tabella
--   3) ⭐ pin dei tipi: 23 colonne e `consegnato` numeric(18,6) — un SELECT *
--      dalla funzione lo perderebbe in silenzio (§2-bis.1)
--   4) ⭐ R1 E' INDISPENSABILE: ordine su tre DDT, fatturato d'ordine 15; il
--      solo DDT DI MEZZO deve dare fatturato_da_ordine 5 (la greedy versa nel
--      piu' vecchio: senza R1 il DDT di mezzo si crederebbe primo e direbbe 10)
--   5) ...e la riga e' IDENTICA alla vista filtrata (EXCEPT ALL nei due versi)
--   6) il terzo DDT non prende niente: fatturato_da_ordine 0, differenza 10
--   7) seme per ORDINE: fn(NULL, ARRAY[o]) = 3 righe = vista WHERE ordine_id = o
--   8) ⭐ LE SORELLE SERVONO: reso per ri-consegna con accredito PARZIALE (1 su
--      5 resi) e due ri-spedizioni (3, poi 2): la SECONDA chiesta da sola deve
--      dare quota 0 / RICONSEGNA — senza la sorella prenderebbe 1
--   9) la prima ri-spedizione prende la quota 1: DA_FATTURARE per 1
--  10) l'origine, chiesta da sola: consegnato 10 + 5 - 1 = 14, identica alla vista
--  11) la riga a mano su un DDT misto: sospetto_duplicato_ordine acceso e
--      origine NESSUNA anche per la chiusura
--  12) niente da seminare: DDT in bozza, id inesistente, array VUOTO -> zero
--      righe (vuoto NON e' «tutte»)
--  13) ⭐ riga MULTIPLA (evade due ordini): esce SOLO sotto l'ordine della riga
--      minima — il filtro d'uscita e' sulla colonna proiettata (§2-bis.7)
--  14) scope: chi non vede il documento non vede la partita — zero righe, non
--      conti a zero
--  15) ⭐ un ONERE sul segmento ORD della stessa riga NON entra nel fatturato
--      della partita (tipo_movimento = 'NORMALE'): fatturata via DDT per 10,
--      fatturato_da_ordine 0 e non 5, differenza 0 e non -5 — ereditato il
--      22-09 da test-vw-contatore-merce-v1 (ritirato con la vista, D6): era il
--      solo presidio di questa cintura
--  16) ⭐ la riga che evade UNA riga d'ordine ha origine ORDINE_VENDITA, il
--      codice della sorgente, e il codice esiste in config.sorgenti (rev
--      2026-10-20, 20261020-24, brief-db-grammatica-unica-documenti §12.8:
--      prima era il codice corto ORDINE; rosso senza il changeSet)
--
-- Scopo:
--  - la chiusura e' «equivalente per costruzione» alla vista; questo file la
--    prova COSTRUENDO i casi in cui, senza un pezzo della chiusura, il numero
--    sarebbe sbagliato (4, 8, 13). Un EXCEPT ALL sulle righe di oggi non lo
--    farebbe: il dato vivo non ha ordini su tre DDT ne' accrediti parziali.
--  - il 2 e il 3 sono pin di FORMA: D1 (un corpo) e il contratto dei tipi.
--    Il confronto fn(NULL,NULL) = vista sarebbe tautologico (§2-bis.6).
--  - ⛔ chi aggiunge alla partita una finestra con una chiave nuova deve
--    allargare la chiusura E costruire qui il caso che la richiede.
--  - ⭐ il mondo (cliente, articolo) e' COSTRUITO dai builder di dbops, non
--    cercato: il file deve girare identico su dbdev e su un database da zero
--    (CI). Rev 2026-09-21: nato con la fixture «pesca un BA» dei gemelli,
--    moriva sullo scratch zeroerp_ci dopo i tre pin di forma.
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

SELECT plan(16);

-- ⛔ Niente `SET LOCAL app.current_user_id = '1'` dopo la riga di contesto:
--    l'operatore lo sceglie (o lo COSTRUISCE, su un database vuoto)
--    fn_pgtap_set_contesto_operatore, e l'utente 1 in CI non esiste (D7).

-- ============================================================
-- 1-3) Struttura: funzione, pin di D1, pin dei tipi
-- ============================================================
SELECT ok(
  (SELECT p.prosqlbody IS NOT NULL AND NOT p.prosecdef
     FROM pg_proc p
    WHERE p.proname = 'fn_partite_merce' AND p.pronamespace = 'vendite'::regnamespace),
  '1) fn_partite_merce esiste, e'' BEGIN ATOMIC (dipendenze in pg_depend) e non e'' SECURITY DEFINER');

-- ⭐ D1, un corpo: la vista non ha un calcolo suo. Si legge la FORMA, non le
--    righe — fn(NULL,NULL) confrontata con la vista sarebbe la stessa query.
SELECT ok(
  (SELECT d ~ 'fn_partite_merce' AND d !~ 'vendite\.ddt_righe' AND d !~ 'vw_af_merce_per_riga'
     FROM pg_get_viewdef('vendite.vw_partite_merce'::regclass, true) AS d),
  '2) la vista e'' la proiezione di fn_partite_merce: nomina la funzione e nessuna tabella');

-- ⭐ Il typmod. RETURNS TABLE lo perde; la vista lo tiene col cast per nome.
SELECT is(
  (SELECT count(*)::int || '|' || max(format_type(a.atttypid, a.atttypmod)) FILTER (WHERE a.attname = 'consegnato')
     FROM pg_attribute a
    WHERE a.attrelid = 'vendite.vw_partite_merce'::regclass AND a.attnum > 0 AND NOT a.attisdropped),
  '23|numeric(18,6)',
  '3) la vista ha 23 colonne e consegnato resta numeric(18,6)');

-- ============================================================
-- Il mondo si COSTRUISCE, non si cerca (guida pgTAP). Su un database da
-- zero `anagrafiche.*` e' vuoto: la prima corsa sullo scratch zeroerp_ci
-- (2026-09-21) moriva qui — `p_billing_account_id` NULL, tre asserzioni su
-- quattordici — come i sei gemelli della partita gia' in baseline-rossi-ci
-- (D7). Cliente e articolo li fabbricano i builder di dbops; il catalogo si
-- legge per codice_interno.
-- ⚠️ Ordine obbligato: PRIMA il contesto (la riga in testa), POI il cliente.
--    Come zeroerp_app il legame BA -> emittente lo scrive il trigger z90
--    verso l'emittente di chi agisce: e' lo stesso che rispondono
--    fn_pgtap_emittente_operatore / _sr_operatore, quindi la terna
--    emittente / BA / registro e' scelta INSIEME, non a pescate.
-- ⚠️ L'articolo NON gestito a magazzino: il ciclo DDT non tocca il ledger e
--    la partita conta merce, non giacenza. Pescarne uno dal catalogo, su un
--    DB da zero, darebbe un ONERE_* (gli unici a seed), che e' sourceless.
-- ============================================================
CREATE TEMP TABLE tmp_cli_ch AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('pgtap_chiusura');

CREATE TEMP TABLE tmp_refs_ch AS
SELECT
  c.billing_account_id,
  c.utility_id,
  c.istanza_utility_id,
  script.fn_pgtap_emittente_operatore()    AS emittente_fiscale_id,
  script.fn_pgtap_emittente_sr_operatore() AS emittente_sr_id,
  c.soggetto_ruolo_id,
  dbops.fn_pgtap_crea_articolo('PGT-CH-ART', false)                                                  AS articolo_id,
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
  (SELECT t.id FROM config.tipi_reso t WHERE t.codice_interno='RESO_PER_RICONSEGNA' AND t.attivo ORDER BY t.id LIMIT 1) AS tipo_riconsegna_id,
  (SELECT t.id FROM config.tipi_doc_fiscale t WHERE t.attivo IS TRUE ORDER BY t.id LIMIT 1)                           AS tipo_doc_fiscale_id,
  (SELECT s.id FROM config.stati_doc_fiscale s WHERE s.codice_interno='DRAFT' AND s.attivo IS TRUE ORDER BY s.id LIMIT 1) AS stato_fatt_draft_id,
  script.fn_pgtap_registro_fattura()                     AS registro_id,
  (SELECT c.id FROM config.causali_trasporto c WHERE c.codice='VENDITA' ORDER BY c.id LIMIT 1)                        AS causale_vendita_id,
  (SELECT id FROM config.tipi_indirizzi WHERE codice_interno='CON')                                                   AS tipo_ind_con_id
FROM tmp_cli_ch c;

-- Commessa + ROOT: serve alle attivita' fatturabili (corsia ORD e DDT).
CREATE TEMP TABLE tmp_com_ch AS
SELECT vendite.fn_get_or_create_commessa(
  p_billing_account_id     => (SELECT billing_account_id FROM tmp_refs_ch),
  p_utility_id             => (SELECT utility_id FROM tmp_refs_ch),
  p_tipo_commessa          => 'AUTO',
  p_policy_fatturazione    => 'DA_DOCUMENTO',
  p_fatturazione_immediata => false,
  p_priorita_operativa     => 'NORMALE',
  p_competenza_dal         => DATE '2026-08-01',
  p_competenza_al          => DATE '2026-08-31',
  p_meta                   => jsonb_build_object('test_scope','pgtap_chiusura'),
  p_force_new              => true) AS commessa_id;

SELECT vendite.fn_link_commessa_sorgente(
  p_commessa_id      => (SELECT commessa_id FROM tmp_com_ch),
  p_sorgente_tipo_id => (SELECT sorgente_root_id FROM tmp_refs_ch),
  p_sorgente_uid     => (SELECT commessa_id FROM tmp_com_ch)::text,
  p_sorgente_riga    => 1,
  p_meta             => '{}'::jsonb);

-- ============================================================
-- Helper (padre e figlio in due istruzioni: le CTE che scrivono condividono
-- la snapshot e le policy negano fail-closed)
-- ============================================================

-- Un ordine CONFERMATO con una riga da p_qta.
CREATE OR REPLACE FUNCTION pg_temp.ch_mk_ordine(p_qta numeric)
RETURNS TABLE(ordine_id bigint, ordine_uid uuid, ordine_riga_id bigint) AS $$
DECLARE r RECORD; v_ord bigint; v_uid uuid; v_orr bigint;
BEGIN
  SELECT * INTO r FROM tmp_refs_ch;
  INSERT INTO vendite.ordini (soggetto_ruolo_id, billing_account_id, stato_doc_ordine_id,
    valuta_id, data, fatturazione_trigger, emittente_fiscale_id, storicizza, meta)
  VALUES (r.soggetto_ruolo_id, r.billing_account_id, r.stato_ord_draft_id, r.valuta_id,
          DATE '2026-08-05', 'CONSEGNATO', r.emittente_fiscale_id, false,
          jsonb_build_object('test_scope','pgtap_chiusura'))
  RETURNING id, uid INTO v_ord, v_uid;
  UPDATE vendite.ordini SET fatturazione_trigger = 'CONSEGNATO' WHERE id = v_ord;
  INSERT INTO vendite.ordini_righe (ordine_id, riga_nr, articolo_id, descrizione,
    qta_operativa, quantita, prezzo_unitario, iva_id, attivo, storicizza, meta)
  VALUES (v_ord, 1, r.articolo_id, 'Riga chiusura pgTAP', p_qta, p_qta, 20, r.iva_id,
          true, false, jsonb_build_object('test_scope','pgtap_chiusura'))
  RETURNING id INTO v_orr;
  -- ⚠️ rev 2026-10-08 (D-1): righe scritte in bozza, ora la conferma vera (20261008-90).
  PERFORM dbops.fn_pgtap_porta_a_stato('vendite.ordini', v_ord, 'CONFERMATO');
  RETURN QUERY SELECT v_ord, v_uid, v_orr;
END $$ LANGUAGE plpgsql;

-- Un DDT CONSEGNATO che evade p_qta della riga d'ordine, alla data p_data.
-- La data e' la chiave della greedy `alloc` (oldest-first): va scelta.
-- `p_riga_manuale` (rev 2026-09-22): la riga aggiunta A MANO (caso 3) entra
-- PRIMA delle transizioni — il BB trgfn_doc_righe_lock_fuori_bozza non
-- ammette righe in un DDT fuori bozza.
CREATE OR REPLACE FUNCTION pg_temp.ch_mk_ddt(p_ordine_id bigint, p_ordine_riga_id bigint,
                                             p_qta numeric, p_data date,
                                             p_riga_manuale numeric DEFAULT NULL,
                                             p_lega_anche bigint DEFAULT NULL)
RETURNS TABLE(ddt_id bigint, ddt_uid uuid, ddt_riga_id bigint) AS $$
DECLARE r RECORD; v_ddt bigint; v_uid uuid; v_ddtr bigint;
BEGIN
  SELECT * INTO r FROM tmp_refs_ch;
  v_ddt := vendite.fn_genera_ddt_da_ordine(
      p_ordine_id,
      jsonb_build_array(jsonb_build_object('ordine_riga_id', p_ordine_riga_id, 'qta_da_evadere', p_qta)),
      p_data);
  INSERT INTO vendite.ddt_indirizzi (ddt_id, tipo_indirizzo_id, snapshot)
  VALUES (v_ddt, r.tipo_ind_con_id, '{"display":"CON"}'::jsonb) ON CONFLICT DO NOTHING;
  UPDATE vendite.ddt SET causale_trasporto_id = r.causale_vendita_id      WHERE id = v_ddt;
  IF p_riga_manuale IS NOT NULL THEN
    INSERT INTO vendite.ddt_righe (ddt_id, riga_nr, articolo_id, descrizione,
        qta_operativa, quantita, prezzo_unitario, iva_id, attivo, storicizza, meta)
    VALUES (v_ddt, 900, r.articolo_id, 'Riga aggiunta a mano', p_riga_manuale, p_riga_manuale, 20, r.iva_id,
            true, false, jsonb_build_object('test_scope','pgtap_chiusura'));
  END IF;
  -- ⭐ rev 2026-10-11 (brief-db-ddt-righe-evase-dall-ordine, D-6): un legame
  --   nasce solo con la bolla in bozza. La riga MULTIPLA si lega qui, prima
  --   delle transizioni: dopo la consegna l'INSERT e' E_RIGA_DOC_NON_BOZZA.
  IF p_lega_anche IS NOT NULL THEN
    INSERT INTO vendite.ordini_righe_fulfillment (ordine_riga_id, ddt_riga_id, qta_evasa, storicizza)
    SELECT p_lega_anche, dr.id, dr.quantita, false
      FROM vendite.ddt_righe dr WHERE dr.ddt_id = v_ddt ORDER BY dr.id LIMIT 1;
  END IF;
  UPDATE vendite.ddt SET stato_doc_ddt_id     = r.stato_ddt_emesso_id     WHERE id = v_ddt;
  UPDATE vendite.ddt SET stato_doc_ddt_id     = r.stato_ddt_spedito_id    WHERE id = v_ddt;
  UPDATE vendite.ddt SET stato_doc_ddt_id     = r.stato_ddt_consegnato_id WHERE id = v_ddt;
  SELECT d.uid INTO v_uid  FROM vendite.ddt d        WHERE d.id = v_ddt;
  SELECT dr.id INTO v_ddtr FROM vendite.ddt_righe dr WHERE dr.ddt_id = v_ddt ORDER BY dr.id LIMIT 1;
  RETURN QUERY SELECT v_ddt, v_uid, v_ddtr;
END $$ LANGUAGE plpgsql;

-- Un DDT lasciato in BOZZA (serve al 12).
CREATE OR REPLACE FUNCTION pg_temp.ch_mk_ddt_bozza(p_ordine_id bigint, p_ordine_riga_id bigint, p_qta numeric)
RETURNS bigint AS $$
DECLARE v_ddt bigint;
BEGIN
  v_ddt := vendite.fn_genera_ddt_da_ordine(
      p_ordine_id,
      jsonb_build_array(jsonb_build_object('ordine_riga_id', p_ordine_riga_id, 'qta_da_evadere', p_qta)),
      DATE '2026-08-20');
  RETURN v_ddt;
END $$ LANGUAGE plpgsql;

-- Un'attivita' fatturabile sul segmento dato (corsia ORD o DDT): NORMALE, o
-- ONERE (caso 5) — la causale e' obbligatoria se e solo se tipo_movimento =
-- 'ONERE' (chk_commesse_attivita_causale_onere); si legge dal catalogo seed.
CREATE OR REPLACE FUNCTION pg_temp.ch_mk_af(p_segment varchar, p_qta numeric,
                                            p_tipo_mov varchar DEFAULT 'NORMALE')
RETURNS void AS $$
DECLARE r RECORD; v_causale_id bigint;
BEGIN
  SELECT * INTO r FROM tmp_refs_ch;
  IF p_tipo_mov = 'ONERE' THEN
    SELECT c.id INTO v_causale_id FROM config.causali_onere c WHERE c.attivo ORDER BY c.id LIMIT 1;
  END IF;
  PERFORM vendite.fn_upsert_commessa_attivita(
    p_commessa_id => (SELECT commessa_id FROM tmp_com_ch),
    -- La riga NORMALE ha la sua sorgente; ONERE e RETTIFICA no (vincolo 20261012-27).
    p_sorgente_tipo_id => CASE WHEN p_tipo_mov = 'NORMALE' THEN (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'COMMESSA') END,
    p_sorgente_uid => CASE WHEN p_tipo_mov = 'NORMALE' THEN ((SELECT commessa_id FROM tmp_com_ch))::text END,
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
    p_tipo_movimento => p_tipo_mov, p_causale_onere_id => v_causale_id);
  PERFORM vendite.fn_emit_attivita_fatturabili_da_commessa((SELECT commessa_id FROM tmp_com_ch), true, false);
END $$ LANGUAGE plpgsql;

-- Una FATTURA sul segmento DDT (serve all'accredito, che copia il prezzo da
-- fatture_righe): stessa forma di test-vw-partite-merce-riconsegna-dopo-nc-v1.
CREATE OR REPLACE FUNCTION pg_temp.ch_fattura(p_segment varchar, p_qta numeric)
RETURNS bigint AS $$
DECLARE r RECORD; v_af bigint; v_fatt bigint; v_riga bigint;
BEGIN
  SELECT * INTO r FROM tmp_refs_ch;
  PERFORM pg_temp.ch_mk_af(p_segment, p_qta);
  SELECT af.id INTO v_af
    FROM vendite.attivita_fatturabili af
    JOIN vendite.commesse_attivita ca ON ca.id = af.commessa_attivita_id
   WHERE ca.segment_key = p_segment ORDER BY af.id DESC LIMIT 1;
  INSERT INTO vendite.fatture (registro_id, data, tipo_doc_fiscale_id, stato_doc_fiscale_id,
      emittente_soggetto_ruolo_id, billing_account_id, utility_id, valuta_id, tasso_cambio, meta)
  VALUES (r.registro_id, DATE '2026-08-31', r.tipo_doc_fiscale_id, r.stato_fatt_draft_id,
      r.emittente_sr_id, r.billing_account_id, r.utility_id, r.valuta_id, 1,
      jsonb_build_object('test_scope','pgtap_chiusura'))
  RETURNING id INTO v_fatt;
  INSERT INTO vendite.fatture_righe (fattura_id, riga_nr, articolo_id, descrizione,
      uom_id, qta, prezzo_unitario, iva_id, imponibile_riga, competenza_dal, competenza_al)
  VALUES (v_fatt, 1, r.articolo_id, 'Riga fattura pgTAP', r.uom_id, p_qta, 20,
      r.iva_id, p_qta * 20, script.fn_data_operativa(), script.fn_data_operativa())
  RETURNING id INTO v_riga;
  UPDATE vendite.attivita_fatturabili SET fattura_riga_id = v_riga WHERE id = v_af;
  RETURN v_riga;
END $$ LANGUAGE plpgsql;

-- Reso PER RI-CONSEGNA, confermato.
CREATE OR REPLACE FUNCTION pg_temp.ch_mk_reso(p_ddt_riga bigint, p_ddt_uid uuid, p_qta numeric)
RETURNS TABLE(reso_id bigint, resi_riga_id bigint) AS $$
DECLARE r RECORD; v_reso bigint; v_riga bigint;
BEGIN
  SELECT * INTO r FROM tmp_refs_ch;
  INSERT INTO vendite.resi (stato_doc_reso_id, sorgente_tipo_id, sorgente_uid, storicizza, meta)
  VALUES (r.stato_reso_draft_id, r.sorgente_ddt_id, p_ddt_uid, false,
          jsonb_build_object('test_scope','pgtap_chiusura'))
  RETURNING id INTO v_reso;
  INSERT INTO vendite.resi_righe (reso_id, riga_nr, ddt_riga_id, ordine_riga_id,
      articolo_id, descrizione, qta_operativa, uom_operativa_id, factor_to_base,
      tipo_reso_id, storicizza)
  SELECT v_reso, 1, dr.id,
         (SELECT f.ordine_riga_id FROM vendite.ordini_righe_fulfillment f
           WHERE f.ddt_riga_id = dr.id ORDER BY f.id LIMIT 1),
         dr.articolo_id, dr.descrizione, p_qta, dr.uom_operativa_id, dr.factor_to_base,
         r.tipo_riconsegna_id, false
    FROM vendite.ddt_righe dr WHERE dr.id = p_ddt_riga
  RETURNING id INTO v_riga;
  PERFORM vendite.fn_conferma_reso(v_reso);
  RETURN QUERY SELECT v_reso, v_riga;
END $$ LANGUAGE plpgsql;

-- La RI-SPEDIZIONE (DDT di ri-consegna portato a CONSEGNATO), alla data data:
-- la data ordina le sorelle nella finestra di `migra`.
CREATE OR REPLACE FUNCTION pg_temp.ch_rispedisci(p_reso_id bigint, p_resi_riga_id bigint,
                                                 p_qta numeric, p_data date)
RETURNS TABLE(ddt_id bigint, ddt_riga_id bigint) AS $$
DECLARE r RECORD; v_ddt bigint; v_ord smallint; v_tappa RECORD; v_riga bigint;
BEGIN
  SELECT * INTO r FROM tmp_refs_ch;
  v_ddt := vendite.fn_genera_ddt_riconsegna(
      p_reso_id,
      jsonb_build_array(jsonb_build_object('resi_riga_id', p_resi_riga_id, 'qta', p_qta)),
      p_data);
  INSERT INTO vendite.ddt_indirizzi (ddt_id, tipo_indirizzo_id, snapshot)
  VALUES (v_ddt, r.tipo_ind_con_id, '{"display":"CON"}'::jsonb) ON CONFLICT DO NOTHING;
  UPDATE vendite.ddt SET causale_trasporto_id = r.causale_vendita_id WHERE id = v_ddt;
  FOR v_tappa IN
      SELECT s.id, s.ordine FROM config.stati_doc_ddt s
       WHERE s.codice_interno IN ('EMESSO','SPEDITO','CONSEGNATO') ORDER BY s.ordine
  LOOP
      SELECT s.ordine INTO v_ord
        FROM vendite.ddt d JOIN config.stati_doc_ddt s ON s.id = d.stato_doc_ddt_id
       WHERE d.id = v_ddt;
      CONTINUE WHEN v_ord >= v_tappa.ordine;
      UPDATE vendite.ddt SET stato_doc_ddt_id = v_tappa.id WHERE id = v_ddt;
  END LOOP;
  SELECT dr.id INTO v_riga FROM vendite.ddt_righe dr WHERE dr.ddt_id = v_ddt ORDER BY dr.id LIMIT 1;
  RETURN QUERY SELECT v_ddt, v_riga;
END $$ LANGUAGE plpgsql;

-- Il confronto fn(seme) = vista filtrata, nei DUE versi: zero righe diverse.
CREATE OR REPLACE FUNCTION pg_temp.ch_diff_ddt(p_ddt bigint) RETURNS bigint AS $$
  SELECT (SELECT count(*) FROM (SELECT * FROM vendite.fn_partite_merce(ARRAY[p_ddt])
                                 EXCEPT ALL
                                SELECT * FROM vendite.vw_partite_merce v WHERE v.ddt_id = p_ddt) a)
       + (SELECT count(*) FROM (SELECT * FROM vendite.vw_partite_merce v WHERE v.ddt_id = p_ddt
                                 EXCEPT ALL
                                SELECT * FROM vendite.fn_partite_merce(ARRAY[p_ddt])) b);
$$ LANGUAGE sql;

-- ============================================================
-- CASO 1 — un ordine da 30 spedito su TRE DDT (10, 10, 10, date crescenti),
--          fatturato dall'ORDINE per 15. La greedy `alloc` versa nel piu'
--          vecchio: 10 al primo, 5 al secondo, 0 al terzo.
-- ============================================================
CREATE TEMP TABLE tmp_o1 AS SELECT * FROM pg_temp.ch_mk_ordine(30);
CREATE TEMP TABLE tmp_ob AS SELECT * FROM pg_temp.ch_mk_ordine(10);
CREATE TEMP TABLE tmp_d1 AS SELECT * FROM pg_temp.ch_mk_ddt((SELECT ordine_id FROM tmp_o1), (SELECT ordine_riga_id FROM tmp_o1), 10, DATE '2026-08-10',
                                                        p_lega_anche => (SELECT ordine_riga_id FROM tmp_ob));
CREATE TEMP TABLE tmp_d2 AS SELECT * FROM pg_temp.ch_mk_ddt((SELECT ordine_id FROM tmp_o1), (SELECT ordine_riga_id FROM tmp_o1), 10, DATE '2026-08-11');
CREATE TEMP TABLE tmp_d3 AS SELECT * FROM pg_temp.ch_mk_ddt((SELECT ordine_id FROM tmp_o1), (SELECT ordine_riga_id FROM tmp_o1), 10, DATE '2026-08-12');
SELECT pg_temp.ch_mk_af(('ORD:' || (SELECT ordine_uid FROM tmp_o1)::text || ':R:' || (SELECT ordine_riga_id FROM tmp_o1)::text)::varchar, 15);

-- ⭐ Il DDT di MEZZO chiesto da solo. Senza R1 (il primo DDT, stessa riga
--    d'ordine) la sua partizione sarebbe {se stesso} e prenderebbe 10.
SELECT ok(
  (SELECT count(*) = 1 AND max(p.fatturato_da_ordine) = 5 AND max(p.differenza) = 5
     FROM vendite.fn_partite_merce(ARRAY[(SELECT ddt_id FROM tmp_d2)]) p),
  '4) R1 indispensabile: il DDT di mezzo da solo ha fatturato_da_ordine 5 (la greedy ha gia'' versato 10 nel primo)');

SELECT is(pg_temp.ch_diff_ddt((SELECT ddt_id FROM tmp_d2)), 0::bigint,
  '5) ...e la sua riga e'' identica alla vista filtrata, nei due versi');

SELECT ok(
  (SELECT max(p.fatturato_da_ordine) = 0 AND max(p.differenza) = 10 AND max(p.stato) = 'DA_FATTURARE'
     FROM vendite.fn_partite_merce(ARRAY[(SELECT ddt_id FROM tmp_d3)]) p),
  '6) il terzo DDT non prende niente dal serbatoio: fatturato_da_ordine 0, 10 da fatturare');

-- Seme per ORDINE: le tre spedizioni, identiche alla vista filtrata su ordine_id.
SELECT is(
  (SELECT count(*) FROM vendite.fn_partite_merce(NULL, ARRAY[(SELECT ordine_id FROM tmp_o1)]))::text
  || '|' ||
  ((SELECT count(*) FROM (SELECT * FROM vendite.fn_partite_merce(NULL, ARRAY[(SELECT ordine_id FROM tmp_o1)])
                          EXCEPT ALL
                          SELECT * FROM vendite.vw_partite_merce v WHERE v.ordine_id = (SELECT ordine_id FROM tmp_o1)) a)
   + (SELECT count(*) FROM (SELECT * FROM vendite.vw_partite_merce v WHERE v.ordine_id = (SELECT ordine_id FROM tmp_o1)
                          EXCEPT ALL
                          SELECT * FROM vendite.fn_partite_merce(NULL, ARRAY[(SELECT ordine_id FROM tmp_o1)])) b))::text,
  '3|0',
  '7) seme per ordine: tre righe, identiche alla vista WHERE ordine_id = o');

-- ============================================================
-- CASO 2 — reso -> nota di credito PARZIALE -> due ri-spedizioni.
--   Partita da 10, fatturata 6 (corsia DDT), resa 5 per ri-consegna:
--   tenuti 5, fatturati 6 -> accredito dovuto 1 (D-NC-6: pieno, cioe' 1).
--   Ri-spedita in due DDT: 3 (01-09) e 2 (02-09). La capienza accreditata
--   e' 1: la PRIMA sorella la prende tutta, la SECONDA resta a 0.
--   Chiedere la seconda da sola SENZA la sorella darebbe LEAST(2, 1 - 0) = 1.
-- ============================================================
CREATE TEMP TABLE tmp_o2 AS SELECT * FROM pg_temp.ch_mk_ordine(10);
CREATE TEMP TABLE tmp_p AS SELECT * FROM pg_temp.ch_mk_ddt((SELECT ordine_id FROM tmp_o2), (SELECT ordine_riga_id FROM tmp_o2), 10, DATE '2026-08-13');
SELECT pg_temp.ch_fattura(('DDT:' || (SELECT ddt_uid FROM tmp_p)::text || ':R:' || (SELECT ddt_riga_id FROM tmp_p)::text)::varchar, 6);
CREATE TEMP TABLE tmp_reso AS SELECT * FROM pg_temp.ch_mk_reso((SELECT ddt_riga_id FROM tmp_p), (SELECT ddt_uid FROM tmp_p), 5);
SELECT vendite.fn_accredita_riga_reso((SELECT resi_riga_id FROM tmp_reso));
SELECT vendite.fn_emit_attivita_fatturabili_da_commessa((SELECT commessa_id FROM tmp_com_ch), true, false);
CREATE TEMP TABLE tmp_r1 AS SELECT * FROM pg_temp.ch_rispedisci((SELECT reso_id FROM tmp_reso), (SELECT resi_riga_id FROM tmp_reso), 3, DATE '2026-09-01');
CREATE TEMP TABLE tmp_r2 AS SELECT * FROM pg_temp.ch_rispedisci((SELECT reso_id FROM tmp_reso), (SELECT resi_riga_id FROM tmp_reso), 2, DATE '2026-09-02');

SELECT ok(
  (SELECT p.riconsegna_quota_nuova = 0 AND p.stato = 'RICONSEGNA'
     FROM vendite.fn_partite_merce(ARRAY[(SELECT ddt_id FROM tmp_r2)]) p),
  '8) le sorelle servono: la seconda ri-spedizione da sola ha quota 0 (la prima ha preso l''unico pezzo accreditato)');

SELECT ok(
  (SELECT p.riconsegna_quota_nuova = 1 AND p.differenza = 1 AND p.stato = 'DA_FATTURARE'
     FROM vendite.fn_partite_merce(ARRAY[(SELECT ddt_id FROM tmp_r1)]) p),
  '9) la prima ri-spedizione prende la quota 1: una partita vera, 1 da fatturare');

SELECT ok(
  (SELECT p.consegnato = 14 FROM vendite.fn_partite_merce(ARRAY[(SELECT ddt_id FROM tmp_p)]) p)
  AND pg_temp.ch_diff_ddt((SELECT ddt_id FROM tmp_p)) = 0,
  '10) l''origine da sola: consegnato 10 + 5 ri-consegnati - 1 migrato = 14, identica alla vista');

-- ============================================================
-- CASO 3 — la riga A MANO su un DDT misto, stesso articolo dell'ordine:
--          sospetto acceso e origine NESSUNA anche per la chiusura.
--          rev 2026-09-22: DDT SUO (ordine da 10 + riga a mano da 4, entrata
--          in bozza dentro ch_mk_ddt): fino al 21-09 la riga si aggiungeva
--          al DDT di mezzo gia' consegnato, che il BB delle righe non
--          ammette piu' — e aggiungerla prima avrebbe cambiato i conti dei
--          test 4-10.
-- ============================================================
CREATE TEMP TABLE tmp_o3 AS SELECT * FROM pg_temp.ch_mk_ordine(10);
CREATE TEMP TABLE tmp_d3m AS SELECT * FROM pg_temp.ch_mk_ddt((SELECT ordine_id FROM tmp_o3), (SELECT ordine_riga_id FROM tmp_o3), 10, DATE '2026-08-14', 4);

SELECT is(
  (SELECT p.origine || '|' || p.sospetto_duplicato_ordine::text
     FROM vendite.fn_partite_merce(ARRAY[(SELECT ddt_id FROM tmp_d3m)]) p
    WHERE p.ddt_riga_id <> (SELECT ddt_riga_id FROM tmp_d3m)),
  'NESSUNA|true',
  '11) la riga a mano con l''articolo gia'' nell''ordine: origine NESSUNA e sospetto acceso, anche per chiusura');

-- 16) Sullo stesso DDT, la riga che evade la riga d'ordine: l'origine e' il
--     codice della sorgente (grammatica unica, §12.8), non il codice corto, e
--     nomina una riga di config.sorgenti. Funzione e vista dicono lo stesso.
SELECT results_eq(
  $q$SELECT p.origine::text,
            EXISTS (SELECT 1 FROM config.sorgenti s WHERE s.codice_interno = p.origine),
            (SELECT v.origine::text FROM vendite.vw_partite_merce v WHERE v.ddt_riga_id = p.ddt_riga_id)
       FROM vendite.fn_partite_merce(ARRAY[(SELECT ddt_id FROM tmp_d3m)]) p
      WHERE p.ddt_riga_id = (SELECT ddt_riga_id FROM tmp_d3m)$q$,
  $q$VALUES ('ORDINE_VENDITA', true, 'ORDINE_VENDITA')$q$,
  '16) la riga che evade una riga d''ordine: origine ORDINE_VENDITA, codice di config.sorgenti, per la funzione come per la vista');

-- ============================================================
-- CASO 4 — niente da seminare
-- ============================================================
-- Un ordine SUO: quello del caso 2 e' EVASO (10 su 10) e non ammette altri DDT.
CREATE TEMP TABLE tmp_o4 AS SELECT * FROM pg_temp.ch_mk_ordine(5);
CREATE TEMP TABLE tmp_bozza AS SELECT pg_temp.ch_mk_ddt_bozza((SELECT ordine_id FROM tmp_o4), (SELECT ordine_riga_id FROM tmp_o4), 5) AS ddt_id;

SELECT is(
  (SELECT count(*) FROM vendite.fn_partite_merce(ARRAY[(SELECT ddt_id FROM tmp_bozza)]))::text
  || '|' || (SELECT count(*) FROM vendite.fn_partite_merce(ARRAY[-1]))::text
  || '|' || (SELECT count(*) FROM vendite.fn_partite_merce(ARRAY[]::bigint[]))::text,
  '0|0|0',
  '12) DDT in bozza, id inesistente, array VUOTO: zero righe — vuoto non e'' «tutte»');

-- ============================================================
-- CASO 8 — la riga MULTIPLA. Il primo DDT del caso 1 evade ANCHE un secondo
--          ordine (B, id maggiore): `ordine_id` proiettato resta quello della
--          riga minima (A). Chiesta per B non esce; chiesta per A esce
--          MULTIPLA — come la legge il backend (§2-bis.7).
-- ============================================================
-- (il legame con B nasce con il primo DDT in bozza: pg_temp.ch_mk_ddt, D-6 del 2026-10-11)

SELECT results_eq(
  $q$SELECT (SELECT count(*)::int FROM vendite.fn_partite_merce(NULL, ARRAY[(SELECT ordine_id FROM tmp_ob)]) p
              WHERE p.ddt_riga_id = (SELECT ddt_riga_id FROM tmp_d1)),
            (SELECT p.origine::text FROM vendite.fn_partite_merce(NULL, ARRAY[(SELECT ordine_id FROM tmp_o1)]) p
              WHERE p.ddt_riga_id = (SELECT ddt_riga_id FROM tmp_d1)),
            (SELECT count(*)::int FROM vendite.vw_partite_merce v
              WHERE v.ddt_riga_id = (SELECT ddt_riga_id FROM tmp_d1)
                AND v.ordine_id = (SELECT ordine_id FROM tmp_ob))$q$,
  $q$VALUES (0, 'MULTIPLA', 0)$q$,
  '13) riga MULTIPLA: esce solo sotto l''ordine della riga minima, per la funzione come per la vista');

-- ============================================================
-- CASO 5 — l'ONERE non e' merce. Ordine da 10 spedito 10, fatturato via DDT
--          per 10 (NORMALE, corsia DDT) + un ONERE da 5 sul segmento ORD della
--          stessa riga d'ordine (un segmento e' UNA attivita': l'onere ha la
--          sua chiave). La partita legge il conto delle AF per chiave
--          (fn_af_merce_per_riga, che NON filtra il tipo — e' la porta della
--          nota di credito) e tiene solo tipo_movimento = 'NORMALE': senza la
--          cintura l'onere entrerebbe come fatturato d'ordine 5, fatturato 15
--          e differenza -5, cioe' «da accreditare» su una merce fatturata
--          giusta. Ereditato dal presidio del contatore ritirato
--          (test-vw-contatore-merce-v1, test 5).
-- ============================================================
CREATE TEMP TABLE tmp_o5 AS SELECT * FROM pg_temp.ch_mk_ordine(10);
CREATE TEMP TABLE tmp_d5 AS SELECT * FROM pg_temp.ch_mk_ddt((SELECT ordine_id FROM tmp_o5), (SELECT ordine_riga_id FROM tmp_o5), 10, DATE '2026-08-16');
SELECT pg_temp.ch_mk_af(('DDT:' || (SELECT ddt_uid FROM tmp_d5)::text || ':R:' || (SELECT ddt_riga_id FROM tmp_d5)::text)::varchar, 10);
SELECT pg_temp.ch_mk_af(('ORD:' || (SELECT ordine_uid FROM tmp_o5)::text || ':R:' || (SELECT ordine_riga_id FROM tmp_o5)::text)::varchar, 5, 'ONERE');

SELECT results_eq(
  $q$SELECT p.fatturato_merce, p.fatturato_da_ordine, p.fatturato, p.differenza,
            (SELECT count(*)::int FROM vendite.fn_af_merce_per_riga(ARRAY[('ORD:' || o.ordine_uid::text || ':R:' || o.ordine_riga_id::text)::varchar]) f
              WHERE f.tipo_movimento = 'ONERE' AND f.quantita = 5)
       FROM vendite.fn_partite_merce(ARRAY[(SELECT ddt_id FROM tmp_d5)]) p, tmp_o5 o$q$,
  $q$VALUES (10::numeric, 0::numeric, 10::numeric, 0::numeric, 1)$q$,
  '15) l''ONERE sul segmento ORD e'' nel conto delle AF (1 riga ONERE da 5) ma NON nel fatturato della partita: merce 10, da ordine 0, differenza 0');

-- ============================================================
-- 14) Scope: chi non vede il documento non vede la partita.
-- ⚠️ Il cancello e' `app.ruolo_applicativo`: con la veste OPERATORE e un
--    utente senza whitelist la RLS non fa vedere il DDT, e la funzione —
--    INVOKER, letta come chi chiede — risponde ZERO righe, non conti a zero.
-- ============================================================
SELECT set_config('app.current_user_id', '999999999', true);

SELECT is(
  (SELECT count(*) FROM vendite.fn_partite_merce(ARRAY[(SELECT ddt_id FROM tmp_d2)])),
  0::bigint,
  '14) scope che non vede il DDT: la partita sparisce, non esce con dei conti a zero');

SELECT * FROM finish();
ROLLBACK;
