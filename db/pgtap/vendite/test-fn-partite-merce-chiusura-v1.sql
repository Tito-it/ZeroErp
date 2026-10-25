-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- rev 2026-10-25 (brief-db-pgtap-reso-costruito, giro D-4): l'ordine B da dbops.fn_pgtap_crea_ordine_con_righe, la commessa da dbops.fn_pgtap_crea_commessa (sorgente ROOT), le attivita' da dbops.fn_pgtap_crea_commessa_attivita con la sorgente vera (ORDINE_VENDITA / DDT_VENDITA, E-3), la fattura del caso 2 da dbops.fn_pgtap_fattura_attivita; helper ch_mk_ordine e ch_fattura ritirati. Resta a mano l'ONERE del caso 5 (il caso; il builder dell'attivita' scrive solo NORMALE).
-- rev 2026-10-25 (brief-db-pgtap-reso-costruito): il reso dal builder dbops.fn_pgtap_crea_reso, le due ri-spedizioni da dbops.fn_pgtap_crea_ddt_riconsegna (parziali dalla stessa riga del reso, alle loro date); helper ch_mk_reso e ch_rispedisci ritirati, l'azione conferma_reso la concede il builder.
-- rev 2026-10-25 (brief-db-pgtap-bolla-e-reso-costruiti, D-1): gli ordini costruiti dal builder nascono al 2026-08-05 (p_data_ordine), come gli ordini scritti a mano prima del giro 1: nessuna bolla piu' vecchia del suo ordine.
-- rev 2026-10-25 (brief-db-pgtap-bolla-e-reso-costruiti, giro 1): le bolle da ordine dal builder dbops.fn_pgtap_crea_ddt_da_ordine (date della greedy con p_data, tre spedizioni dalla stessa riga con p_qta_da_evadere e p_ordine_id, la bozza DRAFT); restano scritti a mano l'ordine B senza bolla, il legame della riga MULTIPLA e la riga a mano (in bozza, il caso del 11/13), la bolla di ri-consegna (indirizzo e causale; gli stati per dbops.fn_pgtap_porta_a_stato) e il reso (giro 2).
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13, 2e/L2c-1): le chiavi del push col codice della sorgente, composte da script.fn_segment_key dove la forma lo permette (le forme su piu' righe col prefisso lungo); corsia e codice del registro coi codici lunghi.
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
  c.istanza_utility_id,
  dbops.fn_pgtap_crea_articolo('PGT-CH-ART', false)                                                  AS articolo_id,
  (SELECT u.id FROM catalogo.unita_misura u WHERE u.attivo IS TRUE ORDER BY u.id LIMIT 1)             AS uom_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1)                                            AS valuta_id,
  (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1)                        AS iva_id,
  (SELECT t.id FROM config.tipi_doc_fiscale t WHERE t.attivo IS TRUE ORDER BY t.id LIMIT 1)           AS tipo_doc_fiscale_id
FROM tmp_cli_ch c;

-- Commessa + ROOT, dal builder: serve alle attivita' fatturabili (corsia ORD e DDT).
CREATE TEMP TABLE tmp_com_ch AS
SELECT commessa_id
  FROM dbops.fn_pgtap_crea_commessa('pgtap_chiusura', NULL, (SELECT billing_account_id FROM tmp_refs_ch),
                                    p_con_sorgente_root => true);

-- ============================================================
-- Helper (padre e figlio in due istruzioni: le CTE che scrivono condividono
-- la snapshot e le policy negano fail-closed)
-- ============================================================

-- Una bolla dal builder, col cliente e l'articolo del file, riga a 20 e
-- trigger CONSEGNATO. La data e' la chiave della greedy `alloc`
-- (oldest-first): va scelta (p_data).
-- ⚠️ La riga a mano (caso 3) e il legame della riga MULTIPLA (caso 8) nascono
--   solo con la bolla in bozza (trgfn_doc_righe_lock_fuori_bozza; D-6 del
--   2026-10-11): quelle bolle si chiedono DRAFT e si portano a CONSEGNATO
--   con dbops.fn_pgtap_porta_a_stato.

