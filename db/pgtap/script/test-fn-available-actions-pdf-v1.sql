-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- rev 2026-10-25 (brief-db-pgtap-bolla-e-reso-costruiti, giro 1): la bolla da ordine dal builder dbops.fn_pgtap_crea_ddt_da_ordine (in bozza), l'emissione da dbops.fn_pgtap_porta_a_stato; niente resta scritto a mano.
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

-- ⛔ rev 2026-10-13: il mondo si COSTRUISCE (su un DB ricostruito anagrafiche e
--   articoli sono vuoti). Prima BA, ruolo, «il primo emittente» e articolo si
--   pescavano col LIMIT 1: su zeroerp_ci erano NULL, la fixture restava vuota e
--   la riga di ddt_indirizzi (ddt_id NULL) moriva sulla RLS. Ora un'azienda
--   nuova col suo operatore — il contesto passa su di lui, e da qui vale per
--   tutto il file — il cliente legato a lei (dbops.fn_pgtap_crea_mondo_cliente)
--   e un articolo merce non gestito. Modello: test-ddt-magazzino-testata-v1.
CREATE TEMP TABLE _az AS SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _az)); END $ctx$;
CREATE TEMP TABLE _m AS SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('pgTAP pdf capability');

CREATE TEMP TABLE tmp_refs_pdf AS
SELECT
  m.billing_account_id,
  dbops.fn_pgtap_crea_articolo('PGTAP-PDF-CAPAB', false) AS articolo_id,
  (SELECT s.id FROM config.stati_doc_ordini s
    WHERE s.codice_interno = 'CONFERMATO' AND s.attivo IS TRUE ORDER BY s.id LIMIT 1) AS stato_ord_conf_id,
  (SELECT s.id FROM config.stati_doc_ddt s
    WHERE s.codice_interno = 'EMESSO' AND s.attivo IS TRUE ORDER BY s.id LIMIT 1)     AS stato_ddt_emesso_id
FROM _m m;

SELECT ok(
  (SELECT billing_account_id IS NOT NULL AND articolo_id IS NOT NULL
      AND stato_ord_conf_id IS NOT NULL AND stato_ddt_emesso_id IS NOT NULL
   FROM tmp_refs_pdf),
  '1) riferimenti minimi disponibili');

-- La bolla in bozza dal builder: ordine del cliente del file (trigger SPEDITO,
-- una riga di 5 a 10), evaso tutto. Causale e CON li scrive gia' il builder:
-- servono all'emissione del test 5, e in bozza il pdf non li guarda.
CREATE TEMP TABLE tmp_ddt_pdf AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('pgtap_pdf_capability', 'DRAFT',
         p_billing_account_id   => (SELECT billing_account_id FROM tmp_refs_pdf),
         p_articolo_id          => (SELECT articolo_id FROM tmp_refs_pdf),
         p_quantita             => 5,
         p_prezzo               => 10,
         p_fatturazione_trigger => 'SPEDITO');

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
-- L'emissione per la matrice, sotto i guard veri (causale, CON, prezzo dalla
-- riga d'ordine ereditato via fulfillment).
SELECT dbops.fn_pgtap_porta_a_stato('vendite.ddt', (SELECT ddt_id FROM tmp_ddt_pdf), 'EMESSO');

SELECT ok(
  (script.fn_available_actions_ddt((SELECT ddt_id FROM tmp_ddt_pdf))->'pdf'->>'mode') = 'ARCHIVE'
  OR (SELECT billing_account_id IS NULL FROM tmp_refs_pdf),
  '5) DDT EMESSO -> pdf.mode = ARCHIVE (proiezione stato->capability)');

SELECT * FROM finish();
ROLLBACK;
