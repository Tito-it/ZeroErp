-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: vendite.fn_genera_ddt_riconsegna — eredita' di testata e di riga
-- Brief: brief-db-ddt-riconsegna-eredita-testata, Fase B (+ Fase C, C-1)
-- ------------------------------------------------------------
-- Indice test (plan 17):
--  0) oggetti presenti (madre, gemello, check di emittibilita')
--  1) ORDER-BACKED, testata: causale/aspetto/addebito/mittente/vettore/
--     fatturazione_immediata uguali al DDT d'origine
--  2) ORDER-BACKED, indirizzi ambito DDT copiati 1:1 con origine_* propagati
--  3) STANDALONE, testata: idem 1) — e' il caso della prova 9, COSTRUITO
--  4) STANDALONE, riga: prezzo e sconto uguali alla riga di DDT d'origine
--  5) STANDALONE, riga: iva_id uguale alla riga d'origine (R4-quater)
--  6) ORDER-BACKED, riga: prezzo_unitario resta NULL — la copia NON ci deve
--     essere, la sorgente e' il COALESCE di fn_list_ddt_da_pushare
--  7) il blocco «viaggio» resta a NULL anche se l'origine lo ha valorizzato
--  8) STANDALONE, indirizzi copiati (senza, l'emissione e' bloccata)
--  9) STANDALONE: il documento SI EMETTE — A-1..A-5 insieme disarmano il
--     punto 3 di fn_check_ddt_emittibile
-- 10) STANDALONE: il riepilogo IVA non ha righe con iva_id NULL
-- 11) il freno della fatturazione non si e' allentato: partita RICONSEGNA,
--     differenza NULL — anche ora che la riga un prezzo ce l'ha
-- 12) idem: la riga non compare in fn_list_ddt_da_pushare
-- 13) C-1: riga con prezzo e senza aliquota -> l'emissione RIFIUTA
-- 14) C-1: causale NON fatturabile e riga senza prezzo -> l'emissione PASSA
--     (il DDT di solo trasporto non si rompe)
-- 15) C-1: fn_available_actions_ddt espone «Emetti» disabilitato COL MOTIVO
-- 16) C-1: ⭐ causale NON fatturabile ma riga con prezzo senza aliquota ->
--     rifiuta LO STESSO — il discrimine e' il prezzo, non la causale
--
-- Scopo:
--  - il documento generato dal database non nasce piu' nudo: eredita cio' che
--    e' una SCELTA (relazione commerciale) e non cio' che e' una MISURA
--    (il viaggio gia' avvenuto);
--  - il 6) e il 7) sono i due test che presidiano una decisione di NON fare:
--    senza, «non copiare» e' un commento, e il primo che allarga la INSERT
--    non accende niente;
--  - l'11) e il 12) sono la non-regressione resa necessaria dal prezzo: prima
--    il prezzo assente NASCONDEVA l'esito, quindi un verde di ieri non prova
--    niente su oggi.
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga non verrebbero mai esercitati (qui
--   il COMMIT non arriva mai, si chiude in ROLLBACK) e il file sarebbe verde
--   per sottrazione. In testa: le unita' padre/figlio di questa fixture sono
--   sempre complete a fine istruzione.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: il test gira come gira l'applicazione (OPERATORE +
-- RLS attiva), non come owner.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(17);

SET LOCAL app.ruolo_applicativo = 'OPERATORE';
SET LOCAL app.current_user_id = '1';

-- ============================================================
-- 0) Oggetti presenti
-- ============================================================
SELECT ok(
  (SELECT count(*) = 3 FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE (n.nspname = 'vendite' AND p.proname IN
             ('fn_genera_ddt_riconsegna','fn_genera_ddt_da_ordine'))
       OR (n.nspname = 'script'  AND p.proname = 'fn_check_ddt_emittibile'))
  AND to_regclass('vendite.ddt_indirizzi')                IS NOT NULL
  AND to_regclass('vendite.vw_ddt_riepilogo_iva_dettaglio') IS NOT NULL
  AND to_regclass('vendite.vw_partite_merce')             IS NOT NULL,
  '0) oggetti presenti (madre, gemello, check emittibilita)');