-- Le attivita' NORMALI (corsia ORD o DDT) vengono dal builder, con la sorgente
-- vera (E-3): la chiave la compone script.fn_segment_key. Questo helper scrive
-- solo l'ONERE del caso 5 (il caso): la causale e' obbligatoria se e solo se
-- tipo_movimento = 'ONERE' (chk_commesse_attivita_causale_onere), l'onere non
-- ha sorgente (vincolo 20261012-27).
CREATE OR REPLACE FUNCTION pg_temp.ch_mk_onere(p_segment varchar, p_qta numeric)
RETURNS void AS $$
DECLARE r RECORD; v_causale_id bigint;
BEGIN
  SELECT * INTO r FROM tmp_refs_ch;
  SELECT c.id INTO v_causale_id FROM config.causali_onere c WHERE c.attivo ORDER BY c.id LIMIT 1;
  PERFORM vendite.fn_upsert_commessa_attivita(
    p_commessa_id => (SELECT commessa_id FROM tmp_com_ch),
    p_sorgente_tipo_id => NULL, p_sorgente_uid => NULL,
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
    p_tipo_movimento => 'ONERE', p_causale_onere_id => v_causale_id);
  PERFORM vendite.fn_emit_attivita_fatturabili_da_commessa((SELECT commessa_id FROM tmp_com_ch), true, false);
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
-- Il primo DDT resta in bozza: prende il legame con l'ordine B (caso 8).
CREATE TEMP TABLE tmp_d1 AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('chiusura 1', 'DRAFT', p_billing_account_id => (SELECT billing_account_id FROM tmp_refs_ch),
         p_articolo_id => (SELECT articolo_id FROM tmp_refs_ch), p_prezzo => 20,
         p_fatturazione_trigger => 'CONSEGNATO',
         p_quantita => 30, p_qta_da_evadere => 10, p_data => DATE '2026-08-10',
         p_data_ordine => DATE '2026-08-05');
CREATE TEMP TABLE tmp_o1 AS SELECT ordine_id, ordine_uid, ordine_riga_id FROM tmp_d1;
-- L'ordine B, confermato e SENZA bolla: una bolla la riceve solo per legame (caso 8).
CREATE TEMP TABLE tmp_ob AS
SELECT ordine_id, ordine_uid, ordine_riga_id
  FROM dbops.fn_pgtap_crea_ordine_con_righe('chiusura 1 B', 'CONFERMATO',
         (SELECT billing_account_id FROM tmp_refs_ch), p_quantita => 10, p_prezzo => 20,
         p_articolo_id => (SELECT articolo_id FROM tmp_refs_ch), p_fatturazione_trigger => 'CONSEGNATO',
         p_data_ordine => DATE '2026-08-05');
INSERT INTO vendite.ordini_righe_fulfillment (ordine_riga_id, ddt_riga_id, qta_evasa, storicizza)
SELECT (SELECT ordine_riga_id FROM tmp_ob), d.ddt_riga_id, d.quantita, false
  FROM tmp_d1 d;
SELECT dbops.fn_pgtap_porta_a_stato('vendite.ddt', (SELECT ddt_id FROM tmp_d1), 'CONSEGNATO');
CREATE TEMP TABLE tmp_d2 AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('chiusura 1', p_ordine_id => (SELECT ordine_id FROM tmp_o1),
         p_qta_da_evadere => 10, p_data => DATE '2026-08-11');
CREATE TEMP TABLE tmp_d3 AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('chiusura 1', p_ordine_id => (SELECT ordine_id FROM tmp_o1),
         p_qta_da_evadere => 10, p_data => DATE '2026-08-12');
