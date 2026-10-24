-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- rev 2026-10-25 (brief-db-pgtap-reso-costruito): il reso per ri-consegna dal builder dbops.fn_pgtap_crea_reso (che concede da se' conferma_reso); resta scritta a mano la commessa con l'attivita' fatturata, che e' il caso del test.
-- rev 2026-10-25 (brief-db-pgtap-bolla-e-reso-costruiti, giro 1): la bolla da ordine dal builder dbops.fn_pgtap_crea_ddt_da_ordine; resta scritto a mano il reso per ri-consegna (giro 2) e la commessa con l'attivita' fatturata, che sono il caso del test.
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13.5-ter, 2e): le chiavi del push col codice della sorgente (PREVENTIVO:, DDT_VENDITA:, ORDINE_VENDITA:, CONTRATTO:, ATTIVITA_CONSUMI:), stessa forma di script.fn_segment_key carattere per carattere.
-- rev 2026-10-24 (brief-modello-documento-vendita Q-2/Q-4): la bolla consegnata non si pesca piu' dal database: ordine dal builder, riga di un articolo costruito, bolla generata dall'ordine e portata a CONSEGNATO per la matrice; il tipo reso si legge per codice.
-- pgTAP test per Zero ERP
-- Test: SCENARIO end-to-end della chiusura ri-consegna (Fase 2)
--   fn_chiudi_riconsegna_reso + fn_riapri_riconsegna_reso e i loro effetti
--   su residuo ordine, elenco ri-spedizione e coda accrediti.
-- Brief: brief-db-chiusura-riconsegna-reso-definitivo §6 (voce 10 del §8).
--
-- Complementare a test-resi-rinunce-fondamenta-v1.sql, che copre tabella,
-- helper e i due guard. Qui si esercitano le MADRI e le CONSEGUENZE.
--
-- ⚠️ IL TEST CHE VALE PIU' DEGLI ALTRI e' il 6: l'accredito deve restare
-- IN CODA con l'IMPORTO IDENTICO, e cambiare solo etichetta
-- (FACOLTATIVA -> DOVUTA). E' la promessa del brief §3 ("chiudere la
-- ri-consegna non cambia nessun numero") ed e' il discriminante della
-- decisione §4.2: se la sottrazione delle rinunce finisse in
-- vw_resi_righe_effettive invece che in fn_ordine_riga_qta_riconsegna, la riga
-- USCIREBBE dalla coda e l'accredito dovuto al cliente sparirebbe in silenzio.
-- Il probe manuale del 2026-07-26 non aveva potuto verificarlo (fixture senza
-- merce "fatturata"): questo test chiude quel buco.
--
-- FIXTURE — perche' e' articolato: per far entrare la riga in coda accrediti
-- serve differenza < 0 nella partita di merce (fn_partite_merce; fino al
-- 22-09-2026 il conto era vw_contatore_merce, ritirata), cioe' tenuti < fatturati:
--   tenuti    = evaso - reso            (dai fulfillment e dai resi)
--   fatturati = somma delle attivita_fatturabili NORMALE con segment_key
--               'DDT_VENDITA:<uid>:R:<ddt_riga_id>' (o 'ORDINE_VENDITA:...'), ricondotte alla riga
--               ordine via ordini_righe_fulfillment.
-- Quindi servono: una riga DDT consegnata order-backed, una commessa con una
-- commessa_attivita che porti quel segment_key, l'AF corrispondente, e il reso.
-- Nessuna fattura vera e' necessaria: 'fatturati' non guarda fattura_riga_id.
-- ------------------------------------------------------------
-- Indice test (1..9):
--   1  le due madri presenti
--   2  fixture: riga in elenco ri-spedizione con residuo atteso
--   3  fixture: riga in coda accrediti, etichetta FACOLTATIVA
--   4  chiusura: ritorna il numero di righe chiuse
--   5  dopo la chiusura: residuo 0 e riga FUORI dall'elenco ri-spedizione
--   6  [IL PUNTO] accredito ANCORA in coda, importo IDENTICO, etichetta DOVUTA
--   7  non-regressione: la quota rinunciata non e' piu' ri-spedibile
--   8  riapertura: residuo e elenco tornano allo stato iniziale
--   9  riapertura: etichetta torna FACOLTATIVA (round-trip completo)
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

