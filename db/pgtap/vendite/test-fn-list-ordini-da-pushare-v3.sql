-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: vendite.fn_list_ordini_da_pushare — fix «orfano da push»
--       (decoupling fatturazione <-> spedizione, rev 20260710-01)
-- Piano: piano-db-fix-orfano-push-ordine-confermato.md §4.2
-- Brief: brief-db-ddt-vendita-evasione-e-stati §16 (casi 7-10)
-- ------------------------------------------------------------
-- Indice test (1..10):
--  1) riferimenti minimi disponibili (BA pushabile CONFERMATO)
--  2) sanity: evasione full -> ordine EVASO (proiezione C5 invariata)
--  3) caso 7  — orfano recuperato: ordine EVASO trigger CONFERMATO in fn_list (>=1)
--  4) caso 8  — XOR: DDT ordine-sourced (src_trigger=CONFERMATO) a SPEDITO
--               NON compare in fn_list_ddt_da_pushare
--  5) caso 10 — no doppione: dopo push simulato (commessa+attivita EMESSA)
--               la re-list ritorna 0
--  6) caso 7b — evasione parziale: ordine PARZIALMENTE_EVASO in fn_list (>=1)
--  7) caso 9  — non-regressione SPEDITO: ordine trigger SPEDITO evaso
--               NON compare in fn_list_ordini_da_pushare
--  8) caso 9b — il DDT dell'ordine trigger SPEDITO (a SPEDITO) compare
--               in fn_list_ddt_da_pushare
--  9) DRAFT escluso (non-regressione predicato stato)
-- 10) ANNULLATO escluso (predicato stato)
-- ------------------------------------------------------------
-- Nota fixture: trgfn_ordini_normalize eredita fatturazione_trigger dal
--   billing_account su INSERT (sovrascrive il valore passato): per il
--   trigger CONFERMATO si usa un BA con fatturazione_ordini='CONFERMATO';
--   per il caso SPEDITO si aggiorna la colonna DOPO l'INSERT (non locked,
--   normalize e' INSERT-only).
-- Nota skip-tolerance: se il DB di test non ha un BA pushabile, i test
--   degradano a pass con fallback OR (pattern test-fn-available-actions-v1).

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

SELECT plan(10);

-- ============================================================
-- Riferimenti minimi (dati esistenti, no creazione da zero)
-- ============================================================
CREATE TEMP TABLE tmp_refs_v3 AS
SELECT
  -- BA pushabile: utility/istanza valorizzate, fatturazione CONFERMATO,
  -- emittente risolvibile (mirror fixture test-fn-available-actions-ordine-v1)
  (SELECT ba.id FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL
      AND ba.istanza_utility_id IS NOT NULL
      AND ba.fatturazione_ordini = 'CONFERMATO'
      AND anagrafiche.fn_get_emittente_fiscale_pk(ba.id) IS NOT NULL
    ORDER BY ba.id LIMIT 1)                          AS push_ba_id,
  (SELECT sr.id FROM anagrafiche.soggetti_ruoli sr
    ORDER BY sr.id LIMIT 1)                          AS soggetto_ruolo_id,
  (SELECT a.id FROM catalogo.articoli a
    WHERE a.attivo IS TRUE
      AND COALESCE(a.is_composito, FALSE) IS FALSE
    ORDER BY a.data_insert DESC NULLS LAST LIMIT 1)  AS articolo_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1) AS valuta_id,
  (SELECT i.id FROM config.iva i
    WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1)    AS iva_id,
  (SELECT s.id FROM config.stati_doc_ordini s
    WHERE s.codice_interno = 'CONFERMATO' AND s.attivo IS TRUE LIMIT 1) AS stato_ord_conf_id,
  (SELECT s.id FROM config.stati_doc_ordini s
    WHERE s.codice_interno = 'DRAFT' AND s.attivo IS TRUE LIMIT 1)      AS stato_ord_draft_id,
  (SELECT s.id FROM config.stati_doc_ordini s
    WHERE s.codice_interno = 'ANNULLATO' AND s.attivo IS TRUE LIMIT 1)  AS stato_ord_annullato_id,
  (SELECT s.id FROM config.stati_doc_ddt s
    WHERE s.codice_interno = 'EMESSO' AND s.attivo IS TRUE LIMIT 1)     AS stato_ddt_emesso_id,
  (SELECT s.id FROM config.stati_doc_ddt s
    WHERE s.codice_interno = 'SPEDITO' AND s.attivo IS TRUE LIMIT 1)    AS stato_ddt_spedito_id,
  -- Dal 2026-07-18 (step 5b / DL-28) la causale di trasporto e' obbligatoria
  -- all'emissione del DDT: VENDITA e' l'unica causale fatturabile, quindi
  -- l'unica che tiene il DDT eleggibile al push.
  (SELECT c.id FROM config.causali_trasporto c WHERE c.codice='VENDITA' LIMIT 1) AS causale_vendita_id;

