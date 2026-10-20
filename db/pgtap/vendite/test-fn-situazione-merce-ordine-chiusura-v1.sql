-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13, 2e/L2c-1): le chiavi del push col codice della sorgente, composte da script.fn_segment_key dove la forma lo permette (le forme su piu' righe col prefisso lungo); corsia e codice del registro coi codici lunghi.
-- pgTAP test per Zero ERP
-- Test: vendite.fn_situazione_merce_ordine — la situazione merce per riga
--       d'ordine PER DOCUMENTO (D14 giro 2 — D3;
--       brief-db-partita-merce-per-documento §2.2, §7; changeSet 20260921-26, -27).
--
-- Indice test (plan 13):
--   1) la funzione esiste, e' BEGIN ATOMIC, NON e' SECURITY DEFINER e dipende
--      da fn_partite_merce nel catalogo (la catena RLS passa di li')
--   2) ⭐ pin di D1: la vista e' la PROIEZIONE della funzione — nomina
--      fn_situazione_merce_ordine e nessuna tabella, nessuna partita
--   3) ⭐ pin dei tipi: 21 colonne, `ordinato` numeric(18,6) (un SELECT * dalla
--      funzione lo perderebbe), security_invoker=on
--   4) ⭐ ordine su tre DDT (10+10+10), fatturato dall'ORDINE per 15: chiesto
--      per ORDINE, una riga con consegnato 30, fatturato_da_ordine 15,
--      differenza 15, DA_FATTURARE, 3 partite, da_spedire 0
--   5) ⭐ LA SEMANTICA DEL SEME PER DDT: chiesto dal DDT DI MEZZO, la stessa
--      riga con la situazione INTERA (consegnato 30, 3 partite) — non la sola
--      partita di quel DDT (10, 1). E' «le righe d'ordine che quella spedizione
--      ha toccato», come il pannello legge dal 2026-08-19
--   6) ...e nei due semi le righe sono IDENTICHE alla vista filtrata come la
--      filtra il backend (EXCEPT ALL nei due versi)
--   7) la riga MAI SPEDITA dello stesso ordine: NON_SPEDITA con da_spedire 4
--      per seme ORDINE; per seme DDT non esce (nessuna spedizione l'ha toccata)
--   8) un ordine in BOZZA: NON_IMPEGNATA e da_spedire NULL, non zero
--   9) ⭐ riga MULTIPLA (un DDT dell'ordine A3 evade anche un ordine B, legato
--      in bozza dal 2026-10-11, D-6): per seme DDT
--      escono ENTRAMBE le righe d'ordine; quella di A e' NON_MISURABILE e quella
--      di B ha 0 partite (la partita conta sotto la riga MINIMA) — come la vista
--  10) ri-consegna: reso per ri-consegna 5 e ri-spedizione 3 — consegnato 13,
--      reso 5, tenuti 8, da_spedire 2 (5 resi − 3 ri-spediti), identica alla vista
--  11) niente da seminare: id inesistente e array VUOTO danno zero righe — vuoto
--      NON e' «tutte» (NULL, NULL lo e')
--  12) scope: chi non vede l'ordine non vede la situazione — zero righe
--  13) ⭐ `fatturato_anticipato`: spedito 4 di 10, fatturato 10 sull'ORDINE —
--      allocato sulla merce 4 (la capienza e' il consegnato), anticipato 6,
--      differenza 0 e PAREGGIATA (non «da accreditare»), da_spedire 6.
--      Ereditato il 22-09 da test-vw-contatore-merce-v1 (ritirato con la
--      vista, D6): era il solo presidio del VALORE di questa colonna
--
-- Scopo:
--  - la funzione e' equivalente alla vista per costruzione; questo file
--    COSTRUISCE i casi in cui il seme per DDT risponderebbe un numero sbagliato
--    se leggesse la sola partita di quel DDT (5), o se non riportasse tutte le
--    righe toccate (9). Un EXCEPT ALL sulle righe di oggi non lo farebbe.
--  - il 2 e il 3 sono pin di FORMA: D1 (un corpo) e il contratto dei tipi.
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

SELECT plan(13);

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
    WHERE p.proname = 'fn_situazione_merce_ordine' AND p.pronamespace = 'vendite'::regnamespace),
  '1) fn_situazione_merce_ordine esiste, e'' BEGIN ATOMIC, non DEFINER, e dipende da fn_partite_merce in pg_depend');

