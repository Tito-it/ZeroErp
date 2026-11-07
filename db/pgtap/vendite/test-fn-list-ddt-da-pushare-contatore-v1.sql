-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- rev 2026-10-26 (brief-modello-documento-vendita §14, giro 10): il passaggio a PRONTA_FATTURAZIONE dal verbo chiede l'azione cambia_stato_commessa: il file prova il contatore, non il permesso, e la concede all'utente del contesto.
-- rev 2026-10-25 (brief-db-pgtap-reso-costruito): i resi dal builder dbops.fn_pgtap_crea_reso (pg_temp.mk_reso ritirata), la bolla di ri-consegna di D da dbops.fn_pgtap_crea_ddt_riconsegna (via indirizzo e causale a mano); nulla della strada del reso resta scritto a mano.
-- rev 2026-10-25 (brief-db-pgtap-bolla-e-reso-costruiti, giro 1): la bolla da ordine dal builder dbops.fn_pgtap_crea_ddt_da_ordine (le due spedizioni di F con p_qta_da_evadere e p_ordine_id; ritirate pg_temp.mk_partita_ordine, mk_ddt_consegnato, mk_partita); il reso (pg_temp.mk_reso) resta scritto a mano (giro 2), la bolla di ri-consegna di D resta del verbo fn_genera_ddt_riconsegna (con causale e indirizzo) e va a CONSEGNATO per la matrice.
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13, 2e/L2c-1): le chiavi del push col codice della sorgente, composte da script.fn_segment_key dove la forma lo permette (le forme su piu' righe col prefisso lungo); corsia e codice del registro coi codici lunghi.
-- pgTAP test per Zero ERP
-- Test: fn_list_ddt_da_pushare proietta la DIFFERENZA del conto della merce,
--       non piu' dr.quantita grezza — step 3, brief-db-fatturazione-ddt-resi
--       §3a/§9-3. Chiude la doppia fatturazione.
-- (changeset 20260717-12; dal 20260921-23 la differenza viene da
--  fn_partite_merce col DDT come seme, attraverso fn_ddt_push_diagnosi —
--  vw_contatore_merce, che la dava fino ad allora, e' ritirata dal 20260922-08)
-- ------------------------------------------------------------
-- Indice test (1..5):
--   1) A: order 10, consegnato, nessun reso -> lister proietta 10 (nessuna riduzione)
--   2) B: order 10, reso 3 -> lister proietta 7 (IL RESO RIDUCE IL PUSH — il fix)
--   3) B: qta_operativa scalata a 7 (coerente con la base, factor 1)
--   4) C: reso 3 + fatturato 7 -> riga DDT EMESSA -> esclusa (frontiera, 0 righe)
--   5) D (caso 8 §3a): ri-consegna di merce GIA' fatturata -> il DDT nuovo
--      proietta 0 -> NON pushato -> niente doppia fattura (chiude bug 1a)
--   6-7) F (§3d): partita 10 spezzata in DUE DDT parziali (6+4) con reso 5.
--      6) INVARIANTE: il totale spinto resta 5 — e' quello che finisce in fattura.
--      7) ⭐ riscritto 2026-08-17: ogni spedizione porta il SUO residuo (1 e 4),
--         non piu' 5 e 0. Il greedy d'ordine non sapeva da quale spedizione la
--         merce fosse tornata e la scaricava sulla piu' vecchia.
-- Nota: standalone (dr.quantita grezza invariata) coperto da
--       test-fn-list-ddt-da-pushare-v1 casi 7-8.
-- ------------------------------------------------------------

BEGIN;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file sarebbe verde per sottrazione. IMMEDIATE li riporta a scattare a fine
--   di ogni istruzione. In testa e non in coda: in coda scatterebbero dopo il
--   cleanup, su righe ormai cancellate.
--   Brief: brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(7);

SET LOCAL app.ruolo_applicativo = 'OPERATORE';
-- ⛔ rev 2026-10-13: niente app.current_user_id = '1' (in CI l'utente 1 non
--   esiste): l'operatore e' quello del contesto aperto qui sopra.

-- ============================================================
-- Riferimenti + helper
-- ============================================================
-- ⛔ rev 2026-10-13: il mondo si COSTRUISCE (su un DB ricostruito anagrafiche e
--   articoli sono vuoti): cliente fatturabile legato all'azienda di chi agisce,
--   articolo merce non gestito a magazzino (il test non misura il magazzino).
--   Dal DB si legge solo il seed.
CREATE TEMP TABLE tmp_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('pgTAP lister DDT contatore');
CREATE TEMP TABLE tmp_art AS
SELECT dbops.fn_pgtap_crea_articolo('PGT-LDC-V1', false) AS id;

