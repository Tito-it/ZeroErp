-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- rev 2026-10-25 (brief-db-pgtap-bolla-e-reso-costruiti, giro 1): la bolla da ordine dal builder dbops.fn_pgtap_crea_ddt_da_ordine, col trigger e lo stato finale del caso (ritirata pg_temp.mk_caso); resta a mano l'annullo di C col verbo vendite.fn_annulla_ddt, che e' la strada del caso.
-- ⚠️ rev 2026-10-19 (brief-db-grammatica-unica-documenti, lotto 2a, 20261019-40 … -79):
--   il documento passato ai lettori delle testate, ai legami e ai montaggi del
--   lock e' il codice della sorgente (DDT_VENDITA, ORDINE_VENDITA,
--   OFFERTA_COMMERCIALE, RESO_VENDITA). Restano corti i prefissi delle chiavi
--   (G-8), l'origine dei legami (V7) e l'ambito degli indirizzi (G-6).
-- Test: fn_list_ddt_da_pushare — eleggibilita' DALLO stato-trigger IN POI,
--       senza aprire il DDT annullato — step 5,
--       brief-db-fatturazione-ddt-resi §3e/§9-5.
-- (changeset 20260718-02)
-- ------------------------------------------------------------
-- Indice test (1..5):
--   1) ORFANO (il fix): ordine trigger SPEDITO, DDT gia' CONSEGNATO (ha
--      superato lo stato-trigger senza essere pushato) -> ORA eleggibile.
--      Prima dell'uguaglianza secca non fatturava mai.
--   2) A-STATO: ordine trigger SPEDITO, DDT SPEDITO -> eleggibile (non
--      regredito dal passaggio al confronto di rank)
--   3) ANNULLATO (§3e.2, il rischio del rank puro): 70 >= 40 lo renderebbe
--      eleggibile -> NOT is_abortito lo esclude. Un DDT annullato non ha resi,
--      i tenuti non si azzerano: senza questo VERREBBE FATTURATO
--   4) RESO: escluso esplicitamente (merce tornata tutta indietro)
--   5) CINTURA XOR (§3e.1): ordine trigger CONFERMATO -> il suo DDT NON e'
--      eleggibile nemmeno ora. E' l'ordine a fatturare: senza questa clausola
--      doppia fatturazione su TUTTI gli ordini in configurazione di default
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
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('pgTAP DDT orfano');
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _m)); END $ctx$;

-- L'annullo di una bolla emessa passa dal verbo di stato, che chiede l'azione
-- emetti_ddt (rev 2026-10-11, D-8 di brief-db-ddt-righe-evase-dall-ordine).
DO $az_ann$ BEGIN
  PERFORM dbops.fn_pgtap_concedi_azione(
      NULLIF(current_setting('app.current_user_id', true), '')::integer, 'emetti_ddt');
END $az_ann$;

SELECT plan(5);

-- ============================================================
-- Riferimenti
-- ============================================================
CREATE TEMP TABLE tmp_refs AS
SELECT
  -- ⛔ rev 2026-10-13: cliente dal mondo costruito, non il primo BA del
  --   database; l'articolo si costruisce (nasce merce, non solo componente:
  --   ordine e bolla lo ammettono — brief-db-articoli-ammessi-per-documento, Lotto 3a).
  (SELECT billing_account_id FROM _m)                                    AS billing_account_id,
  dbops.fn_pgtap_crea_articolo('PGTAP-DDT-ORFANO', false)                AS articolo_id;

-- ============================================================
-- FIXTURE: ordine 10 @25 col trigger del caso, bolla dal builder nello stato
--   finale del caso, per la matrice (config.transizioni_stati_ddt: RESO si
--   raggiunge solo da CONSEGNATO, ANNULLATO solo da DRAFT/EMESSO).
-- ============================================================
-- A: trigger SPEDITO, DDT CONSEGNATO -> l'ORFANO che il fix recupera
CREATE TEMP TABLE tmp_a AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('orfano A', 'CONSEGNATO',
    (SELECT billing_account_id FROM tmp_refs), p_quantita => 10, p_prezzo => 25,
    p_articolo_id => (SELECT articolo_id FROM tmp_refs), p_fatturazione_trigger => 'SPEDITO');
