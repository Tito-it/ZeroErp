-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: vendite.fn_annulla_accredito_riga_reso — l'annullo dell'accredito
--       (brief-db-note-credito-prerequisiti-be-fe §8 passo 3 / §9;
--        changeset 20260818-71)
-- ------------------------------------------------------------
-- ⛔ QUESTO FILE NON PUO' ESSERE VERDE FINCHE' 20260818-71 NON E' APPLICATO:
--    la funzione non esiste ancora nel DB. Prima dell'apply il rosso atteso e'
--    «function ... does not exist», non un difetto del test.
--
-- Indice test (1..17):
--   PARTITA A — il percorso pulito (la rettifica non viene mai emessa)
--     1) fixture: la coda vede l'accredito dovuto 3
--     2) il verbo scrive UNA coppia sul ponte
--     3) guard: motivo vuoto -> rifiuto
--     4) guard: parametro nullo -> errore di dominio (P0001)
--     5) guard: riga di reso inesistente -> rifiuto
--     6) ⭐ dopo i tre rifiuti NIENTE e' cambiato — un guard che scrive non e'
--        un guard, ed e' l'unico modo di accorgersene
--     7) l'annullo riesce e RITORNA la coppia rimossa
--     8) il ponte e' vuoto
--     9) la rettifica e' ANNULLATA, non cancellata
--    10) ⭐ LA CODA RISALE: accredito_dovuto torna 3, gia_accreditato torna 0.
--        E' l'unica prova osservabile che l'annullo ha funzionato: senza,
--        «la riga e' sparita» direbbe solo che una DELETE e' andata a buon fine
--    11) audit: l'evento ACCREDITO_ANNULLATO porta il motivo
--    12) un secondo annullo -> E_ACCREDITO_NON_TROVATO
--    13) ⭐ un secondo accredito RIESCE: la merce e' di nuovo accreditabile
--
--   PARTITA B — la semantica d'INSIEME (C-2), che il caso singolo non verifica
--    14) fixture plurale: DUE coppie e DUE rettifiche sulla stessa riga di reso
--    15) ⭐ una sola rettifica emessa -> l'annullo rifiuta ENTRAMBE
--    16) ⭐ e non ha toccato niente: tutto-o-niente, non «quel che si puo'»
--    17) ⭐ dopo il reset del lotto l'attivita' fatturabile SOPRAVVIVE sbloccata,
--        e l'annullo riesce lo stesso — «esiste una AF -> bloccato» sarebbe
--        stata la scorciatoia sbagliata (§9 D-9-3)
--    18) ⭐⭐ IL PERCORSO COMPLETO: accredito -> emissione -> reset -> annullo
--        -> LA CODA RISALE. E' l'unico test che dimostra chiuso il difetto di
--        §10, e prima del changeset 20260818-73 e' ROSSO — vedi sotto.
--
-- ⚠️ PERCHE' DUE PARTITE E NON UNA. Il caso plurale esige che le rettifiche
--    siano EMESSE, e l'emissione crea attivita_fatturabili che restano nel
--    conto della merce. La partita A tiene quindi il percorso in cui la coda
--    e' osservabile pulita (nessuna emissione), la B la semantica d'insieme.
--    Sulla B il ritorno in coda e' il TEST 18, e non e' un di piu': e' il
--    percorso che il messaggio di E_ACCREDITO_ANNULLO_NON_AMMESSO consiglia
--    all'operatore («resetta il lotto, poi annulla»). ⛔ Prima del changeset
--    20260818-73 quel test e' ROSSO, e il rosso NON e' del test: e'
--    vw_af_merce_per_riga che continua a contare l'attivita_fatturabili di una
--    rettifica ANNULLATA, quindi la partita resta pareggiata e la riga non
--    torna mai in coda (brief §10).
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: scattano al COMMIT, che qui non arriva mai (si chiude
--   in ROLLBACK). Senza questa riga il file sarebbe verde per sottrazione.
SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(18);

SET LOCAL app.ruolo_applicativo = 'OPERATORE';
SET LOCAL app.current_user_id = '1';