SELECT ok(
  (SELECT d ~ 'fn_situazione_merce_ordine' AND d !~ 'vendite\.ordini_righe'
      AND d !~ 'vw_partite_merce' AND d !~ 'fn_partite_merce' AND d !~ 'vw_af_merce_per_riga'
     FROM pg_get_viewdef('vendite.vw_situazione_merce_ordine'::regclass, true) AS d),
  '2) la vista e'' la proiezione di fn_situazione_merce_ordine: nomina la funzione e nessuna tabella');

SELECT is(
  (SELECT count(*)::int || '|' || max(format_type(a.atttypid, a.atttypmod)) FILTER (WHERE a.attname = 'ordinato')
     FROM pg_attribute a
    WHERE a.attrelid = 'vendite.vw_situazione_merce_ordine'::regclass AND a.attnum > 0 AND NOT a.attisdropped)
  || '|' || COALESCE((SELECT o.option_value FROM pg_options_to_table(
                        (SELECT c.reloptions FROM pg_class c WHERE c.oid = 'vendite.vw_situazione_merce_ordine'::regclass)) o
                       WHERE o.option_name = 'security_invoker'), 'off'),
  '21|numeric(18,6)|on',
  '3) la vista ha 21 colonne, ordinato resta numeric(18,6), security_invoker=on');

-- ============================================================
-- Il mondo si COSTRUISCE, non si cerca (guida pgTAP; D7). Stessa fixture di
-- test-fn-partite-merce-chiusura-v1: cliente e articolo dai builder di dbops,
-- il catalogo per codice_interno.
-- ⚠️ Ordine obbligato: PRIMA il contesto, POI il cliente (il legame BA ->
--    emittente lo scrive il trigger z90 verso chi agisce).
-- ============================================================
CREATE TEMP TABLE tmp_cli_sm AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('pgtap_situazione');

CREATE TEMP TABLE tmp_refs_sm AS
SELECT
  c.billing_account_id,
  c.utility_id,
  c.istanza_utility_id,
  script.fn_pgtap_emittente_operatore()    AS emittente_fiscale_id,
  script.fn_pgtap_emittente_sr_operatore() AS emittente_sr_id,
  c.soggetto_ruolo_id,
  dbops.fn_pgtap_crea_articolo('PGT-SM-ART', false)                                                  AS articolo_id,
  (SELECT u.id FROM catalogo.unita_misura u WHERE u.attivo IS TRUE ORDER BY u.id LIMIT 1)             AS uom_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1)                                            AS valuta_id,
  (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1)                        AS iva_id,
  (SELECT s.id FROM config.stati_doc_ordini s WHERE s.codice_interno='DRAFT'      AND s.attivo ORDER BY s.id LIMIT 1) AS stato_ord_draft_id,
  (SELECT s.id FROM config.stati_doc_ordini s WHERE s.codice_interno='CONFERMATO' AND s.attivo ORDER BY s.id LIMIT 1) AS stato_ord_conf_id,
  (SELECT s.id FROM config.stati_doc_ddt s WHERE s.codice_interno='EMESSO'     AND s.attivo ORDER BY s.id LIMIT 1)    AS stato_ddt_emesso_id,
  (SELECT s.id FROM config.stati_doc_ddt s WHERE s.codice_interno='SPEDITO'    AND s.attivo ORDER BY s.id LIMIT 1)    AS stato_ddt_spedito_id,
  (SELECT s.id FROM config.stati_doc_ddt s WHERE s.codice_interno='CONSEGNATO' AND s.attivo ORDER BY s.id LIMIT 1)    AS stato_ddt_consegnato_id,
  (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno='DDT_VENDITA' AND s.attivo ORDER BY s.id LIMIT 1)        AS sorgente_ddt_id,
  (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno='COMMESSA'    AND s.attivo ORDER BY s.id LIMIT 1)        AS sorgente_root_id,
  (SELECT s.id FROM config.stati_doc_reso s WHERE s.codice_interno='DRAFT' AND s.attivo ORDER BY s.id LIMIT 1)        AS stato_reso_draft_id,
  (SELECT t.id FROM config.tipi_reso t WHERE t.codice_interno='RESO_PER_RICONSEGNA' AND t.attivo ORDER BY t.id LIMIT 1) AS tipo_riconsegna_id,
  (SELECT t.id FROM config.tipi_doc_fiscale t WHERE t.attivo IS TRUE ORDER BY t.id LIMIT 1)                           AS tipo_doc_fiscale_id,
  (SELECT c.id FROM config.causali_trasporto c WHERE c.codice='VENDITA' ORDER BY c.id LIMIT 1)                        AS causale_vendita_id,
  (SELECT id FROM config.tipi_indirizzi WHERE codice_interno='CON')                                                   AS tipo_ind_con_id