-- ============================================================
-- Riferimenti. ⚠️ Una sola scelta per riga, mai due sotto-select
--   indipendenti sulla stessa tabella: potrebbero pescare righe diverse.
--   ⚠️ L'emittente NON si pesca, si DERIVA da chi agisce.
-- ============================================================
CREATE TEMP TABLE tmp_ref AS
SELECT
  (SELECT ba.id FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL AND ba.istanza_utility_id IS NOT NULL
    ORDER BY ba.id LIMIT 1)                                                AS billing_account_id,
  (SELECT sr.id FROM anagrafiche.soggetti_ruoli sr ORDER BY sr.id LIMIT 1) AS soggetto_ruolo_id,
  -- ⭐ Mittente e vettore DEVONO essere due soggetti DIVERSI fra loro e dal
  --   destinatario: se coincidessero, il test 1) e il 3) passerebbero anche
  --   con una funzione che copia la colonna sbagliata.
  (SELECT sr.id FROM anagrafiche.soggetti_ruoli sr ORDER BY sr.id OFFSET 1 LIMIT 1) AS mittente_sr_id,
  (SELECT sr.id FROM anagrafiche.soggetti_ruoli sr ORDER BY sr.id OFFSET 2 LIMIT 1) AS vettore_sr_id,
  (SELECT a.id FROM catalogo.articoli a
    WHERE a.attivo IS TRUE AND COALESCE(a.is_composito, FALSE) IS FALSE
    ORDER BY a.data_insert DESC NULLS LAST LIMIT 1)                        AS articolo_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1)                 AS valuta_id,
  (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1) AS iva_id,
  script.fn_pgtap_emittente_operatore()                                    AS emittente_fiscale_id,
  (SELECT s.id FROM config.stati_doc_ordini s WHERE s.codice_interno='CONFERMATO'  AND s.attivo LIMIT 1) AS stato_ord_conf_id,
  (SELECT s.id FROM config.stati_doc_ddt   s WHERE s.codice_interno='DRAFT'        AND s.attivo LIMIT 1) AS stato_ddt_draft_id,
  (SELECT s.id FROM config.stati_doc_ddt   s WHERE s.codice_interno='EMESSO'       AND s.attivo LIMIT 1) AS stato_ddt_emesso_id,
  (SELECT s.id FROM config.stati_doc_ddt   s WHERE s.codice_interno='SPEDITO'      AND s.attivo LIMIT 1) AS stato_ddt_spedito_id,
  (SELECT s.id FROM config.stati_doc_ddt   s WHERE s.codice_interno='CONSEGNATO'   AND s.attivo LIMIT 1) AS stato_ddt_conseg_id,
  (SELECT s.id FROM config.sorgenti        s WHERE s.codice_interno='DDT_VENDITA'  AND s.attivo LIMIT 1) AS sorgente_ddt_id,
  (SELECT s.id FROM config.stati_doc_reso  s WHERE s.codice_interno='DRAFT'        AND s.attivo LIMIT 1) AS stato_reso_draft_id,
  (SELECT t.id FROM config.tipi_reso       t WHERE t.codice_interno='RESO_PER_RICONSEGNA' AND t.attivo LIMIT 1) AS tipo_riconsegna_id,
  (SELECT id FROM config.tipi_indirizzi WHERE codice_interno='CON')         AS tipo_ind_con_id,
  -- ⚠️ Aggancio per `codice`, non per `codice_interno`: config.causali_trasporto
  --   la colonna immutabile NON ce l'ha (caso CANDIDATE_ADD_CI delle linee
  --   guida §6d). E' un debito noto e questo test non lo aggrava — la funzione
  --   sotto test non contiene nessun letterale di causale, eredita l'id.
  (SELECT c.id FROM config.causali_trasporto c WHERE c.codice='VENDITA' AND c.attivo LIMIT 1) AS causale_vendita_id,
  -- ⭐ Una causale NON fatturabile serve a due test, e sono i due che
  --   distinguono il punto 3 dal punto 3-bis: senza prezzo il documento si
  --   emette (solo trasporto), CON un prezzo no — perche' il discrimine del
  --   3-bis e' il prezzo, non la causale.
  (SELECT c.id FROM config.causali_trasporto c
    WHERE c.fatturabile IS FALSE AND c.attivo IS TRUE ORDER BY c.id LIMIT 1) AS causale_non_fatt_id,
  (SELECT ab.id FROM config.aspetti_beni ab WHERE ab.attivo IS TRUE ORDER BY ab.id LIMIT 1)   AS aspetto_id,
  (SELECT ma.id FROM config.modalita_addebito_trasporto ma
     WHERE ma.attivo IS TRUE ORDER BY ma.id LIMIT 1)                        AS modalita_addebito_id;

