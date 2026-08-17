-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: vendite.vw_situazione_merce_ordine — l'aggregato PARLANTE per riga
--       d'ordine, per il pannello situazione merce.
--       (brief-db-situazione-merce-ordine-aggregato.md, changeSet 20260817-15)
--
-- Elenco test (plan 11):
--   1) la vista esiste
--   2) e' security_invoker=on
--   3) espone le colonne del contratto
--   4) riga d'ordine MAI SPEDITA: c'e', partite_merce 0, differenza NULL,
--      stato NON_SPEDITA
--   5) riga mai spedita: da_spedire = ordinato
--   6) ⭐ tutte le partite NON fatturabili -> differenza NULL, NON `tenuti`
--   7) partite MISTE -> somma dei soli conti che si applicano
--   8) ⭐ `da_spedire` viene dal residuo ESISTENTE: evaso = ordinato ma un reso
--      per ri-consegna e' pendente -> 3, non 0
--   9) la RI-CONSEGNA emessa non conta due volte, e da_spedire torna a 0
--  10) kit senza `coeff_qta` sulla corsia ORD -> misurabile false, differenza NULL
--  11) scope ristretto: la riga SPARISCE, non esce a zero
--
-- Scopo:
--  - il 6) e' il ramo che **nessun dato attraversa oggi** e che il perimetro
--    BE ha chiesto esplicitamente di costruire: su una riga d'ordine le cui
--    partite sono tutte NON_FATTURABILE, `vw_contatore_merce` direbbe
--    «N da fatturare» (fa `tenuti − 0`). Qui deve dire «non si applica».
--  - l' 8) presidia la correzione piu' importante rispetto alla richiesta
--    originale. `GREATEST(0, ordinato − consegnato)` avrebbe dato 0 su questa
--    fixture, mentre l'ordine deve ancora spedire: il `consegnato` delle
--    partite include le ri-consegne e non e' comparabile con l'ordinato.
--    Il caso e' quello reale della riga d'ordine 18946 (ORD0018586).
--  - l' 11) presidia la regola «zero non e' un dato»: se lo scope nasconde
--    l'ordine, la riga non deve uscire con dei conti a zero.
--    ⭐ E ha gia' fatto il suo mestiere: la prima versione della vista partiva
--    da `vendite.ordini_righe`, che NON ha policy — la RLS sta su
--    `vendite.ordini`. Un utente fuori scope avrebbe visto TUTTE le 107 righe
--    con i conti a zero, perche' le partite erano nascoste e i COALESCE le
--    trasformavano in zeri. Il `JOIN vendite.ordini` della vista esiste per
--    questo.
--    ⚠️ Questo test ha senso SOLO col runner applicativo (il default dal
--    2026-08-07): l'owner salta la RLS e lo vedrebbe passare per finta.
-- ------------------------------------------------------------

-- ⚠️ 1. TRANSAZIONE. Senza, un fallimento a meta' lascia i dati di prova nel
--   database e rompe la corsa successiva, che vede un rosso non suo.
BEGIN;

-- ⚠️ 2. VINCOLI DIFFERITI. Scattano al COMMIT, e qui il COMMIT non arriva mai:
--   senza questa riga il file sarebbe verde per sottrazione.
SET CONSTRAINTS ALL IMMEDIATE;

-- ⚠️ 3. CONTESTO APPLICATIVO. La vista legge ordini e ddt, che hanno RLS.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(11);

SET LOCAL app.ruolo_applicativo = 'OPERATORE';
SET LOCAL app.current_user_id = '1';

-- ============================================================
-- 1-3) Struttura
-- ============================================================
SELECT has_view('vendite', 'vw_situazione_merce_ordine', '1) la vista esiste');

SELECT ok(
  (SELECT 'security_invoker=on' = ANY(c.reloptions)
     FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'vendite' AND c.relname = 'vw_situazione_merce_ordine'),
  '2) vw_situazione_merce_ordine e'' security_invoker=on');

SELECT columns_are('vendite', 'vw_situazione_merce_ordine',
  ARRAY['ordine_riga_id','ordine_id','riga_nr','articolo_id','ordinato',
        'consegnato','reso','in_riconsegna','tenuti','fatturato_merce',
        'fatturato_da_ordine','fatturato','fatturato_anticipato','da_spedire',
        'partite_merce','misurabile','differenza','stato'],
  '3) espone le 18 colonne del contratto');