CREATE TEMP TABLE tmp_refs AS
SELECT
  (SELECT m.billing_account_id FROM tmp_mondo m)                         AS billing_account_id,
  (SELECT m.utility_id FROM tmp_mondo m)                                 AS utility_id,
  (SELECT m.istanza_utility_id FROM tmp_mondo m)                         AS istanza_utility_id,
  (SELECT t.id FROM tmp_art t)                                           AS articolo_id,
  (SELECT u.id FROM catalogo.unita_misura u WHERE u.attivo IS TRUE ORDER BY u.id LIMIT 1) AS uom_id,
  (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'COMMESSA' AND s.attivo LIMIT 1)      AS sorgente_root_id,
  (SELECT t.id FROM config.tipi_doc_fiscale t WHERE t.attivo IS TRUE ORDER BY t.id LIMIT 1) AS tipo_doc_fiscale_id;

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
  -- ROOT: sorgente COMMESSA (key_selector='id') con uid = id della commessa
  -- stessa: esiste per costruzione, quindi passa il guard sorgente polimorfa
  -- (formato id::text + esistenza nel target). fn_emit pretende solo che una
  -- ROOT esista, non ne dereferenzia il tipo. rev 2026-07-27 (bonifica).
  p_sorgente_uid => (SELECT commessa_id FROM tmp_com)::text,
  p_sorgente_riga => NULL, p_meta => '{}'::jsonb);

CREATE OR REPLACE FUNCTION pg_temp.mk_af(p_segment varchar, p_qta numeric)
RETURNS void AS $$
DECLARE r RECORD;
BEGIN
  SELECT * INTO r FROM tmp_refs;
  PERFORM vendite.fn_upsert_commessa_attivita(
    p_commessa_id => (SELECT commessa_id FROM tmp_com),
    -- La riga NORMALE ha la sua sorgente (vincolo 20261012-27).
    -- La provenienza e' il documento che la chiave nomina (come nel push).
    p_sorgente_tipo_id => (SELECT k.sorgente_tipo_id FROM dbops.fn_pgtap_provenienza_da_chiave(p_segment) k),
    p_sorgente_uid => (SELECT k.sorgente_chiave FROM dbops.fn_pgtap_provenienza_da_chiave(p_segment) k),
    p_sorgente_riga => (SELECT k.sorgente_riga FROM dbops.fn_pgtap_provenienza_da_chiave(p_segment) k),
    p_segment_key => p_segment,
    p_articolo_id => r.articolo_id, p_istanza_utility_id => r.istanza_utility_id,
    p_data_attivita => DATE '2026-07-15', p_uom_id => r.uom_id, p_quantita => p_qta,
    p_competenza_mese => DATE '2026-07-01', p_competenza_dal => DATE '2026-07-01', p_competenza_al => DATE '2026-07-31',
    p_prezzo_snapshot => 10.0, p_prezzo_base_snapshot => NULL, p_origine_prezzo => NULL,
    p_tipo_variazione_applicata => NULL, p_valore_variazione_applicata => NULL,
    p_promo_id => NULL, p_contratto_id => NULL, p_categoria_cliente_id_snapshot => NULL, p_classe_utenza_id_snapshot => NULL,
    p_tipo_doc_fiscale_id => r.tipo_doc_fiscale_id, p_stato_approvazione => 'APPROVATA', p_stato_emissione => 'NON_EMESSA',
    p_tipo_movimento => 'NORMALE', p_meta => '{}'::jsonb);
END $$ LANGUAGE plpgsql;

-- ============================================================
-- FIXTURE: A (no reso), B (reso 3), C (reso 3 + fatt 7), D (caso 8), E (standalone)
-- ============================================================
-- La partita: ordine 10 @25 trigger CONSEGNATO (supera la cintura XOR), bolla
-- CONSEGNATA dal builder (stato = trigger: il lister la lista E il reso-guard passa).
CREATE TEMP TABLE tmp_a AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('lister A', 'CONSEGNATO',
    (SELECT billing_account_id FROM tmp_refs), p_quantita => 10, p_prezzo => 25,
    p_articolo_id => (SELECT articolo_id FROM tmp_refs), p_fatturazione_trigger => 'CONSEGNATO');

CREATE TEMP TABLE tmp_b AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('lister B', 'CONSEGNATO',
    (SELECT billing_account_id FROM tmp_refs), p_quantita => 10, p_prezzo => 25,
    p_articolo_id => (SELECT articolo_id FROM tmp_refs), p_fatturazione_trigger => 'CONSEGNATO');
