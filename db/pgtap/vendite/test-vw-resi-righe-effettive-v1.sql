-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- rev 2026-10-25 (brief-db-pgtap-bolla-e-reso-costruiti, giro 1): la bolla da ordine dal builder dbops.fn_pgtap_crea_ddt_da_ordine; restano scritti a mano i resi A, B, C (il caso del test, e giro 2).
-- pgTAP test per Zero ERP
-- Test: vendite.vw_resi_righe_effettive — helper unico «merce tornata indietro»
--       (brief-db-fatturazione-ddt-resi §3b, step 2). Fonte unica CONFERMATI +
--       attivi + tutti i tipi, con le due chiavi di partita + riapre_residuo.
-- (changeset 20260717-07)
-- ------------------------------------------------------------
-- Indice test (1..9):
--   1) la vista esiste
--   2) e' security_invoker=on (RLS su resi preservata — regressione V-1)
--   3) espone le colonne del contratto (chiavi + riapre_residuo + quantita)
--   4) riga di reso CONFERMATO + attiva -> PRESENTE, quantita base corretta
--   5) espone ddt_riga_id corretto (chiave partita standalone)
--   6) espone ordine_riga_id corretto (chiave partita order-backed)
--   7) espone riapre_residuo decodificato dal tipo (credito -> false)
--   8) filtro STATO: riga di reso DRAFT -> ASSENTE
--   9) filtro ATTIVO (il nuovo canonico dello step 2): riga di reso CONFERMATO
--      ma disattivata -> ASSENTE (dal 2026-09-29 la riga si spegne in bozza:
--      fuori bozza le righe del reso sono congelate, D-3b-h)
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
CREATE TEMP TABLE _m AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('pgTAP resi righe effettive');
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _m)); END $ctx$;

SELECT plan(9);

-- Dal 2026-09-28 conferma e annullo del reso sono verbi SECURITY DEFINER col
-- perimetro nella WHERE e il permesso conferma_reso (Lotto 3-bis, D-3b-f):
-- il perimetro e' quello dell'operatore del mondo, aperto qui sopra.

-- Dal 2026-09-28 conferma e annullo del reso sono verbi che applicano
-- l'azione conferma_reso (brief-db-magazzino-lotto-3-bis-carico-da-reso, D-3b-f):
-- l'operatore di fixture non ha azioni, si concede qui.
DO $az$ BEGIN
    PERFORM dbops.fn_pgtap_concedi_azione(
        NULLIF(current_setting('app.current_user_id', true), '')::integer, 'conferma_reso');
END $az$;

-- ============================================================
-- 1) La vista esiste
-- ============================================================
SELECT has_view('vendite', 'vw_resi_righe_effettive', '1) la vista esiste');

-- ============================================================
-- 2) security_invoker=on (la reloption non e' visibile in pg_get_viewdef:
--    va ri-specificata a ogni CREATE OR REPLACE, altrimenti PG la azzera).
-- ============================================================
SELECT ok(
  (SELECT 'security_invoker=on' = ANY(c.reloptions)
     FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'vendite' AND c.relname = 'vw_resi_righe_effettive'),
  '2) vw_resi_righe_effettive e'' security_invoker=on');

-- ============================================================
-- 3) Colonne del contratto
-- ============================================================
SELECT columns_are('vendite', 'vw_resi_righe_effettive',
  ARRAY['resi_riga_id','reso_id','ddt_riga_id','ordine_riga_id',
        'tipo_reso_id','riapre_residuo','quantita'],
  '3) espone chiavi + riapre_residuo + quantita');

-- ============================================================
-- Riferimenti minimi: il mondo costruito + il catalogo di seed
-- ============================================================
CREATE TEMP TABLE tmp_refs AS
SELECT
  -- ⛔ rev 2026-10-13: cliente ed emittente dal mondo costruito, non il primo BA
  --   del database; l'articolo si costruisce (nasce merce, non solo componente:
  --   ordine e bolla lo ammettono — brief-db-articoli-ammessi-per-documento, Lotto 3a).
  (SELECT billing_account_id FROM _m)                                    AS billing_account_id,
  dbops.fn_pgtap_crea_articolo('PGTAP-RESI-EFFETTIVE', false)           AS articolo_id,
  (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno='DDT_VENDITA' AND s.attivo LIMIT 1)     AS sorgente_ddt_id,
  (SELECT s.id FROM config.stati_doc_reso s WHERE s.codice_interno='DRAFT' AND s.attivo LIMIT 1)     AS stato_reso_draft_id,
  (SELECT t.id FROM config.tipi_reso t WHERE t.codice_interno='RESO_A_CREDITO' AND t.attivo LIMIT 1) AS tipo_credito_id;