-- ============================================================
-- Riferimenti — ogni scelta col suo ORDER BY: senza, quale riga esca dipende
-- dal piano del planner e il test passa a giorni alterni.
-- ============================================================
CREATE TEMP TABLE tmp_refs_ann AS
SELECT
  ba.id                                        AS billing_account_id,
  ba.utility_id                                AS utility_id,
  ba.istanza_utility_id                        AS istanza_utility_id,
  script.fn_pgtap_emittente_operatore()        AS emittente_fiscale_id,
  script.fn_pgtap_emittente_sr_operatore()     AS emittente_sr_id,
  (SELECT sr.id FROM anagrafiche.soggetti_ruoli sr ORDER BY sr.id LIMIT 1)                AS soggetto_ruolo_id,
  (SELECT a.id FROM catalogo.articoli a
    WHERE a.attivo IS TRUE AND COALESCE(a.is_composito, FALSE) IS FALSE
    ORDER BY a.data_insert DESC NULLS LAST, a.id DESC LIMIT 1)                            AS articolo_id,
  (SELECT u.id FROM catalogo.unita_misura u WHERE u.attivo IS TRUE ORDER BY u.id LIMIT 1) AS uom_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1)                                AS valuta_id,
  (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1)            AS iva_id,
  (SELECT s.id FROM config.stati_doc_ordini s WHERE s.codice_interno='CONFERMATO' AND s.attivo ORDER BY s.id LIMIT 1)     AS stato_ord_conf_id,
  (SELECT s.id FROM config.stati_doc_ddt s WHERE s.codice_interno='EMESSO'     AND s.attivo ORDER BY s.id LIMIT 1)        AS stato_ddt_emesso_id,
  (SELECT s.id FROM config.stati_doc_ddt s WHERE s.codice_interno='SPEDITO'    AND s.attivo ORDER BY s.id LIMIT 1)        AS stato_ddt_spedito_id,
  (SELECT s.id FROM config.stati_doc_ddt s WHERE s.codice_interno='CONSEGNATO' AND s.attivo ORDER BY s.id LIMIT 1)        AS stato_ddt_consegnato_id,
  (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno='DDT_VENDITA' AND s.attivo ORDER BY s.id LIMIT 1)            AS sorgente_ddt_id,
  (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno='COMMESSA'    AND s.attivo ORDER BY s.id LIMIT 1)            AS sorgente_root_id,
  (SELECT s.id FROM config.stati_doc_reso s WHERE s.codice_interno='DRAFT' AND s.attivo ORDER BY s.id LIMIT 1)            AS stato_reso_draft_id,
  (SELECT t.id FROM config.tipi_reso t WHERE t.codice_interno='RESO_A_CREDITO' AND t.attivo ORDER BY t.id LIMIT 1)        AS tipo_credito_id,
  (SELECT t.id FROM config.tipi_doc_fiscale t WHERE t.attivo IS TRUE ORDER BY t.id LIMIT 1)                               AS tipo_doc_fiscale_id,
  (SELECT s.id FROM config.stati_doc_fiscale s WHERE s.codice_interno='DRAFT' AND s.attivo IS TRUE ORDER BY s.id LIMIT 1) AS stato_fatt_draft_id,
  (SELECT r.id FROM vendite.registri_fatturazione r WHERE r.attivo IS TRUE ORDER BY r.id LIMIT 1)                         AS registro_id,
  (SELECT c.id FROM config.causali_trasporto c WHERE c.codice='VENDITA' ORDER BY c.id LIMIT 1)                            AS causale_vendita_id,
  (SELECT id FROM config.tipi_indirizzi WHERE codice_interno='CON')                                                       AS tipo_ind_con_id,
  config.fn_get_natura_doc_fiscale_id('NOTA_CREDITO')                                                                     AS natura_nc_id
FROM anagrafiche.billing_account ba
WHERE ba.utility_id IS NOT NULL AND ba.istanza_utility_id IS NOT NULL
  AND anagrafiche.fn_get_emittente_fiscale_id(ba.id) IS NOT NULL
ORDER BY ba.id
LIMIT 1;

