-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- rev 2026-10-25 (brief-db-pgtap-reso-costruito): i resi dal builder dbops.fn_pgtap_crea_reso, le ri-spedizioni da dbops.fn_pgtap_crea_ddt_riconsegna (ritirati pg_temp.ric_mk_reso e pg_temp.ric_rispedisci, con indirizzo e causale a mano); nulla della strada del reso resta scritto a mano.
-- rev 2026-10-25 (brief-db-pgtap-bolla-e-reso-costruiti, giro 1): la bolla da ordine dal builder dbops.fn_pgtap_crea_ddt_da_ordine; la bolla di ri-consegna (fn_genera_ddt_riconsegna) tiene indirizzo e causale scritti a mano, gli stati per dbops.fn_pgtap_porta_a_stato; i resi restano a mano (giro 2).
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13, 2e/L2c-1): le chiavi del push col codice della sorgente, composte da script.fn_segment_key dove la forma lo permette (le forme su piu' righe col prefisso lungo); corsia e codice del registro coi codici lunghi.
-- pgTAP test per Zero ERP
-- Test: D-NC-4 — «una ri-consegna e' merce nuova SOLO per la parte accreditata»
--       (brief-design-note-credito-resi §12.5-bis; changeset 20260818-38)
-- ------------------------------------------------------------
-- Indice test (1..8):
--   1) fixture: partita da 10 fatturata, reso 3 per ri-consegna -> in coda
--   2) ⚠️ SENZA nota di credito la regola e' INERTE: la ri-consegna resta un
--      conto vuoto (differenza NULL, stato RICONSEGNA) — e' il caso D che a
--      agosto ha fermato tutto, e deve restare verde
--   3) SENZA nota di credito la spedizione d'ORIGINE riassorbe i pezzi
--      ri-consegnati: consegnato 10 + 3 = 13
--   4) ⭐ CON la nota di credito i pezzi accreditati CAMBIANO CASA: la
--      spedizione nuova prende quota 3
--   5) ⭐ e diventa una partita vera: DA_FATTURARE per 3
--   6) ⭐ la spedizione d'origine non porta piu' quei pezzi: torna a 10, e non
--      li puo' fatturare una seconda volta (il buco di luglio resta chiuso)
--   7) ⭐ INVARIANTE: la somma dei `consegnato` non cambia mai — i pezzi si
--      spostano, non si moltiplicano
--   8) ⭐ il segmento della spedizione nuova e' LIBERA, quindi il giro di
--      fatturazione normale la vede: nessun verbo nuovo, nessuna seconda
--      pipeline
--
-- Scopo:
--  - il caso non esiste nei dati (zero righe RETTIFICA al 2026-08-17) e si
--    costruisce PASSANDO DALLA MADRE: la nota di credito la crea
--    fn_accredita_riga_reso, non un INSERT a mano. Un ramo si verifica dal
--    percorso che lo attraversa, non dal codice che lo dichiara.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(8);

SET LOCAL app.ruolo_applicativo = 'OPERATORE';
-- ⛔ rev 2026-10-13: niente app.current_user_id = '1' (in CI l'utente 1 non
--   esiste): l'operatore e' quello del contesto aperto qui sopra.

-- ============================================================
-- Riferimenti (ogni scelta col suo ORDER BY; l'emittente si DERIVA)
-- ============================================================
-- ⛔ rev 2026-10-13: il mondo si COSTRUISCE (su un DB ricostruito anagrafiche e
--   articoli sono vuoti): cliente fatturabile legato all'azienda di chi agisce
--   e articolo merce non gestito a magazzino; dal DB si legge solo il seed.
CREATE TEMP TABLE tmp_mondo_ric AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('pgTAP riconsegna dopo NC');

CREATE TEMP TABLE tmp_refs_ric AS
SELECT
  m.billing_account_id                    AS billing_account_id,
  m.utility_id                            AS utility_id,
  m.istanza_utility_id                    AS istanza_utility_id,
  script.fn_pgtap_emittente_sr_operatore() AS emittente_sr_id,
  dbops.fn_pgtap_crea_articolo('PGT-RIC-NC-V1', false)                                              AS articolo_id,  -- rev 2026-10-13: costruito
  (SELECT u.id FROM catalogo.unita_misura u WHERE u.attivo IS TRUE ORDER BY u.id LIMIT 1)             AS uom_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1)                                            AS valuta_id,
  (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1)                        AS iva_id,
  (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno='COMMESSA'    AND s.attivo ORDER BY s.id LIMIT 1)        AS sorgente_root_id,
  (SELECT t.id FROM config.tipi_doc_fiscale t WHERE t.attivo IS TRUE ORDER BY t.id LIMIT 1)                           AS tipo_doc_fiscale_id,
  (SELECT s.id FROM config.stati_doc_fiscale s WHERE s.codice_interno='DRAFT' AND s.attivo IS TRUE ORDER BY s.id LIMIT 1) AS stato_fatt_draft_id,
  script.fn_pgtap_registro_fattura()                     AS registro_id