-- ============================================================
-- Riferimenti
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
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1)               AS valuta_id,
  (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1) AS iva_id,
  (SELECT ef.id FROM anagrafiche.emittenti_fiscali ef ORDER BY ef.id LIMIT 1)  AS emittente_fiscale_id,
  (SELECT s.id FROM config.stati_doc_ordini s WHERE s.codice_interno='CONFERMATO' AND s.attivo LIMIT 1) AS stato_ord_conf_id,
  (SELECT s.id FROM config.stati_doc_ddt s WHERE s.codice_interno='EMESSO' AND s.attivo LIMIT 1)     AS stato_ddt_emesso_id,
  (SELECT s.id FROM config.stati_doc_ddt s WHERE s.codice_interno='SPEDITO' AND s.attivo LIMIT 1)    AS stato_ddt_spedito_id,
  (SELECT s.id FROM config.stati_doc_ddt s WHERE s.codice_interno='CONSEGNATO' AND s.attivo LIMIT 1) AS stato_ddt_consegnato_id,
  (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno='DDT_VENDITA' AND s.attivo LIMIT 1)     AS sorgente_ddt_id,
  (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno='COMMESSA' AND s.attivo LIMIT 1)        AS sorgente_root_id,
  (SELECT s.id FROM config.stati_doc_reso s WHERE s.codice_interno='DRAFT' AND s.attivo LIMIT 1)     AS stato_reso_draft_id,
  (SELECT t.id FROM config.tipi_reso t WHERE t.codice_interno='RESO_PER_RICONSEGNA' AND t.attivo LIMIT 1) AS tipo_riconsegna_id,
  (SELECT t.id FROM config.tipi_doc_fiscale t WHERE t.attivo IS TRUE ORDER BY t.id LIMIT 1) AS tipo_doc_fiscale_id,
  (SELECT c.id FROM config.causali_trasporto c WHERE c.codice='VENDITA' LIMIT 1)       AS causale_vendita_id,
  (SELECT c.id FROM config.causali_trasporto c WHERE c.codice='CONTO_VISIONE' LIMIT 1) AS causale_non_fatt_id,
  (SELECT id FROM config.tipi_indirizzi WHERE codice_interno='CON')      AS tipo_ind_con_id;

-- Helper: crea l'ordine (una riga da p_qta) e ritorna gli id.
CREATE OR REPLACE FUNCTION pg_temp.mk_ordine(p_qta numeric)
RETURNS TABLE(ordine_id bigint, ordine_uid uuid, ordine_riga_id bigint) AS $$
DECLARE r RECORD; v_ord bigint; v_uid uuid; v_orr bigint;
BEGIN
  SELECT * INTO r FROM tmp_refs;
  INSERT INTO vendite.ordini (soggetto_ruolo_id, billing_account_id, stato_doc_ordine_id,
    valuta_id, data, fatturazione_trigger, emittente_fiscale_id, storicizza, meta)
  VALUES (r.soggetto_ruolo_id, r.billing_account_id, r.stato_ord_conf_id, r.valuta_id,
          DATE '2026-08-15', 'SPEDITO', r.emittente_fiscale_id, false,
          jsonb_build_object('test_scope','pgtap_situazione_ordine'))
  RETURNING id, uid INTO v_ord, v_uid;
  UPDATE vendite.ordini SET fatturazione_trigger='SPEDITO' WHERE id=v_ord;
  INSERT INTO vendite.ordini_righe (ordine_id, riga_nr, articolo_id, descrizione,
    qta_operativa, quantita, prezzo_unitario, iva_id, attivo, storicizza, meta)
  VALUES (v_ord, 1, r.articolo_id, 'Riga situazione', p_qta, p_qta, 25, r.iva_id, true, false,
          jsonb_build_object('test_scope','pgtap_situazione_ordine'))
  RETURNING id INTO v_orr;
  RETURN QUERY SELECT v_ord, v_uid, v_orr;
END $$ LANGUAGE plpgsql;

-- Helper: spedisce p_qta della riga d'ordine con una causale data, fino a CONSEGNATO.
CREATE OR REPLACE FUNCTION pg_temp.mk_spedizione(p_ordine bigint, p_orr bigint,
                                                 p_qta numeric, p_causale bigint)