FROM tmp_cli_sm c;

-- Commessa + ROOT: serve alle attivita' fatturabili (corsia ORD).
CREATE TEMP TABLE tmp_com_sm AS
SELECT vendite.fn_get_or_create_commessa(
  p_billing_account_id     => (SELECT billing_account_id FROM tmp_refs_sm),
  p_utility_id             => (SELECT utility_id FROM tmp_refs_sm),
  p_tipo_commessa          => 'AUTO',
  p_policy_fatturazione    => 'DA_DOCUMENTO',
  p_fatturazione_immediata => false,
  p_priorita_operativa     => 'NORMALE',
  p_competenza_dal         => DATE '2026-08-01',
  p_competenza_al          => DATE '2026-08-31',
  p_meta                   => jsonb_build_object('test_scope','pgtap_situazione'),
  p_force_new              => true) AS commessa_id;

SELECT vendite.fn_link_commessa_sorgente(
  p_commessa_id      => (SELECT commessa_id FROM tmp_com_sm),
  p_sorgente_tipo_id => (SELECT sorgente_root_id FROM tmp_refs_sm),
  p_sorgente_uid     => (SELECT commessa_id FROM tmp_com_sm)::text,
  p_sorgente_riga    => 1,
  p_meta             => '{}'::jsonb);

-- ============================================================
-- Helper (padre e figlio in due istruzioni: le CTE che scrivono condividono
-- la snapshot e le policy negano fail-closed)
-- ============================================================

-- Un ordine nello stato dato con una riga da p_qta (e, se p_qta_mai_spedita,
-- una riga 2 «mai spedita»).
-- ⚠️ rev 2026-10-08 (brief-db-righe-e-componenti-debiti-residui, D-1): la testata nasce DRAFT, prende le righe, poi passa allo stato voluto con dbops.fn_pgtap_porta_a_stato — fuori bozza le righe non si scrivono piu' (20261008-90).
CREATE OR REPLACE FUNCTION pg_temp.sm_mk_ordine(p_qta numeric, p_stato_id bigint,
                                                p_qta_mai_spedita numeric DEFAULT NULL)
