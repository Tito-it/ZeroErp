-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- rev 2026-10-25 (brief-db-pgtap-bolla-e-reso-costruiti, giro 1): la bolla da ordine dal builder dbops.fn_pgtap_crea_ddt_da_ordine, in bozza con la causale del caso, poi a CONSEGNATO per la matrice (ritirata pg_temp.porta_a); restano a mano il prezzo tolto dalla riga e la causale tolta (test 2), le emissioni di 2-4 (sono il caso: i gate) e la bolla standalone di 3 (non nasce da un ordine).
-- Test: DDT di solo trasporto — l'intento si dichiara con la CAUSALE
--       (fatturabile) — step 5b, brief-db-fatturazione-ddt-resi §4a / DL-28.
-- (changeset 20260718-03/-04/-05/-06)
-- ------------------------------------------------------------
-- Indice test (1..6):
--   1) Seed del vocabolario: VENDITA fatturabile, le altre sette no
--   2) Gate R1: emissione senza causale -> BLOCCATA (E_DDT_CAUSALE_OBBLIGATORIA)
--   3) Gate R2: causale VENDITA + riga senza prezzo risolvibile (standalone,
--      nessun ordine da cui ereditare) -> BLOCCATA (E_DDT_PREZZO_NON_RISOLVIBILE)
--   4) Gate R2, il caso legittimo: riga da EVASIONE senza prezzo proprio ma con
--      la riga d'ordine che lo fornisce -> emissione PASSA (e' la COALESCE del
--      lister: le righe da evasione senza prezzo restano legittime)
--   5) Causale NON fatturabile (CAMPIONATURA) -> mai eleggibile al push, anche
--      a CONSEGNATO e con prezzi validi: e' la cintura del lister
--   6) Controprova: stessa identica situazione con causale VENDITA -> eleggibile
--      (senza questa, il test 5 passerebbe anche se il lister fosse rotto)
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
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('pgTAP DDT solo trasporto');
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _m)); END $ctx$;

SELECT plan(6);

-- ============================================================
-- Riferimenti + helper
-- ============================================================
CREATE TEMP TABLE tmp_refs AS
SELECT
  -- ⛔ rev 2026-10-13: cliente ed emittente dal mondo costruito, non il primo BA
  --   del database; l'articolo si costruisce (nasce merce, non solo componente:
  --   ordine e bolla lo ammettono — brief-db-articoli-ammessi-per-documento, Lotto 3a).
  (SELECT billing_account_id FROM _m)                                    AS billing_account_id,
  (SELECT cliente_soggetto_ruolo_id FROM _m)                             AS soggetto_ruolo_id,
  dbops.fn_pgtap_crea_articolo('PGTAP-DDT-SOLO-TRASP', false)            AS articolo_id,
  (SELECT u.id FROM catalogo.unita_misura u WHERE u.attivo IS TRUE ORDER BY u.id LIMIT 1) AS uom_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1)              AS valuta_id,
  (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1) AS iva_id,
  (SELECT emittente_fiscale_id FROM _m)                                 AS emittente_fiscale_id,
  (SELECT s.id FROM config.stati_doc_ddt s WHERE s.codice_interno='EMESSO' AND s.attivo LIMIT 1)     AS stato_ddt_emesso_id,
  (SELECT c.id FROM config.causali_trasporto c WHERE c.codice='VENDITA' LIMIT 1)      AS causale_vendita_id,
  (SELECT id FROM config.tipi_indirizzi WHERE codice_interno='CON')     AS tipo_ind_con_id;

-- Ordine (10 @25, trigger CONSEGNATO) -> bolla dal builder, in bozza, con la
-- causale del caso (NULL = tolta: il gate R1). La riga della bolla perde il
-- prezzo proprio: deve ereditarlo dall'ordine via fulfillment.
CREATE OR REPLACE FUNCTION pg_temp.mk_ddt_da_ordine(p_causale varchar)
RETURNS TABLE(ordine_id bigint, ddt_id bigint) AS $$
DECLARE r RECORD; v_ord bigint; v_ddt bigint;
BEGIN
  SELECT * INTO r FROM tmp_refs;
  SELECT b.ordine_id, b.ddt_id INTO v_ord, v_ddt
    FROM dbops.fn_pgtap_crea_ddt_da_ordine('causale', 'DRAFT', r.billing_account_id,
           p_quantita => 10, p_prezzo => 25, p_articolo_id => r.articolo_id,
           p_fatturazione_trigger => 'CONSEGNATO',
           p_causale_codice => COALESCE(p_causale, 'VENDITA')) b;
  IF p_causale IS NULL THEN
    UPDATE vendite.ddt d SET causale_trasporto_id = NULL WHERE d.id = v_ddt;
  END IF;
  -- Alias obbligatorio: `ddt_id` e' anche un parametro OUT di questa funzione.
  UPDATE vendite.ddt_righe dr SET prezzo_unitario = NULL WHERE dr.ddt_id = v_ddt;
  RETURN QUERY SELECT v_ord, v_ddt;
END $$ LANGUAGE plpgsql;