-- ⛔ rev 2026-10-24: il mondo si COSTRUISCE (su un DB ricostruito non c'e'
--   nessuna bolla consegnata da pescare): azienda + operatore + cliente +
--   la partita dal builder, e il contesto si apre sul suo operatore. Gira come
--   l'applicazione (ruolo OPERATORE + RLS attiva), non come owner.
-- La partita: un ordine di 5 pezzi a 10 di un articolo merce costruito (non
--   gestito: il test non misura il magazzino), confermato, e la bolla generata
--   dall'ordine (order-backed: ha il fulfillment), CONSEGNATA.
CREATE TEMP TABLE tmp_o AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('pgTAP rinunce scenario',
                  p_quantita => 5, p_prezzo => 10);
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM tmp_o)); END $ctx$;

SELECT plan(9);

-- ============================================================
-- 1) STRUTTURA
-- ============================================================
SELECT ok(
  EXISTS (SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
           WHERE n.nspname = 'vendite' AND p.proname = 'fn_chiudi_riconsegna_reso')
  AND
  EXISTS (SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
           WHERE n.nspname = 'vendite' AND p.proname = 'fn_riapri_riconsegna_reso'),
  '1) fn_chiudi_riconsegna_reso e fn_riapri_riconsegna_reso presenti');

-- ============================================================
-- FIXTURE
-- ============================================================
-- Riga DDT consegnata, order-backed (ha fulfillment): quella costruita qui sopra.
CREATE TEMP TABLE tmp_r AS
SELECT dr.id AS ddt_riga_id, dr.quantita AS consegnato, dr.articolo_id,
       d.id AS ddt_id, d.uid AS ddt_uid,
       f.ordine_riga_id, orr.ordine_id,
       d.billing_account_id, d.utility_id
  FROM vendite.ddt_righe dr
  JOIN vendite.ddt d ON d.id = dr.ddt_id
  JOIN config.stati_doc_ddt s ON s.id = d.stato_doc_ddt_id
  JOIN vendite.ordini_righe_fulfillment f ON f.ddt_riga_id = dr.id
  JOIN vendite.ordini_righe orr ON orr.id = f.ordine_riga_id
 WHERE orr.ordine_id = (SELECT ordine_id FROM tmp_o)
   AND dr.attivo IS TRUE
   AND s.codice_interno = 'CONSEGNATO';

-- Commessa + attivita' con il segment_key che il conto della merce riconosce
-- come "fatturato": 'DDT_VENDITA:<uid>:R:<ddt_riga_id>' (la corsia DDT di
-- fn_af_merce_per_riga, letta dalla partita per chiave).
CREATE TEMP TABLE tmp_com AS
SELECT vendite.fn_get_or_create_commessa(
  p_billing_account_id     => (SELECT billing_account_id FROM tmp_r),
  p_utility_id             => (SELECT utility_id FROM tmp_r),
  p_tipo_commessa          => 'AUTO',
  p_policy_fatturazione    => 'DA_DOCUMENTO',
  p_fatturazione_immediata => false,
  p_priorita_operativa     => 'NORMALE',
  p_meta                   => jsonb_build_object('test_scope','pgtap_rinunce_scenario'),
  p_force_new              => true
) AS commessa_id;