CREATE TEMP TABLE tmp_b_reso AS
SELECT * FROM dbops.fn_pgtap_crea_reso('lister B', (SELECT ddt_id FROM tmp_b), 3);

CREATE TEMP TABLE tmp_c AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('lister C', 'CONSEGNATO',
    (SELECT billing_account_id FROM tmp_refs), p_quantita => 10, p_prezzo => 25,
    p_articolo_id => (SELECT articolo_id FROM tmp_refs), p_fatturazione_trigger => 'CONSEGNATO');
CREATE TEMP TABLE tmp_c_reso AS
SELECT * FROM dbops.fn_pgtap_crea_reso('lister C', (SELECT ddt_id FROM tmp_c), 3);

-- D (caso 8): consegnato + fatturato 10, reso 3 PER RICONSEGNA, ri-spedito.
CREATE TEMP TABLE tmp_d AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('lister D', 'CONSEGNATO',
    (SELECT billing_account_id FROM tmp_refs), p_quantita => 10, p_prezzo => 25,
    p_articolo_id => (SELECT articolo_id FROM tmp_refs), p_fatturazione_trigger => 'CONSEGNATO');
CREATE TEMP TABLE tmp_d_reso AS
SELECT * FROM dbops.fn_pgtap_crea_reso('lister D', (SELECT ddt_id FROM tmp_d), 3, 'RESO_PER_RICONSEGNA');
-- ri-spedizione dei 3 (tutto il reso) -> nuovo DDT, CONSEGNATO per essere
-- eleggibile al lister; la causale VENDITA (la sola fatturabile) la copia la
-- madre dalla bolla d'origine.
CREATE TEMP TABLE tmp_d_ric AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_riconsegna((SELECT reso_id FROM tmp_d_reso));

-- F (§3d, distribuzione greedy): UNA partita da 10 spezzata in DUE DDT parziali
-- (6 + 4), entrambi CONSEGNATO ed eleggibili, con reso 5 -> differenza 5.
-- E' l'unico caso che esercita la window del greedy con un precedente NON vuoto:
-- il 1o DDT assorbe 5 (cappato dalla differenza), al 2o non resta nulla -> 0.
-- Senza il termine ROWS ... 1 PRECEDING il 2o proietterebbe 4 = merce gia'
-- coperta dal 1o -> doppia fatturazione.
-- Le due spedizioni dal builder: la prima costruisce l'ordine, la seconda
-- evade il resto della stessa riga (p_ordine_id).
CREATE TEMP TABLE tmp_f1 AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('lister F', 'CONSEGNATO',
    (SELECT billing_account_id FROM tmp_refs), p_quantita => 10, p_prezzo => 25,
    p_articolo_id => (SELECT articolo_id FROM tmp_refs), p_fatturazione_trigger => 'CONSEGNATO',
    p_qta_da_evadere => 6);
CREATE TEMP TABLE tmp_f2 AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('lister F', 'CONSEGNATO',
    p_ordine_id => (SELECT ordine_id FROM tmp_f1), p_qta_da_evadere => 4);
CREATE TEMP TABLE tmp_f AS
SELECT f1.ordine_id, f1.ordine_riga_id, f1.ddt_id AS ddt1_id, f2.ddt_id AS ddt2_id
  FROM tmp_f1 f1, tmp_f2 f2;

-- reso 5 sul PRIMO DDT (riga da 6) -> tenuti 5 sulla partita
CREATE TEMP TABLE tmp_f_reso AS
SELECT * FROM dbops.fn_pgtap_crea_reso('lister F', (SELECT ddt_id FROM tmp_f1), 5);

-- Nota: lo standalone (ramo ELSE = dr.quantita grezza, invariato) e' gia' coperto
-- da test-fn-list-ddt-da-pushare-v1 (casi 7-8, "DDT autonomo"): non ripetuto qui.

-- Fatturazione: CA per C (DDT_C, 7) e D (DDT_orig_D, 10) -> emit.
SELECT pg_temp.mk_af(script.fn_segment_key('DDT_VENDITA', (SELECT ddt_uid FROM tmp_c)::text, (SELECT ddt_riga_id FROM tmp_c)), 7);
SELECT pg_temp.mk_af(script.fn_segment_key('DDT_VENDITA', (SELECT ddt_uid FROM tmp_d)::text, (SELECT ddt_riga_id FROM tmp_d)), 10);
-- rev 2026-10-26 (giro 10): «rendi pronta» chiede l'azione cambia_stato_commessa
-- (brief-modello-documento-vendita §14, C-1); questo file prova il contatore dei DDT da pushare, non il
-- permesso: la si concede all'utente del contesto.
SELECT dbops.fn_pgtap_concedi_azione(current_setting('app.current_user_id')::integer, 'cambia_stato_commessa');
SELECT vendite.fn_cambia_stato_commessa((SELECT commessa_id FROM tmp_com), 'PRONTA_FATTURAZIONE');
SELECT vendite.fn_emit_attivita_fatturabili_da_commessa((SELECT commessa_id FROM tmp_com));