RETURNS TABLE(ddt_id bigint, ddt_uid uuid, ddt_riga_id bigint) AS $$
DECLARE r RECORD; v_ddt bigint; v_uid uuid; v_dr bigint;
BEGIN
  SELECT * INTO r FROM tmp_refs;
  v_ddt := vendite.fn_genera_ddt_da_ordine(p_ordine,
             jsonb_build_array(jsonb_build_object('ordine_riga_id', p_orr, 'qta_da_evadere', p_qta)));
  INSERT INTO vendite.ddt_indirizzi (ddt_id, tipo_indirizzo_id, snapshot)
  VALUES (v_ddt, r.tipo_ind_con_id, '{"display":"CON"}'::jsonb) ON CONFLICT DO NOTHING;
  UPDATE vendite.ddt SET causale_trasporto_id=p_causale               WHERE id=v_ddt;
  UPDATE vendite.ddt SET stato_doc_ddt_id=r.stato_ddt_emesso_id       WHERE id=v_ddt;
  UPDATE vendite.ddt SET stato_doc_ddt_id=r.stato_ddt_spedito_id      WHERE id=v_ddt;
  UPDATE vendite.ddt SET stato_doc_ddt_id=r.stato_ddt_consegnato_id   WHERE id=v_ddt;
  SELECT d.uid INTO v_uid FROM vendite.ddt d WHERE d.id=v_ddt;
  SELECT dr.id INTO v_dr FROM vendite.ddt_righe dr WHERE dr.ddt_id=v_ddt ORDER BY dr.id LIMIT 1;
  RETURN QUERY SELECT v_ddt, v_uid, v_dr;
END $$ LANGUAGE plpgsql;

-- ============================================================
-- A) Riga MAI SPEDITA — test 4 e 5
-- ============================================================
CREATE TEMP TABLE tmp_a AS SELECT * FROM pg_temp.mk_ordine(10);

SELECT results_eq(
  $q$SELECT partite_merce, differenza, stato::text FROM vendite.vw_situazione_merce_ordine
      WHERE ordine_riga_id = (SELECT ordine_riga_id FROM tmp_a)$q$,
  $q$VALUES (0, NULL::numeric, 'NON_SPEDITA')$q$,
  '4) riga mai spedita: c''e'', 0 partite, differenza NULL, stato NON_SPEDITA');

SELECT is(
  (SELECT da_spedire FROM vendite.vw_situazione_merce_ordine
    WHERE ordine_riga_id = (SELECT ordine_riga_id FROM tmp_a)),
  10::numeric, '5) riga mai spedita: da_spedire = tutto l''ordinato');

-- ============================================================
-- B) Tutte le partite NON fatturabili — test 6
--    ⭐ Il ramo che nessun dato attraversa: `vw_contatore_merce` qui direbbe
--    «10 da fatturare» (tenuti − 0) su un conto visione.
-- ============================================================
CREATE TEMP TABLE tmp_b AS SELECT * FROM pg_temp.mk_ordine(10);
SELECT pg_temp.mk_spedizione((SELECT ordine_id FROM tmp_b), (SELECT ordine_riga_id FROM tmp_b),
                             10, (SELECT causale_non_fatt_id FROM tmp_refs));

SELECT results_eq(
  $q$SELECT tenuti, differenza, stato::text FROM vendite.vw_situazione_merce_ordine
      WHERE ordine_riga_id = (SELECT ordine_riga_id FROM tmp_b)$q$,
  $q$VALUES (10::numeric, NULL::numeric, 'NON_FATTURABILE')$q$,
  '6) tutte le partite non fatturabili: tenuti 10 ma differenza NULL, non 10');

-- ============================================================
-- C) Partite MISTE — test 7
--    4 su causale fatturabile + 6 su conto visione: il conto e' 4, non 10.
-- ============================================================
CREATE TEMP TABLE tmp_c AS SELECT * FROM pg_temp.mk_ordine(10);
SELECT pg_temp.mk_spedizione((SELECT ordine_id FROM tmp_c), (SELECT ordine_riga_id FROM tmp_c),
                             4, (SELECT causale_vendita_id FROM tmp_refs));
SELECT pg_temp.mk_spedizione((SELECT ordine_id FROM tmp_c), (SELECT ordine_riga_id FROM tmp_c),
                             6, (SELECT causale_non_fatt_id FROM tmp_refs));

SELECT results_eq(
  $q$SELECT partite_merce, tenuti, differenza FROM vendite.vw_situazione_merce_ordine
      WHERE ordine_riga_id = (SELECT ordine_riga_id FROM tmp_c)$q$,
  $q$VALUES (2, 10::numeric, 4::numeric)$q$,
  '7) partite miste: 2 partite, tenuti 10, ma il conto e'' 4 — solo cio'' che si applica');