SELECT ok(
  (SELECT push_ba_id IS NOT NULL
      AND soggetto_ruolo_id IS NOT NULL
      AND articolo_id IS NOT NULL
      AND stato_ord_conf_id IS NOT NULL
      AND stato_ddt_emesso_id IS NOT NULL
      AND stato_ddt_spedito_id IS NOT NULL
   FROM tmp_refs_v3),
  '1) riferimenti minimi disponibili (BA pushabile CONFERMATO)'
);

-- ============================================================
-- FIXTURE A: ordine trigger CONFERMATO, evasione FULL (orfano)
-- ============================================================
CREATE TEMP TABLE tmp_ord_a3 AS
WITH ins AS (
  INSERT INTO vendite.ordini (
    soggetto_ruolo_id, billing_account_id, emittente_fiscale_id,
    stato_doc_ordine_id, valuta_id, data, storicizza, meta)
  SELECT r.soggetto_ruolo_id, r.push_ba_id,
         anagrafiche.fn_get_emittente_fiscale_pk(r.push_ba_id),
         r.stato_ord_draft_id, r.valuta_id, DATE '2026-07-05', false,
         jsonb_build_object('test_scope','pgtap_list_ordini_v3','fix','orfano_a')
  FROM tmp_refs_v3 r
  WHERE r.push_ba_id IS NOT NULL
  RETURNING id, uid)
SELECT * FROM ins;

CREATE TEMP TABLE tmp_ord_a3_riga AS
WITH ins AS (
  INSERT INTO vendite.ordini_righe (
    ordine_id, riga_nr, articolo_id, descrizione,
    qta_operativa, quantita, prezzo_unitario, iva_id,
    attivo, storicizza, meta)
  SELECT o.id, 1, r.articolo_id, 'Riga orfano A (v3)',
         10.000000, 10.000000, 30.000000, r.iva_id,
         true, false, jsonb_build_object('test_scope','pgtap_list_ordini_v3')
  FROM tmp_ord_a3 o, tmp_refs_v3 r
  RETURNING id)
SELECT * FROM ins;

-- ⚠️ rev 2026-10-08 (brief-db-righe-e-componenti-debiti-residui, D-1): la testata nasce DRAFT,
-- prende le righe, poi passa a CONFERMATO con dbops.fn_pgtap_porta_a_stato — fuori bozza le
-- righe non si scrivono piu' (20261008-90). PERFORM ... FROM: tabella vuota se il BA manca.
DO $x$ BEGIN
  PERFORM dbops.fn_pgtap_porta_a_stato('vendite.ordini', o.id, 'CONFERMATO') FROM tmp_ord_a3 o;
END $x$;

-- Evasione FULL: e' il gesto che PRIMA del fix chiudeva la finestra di push
-- (WHERE EXISTS: skip-tolerance se il BA pushabile manca -> fixture vuota)
CREATE TEMP TABLE tmp_ddt_a3 AS
SELECT vendite.fn_genera_ddt_da_ordine((SELECT id FROM tmp_ord_a3)) AS ddt_id
 WHERE EXISTS (SELECT 1 FROM tmp_ord_a3);

-- 2) sanity: proiezione stato C5 invariata (full -> EVASO)
SELECT ok(
  (SELECT sdo.codice_interno = 'EVASO'
     FROM vendite.ordini o
     JOIN config.stati_doc_ordini sdo ON sdo.id = o.stato_doc_ordine_id
    WHERE o.id = (SELECT id FROM tmp_ord_a3))
  OR (SELECT push_ba_id IS NULL FROM tmp_refs_v3),
  '2) sanity: evasione full -> ordine EVASO (C5 invariata)'
);