CREATE TEMP TABLE tmp_ca AS
SELECT u.attivita_id
  FROM tmp_r r,
       vendite.fn_upsert_commessa_attivita(
         p_commessa_id                   => (SELECT commessa_id FROM tmp_com),
         -- La riga NORMALE ha la sua sorgente (vincolo 20261012-27).
         p_sorgente_tipo_id => (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'COMMESSA'),
         p_sorgente_uid => ((SELECT commessa_id FROM tmp_com))::text,
         p_segment_key                   => ('DDT_VENDITA:' || r.ddt_uid || ':R:' || r.ddt_riga_id)::varchar,
         p_articolo_id                   => r.articolo_id,
         p_istanza_utility_id            => (SELECT ba.istanza_utility_id
                                               FROM anagrafiche.billing_account ba
                                              WHERE ba.id = r.billing_account_id),
         p_data_attivita                 => script.fn_data_operativa(),
         p_uom_id                        => (SELECT uom_id FROM catalogo.articoli
                                              WHERE id = r.articolo_id),
         p_quantita                      => r.consegnato,
         p_competenza_mese               => date_trunc('month', script.fn_data_operativa())::date,
         p_competenza_dal                => script.fn_data_operativa(),
         p_competenza_al                 => script.fn_data_operativa(),
         p_prezzo_snapshot               => 10.0000000000,
         p_prezzo_base_snapshot          => NULL,
         p_origine_prezzo                => NULL,
         p_tipo_variazione_applicata     => NULL,
         p_valore_variazione_applicata   => NULL,
         p_promo_id                      => NULL,
         p_contratto_id                  => NULL,
         p_categoria_cliente_id_snapshot => NULL,
         p_classe_utenza_id_snapshot     => NULL,
         p_tipo_doc_fiscale_id           => (SELECT id FROM config.tipi_doc_fiscale
                                              WHERE attivo ORDER BY id LIMIT 1),
         p_stato_approvazione            => 'APPROVATA',
         p_stato_emissione               => 'EMESSA',
         p_tipo_movimento                => 'NORMALE',
         p_meta                          => jsonb_build_object('case','RIN_SCEN')
       ) u;

-- AF che rappresenta la quota "fatturata" (tutto il consegnato).
INSERT INTO vendite.attivita_fatturabili (
  articolo_id, istanza_utility_id, data_attivita, quantita,
  competenza_mese, competenza_dal, competenza_al,
  uom_id, prezzo_unitario, tipo_doc_fiscale_id,
  commessa_id, commessa_attivita_id, tipo_movimento,
  -- ⭐ billing_account_id: NOT NULL dal changeSet 20260910-25. Si deriva
  --   dalla COMMESSA, che e' la rotta portante (commessa_id NOT NULL ->
  --   commesse.billing_account_id NOT NULL): la fixture non lo inventa.
  billing_account_id)
SELECT r.articolo_id,
       (SELECT ba.istanza_utility_id FROM anagrafiche.billing_account ba
         WHERE ba.id = r.billing_account_id),
       script.fn_data_operativa(), r.consegnato,
       date_trunc('month', script.fn_data_operativa())::date, script.fn_data_operativa(), script.fn_data_operativa(),
       (SELECT uom_id FROM catalogo.articoli WHERE id = r.articolo_id),
       10.000000,
       (SELECT id FROM config.tipi_doc_fiscale WHERE attivo ORDER BY id LIMIT 1),
       (SELECT commessa_id FROM tmp_com),
       (SELECT attivita_id FROM tmp_ca),
       'NORMALE',
       (SELECT c.billing_account_id FROM vendite.commesse c
         WHERE c.id = (SELECT commessa_id FROM tmp_com))
       FROM tmp_r r;

-- Reso PER RI-CONSEGNA (riapre_residuo = true) di 2 sulla riga DDT, CONFERMATO:
--   la conferma proietta lo stato ordine (residuo riaperto dal reso).
CREATE TEMP TABLE tmp_reso AS
SELECT * FROM dbops.fn_pgtap_crea_reso('rinunce scenario', (SELECT ddt_id FROM tmp_r), 2,
                                       'RESO_PER_RICONSEGNA',
                                       p_ddt_riga_id    => (SELECT ddt_riga_id FROM tmp_r),
                                       p_ordine_riga_id => (SELECT ordine_riga_id FROM tmp_r));

-- Snapshot dell'accredito PRIMA della chiusura: e' il valore che il test 6
-- pretende INVARIATO.
CREATE TEMP TABLE tmp_pre AS
SELECT a.accredito_dovuto, a.etichetta
  FROM vendite.vw_resi_da_accreditare a
 WHERE a.resi_riga_id = (SELECT resi_riga_id FROM tmp_reso);