RETURNS TABLE(ordine_id bigint, ordine_uid uuid, ordine_riga_id bigint) AS $$
DECLARE r RECORD; v_ord bigint; v_uid uuid; v_orr bigint; v_stato text;
BEGIN
  SELECT * INTO r FROM tmp_refs_sm;
  INSERT INTO vendite.ordini (soggetto_ruolo_id, billing_account_id, stato_doc_ordine_id,
    valuta_id, data, fatturazione_trigger, emittente_fiscale_id, storicizza, meta)
  VALUES (r.soggetto_ruolo_id, r.billing_account_id, r.stato_ord_draft_id, r.valuta_id,
          DATE '2026-08-05', 'CONSEGNATO', r.emittente_fiscale_id, false,
          jsonb_build_object('test_scope','pgtap_situazione'))
  RETURNING id, uid INTO v_ord, v_uid;
  INSERT INTO vendite.ordini_righe (ordine_id, riga_nr, articolo_id, descrizione,
    qta_operativa, quantita, prezzo_unitario, iva_id, attivo, storicizza, meta)
  VALUES (v_ord, 1, r.articolo_id, 'Riga situazione pgTAP', p_qta, p_qta, 20, r.iva_id,
          true, false, jsonb_build_object('test_scope','pgtap_situazione'))
  RETURNING id INTO v_orr;
  IF p_qta_mai_spedita IS NOT NULL THEN
    INSERT INTO vendite.ordini_righe (ordine_id, riga_nr, articolo_id, descrizione,
      qta_operativa, quantita, prezzo_unitario, iva_id, attivo, storicizza, meta)
    VALUES (v_ord, 2, r.articolo_id, 'Riga mai spedita', p_qta_mai_spedita, p_qta_mai_spedita, 20, r.iva_id,
            true, false, jsonb_build_object('test_scope','pgtap_situazione'));
  END IF;
  SELECT s.codice_interno INTO v_stato FROM config.stati_doc_ordini s WHERE s.id = p_stato_id;
  PERFORM dbops.fn_pgtap_porta_a_stato('vendite.ordini', v_ord, v_stato);
  RETURN QUERY SELECT v_ord, v_uid, v_orr;
END $$ LANGUAGE plpgsql;

-- Un DDT CONSEGNATO che evade p_qta della riga d'ordine, alla data p_data.
CREATE OR REPLACE FUNCTION pg_temp.sm_mk_ddt(p_ordine_id bigint, p_ordine_riga_id bigint,
                                             p_qta numeric, p_data date,
                                             p_lega_anche bigint DEFAULT NULL)
RETURNS TABLE(ddt_id bigint, ddt_uid uuid, ddt_riga_id bigint) AS $$
DECLARE r RECORD; v_ddt bigint; v_uid uuid; v_ddtr bigint;
BEGIN
  SELECT * INTO r FROM tmp_refs_sm;
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