-- 3) caso 7 — ORFANO RECUPERATO: l'ordine EVASO trigger CONFERMATO
--    (mai pushato) e' di nuovo eleggibile al push
SELECT ok(
  (SELECT count(*) >= 1
     FROM vendite.fn_list_ordini_da_pushare(
            p_ordine_id => (SELECT id FROM tmp_ord_a3)))
  OR (SELECT push_ba_id IS NULL FROM tmp_refs_v3),
  '3) caso 7: ordine EVASO trigger CONFERMATO eleggibile al push (orfano recuperato)'
);

-- 4) caso 8 — XOR preservato: il DDT ordine-sourced (src_trigger=CONFERMATO)
--    portato a SPEDITO NON diventa una seconda sorgente di push
-- Setup guard indirizzi obbligatori (DDT): CON obbligatorio all'emissione.
INSERT INTO vendite.ddt_indirizzi (ddt_id, tipo_indirizzo_id, snapshot)
SELECT (SELECT ddt_id FROM tmp_ddt_a3),
       (SELECT id FROM config.tipi_indirizzi WHERE codice_interno = 'CON'),
       '{"display":"CON test"}'::jsonb
ON CONFLICT DO NOTHING;
-- Causale obbligatoria all'emissione (guard causale_emissione, 2026-07-18).
UPDATE vendite.ddt SET causale_trasporto_id = (SELECT causale_vendita_id FROM tmp_refs_v3)
 WHERE id = (SELECT ddt_id FROM tmp_ddt_a3);
UPDATE vendite.ddt SET stato_doc_ddt_id = (SELECT stato_ddt_emesso_id FROM tmp_refs_v3)
 WHERE id = (SELECT ddt_id FROM tmp_ddt_a3);
UPDATE vendite.ddt SET stato_doc_ddt_id = (SELECT stato_ddt_spedito_id FROM tmp_refs_v3)
 WHERE id = (SELECT ddt_id FROM tmp_ddt_a3);

SELECT ok(
  (SELECT count(*) = 0
     FROM vendite.fn_list_ddt_da_pushare(
            p_ddt_id => (SELECT ddt_id FROM tmp_ddt_a3)))
  OR (SELECT push_ba_id IS NULL FROM tmp_refs_v3),
  '4) caso 8: DDT src_trigger=CONFERMATO a SPEDITO escluso da fn_list_ddt_da_pushare (XOR)'
);

-- 5) caso 10 — NO DOPPIONE: simulazione push a livello DB (commessa +
--    attivita con stato_emissione=EMESSA) -> la re-list torna 0.
--    E' la cintura che sostituisce la transizione forzata ->EVASO del BE.
CREATE TEMP TABLE tmp_pushrow_a3 AS
SELECT * FROM vendite.fn_list_ordini_da_pushare(
         p_ordine_id => (SELECT id FROM tmp_ord_a3));

CREATE TEMP TABLE tmp_commessa_a3 AS
SELECT vendite.fn_get_or_create_commessa(
         p_billing_account_id          => pr.billing_account_id,
         p_utility_id                  => pr.utility_id,
         p_competenza_dal              => pr.competenza_dal,
         p_competenza_al               => pr.competenza_al,
         p_meta => jsonb_build_object('test_scope','pgtap_list_ordini_v3')
       ) AS commessa_id
  FROM tmp_pushrow_a3 pr
 LIMIT 1;

SELECT vendite.fn_upsert_commessa_attivita(
         p_commessa_id                   => c.commessa_id,
         p_segment_key                   => pr.segment_key,
         p_articolo_id                   => pr.articolo_id,
         p_istanza_utility_id            => pr.istanza_utility_id,
         p_data_attivita                 => pr.data_attivita,
         p_uom_id                        => pr.uom_id,
         p_quantita                      => pr.quantita,
         p_competenza_mese               => pr.competenza_mese,
         p_competenza_dal                => pr.competenza_dal,
         p_competenza_al                 => pr.competenza_al,
         p_prezzo_snapshot               => pr.prezzo_snapshot,
         p_prezzo_base_snapshot          => NULL,
         p_origine_prezzo                => NULL,
         p_tipo_variazione_applicata     => NULL,
         p_valore_variazione_applicata   => NULL,
         p_promo_id                      => NULL,
         p_contratto_id                  => NULL,
         p_categoria_cliente_id_snapshot => NULL,
         p_classe_utenza_id_snapshot     => NULL,
         p_qta_operativa                 => pr.qta_operativa,
         p_uom_operativa_id              => pr.uom_operativa_id,
         p_factor_to_base                => pr.factor_to_base,
         p_tipo_doc_fiscale_id           => pr.tipo_doc_fiscale_id,
         p_valuta_id                     => pr.valuta_id,
         p_prezzo_bloccato               => pr.prezzo_bloccato,
         p_pricing_mode                  => pr.pricing_mode,
         p_stato_emissione               => 'EMESSA',
         p_sorgente_tipo_id              => pr.sorgente_tipo_id,
         p_sorgente_uid                  => pr.sorgente_uid,
         p_meta                          => pr.meta)
  FROM tmp_pushrow_a3 pr, tmp_commessa_a3 c;

