-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: capability can_genera_ordine di script.fn_available_actions_preventivo
--       (20260609-07, brief-preventivi-ordini.md D8). L'azione "genera ordine"
--       e' disponibile finche' restano righe natura destinazione_tipo='ORDINE'
--       non allocate (residuo a livello riga).
--
-- Indice test (1..4):
--   1) ACCETTATO con riga MERCE non allocata -> can_genera_ordine = true
--   2) DRAFT -> can_genera_ordine = false, reason PREVENTIVO_NON_ACCETTATO
--   3) dopo il push (riga allocata) -> can_genera_ordine = false
--   4) ...con reason PREVENTIVO_NESSUNA_RIGA_ORDINE
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

SELECT plan(4);

CREATE TEMP TABLE tmp_refs AS
SELECT
  (SELECT ba.id FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL AND ba.istanza_utility_id IS NOT NULL
      AND ba.soggetto_ruolo_id IS NOT NULL ORDER BY ba.id LIMIT 1) AS billing_account_id,
  (SELECT ba.utility_id FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL AND ba.istanza_utility_id IS NOT NULL
      AND ba.soggetto_ruolo_id IS NOT NULL ORDER BY ba.id LIMIT 1) AS utility_id,
  (SELECT ba.istanza_utility_id FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL AND ba.istanza_utility_id IS NOT NULL
      AND ba.soggetto_ruolo_id IS NOT NULL ORDER BY ba.id LIMIT 1) AS istanza_utility_id,
  (SELECT a.id FROM catalogo.articoli a
    WHERE a.attivo IS TRUE AND a.is_composito = FALSE ORDER BY a.id LIMIT 1) AS articolo_id,
  (SELECT s.id FROM config.stati_doc_preventivi s
    WHERE s.codice = 'ACCETTATO' AND s.attivo IS TRUE LIMIT 1) AS stato_accettato_id,
  (SELECT s.id FROM config.stati_doc_preventivi s
    WHERE s.codice = 'DRAFT' AND s.attivo IS TRUE LIMIT 1) AS stato_draft_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1) AS valuta_id,
  (SELECT ef.id FROM anagrafiche.emittenti_fiscali ef WHERE ef.attivo IS TRUE
    ORDER BY ef.id LIMIT 1) AS emittente_fiscale_id,
  (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1) AS iva_id,
  (SELECT id FROM config.nature_vendita WHERE codice_interno = 'MERCE') AS natura_merce_id;

UPDATE catalogo.articoli SET natura_vendita_id = (SELECT natura_merce_id FROM tmp_refs)
 WHERE id = (SELECT articolo_id FROM tmp_refs);

-- Preventivo ACCETTATO + riga MERCE.
CREATE TEMP TABLE tmp_prev AS
WITH ins AS (
  INSERT INTO vendite.preventivi (
    numero, rev, billing_account_id, istanza_utility_id, utility_id,
    validita_dal, validita_al, valuta_id, stato_doc_preventivo_id, data,
    fatturazione_immediata, storicizza, meta, emittente_fiscale_id)
  SELECT 'PGTAP-CAP-ORD', 0, r.billing_account_id, r.istanza_utility_id, r.utility_id,
         DATE '2080-01-01', DATE '2080-12-31', r.valuta_id, r.stato_accettato_id,
         DATE '2080-01-01', false, false,
         jsonb_build_object('test_scope','pgtap_cap_genera_ordine'), r.emittente_fiscale_id
    FROM tmp_refs r
  RETURNING id)
SELECT * FROM ins;

INSERT INTO vendite.preventivi_righe (
    preventivo_id, articolo_id, qta_operativa, prezzo_unitario, iva_id, attivo, meta)
SELECT p.id, r.articolo_id, 3.000000, 12.000000, r.iva_id, true,
       jsonb_build_object('test_scope','pgtap_cap_genera_ordine')
  FROM tmp_prev p, tmp_refs r;

-- Preventivo DRAFT (per test 2).
CREATE TEMP TABLE tmp_prev_draft AS
WITH ins AS (
  INSERT INTO vendite.preventivi (
    numero, rev, billing_account_id, istanza_utility_id, utility_id,
    validita_dal, validita_al, valuta_id, stato_doc_preventivo_id, data,
    fatturazione_immediata, storicizza, meta, emittente_fiscale_id)
  SELECT 'PGTAP-CAP-ORD-DRAFT', 0, r.billing_account_id, r.istanza_utility_id, r.utility_id,
         DATE '2080-01-01', DATE '2080-12-31', r.valuta_id, r.stato_draft_id,
         DATE '2080-01-01', false, false,
         jsonb_build_object('test_scope','pgtap_cap_genera_ordine_draft'), r.emittente_fiscale_id
    FROM tmp_refs r
  RETURNING id)
SELECT * FROM ins;

-- ============================================================
-- 1) ACCETTATO con riga MERCE non allocata -> can_genera_ordine = true
-- ============================================================
SELECT is(
  (SELECT (script.fn_available_actions_preventivo((SELECT id FROM tmp_prev))->>'can_genera_ordine')::boolean),
  true,
  '1) ACCETTATO + riga MERCE non allocata -> can_genera_ordine = true'
);

-- ============================================================
-- 2) DRAFT -> can_genera_ordine = false + reason PREVENTIVO_NON_ACCETTATO
-- ============================================================
SELECT is(
  (SELECT script.fn_available_actions_preventivo((SELECT id FROM tmp_prev_draft))
            ->>'can_genera_ordine_reason'),
  'PREVENTIVO_NON_ACCETTATO',
  '2) DRAFT -> can_genera_ordine = false, reason PREVENTIVO_NON_ACCETTATO'
);

-- Push: alloca la riga MERCE del preventivo ACCETTATO.
SELECT vendite.fn_push_preventivo_a_ordine((SELECT id FROM tmp_prev));

-- ============================================================
-- 3) dopo il push -> can_genera_ordine = false
-- ============================================================
SELECT is(
  (SELECT (script.fn_available_actions_preventivo((SELECT id FROM tmp_prev))->>'can_genera_ordine')::boolean),
  false,
  '3) dopo push (riga allocata) -> can_genera_ordine = false'
);

-- ============================================================
-- 4) ...con reason PREVENTIVO_STATO_CHIUSO
--
-- 🔴 ATTESA AGGIORNATA il 2026-08-18: era PREVENTIVO_NESSUNA_RIGA_ORDINE.
--   Dopo il push il preventivo NON e' piu' aperto: `fn_push_preventivo_a_ordine`
--   lo porta a EVASO. Quindi due cose sono vere insieme — il documento e'
--   chiuso E non ha piu' righe da ordinare — e la capability risponde con la
--   prima, che ha la precedenza.
--   ⭐ Ed e' la risposta giusta: «chiuso» rende irrilevante il conteggio delle
--   righe, mentre «nessuna riga» lascerebbe pensare che basti aggiungerne una.
--   ⚠️ Il test 3 qui sopra continua a garantire la SOSTANZA (`can_genera_ordine
--   = false`); questo garantisce che l'ostacolo sia dichiarato, non quale sia
--   il piu' profondo dei due.
-- ============================================================
SELECT is(
  (SELECT script.fn_available_actions_preventivo((SELECT id FROM tmp_prev))
            ->>'can_genera_ordine_reason'),
  'PREVENTIVO_STATO_CHIUSO',
  '4) dopo push (preventivo EVASO) -> reason PREVENTIVO_STATO_CHIUSO'
);

SELECT * FROM finish();
ROLLBACK;