-- Il fatturato d'ordine 15: un'attivita' sulla riga d'ordine, emessa.
CREATE TEMP TABLE tmp_att1 AS
SELECT * FROM dbops.fn_pgtap_crea_commessa_attivita((SELECT commessa_id FROM tmp_com_ch), 20,
         (SELECT articolo_id FROM tmp_refs_ch),
         p_sorgente_codice => 'ORDINE_VENDITA', p_sorgente_uid => (SELECT ordine_uid FROM tmp_o1)::text,
         p_sorgente_riga_id => (SELECT ordine_riga_id FROM tmp_o1), p_quantita => 15,
         p_competenza_dal => DATE '2026-08-01', p_competenza_al => DATE '2026-08-31');
SELECT vendite.fn_emit_attivita_fatturabili_da_commessa((SELECT commessa_id FROM tmp_com_ch), true, false);

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
CREATE TEMP TABLE tmp_p AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('chiusura 2', p_stato_codice_interno => 'CONSEGNATO', p_billing_account_id => (SELECT billing_account_id FROM tmp_refs_ch),
         p_articolo_id => (SELECT articolo_id FROM tmp_refs_ch), p_prezzo => 20,
         p_fatturazione_trigger => 'CONSEGNATO',
         p_quantita => 10, p_data => DATE '2026-08-13',
         p_data_ordine => DATE '2026-08-05');
-- Fatturata 6 sulla corsia DDT (l'accredito copia il prezzo dalla riga di fattura).
CREATE TEMP TABLE tmp_att2 AS
SELECT * FROM dbops.fn_pgtap_crea_commessa_attivita((SELECT commessa_id FROM tmp_com_ch), 20,
         (SELECT articolo_id FROM tmp_refs_ch),
         p_sorgente_codice => 'DDT_VENDITA', p_sorgente_uid => (SELECT ddt_uid FROM tmp_p)::text,
         p_sorgente_riga_id => (SELECT ddt_riga_id FROM tmp_p), p_quantita => 6,
         p_competenza_dal => DATE '2026-08-01', p_competenza_al => DATE '2026-08-31');
CREATE TEMP TABLE tmp_fatt2 AS
SELECT * FROM dbops.fn_pgtap_fattura_attivita('pgtap_chiusura', ARRAY[(SELECT attivita_id FROM tmp_att2)]);
-- Il reso per ri-consegna, confermato: dal builder, sulla riga della partita.
CREATE TEMP TABLE tmp_reso AS
SELECT * FROM dbops.fn_pgtap_crea_reso('chiusura 2', (SELECT ddt_id FROM tmp_p), 5, 'RESO_PER_RICONSEGNA',
         p_ddt_riga_id => (SELECT ddt_riga_id FROM tmp_p));
SELECT vendite.fn_accredita_riga_reso((SELECT resi_riga_id FROM tmp_reso));
SELECT vendite.fn_emit_attivita_fatturabili_da_commessa((SELECT commessa_id FROM tmp_com_ch), true, false);
-- Le due ri-spedizioni, consegnate: la data ordina le sorelle nella finestra di `migra`.
CREATE TEMP TABLE tmp_r1 AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_riconsegna((SELECT reso_id FROM tmp_reso),
         p_resi_riga_id => (SELECT resi_riga_id FROM tmp_reso), p_quantita => 3, p_data => DATE '2026-09-01');
CREATE TEMP TABLE tmp_r2 AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_riconsegna((SELECT reso_id FROM tmp_reso),
         p_resi_riga_id => (SELECT resi_riga_id FROM tmp_reso), p_quantita => 2, p_data => DATE '2026-09-02');

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
--          con la bolla in bozza): fino al 21-09 la riga si aggiungeva
--          al DDT di mezzo gia' consegnato, che il BB delle righe non
--          ammette piu' — e aggiungerla prima avrebbe cambiato i conti dei
--          test 4-10.
-- ============================================================
CREATE TEMP TABLE tmp_d3m AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('chiusura 3', 'DRAFT', p_billing_account_id => (SELECT billing_account_id FROM tmp_refs_ch),
         p_articolo_id => (SELECT articolo_id FROM tmp_refs_ch), p_prezzo => 20,
         p_fatturazione_trigger => 'CONSEGNATO',
         p_quantita => 10, p_data => DATE '2026-08-14',
         p_data_ordine => DATE '2026-08-05');