SELECT ok(
  (SELECT count(*) = 0
     FROM vendite.fn_list_ordini_da_pushare(
            p_ordine_id => (SELECT id FROM tmp_ord_a3)))
  OR (SELECT push_ba_id IS NULL FROM tmp_refs_v3),
  '5) caso 10: dopo push simulato (EMESSA) la re-list = 0 (no doppione)'
);

-- ============================================================
-- FIXTURE B: ordine trigger CONFERMATO, evasione PARZIALE
-- ============================================================
CREATE TEMP TABLE tmp_ord_b3 AS
WITH ins AS (
  INSERT INTO vendite.ordini (
    soggetto_ruolo_id, billing_account_id, emittente_fiscale_id,
    stato_doc_ordine_id, valuta_id, data, storicizza, meta)
  SELECT r.soggetto_ruolo_id, r.push_ba_id,
         anagrafiche.fn_get_emittente_fiscale_pk(r.push_ba_id),
         r.stato_ord_draft_id, r.valuta_id, DATE '2026-07-06', false,
         jsonb_build_object('test_scope','pgtap_list_ordini_v3','fix','orfano_b')
  FROM tmp_refs_v3 r
  WHERE r.push_ba_id IS NOT NULL
  RETURNING id)
SELECT * FROM ins;

CREATE TEMP TABLE tmp_ord_b3_riga AS
WITH ins AS (
  INSERT INTO vendite.ordini_righe (
    ordine_id, riga_nr, articolo_id, descrizione,
    qta_operativa, quantita, prezzo_unitario, iva_id,
    attivo, storicizza, meta)
  SELECT o.id, 1, r.articolo_id, 'Riga orfano B (v3)',
         10.000000, 10.000000, 20.000000, r.iva_id,
         true, false, jsonb_build_object('test_scope','pgtap_list_ordini_v3')
  FROM tmp_ord_b3 o, tmp_refs_v3 r
  RETURNING id)
SELECT * FROM ins;

-- ⚠️ rev 2026-10-08 (brief-db-righe-e-componenti-debiti-residui, D-1): la testata nasce DRAFT,
-- prende le righe, poi passa a CONFERMATO con dbops.fn_pgtap_porta_a_stato — fuori bozza le
-- righe non si scrivono piu' (20261008-90). PERFORM ... FROM: tabella vuota se il BA manca.
DO $x$ BEGIN
  PERFORM dbops.fn_pgtap_porta_a_stato('vendite.ordini', o.id, 'CONFERMATO') FROM tmp_ord_b3 o;
END $x$;

-- Evasione parziale 4/10 -> PARZIALMENTE_EVASO
SELECT vendite.fn_genera_ddt_da_ordine(
         (SELECT id FROM tmp_ord_b3),
         jsonb_build_array(jsonb_build_object(
             'ordine_riga_id', (SELECT id FROM tmp_ord_b3_riga),
             'qta_da_evadere', 4)))
 WHERE EXISTS (SELECT 1 FROM tmp_ord_b3);

-- 6) caso 7b — anche il PARZIALMENTE_EVASO resta eleggibile
SELECT ok(
  ((SELECT sdo.codice_interno = 'PARZIALMENTE_EVASO'
      FROM vendite.ordini o
      JOIN config.stati_doc_ordini sdo ON sdo.id = o.stato_doc_ordine_id
     WHERE o.id = (SELECT id FROM tmp_ord_b3))
   AND (SELECT count(*) >= 1
          FROM vendite.fn_list_ordini_da_pushare(
                 p_ordine_id => (SELECT id FROM tmp_ord_b3))))
  OR (SELECT push_ba_id IS NULL FROM tmp_refs_v3),
  '6) caso 7b: ordine PARZIALMENTE_EVASO trigger CONFERMATO eleggibile al push'
);