-- ============================================================
-- FIXTURE ORD — ordine -> DDT (gemello) -> CONSEGNATO -> reso order-backed
-- ============================================================
CREATE TEMP TABLE tmp_ord AS
WITH ins AS (
  INSERT INTO vendite.ordini (soggetto_ruolo_id, billing_account_id, stato_doc_ordine_id,
    valuta_id, data, fatturazione_trigger, emittente_fiscale_id, storicizza, meta)
  SELECT r.soggetto_ruolo_id, r.billing_account_id, r.stato_ord_conf_id,
         r.valuta_id, CURRENT_DATE, 'SPEDITO', r.emittente_fiscale_id, false,
         jsonb_build_object('test_scope','pgtap_riconsegna_eredita')
  FROM tmp_ref r RETURNING id, uid)
SELECT * FROM ins;

CREATE TEMP TABLE tmp_ord_riga AS
WITH ins AS (
  INSERT INTO vendite.ordini_righe (ordine_id, riga_nr, articolo_id, descrizione,
    qta_operativa, quantita, prezzo_unitario, sconto_percentuale, iva_id,
    attivo, storicizza, meta)
  SELECT o.id, 1, r.articolo_id, 'Riga eredita ORD', 10, 10, 25, 5, r.iva_id,
         true, false, jsonb_build_object('test_scope','pgtap_riconsegna_eredita')
  FROM tmp_ord o, tmp_ref r RETURNING id)
SELECT * FROM ins;

CREATE TEMP TABLE tmp_ddt_ord AS
SELECT vendite.fn_genera_ddt_da_ordine((SELECT id FROM tmp_ord)) AS ddt_id;

-- Il DDT d'origine porta il blocco «relazione» E il blocco «viaggio»: e' cio'
-- che rende distinguibili i test 1) e 7).
UPDATE vendite.ddt d
   SET causale_trasporto_id           = r.causale_vendita_id,
       aspetto_bene_id                = r.aspetto_id,
       modalita_addebito_trasporto_id = r.modalita_addebito_id,
       mittente_soggetto_ruolo_id     = r.mittente_sr_id,
       vettore_soggetto_ruolo_id      = r.vettore_sr_id,
       num_colli   = 7,   peso_lordo = 120.5, peso_netto = 110.0, volume = 3.25,
       targa       = 'AB123CD',  autista = 'Mario Bianchi',
       tracking_code = 'TRK-ORIGINE-0001',
       data_ora_partenza = now(), data_ora_consegna_prev = now() + interval '1 day'
  FROM tmp_ref r
 WHERE d.id = (SELECT ddt_id FROM tmp_ddt_ord);

INSERT INTO vendite.ddt_indirizzi (ddt_id, tipo_indirizzo_id, snapshot,
                                   origine_soggetto_ruolo_id)
SELECT (SELECT ddt_id FROM tmp_ddt_ord), r.tipo_ind_con_id,
       '{"display":"CON eredita ORD"}'::jsonb, r.soggetto_ruolo_id
  FROM tmp_ref r
ON CONFLICT DO NOTHING;

UPDATE vendite.ddt SET stato_doc_ddt_id=(SELECT stato_ddt_emesso_id  FROM tmp_ref) WHERE id=(SELECT ddt_id FROM tmp_ddt_ord);
UPDATE vendite.ddt SET stato_doc_ddt_id=(SELECT stato_ddt_spedito_id FROM tmp_ref) WHERE id=(SELECT ddt_id FROM tmp_ddt_ord);
UPDATE vendite.ddt SET stato_doc_ddt_id=(SELECT stato_ddt_conseg_id  FROM tmp_ref) WHERE id=(SELECT ddt_id FROM tmp_ddt_ord);

CREATE TEMP TABLE tmp_ddt_ord_riga AS
SELECT dr.id, dr.articolo_id, dr.descrizione, dr.uom_operativa_id, dr.factor_to_base,
       dr.prezzo_unitario, dr.sconto_percentuale, dr.iva_id
  FROM vendite.ddt_righe dr
 WHERE dr.ddt_id = (SELECT ddt_id FROM tmp_ddt_ord)
 ORDER BY dr.riga_nr, dr.id LIMIT 1;