-- Un'attivita' fatturabile NORMALE sul segmento dato (corsia ORD).
CREATE OR REPLACE FUNCTION pg_temp.sm_mk_af(p_segment varchar, p_qta numeric)
RETURNS void AS $$
DECLARE r RECORD;
BEGIN
  SELECT * INTO r FROM tmp_refs_sm;
  PERFORM vendite.fn_upsert_commessa_attivita(
    p_commessa_id => (SELECT commessa_id FROM tmp_com_sm),
    -- La riga NORMALE ha la sua sorgente (vincolo 20261012-27).
    p_sorgente_tipo_id => (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'COMMESSA'),
    p_sorgente_uid => ((SELECT commessa_id FROM tmp_com_sm))::text,
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
  PERFORM vendite.fn_emit_attivita_fatturabili_da_commessa((SELECT commessa_id FROM tmp_com_sm), true, false);
END $$ LANGUAGE plpgsql;

-- Reso PER RI-CONSEGNA, confermato.
CREATE OR REPLACE FUNCTION pg_temp.sm_mk_reso(p_ddt_riga bigint, p_ddt_uid uuid, p_qta numeric)
RETURNS TABLE(reso_id bigint, resi_riga_id bigint) AS $$
DECLARE r RECORD; v_reso bigint; v_riga bigint;
BEGIN
  SELECT * INTO r FROM tmp_refs_sm;
  INSERT INTO vendite.resi (stato_doc_reso_id, sorgente_tipo_id, sorgente_uid, storicizza, meta)
  VALUES (r.stato_reso_draft_id, r.sorgente_ddt_id, p_ddt_uid, false,
          jsonb_build_object('test_scope','pgtap_situazione'))
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

-- La RI-SPEDIZIONE (DDT di ri-consegna portato a CONSEGNATO).
CREATE OR REPLACE FUNCTION pg_temp.sm_rispedisci(p_reso_id bigint, p_resi_riga_id bigint,
                                                 p_qta numeric, p_data date)
RETURNS bigint AS $$
DECLARE r RECORD; v_ddt bigint; v_ord smallint; v_tappa RECORD;
BEGIN
  SELECT * INTO r FROM tmp_refs_sm;
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
  RETURN v_ddt;
END $$ LANGUAGE plpgsql;

-- Il confronto fn(seme) = vista filtrata COME LA FILTRA IL BACKEND, nei DUE
-- versi: per ordine `ordine_id = o`, per DDT l'EXISTS sul fulfillment.
CREATE OR REPLACE FUNCTION pg_temp.sm_diff_ordine(p_ord bigint) RETURNS bigint AS $$
  SELECT (SELECT count(*) FROM (SELECT * FROM vendite.fn_situazione_merce_ordine(NULL, ARRAY[p_ord])
                                 EXCEPT ALL
                                SELECT * FROM vendite.vw_situazione_merce_ordine v WHERE v.ordine_id = p_ord) a)
       + (SELECT count(*) FROM (SELECT * FROM vendite.vw_situazione_merce_ordine v WHERE v.ordine_id = p_ord
                                 EXCEPT ALL
                                SELECT * FROM vendite.fn_situazione_merce_ordine(NULL, ARRAY[p_ord])) b);
$$ LANGUAGE sql;

CREATE OR REPLACE FUNCTION pg_temp.sm_diff_ddt(p_ddt bigint) RETURNS bigint AS $$
  WITH v AS (
    SELECT s.* FROM vendite.vw_situazione_merce_ordine s
     WHERE EXISTS (SELECT 1 FROM vendite.ordini_righe_fulfillment f
                     JOIN vendite.ddt_righe dr_f ON dr_f.id = f.ddt_riga_id
                    WHERE f.ordine_riga_id = s.ordine_riga_id AND dr_f.ddt_id = p_ddt))
  SELECT (SELECT count(*) FROM (SELECT * FROM vendite.fn_situazione_merce_ordine(ARRAY[p_ddt], NULL)
                                 EXCEPT ALL SELECT * FROM v) a)
       + (SELECT count(*) FROM (SELECT * FROM v
                                 EXCEPT ALL SELECT * FROM vendite.fn_situazione_merce_ordine(ARRAY[p_ddt], NULL)) b);
$$ LANGUAGE sql;

-- ============================================================
-- CASO 1 — un ordine da 30 spedito su TRE DDT (10, 10, 10), fatturato
--          dall'ORDINE per 15.
-- ============================================================
-- ⚠️ rev 2026-10-08 (brief-db-righe-e-componenti-debiti-residui, D-1): la riga 2 «mai
--   spedita» del caso 2 nasce QUI, in bozza, con la riga 1 (20261008-90: dopo i
--   DDT l'ordine e' fuori bozza e non prende righe). Il 4 legge percio' la riga 1.
CREATE TEMP TABLE tmp_o1 AS SELECT * FROM pg_temp.sm_mk_ordine(30, (SELECT stato_ord_conf_id FROM tmp_refs_sm), 4);
CREATE TEMP TABLE tmp_d1 AS SELECT * FROM pg_temp.sm_mk_ddt((SELECT ordine_id FROM tmp_o1), (SELECT ordine_riga_id FROM tmp_o1), 10, DATE '2026-08-10');
CREATE TEMP TABLE tmp_d2 AS SELECT * FROM pg_temp.sm_mk_ddt((SELECT ordine_id FROM tmp_o1), (SELECT ordine_riga_id FROM tmp_o1), 10, DATE '2026-08-11');
CREATE TEMP TABLE tmp_d3 AS SELECT * FROM pg_temp.sm_mk_ddt((SELECT ordine_id FROM tmp_o1), (SELECT ordine_riga_id FROM tmp_o1), 10, DATE '2026-08-12');
SELECT pg_temp.sm_mk_af(script.fn_segment_key('ORDINE_VENDITA', (SELECT ordine_uid FROM tmp_o1)::text, (SELECT ordine_riga_id FROM tmp_o1)), 15);

SELECT results_eq(
  $q$SELECT s.consegnato, s.fatturato_da_ordine, s.differenza, s.stato::text, s.partite_merce, s.da_spedire
       FROM vendite.fn_situazione_merce_ordine(NULL, ARRAY[(SELECT ordine_id FROM tmp_o1)]) s
      WHERE s.riga_nr = 1$q$,
  $q$VALUES (30::numeric, 15::numeric, 15::numeric, 'DA_FATTURARE', 3, 0::numeric)$q$,
  '4) per ORDINE: consegnato 30, fatturato dall''ordine 15, differenza 15, DA_FATTURARE, 3 partite, niente da spedire');

-- ⭐ Il DDT di MEZZO. La situazione della riga d'ordine e' INTERA: 30 e 3
--    partite, non i 10 di quella spedizione.
SELECT results_eq(
  $q$SELECT s.ordine_riga_id, s.consegnato, s.fatturato_da_ordine, s.partite_merce
       FROM vendite.fn_situazione_merce_ordine(ARRAY[(SELECT ddt_id FROM tmp_d2)], NULL) s$q$,
  $q$SELECT ordine_riga_id, 30::numeric, 15::numeric, 3 FROM tmp_o1$q$,
  '5) per il DDT di mezzo: la riga d''ordine toccata, con la situazione INTERA (30 consegnati, 3 partite) e non la sola partita di quel DDT');

SELECT is(
  pg_temp.sm_diff_ordine((SELECT ordine_id FROM tmp_o1)) + pg_temp.sm_diff_ddt((SELECT ddt_id FROM tmp_d2)),
  0::bigint,
  '6) nei due semi le righe sono identiche alla vista filtrata come la filtra il backend, nei due versi');

-- ============================================================
-- CASO 2 — la riga MAI SPEDITA dello stesso ordine e l'ordine in BOZZA
-- ============================================================
-- (la riga 2 di tmp_o1 e' nata in bozza con l'ordine: vedi il caso 1)

SELECT results_eq(
  $q$SELECT (SELECT s.stato::text || '|' || (s.da_spedire = 4)::text || '|' || s.partite_merce::text
               FROM vendite.fn_situazione_merce_ordine(NULL, ARRAY[(SELECT ordine_id FROM tmp_o1)]) s
              WHERE s.riga_nr = 2),
            (SELECT count(*)::int FROM vendite.fn_situazione_merce_ordine(NULL, ARRAY[(SELECT ordine_id FROM tmp_o1)])),
            (SELECT count(*)::int FROM vendite.fn_situazione_merce_ordine(ARRAY[(SELECT ddt_id FROM tmp_d2)], NULL))$q$,
  $q$VALUES ('NON_SPEDITA|true|0', 2, 1)$q$,
  '7) la riga mai spedita: NON_SPEDITA con 4 da spedire per seme ordine (2 righe); per seme DDT non esce (1 riga)');

CREATE TEMP TABLE tmp_ob AS SELECT * FROM pg_temp.sm_mk_ordine(7, (SELECT stato_ord_draft_id FROM tmp_refs_sm));

SELECT results_eq(
  $q$SELECT s.stato::text, s.da_spedire IS NULL, s.giorni_ritardo IS NULL
       FROM vendite.fn_situazione_merce_ordine(NULL, ARRAY[(SELECT ordine_id FROM tmp_ob)]) s$q$,
  $q$VALUES ('NON_IMPEGNATA', true, true)$q$,
  '8) l''ordine in bozza: NON_IMPEGNATA, da_spedire NULL (non si applica), non zero');

-- ============================================================
-- CASO 3 — la riga MULTIPLA: un DDT dell'ordine A3 evade ANCHE un ordine B
--          (id maggiore). La partita conta sotto la riga MINIMA (A3): per seme
--          DDT escono entrambe le righe toccate — A3 NON_MISURABILE, B senza
--          partite.
-- ⭐ rev 2026-10-11 (brief-db-ddt-righe-evase-dall-ordine, D-6): un legame nasce
--   solo con la bolla in bozza. Fino a quel giorno il legame con B si scriveva
--   sul primo DDT del caso 1, gia' consegnato; ora nasce con la bolla
--   (pg_temp.sm_mk_ddt, p_lega_anche), e la coppia e' DEDICATA: sul DDT del
--   caso 1 avrebbe reso A non misurabile gia' al test 4.
-- ============================================================
CREATE TEMP TABLE tmp_o3 AS SELECT * FROM pg_temp.sm_mk_ordine(10, (SELECT stato_ord_conf_id FROM tmp_refs_sm));
CREATE TEMP TABLE tmp_om AS SELECT * FROM pg_temp.sm_mk_ordine(10, (SELECT stato_ord_conf_id FROM tmp_refs_sm));
CREATE TEMP TABLE tmp_dm AS SELECT * FROM pg_temp.sm_mk_ddt((SELECT ordine_id FROM tmp_o3), (SELECT ordine_riga_id FROM tmp_o3), 10, DATE '2026-08-10',
                                                        (SELECT ordine_riga_id FROM tmp_om));

SELECT results_eq(
  $q$SELECT s.ordine_riga_id = (SELECT ordine_riga_id FROM tmp_o3), s.stato::text, s.partite_merce, s.misurabile
       FROM vendite.fn_situazione_merce_ordine(ARRAY[(SELECT ddt_id FROM tmp_dm)], NULL) s
      ORDER BY s.ordine_riga_id$q$,
  $q$VALUES (true, 'NON_MISURABILE', 1, false), (false, 'NON_SPEDITA', 0, true)$q$,
  '9) riga MULTIPLA: per il DDT escono le DUE righe toccate — A3 NON_MISURABILE con la sua partita, B senza partite');

-- (l'uguaglianza con la vista per DDT1 e per l'ordine B e' asserita nel 10,
--  insieme a quella del caso della ri-consegna)

-- ============================================================
-- CASO 4 — la ri-consegna: reso per ri-consegna 5, ri-spedizione 3.
--   Partita d'origine: consegnato 10 + 3 ri-consegnati = 13, reso 5, tenuti 8;
--   la riga del DDT di ri-consegna e' esclusa (e_riconsegna). Evaso 13 (il
--   DDT di ri-consegna scrive un fulfillment); qta_riconsegna = 5 resi − 0
--   rinunciati = 5 → da_spedire = 10 − 13 + 5 = 2 (i pezzi non ancora
--   ri-spediti).
-- ============================================================
CREATE TEMP TABLE tmp_o2 AS SELECT * FROM pg_temp.sm_mk_ordine(10, (SELECT stato_ord_conf_id FROM tmp_refs_sm));
CREATE TEMP TABLE tmp_p AS SELECT * FROM pg_temp.sm_mk_ddt((SELECT ordine_id FROM tmp_o2), (SELECT ordine_riga_id FROM tmp_o2), 10, DATE '2026-08-13');
CREATE TEMP TABLE tmp_reso AS SELECT * FROM pg_temp.sm_mk_reso((SELECT ddt_riga_id FROM tmp_p), (SELECT ddt_uid FROM tmp_p), 5);
CREATE TEMP TABLE tmp_r1 AS SELECT pg_temp.sm_rispedisci((SELECT reso_id FROM tmp_reso), (SELECT resi_riga_id FROM tmp_reso), 3, DATE '2026-09-01') AS ddt_id;

