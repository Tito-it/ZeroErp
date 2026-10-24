-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- rev 2026-10-25 (brief-db-pgtap-bolla-e-reso-costruiti, giro 1): la bolla da ordine dal builder dbops.fn_pgtap_crea_ddt_da_ordine; restano scritti a mano i resi (giro 2), che sono il caso del test; la colonna stato_ddt_consegnato_id resta in tmp_refs perche' la legge il test 2.
-- pgTAP test per Zero ERP
-- Test: motore resi vendita (vendite.resi / resi_righe / ponte)
--       fn_conferma_reso, fn_genera_ddt_riconsegna, fn_annulla_reso,
--       residuo reso-aware, flip DDT, read-side.
-- Brief: brief-db-resi-vendita §6
-- ------------------------------------------------------------
-- Indice test (27 asserzioni: 1..26 + sub 8b/23a, meno la 21 rimossa):
--  1) oggetti motore resi presenti
--  2) riferimenti minimi disponibili
--  3) reso DRAFT: emittente ereditato dal DDT (normalize)
--  4) reso: billing ereditato dal DDT
--  5) numero NULL in DRAFT
--  6) resi_righe: quantita derivata da qta_operativa (3)
--  7) guard over-return: Sigma qta_resa > consegnato -> E_RESO_QTA_SUPERA_CONSEGNATO
--  8) fn_conferma_reso -> stato CONFERMATO
--  9) numero assegnato alla CONFERMA
-- 10) numero immutabile dopo assegnazione
-- 11) residuo riaperto: fn_ordine_ha_residuo_evasione = true (reso-aware)
-- 12) proiezione stato ordine -> PARZIALMENTE_EVASO
-- 13) coda da_riconsegnare: qta_residua=3, stato DA_RICONSEGNARE
-- 14) fn_genera_ddt_riconsegna parziale (qta 2) -> nuovo ddt non-null
-- 15) ponte: copertura=2, stato_riconsegna=PARZIALE
-- 16) fn_genera_ddt_riconsegna resto (NULL) -> copertura=3
-- 17) stato_riconsegna=COMPLETATA, sparita dalla coda
-- 18) ordine torna EVASO (residuo chiuso dalla ri-spedizione)
-- 19) annullo bloccato se gia' ri-spedito -> E_RESO_ANNULLO_CON_RICONSEGNE
-- 20) flip DDT: reso a credito TOTALE confermato -> DDT CONSEGNATO->RESO
-- 21) RIMOSSA (step 4): la coda accrediti si popola dal conto, non dal tipo reso
--     -> coperta da test-vw-resi-da-accreditare-contatore-v1
-- 22) fn_available_actions_reso: reso CONFERMATO espone azione 'annulla'
-- 23) annullo reso a credito (non ri-spedito) -> ANNULLATO
-- 24) guard: reso da DDT non CONSEGNATO -> E_RESO_DDT_NON_CONSEGNATO
-- 25) flip: bozza 6 + confermato 4 su DDT da 10 -> DDT resta CONSEGNATO
--     (le BOZZE non contano: step 2b, brief-db-fatturazione-ddt-resi §3b)
-- 26) confermata anche la bozza (6+4=10 confermati) -> DDT flippa a RESO
--     (il flip funziona ancora: e' lo STATO a decidere, non l'esistenza)
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
-- ⛔ rev 2026-10-13: il mondo si COSTRUISCE (in CI l'utente 1 non esiste;
--   anagrafiche e articoli sono vuoti). Prima il mondo — azienda, operatore,
--   cliente legato a quell'azienda — poi il contesto, sul SUO operatore.
--   Dal 2026-09-28 conferma e annullo del reso sono verbi SECURITY DEFINER
--   col perimetro nella WHERE e il permesso conferma_reso (Lotto 3-bis, D-3b-f).
CREATE TEMP TABLE _m AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('pgTAP resi motore');
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _m)); END $ctx$;

SELECT plan(27);

-- Dal 2026-09-28 conferma e annullo del reso sono verbi che applicano
-- l'azione conferma_reso (brief-db-magazzino-lotto-3-bis-carico-da-reso, D-3b-f):
-- l'operatore di fixture non ha azioni, si concede qui.
DO $az$ BEGIN
    PERFORM dbops.fn_pgtap_concedi_azione(
        NULLIF(current_setting('app.current_user_id', true), '')::integer, 'conferma_reso');
