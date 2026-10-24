-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13.5-ter, 2d/2e): chiavi del push e ambito degli indirizzi col codice della sorgente.
-- rev 2026-10-24 (brief-modello-documento-vendita N-1): i documenti nascono in
--   bozza e si portano avanti con dbops.fn_pgtap_porta_a_stato (prima il
--   preventivo del test 9 nasceva gia' ACCETTATO).
-- pgTAP test per Zero ERP
-- Test: vendite.fn_crea_revisione_preventivo
-- ------------------------------------------------------------
-- Indice test (1..9):
-- 1) Funzione presente
-- 2) Riferimenti minimi disponibili
-- 3) Setup preventivo EMESSO con righe e indirizzi
-- 4) Revisione da EMESSO ammessa: nuova rev in DRAFT
-- 5) Revisione copia righe attive
-- 6) Revisione copia indirizzi
-- 7) Revisione disattiva precedente (vw_preventivi.is_attiva = false)
-- 8) Revisione da DRAFT vietata
-- 9) Revisione da ACCETTATO vietata (rev 03-05-2026: ACCETTATO chiude
--    la negoziazione, non rivisitabile - regola di dominio)
-- 10) anti-regressione: rename codice stati -> revisione risolta per codice_interno
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

SELECT plan(10);

-- ============================================================
-- Setup GUC app.current_user_id: serve a fn_crea_revisione_preventivo
-- per risolvere l'emittente fiscale dell'operatore corrente sulla
-- nuova revisione (modello user-derived rev2). Senza GUC valorizzata
-- il trigger BEFORE INSERT su preventivi solleva
-- E_PREV_EMITTENTE_NON_RISOLTO.
--
-- Pesca un django_user_id che abbia un emittente fiscale assegnato
-- in config.user_emittenti_fiscali (deterministico per il seed).
-- Se nessun user e' configurato, il setup fallisce e il test halta
-- a un punto chiaro (test 4 in throw_ok inatteso).
-- ============================================================
SELECT set_config(
  'app.current_user_id',
  (SELECT uef.auth_user_id::text
     FROM config.user_emittenti_fiscali uef
    ORDER BY uef.auth_user_id LIMIT 1),
  true
);

-- ============================================================
-- 1) Funzione presente
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite'
      AND p.proname = 'fn_crea_revisione_preventivo'
  ),
  '1. fn_crea_revisione_preventivo presente'
);