-- FIXTURE: ordine (qta 10 a 25, trigger SPEDITO) -> DDT -> CONSEGNATO, dal builder
CREATE TEMP TABLE tmp_bolla AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('resi righe effettive',
                  p_billing_account_id   => (SELECT billing_account_id FROM tmp_refs),
                  p_quantita             => 10,
                  p_prezzo               => 25,
                  p_articolo_id          => (SELECT articolo_id FROM tmp_refs),
                  p_fatturazione_trigger => 'SPEDITO');
CREATE TEMP TABLE tmp_ddt AS SELECT ddt_id FROM tmp_bolla;

CREATE TEMP TABLE tmp_ddt_riga AS
SELECT dr.id, dr.articolo_id, dr.descrizione, dr.uom_operativa_id, dr.factor_to_base
  FROM vendite.ddt_righe dr WHERE dr.id=(SELECT ddt_riga_id FROM tmp_bolla);

-- Reso A: CONFERMATO, riga a credito qta 3 -> deve essere IN vista.
CREATE TEMP TABLE tmp_reso_a AS
WITH ins AS (
  INSERT INTO vendite.resi (stato_doc_reso_id, sorgente_tipo_id, sorgente_uid, storicizza, meta)
  SELECT r.stato_reso_draft_id, r.sorgente_ddt_id,
         (SELECT d.uid FROM vendite.ddt d WHERE d.id=(SELECT ddt_id FROM tmp_ddt)),
         false, jsonb_build_object('test_scope','pgtap_vw_effettive')
  FROM tmp_refs r RETURNING id)
SELECT * FROM ins;
CREATE TEMP TABLE tmp_reso_a_riga AS
WITH ins AS (
  INSERT INTO vendite.resi_righe (reso_id, riga_nr, ddt_riga_id, ordine_riga_id,
    articolo_id, descrizione, qta_operativa, uom_operativa_id, factor_to_base, tipo_reso_id, storicizza)
  SELECT (SELECT id FROM tmp_reso_a), 1, dr.id,
         (SELECT f.ordine_riga_id FROM vendite.ordini_righe_fulfillment f WHERE f.ddt_riga_id=dr.id LIMIT 1),
         dr.articolo_id, dr.descrizione, 3, dr.uom_operativa_id, dr.factor_to_base,
         (SELECT tipo_credito_id FROM tmp_refs), false
  FROM tmp_ddt_riga dr RETURNING id, ddt_riga_id, ordine_riga_id)
SELECT * FROM ins;
SELECT vendite.fn_conferma_reso((SELECT id FROM tmp_reso_a));

-- ============================================================
-- 4) Riga CONFERMATA + attiva presente, quantita base = 3
-- ============================================================
SELECT is(
  (SELECT e.quantita FROM vendite.vw_resi_righe_effettive e
    WHERE e.resi_riga_id=(SELECT id FROM tmp_reso_a_riga)),
  3::numeric,
  '4) riga reso CONFERMATO+attiva presente, quantita base = 3');

-- 5) ddt_riga_id corretto
SELECT is(
  (SELECT e.ddt_riga_id FROM vendite.vw_resi_righe_effettive e
    WHERE e.resi_riga_id=(SELECT id FROM tmp_reso_a_riga)),
  (SELECT ddt_riga_id FROM tmp_reso_a_riga),
  '5) espone ddt_riga_id corretto');

-- 6) ordine_riga_id corretto (order-backed)
SELECT is(
  (SELECT e.ordine_riga_id FROM vendite.vw_resi_righe_effettive e
    WHERE e.resi_riga_id=(SELECT id FROM tmp_reso_a_riga)),
  (SELECT ordine_riga_id FROM tmp_reso_a_riga),
  '6) espone ordine_riga_id corretto');

-- 7) riapre_residuo decodificato dal tipo: credito -> false
SELECT is(
  (SELECT e.riapre_residuo FROM vendite.vw_resi_righe_effettive e
    WHERE e.resi_riga_id=(SELECT id FROM tmp_reso_a_riga)),
  false,
  '7) riapre_residuo decodificato dal tipo (credito -> false)');

-- ============================================================
-- 8) Filtro STATO: reso DRAFT -> ASSENTE
-- ============================================================
CREATE TEMP TABLE tmp_reso_b AS
WITH ins AS (
  INSERT INTO vendite.resi (stato_doc_reso_id, sorgente_tipo_id, sorgente_uid, storicizza, meta)
  SELECT r.stato_reso_draft_id, r.sorgente_ddt_id,
         (SELECT d.uid FROM vendite.ddt d WHERE d.id=(SELECT ddt_id FROM tmp_ddt)),
         false, jsonb_build_object('test_scope','pgtap_vw_effettive')
  FROM tmp_refs r RETURNING id)
