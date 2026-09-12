-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: script.fn_available_actions_ddt — blocco pdf {mode, allow_allegati}
--       (bottone PDF data-driven via capabilities — dominio PILOTA)
-- Piano: piano-db-pdf-mode-capabilities-5-domini.md §6
-- ------------------------------------------------------------
-- Il blocco pdf e' una proiezione identica nelle 5 fn: il pilota DDT
-- prova il wiring (stato -> pdf_mode/pdf_allow_allegati); il seed
-- per-dominio e' coperto da test-stati-doc-pdf-mode-v1.sql.
-- ------------------------------------------------------------
-- Indice test (1..5):
--  1) riferimenti minimi disponibili
--  2) DDT DRAFT -> pdf.mode = PREVIEW
--  3) DDT DRAFT -> pdf.allow_allegati = false
--  4) blocco pdf presente come oggetto con entrambe le chiavi
--  5) DDT EMESSO -> pdf.mode = ARCHIVE (proiezione segue lo stato)
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

SELECT plan(5);

-- Contesto non-API: GUC vuota (emittente esplicito nei payload).
-- ⛔ 2026-09-04 — QUI IL TEST SPEGNEVA IL GUARD, e adesso non piu'.
--   La riga rimossa era `set_config('app.current_user_id', '', true)`: senza
--   utente in sessione `script.trgfn_guard_emittente_scope` usciva subito con
--   RETURN NEW, e le fixture entravano senza che nessuno guardasse l'emittente.
--   La fase 6 di `brief-db-processi-automatici-identita-e-perimetro` chiude quel
--   ramo — una sessione applicativa senza utente non scrive piu'.
--   ⇒ Il contesto operatore del preambolo RESTA valido per tutto il file, e le
--     fixture prendono l'emittente su cui quell'operatore puo' davvero scrivere
--     (`script.fn_pgtap_emittente_operatore()`).
--   ⭐ Non e' una riparazione di comodo: prima questo file collaudava il
--     comportamento di una porta aperta, adesso attraversa il guard come lo
--     attraversa l'applicazione.

CREATE TEMP TABLE tmp_refs_pdf AS
SELECT
  (SELECT ba.id FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL
      AND ba.istanza_utility_id IS NOT NULL
    ORDER BY ba.id LIMIT 1)                          AS billing_account_id,
  (SELECT sr.id FROM anagrafiche.soggetti_ruoli sr
    ORDER BY sr.id LIMIT 1)                          AS soggetto_ruolo_id,
  (SELECT a.id FROM catalogo.articoli a
    WHERE a.attivo IS TRUE
      AND COALESCE(a.is_composito, FALSE) IS FALSE
    ORDER BY a.data_insert DESC NULLS LAST LIMIT 1)  AS articolo_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1) AS valuta_id,
  (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1) AS iva_id,
  (SELECT ef.id FROM anagrafiche.emittenti_fiscali ef ORDER BY ef.id LIMIT 1)  AS emittente_fiscale_id,
  (SELECT s.id FROM config.stati_doc_ordini s
    WHERE s.codice_interno = 'CONFERMATO' AND s.attivo IS TRUE LIMIT 1) AS stato_ord_conf_id,
  (SELECT s.id FROM config.stati_doc_ddt s
    WHERE s.codice_interno = 'EMESSO' AND s.attivo IS TRUE LIMIT 1)     AS stato_ddt_emesso_id,
  (SELECT ct.id FROM config.causali_trasporto ct
    WHERE ct.codice = 'VENDITA' LIMIT 1)                               AS causale_vendita_id;

SELECT ok(
  (SELECT billing_account_id IS NOT NULL AND articolo_id IS NOT NULL
      AND stato_ord_conf_id IS NOT NULL AND stato_ddt_emesso_id IS NOT NULL
   FROM tmp_refs_pdf),
  '1) riferimenti minimi disponibili');

-- Ordine CONFERMATO + riga, poi evasione full -> DDT in DRAFT.
CREATE TEMP TABLE tmp_ord_pdf AS
WITH ins AS (
  INSERT INTO vendite.ordini (
    soggetto_ruolo_id, billing_account_id, stato_doc_ordine_id,
    valuta_id, data, fatturazione_trigger, emittente_fiscale_id, storicizza, meta)
  SELECT r.soggetto_ruolo_id, r.billing_account_id, r.stato_ord_conf_id,
         r.valuta_id, DATE '2026-07-05', 'SPEDITO', r.emittente_fiscale_id, false,
         jsonb_build_object('test_scope','pgtap_pdf_capability')
  FROM tmp_refs_pdf r
  WHERE r.billing_account_id IS NOT NULL
  RETURNING id)