-- ============================================================
-- 2) Riferimenti minimi
-- ============================================================
CREATE TEMP TABLE tmp_rv_refs AS
SELECT
  (SELECT ba.id
     FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL
      AND ba.istanza_utility_id IS NOT NULL
    ORDER BY ba.id LIMIT 1
  ) AS billing_account_id,
  (SELECT ba.utility_id
     FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL
      AND ba.istanza_utility_id IS NOT NULL
    ORDER BY ba.id LIMIT 1
  ) AS utility_id,
  (SELECT ba.istanza_utility_id
     FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL
      AND ba.istanza_utility_id IS NOT NULL
    ORDER BY ba.id LIMIT 1
  ) AS istanza_utility_id,
  (SELECT a.id
     FROM catalogo.articoli a
    WHERE a.attivo IS TRUE
    ORDER BY a.data_insert DESC NULLS LAST LIMIT 1
  ) AS articolo_id,
  (SELECT s.id FROM config.stati_doc_preventivi s
    WHERE s.codice = 'DRAFT' AND s.attivo IS TRUE LIMIT 1
  ) AS stato_draft_id,
  (SELECT s.id FROM config.stati_doc_preventivi s
    WHERE s.codice = 'EMESSO' AND s.attivo IS TRUE LIMIT 1
  ) AS stato_emesso_id,
  (SELECT s.id FROM config.stati_doc_preventivi s
    WHERE s.codice = 'ACCETTATO' AND s.attivo IS TRUE LIMIT 1
  ) AS stato_accettato_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1
  ) AS valuta_id,
  -- emittente fiscale (richiesto da trigger BEFORE INSERT preventivi
  -- quando GUC app.current_user_id e' vuota - contesto pgTAP).
  (SELECT ef.id FROM anagrafiche.emittenti_fiscali ef
    WHERE ef.attivo IS TRUE
    ORDER BY ef.id LIMIT 1
  ) AS emittente_fiscale_id,
  (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE LIMIT 1
  ) AS iva_id,
  (SELECT a.tipo_indirizzo_id
     FROM config.tipi_indirizzi_allowed a
    WHERE a.ambito = 'PREVENTIVO' AND a.attivo IS TRUE
    LIMIT 1
  ) AS tipo_indirizzo_id;

SELECT ok(
  (SELECT billing_account_id IS NOT NULL
      AND articolo_id IS NOT NULL
      AND stato_draft_id IS NOT NULL
      AND stato_emesso_id IS NOT NULL
      AND stato_accettato_id IS NOT NULL
      AND emittente_fiscale_id IS NOT NULL
   FROM tmp_rv_refs),
  '2. Riferimenti minimi disponibili (DRAFT/EMESSO/ACCETTATO + emittente)'
);

-- ============================================================
-- 3) Setup preventivo EMESSO con righe e indirizzi
-- ⚠️ rev 2026-10-08 (brief-db-righe-e-componenti-debiti-residui, D-1): i
--   preventivi EMESSO di questo file (qui e al test 10) nascono DRAFT,
--   prendono le righe, poi passano a EMESSO con dbops.fn_pgtap_porta_a_stato —
--   fuori bozza le righe non si scrivono piu' (20261008-91).
-- ============================================================
CREATE TEMP TABLE tmp_rv_prev AS
WITH ins AS (
  INSERT INTO vendite.preventivi (
    numero, rev,
    billing_account_id, istanza_utility_id, utility_id,
    validita_dal, validita_al, valuta_id,
    stato_doc_preventivo_id, data,
    emittente_fiscale_id,
    storicizza, meta
  )
  SELECT
    'PGTAP-RV-' || substr(md5(clock_timestamp()::text), 1, 8),
    0,
    r.billing_account_id, r.istanza_utility_id, r.utility_id,
    DATE '2026-06-01', DATE '2026-06-30', r.valuta_id,
    r.stato_draft_id, DATE '2026-06-01',
    r.emittente_fiscale_id,
    false, jsonb_build_object('test_scope', 'pgtap_revisione')
  FROM tmp_rv_refs r
  RETURNING id, uid, numero
)
SELECT * FROM ins;

-- 2 righe attive + 1 inattiva
INSERT INTO vendite.preventivi_righe (
  preventivo_id, articolo_id, qta_operativa, quantita,
  prezzo_unitario, iva_id, attivo, ordine, meta
)
SELECT p.id, r.articolo_id, 10, 10, 100.00, r.iva_id, true, 1,
       jsonb_build_object('test_scope', 'pgtap_revisione', 'riga', 1)
FROM tmp_rv_prev p, tmp_rv_refs r
UNION ALL
SELECT p.id, r.articolo_id, 5, 5, 50.00, r.iva_id, true, 2,
       jsonb_build_object('test_scope', 'pgtap_revisione', 'riga', 2)
FROM tmp_rv_prev p, tmp_rv_refs r
UNION ALL
SELECT p.id, r.articolo_id, 1, 1, 10.00, r.iva_id, false, 3,
       jsonb_build_object('test_scope', 'pgtap_revisione', 'riga', 3)
FROM tmp_rv_prev p, tmp_rv_refs r;

-- 1 indirizzo
INSERT INTO vendite.preventivi_indirizzi (
  preventivo_id, tipo_indirizzo_id, snapshot
)
SELECT p.id, r.tipo_indirizzo_id,
       jsonb_build_object('test', true)
FROM tmp_rv_prev p, tmp_rv_refs r
WHERE r.tipo_indirizzo_id IS NOT NULL;

DO $x$ BEGIN
  PERFORM dbops.fn_pgtap_porta_a_stato('vendite.preventivi', (SELECT id FROM tmp_rv_prev), 'EMESSO');
END $x$;

SELECT ok(
  (SELECT id IS NOT NULL FROM tmp_rv_prev),
  '3. Setup preventivo EMESSO con righe e indirizzi'
);