END $az$;

-- ============================================================
-- 1) Oggetti motore resi presenti
-- ============================================================
SELECT ok(
  (SELECT count(*) = 4 FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE (n.nspname = 'vendite' AND p.proname IN
             ('fn_conferma_reso','fn_genera_ddt_riconsegna','fn_annulla_reso'))
       OR (n.nspname = 'script' AND p.proname = 'fn_available_actions_reso'))
  AND to_regclass('vendite.resi') IS NOT NULL
  AND to_regclass('vendite.resi_righe') IS NOT NULL
  AND to_regclass('vendite.resi_righe_riconsegne') IS NOT NULL
  AND to_regclass('vendite.vw_resi_da_riconsegnare') IS NOT NULL
  AND to_regclass('vendite.vw_resi_da_accreditare') IS NOT NULL,
  '1) oggetti motore resi presenti');

-- ============================================================
-- Riferimenti minimi: il mondo costruito + il catalogo di seed
-- ============================================================
CREATE TEMP TABLE tmp_refs AS
SELECT
  -- ⛔ rev 2026-10-13: cliente ed emittente dal mondo costruito, non il primo BA
  --   del database; l'articolo si costruisce (nasce merce, non solo componente:
  --   ordine e bolla lo ammettono — brief-db-articoli-ammessi-per-documento, Lotto 3a).
  (SELECT billing_account_id FROM _m)                                    AS billing_account_id,
  dbops.fn_pgtap_crea_articolo('PGTAP-RESI-MOTORE', false)               AS articolo_id,
  (SELECT s.id FROM config.stati_doc_ddt s WHERE s.codice_interno='CONSEGNATO' AND s.attivo LIMIT 1) AS stato_ddt_consegnato_id,
  (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno='DDT_VENDITA' AND s.attivo LIMIT 1)     AS sorgente_ddt_id,
  (SELECT s.id FROM config.stati_doc_reso s WHERE s.codice_interno='DRAFT' AND s.attivo LIMIT 1)     AS stato_reso_draft_id,
  (SELECT s.id FROM config.stati_doc_reso s WHERE s.codice_interno='ANNULLATO' AND s.attivo LIMIT 1) AS stato_reso_ann_id,
  (SELECT t.id FROM config.tipi_reso t WHERE t.codice_interno='RESO_PER_RICONSEGNA' AND t.attivo LIMIT 1) AS tipo_riconsegna_id,
  (SELECT t.id FROM config.tipi_reso t WHERE t.codice_interno='RESO_A_CREDITO' AND t.attivo LIMIT 1)      AS tipo_credito_id;

SELECT ok(
  (SELECT billing_account_id IS NOT NULL AND articolo_id IS NOT NULL
      AND sorgente_ddt_id IS NOT NULL AND stato_reso_draft_id IS NOT NULL
      AND tipo_riconsegna_id IS NOT NULL AND tipo_credito_id IS NOT NULL
      AND stato_ddt_consegnato_id IS NOT NULL FROM tmp_refs),
  '2) riferimenti minimi disponibili');

-- ============================================================
-- FIXTURE A: ordine (qta 10) -> DDT -> CONSEGNATO (builder)
-- ============================================================
-- La bolla dal builder: ordine di 10 a 25, trigger SPEDITO, del cliente del
-- mondo, confermato; bolla generata e CONSEGNATA.
CREATE TEMP TABLE tmp_bolla_a AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('resi motore A', 
           p_billing_account_id   => (SELECT billing_account_id FROM tmp_refs),
           p_quantita             => 10,
           p_prezzo               => 25,
           p_articolo_id          => (SELECT articolo_id FROM tmp_refs),
           p_fatturazione_trigger => 'SPEDITO');

-- L'ordine come l'ha scritto il dominio (emittente e billing dopo il
-- normalize): i test 3 e 4 li confrontano col reso.
CREATE TEMP TABLE tmp_ord_a AS
SELECT o.id, o.uid, o.billing_account_id, o.emittente_fiscale_id
  FROM vendite.ordini o WHERE o.id = (SELECT ordine_id FROM tmp_bolla_a);