-- ============================================================
-- FIXTURE C: ordine trigger SPEDITO (non-regressione XOR lato DDT)
-- trgfn_ordini_normalize e' INSERT-only: il trigger si aggiorna DOPO
-- ============================================================
CREATE TEMP TABLE tmp_ord_c3 AS
WITH ins AS (
  INSERT INTO vendite.ordini (
    soggetto_ruolo_id, billing_account_id, emittente_fiscale_id,
    stato_doc_ordine_id, valuta_id, data, storicizza, meta)
  SELECT r.soggetto_ruolo_id, r.push_ba_id,
         anagrafiche.fn_get_emittente_fiscale_pk(r.push_ba_id),
         r.stato_ord_draft_id, r.valuta_id, DATE '2026-07-07', false,
         jsonb_build_object('test_scope','pgtap_list_ordini_v3','fix','spedito_c')
  FROM tmp_refs_v3 r
  WHERE r.push_ba_id IS NOT NULL
  RETURNING id)
SELECT * FROM ins;

UPDATE vendite.ordini
   SET fatturazione_trigger = 'SPEDITO'
 WHERE id = (SELECT id FROM tmp_ord_c3);

INSERT INTO vendite.ordini_righe (
  ordine_id, riga_nr, articolo_id, descrizione,
  qta_operativa, quantita, prezzo_unitario, iva_id,
  attivo, storicizza, meta)
SELECT o.id, 1, r.articolo_id, 'Riga spedito C (v3)',
       5.000000, 5.000000, 15.000000, r.iva_id,
       true, false, jsonb_build_object('test_scope','pgtap_list_ordini_v3')
FROM tmp_ord_c3 o, tmp_refs_v3 r;

-- ⚠️ rev 2026-10-08 (brief-db-righe-e-componenti-debiti-residui, D-1): la testata nasce DRAFT,
-- prende le righe, poi passa a CONFERMATO con dbops.fn_pgtap_porta_a_stato — fuori bozza le
-- righe non si scrivono piu' (20261008-90). PERFORM ... FROM: tabella vuota se il BA manca.
DO $x$ BEGIN
  PERFORM dbops.fn_pgtap_porta_a_stato('vendite.ordini', o.id, 'CONFERMATO') FROM tmp_ord_c3 o;
END $x$;

CREATE TEMP TABLE tmp_ddt_c3 AS
SELECT vendite.fn_genera_ddt_da_ordine((SELECT id FROM tmp_ord_c3)) AS ddt_id
 WHERE EXISTS (SELECT 1 FROM tmp_ord_c3);

-- 7) caso 9 — l'ordine trigger SPEDITO evaso NON pusha (filtro trigger)
SELECT ok(
  (SELECT count(*) = 0
     FROM vendite.fn_list_ordini_da_pushare(
            p_ordine_id => (SELECT id FROM tmp_ord_c3)))
  OR (SELECT push_ba_id IS NULL FROM tmp_refs_v3),
  '7) caso 9: ordine trigger SPEDITO evaso escluso da fn_list_ordini_da_pushare'
);

-- 8) caso 9b — per il trigger SPEDITO pusha il DDT (invariato)
-- Setup guard indirizzi obbligatori (DDT): CON obbligatorio all'emissione.
INSERT INTO vendite.ddt_indirizzi (ddt_id, tipo_indirizzo_id, snapshot)
SELECT (SELECT ddt_id FROM tmp_ddt_c3),
       (SELECT id FROM config.tipi_indirizzi WHERE codice_interno = 'CON'),
       '{"display":"CON test"}'::jsonb
ON CONFLICT DO NOTHING;
-- Causale obbligatoria all'emissione (guard causale_emissione, 2026-07-18).
UPDATE vendite.ddt SET causale_trasporto_id = (SELECT causale_vendita_id FROM tmp_refs_v3)
 WHERE id = (SELECT ddt_id FROM tmp_ddt_c3);
UPDATE vendite.ddt SET stato_doc_ddt_id = (SELECT stato_ddt_emesso_id FROM tmp_refs_v3)
 WHERE id = (SELECT ddt_id FROM tmp_ddt_c3);
UPDATE vendite.ddt SET stato_doc_ddt_id = (SELECT stato_ddt_spedito_id FROM tmp_refs_v3)
 WHERE id = (SELECT ddt_id FROM tmp_ddt_c3);

SELECT ok(
  (SELECT count(*) >= 1
     FROM vendite.fn_list_ddt_da_pushare(
            p_ddt_id => (SELECT ddt_id FROM tmp_ddt_c3)))
  OR (SELECT push_ba_id IS NULL FROM tmp_refs_v3),
  '8) caso 9b: DDT dell''ordine trigger SPEDITO (a SPEDITO) eleggibile in fn_list_ddt_da_pushare'
);