SELECT * FROM ins;
CREATE TEMP TABLE tmp_reso_b_riga AS
WITH ins AS (
  INSERT INTO vendite.resi_righe (reso_id, riga_nr, ddt_riga_id, ordine_riga_id,
    articolo_id, descrizione, qta_operativa, uom_operativa_id, factor_to_base, tipo_reso_id, storicizza)
  SELECT (SELECT id FROM tmp_reso_b), 1, dr.id,
         (SELECT f.ordine_riga_id FROM vendite.ordini_righe_fulfillment f WHERE f.ddt_riga_id=dr.id LIMIT 1),
         dr.articolo_id, dr.descrizione, 2, dr.uom_operativa_id, dr.factor_to_base,
         (SELECT tipo_credito_id FROM tmp_refs), false
  FROM tmp_ddt_riga dr RETURNING id)
SELECT * FROM ins;

SELECT ok(
  NOT EXISTS (SELECT 1 FROM vendite.vw_resi_righe_effettive e
               WHERE e.resi_riga_id=(SELECT id FROM tmp_reso_b_riga)),
  '8) filtro stato: riga di reso DRAFT assente dalla vista');

-- ============================================================
-- 9) Filtro ATTIVO (nuovo canonico step 2): reso CONFERMATO ma riga disattivata
--    -> ASSENTE. Reso C: due righe da 1 pz; la seconda si spegne IN BOZZA, poi
--    il reso si conferma (la prima resta attiva: un reso senza righe attive
--    non si conferma).
--    ⚠️ Rev 2026-09-29 (brief-db-magazzino-lotto-3-bis-carico-da-reso, D-3b-h):
--    prima la riga si spegneva DOPO la conferma, con un UPDATE diretto. Ora le
--    righe di un reso confermato sono congelate (BB
--    trgfn_doc_righe_lock_fuori_bozza), e quel caso non esiste piu'; il filtro
--    si prova con la sola forma che il modello ammette.
--    Totale non-annullati sulla riga DDT = 3(A)+2(B bozza)+1+1(C) = 7 < 10 -> il
--    guard over-return non blocca l'inserimento di C.
-- ============================================================
CREATE TEMP TABLE tmp_reso_c AS
WITH ins AS (
  INSERT INTO vendite.resi (stato_doc_reso_id, sorgente_tipo_id, sorgente_uid, storicizza, meta)
  SELECT r.stato_reso_draft_id, r.sorgente_ddt_id,
         (SELECT d.uid FROM vendite.ddt d WHERE d.id=(SELECT ddt_id FROM tmp_ddt)),
         false, jsonb_build_object('test_scope','pgtap_vw_effettive')
  FROM tmp_refs r RETURNING id)
SELECT * FROM ins;
CREATE TEMP TABLE tmp_reso_c_riga AS
WITH ins AS (
  INSERT INTO vendite.resi_righe (reso_id, riga_nr, ddt_riga_id, ordine_riga_id,
    articolo_id, descrizione, qta_operativa, uom_operativa_id, factor_to_base, tipo_reso_id, storicizza)
  SELECT (SELECT id FROM tmp_reso_c), 1, dr.id,
         (SELECT f.ordine_riga_id FROM vendite.ordini_righe_fulfillment f WHERE f.ddt_riga_id=dr.id LIMIT 1),
         dr.articolo_id, dr.descrizione, 1, dr.uom_operativa_id, dr.factor_to_base,
         (SELECT tipo_credito_id FROM tmp_refs), false
  FROM tmp_ddt_riga dr RETURNING id)
SELECT * FROM ins;
-- La riga che resta attiva (riga 2), poi la riga 1 spenta in bozza.
INSERT INTO vendite.resi_righe (reso_id, riga_nr, ddt_riga_id, ordine_riga_id,
  articolo_id, descrizione, qta_operativa, uom_operativa_id, factor_to_base, tipo_reso_id, storicizza)
SELECT (SELECT id FROM tmp_reso_c), 2, dr.id,
       (SELECT f.ordine_riga_id FROM vendite.ordini_righe_fulfillment f WHERE f.ddt_riga_id=dr.id LIMIT 1),
       dr.articolo_id, dr.descrizione, 1, dr.uom_operativa_id, dr.factor_to_base,
       (SELECT tipo_credito_id FROM tmp_refs), false
FROM tmp_ddt_riga dr;
UPDATE vendite.resi_righe SET attivo = false WHERE id=(SELECT id FROM tmp_reso_c_riga);
SELECT vendite.fn_conferma_reso((SELECT id FROM tmp_reso_c));

SELECT ok(
  NOT EXISTS (SELECT 1 FROM vendite.vw_resi_righe_effettive e
               WHERE e.resi_riga_id=(SELECT id FROM tmp_reso_c_riga)),
  '9) filtro attivo: riga di reso CONFERMATO ma disattivata assente dalla vista');

SELECT * FROM finish();
ROLLBACK;