CREATE TEMP TABLE tmp_ord_a_riga AS SELECT ordine_riga_id AS id FROM tmp_bolla_a;
CREATE TEMP TABLE tmp_ddt_a AS SELECT ddt_id FROM tmp_bolla_a;

CREATE TEMP TABLE tmp_ddt_a_riga AS
SELECT dr.id, dr.articolo_id, dr.descrizione, dr.uom_operativa_id, dr.factor_to_base
  FROM vendite.ddt_righe dr WHERE dr.id=(SELECT ddt_riga_id FROM tmp_bolla_a);

-- Crea reso DRAFT dal DDT (sorgente DDT_VENDITA, uid del DDT).
CREATE TEMP TABLE tmp_reso_a AS
WITH ins AS (
  INSERT INTO vendite.resi (stato_doc_reso_id, sorgente_tipo_id, sorgente_uid, storicizza, meta)
  SELECT r.stato_reso_draft_id, r.sorgente_ddt_id,
         (SELECT d.uid FROM vendite.ddt d WHERE d.id=(SELECT ddt_id FROM tmp_ddt_a)),
         false, jsonb_build_object('test_scope','pgtap_resi')
  FROM tmp_refs r RETURNING id, emittente_fiscale_id, billing_account_id)
SELECT * FROM ins;

-- 3) emittente ereditato dal DDT
SELECT is(
  (SELECT emittente_fiscale_id FROM tmp_reso_a),
  (SELECT emittente_fiscale_id FROM tmp_ord_a),
  '3) reso: emittente ereditato dal DDT (normalize)');

-- 4) billing ereditato dal DDT
SELECT is(
  (SELECT billing_account_id FROM tmp_reso_a),
  (SELECT billing_account_id FROM tmp_ord_a),
  '4) reso: billing ereditato dal DDT');

-- 5) numero NULL in DRAFT
SELECT ok((SELECT numero IS NULL FROM vendite.resi WHERE id=(SELECT id FROM tmp_reso_a)),
  '5) numero NULL in DRAFT');

-- Riga reso: ri-consegna, qta 3
CREATE TEMP TABLE tmp_reso_a_riga AS
WITH ins AS (
  INSERT INTO vendite.resi_righe (reso_id, riga_nr, ddt_riga_id, ordine_riga_id,
    articolo_id, descrizione, qta_operativa, uom_operativa_id, factor_to_base,
    tipo_reso_id, storicizza)
  SELECT (SELECT id FROM tmp_reso_a), 1, dr.id, (SELECT id FROM tmp_ord_a_riga),
         dr.articolo_id, dr.descrizione, 3, dr.uom_operativa_id, dr.factor_to_base,
         (SELECT tipo_riconsegna_id FROM tmp_refs), false
  FROM tmp_ddt_a_riga dr RETURNING id, quantita)
SELECT * FROM ins;

-- 6) quantita derivata da qta_operativa
SELECT is((SELECT quantita FROM tmp_reso_a_riga), 3.000000::numeric,
  '6) resi_righe: quantita derivata da qta_operativa (3)');

-- 7) over-return: aggiungere 8 (3+8>10) -> throws
SELECT throws_ok(
  format($q$INSERT INTO vendite.resi_righe (reso_id, riga_nr, ddt_riga_id, ordine_riga_id,
             articolo_id, descrizione, qta_operativa, factor_to_base, tipo_reso_id, storicizza)
             SELECT %s, 2, %s, %s, %L, 'over', 8, 1, %s, false$q$,
         (SELECT id FROM tmp_reso_a), (SELECT id FROM tmp_ddt_a_riga),
         (SELECT id FROM tmp_ord_a_riga), (SELECT articolo_id FROM tmp_ddt_a_riga),
         (SELECT tipo_riconsegna_id FROM tmp_refs)),
  'P0001', NULL,
  '7) over-return -> E_RESO_QTA_SUPERA_CONSEGNATO');