SELECT results_eq(
  $q$SELECT s.consegnato, s.reso, s.tenuti, s.in_riconsegna, s.da_spedire, s.partite_merce,
            pg_temp.sm_diff_ordine((SELECT ordine_id FROM tmp_o2))
            + pg_temp.sm_diff_ddt((SELECT ddt_id FROM tmp_p))
            + pg_temp.sm_diff_ddt((SELECT ddt_id FROM tmp_dm))
            + pg_temp.sm_diff_ordine((SELECT ordine_id FROM tmp_om))
       FROM vendite.fn_situazione_merce_ordine(NULL, ARRAY[(SELECT ordine_id FROM tmp_o2)]) s$q$,
  $q$VALUES (13::numeric, 5::numeric, 8::numeric, 0::numeric, 2::numeric, 1, 0::bigint)$q$,
  '10) ri-consegna: consegnato 13, reso 5, tenuti 8, 2 da spedire; identica alla vista (anche i casi 3 e 9)');

-- ============================================================
-- 11) Niente da seminare
-- ============================================================
SELECT is(
  (SELECT count(*) FROM vendite.fn_situazione_merce_ordine(ARRAY[-1], NULL))::text
  || '|' || (SELECT count(*) FROM vendite.fn_situazione_merce_ordine(NULL, ARRAY[-1]))::text
  || '|' || (SELECT count(*) FROM vendite.fn_situazione_merce_ordine(ARRAY[]::bigint[], ARRAY[]::bigint[]))::text
  || '|' || ((SELECT count(*) FROM vendite.fn_situazione_merce_ordine(NULL, NULL))
             = (SELECT count(*) FROM vendite.vw_situazione_merce_ordine))::text,
  '0|0|0|true',
  '11) id inesistente e array VUOTO: zero righe — vuoto non e'' «tutte»; (NULL, NULL) lo e''');