CREATE TEMP TABLE tmp_reso_ord AS
WITH ins AS (
  INSERT INTO vendite.resi (stato_doc_reso_id, sorgente_tipo_id, sorgente_uid, storicizza, meta)
  SELECT r.stato_reso_draft_id, r.sorgente_ddt_id,
         (SELECT d.uid FROM vendite.ddt d WHERE d.id=(SELECT ddt_id FROM tmp_ddt_ord)),
         false, jsonb_build_object('test_scope','pgtap_riconsegna_eredita')
  FROM tmp_ref r RETURNING id)
SELECT * FROM ins;

INSERT INTO vendite.resi_righe (reso_id, riga_nr, ddt_riga_id, ordine_riga_id,
  articolo_id, descrizione, qta_operativa, uom_operativa_id, factor_to_base,
  tipo_reso_id, storicizza)
SELECT (SELECT id FROM tmp_reso_ord), 1, dr.id, (SELECT id FROM tmp_ord_riga),
       dr.articolo_id, dr.descrizione, 4, dr.uom_operativa_id, dr.factor_to_base,
       (SELECT tipo_riconsegna_id FROM tmp_ref), false
  FROM tmp_ddt_ord_riga dr;

SELECT vendite.fn_conferma_reso((SELECT id FROM tmp_reso_ord));

CREATE TEMP TABLE tmp_ric_ord AS
SELECT vendite.fn_genera_ddt_riconsegna((SELECT id FROM tmp_reso_ord)) AS ddt_id;

-- ============================================================
-- 1) ORDER-BACKED, testata ereditata
-- ============================================================
SELECT results_eq(
  format($q$SELECT causale_trasporto_id, aspetto_bene_id,
                   modalita_addebito_trasporto_id, mittente_soggetto_ruolo_id,
                   vettore_soggetto_ruolo_id, fatturazione_immediata
              FROM vendite.ddt WHERE id = %s$q$, (SELECT ddt_id FROM tmp_ric_ord)),
  format($q$SELECT causale_trasporto_id, aspetto_bene_id,
                   modalita_addebito_trasporto_id, mittente_soggetto_ruolo_id,
                   vettore_soggetto_ruolo_id, fatturazione_immediata
              FROM vendite.ddt WHERE id = %s$q$, (SELECT ddt_id FROM tmp_ddt_ord)),
  '1) order-backed: causale/aspetto/addebito/mittente/vettore/fatt_immediata ereditati');

-- ============================================================
-- 2) ORDER-BACKED, indirizzi copiati 1:1 con origine_* propagati
-- ============================================================
SELECT results_eq(
  format($q$SELECT tipo_indirizzo_id, snapshot, origine_indirizzo_id,
                   origine_soggetto_ruolo_id
              FROM vendite.ddt_indirizzi WHERE ddt_id = %s
             ORDER BY tipo_indirizzo_id$q$, (SELECT ddt_id FROM tmp_ric_ord)),
  format($q$SELECT tipo_indirizzo_id, snapshot, origine_indirizzo_id,
                   origine_soggetto_ruolo_id
              FROM vendite.ddt_indirizzi WHERE ddt_id = %s
             ORDER BY tipo_indirizzo_id$q$, (SELECT ddt_id FROM tmp_ddt_ord)),
  '2) order-backed: indirizzi ambito DDT copiati 1:1, origine_* propagati');

-- ============================================================
-- 6) ORDER-BACKED, la riga NON porta il prezzo — la copia non ci deve essere
--    ⭐ E' il test di una decisione di NON fare: senza, nessuno si accorge
--    del giorno in cui qualcuno "uniforma" i due rami.
-- ============================================================
SELECT ok(
  (SELECT bool_and(dr.prezzo_unitario IS NULL AND dr.sconto_percentuale IS NULL
                   AND dr.iva_id IS NULL)
     FROM vendite.ddt_righe dr WHERE dr.ddt_id = (SELECT ddt_id FROM tmp_ric_ord)),
  '6) order-backed: prezzo/sconto/iva restano NULL (la sorgente e il COALESCE del lister)');