-- 8) conferma
SELECT lives_ok(
  format($q$SELECT vendite.fn_conferma_reso(%s)$q$, (SELECT id FROM tmp_reso_a)),
  '8) fn_conferma_reso eseguita');
SELECT is(
  (SELECT sdr.codice_interno FROM vendite.resi r
     JOIN config.stati_doc_reso sdr ON sdr.id=r.stato_doc_reso_id
    WHERE r.id=(SELECT id FROM tmp_reso_a)),
  'CONFERMATO', '8b) reso -> CONFERMATO');

-- 9) numero assegnato
SELECT ok(
  (SELECT numero IS NOT NULL AND btrim(numero) <> '' FROM vendite.resi WHERE id=(SELECT id FROM tmp_reso_a)),
  '9) numero assegnato alla CONFERMA');

-- 10) numero immutabile
SELECT throws_ok(
  format($q$UPDATE vendite.resi SET numero='ZZZ' WHERE id=%s$q$, (SELECT id FROM tmp_reso_a)),
  'P0001', NULL, '10) numero immutabile dopo assegnazione');

-- 11) residuo riaperto (reso-aware)
SELECT ok(
  vendite.fn_ordine_ha_residuo_evasione((SELECT id FROM tmp_ord_a)),
  '11) residuo riaperto: fn_ordine_ha_residuo_evasione = true');

-- 12) ordine -> PARZIALMENTE_EVASO
SELECT is(
  (SELECT sdo.codice_interno FROM vendite.ordini o
     JOIN config.stati_doc_ordini sdo ON sdo.id=o.stato_doc_ordine_id
    WHERE o.id=(SELECT id FROM tmp_ord_a)),
  'PARZIALMENTE_EVASO', '12) proiezione stato ordine -> PARZIALMENTE_EVASO');

-- 13) coda da_riconsegnare
SELECT ok(
  (SELECT qta_residua = 3 AND stato_riconsegna = 'DA_RICONSEGNARE'
     FROM vendite.vw_resi_da_riconsegnare WHERE resi_riga_id=(SELECT id FROM tmp_reso_a_riga)),
  '13) coda da_riconsegnare: qta_residua=3, DA_RICONSEGNARE');

-- 14) ri-spedizione parziale (qta 2)
CREATE TEMP TABLE tmp_ddt_ric1 AS
SELECT vendite.fn_genera_ddt_riconsegna(
         (SELECT id FROM tmp_reso_a),
         jsonb_build_array(jsonb_build_object('resi_riga_id',(SELECT id FROM tmp_reso_a_riga),'qta',2))
       ) AS ddt_id;
SELECT ok((SELECT ddt_id IS NOT NULL FROM tmp_ddt_ric1), '14) ri-spedizione parziale -> nuovo ddt');

-- 15) copertura 2 + PARZIALE
SELECT ok(
  (SELECT COALESCE(SUM(qta),0) = 2 FROM vendite.resi_righe_riconsegne WHERE resi_riga_id=(SELECT id FROM tmp_reso_a_riga))
  AND (SELECT stato_riconsegna='PARZIALE' FROM vendite.vw_resi_da_riconsegnare WHERE resi_riga_id=(SELECT id FROM tmp_reso_a_riga)),
  '15) ponte copertura=2, stato_riconsegna=PARZIALE');

-- 16) ri-spedizione del resto (NULL -> tutta la copertura residua = 1)
CREATE TEMP TABLE tmp_ddt_ric2 AS
SELECT vendite.fn_genera_ddt_riconsegna((SELECT id FROM tmp_reso_a)) AS ddt_id;
SELECT is(
  (SELECT COALESCE(SUM(qta),0) FROM vendite.resi_righe_riconsegne WHERE resi_riga_id=(SELECT id FROM tmp_reso_a_riga)),
  3.000000::numeric, '16) ri-spedizione resto -> copertura=3');

-- 17) COMPLETATA + fuori dalla coda
SELECT ok(
  NOT EXISTS (SELECT 1 FROM vendite.vw_resi_da_riconsegnare WHERE resi_riga_id=(SELECT id FROM tmp_reso_a_riga)),
  '17) copertura completa -> sparita dalla coda da_riconsegnare');