-- ============================================================
-- 4) Revisione da EMESSO: nuova rev in DRAFT
-- ============================================================
CREATE TEMP TABLE tmp_rv_result AS
SELECT * FROM vendite.fn_crea_revisione_preventivo(
  (SELECT id FROM tmp_rv_prev),
  'pgtap'
);

SELECT ok(
  (SELECT nuova_rev = 1
      AND nuovo_preventivo_id IS NOT NULL
      AND numero = (SELECT numero FROM tmp_rv_prev)
   FROM tmp_rv_result),
  '4. Revisione da EMESSO: rev=1, stesso numero, nuovo id'
);

-- ============================================================
-- 5) Righe copiate: solo le 2 attive (non la inattiva)
-- ============================================================
SELECT ok(
  (SELECT COUNT(*) = 2
   FROM vendite.preventivi_righe pr
   WHERE pr.preventivo_id = (SELECT nuovo_preventivo_id FROM tmp_rv_result)
     AND pr.attivo IS TRUE),
  '5. Revisione copia solo righe attive (2 su 3)'
);

-- ============================================================
-- 6) Indirizzi copiati (stessa quantita' dell'originale)
-- ============================================================
SELECT ok(
  (SELECT COUNT(*) FROM vendite.preventivi_indirizzi
    WHERE preventivo_id = (SELECT nuovo_preventivo_id FROM tmp_rv_result))
  =
  (SELECT COUNT(*) FROM vendite.preventivi_indirizzi
    WHERE preventivo_id = (SELECT id FROM tmp_rv_prev)),
  '6. Revisione copia indirizzi (stesso numero dell''originale)'
);

-- ============================================================
-- 7) Revisione precedente disattivata
-- ============================================================
SELECT ok(
  (SELECT is_attiva = false
   FROM vendite.vw_preventivi
   WHERE id = (SELECT id FROM tmp_rv_prev)),
  '7. Revisione precedente disattivata (vw_preventivi.is_attiva = false; is_revision_attiva droppata 20260515-05)'
);

-- ============================================================
-- 8) Revisione da DRAFT vietata
-- ============================================================
CREATE TEMP TABLE tmp_rv_prev_draft AS
WITH ins AS (
  INSERT INTO vendite.preventivi (
    numero, rev,
    billing_account_id, istanza_utility_id, utility_id,
    validita_dal, validita_al, valuta_id,
    stato_doc_preventivo_id, data,
    emittente_fiscale_id,
    storicizza, meta
  )
  SELECT
    'PGTAP-RVD-' || substr(md5(clock_timestamp()::text), 1, 8),
    0,
    r.billing_account_id, r.istanza_utility_id, r.utility_id,
    DATE '2026-06-01', DATE '2026-06-30', r.valuta_id,
    r.stato_draft_id, DATE '2026-06-01',
    r.emittente_fiscale_id,
    false, jsonb_build_object('test_scope', 'pgtap_revisione')
  FROM tmp_rv_refs r
  RETURNING id, uid, numero
)
SELECT * FROM ins;

SELECT throws_ok(
  format(
    'SELECT * FROM vendite.fn_crea_revisione_preventivo(%s, ''pgtap'')',
    (SELECT id FROM tmp_rv_prev_draft)
  ),
  NULL, NULL,
  '8. Revisione da DRAFT vietata'
);

-- ============================================================
-- 9) Revisione da ACCETTATO vietata (rev 03-05-2026)
--    Setup: nuovo preventivo portato ad ACCETTATO.
--    ⚠️ rev 2026-10-24: nasce DRAFT e va ad ACCETTATO (DRAFT -> EMESSO ->
--    ACCETTATO) con dbops.fn_pgtap_porta_a_stato, sotto i guard veri: senza
--    righe non hanno motivi da sollevare. Prima nasceva gia' ACCETTATO con
--    un INSERT diretto, che il trigger della nascita ora rifiuta.
-- ============================================================
CREATE TEMP TABLE tmp_rv_prev_accettato AS
WITH ins AS (
  INSERT INTO vendite.preventivi (
    numero, rev,
    billing_account_id, istanza_utility_id, utility_id,
    validita_dal, validita_al, valuta_id,
    stato_doc_preventivo_id, data,
    emittente_fiscale_id,
    storicizza, meta
  )
  SELECT
    'PGTAP-RVA-' || substr(md5(clock_timestamp()::text), 1, 8),
    0,
    r.billing_account_id, r.istanza_utility_id, r.utility_id,
    DATE '2026-06-01', DATE '2026-06-30', r.valuta_id,
    r.stato_draft_id, DATE '2026-06-01',
    r.emittente_fiscale_id,
    false, jsonb_build_object('test_scope', 'pgtap_revisione')
  FROM tmp_rv_refs r
  RETURNING id, uid, numero
)
SELECT * FROM ins;

