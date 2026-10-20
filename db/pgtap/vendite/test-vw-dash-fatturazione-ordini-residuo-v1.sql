-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13, 2d): l'area della dashboard e' il codice della sorgente (ORDINE_VENDITA).
-- pgTAP test per Zero ERP
-- Test: vw_dash_fatturazione_ordini a valore RESIDUO da spedire — step 8,
--       brief-db-fatturazione-ddt-resi §4c / DL-23 EMENDATO.
-- (changeset 20260718-13)
-- ------------------------------------------------------------
-- Indice test (1..6):
--   1) security_invoker=on sulla vista (regressione V-1)
--   2) A trigger CONSEGNATO, 10 pz @25, evasi 4 -> valore_totale 150 (6x25):
--      il valore spedito lo porta il DDT, l'ordine porta il RESTO
--   3) B trigger CONSEGNATO, evaso tutto -> valore_totale 0 (staffetta
--      completata: il valore e' interamente in mano al DDT)
--   4) B + reso 3 PER RICONSEGNA confermato -> il residuo RISALE -> 75 (3x25).
--      E' la formula reso-aware single-source (fn_ordine_riga_qta_riconsegna):
--      la merce tornata per ri-spedizione e' di nuovo "da spedire"
--   5) C trigger CONFERMATO, evasi 4 -> valore PIENO 250 (DL-23 emendato:
--      fattura l'ordine, il DDT non conta nulla — col netto sarebbe un nuovo
--      buco cieco sulla configurazione di default)
--   6) effetto a valle: vw_dash_aperto_documenti (serbatoio) eredita il netto
--      di A (150) senza modifiche proprie
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
--   anagrafiche e articoli sono vuoti). fn_pgtap_crea_mondo_cliente fa azienda,
--   operatore, cliente BA legato a quell'azienda e APRE il contesto da se'.
CREATE TEMP TABLE _m AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('pgTAP dash residuo');
-- Il mondo ha gia' aperto il contesto sul suo operatore: la riga lo
--   dichiara (e il guardrail del preambolo la cerca).
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _m)); END $ctx$;

SELECT plan(6);

-- Dal 2026-09-28 conferma e annullo del reso sono verbi che applicano
-- l'azione conferma_reso (brief-db-magazzino-lotto-3-bis-carico-da-reso, D-3b-f):
-- l'operatore di fixture non ha azioni, si concede qui.
DO $az$ BEGIN
    PERFORM dbops.fn_pgtap_concedi_azione(
        NULLIF(current_setting('app.current_user_id', true), '')::integer, 'conferma_reso');
END $az$;

-- ============================================================
-- Riferimenti + helper
-- ============================================================
CREATE TEMP TABLE tmp_refs AS
SELECT
  -- ⛔ rev 2026-10-13: BA, ruolo del cliente ed emittente dal mondo costruito;
  --   l'articolo si costruisce (merce, non gestito: il test non misura il magazzino).
  (SELECT billing_account_id FROM _m)                                    AS billing_account_id,
  (SELECT cliente_soggetto_ruolo_id FROM _m)                             AS soggetto_ruolo_id,
  dbops.fn_pgtap_crea_articolo('PGTAP-DASH-RESIDUO', false)                  AS articolo_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1)              AS valuta_id,
  (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1) AS iva_id,
  (SELECT emittente_fiscale_id FROM _m)                                  AS emittente_fiscale_id,
  (SELECT s.id FROM config.stati_doc_ordini s WHERE s.codice_interno='CONFERMATO' AND s.attivo LIMIT 1) AS stato_ord_conf_id,
  (SELECT s.id FROM config.stati_doc_ddt s WHERE s.codice_interno='EMESSO' AND s.attivo LIMIT 1)     AS stato_ddt_emesso_id,
  (SELECT s.id FROM config.stati_doc_ddt s WHERE s.codice_interno='SPEDITO' AND s.attivo LIMIT 1)    AS stato_ddt_spedito_id,
  (SELECT s.id FROM config.stati_doc_ddt s WHERE s.codice_interno='CONSEGNATO' AND s.attivo LIMIT 1) AS stato_ddt_consegnato_id,
  (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno='DDT_VENDITA' AND s.attivo LIMIT 1)     AS sorgente_ddt_id,
  (SELECT s.id FROM config.stati_doc_reso s WHERE s.codice_interno='DRAFT' AND s.attivo LIMIT 1)     AS stato_reso_draft_id,
  (SELECT t.id FROM config.tipi_reso t WHERE t.codice_interno='RESO_PER_RICONSEGNA' AND t.attivo LIMIT 1) AS tipo_riconsegna_id,
  (SELECT c.id FROM config.causali_trasporto c WHERE c.codice='VENDITA' LIMIT 1) AS causale_vendita_id,
  (SELECT id FROM config.tipi_indirizzi WHERE codice_interno='CON')     AS tipo_ind_con_id;