-- ============================================================
-- CASO 5 — il fatturato che non ha ancora una merce. Ordine da 10, spedito 4,
--          fatturato 10 sull'ORDINE (trigger CONFERMATO, la configurazione del
--          cliente standard). L'allocazione sulla merce ha per capienza il
--          CONSEGNATO: 4 alla partita, 6 restano `fatturato_anticipato`. Il
--          saldo NON li vede — differenza 0, PAREGGIATA — perche' un -6 senza
--          reso non e' un accredito dovuto: e' merce da spedire (da_spedire 6).
--          ⚠️ Il contatore ritirato (vw_contatore_merce) qui diceva -6: era la
--          «parita'» del vecchio conto, e la ragione per cui il pannello
--          leggeva la situazione e non lui.
-- ============================================================
CREATE TEMP TABLE tmp_o5 AS SELECT * FROM pg_temp.sm_mk_ordine(10, (SELECT stato_ord_conf_id FROM tmp_refs_sm));
CREATE TEMP TABLE tmp_d5 AS SELECT * FROM pg_temp.sm_mk_ddt((SELECT ordine_id FROM tmp_o5), (SELECT ordine_riga_id FROM tmp_o5), 4, DATE '2026-08-16');
SELECT pg_temp.sm_mk_af(script.fn_segment_key('ORDINE_VENDITA', (SELECT ordine_uid FROM tmp_o5)::text, (SELECT ordine_riga_id FROM tmp_o5)), 10);