DO $porta$ BEGIN
  PERFORM dbops.fn_pgtap_porta_a_stato('vendite.preventivi', (SELECT id FROM tmp_rv_prev_accettato), 'ACCETTATO');
END $porta$;

SELECT throws_ok(
  format(
    'SELECT * FROM vendite.fn_crea_revisione_preventivo(%s, ''pgtap'')',
    (SELECT id FROM tmp_rv_prev_accettato)
  ),
  'P0001', NULL,
  '9. Revisione da ACCETTATO vietata (E_PREV_REVISIONE_STATO_NON_AMMESSO)'
);

-- ============================================================
-- 10) Anti-regressione codice_interno (analisi-hardcoded-codice §3a #2):
--     rinominando il `codice` (mutabile) degli stati, la creazione revisione
--     DEVE risolvere stato corrente (EMESSO) e DRAFT per `codice_interno`.
--     Col vecchio codice lo stato corrente non risulterebbe 'EMESSO' ->
--     E_PREV_REVISIONE_STATO_NON_AMMESSO. Preventivo EMESSO fresco (numero nuovo,
--     nessuna revisione DRAFT preesistente).
-- ============================================================
CREATE TEMP TABLE tmp_rv_prev_antireg AS
WITH ins AS (
  INSERT INTO vendite.preventivi (
    numero, rev,
    billing_account_id, istanza_utility_id, utility_id,
    validita_dal, validita_al, valuta_id,
    stato_doc_preventivo_id, data,
    emittente_fiscale_id,
    storicizza, meta
  )
  SELECT
    'PGTAP-RVAR-' || substr(md5(clock_timestamp()::text), 1, 8),
    0,
    r.billing_account_id, r.istanza_utility_id, r.utility_id,
    DATE '2026-06-01', DATE '2026-06-30', r.valuta_id,
    r.stato_draft_id, DATE '2026-06-01',
    r.emittente_fiscale_id,
    false, jsonb_build_object('test_scope', 'pgtap_revisione')
  FROM tmp_rv_refs r
  RETURNING id, uid, numero
)
SELECT * FROM ins;

-- Riga attiva con quantita > 0 (copiata dalla revisione)
INSERT INTO vendite.preventivi_righe (
  preventivo_id, articolo_id, qta_operativa, quantita,
  prezzo_unitario, iva_id, attivo, ordine, meta
)
SELECT p.id, r.articolo_id, 10, 10, 100.00, r.iva_id, true, 1,
       jsonb_build_object('test_scope', 'pgtap_revisione')
FROM tmp_rv_prev_antireg p, tmp_rv_refs r;

DO $x$ BEGIN
  PERFORM dbops.fn_pgtap_porta_a_stato('vendite.preventivi', (SELECT id FROM tmp_rv_prev_antireg), 'EMESSO');
END $x$;

-- Rinomina il codice (mutabile) di EMESSO/DRAFT; codice_interno invariato.
UPDATE config.stati_doc_preventivi
   SET codice = codice || '_RENAMED'
 WHERE codice_interno IN ('EMESSO', 'DRAFT');

SELECT lives_ok(
  format(
    'SELECT * FROM vendite.fn_crea_revisione_preventivo(%s, ''pgtap'')',
    (SELECT id FROM tmp_rv_prev_antireg)
  ),
  '10. anti-regressione: rename codice stati -> revisione risolta per codice_interno'
);

-- ============================================================
SELECT * FROM finish();
ROLLBACK;