-- ============================================================
-- FIXTURE STD — DDT autonomo (nessun ordine, nessun fulfillment)
--   E' il caso della prova 9, e va COSTRUITO: su un database ricostruito da
--   zero non ce n'e' nessuno, e un test che lo cercasse passerebbe a vuoto.
-- ============================================================
CREATE TEMP TABLE tmp_ddt_std AS
WITH ins AS (
  INSERT INTO vendite.ddt (data, stato_doc_ddt_id, destinatario_soggetto_ruolo_id,
    billing_account_id, utility_id, valuta_id, emittente_fiscale_id,
    causale_trasporto_id, aspetto_bene_id, modalita_addebito_trasporto_id,
    mittente_soggetto_ruolo_id, vettore_soggetto_ruolo_id,
    num_colli, peso_lordo, peso_netto, volume, targa, autista, tracking_code,
    data_ora_partenza, data_ora_consegna_prev, storicizza, meta)
  SELECT CURRENT_DATE, r.stato_ddt_draft_id, r.soggetto_ruolo_id,
         r.billing_account_id, ba.utility_id, r.valuta_id, r.emittente_fiscale_id,
         r.causale_vendita_id, r.aspetto_id, r.modalita_addebito_id,
         r.mittente_sr_id, r.vettore_sr_id,
         9, 200.75, 180.25, 5.5, 'ZZ999ZZ', 'Luigi Verdi', 'TRK-STANDALONE-0009',
         now(), now() + interval '2 days', false,
         jsonb_build_object('test_scope','pgtap_riconsegna_eredita')
    FROM tmp_ref r
    LEFT JOIN anagrafiche.billing_account ba ON ba.id = r.billing_account_id
  RETURNING id, uid)
SELECT * FROM ins;

CREATE TEMP TABLE tmp_ddt_std_riga AS
WITH ins AS (
  INSERT INTO vendite.ddt_righe (ddt_id, riga_nr, articolo_id, descrizione,
    qta_operativa, factor_to_base, prezzo_unitario, sconto_percentuale, iva_id,
    attivo, storicizza, meta)
  SELECT (SELECT id FROM tmp_ddt_std), 1, r.articolo_id, 'Riga eredita STD',
         6, 1, 42.50, 12.5, r.iva_id, true, false,
         jsonb_build_object('test_scope','pgtap_riconsegna_eredita')
    FROM tmp_ref r
  RETURNING id, articolo_id, descrizione, uom_operativa_id, factor_to_base,
            prezzo_unitario, sconto_percentuale, iva_id)
SELECT * FROM ins;

INSERT INTO vendite.ddt_indirizzi (ddt_id, tipo_indirizzo_id, snapshot,
                                   origine_soggetto_ruolo_id)
SELECT (SELECT id FROM tmp_ddt_std), r.tipo_ind_con_id,
       '{"display":"CON eredita STD"}'::jsonb, r.soggetto_ruolo_id
  FROM tmp_ref r;

UPDATE vendite.ddt SET stato_doc_ddt_id=(SELECT stato_ddt_emesso_id  FROM tmp_ref) WHERE id=(SELECT id FROM tmp_ddt_std);
UPDATE vendite.ddt SET stato_doc_ddt_id=(SELECT stato_ddt_spedito_id FROM tmp_ref) WHERE id=(SELECT id FROM tmp_ddt_std);
UPDATE vendite.ddt SET stato_doc_ddt_id=(SELECT stato_ddt_conseg_id  FROM tmp_ref) WHERE id=(SELECT id FROM tmp_ddt_std);

CREATE TEMP TABLE tmp_reso_std AS
WITH ins AS (
  INSERT INTO vendite.resi (stato_doc_reso_id, sorgente_tipo_id, sorgente_uid, storicizza, meta)
  SELECT r.stato_reso_draft_id, r.sorgente_ddt_id, (SELECT uid FROM tmp_ddt_std),
         false, jsonb_build_object('test_scope','pgtap_riconsegna_eredita')
  FROM tmp_ref r RETURNING id)
SELECT * FROM ins;