-- ============================================================
-- Helper di fixture (stessa forma di test-fn-accredita-riga-reso-v1)
-- ⚠️ Padre e figlio in DUE istruzioni, mai in una CTE sola: le CTE che
--    scrivono condividono la stessa snapshot e una policy che risolve il
--    perimetro dal padre non lo trova, negando fail-closed.
-- ============================================================
CREATE OR REPLACE FUNCTION pg_temp.ann_mk_partita(p_qta numeric, p_prezzo numeric)
RETURNS TABLE(ordine_riga_id bigint, ddt_id bigint, ddt_uid uuid, ddt_riga_id bigint) AS $$
DECLARE r RECORD; v_ord bigint; v_orr bigint; v_ddt bigint; v_uid uuid; v_ddtr bigint;
BEGIN
  SELECT * INTO r FROM tmp_refs_ann;
  INSERT INTO vendite.ordini (soggetto_ruolo_id, billing_account_id, stato_doc_ordine_id,
    valuta_id, data, fatturazione_trigger, emittente_fiscale_id, storicizza, meta)
  VALUES (r.soggetto_ruolo_id, r.billing_account_id, r.stato_ord_conf_id, r.valuta_id,
          DATE '2026-07-15', 'CONSEGNATO', r.emittente_fiscale_id, false,
          jsonb_build_object('test_scope','pgtap_fn_annulla_accredito'))
  RETURNING id INTO v_ord;
  UPDATE vendite.ordini SET fatturazione_trigger = 'CONSEGNATO' WHERE id = v_ord;

  INSERT INTO vendite.ordini_righe (ordine_id, riga_nr, articolo_id, descrizione,
    qta_operativa, quantita, prezzo_unitario, iva_id, attivo, storicizza, meta)
  VALUES (v_ord, 1, r.articolo_id, 'Riga annullo accredito pgTAP', p_qta, p_qta, p_prezzo,
          r.iva_id, true, false, jsonb_build_object('test_scope','pgtap_fn_annulla_accredito'))
  RETURNING id INTO v_orr;

  v_ddt := vendite.fn_genera_ddt_da_ordine(v_ord);
  INSERT INTO vendite.ddt_indirizzi (ddt_id, tipo_indirizzo_id, snapshot)
  VALUES (v_ddt, r.tipo_ind_con_id, '{"display":"CON"}'::jsonb) ON CONFLICT DO NOTHING;
  UPDATE vendite.ddt SET causale_trasporto_id = r.causale_vendita_id      WHERE id = v_ddt;
  UPDATE vendite.ddt SET stato_doc_ddt_id     = r.stato_ddt_emesso_id     WHERE id = v_ddt;
  UPDATE vendite.ddt SET stato_doc_ddt_id     = r.stato_ddt_spedito_id    WHERE id = v_ddt;
  UPDATE vendite.ddt SET stato_doc_ddt_id     = r.stato_ddt_consegnato_id WHERE id = v_ddt;

  SELECT d.uid INTO v_uid  FROM vendite.ddt d        WHERE d.id = v_ddt;
  SELECT dr.id INTO v_ddtr FROM vendite.ddt_righe dr WHERE dr.ddt_id = v_ddt ORDER BY dr.id LIMIT 1;
  RETURN QUERY SELECT v_orr, v_ddt, v_uid, v_ddtr;
END $$ LANGUAGE plpgsql;

-- La merce viene FATTURATA per intero: e' la catena che la madre risale per
-- copiare il prezzo. Senza `fattura_riga_id` l'accredito e' impossibile.
CREATE OR REPLACE FUNCTION pg_temp.ann_fattura(p_segment varchar, p_qta numeric, p_prezzo numeric)
RETURNS bigint AS $$
DECLARE r RECORD; v_af bigint; v_fatt bigint; v_riga bigint;
BEGIN
  SELECT * INTO r FROM tmp_refs_ann;

  PERFORM vendite.fn_upsert_commessa_attivita(
    p_commessa_id                   => (SELECT commessa_id FROM tmp_com_ann),
    p_segment_key                   => p_segment,
    p_articolo_id                   => r.articolo_id,
    p_istanza_utility_id            => r.istanza_utility_id,
    p_data_attivita                 => DATE '2026-07-15',
    p_uom_id                        => r.uom_id,
    p_quantita                      => p_qta,
    p_competenza_mese               => DATE '2026-07-01',
    p_competenza_dal                => DATE '2026-07-01',
    p_competenza_al                 => DATE '2026-07-31',
    p_prezzo_snapshot               => p_prezzo,
    p_prezzo_base_snapshot          => NULL,
    p_origine_prezzo                => NULL,
    p_tipo_variazione_applicata     => NULL,
    p_valore_variazione_applicata   => NULL,
    p_promo_id                      => NULL,
    p_contratto_id                  => NULL,
    p_categoria_cliente_id_snapshot => NULL,
    p_classe_utenza_id_snapshot     => NULL,
    p_tipo_doc_fiscale_id           => r.tipo_doc_fiscale_id,
    p_valuta_id                     => r.valuta_id,
    p_stato_approvazione            => 'APPROVATA',
    p_stato_emissione               => 'NON_EMESSA',
    p_tipo_movimento                => 'NORMALE');

  PERFORM vendite.fn_emit_attivita_fatturabili_da_commessa(
      (SELECT commessa_id FROM tmp_com_ann), true, false);

  SELECT af.id INTO v_af
    FROM vendite.attivita_fatturabili af
    JOIN vendite.commesse_attivita ca ON ca.id = af.commessa_attivita_id
   WHERE ca.segment_key = p_segment
   ORDER BY af.id DESC LIMIT 1;

  INSERT INTO vendite.fatture (registro_id, data, tipo_doc_fiscale_id, stato_doc_fiscale_id,
      emittente_soggetto_ruolo_id, billing_account_id, utility_id, valuta_id, tasso_cambio, meta)
  VALUES (r.registro_id, DATE '2026-07-31', r.tipo_doc_fiscale_id, r.stato_fatt_draft_id,
      r.emittente_sr_id, r.billing_account_id, r.utility_id, r.valuta_id, 1,
      jsonb_build_object('test_scope','pgtap_fn_annulla_accredito'))
  RETURNING id INTO v_fatt;

  INSERT INTO vendite.fatture_righe (fattura_id, riga_nr, articolo_id, descrizione,
      uom_id, qta, prezzo_unitario, iva_id, imponibile_riga)
  VALUES (v_fatt, 1, r.articolo_id, 'Riga fattura pgTAP', r.uom_id, p_qta, p_prezzo,
      r.iva_id, p_qta * p_prezzo)
  RETURNING id INTO v_riga;

  UPDATE vendite.attivita_fatturabili
     SET fattura_riga_id = v_riga, fatturato = true
   WHERE id = v_af;

  RETURN v_riga;