-- 18) ordine torna EVASO
SELECT is(
  (SELECT sdo.codice_interno FROM vendite.ordini o
     JOIN config.stati_doc_ordini sdo ON sdo.id=o.stato_doc_ordine_id
    WHERE o.id=(SELECT id FROM tmp_ord_a)),
  'EVASO', '18) ordine torna EVASO (residuo chiuso)');

-- 19) annullo bloccato se gia' ri-spedito
SELECT throws_ok(
  format($q$SELECT vendite.fn_annulla_reso(%s)$q$, (SELECT id FROM tmp_reso_a)),
  'P0001', NULL, '19) annullo bloccato con riconsegne -> E_RESO_ANNULLO_CON_RICONSEGNE');

-- ============================================================
-- FIXTURE B: reso a credito TOTALE -> flip DDT + coda accrediti
-- ============================================================
-- La bolla dal builder: 5 a 25, trigger SPEDITO, CONSEGNATA.
CREATE TEMP TABLE tmp_ddt_b AS
SELECT b.ddt_id FROM dbops.fn_pgtap_crea_ddt_da_ordine('resi motore B', 
           p_billing_account_id   => (SELECT billing_account_id FROM tmp_refs),
           p_quantita             => 5,
           p_prezzo               => 25,
           p_articolo_id          => (SELECT articolo_id FROM tmp_refs),
           p_fatturazione_trigger => 'SPEDITO') b;

CREATE TEMP TABLE tmp_reso_b AS
WITH ins AS (
  INSERT INTO vendite.resi (stato_doc_reso_id, sorgente_tipo_id, sorgente_uid, storicizza, meta)
  SELECT r.stato_reso_draft_id, r.sorgente_ddt_id,
         (SELECT d.uid FROM vendite.ddt d WHERE d.id=(SELECT ddt_id FROM tmp_ddt_b)),
         false, jsonb_build_object('test_scope','pgtap_resi')
  FROM tmp_refs r RETURNING id)
SELECT * FROM ins;
-- Riga credito, qta piena (5) -> reso totale
CREATE TEMP TABLE tmp_reso_b_riga AS
WITH ins AS (
  INSERT INTO vendite.resi_righe (reso_id, riga_nr, ddt_riga_id, ordine_riga_id,
    articolo_id, descrizione, qta_operativa, uom_operativa_id, factor_to_base, tipo_reso_id, storicizza)
  SELECT (SELECT id FROM tmp_reso_b), 1, dr.id,
         (SELECT f.ordine_riga_id FROM vendite.ordini_righe_fulfillment f WHERE f.ddt_riga_id=dr.id LIMIT 1),
         dr.articolo_id, dr.descrizione, 5, dr.uom_operativa_id, dr.factor_to_base,
         (SELECT tipo_credito_id FROM tmp_refs), false
  FROM vendite.ddt_righe dr WHERE dr.ddt_id=(SELECT ddt_id FROM tmp_ddt_b) LIMIT 1
  RETURNING id)
SELECT * FROM ins;
SELECT vendite.fn_conferma_reso((SELECT id FROM tmp_reso_b));

-- 20) flip DDT -> RESO
SELECT is(
  (SELECT sdd.codice_interno FROM vendite.ddt d
     JOIN config.stati_doc_ddt sdd ON sdd.id=d.stato_doc_ddt_id
    WHERE d.id=(SELECT ddt_id FROM tmp_ddt_b)),
  'RESO', '20) reso a credito totale -> DDT CONSEGNATO->RESO (flip automatico)');

-- 21) RIMOSSA (2026-07-18, step 4): verificava "riga a credito confermata =>
--     presente in coda", cioe' la popolazione PER TIPO DI RESO. Dal changeset
--     20260718-01 vw_resi_da_accreditare si popola dal CONTO (differenza
--     negativa del contatore): la fixture B rende 5 su 5 senza aver mai
--     fatturato nulla, quindi non c'e' niente da accreditare e la vista
--     giustamente la esclude. La coda ha ora il suo test dedicato,
--     test-vw-resi-da-accreditare-contatore-v1 (plan(8)), che copre anche
--     questo caso (P1). Qui resta il motore dei resi, che e' l'oggetto del file.