-- ⚠️ ordine_riga_id NULL, e non e' una scorciatoia: la riga di DDT non ha
--   nessun fulfillment, e trgfn_resi_righe_guard_origine_coerente RIFIUTA un
--   riferimento a un ordine che quella merce non l'ha spedita.
INSERT INTO vendite.resi_righe (reso_id, riga_nr, ddt_riga_id, ordine_riga_id,
  articolo_id, descrizione, qta_operativa, uom_operativa_id, factor_to_base,
  tipo_reso_id, storicizza)
SELECT (SELECT id FROM tmp_reso_std), 1, dr.id, NULL,
       dr.articolo_id, dr.descrizione, 2, dr.uom_operativa_id, dr.factor_to_base,
       (SELECT tipo_riconsegna_id FROM tmp_ref), false
  FROM tmp_ddt_std_riga dr;

SELECT vendite.fn_conferma_reso((SELECT id FROM tmp_reso_std));

CREATE TEMP TABLE tmp_ric_std AS
SELECT vendite.fn_genera_ddt_riconsegna((SELECT id FROM tmp_reso_std)) AS ddt_id;

CREATE TEMP TABLE tmp_ric_std_riga AS
SELECT dr.* FROM vendite.ddt_righe dr
 WHERE dr.ddt_id = (SELECT ddt_id FROM tmp_ric_std)
 ORDER BY dr.riga_nr, dr.id LIMIT 1;

-- ============================================================
-- 3) STANDALONE, testata ereditata — il caso della prova 9
-- ============================================================
SELECT results_eq(
  format($q$SELECT causale_trasporto_id, aspetto_bene_id,
                   modalita_addebito_trasporto_id, mittente_soggetto_ruolo_id,
                   vettore_soggetto_ruolo_id
              FROM vendite.ddt WHERE id = %s$q$, (SELECT ddt_id FROM tmp_ric_std)),
  format($q$SELECT causale_trasporto_id, aspetto_bene_id,
                   modalita_addebito_trasporto_id, mittente_soggetto_ruolo_id,
                   vettore_soggetto_ruolo_id
              FROM vendite.ddt WHERE id = %s$q$, (SELECT id FROM tmp_ddt_std)),
  '3) standalone: causale/aspetto/addebito/mittente/vettore ereditati (prova 9)');

-- ============================================================
-- 4) STANDALONE, riga: prezzo e sconto dalla riga di DDT d'origine
-- ============================================================
SELECT results_eq(
  $q$SELECT prezzo_unitario, sconto_percentuale FROM tmp_ric_std_riga$q$,
  $q$SELECT prezzo_unitario, sconto_percentuale FROM tmp_ddt_std_riga$q$,
  '4) standalone: prezzo e sconto uguali alla riga di DDT d''origine');

-- ============================================================
-- 5) STANDALONE, riga: aliquota ereditata (R4-quater)
--    ⚠️ Provvisorio per progetto: col risolutore IVA questa copia va tolta,
--    e allora questa asserzione va riscritta, non cancellata.
-- ============================================================
SELECT is(
  (SELECT iva_id FROM tmp_ric_std_riga),
  (SELECT iva_id FROM tmp_ddt_std_riga),
  '5) standalone: iva_id uguale alla riga d''origine (R4-quater, provvisorio)');

-- ============================================================
-- 7) ⛔ Il blocco «viaggio» resta a NULL, benche' l'origine lo abbia pieno
--    Senza questo test «non copiare» e' un commento, e il primo che allarga
--    la INSERT li porta dentro senza che niente si accenda.
-- ============================================================
SELECT ok(
  (SELECT num_colli IS NULL AND peso_lordo IS NULL AND peso_netto IS NULL
      AND volume IS NULL AND targa IS NULL AND autista IS NULL
      AND tracking_code IS NULL AND data_ora_partenza IS NULL
      AND data_ora_consegna_prev IS NULL
     FROM vendite.ddt WHERE id = (SELECT ddt_id FROM tmp_ric_std)),
  '7) il blocco viaggio resta NULL anche se l''origine lo ha valorizzato');

-- ============================================================
-- 8) STANDALONE, indirizzi copiati
-- ============================================================
SELECT is(
  (SELECT count(*)::int FROM vendite.ddt_indirizzi
    WHERE ddt_id = (SELECT ddt_id FROM tmp_ric_std)),
  (SELECT count(*)::int FROM vendite.ddt_indirizzi
    WHERE ddt_id = (SELECT id FROM tmp_ddt_std)),
  '8) standalone: indirizzi ambito DDT copiati (senza, l''emissione e bloccata)');