END $$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION pg_temp.ann_mk_reso(p_ddt_riga bigint, p_ddt_uid uuid, p_qta numeric)
RETURNS bigint AS $$
DECLARE r RECORD; v_reso bigint; v_riga bigint;
BEGIN
  SELECT * INTO r FROM tmp_refs_ann;
  INSERT INTO vendite.resi (stato_doc_reso_id, sorgente_tipo_id, sorgente_uid, storicizza, meta)
  VALUES (r.stato_reso_draft_id, r.sorgente_ddt_id, p_ddt_uid, false,
          jsonb_build_object('test_scope','pgtap_fn_annulla_accredito'))
  RETURNING id INTO v_reso;

  INSERT INTO vendite.resi_righe (reso_id, riga_nr, ddt_riga_id, ordine_riga_id,
      articolo_id, descrizione, qta_operativa, uom_operativa_id, factor_to_base,
      tipo_reso_id, storicizza)
  SELECT v_reso, 1, dr.id,
         (SELECT f.ordine_riga_id FROM vendite.ordini_righe_fulfillment f
           WHERE f.ddt_riga_id = dr.id ORDER BY f.id LIMIT 1),
         dr.articolo_id, dr.descrizione, p_qta, dr.uom_operativa_id, dr.factor_to_base,
         r.tipo_credito_id, false
    FROM vendite.ddt_righe dr WHERE dr.id = p_ddt_riga
  RETURNING id INTO v_riga;

  PERFORM vendite.fn_conferma_reso(v_reso);
  RETURN v_riga;
END $$ LANGUAGE plpgsql;

-- Il reset del lotto, nella forma esatta in cui lo fa
-- vendite.fn_cleanup_fatture_by_ids (RD-4): l'attivita' torna NON_EMESSA e
-- l'attivita_fatturabili SOPRAVVIVE, sbloccata e senza fattura_riga_id.
-- ⭐ E' proprio questa sopravvivenza che il test 17 mette alla prova.
CREATE OR REPLACE FUNCTION pg_temp.ann_reset_lotto(p_ca_id bigint)
RETURNS void AS $$
BEGIN
  UPDATE vendite.attivita_fatturabili
     SET lock_in_fatturazione = false, lock_batch_id = NULL,
         fattura_riga_id = NULL, fatturato = false
   WHERE commessa_attivita_id = p_ca_id;
  UPDATE vendite.commesse_attivita
     SET stato_emissione = 'NON_EMESSA'
   WHERE id = p_ca_id;
END $$ LANGUAGE plpgsql;

-- ============================================================
-- COMMESSA + PARTITA A: consegnati 10 a 25, fatturati 10, resi 3
--                       -> tenuti 7, fatturati 10 -> accredito dovuto 3
-- ============================================================
CREATE TEMP TABLE tmp_com_ann AS
SELECT vendite.fn_get_or_create_commessa(
  p_billing_account_id     => (SELECT billing_account_id FROM tmp_refs_ann),
  p_utility_id             => (SELECT utility_id FROM tmp_refs_ann),
  p_tipo_commessa          => 'AUTO',
  p_policy_fatturazione    => 'DA_DOCUMENTO',
  p_fatturazione_immediata => false,
  p_priorita_operativa     => 'NORMALE',
  p_competenza_dal         => DATE '2026-07-01',
  p_competenza_al          => DATE '2026-07-31',
  p_meta                   => '{}'::jsonb,
  p_force_new              => true) AS commessa_id;