-- 22) available_actions su reso CONFERMATO espone 'annulla'
SELECT ok(
  (SELECT (script.fn_available_actions_reso((SELECT id FROM tmp_reso_b))->'available_actions')
          @> '[{"key":"annulla"}]'::jsonb),
  '22) fn_available_actions_reso: reso CONFERMATO espone azione annulla');

-- ============================================================
-- 23) annullo reso a credito (non ri-spedito) -> ANNULLATO
-- ============================================================
SELECT lives_ok(
  format($q$SELECT vendite.fn_annulla_reso(%s)$q$, (SELECT id FROM tmp_reso_b)),
  '23a) fn_annulla_reso credito eseguita');
SELECT is(
  (SELECT sdr.codice_interno FROM vendite.resi r
     JOIN config.stati_doc_reso sdr ON sdr.id=r.stato_doc_reso_id
    WHERE r.id=(SELECT id FROM tmp_reso_b)),
  'ANNULLATO', '23) annullo reso a credito -> ANNULLATO');

-- ============================================================
-- 24) guard: reso da DDT NON CONSEGNATO -> throws
-- ============================================================
-- La bolla dal builder, lasciata in DRAFT (non consegnata): e' il caso del test.
CREATE TEMP TABLE tmp_ddt_c AS
SELECT b.ddt_id FROM dbops.fn_pgtap_crea_ddt_da_ordine('resi motore C', 'DRAFT', 
           p_billing_account_id   => (SELECT billing_account_id FROM tmp_refs),
           p_quantita             => 5,
           p_prezzo               => 25,
           p_articolo_id          => (SELECT articolo_id FROM tmp_refs),
           p_fatturazione_trigger => 'SPEDITO') b;

SELECT throws_ok(
  format($q$INSERT INTO vendite.resi (stato_doc_reso_id, sorgente_tipo_id, sorgente_uid, storicizza, meta)
             SELECT %s, %s, (SELECT uid FROM vendite.ddt WHERE id=%s), false, '{}'::jsonb$q$,
         (SELECT stato_reso_draft_id FROM tmp_refs), (SELECT sorgente_ddt_id FROM tmp_refs),
         (SELECT ddt_id FROM tmp_ddt_c)),
  'P0001', NULL, '24) reso da DDT non CONSEGNATO -> E_RESO_DDT_NON_CONSEGNATO');

-- ============================================================
-- FIXTURE D: il caso-bozza del flip (step 2b — il test che dimostra il fix)
--   DDT da 10 pz CONSEGNATO, due resi a credito sulla stessa riga:
--     - reso D1: 6 pz, lasciato in BOZZA (il reso "di un altro operatore")
--     - reso D2: 4 pz, CONFERMATO
--   Somma dei NON-ANNULLATI = 10 = qta del DDT -> col vecchio calcolo
--   (`<> 'ANNULLATO'`) il DDT veniva dichiarato RESO, ma il cliente tiene 6 pz
--   e quei 6 pz non si sarebbero fatturati mai (DDT in RESO = non piu'
--   eleggibile al push), senza nessuna segnalazione.
--   Nota: il guard over-return conta anch'esso i non-annullati, quindi il reso
--   D2 da 4 passa per un pelo (residuo 10-6=4, il guard blocca solo se >).
-- ============================================================
-- La bolla dal builder: 10 a 25, trigger SPEDITO, CONSEGNATA.
CREATE TEMP TABLE tmp_bolla_d AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('resi motore D', 
           p_billing_account_id   => (SELECT billing_account_id FROM tmp_refs),
           p_quantita             => 10,
           p_prezzo               => 25,
           p_articolo_id          => (SELECT articolo_id FROM tmp_refs),
           p_fatturazione_trigger => 'SPEDITO');
CREATE TEMP TABLE tmp_ddt_d AS SELECT ddt_id FROM tmp_bolla_d;

CREATE TEMP TABLE tmp_ddt_d_riga AS
SELECT dr.id, dr.articolo_id, dr.descrizione, dr.uom_operativa_id, dr.factor_to_base
  FROM vendite.ddt_righe dr WHERE dr.id=(SELECT ddt_riga_id FROM tmp_bolla_d);