-- ============================================================
-- 9) ⭐ STANDALONE: il documento SI EMETTE.
--    E' la prova che A-1..A-5 INSIEME disarmano il punto 3 di
--    fn_check_ddt_emittibile: la causale ereditata e' fatturabile, e nello
--    standalone non c'e' nessun fulfillment da cui risalire il prezzo.
--    Provare le colonne una per una non lo dimostra.
-- ============================================================
SELECT lives_ok(
  format($q$UPDATE vendite.ddt SET stato_doc_ddt_id = %s WHERE id = %s$q$,
         (SELECT stato_ddt_emesso_id FROM tmp_ref), (SELECT ddt_id FROM tmp_ric_std)),
  '9) standalone: il DDT di ri-consegna si EMETTE');

-- ============================================================
-- 10) STANDALONE: nessuna riga di riepilogo IVA senza aliquota.
--     ⭐ E' il presidio del difetto silenzioso: vw_ddt_righe_iva_base filtra
--     il prezzo e NON l'aliquota, quindi una riga con prezzo e senza iva_id
--     comparirebbe qui con imponibile pieno e imposta zero.
-- ============================================================
SELECT is(
  (SELECT count(*)::int FROM vendite.vw_ddt_riepilogo_iva_dettaglio
    WHERE ddt_id = (SELECT ddt_id FROM tmp_ric_std) AND iva_id IS NULL),
  0,
  '10) standalone: il riepilogo IVA non ha righe senza aliquota');

-- ============================================================
-- 11) ⭐ Il freno della fatturazione non si e' allentato.
--     Prima il prezzo assente NASCONDEVA l'esito: un verde di ieri non prova
--     niente su oggi, che la riga un prezzo ce l'ha.
-- ============================================================
SELECT ok(
  (SELECT bool_and(pm.stato = 'RICONSEGNA' AND pm.differenza IS NULL)
     FROM vendite.vw_partite_merce pm
    WHERE pm.ddt_riga_id = (SELECT id FROM tmp_ric_std_riga)),
  '11) partita merce: stato RICONSEGNA e differenza NULL, col prezzo valorizzato');

-- ============================================================
-- 12) ...e la riga non entra nel lister della fatturazione.
-- ============================================================
SELECT is(
  (SELECT count(*)::int FROM vendite.fn_list_ddt_da_pushare(
            p_ddt_id => (SELECT ddt_id FROM tmp_ric_std))),
  0,
  '12) la riga di ri-consegna non compare in fn_list_ddt_da_pushare');

-- ============================================================
-- FASE C (C-1) — una riga con prezzo porta anche l'aliquota
--   Fixture propria: un DDT autonomo con DUE righe, per poter spegnere
--   l'aliquota su una sola.
-- ============================================================
CREATE TEMP TABLE tmp_ddt_iva AS
WITH ins AS (
  INSERT INTO vendite.ddt (data, stato_doc_ddt_id, destinatario_soggetto_ruolo_id,
    billing_account_id, valuta_id, emittente_fiscale_id, causale_trasporto_id,
    storicizza, meta)
  SELECT CURRENT_DATE, r.stato_ddt_draft_id, r.soggetto_ruolo_id,
         r.billing_account_id, r.valuta_id, r.emittente_fiscale_id,
         r.causale_vendita_id, false,
         jsonb_build_object('test_scope','pgtap_riconsegna_eredita')
  FROM tmp_ref r RETURNING id)
SELECT * FROM ins;

INSERT INTO vendite.ddt_indirizzi (ddt_id, tipo_indirizzo_id, snapshot)
SELECT (SELECT id FROM tmp_ddt_iva), (SELECT tipo_ind_con_id FROM tmp_ref),
       '{"display":"CON gate iva"}'::jsonb;

-- Riga CON prezzo e SENZA aliquota: e' il caso che deve rifiutare.
INSERT INTO vendite.ddt_righe (ddt_id, riga_nr, articolo_id, descrizione,
  qta_operativa, factor_to_base, prezzo_unitario, iva_id, attivo, storicizza, meta)
SELECT (SELECT id FROM tmp_ddt_iva), 1, r.articolo_id, 'Riga con prezzo senza IVA',
       1, 1, 10, NULL, true, false,
       jsonb_build_object('test_scope','pgtap_riconsegna_eredita')
  FROM tmp_ref r;