-- ============================================================
-- D) ⭐ `da_spedire` dal residuo ESISTENTE — test 8
--    Ordine 10, spediti tutti e 10, poi 3 tornati indietro PER RI-CONSEGNA e
--    non ancora rispediti. L'ordine deve ancora 3.
--    ⚠️ `GREATEST(0, ordinato − consegnato)` darebbe 10 − 10 = 0: e' la
--    divergenza misurata sulla riga d'ordine reale 18946.
-- ============================================================
CREATE TEMP TABLE tmp_d AS SELECT * FROM pg_temp.mk_ordine(10);
CREATE TEMP TABLE tmp_d_ddt AS
SELECT * FROM pg_temp.mk_spedizione((SELECT ordine_id FROM tmp_d), (SELECT ordine_riga_id FROM tmp_d),
                                    10, (SELECT causale_vendita_id FROM tmp_refs));
CREATE TEMP TABLE tmp_d_reso AS
WITH t AS (
  INSERT INTO vendite.resi (stato_doc_reso_id, sorgente_tipo_id, sorgente_uid, storicizza, meta)
  SELECT r.stato_reso_draft_id, r.sorgente_ddt_id, (SELECT ddt_uid FROM tmp_d_ddt), false,
         jsonb_build_object('test_scope','pgtap_situazione_ordine')
  FROM tmp_refs r RETURNING id
) SELECT id AS reso_id FROM t;
INSERT INTO vendite.resi_righe (reso_id, riga_nr, ddt_riga_id, ordine_riga_id,
  articolo_id, descrizione, qta_operativa, uom_operativa_id, factor_to_base, tipo_reso_id, storicizza)
SELECT (SELECT reso_id FROM tmp_d_reso), 1, dr.id, (SELECT ordine_riga_id FROM tmp_d),
       dr.articolo_id, dr.descrizione, 3, dr.uom_operativa_id, dr.factor_to_base,
       (SELECT tipo_riconsegna_id FROM tmp_refs), false
FROM vendite.ddt_righe dr WHERE dr.id = (SELECT ddt_riga_id FROM tmp_d_ddt);
SELECT vendite.fn_conferma_reso((SELECT reso_id FROM tmp_d_reso));

SELECT results_eq(
  $q$SELECT ordinato, consegnato, da_spedire FROM vendite.vw_situazione_merce_ordine
      WHERE ordine_riga_id = (SELECT ordine_riga_id FROM tmp_d)$q$,
  $q$VALUES (10::numeric, 10::numeric, 3::numeric)$q$,
  '8) evaso = ordinato ma 3 tornati per ri-consegna: da_spedire 3, non 0 (residuo esistente)');

-- ============================================================
-- E) La RI-CONSEGNA emessa — test 9
--    I 3 pezzi rispediti tornano nel consegnato dell'ORIGINE, non aprono una
--    partita nuova, e il residuo si chiude.
-- ============================================================
CREATE TEMP TABLE tmp_e AS
SELECT vendite.fn_genera_ddt_riconsegna((SELECT reso_id FROM tmp_d_reso)) AS ddt_id;
INSERT INTO vendite.ddt_indirizzi (ddt_id, tipo_indirizzo_id, snapshot)
SELECT (SELECT ddt_id FROM tmp_e), (SELECT tipo_ind_con_id FROM tmp_refs),
       '{"display":"CON"}'::jsonb ON CONFLICT DO NOTHING;
UPDATE vendite.ddt SET causale_trasporto_id=(SELECT causale_vendita_id FROM tmp_refs) WHERE id=(SELECT ddt_id FROM tmp_e);
UPDATE vendite.ddt SET stato_doc_ddt_id=(SELECT stato_ddt_emesso_id FROM tmp_refs)     WHERE id=(SELECT ddt_id FROM tmp_e);
UPDATE vendite.ddt SET stato_doc_ddt_id=(SELECT stato_ddt_spedito_id FROM tmp_refs)    WHERE id=(SELECT ddt_id FROM tmp_e);
UPDATE vendite.ddt SET stato_doc_ddt_id=(SELECT stato_ddt_consegnato_id FROM tmp_refs) WHERE id=(SELECT ddt_id FROM tmp_e);

SELECT results_eq(
  $q$SELECT partite_merce, consegnato, da_spedire FROM vendite.vw_situazione_merce_ordine
      WHERE ordine_riga_id = (SELECT ordine_riga_id FROM tmp_d)$q$,
  $q$VALUES (1, 13::numeric, 0::numeric)$q$,
  '9) ri-consegna emessa: UNA partita (non due), consegnato 13, da_spedire 0');

-- ============================================================
-- F) Kit senza coefficiente sulla corsia ORD — test 10
--    Il conto non si sa fare: si dichiara, non si mette a zero.
-- ============================================================
CREATE TEMP TABLE tmp_f AS SELECT * FROM pg_temp.mk_ordine(5);
SELECT pg_temp.mk_spedizione((SELECT ordine_id FROM tmp_f), (SELECT ordine_riga_id FROM tmp_f),
                             5, (SELECT causale_vendita_id FROM tmp_refs));