-- Reso D1: 6 pz, resta in BOZZA (mai confermato).
CREATE TEMP TABLE tmp_reso_d1 AS
WITH ins AS (
  INSERT INTO vendite.resi (stato_doc_reso_id, sorgente_tipo_id, sorgente_uid, storicizza, meta)
  SELECT r.stato_reso_draft_id, r.sorgente_ddt_id,
         (SELECT d.uid FROM vendite.ddt d WHERE d.id=(SELECT ddt_id FROM tmp_ddt_d)),
         false, jsonb_build_object('test_scope','pgtap_resi')
  FROM tmp_refs r RETURNING id)
SELECT * FROM ins;
INSERT INTO vendite.resi_righe (reso_id, riga_nr, ddt_riga_id, ordine_riga_id,
  articolo_id, descrizione, qta_operativa, uom_operativa_id, factor_to_base, tipo_reso_id, storicizza)
SELECT (SELECT id FROM tmp_reso_d1), 1, dr.id,
       (SELECT f.ordine_riga_id FROM vendite.ordini_righe_fulfillment f WHERE f.ddt_riga_id=dr.id LIMIT 1),
       dr.articolo_id, dr.descrizione, 6, dr.uom_operativa_id, dr.factor_to_base,
       (SELECT tipo_credito_id FROM tmp_refs), false
FROM tmp_ddt_d_riga dr;

-- Reso D2: 4 pz, confermato.
CREATE TEMP TABLE tmp_reso_d2 AS
WITH ins AS (
  INSERT INTO vendite.resi (stato_doc_reso_id, sorgente_tipo_id, sorgente_uid, storicizza, meta)
  SELECT r.stato_reso_draft_id, r.sorgente_ddt_id,
         (SELECT d.uid FROM vendite.ddt d WHERE d.id=(SELECT ddt_id FROM tmp_ddt_d)),
         false, jsonb_build_object('test_scope','pgtap_resi')
  FROM tmp_refs r RETURNING id)
SELECT * FROM ins;
INSERT INTO vendite.resi_righe (reso_id, riga_nr, ddt_riga_id, ordine_riga_id,
  articolo_id, descrizione, qta_operativa, uom_operativa_id, factor_to_base, tipo_reso_id, storicizza)
SELECT (SELECT id FROM tmp_reso_d2), 1, dr.id,
       (SELECT f.ordine_riga_id FROM vendite.ordini_righe_fulfillment f WHERE f.ddt_riga_id=dr.id LIMIT 1),
       dr.articolo_id, dr.descrizione, 4, dr.uom_operativa_id, dr.factor_to_base,
       (SELECT tipo_credito_id FROM tmp_refs), false
FROM tmp_ddt_d_riga dr;

SELECT vendite.fn_conferma_reso((SELECT id FROM tmp_reso_d2));

-- 25) IL FIX: la bozza da 6 non conta -> confermati 4 < 10 -> niente flip.
--     Col vecchio `<> 'ANNULLATO'` qui il DDT sarebbe gia' RESO (6+4=10).
SELECT is(
  (SELECT sdd.codice_interno FROM vendite.ddt d
     JOIN config.stati_doc_ddt sdd ON sdd.id=d.stato_doc_ddt_id
    WHERE d.id=(SELECT ddt_id FROM tmp_ddt_d)),
  'CONSEGNATO',
  '25) bozza 6 + confermato 4 su DDT da 10 -> DDT resta CONSEGNATO (le bozze non contano)');

-- 26) Confermata anche la bozza: 6+4=10 CONFERMATI -> il flip scatta.
--     Prova che il fix non ha rotto il flip: e' lo stato a decidere.
SELECT vendite.fn_conferma_reso((SELECT id FROM tmp_reso_d1));
SELECT is(
  (SELECT sdd.codice_interno FROM vendite.ddt d
     JOIN config.stati_doc_ddt sdd ON sdd.id=d.stato_doc_ddt_id
    WHERE d.id=(SELECT ddt_id FROM tmp_ddt_d)),
  'RESO',
  '26) confermata anche la bozza (6+4=10 confermati) -> DDT CONSEGNATO->RESO');

SELECT * FROM finish();
ROLLBACK;