SELECT vendite.fn_link_commessa_sorgente(
  p_commessa_id      => (SELECT commessa_id FROM tmp_com_ann),
  p_sorgente_tipo_id => (SELECT sorgente_root_id FROM tmp_refs_ann),
  p_sorgente_uid     => (SELECT commessa_id FROM tmp_com_ann)::text,
  p_sorgente_riga    => 1,
  p_meta             => '{}'::jsonb);

CREATE TEMP TABLE tmp_pa AS SELECT * FROM pg_temp.ann_mk_partita(10, 25);
CREATE TEMP TABLE tmp_pa_fattura AS
SELECT pg_temp.ann_fattura(
    ('DDT:' || (SELECT ddt_uid FROM tmp_pa)::text || ':R:' || (SELECT ddt_riga_id FROM tmp_pa)::text)::varchar,
    10, 25) AS fattura_riga_id;
CREATE TEMP TABLE tmp_pa_reso AS
SELECT pg_temp.ann_mk_reso((SELECT ddt_riga_id FROM tmp_pa), (SELECT ddt_uid FROM tmp_pa), 3) AS resi_riga_id;

SELECT is(
  (SELECT q.accredito_dovuto FROM vendite.vw_resi_da_accreditare q
    WHERE q.resi_riga_id = (SELECT resi_riga_id FROM tmp_pa_reso)),
  3::numeric,
  '1) fixture: la partita e'' in coda accrediti con accredito dovuto 3'
);

-- ⭐ Si passa DALLA MADRE, non si inserisce la coppia a mano: un ramo si
--    verifica dal percorso che lo attraversa, non dal codice che lo dichiara.
CREATE TEMP TABLE tmp_acc_a AS
SELECT * FROM vendite.fn_accredita_riga_reso((SELECT resi_riga_id FROM tmp_pa_reso));

SELECT is(
  (SELECT count(*)::int FROM vendite.resi_righe_accrediti a
    WHERE a.resi_riga_id = (SELECT resi_riga_id FROM tmp_pa_reso)),
  1,
  '2) il verbo ha scritto UNA coppia sul ponte (la partita ha una sola riga di fattura)'
);

-- ============================================================
-- I RIFIUTI. ⚠️ SQLSTATE o frase, mai throws_ok nudo: senza discriminante
--    accetterebbe qualunque errore, anche il crash del guard stesso.
-- ============================================================
SELECT throws_like(
  format($$ SELECT * FROM vendite.fn_annulla_accredito_riga_reso(%s, '   ') $$,
         (SELECT resi_riga_id FROM tmp_pa_reso)),
  '%motivo%',
  '3) il motivo e'' obbligatorio: l''annullo cancella, e senza motivo resta il fatto senza la ragione'
);

SELECT throws_ok(
  $$ SELECT * FROM vendite.fn_annulla_accredito_riga_reso(NULL, 'motivo') $$,
  'P0001', NULL,
  '4) guard sul parametro: id nullo -> errore di dominio, mai normalizzazione silenziosa'
);

SELECT throws_like(
  $$ SELECT * FROM vendite.fn_annulla_accredito_riga_reso(999999999, 'motivo') $$,
  '%valore%',
  '5) riga di reso inesistente -> rifiuto parlante, non un insieme vuoto trattato come «niente da fare»'
);

-- ⭐ La verifica che i tre rifiuti non abbiano lasciato tracce. Un guard che
--    scrive prima di rifiutare passa inosservato per anni: e' l'unica forma in
--    cui il difetto si vede.
SELECT is(
  (SELECT count(*)::int FROM vendite.resi_righe_accrediti a
     WHERE a.resi_riga_id = (SELECT resi_riga_id FROM tmp_pa_reso))::text
  || '|' ||
  (SELECT ca.stato_emissione FROM vendite.commesse_attivita ca
     WHERE ca.id = (SELECT commessa_attivita_id FROM tmp_acc_a)),
  '1|NON_EMESSA',
  '6) dopo i tre rifiuti NIENTE e'' cambiato: la coppia c''e'' e la rettifica e'' ancora da emettere'
);

-- ============================================================
-- L'ANNULLO
-- ============================================================
CREATE TEMP TABLE tmp_ann_a AS
SELECT * FROM vendite.fn_annulla_accredito_riga_reso(
    (SELECT resi_riga_id FROM tmp_pa_reso), 'riga sbagliata, pgTAP');

SELECT is(
  (SELECT count(*)::int || '|' || (min(commessa_attivita_id) = (SELECT commessa_attivita_id FROM tmp_acc_a))::text
     FROM tmp_ann_a),
  '1|true',
  '7) l''annullo ritorna la coppia rimossa, nella stessa forma con cui la madre l''aveva creata'
);