FROM tmp_mondo_ric m;

-- ============================================================
-- Helper (padre e figlio in due istruzioni: le CTE che scrivono condividono
-- la snapshot e le policy negano fail-closed)
-- ============================================================
CREATE OR REPLACE FUNCTION pg_temp.ric_fattura(p_segment varchar, p_qta numeric, p_prezzo numeric)
RETURNS bigint AS $$
DECLARE r RECORD; v_af bigint; v_fatt bigint; v_riga bigint;
BEGIN
  SELECT * INTO r FROM tmp_refs_ric;
  PERFORM vendite.fn_upsert_commessa_attivita(
    p_commessa_id => (SELECT commessa_id FROM tmp_com_ric),
    -- La riga NORMALE ha la sua sorgente (vincolo 20261012-27).
    p_sorgente_tipo_id => (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'COMMESSA'),
    p_sorgente_uid => ((SELECT commessa_id FROM tmp_com_ric))::text, p_segment_key => p_segment,
    p_articolo_id => r.articolo_id, p_istanza_utility_id => r.istanza_utility_id,
    p_data_attivita => DATE '2026-07-15', p_uom_id => r.uom_id, p_quantita => p_qta,
    p_competenza_mese => DATE '2026-07-01', p_competenza_dal => DATE '2026-07-01',
    p_competenza_al => DATE '2026-07-31', p_prezzo_snapshot => p_prezzo,
    p_prezzo_base_snapshot => NULL, p_origine_prezzo => NULL,
    p_tipo_variazione_applicata => NULL, p_valore_variazione_applicata => NULL,
    p_promo_id => NULL, p_contratto_id => NULL,
    p_categoria_cliente_id_snapshot => NULL, p_classe_utenza_id_snapshot => NULL,
    p_tipo_doc_fiscale_id => r.tipo_doc_fiscale_id, p_valuta_id => r.valuta_id,
    p_stato_approvazione => 'APPROVATA', p_stato_emissione => 'NON_EMESSA',
    p_tipo_movimento => 'NORMALE');

  PERFORM vendite.fn_emit_attivita_fatturabili_da_commessa((SELECT commessa_id FROM tmp_com_ric), true, false);

  SELECT af.id INTO v_af
    FROM vendite.attivita_fatturabili af
    JOIN vendite.commesse_attivita ca ON ca.id = af.commessa_attivita_id
   WHERE ca.segment_key = p_segment ORDER BY af.id DESC LIMIT 1;

  INSERT INTO vendite.fatture (registro_id, data, tipo_doc_fiscale_id, stato_doc_fiscale_id,
      emittente_soggetto_ruolo_id, billing_account_id, utility_id, valuta_id, tasso_cambio, meta)
  VALUES (r.registro_id, DATE '2026-07-31', r.tipo_doc_fiscale_id, r.stato_fatt_draft_id,
      r.emittente_sr_id, r.billing_account_id, r.utility_id, r.valuta_id, 1,
      jsonb_build_object('test_scope','pgtap_riconsegna_nc'))
  RETURNING id INTO v_fatt;

  INSERT INTO vendite.fatture_righe (fattura_id, riga_nr, articolo_id, descrizione,
      uom_id, qta, prezzo_unitario, iva_id, imponibile_riga, competenza_dal, competenza_al)
  VALUES (v_fatt, 1, r.articolo_id, 'Riga fattura pgTAP', r.uom_id, p_qta, p_prezzo,
      r.iva_id, p_qta * p_prezzo, script.fn_data_operativa(), script.fn_data_operativa())
  RETURNING id INTO v_riga;

  UPDATE vendite.attivita_fatturabili SET fattura_riga_id = v_riga WHERE id = v_af;
  RETURN v_riga;
END $$ LANGUAGE plpgsql;

