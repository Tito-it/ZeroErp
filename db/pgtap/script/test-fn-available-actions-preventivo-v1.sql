-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: script.fn_available_actions_preventivo — meta transizioni e filtro manuale
-- ------------------------------------------------------------
-- Indice test (1..7):
-- 1) Preventivo inesistente → NULL
-- 2) Preventivo ACCETTATO → 1 sola azione (ANNULLATO; EVASO escluso perché manuale=false)
-- 3) Preventivo ACCETTATO, azione ANNULLATO → key='annulla' valorizzato (regressione bug meta={})
-- 4) Preventivo ACCETTATO, azione ANNULLATO → label_key='preventivi.azione_annulla' valorizzato
-- 5) Preventivo ACCETTATO → can_push_commessa=true, can_edit_testata=false
-- 6) Preventivo DRAFT → 2 azioni manuali (emetti + annulla)
-- 7) Preventivo DRAFT → tutte le azioni hanno key valorizzato (nessun null da meta={})
-- ------------------------------------------------------------

BEGIN;
SELECT plan(7);

-- ============================================================
-- Riferimenti minimi per creare preventivi in pgTAP
-- ============================================================
CREATE TEMP TABLE tmp_refs_aa AS
SELECT
  (SELECT ba.istanza_utility_id
     FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL
      AND ba.istanza_utility_id IS NOT NULL
    ORDER BY ba.id LIMIT 1
  ) AS istanza_utility_id,
  (SELECT ba.utility_id
     FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL
      AND ba.istanza_utility_id IS NOT NULL
    ORDER BY ba.id LIMIT 1
  ) AS utility_id,
  (SELECT v.id
     FROM config.valute v
    ORDER BY v.id LIMIT 1
  ) AS valuta_id,
  (SELECT ef.id
     FROM anagrafiche.emittenti_fiscali ef
    WHERE ef.attivo IS TRUE
    ORDER BY ef.id LIMIT 1
  ) AS emittente_fiscale_id,
  (SELECT s.id
     FROM config.stati_doc_preventivi s
    WHERE s.codice_interno = 'ACCETTATO' AND s.attivo IS TRUE
    LIMIT 1
  ) AS stato_accettato_id,
  (SELECT s.id
     FROM config.stati_doc_preventivi s
    WHERE s.codice_interno = 'DRAFT' AND s.attivo IS TRUE
    LIMIT 1
  ) AS stato_draft_id;

-- Preventivo ACCETTATO (fixture per test 2-5)
CREATE TEMP TABLE tmp_prev_aa_accettato AS
WITH ins AS (
  INSERT INTO vendite.preventivi (
    numero, rev, istanza_utility_id, utility_id,
    validita_dal, validita_al, valuta_id,
    stato_doc_preventivo_id, data, fatturazione_immediata,
    storicizza, meta, emittente_fiscale_id
  )
  SELECT
    'PGTAP-AA-ACCT-' || substr(md5(clock_timestamp()::text), 1, 8),
    0,
    r.istanza_utility_id, r.utility_id,
    DATE '2026-06-01', DATE '2026-06-30', r.valuta_id,
    r.stato_accettato_id, DATE '2026-06-01', false,
    false, '{"test_scope":"pgtap_fn_available_actions"}'::jsonb,
    r.emittente_fiscale_id
  FROM tmp_refs_aa r
  RETURNING id
)
SELECT * FROM ins;

-- Preventivo DRAFT (fixture per test 6-7)
CREATE TEMP TABLE tmp_prev_aa_draft AS
WITH ins AS (
  INSERT INTO vendite.preventivi (
    numero, rev, istanza_utility_id, utility_id,
    validita_dal, validita_al, valuta_id,
    stato_doc_preventivo_id, data, fatturazione_immediata,
    storicizza, meta, emittente_fiscale_id
  )
  SELECT
    'PGTAP-AA-DRF-' || substr(md5(clock_timestamp()::text), 1, 8),
    0,
    r.istanza_utility_id, r.utility_id,
    DATE '2026-06-01', DATE '2026-06-30', r.valuta_id,
    r.stato_draft_id, DATE '2026-06-01', false,
    false, '{"test_scope":"pgtap_fn_available_actions","stato":"draft"}'::jsonb,
    r.emittente_fiscale_id
  FROM tmp_refs_aa r
  RETURNING id
)
SELECT * FROM ins;