SELECT is(
  (SELECT count(*)::int FROM vendite.resi_righe_accrediti a
    WHERE a.resi_riga_id = (SELECT resi_riga_id FROM tmp_pa_reso)),
  0,
  '8) il ponte e'' vuoto: la coppia si CANCELLA, non si marca (da qui dipende il gate della rinuncia)'
);

SELECT is(
  (SELECT ca.stato_emissione FROM vendite.commesse_attivita ca
    WHERE ca.id = (SELECT commessa_attivita_id FROM tmp_acc_a)),
  'ANNULLATA'::varchar,
  '9) la rettifica e'' ANNULLATA e non cancellata: resta con importo e storia, smette solo di essere eleggibile'
);

-- ============================================================
-- 10) ⭐ L'ASSERZIONE CHE CONTA. «La riga e' sparita» direbbe solo che una
--     DELETE e' andata a buon fine; che l'annullo abbia FUNZIONATO lo dice la
--     coda, ed e' l'unico effetto osservabile dall'operatore.
-- ============================================================
-- ⚠️ Confronto NUMERICO e non testuale: la scala con cui la vista compone
--    accredito_dovuto non e' un contratto, e '3.000000' vs '3.0' renderebbe
--    rosso un test corretto. Se la riga non torna in coda, il risultato e'
--    NULL e ok() fallisce — che e' esattamente cio' che si vuole vedere.
SELECT ok(
  (SELECT q.accredito_dovuto = 3::numeric AND q.gia_accreditato = 0::numeric
     FROM vendite.vw_resi_da_accreditare q
    WHERE q.resi_riga_id = (SELECT resi_riga_id FROM tmp_pa_reso)),
  '10) LA CODA RISALE: l''accredito torna dovuto per intero e il gia'' accreditato torna a zero'
);

SELECT is(
  (SELECT l.dettaglio ->> 'motivo' FROM vendite.commesse_attivita_log l
    WHERE l.commessa_attivita_id = (SELECT commessa_attivita_id FROM tmp_acc_a)
      AND l.evento = 'ACCREDITO_ANNULLATO'
    ORDER BY l.id DESC LIMIT 1),
  'riga sbagliata, pgTAP',
  '11) audit: l''evento ACCREDITO_ANNULLATO porta il motivo — unica traccia del perche'''
);

SELECT throws_like(
  format($$ SELECT * FROM vendite.fn_annulla_accredito_riga_reso(%s, 'ancora') $$,
         (SELECT resi_riga_id FROM tmp_pa_reso)),
  '%nessun accredito%',
  '12) un secondo annullo non trova nulla: dopo il primo, «mai accreditato» e «gia'' annullato» sono lo stesso stato'
);

-- ⭐ La prova finale: la merce e' di nuovo accreditabile DAVVERO, non solo
--    «sembra» libera. Se il ponte non fosse stato cancellato, la madre
--    solleverebbe ancora E_ACCREDITO_GIA_ESEGUITO.
SELECT is(
  (SELECT count(*)::int FROM vendite.fn_accredita_riga_reso((SELECT resi_riga_id FROM tmp_pa_reso))),
  1,
  '13) un secondo accredito RIESCE: e'' la prova che l''annullo ha restituito la merce alla coda'
);

-- ============================================================
-- PARTITA B — LA SEMANTICA D'INSIEME (C-2)
--   Senza questo blocco una fixture a UNA sola rettifica passerebbe anche con
--   la versione sbagliata della funzione, quella che annulla «quel che puo'».
-- ============================================================
CREATE TEMP TABLE tmp_pb AS SELECT * FROM pg_temp.ann_mk_partita(10, 25);
CREATE TEMP TABLE tmp_pb_fattura AS
SELECT pg_temp.ann_fattura(
    ('DDT:' || (SELECT ddt_uid FROM tmp_pb)::text || ':R:' || (SELECT ddt_riga_id FROM tmp_pb)::text)::varchar,
    10, 25) AS fattura_riga_id;
CREATE TEMP TABLE tmp_pb_reso AS
SELECT pg_temp.ann_mk_reso((SELECT ddt_riga_id FROM tmp_pb), (SELECT ddt_uid FROM tmp_pb), 3) AS resi_riga_id;

CREATE TEMP TABLE tmp_acc_b AS
SELECT * FROM vendite.fn_accredita_riga_reso((SELECT resi_riga_id FROM tmp_pb_reso));

