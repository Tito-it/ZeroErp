-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- ⚠️ rev 2026-10-19 (brief-db-grammatica-unica-documenti, lotto 2b, 20261019-87 … -99):
--   solo il commento: la destinazione della merce e' ORDINE_VENDITA.
-- pgTAP test per Zero ERP
--
-- Test: capability can_genera_ordine di script.fn_available_actions_preventivo
--       (20260609-07, brief-preventivi-ordini.md D8). L'azione "genera ordine"
--       e' disponibile finche' restano righe natura destinazione_tipo='ORDINE_VENDITA'
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

-- ============================================================================
-- rev 2026-09-23 (brief-db-fixture-che-costruiscono-giro-2, lotto 2).
--   Il billing account si PESCAVA («il primo BA con utility, istanza e
--   ruolo»): su un database ricostruito (la CI) non ce n'e' nessuno, e il file
--   moriva al primo INSERT del preventivo (istanza_utility_id NULL) con zero
--   asserzioni eseguite. E l'articolo si pescava dal catalogo e gli si
--   CAMBIAVA la natura: un articolo di qualcun altro, modificato.
--   Ora il cliente viene da dbops.fn_pgtap_crea_mondo_cliente (con il
--   contesto gia' aperto riusa l'azienda di chi agisce: il BA e' legato a
--   quell'emittente) e l'articolo da dbops.fn_pgtap_crea_articolo, con codice
--   unico per corsa. ⛔ Cio' che i builder scrivono si legge in
--   un'istruzione SEPARATA.
-- ============================================================================
CREATE TEMP TABLE tmp_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('cap genera ordine');

CREATE TEMP TABLE tmp_art AS
SELECT dbops.fn_pgtap_crea_articolo(
         ('PGT-CAP-ORD-' || substring(md5(clock_timestamp()::text) from 1 for 12))::varchar,
         p_natura_vendita_id => (SELECT id FROM config.nature_vendita WHERE codice_interno = 'MERCE')
       ) AS articolo_id;

CREATE TEMP TABLE tmp_refs AS
SELECT
  (SELECT billing_account_id FROM tmp_mondo) AS billing_account_id,
  (SELECT utility_id FROM tmp_mondo) AS utility_id,
  (SELECT istanza_utility_id FROM tmp_mondo) AS istanza_utility_id,
  (SELECT articolo_id FROM tmp_art) AS articolo_id,
  (SELECT s.id FROM config.stati_doc_preventivi s
    WHERE s.codice = 'ACCETTATO' AND s.attivo IS TRUE LIMIT 1) AS stato_accettato_id,
  (SELECT s.id FROM config.stati_doc_preventivi s
    WHERE s.codice = 'DRAFT' AND s.attivo IS TRUE LIMIT 1) AS stato_draft_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1) AS valuta_id,
  -- ⛔ L'emittente NON si pesca, si DERIVA (2026-09-23, guida pgTAP §5).
  script.fn_pgtap_emittente_operatore() AS emittente_fiscale_id,
  (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1) AS iva_id;

-- Preventivo ACCETTATO + riga MERCE.
-- ⚠️ rev 2026-10-08 (brief-db-righe-e-componenti-debiti-residui, D-1): la
--   testata nasce DRAFT, prende la riga, poi passa ad ACCETTATO con
--   dbops.fn_pgtap_porta_a_stato — fuori bozza le righe non si scrivono piu'
--   (20261008-91).
CREATE TEMP TABLE tmp_prev AS
WITH ins AS (
  INSERT INTO vendite.preventivi (
    numero, rev, billing_account_id, istanza_utility_id, utility_id,
    validita_dal, validita_al, valuta_id, stato_doc_preventivo_id, data,
    fatturazione_immediata, storicizza, meta, emittente_fiscale_id)
  SELECT 'PGTAP-CAP-ORD', 0, r.billing_account_id, r.istanza_utility_id, r.utility_id,
         DATE '2080-01-01', DATE '2080-12-31', r.valuta_id, r.stato_draft_id,
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

DO $x$ BEGIN
  PERFORM dbops.fn_pgtap_porta_a_stato('vendite.preventivi', (SELECT id FROM tmp_prev), 'ACCETTATO');
END $x$;

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