-- ============================================================
-- ASSERZIONI
-- ============================================================
-- ⚠️ Si filtra sulla RIGA, non si prende la prima che capita: la funzione
--   ritorna una riga per riga-DDT (la RETURNS TABLE ha riga_id), e `quantita`
--   e `qta_operativa` sono valori DI RIGA. Oggi il builder ne crea una sola e
--   il LIMIT 1 tornava per forza quella, ma il giorno in cui una partita avesse
--   due righe l'asserzione cambierebbe soggetto senza dirlo.
-- 1) A: nessun reso -> proietta 10
SELECT is(
  (SELECT quantita FROM vendite.fn_list_ddt_da_pushare(NULL,NULL,NULL,(SELECT ddt_id FROM tmp_a))
    WHERE riga_id = (SELECT ddt_riga_id FROM tmp_a)),
  10::numeric, '1) A senza reso: lister proietta la quantita piena (10)');

-- 2) B: reso 3 -> proietta 7 (IL FIX)
SELECT is(
  (SELECT quantita FROM vendite.fn_list_ddt_da_pushare(NULL,NULL,NULL,(SELECT ddt_id FROM tmp_b))
    WHERE riga_id = (SELECT ddt_riga_id FROM tmp_b)),
  7::numeric, '2) B reso 3: lister proietta la DIFFERENZA (7), non dr.quantita (il fix)');

-- 3) B: qta_operativa scalata a 7
SELECT is(
  (SELECT qta_operativa FROM vendite.fn_list_ddt_da_pushare(NULL,NULL,NULL,(SELECT ddt_id FROM tmp_b))
    WHERE riga_id = (SELECT ddt_riga_id FROM tmp_b)),
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
-- ⭐ RISCRITTI il 2026-08-17 (partita generalizzata, slice S5). NON perche' il
-- comportamento fosse sbagliato, ma perche' e' diventato PIU' PRECISO.
--
--   Fixture: riga d'ordine da 10 spezzata in DDT1=6 e DDT2=4, reso 5 SUL PRIMO.
--
--   PRIMA la differenza era della riga d'ORDINE (5 = 10 consegnati − 5 resi) e
--   veniva ridistribuita greedy: il 1o DDT la assorbiva tutta (5, cappato a 6) e
--   al 2o non restava nulla. Il totale era giusto, la ripartizione arbitraria —
--   il greedy non sapeva DA QUALE spedizione la merce fosse tornata, e la
--   scaricava sulla piu' vecchia.
--
--   ORA ogni spedizione ha il suo conto:
--       DDT1: 6 usciti − 5 tornati  ->  1 ancora fuori  ->  push 1
--       DDT2: 4 usciti − 0 tornati  ->  4 ancora fuori  ->  push 4
--
--   ⚠️ **Il totale non cambia: 5 in entrambi i casi.** Ed e' la cosa che va
--   presidiata per prima, perche' e' quella che finisce in fattura — la
--   ripartizione decide solo su quale documento compare la riga. Per questo il
--   test 6 asserisce l'INVARIANTE (il totale) e il 7 la ripartizione nuova:
--   se un domani cambiasse il totale, il 6 lo direbbe subito.
CREATE TEMP TABLE tmp_batch AS
SELECT ddt_id, riga_id, quantita FROM vendite.fn_list_ddt_da_pushare(NULL,NULL,NULL,NULL);

SELECT is(
  (SELECT COALESCE(SUM(quantita), 0) FROM tmp_batch
    WHERE ddt_id IN ((SELECT ddt1_id FROM tmp_f), (SELECT ddt2_id FROM tmp_f))),
  5::numeric, '6) F batch: INVARIANTE — il totale spinto per la riga d''ordine resta 5');

SELECT results_eq(
  $q$SELECT COALESCE((SELECT quantita FROM tmp_batch WHERE ddt_id=(SELECT ddt1_id FROM tmp_f)), 0),
            COALESCE((SELECT quantita FROM tmp_batch WHERE ddt_id=(SELECT ddt2_id FROM tmp_f)), 0)$q$,
  $q$VALUES (1::numeric, 4::numeric)$q$,
  '7) F batch: ogni spedizione porta il SUO residuo (1 e 4), non piu'' 5 e 0');

SELECT * FROM finish();
ROLLBACK;