-- La SECONDA coppia. ⚠️ Costruita qui e non attesa dalla madre: il plurale
--   nasce dal consumo LIFO su piu' righe di fattura o dai componenti di un
--   kit, e nessuna delle due forme si fissa in una fixture senza inseguire
--   l'aritmetica della coda. Cio' che si collauda qui e' la semantica
--   dell'ANNULLO, il cui ingresso e' il ponte — e la seconda rettifica nasce
--   comunque da fn_upsert_commessa_attivita, la stessa che usa la madre.
-- ⚠️ L'INSERT ... RETURNING sta in una CTE e non in una sottoquery del FROM:
--    PostgreSQL ammette gli statement che scrivono SOLO dentro un WITH.
--    ⛔ E la fattura padre e' gia' stata scritta da un'istruzione PRECEDENTE:
--    padre e figlio nella stessa CTE condividerebbero la snapshot, e la policy
--    che risolve il perimetro dal padre non lo troverebbe.
CREATE TEMP TABLE tmp_pb_riga2 AS
WITH ins AS (
  INSERT INTO vendite.fatture_righe (fattura_id, riga_nr, articolo_id, descrizione,
      uom_id, qta, prezzo_unitario, iva_id, imponibile_riga)
  SELECT fr.fattura_id, 2, r.articolo_id, 'Seconda riga fattura pgTAP', r.uom_id, 5, 25,
         r.iva_id, 125
    FROM vendite.fatture_righe fr, tmp_refs_ann r
   WHERE fr.id = (SELECT fattura_riga_id FROM tmp_pb_fattura)
  RETURNING id)
SELECT id AS fattura_riga_id FROM ins;

CREATE TEMP TABLE tmp_pb_ret2 AS
SELECT u.attivita_id AS commessa_attivita_id
  FROM tmp_refs_ann r,
       vendite.fn_upsert_commessa_attivita(
         p_commessa_id                 => (SELECT commessa_id FROM tmp_com_ann),
         p_segment_key                 => ('DDT:' || (SELECT ddt_uid FROM tmp_pb)::text
                                            || ':R:' || (SELECT ddt_riga_id FROM tmp_pb)::text
                                            || '#RET:2')::varchar,
         p_articolo_id                 => r.articolo_id,
         p_istanza_utility_id          => r.istanza_utility_id,
         p_data_attivita               => DATE '2026-07-31',
         p_uom_id                      => r.uom_id,
         p_quantita                    => -1,
         p_competenza_mese             => DATE '2026-07-01',
         p_competenza_dal              => DATE '2026-07-31',
         p_competenza_al               => DATE '2026-07-31',
         p_prezzo_snapshot             => 25,
         p_prezzo_base_snapshot        => 25,
         p_origine_prezzo              => 'MANUALE',
         -- ⚠️ I primi 19 parametri della upsert NON hanno DEFAULT: vanno
         --    passati tutti, anche quelli che qui non dicono nulla.
         p_tipo_variazione_applicata     => 'NESSUNA',
         p_valore_variazione_applicata   => NULL,
         p_promo_id                      => NULL,
         p_contratto_id                  => NULL,
         p_categoria_cliente_id_snapshot => NULL,
         p_classe_utenza_id_snapshot     => NULL,
         p_tipo_doc_fiscale_id         => r.tipo_doc_fiscale_id,
         p_valuta_id                   => r.valuta_id,
         p_prezzo_bloccato             => true,
         p_pricing_mode                => 'FIXED',
         p_stato_approvazione          => 'APPROVATA',
         p_stato_emissione             => 'NON_EMESSA',
         p_tipo_movimento              => 'RETTIFICA',
         p_natura_doc_id               => r.natura_nc_id,
         p_fattura_riga_rettificata_id => (SELECT fattura_riga_id FROM tmp_pb_riga2)) AS u;

INSERT INTO vendite.resi_righe_accrediti
       (resi_riga_id, fattura_riga_rettificata_id, qta, qta_partita, gruppo, commessa_attivita_id, meta)
SELECT (SELECT resi_riga_id FROM tmp_pb_reso),
       (SELECT fattura_riga_id FROM tmp_pb_riga2),
       1, 1,
       ('DDT:' || (SELECT ddt_uid FROM tmp_pb)::text || ':R:' || (SELECT ddt_riga_id FROM tmp_pb)::text || '#RET:2')::varchar,
       (SELECT commessa_attivita_id FROM tmp_pb_ret2),
       '{}'::jsonb;

SELECT is(
  (SELECT count(*)::int FROM vendite.resi_righe_accrediti a
     WHERE a.resi_riga_id = (SELECT resi_riga_id FROM tmp_pb_reso))::text
  || '|' ||
  (SELECT count(DISTINCT a.commessa_attivita_id)::int FROM vendite.resi_righe_accrediti a
     WHERE a.resi_riga_id = (SELECT resi_riga_id FROM tmp_pb_reso))::text,
  '2|2',
  '14) fixture plurale: la riga di reso porta DUE coppie e DUE rettifiche'
);