-- Ordine (10 pz @25) con trigger parametrico.
-- ⚠️ rev 2026-10-08 (brief-db-righe-e-componenti-debiti-residui, D-1): la testata nasce DRAFT, prende la riga, poi passa a CONFERMATO con dbops.fn_pgtap_porta_a_stato — fuori bozza le righe non si scrivono piu' (20261008-90).
CREATE OR REPLACE FUNCTION pg_temp.mk_ordine(p_trigger varchar)
RETURNS TABLE(ordine_id bigint, ordine_riga_id bigint) AS $$
DECLARE r RECORD; v_ord bigint; v_orr bigint;
BEGIN
  SELECT * INTO r FROM tmp_refs;
  INSERT INTO vendite.ordini (soggetto_ruolo_id, billing_account_id, stato_doc_ordine_id,
    valuta_id, data, fatturazione_trigger, emittente_fiscale_id, storicizza, meta)
  VALUES (r.soggetto_ruolo_id, r.billing_account_id,
          (SELECT s.id FROM config.stati_doc_ordini s WHERE s.codice_interno = 'DRAFT' AND s.attivo IS TRUE),
          r.valuta_id,
          DATE '2026-07-15', p_trigger, r.emittente_fiscale_id, false,
          jsonb_build_object('test_scope','pgtap_residuo'))
  RETURNING id INTO v_ord;
  -- trgfn_ordini_normalize eredita il trigger dal BA solo su INSERT: va rimesso.
  UPDATE vendite.ordini SET fatturazione_trigger = p_trigger WHERE id = v_ord;
  INSERT INTO vendite.ordini_righe (ordine_id, riga_nr, articolo_id, descrizione,
    qta_operativa, quantita, prezzo_unitario, iva_id, attivo, storicizza, meta)
  VALUES (v_ord, 1, r.articolo_id, 'Riga residuo', 10, 10, 25, r.iva_id, true, false,
          jsonb_build_object('test_scope','pgtap_residuo'))
  RETURNING id INTO v_orr;
  PERFORM dbops.fn_pgtap_porta_a_stato('vendite.ordini', v_ord, 'CONFERMATO');
  RETURN QUERY SELECT v_ord, v_orr;
END $$ LANGUAGE plpgsql;

-- Evasione parziale: DDT per qta indicata (resta DRAFT: il residuo legge il
-- fulfillment, che nasce alla generazione — non serve emettere).
CREATE OR REPLACE FUNCTION pg_temp.evadi(p_ord bigint, p_riga bigint, p_qta numeric)
RETURNS bigint AS $$
  SELECT vendite.fn_genera_ddt_da_ordine(p_ord,
    jsonb_build_array(jsonb_build_object('ordine_riga_id', p_riga, 'qta_da_evadere', p_qta)));
$$ LANGUAGE sql;

-- ============================================================
-- FIXTURE
-- ============================================================
-- A: trigger CONSEGNATO, evasi 4 di 10
CREATE TEMP TABLE tmp_a AS SELECT * FROM pg_temp.mk_ordine('CONSEGNATO');
SELECT pg_temp.evadi((SELECT ordine_id FROM tmp_a), (SELECT ordine_riga_id FROM tmp_a), 4);

-- B: trigger CONSEGNATO, evaso tutto (10) in un DDT poi CONSEGNATO (serve al reso)
CREATE TEMP TABLE tmp_b AS SELECT * FROM pg_temp.mk_ordine('CONSEGNATO');
CREATE TEMP TABLE tmp_b_ddt AS
SELECT pg_temp.evadi((SELECT ordine_id FROM tmp_b), (SELECT ordine_riga_id FROM tmp_b), 10) AS ddt_id;
INSERT INTO vendite.ddt_indirizzi (ddt_id, tipo_indirizzo_id, snapshot)
SELECT (SELECT ddt_id FROM tmp_b_ddt), (SELECT tipo_ind_con_id FROM tmp_refs), '{"display":"CON"}'::jsonb
ON CONFLICT DO NOTHING;
-- causale obbligatoria all'emissione (step 5b)
UPDATE vendite.ddt SET causale_trasporto_id=(SELECT causale_vendita_id FROM tmp_refs) WHERE id=(SELECT ddt_id FROM tmp_b_ddt);
UPDATE vendite.ddt SET stato_doc_ddt_id=(SELECT stato_ddt_emesso_id FROM tmp_refs)     WHERE id=(SELECT ddt_id FROM tmp_b_ddt);
UPDATE vendite.ddt SET stato_doc_ddt_id=(SELECT stato_ddt_spedito_id FROM tmp_refs)    WHERE id=(SELECT ddt_id FROM tmp_b_ddt);
UPDATE vendite.ddt SET stato_doc_ddt_id=(SELECT stato_ddt_consegnato_id FROM tmp_refs) WHERE id=(SELECT ddt_id FROM tmp_b_ddt);