-- ============================================================
-- FIXTURE: consegnati 10 a 20 euro, fatturati 10, resi 3 per ri-consegna
--          -> tenuti 7, fatturati 10 -> accredito dovuto 3 (FACOLTATIVA)
-- ============================================================
CREATE TEMP TABLE tmp_com_ric AS
SELECT vendite.fn_get_or_create_commessa(
  p_billing_account_id     => (SELECT billing_account_id FROM tmp_refs_ric),
  p_utility_id             => (SELECT utility_id FROM tmp_refs_ric),
  p_tipo_commessa          => 'AUTO',
  p_policy_fatturazione    => 'DA_DOCUMENTO',
  p_fatturazione_immediata => false,
  p_priorita_operativa     => 'NORMALE',
  p_competenza_dal         => DATE '2026-07-01',
  p_competenza_al          => DATE '2026-07-31',
  p_meta                   => '{}'::jsonb,
  p_force_new              => true) AS commessa_id;

SELECT vendite.fn_link_commessa_sorgente(
  p_commessa_id      => (SELECT commessa_id FROM tmp_com_ric),
  p_sorgente_tipo_id => (SELECT sorgente_root_id FROM tmp_refs_ric),
  p_sorgente_uid     => (SELECT commessa_id FROM tmp_com_ric)::text,
  p_sorgente_riga    => 1,
  p_meta             => '{}'::jsonb);

-- La partita: bolla consegnata dal builder, 10 a 20 euro, trigger CONSEGNATO.
CREATE TEMP TABLE tmp_ric_p AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('riconsegna A',
         p_billing_account_id => (SELECT billing_account_id FROM tmp_refs_ric),
         p_quantita => 10, p_prezzo => 20,
         p_articolo_id => (SELECT articolo_id FROM tmp_refs_ric),
         p_fatturazione_trigger => 'CONSEGNATO');

CREATE TEMP TABLE tmp_ric_fatt AS
SELECT pg_temp.ric_fattura(
    script.fn_segment_key('DDT_VENDITA', (SELECT ddt_uid FROM tmp_ric_p)::text, (SELECT ddt_riga_id FROM tmp_ric_p)),
    10, 20) AS fattura_riga_id;

-- Reso PER RI-CONSEGNA: e' il tipo che riapre il residuo, e l'unico che
-- ammette una spedizione di ritorno.
CREATE TEMP TABLE tmp_ric_reso AS
SELECT * FROM dbops.fn_pgtap_crea_reso('riconsegna A', (SELECT ddt_id FROM tmp_ric_p), 3,
         'RESO_PER_RICONSEGNA');

SELECT is(
  (SELECT q.accredito_dovuto FROM vendite.vw_resi_da_accreditare q
    WHERE q.resi_riga_id = (SELECT resi_riga_id FROM tmp_ric_reso)),
  3::numeric,
  '1) fixture: partita da 10 fatturata, reso 3 per ri-consegna -> accredito dovuto 3'
);

-- ============================================================
-- La RI-SPEDIZIONE (due volte, su due partite diverse): la bolla di
-- ri-consegna dal builder, 3 pezzi del reso al 1° agosto, CONSEGNATA.
-- ============================================================
-- ============================================================
-- CASO A — ri-spedizione SENZA nota di credito.
-- ⚠️ E' il caso D di test-fn-list-ddt-da-pushare-contatore-v1: la ri-consegna
--    non e' merce nuova e non deve proiettare nulla. Se diventa rosso, e' la
--    regola D-NC-4 a essere sbagliata, non il test.
-- ============================================================
CREATE TEMP TABLE tmp_ric_r2 AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_riconsegna((SELECT reso_id FROM tmp_ric_reso),
         p_resi_riga_id => (SELECT resi_riga_id FROM tmp_ric_reso), p_quantita => 3,
         p_data => DATE '2026-08-01');

SELECT is(
  (SELECT COALESCE(p.differenza::text, 'NULL') || '|' || p.stato || '|' || p.riconsegna_quota_nuova::text
     FROM vendite.vw_partite_merce p WHERE p.ddt_riga_id = (SELECT ddt_riga_id FROM tmp_ric_r2)),
  'NULL|RICONSEGNA|0',
  '2) senza nota di credito la regola e'' INERTE: la ri-consegna resta un conto vuoto'
);

SELECT is(
  (SELECT p.consegnato FROM vendite.vw_partite_merce p
    WHERE p.ddt_riga_id = (SELECT ddt_riga_id FROM tmp_ric_p)),
  13::numeric(18,6),
  '3) senza nota di credito la spedizione d''ORIGINE riassorbe i pezzi: 10 + 3 = 13'
);