-- DDT STANDALONE (nessun ordine dietro) con una riga SENZA prezzo: e' l'unico
-- modo per ottenere un prezzo NON risolvibile, visto che ordini_righe.prezzo_unitario
-- e' NOT NULL — da un ordine il prezzo c'e' sempre e la riga DDT lo eredita.
CREATE OR REPLACE FUNCTION pg_temp.mk_ddt_standalone(p_causale bigint)
RETURNS bigint AS $$
DECLARE r RECORD; v_ddt bigint;
BEGIN
  SELECT * INTO r FROM tmp_refs;
  INSERT INTO vendite.ddt (destinatario_soggetto_ruolo_id, stato_doc_ddt_id, data,
    billing_account_id, valuta_id, causale_trasporto_id, emittente_fiscale_id, storicizza, meta)
  VALUES (r.soggetto_ruolo_id,
          (SELECT s.id FROM config.stati_doc_ddt s WHERE s.codice_interno='DRAFT' LIMIT 1),
          DATE '2026-07-15', r.billing_account_id, r.valuta_id, p_causale,
          r.emittente_fiscale_id, false, jsonb_build_object('test_scope','pgtap_causale'))
  RETURNING id INTO v_ddt;
  INSERT INTO vendite.ddt_righe (ddt_id, riga_nr, articolo_id, descrizione,
    qta_operativa, quantita, prezzo_unitario, iva_id, attivo, storicizza, meta)
  VALUES (v_ddt, 1, r.articolo_id, 'Riga senza prezzo', 10, 10, NULL, r.iva_id, true, false,
          jsonb_build_object('test_scope','pgtap_causale'));
  INSERT INTO vendite.ddt_indirizzi (ddt_id, tipo_indirizzo_id, snapshot)
  VALUES (v_ddt, r.tipo_ind_con_id, '{"display":"CON"}'::jsonb) ON CONFLICT DO NOTHING;
  RETURN v_ddt;
END $$ LANGUAGE plpgsql;

-- ============================================================
-- 1) Il vocabolario guida: zero IF hardcoded, una cella di seed
-- ============================================================
SELECT is(
  (SELECT array_agg(c.codice ORDER BY c.codice) FROM config.causali_trasporto c WHERE c.fatturabile),
  ARRAY['VENDITA']::varchar[],
  '1) seed: VENDITA e'' l''unica causale fatturabile (le altre sette sono solo trasporto)');

-- ============================================================
-- 2) Gate R1: senza causale non si emette
-- ============================================================
CREATE TEMP TABLE tmp_senza AS SELECT * FROM pg_temp.mk_ddt_da_ordine(NULL);
SELECT throws_ok(
  $$ UPDATE vendite.ddt SET stato_doc_ddt_id=(SELECT stato_ddt_emesso_id FROM tmp_refs)
      WHERE id=(SELECT ddt_id FROM tmp_senza) $$,
  'P0001', NULL,
  '2) gate R1: emissione senza causale di trasporto -> bloccata');

-- ============================================================
-- 3) Gate R2: VENDITA + prezzo non risolvibile -> bloccata.
--    DDT standalone: senza ordine dietro non c'e' prezzo da ereditare.
-- ============================================================
CREATE TEMP TABLE tmp_nopr AS
SELECT pg_temp.mk_ddt_standalone((SELECT causale_vendita_id FROM tmp_refs)) AS ddt_id;
SELECT throws_ok(
  $$ UPDATE vendite.ddt SET stato_doc_ddt_id=(SELECT stato_ddt_emesso_id FROM tmp_refs)
      WHERE id=(SELECT ddt_id FROM tmp_nopr) $$,
  'P0001', NULL,
  '3) gate R2: causale VENDITA + riga senza prezzo risolvibile -> emissione bloccata');

-- ============================================================
-- 4) Gate R2, il caso legittimo: prezzo ereditato dall'ordine
-- ============================================================
CREATE TEMP TABLE tmp_eredita AS
SELECT * FROM pg_temp.mk_ddt_da_ordine('VENDITA');
SELECT lives_ok(
  $$ UPDATE vendite.ddt SET stato_doc_ddt_id=(SELECT stato_ddt_emesso_id FROM tmp_refs)
      WHERE id=(SELECT ddt_id FROM tmp_eredita) $$,
  '4) gate R2: riga da evasione senza prezzo proprio ma ereditabile dall''ordine -> emissione passa');

-- ============================================================
-- 5-6) La cintura del lister: solo trasporto vs vendita
-- ============================================================
CREATE TEMP TABLE tmp_camp AS
SELECT * FROM pg_temp.mk_ddt_da_ordine('CAMPIONATURA');
SELECT dbops.fn_pgtap_porta_a_stato('vendite.ddt', (SELECT ddt_id FROM tmp_camp), 'CONSEGNATO');

CREATE TEMP TABLE tmp_vend AS
SELECT * FROM pg_temp.mk_ddt_da_ordine('VENDITA');
SELECT dbops.fn_pgtap_porta_a_stato('vendite.ddt', (SELECT ddt_id FROM tmp_vend), 'CONSEGNATO');

SELECT is(
  (SELECT COUNT(*)::int FROM vendite.fn_list_ddt_da_pushare(NULL,NULL,NULL,(SELECT ddt_id FROM tmp_camp))),
  0, '5) causale CAMPIONATURA: solo trasporto -> mai eleggibile al push, anche a CONSEGNATO');

SELECT is(
  (SELECT COUNT(*)::int FROM vendite.fn_list_ddt_da_pushare(NULL,NULL,NULL,(SELECT ddt_id FROM tmp_vend))),
  1, '6) controprova: stessa situazione con causale VENDITA -> eleggibile');

SELECT * FROM finish();
ROLLBACK;