-- C: trigger CONFERMATO, evasi 4 di 10
CREATE TEMP TABLE tmp_c AS SELECT * FROM pg_temp.mk_ordine('CONFERMATO');
SELECT pg_temp.evadi((SELECT ordine_id FROM tmp_c), (SELECT ordine_riga_id FROM tmp_c), 4);

-- ============================================================
-- ASSERZIONI
-- ============================================================
SELECT ok(
  (SELECT 'security_invoker=on' = ANY(c.reloptions)
     FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
    WHERE n.nspname='vendite' AND c.relname='vw_dash_fatturazione_ordini'),
  '1) security_invoker=on ri-specificato (no bypass RLS)');

-- 2) A: il valore spedito lo porta il DDT, l'ordine porta il resto
SELECT is(
  (SELECT valore_totale FROM vendite.vw_dash_fatturazione_ordini
    WHERE documento_id=(SELECT ordine_id FROM tmp_a)),
  150::numeric, '2) trigger CONSEGNATO, evasi 4 di 10 @25 -> valore residuo 150 (6x25)');

-- 3) B: staffetta completata
SELECT is(
  (SELECT valore_totale FROM vendite.vw_dash_fatturazione_ordini
    WHERE documento_id=(SELECT ordine_id FROM tmp_b)),
  0::numeric, '3) evaso tutto -> valore 0 (il valore e'' interamente in mano al DDT)');

-- 4) B + reso 3 PER RICONSEGNA confermato: il residuo risale (reso-aware)
-- ⛔ rev 2026-10-13: testata e righe del reso in due istruzioni. Con un operatore
--   vero (non piu' l'utente 1) la WITH CHECK di resi_righe risale al reso, e un
--   reso scritto nella stessa istruzione (CTE) e' fuori dalla sua snapshot.
CREATE TEMP TABLE reso AS
WITH ins AS (
  INSERT INTO vendite.resi (stato_doc_reso_id, sorgente_tipo_id, sorgente_uid, storicizza, meta)
  SELECT r.stato_reso_draft_id, r.sorgente_ddt_id, (SELECT d.uid FROM vendite.ddt d WHERE d.id=(SELECT ddt_id FROM tmp_b_ddt)),
         false, jsonb_build_object('test_scope','pgtap_residuo')
  FROM tmp_refs r RETURNING id)
SELECT id FROM ins;
INSERT INTO vendite.resi_righe (reso_id, riga_nr, ddt_riga_id, ordine_riga_id,
  articolo_id, descrizione, qta_operativa, uom_operativa_id, factor_to_base, tipo_reso_id, storicizza)
SELECT (SELECT id FROM reso), 1, dr.id, (SELECT ordine_riga_id FROM tmp_b),
       dr.articolo_id, dr.descrizione, 3, dr.uom_operativa_id, dr.factor_to_base,
       (SELECT tipo_riconsegna_id FROM tmp_refs), false
FROM vendite.ddt_righe dr WHERE dr.ddt_id=(SELECT ddt_id FROM tmp_b_ddt);

SELECT vendite.fn_conferma_reso((SELECT id FROM reso));

SELECT is(
  (SELECT valore_totale FROM vendite.vw_dash_fatturazione_ordini
    WHERE documento_id=(SELECT ordine_id FROM tmp_b)),
  75::numeric, '4) reso 3 per riconsegna confermato -> il residuo RISALE a 75 (formula reso-aware single-source)');

-- 5) C: trigger CONFERMATO resta al pieno (DL-23 emendato)
SELECT is(
  (SELECT valore_totale FROM vendite.vw_dash_fatturazione_ordini
    WHERE documento_id=(SELECT ordine_id FROM tmp_c)),
  250::numeric, '5) trigger CONFERMATO, evasi 4 -> valore PIENO 250 (fattura l''ordine: niente netto)');

-- 6) il serbatoio eredita il netto senza modifiche proprie
SELECT is(
  (SELECT valore_totale FROM vendite.vw_dash_aperto_documenti
    WHERE area='ORDINE_VENDITA' AND documento_id=(SELECT ordine_id FROM tmp_a)),
  150::numeric, '6) vw_dash_aperto_documenti (serbatoio) mostra il residuo 150 di A (effetto a valle)');

SELECT * FROM finish();
ROLLBACK;