-- Le rettifiche vengono EMESSE, poi si resetta SOLO la prima: resta una
-- rettifica emessa e una che ha attraversato il reset.
SELECT vendite.fn_emit_attivita_fatturabili_da_commessa(
    (SELECT commessa_id FROM tmp_com_ann), true, false);
SELECT pg_temp.ann_reset_lotto((SELECT commessa_attivita_id FROM tmp_acc_b));

SELECT throws_like(
  format($$ SELECT * FROM vendite.fn_annulla_accredito_riga_reso(%s, 'ci ho ripensato') $$,
         (SELECT resi_riga_id FROM tmp_pb_reso)),
  '%gia'' emesse%',
  '15) UNA sola rettifica emessa basta a rifiutare l''INTERO annullo: la decisione e'' d''insieme'
);

SELECT is(
  (SELECT count(*)::int FROM vendite.resi_righe_accrediti a
     WHERE a.resi_riga_id = (SELECT resi_riga_id FROM tmp_pb_reso))::text
  || '|' ||
  (SELECT ca.stato_emissione FROM vendite.commesse_attivita ca
     WHERE ca.id = (SELECT commessa_attivita_id FROM tmp_acc_b)),
  '2|NON_EMESSA',
  '16) e il rifiuto non ha toccato NIENTE: tutto-o-niente, non «quel che si puo''»'
);

-- ============================================================
-- 17) ⭐ Reset anche della seconda. Le attivita_fatturabili SOPRAVVIVONO al
--     reset (fn_cleanup_fatture_by_ids le sblocca e azzera fattura_riga_id,
--     non le cancella): se la funzione avesse scritto la scorciatoia «esiste
--     una AF -> bloccato», qui rifiuterebbe per sempre un annullo legittimo.
-- ============================================================
SELECT pg_temp.ann_reset_lotto((SELECT commessa_attivita_id FROM tmp_pb_ret2));

-- ⚠️ Il verbo si chiama in un'ISTRUZIONE A PARTE, mai dentro la SELECT che ne
--    verifica gli effetti. Sotto READ COMMITTED tutte le sottoquery di uno
--    stesso statement condividono la snapshot presa al suo inizio: la
--    `count(*)` sul ponte leggerebbe lo stato PRIMA della DELETE e il test
--    fallirebbe accusando la funzione di non aver fatto nulla. E' la stessa
--    trappola delle CTE che scrivono, in un'altra veste.
CREATE TEMP TABLE tmp_ann_b AS
SELECT * FROM vendite.fn_annulla_accredito_riga_reso(
    (SELECT resi_riga_id FROM tmp_pb_reso), 'dopo il reset del lotto');

SELECT is(
  (SELECT count(*)::int FROM tmp_ann_b)::text
  || '|' ||
  (SELECT count(*)::int FROM vendite.resi_righe_accrediti a
     WHERE a.resi_riga_id = (SELECT resi_riga_id FROM tmp_pb_reso))::text
  || '|' ||
  (SELECT count(*)::int FROM vendite.commesse_attivita ca
     WHERE ca.id IN ((SELECT commessa_attivita_id FROM tmp_acc_b),
                     (SELECT commessa_attivita_id FROM tmp_pb_ret2))
       AND ca.stato_emissione = 'ANNULLATA'),
  '2|0|2',
  '17) l''AF sopravvissuta al reset NON blocca: l''annullo toglie entrambe le coppie e annulla entrambe le rettifiche'
);

-- ============================================================
-- 18) ⭐⭐ LA CHIUSURA DEL CERCHIO. Il test 10 mostra che la coda risale sul
--     percorso pulito; questo lo mostra sul percorso che l'errore stesso
--     consiglia — accredito, emissione, reset del lotto, annullo.
--     ⚠️ Le due rettifiche della partita B hanno lasciato ciascuna la propria
--     attivita_fatturabili, sopravvissuta al reset. Se il conto della merce
--     continuasse a sommarle, la partita resterebbe pareggiata e questa riga
--     non tornerebbe MAI accreditabile da nessuno: il ponte e' vuoto, ma la
--     merce e' persa. E' il difetto di §10, e questo test e' la sua misura.
--     ⛔ Rosso prima del changeset 20260818-73, verde dopo.
-- ============================================================
SELECT ok(
  (SELECT q.accredito_dovuto = 3::numeric AND q.gia_accreditato = 0::numeric
     FROM vendite.vw_resi_da_accreditare q
    WHERE q.resi_riga_id = (SELECT resi_riga_id FROM tmp_pb_reso)),
  '18) percorso completo (accredito -> emissione -> reset -> annullo): LA CODA RISALE, e la merce resa torna accreditabile'
);

SELECT * FROM finish();
ROLLBACK;