SELECT * FROM ins;

INSERT INTO vendite.ordini_righe (
  ordine_id, riga_nr, articolo_id, descrizione,
  qta_operativa, quantita, prezzo_unitario, iva_id, attivo, storicizza, meta)
SELECT o.id, 1, r.articolo_id, 'Riga pdf capability',
       5.000000, 5.000000, 10.000000, r.iva_id, true, false,
       jsonb_build_object('test_scope','pgtap_pdf_capability')
FROM tmp_ord_pdf o, tmp_refs_pdf r
WHERE EXISTS (SELECT 1 FROM tmp_ord_pdf);

CREATE TEMP TABLE tmp_ddt_pdf AS
SELECT vendite.fn_genera_ddt_da_ordine((SELECT id FROM tmp_ord_pdf)) AS ddt_id
 WHERE EXISTS (SELECT 1 FROM tmp_ord_pdf);

-- 2) DDT DRAFT -> pdf.mode = PREVIEW
SELECT ok(
  (script.fn_available_actions_ddt((SELECT ddt_id FROM tmp_ddt_pdf))->'pdf'->>'mode') = 'PREVIEW'
  OR (SELECT billing_account_id IS NULL FROM tmp_refs_pdf),
  '2) DDT DRAFT -> pdf.mode = PREVIEW');

-- 3) DDT DRAFT -> pdf.allow_allegati = false
SELECT ok(
  (script.fn_available_actions_ddt((SELECT ddt_id FROM tmp_ddt_pdf))->'pdf'->>'allow_allegati') = 'false'
  OR (SELECT billing_account_id IS NULL FROM tmp_refs_pdf),
  '3) DDT DRAFT -> pdf.allow_allegati = false');

-- 4) blocco pdf presente come oggetto con entrambe le chiavi
SELECT ok(
  (SELECT (script.fn_available_actions_ddt((SELECT ddt_id FROM tmp_ddt_pdf))->'pdf') ? 'mode'
      AND (script.fn_available_actions_ddt((SELECT ddt_id FROM tmp_ddt_pdf))->'pdf') ? 'allow_allegati')
  OR (SELECT billing_account_id IS NULL FROM tmp_refs_pdf),
  '4) blocco pdf presente con chiavi mode + allow_allegati');

-- 5) DDT EMESSO -> pdf.mode = ARCHIVE (proiezione segue lo stato)
-- Causale di trasporto obbligatoria all'emissione dal 2026-07-18
-- (step 5b / DL-28, trg_ddt_a10_guard_causale_emissione_upd): con causale
-- VENDITA (fatturabile) serve anche il prezzo risolvibile, garantito dalla
-- riga d'ordine (prezzo 10) ereditata via fulfillment.
UPDATE vendite.ddt SET causale_trasporto_id = (SELECT causale_vendita_id FROM tmp_refs_pdf)
 WHERE id = (SELECT ddt_id FROM tmp_ddt_pdf);

-- Guard indirizzi obbligatori (DDT): il CON e' obbligatorio all'emissione
-- (trg_ddt_a10_guard_indirizzi_obbligatori_upd).
INSERT INTO vendite.ddt_indirizzi (ddt_id, tipo_indirizzo_id, snapshot)
SELECT (SELECT ddt_id FROM tmp_ddt_pdf),
       (SELECT id FROM config.tipi_indirizzi WHERE codice_interno = 'CON'),
       '{"display":"CON test"}'::jsonb
ON CONFLICT DO NOTHING;

UPDATE vendite.ddt SET stato_doc_ddt_id = (SELECT stato_ddt_emesso_id FROM tmp_refs_pdf)
 WHERE id = (SELECT ddt_id FROM tmp_ddt_pdf);

SELECT ok(
  (script.fn_available_actions_ddt((SELECT ddt_id FROM tmp_ddt_pdf))->'pdf'->>'mode') = 'ARCHIVE'
  OR (SELECT billing_account_id IS NULL FROM tmp_refs_pdf),
  '5) DDT EMESSO -> pdf.mode = ARCHIVE (proiezione stato->capability)');

SELECT * FROM finish();
ROLLBACK;