-- ============================================================
-- 2-3) Stato iniziale
-- ============================================================
SELECT is(
  (SELECT v.qta_residua FROM vendite.vw_resi_da_riconsegnare v
    WHERE v.resi_riga_id = (SELECT resi_riga_id FROM tmp_reso)),
  2.000000::numeric,
  '2) fixture: riga in elenco ri-spedizione con residuo 2');

-- Se questo test fallisce con "0 righe", il fixture non ha prodotto
-- differenza < 0: verificare la catena AF/segment_key, non le madri.
SELECT is(
  (SELECT etichetta::text FROM tmp_pre),
  'FACOLTATIVA',
  '3) fixture: riga in coda accrediti con etichetta FACOLTATIVA');

-- ============================================================
-- 4-6) CHIUSURA
-- ============================================================
SELECT is(
  vendite.fn_chiudi_riconsegna_reso((SELECT reso_id FROM tmp_reso)),
  1,
  '4) chiusura: 1 riga reso chiusa');

SELECT ok(
  vendite.fn_resi_riga_residuo_riconsegna((SELECT resi_riga_id FROM tmp_reso)) = 0
  AND NOT EXISTS (SELECT 1 FROM vendite.vw_resi_da_riconsegnare v
                   WHERE v.resi_riga_id = (SELECT resi_riga_id FROM tmp_reso)),
  '5) dopo la chiusura: residuo 0 e riga fuori dall''elenco ri-spedizione');

-- IL PUNTO: stessa riga, stesso importo, etichetta cambiata.
SELECT is(
  (SELECT a.accredito_dovuto::text || ' / ' || a.etichetta
     FROM vendite.vw_resi_da_accreditare a
    WHERE a.resi_riga_id = (SELECT resi_riga_id FROM tmp_reso)),
  (SELECT accredito_dovuto::text FROM tmp_pre) || ' / DOVUTA',
  '6) accredito ANCORA in coda, importo IDENTICO, etichetta -> DOVUTA');

-- ============================================================
-- 7) Non-regressione: la quota rinunciata non e' ri-spedibile
-- ============================================================
SELECT throws_ok(
  format($$ SELECT vendite.fn_genera_ddt_riconsegna(%s) $$,
         (SELECT reso_id FROM tmp_reso)),
  'P0001', NULL,
  '7) la quota rinunciata non e'' piu'' ri-spedibile');

-- ============================================================
-- 8-9) RIAPERTURA: round-trip
-- ============================================================
-- La riapertura si esegue PRIMA e in isolamento: e' una funzione che SCRIVE, e
-- dentro un AND con le letture che ne dipendono l'ordine di valutazione non
-- sarebbe garantito (il residuo potrebbe essere letto prima della riapertura).
CREATE TEMP TABLE tmp_riap AS
SELECT vendite.fn_riapri_riconsegna_reso((SELECT reso_id FROM tmp_reso)) AS righe;

SELECT ok(
  (SELECT righe FROM tmp_riap) = 1
  AND vendite.fn_resi_riga_residuo_riconsegna((SELECT resi_riga_id FROM tmp_reso)) = 2
  AND EXISTS (SELECT 1 FROM vendite.vw_resi_da_riconsegnare v
               WHERE v.resi_riga_id = (SELECT resi_riga_id FROM tmp_reso)),
  '8) riapertura: residuo torna 2 e la riga torna in elenco');

SELECT is(
  (SELECT a.accredito_dovuto::text || ' / ' || a.etichetta
     FROM vendite.vw_resi_da_accreditare a
    WHERE a.resi_riga_id = (SELECT resi_riga_id FROM tmp_reso)),
  (SELECT accredito_dovuto::text FROM tmp_pre) || ' / FACOLTATIVA',
  '9) round-trip: etichetta torna FACOLTATIVA, importo sempre identico');

SELECT * FROM finish();
ROLLBACK;