-- ============================================================
-- 13) C-1: l'emissione RIFIUTA, e con un errore di DOMINIO (P0001),
--     non con un errore qualunque.
-- ============================================================
SELECT throws_ok(
  format($q$UPDATE vendite.ddt SET stato_doc_ddt_id = %s WHERE id = %s$q$,
         (SELECT stato_ddt_emesso_id FROM tmp_ref), (SELECT id FROM tmp_ddt_iva)),
  'P0001', NULL,
  '13) C-1: riga con prezzo e senza aliquota -> l''emissione rifiuta');

-- ============================================================
-- 15) C-1: il pulsante «Emetti» e' DISABILITATO E DICE PERCHE'.
--     ⚠️ Un motivo che non arriva a video e' un pulsante grigio e muto: qui
--     si verifica che reason e reason_key ci siano entrambi.
-- ============================================================
SELECT ok(
  (WITH a AS (
     SELECT jsonb_array_elements(
              (script.fn_available_actions_ddt((SELECT id FROM tmp_ddt_iva))
                 -> 'available_actions')) AS az)
   SELECT bool_or( (az->>'enabled')::boolean IS FALSE
               AND az->>'reason'     = 'RIGA_SENZA_ALIQUOTA'
               AND az->>'reason_key' = 'vendite.ddt.azione_reason.iva_mancante')
     FROM a),
  '15) C-1: azione Emetti disabilitata con reason e reason_key valorizzati');

-- ============================================================
-- 16) ⭐ IL TEST CHE DIMOSTRA LA DECISIONE: il discrimine e' il PREZZO,
--     NON la causale.
--     Stesso documento con una causale NON fatturabile — quindi il punto 3
--     (prezzo risolvibile) TACE — e la riga che il prezzo ce l'ha e
--     l'aliquota no: l'emissione deve rifiutare LO STESSO.
--     ⛔ Se un domani qualcuno spostasse il controllo dentro il ramo
--     `IF COALESCE(v_fatturabile, false)` — che e' la cosa che sembra
--     ordinata, visto che i punti 3, 5 e 6 stanno li' — questo test
--     diventerebbe rosso. E' l'unico che se ne accorgerebbe: la riga
--     entrerebbe comunque in vw_ddt_righe_iva_base, che la causale non la
--     guarda affatto.
-- ============================================================
UPDATE vendite.ddt SET causale_trasporto_id = (SELECT causale_non_fatt_id FROM tmp_ref)
 WHERE id = (SELECT id FROM tmp_ddt_iva);

SELECT throws_ok(
  format($q$UPDATE vendite.ddt SET stato_doc_ddt_id = %s WHERE id = %s$q$,
         (SELECT stato_ddt_emesso_id FROM tmp_ref), (SELECT id FROM tmp_ddt_iva)),
  'P0001', NULL,
  '16) C-1: causale NON fatturabile ma riga con prezzo senza aliquota -> rifiuta lo stesso');

-- ============================================================
-- 14) C-1: il DDT di SOLO TRASPORTO non si rompe.
--     Causale non fatturabile E riga senza prezzo -> l'emissione PASSA.
--     ⚠️ Sono DUE condizioni, non una: con la causale fatturabile una riga
--     senza prezzo la ferma gia' il punto 3 (E_DDT_PREZZO_NON_RISOLVIBILE),
--     e il «solo trasporto» che il punto 1 dichiara legittimo e' proprio il
--     documento che NON vende. Scritto qui perche' la prima stesura di questo
--     test toglieva il solo prezzo, lasciava VENDITA, e prendeva un rosso che
--     sembrava del punto 3-bis e non lo era.
-- ============================================================
UPDATE vendite.ddt_righe SET prezzo_unitario = NULL
 WHERE ddt_id = (SELECT id FROM tmp_ddt_iva);

SELECT lives_ok(
  format($q$UPDATE vendite.ddt SET stato_doc_ddt_id = %s WHERE id = %s$q$,
         (SELECT stato_ddt_emesso_id FROM tmp_ref), (SELECT id FROM tmp_ddt_iva)),
  '14) C-1: causale non fatturabile e riga senza prezzo -> emette (solo trasporto)');

SELECT * FROM finish();
ROLLBACK;