-- ============================================================
-- 9-10) Predicato stato: DRAFT e ANNULLATO restano esclusi
-- ============================================================
CREATE TEMP TABLE tmp_ord_d3 AS
WITH ins AS (
  INSERT INTO vendite.ordini (
    soggetto_ruolo_id, billing_account_id, emittente_fiscale_id,
    stato_doc_ordine_id, valuta_id, data, storicizza, meta)
  SELECT r.soggetto_ruolo_id, r.push_ba_id,
         anagrafiche.fn_get_emittente_fiscale_pk(r.push_ba_id),
         r.stato_ord_draft_id, r.valuta_id, DATE '2026-07-08', false,
         jsonb_build_object('test_scope','pgtap_list_ordini_v3','fix','draft_d')
  FROM tmp_refs_v3 r
  WHERE r.push_ba_id IS NOT NULL
  RETURNING id)
SELECT * FROM ins;

INSERT INTO vendite.ordini_righe (
  ordine_id, riga_nr, articolo_id, descrizione,
  qta_operativa, quantita, prezzo_unitario, iva_id,
  attivo, storicizza, meta)
SELECT o.id, 1, r.articolo_id, 'Riga draft D (v3)',
       5.000000, 5.000000, 15.000000, r.iva_id,
       true, false, jsonb_build_object('test_scope','pgtap_list_ordini_v3')
FROM tmp_ord_d3 o, tmp_refs_v3 r;

SELECT ok(
  (SELECT count(*) = 0
     FROM vendite.fn_list_ordini_da_pushare(
            p_ordine_id => (SELECT id FROM tmp_ord_d3)))
  OR (SELECT push_ba_id IS NULL FROM tmp_refs_v3),
  '9) DRAFT escluso dal push (non-regressione predicato stato)'
);

CREATE TEMP TABLE tmp_ord_e3 AS
WITH ins AS (
  INSERT INTO vendite.ordini (
    soggetto_ruolo_id, billing_account_id, emittente_fiscale_id,
    stato_doc_ordine_id, valuta_id, data, storicizza, meta)
  SELECT r.soggetto_ruolo_id, r.push_ba_id,
         anagrafiche.fn_get_emittente_fiscale_pk(r.push_ba_id),
         r.stato_ord_draft_id, r.valuta_id, DATE '2026-07-08', false,
         jsonb_build_object('test_scope','pgtap_list_ordini_v3','fix','annullato_e')
  FROM tmp_refs_v3 r
  WHERE r.push_ba_id IS NOT NULL
    AND r.stato_ord_annullato_id IS NOT NULL
  RETURNING id)
SELECT * FROM ins;

INSERT INTO vendite.ordini_righe (
  ordine_id, riga_nr, articolo_id, descrizione,
  qta_operativa, quantita, prezzo_unitario, iva_id,
  attivo, storicizza, meta)
SELECT o.id, 1, r.articolo_id, 'Riga annullato E (v3)',
       5.000000, 5.000000, 15.000000, r.iva_id,
       true, false, jsonb_build_object('test_scope','pgtap_list_ordini_v3')
FROM tmp_ord_e3 o, tmp_refs_v3 r;

-- ⚠️ rev 2026-10-08 (brief-db-righe-e-componenti-debiti-residui, D-1): la testata nasce DRAFT,
-- prende le righe, poi passa a ANNULLATO con dbops.fn_pgtap_porta_a_stato — fuori bozza le
-- righe non si scrivono piu' (20261008-90). PERFORM ... FROM: tabella vuota se il BA manca.
DO $x$ BEGIN
  PERFORM dbops.fn_pgtap_porta_a_stato('vendite.ordini', o.id, 'ANNULLATO') FROM tmp_ord_e3 o;
END $x$;

SELECT ok(
  (SELECT count(*) = 0
     FROM vendite.fn_list_ordini_da_pushare(
            p_ordine_id => (SELECT id FROM tmp_ord_e3)))
  OR (SELECT push_ba_id IS NULL FROM tmp_refs_v3)
  OR (SELECT stato_ord_annullato_id IS NULL FROM tmp_refs_v3),
  '10) ANNULLATO escluso dal push (predicato stato)'
);

SELECT * FROM finish();
ROLLBACK;