CREATE TEMP TABLE tmp_com AS
SELECT vendite.fn_get_or_create_commessa(
  p_billing_account_id => (SELECT billing_account_id FROM tmp_refs),
  p_utility_id => (SELECT utility_id FROM tmp_refs),
  p_tipo_commessa => 'AUTO', p_policy_fatturazione => 'DA_DOCUMENTO',
  p_fatturazione_immediata => false, p_priorita_operativa => 'NORMALE',
  p_competenza_dal => DATE '2026-08-01', p_competenza_al => DATE '2026-08-31',
  p_meta => jsonb_build_object('test_scope','pgtap_situazione_ordine'), p_force_new => true
) AS commessa_id;
SELECT vendite.fn_link_commessa_sorgente(
  p_commessa_id => (SELECT commessa_id FROM tmp_com),
  p_sorgente_tipo_id => (SELECT sorgente_root_id FROM tmp_refs),
  p_sorgente_uid => (SELECT commessa_id FROM tmp_com)::text,
  p_sorgente_riga => 1, p_meta => '{}'::jsonb);
-- Componente di kit SENZA `coeff_qta`: la quantita' del padre non e' ricostruibile.
DO $mk$
DECLARE r RECORD;
BEGIN
  SELECT * INTO r FROM tmp_refs;
  PERFORM vendite.fn_upsert_commessa_attivita(
    p_commessa_id => (SELECT commessa_id FROM tmp_com),
    p_segment_key => 'ORD:' || (SELECT ordine_uid FROM tmp_f)::text || ':R:'
                     || (SELECT ordine_riga_id FROM tmp_f)::text || '#CMP:senza-coeff',
    p_articolo_id => r.articolo_id, p_istanza_utility_id => r.istanza_utility_id,
    p_data_attivita => DATE '2026-08-15', p_uom_id => r.uom_id, p_quantita => 5,
    p_competenza_mese => DATE '2026-08-01',
    p_competenza_dal => DATE '2026-08-01', p_competenza_al => DATE '2026-08-31',
    p_prezzo_snapshot => 10.0, p_prezzo_base_snapshot => NULL, p_origine_prezzo => NULL,
    p_tipo_variazione_applicata => NULL, p_valore_variazione_applicata => NULL,
    p_promo_id => NULL, p_contratto_id => NULL,
    p_categoria_cliente_id_snapshot => NULL, p_classe_utenza_id_snapshot => NULL,
    p_tipo_doc_fiscale_id => r.tipo_doc_fiscale_id,
    p_stato_approvazione => 'APPROVATA', p_stato_emissione => 'NON_EMESSA',
    p_tipo_movimento => 'NORMALE', p_tipo_consumo => 'CONGUAGLIO',
    p_meta => '{}'::jsonb, p_causale_onere_id => NULL);
END $mk$;
SELECT vendite.fn_cambia_stato_commessa((SELECT commessa_id FROM tmp_com), 'PRONTA_FATTURAZIONE');
SELECT vendite.fn_emit_attivita_fatturabili_da_commessa((SELECT commessa_id FROM tmp_com));

SELECT results_eq(
  $q$SELECT misurabile, differenza, stato::text FROM vendite.vw_situazione_merce_ordine
      WHERE ordine_riga_id = (SELECT ordine_riga_id FROM tmp_f)$q$,
  $q$VALUES (false, NULL::numeric, 'NON_MISURABILE')$q$,
  '10) kit senza coeff_qta: misurabile false e differenza NULL, non un numero');

-- ============================================================
-- 11) Scope ristretto: la riga SPARISCE, non esce a zero.
--     ⚠️ Il cancello e' `app.ruolo_applicativo`: con la veste OPERATORE e un
--     utente senza whitelist, la RLS su `ordini` non fa vedere il documento.
--     Se un giorno la vista uscisse con dei conti a zero invece che con
--     l'assenza, questo test lo direbbe — ed e' la differenza fra «non c'e'
--     nulla da fare» e «non ho il permesso di saperlo».
-- ============================================================
SELECT set_config('app.current_user_id', '999999999', true);

SELECT is(
  (SELECT COUNT(*)::int FROM vendite.vw_situazione_merce_ordine
    WHERE ordine_riga_id = (SELECT ordine_riga_id FROM tmp_d)),
  0,
  '11) scope che non vede l''ordine: la riga sparisce, non esce con dei conti a zero');

SELECT * FROM finish();
ROLLBACK;