-- B: trigger SPEDITO, DDT SPEDITO -> il caso "a stato", non deve regredire
CREATE TEMP TABLE tmp_b AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('orfano B', 'SPEDITO',
    (SELECT billing_account_id FROM tmp_refs), p_quantita => 10, p_prezzo => 25,
    p_articolo_id => (SELECT articolo_id FROM tmp_refs), p_fatturazione_trigger => 'SPEDITO');
-- C: trigger SPEDITO, DDT ANNULLATO -> rank 70 >= 40, ma documento morto.
--    NB: annullato da EMESSO (unica transizione viva) -> non e' mai stato
--    spedito, ma il rank resta 70 e il predicato lo pescherebbe comunque.
CREATE TEMP TABLE tmp_c AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('orfano C', 'EMESSO',
    (SELECT billing_account_id FROM tmp_refs), p_quantita => 10, p_prezzo => 25,
    p_articolo_id => (SELECT articolo_id FROM tmp_refs), p_fatturazione_trigger => 'SPEDITO');
-- ⭐ rev 2026-10-11 (brief-db-ddt-righe-evase-dall-ordine, D-8): la bolla nasce
--   dall'ordine e ne porta il legame. L'annullo diretto e' rifiutato
--   (E_DOC_ANNULLO_CON_LEGAMI): passa dal verbo, dichiarando i legami letti
--   da vendite.fn_documento_legami, come fa la finestra di conferma
--   (rev 2026-10-11, brief-db-annullo-documento-con-legami D-4).
SELECT vendite.fn_annulla_ddt(c.ddt_id,
    (SELECT count(*)::integer FROM vendite.fn_documento_legami('DDT_VENDITA', c.ddt_id) l))
  FROM tmp_c c;
-- D: trigger SPEDITO, DDT RESO -> merce tornata tutta indietro
CREATE TEMP TABLE tmp_d AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('orfano D', 'RESO',
    (SELECT billing_account_id FROM tmp_refs), p_quantita => 10, p_prezzo => 25,
    p_articolo_id => (SELECT articolo_id FROM tmp_refs), p_fatturazione_trigger => 'SPEDITO');
-- E: trigger CONFERMATO, DDT CONSEGNATO -> fattura l'ORDINE, non il DDT
CREATE TEMP TABLE tmp_e AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('orfano E', 'CONSEGNATO',
    (SELECT billing_account_id FROM tmp_refs), p_quantita => 10, p_prezzo => 25,
    p_articolo_id => (SELECT articolo_id FROM tmp_refs), p_fatturazione_trigger => 'CONFERMATO');
-- ============================================================
-- ASSERZIONI
-- ============================================================
-- 1) IL FIX: il DDT che ha superato lo stato-trigger torna eleggibile
SELECT is(
  (SELECT COUNT(*)::int FROM vendite.fn_list_ddt_da_pushare(NULL,NULL,NULL,(SELECT ddt_id FROM tmp_a))),
  1, '1) ORFANO: trigger SPEDITO + DDT CONSEGNATO -> eleggibile (prima non fatturava mai)');

-- 2) Nessuna regressione sul caso che gia' funzionava
SELECT is(
  (SELECT COUNT(*)::int FROM vendite.fn_list_ddt_da_pushare(NULL,NULL,NULL,(SELECT ddt_id FROM tmp_b))),
  1, '2) A-STATO: trigger SPEDITO + DDT SPEDITO -> ancora eleggibile (no regressione)');

-- 3) Il rischio del rank puro, chiuso da NOT is_abortito
SELECT is(
  (SELECT COUNT(*)::int FROM vendite.fn_list_ddt_da_pushare(NULL,NULL,NULL,(SELECT ddt_id FROM tmp_c))),
  0, '3) ANNULLATO: rank 70 >= 40 ma is_abortito -> NON eleggibile (senza, verrebbe fatturato)');

-- 4) RESO escluso esplicitamente
SELECT is(
  (SELECT COUNT(*)::int FROM vendite.fn_list_ddt_da_pushare(NULL,NULL,NULL,(SELECT ddt_id FROM tmp_d))),
  0, '4) RESO: merce tornata tutta indietro -> NON eleggibile');

-- 5) La cintura XOR regge: l'ordine CONFERMATO fattura per conto suo
SELECT is(
  (SELECT COUNT(*)::int FROM vendite.fn_list_ddt_da_pushare(NULL,NULL,NULL,(SELECT ddt_id FROM tmp_e))),
  0, '5) CINTURA XOR: trigger CONFERMATO -> DDT mai eleggibile (fattura l''ordine)');

SELECT * FROM finish();
ROLLBACK;