SELECT results_eq(
  $q$SELECT s.consegnato, s.fatturato_da_ordine, s.fatturato_anticipato, s.differenza, s.stato::text, s.da_spedire
       FROM vendite.fn_situazione_merce_ordine(NULL, ARRAY[(SELECT ordine_id FROM tmp_o5)]) s$q$,
  $q$VALUES (4::numeric, 4::numeric, 6::numeric, 0::numeric, 'PAREGGIATA', 6::numeric)$q$,
  '13) spedito 4 di 10 e fatturato 10 sull''ordine: allocato 4, fatturato_anticipato 6, differenza 0 PAREGGIATA, 6 da spedire');

-- ============================================================
-- 12) Scope: chi non vede l'ordine non vede la situazione.
-- ⚠️ Con la veste OPERATORE e un utente senza whitelist la RLS non fa vedere
--    l'ordine, e la funzione — INVOKER — risponde ZERO righe, non conti a zero.
-- ============================================================
SELECT set_config('app.current_user_id', '999999999', true);

SELECT is(
  (SELECT count(*) FROM vendite.fn_situazione_merce_ordine(NULL, ARRAY[(SELECT ordine_id FROM tmp_o1)])),
  0::bigint,
  '12) scope che non vede l''ordine: la situazione sparisce, non esce con dei conti a zero');

SELECT * FROM finish();
ROLLBACK;