-- ============================================================
-- CASO B — la NOTA DI CREDITO arriva PRIMA della ri-spedizione, che e'
-- l'ordine reale dei fatti: l'accredito si decide sulla merce tornata, la
-- ri-spedizione viene dopo. (E non e' un dettaglio del test: dopo la
-- ri-spedizione la partita d'origine pareggia da sola e l'accredito non e'
-- piu' dovuto — il conto lo dice, e ha ragione.)
-- ⭐ La nota di credito la crea la MADRE, non un INSERT a mano.
-- ============================================================
CREATE TEMP TABLE tmp_ric_pb AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('riconsegna B',
         p_billing_account_id => (SELECT billing_account_id FROM tmp_refs_ric),
         p_quantita => 10, p_prezzo => 20,
         p_articolo_id => (SELECT articolo_id FROM tmp_refs_ric),
         p_fatturazione_trigger => 'CONSEGNATO');

CREATE TEMP TABLE tmp_ric_fatt_b AS
SELECT pg_temp.ric_fattura(
    script.fn_segment_key('DDT_VENDITA', (SELECT ddt_uid FROM tmp_ric_pb)::text, (SELECT ddt_riga_id FROM tmp_ric_pb)),
    10, 20) AS fattura_riga_id;

CREATE TEMP TABLE tmp_ric_reso_b AS
SELECT * FROM dbops.fn_pgtap_crea_reso('riconsegna B', (SELECT ddt_id FROM tmp_ric_pb), 3,
         'RESO_PER_RICONSEGNA');

SELECT vendite.fn_accredita_riga_reso((SELECT resi_riga_id FROM tmp_ric_reso_b));
SELECT vendite.fn_emit_attivita_fatturabili_da_commessa((SELECT commessa_id FROM tmp_com_ric), true, false);

CREATE TEMP TABLE tmp_ric_r2b AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_riconsegna((SELECT reso_id FROM tmp_ric_reso_b),
         p_resi_riga_id => (SELECT resi_riga_id FROM tmp_ric_reso_b), p_quantita => 3,
         p_data => DATE '2026-08-01');

SELECT is(
  (SELECT p.riconsegna_quota_nuova FROM vendite.vw_partite_merce p
    WHERE p.ddt_riga_id = (SELECT ddt_riga_id FROM tmp_ric_r2b)),
  3::numeric,
  '4) D-NC-4: i pezzi accreditati CAMBIANO CASA — la spedizione nuova prende quota 3'
);

SELECT is(
  (SELECT p.differenza::text || '|' || p.stato FROM vendite.vw_partite_merce p
    WHERE p.ddt_riga_id = (SELECT ddt_riga_id FROM tmp_ric_r2b)),
  '3.000000|DA_FATTURARE',
  '5) la spedizione nuova diventa una partita vera: 3 da fatturare'
);

SELECT is(
  (SELECT p.consegnato FROM vendite.vw_partite_merce p
    WHERE p.ddt_riga_id = (SELECT ddt_riga_id FROM tmp_ric_pb)),
  10::numeric(18,6),
  '6) la spedizione d''origine non porta piu'' quei pezzi: torna a 10, non li rifattura'
);

SELECT is(
  (SELECT sum(p.consegnato) FROM vendite.vw_partite_merce p
    WHERE p.ddt_riga_id IN ((SELECT ddt_riga_id FROM tmp_ric_pb), (SELECT ddt_riga_id FROM tmp_ric_r2b))),
  13::numeric,
  '7) INVARIANTE: la somma dei consegnato non cambia — i pezzi si spostano, non si moltiplicano'
);

-- ⭐ E' il punto per cui la regola esiste: il segmento della spedizione
--    d'origine e' gia' EMESSA e la cintura del push lo blocca (giustamente);
--    quello della spedizione nuova e' vergine, quindi LIBERA, e il giro di
--    fatturazione NORMALE se ne accorge da solo — nessun verbo nuovo.
SELECT is(
  script.fn_get_stato_push_segment(
    script.fn_segment_key('DDT_VENDITA', (SELECT ddt_uid FROM tmp_ric_r2b)::text, (SELECT ddt_riga_id FROM tmp_ric_r2b))),
  'LIBERA',
  '8) il segmento della spedizione nuova e'' LIBERA: la fatturazione normale la vede'
);

SELECT * FROM finish();
ROLLBACK;