-- ============================================================
-- TEST 1) Preventivo inesistente → NULL
-- ============================================================
SELECT is(
  script.fn_available_actions_preventivo(-1),
  NULL,
  'fn_available_actions_preventivo(-1): preventivo inesistente → NULL'
);

-- ============================================================
-- TEST 2) Preventivo ACCETTATO → 1 sola azione (ANNULLATO)
--         La transizione ACCETTATO→EVASO (manuale=false) deve essere esclusa
-- ============================================================
SELECT is(
  (SELECT jsonb_array_length(
           script.fn_available_actions_preventivo(p.id)->'available_actions'
         )
     FROM tmp_prev_aa_accettato p
  ),
  1,
  'fn_available_actions_preventivo ACCETTATO: 1 azione (EVASO automatico escluso)'
);

-- ============================================================
-- TEST 3) Preventivo ACCETTATO → azione ha key='annulla' valorizzato
--         Regressione diretta del bug meta={}: la CSV aveva meta vuoto
-- ============================================================
SELECT is(
  (SELECT script.fn_available_actions_preventivo(p.id)->'available_actions'->0->>'key'
     FROM tmp_prev_aa_accettato p
  ),
  'annulla',
  'fn_available_actions_preventivo ACCETTATO: key=''annulla'' valorizzato (regressione meta={})'
);

-- ============================================================
-- TEST 4) Preventivo ACCETTATO → azione ha label_key valorizzato
-- ============================================================
SELECT is(
  (SELECT script.fn_available_actions_preventivo(p.id)->'available_actions'->0->>'label_key'
     FROM tmp_prev_aa_accettato p
  ),
  'preventivi.azione_annulla',
  'fn_available_actions_preventivo ACCETTATO: label_key=''preventivi.azione_annulla'' valorizzato'
);

-- ============================================================
-- TEST 5) Preventivo ACCETTATO → can_push_commessa=true, can_edit_testata=false
-- ============================================================
SELECT ok(
  (SELECT (script.fn_available_actions_preventivo(p.id)->>'can_push_commessa')::boolean IS TRUE
      AND (script.fn_available_actions_preventivo(p.id)->>'can_edit_testata')::boolean IS FALSE
     FROM tmp_prev_aa_accettato p
  ),
  'fn_available_actions_preventivo ACCETTATO: can_push_commessa=true, can_edit_testata=false'
);

-- ============================================================
-- TEST 6) Preventivo DRAFT → 2 azioni manuali (emetti + annulla)
-- ============================================================
SELECT is(
  (SELECT jsonb_array_length(
           script.fn_available_actions_preventivo(p.id)->'available_actions'
         )
     FROM tmp_prev_aa_draft p
  ),
  2,
  'fn_available_actions_preventivo DRAFT: 2 azioni manuali (emetti + annulla)'
);

-- ============================================================
-- TEST 7) Preventivo DRAFT → tutte le azioni hanno key valorizzato
-- ============================================================
SELECT ok(
  (SELECT bool_and(
           (elem->>'key') IS NOT NULL AND (elem->>'key') <> ''
         )
     FROM tmp_prev_aa_draft p,
          jsonb_array_elements(
            script.fn_available_actions_preventivo(p.id)->'available_actions'
          ) AS elem
  ),
  'fn_available_actions_preventivo DRAFT: tutte le azioni hanno key valorizzato (no null da meta={})'
);

SELECT * FROM finish();
ROLLBACK;