INSERT INTO vendite.ddt_righe (ddt_id, riga_nr, articolo_id, descrizione,
    qta_operativa, quantita, prezzo_unitario, iva_id, attivo, storicizza, meta)
SELECT d.ddt_id, 900, r.articolo_id, 'Riga aggiunta a mano', 4, 4, 20, r.iva_id,
       true, false, jsonb_build_object('test_scope','pgtap_chiusura')
  FROM tmp_d3m d, tmp_refs_ch r;
SELECT dbops.fn_pgtap_porta_a_stato('vendite.ddt', (SELECT ddt_id FROM tmp_d3m), 'CONSEGNATO');

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
CREATE TEMP TABLE tmp_bozza AS
SELECT ddt_id FROM dbops.fn_pgtap_crea_ddt_da_ordine('chiusura 4', 'DRAFT', p_billing_account_id => (SELECT billing_account_id FROM tmp_refs_ch),
         p_articolo_id => (SELECT articolo_id FROM tmp_refs_ch), p_prezzo => 20,
         p_fatturazione_trigger => 'CONSEGNATO',
         p_quantita => 5, p_data => DATE '2026-08-20',
         p_data_ordine => DATE '2026-08-05');

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
-- (il legame con B nasce con il primo DDT in bozza, caso 1: D-6 del 2026-10-11)

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
CREATE TEMP TABLE tmp_d5 AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('chiusura 5', p_stato_codice_interno => 'CONSEGNATO', p_billing_account_id => (SELECT billing_account_id FROM tmp_refs_ch),
         p_articolo_id => (SELECT articolo_id FROM tmp_refs_ch), p_prezzo => 20,
         p_fatturazione_trigger => 'CONSEGNATO',
         p_quantita => 10, p_data => DATE '2026-08-16',
         p_data_ordine => DATE '2026-08-05');
CREATE TEMP TABLE tmp_o5 AS SELECT ordine_id, ordine_uid, ordine_riga_id FROM tmp_d5;
CREATE TEMP TABLE tmp_att5 AS
SELECT * FROM dbops.fn_pgtap_crea_commessa_attivita((SELECT commessa_id FROM tmp_com_ch), 20,
         (SELECT articolo_id FROM tmp_refs_ch),
         p_sorgente_codice => 'DDT_VENDITA', p_sorgente_uid => (SELECT ddt_uid FROM tmp_d5)::text,
         p_sorgente_riga_id => (SELECT ddt_riga_id FROM tmp_d5), p_quantita => 10,
         p_competenza_dal => DATE '2026-08-01', p_competenza_al => DATE '2026-08-31');
SELECT vendite.fn_emit_attivita_fatturabili_da_commessa((SELECT commessa_id FROM tmp_com_ch), true, false);
SELECT pg_temp.ch_mk_onere(script.fn_segment_key('ORDINE_VENDITA', (SELECT ordine_uid FROM tmp_o5)::text, (SELECT ordine_riga_id FROM tmp_o5)), 5);

SELECT results_eq(
  $q$SELECT p.fatturato_merce, p.fatturato_da_ordine, p.fatturato, p.differenza,
            (SELECT count(*)::int FROM vendite.fn_af_merce_per_riga(ARRAY[script.fn_segment_key('ORDINE_VENDITA', o.ordine_uid::text, o.ordine_riga_id)]) f
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
  '14) scope che non vede il DDT: la partita sparisce, non esce con dei conti a zero (rosso da owner, che salta la RLS; verde come app)');

SELECT * FROM finish();
ROLLBACK;
