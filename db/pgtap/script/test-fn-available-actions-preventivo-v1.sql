-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: script.fn_available_actions_preventivo — meta transizioni e filtro manuale
-- ------------------------------------------------------------
-- Indice test (1..8) — rev 04-08-2026 (ACCETTATO→ANNULLATO RIACCESA dal
-- cantiere «vie d'uscita per l'operatore», 20260804-33/34/35; capability
-- push/ordine gated dal residuo):
-- 1) Preventivo inesistente → NULL
-- 2) Preventivo ACCETTATO (senza righe/BA) → solo 'annulla' (EVASO automatico
--    escluso; push/genera gated dal residuo). Asserito come insieme di chiavi.
-- 3) Preventivo DRAFT, azione ANNULLATO → key='annulla' valorizzato (regressione bug meta={})
-- 4) Preventivo DRAFT, azione ANNULLATO → label_key='vendite.preventivi.azione_annulla' valorizzato
-- 5) Preventivo ACCETTATO senza BA/righe → can_push_commessa=false, reason SENZA_BILLING_ACCOUNT
-- 6) Preventivo DRAFT → 2 azioni manuali (emetti + annulla)
-- 7) Preventivo DRAFT → tutte le azioni hanno key valorizzato (nessun null da meta={})
-- 8) Guard namespace i18n: label_key (da seed) e reason_key (da capability)
--    iniziano per 'vendite.preventivi.' (20260719-14 + seed)
-- ------------------------------------------------------------

BEGIN;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(8);

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
-- TEST 2) Preventivo ACCETTATO (senza righe/BA) → solo 'annulla'
--
--   rev 04-08-2026 — ⚠️ ATTESA CAMBIATA, e non e' una regressione.
--   Fino al 2026-08-04 questo test pretendeva **0 azioni**, con la nota
--   «ACCETTATO→ANNULLATO disattivata (22-05: annulla solo da DRAFT)».
--   Il cantiere *vie d'uscita per l'operatore* (`20260804-33/34/35`,
--   applicato alle 13:25) ha **riacceso** la transizione: la riga
--   ACCETTATO→ANNULLATO di `config.transizioni_stati_preventivi` e'
--   tornata `attivo = true`, perche' dare all'operatore una via d'uscita
--   da ACCETTATO e' esattamente lo scopo di quel cantiere.
--   Il test era rimasto indietro rispetto alla decisione.
--
--   Restano escluse: ACCETTATO→EVASO (manuale=false), push_commessa e
--   genera_ordine (gated dal residuo, che su fixture vuota non c'e').
--
--   ⚠️ Si asserisce l'INSIEME delle chiavi, non il conteggio: un
--   `= 1` sarebbe passato anche con l'azione sbagliata, e questo test
--   e' gia' stato scavalcato una volta da un cambio di dominio.
-- ============================================================
SELECT is(
  (SELECT coalesce(
            jsonb_agg(elem->>'key' ORDER BY elem->>'key'),
            '[]'::jsonb
          )
     FROM tmp_prev_aa_accettato p,
          jsonb_array_elements(
            script.fn_available_actions_preventivo(p.id)->'available_actions'
          ) AS elem
  ),
  '["annulla"]'::jsonb,
  'fn_available_actions_preventivo ACCETTATO senza righe/BA: solo ''annulla'''
);

-- ============================================================
-- TEST 3) Preventivo DRAFT → azione 'annulla' con key valorizzato
--         Regressione diretta del bug meta={}: la CSV aveva meta vuoto
--         (spostata su DRAFT: da ACCETTATO l'annullo non e' piu' ammesso)
-- ============================================================
SELECT ok(
  (SELECT EXISTS (
     SELECT 1
       FROM tmp_prev_aa_draft p,
            jsonb_array_elements(
              script.fn_available_actions_preventivo(p.id)->'available_actions'
            ) AS elem
      WHERE elem->>'key' = 'annulla'
  )),
  'fn_available_actions_preventivo DRAFT: azione key=''annulla'' presente (regressione meta={})'
);

-- ============================================================
-- TEST 4) Preventivo DRAFT → azione 'annulla' con label_key valorizzato
-- ============================================================
SELECT ok(
  (SELECT EXISTS (
     SELECT 1
       FROM tmp_prev_aa_draft p,
            jsonb_array_elements(
              script.fn_available_actions_preventivo(p.id)->'available_actions'
            ) AS elem
      WHERE elem->>'key' = 'annulla'
        AND elem->>'label_key' = 'vendite.preventivi.azione_annulla'
  )),
  'fn_available_actions_preventivo DRAFT: label_key=''vendite.preventivi.azione_annulla'' valorizzato'
);

-- ============================================================
-- TEST 5) Preventivo ACCETTATO senza billing account ne' righe →
--         can_push_commessa=false (rev 12-06-2026: capability con
--         residuo + testata) con reason SENZA_BILLING_ACCOUNT,
--         can_edit_testata=false. I casi positivi (misto, righe
--         eleggibili) sono in test-fn-preventivo-ha-residuo-commessa-v1.
-- ============================================================
SELECT ok(
  (SELECT (script.fn_available_actions_preventivo(p.id)->>'can_push_commessa')::boolean IS FALSE
      AND (script.fn_available_actions_preventivo(p.id)->>'can_push_commessa_reason')
          = 'PREVENTIVO_SENZA_BILLING_ACCOUNT'
      AND (script.fn_available_actions_preventivo(p.id)->>'can_edit_testata')::boolean IS FALSE
     FROM tmp_prev_aa_accettato p
  ),
  'fn_available_actions_preventivo ACCETTATO senza BA/righe: can_push_commessa=false, reason SENZA_BILLING_ACCOUNT'
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

-- ============================================================
-- TEST 8) Guard namespace i18n (20260719-14 + seed).
-- La radice `preventivi.*` e' stata spostata sotto `vendite.preventivi.*`
-- dal FE (brief-i18n-radici-uniformi). Una chiave rimasta piatta non da'
-- errore: da' testo mancante. Qui si copre entrambe le sorgenti che il DB
-- emette: la label_key (dal seed transizioni, via DRAFT) e la reason_key
-- (dal corpo della capability, via ACCETTATO senza BA).
-- ============================================================
SELECT ok(
  (SELECT bool_and(k LIKE 'vendite.preventivi.%')
     FROM (
       -- label_key da seed (azioni del DRAFT)
       SELECT elem->>'label_key' AS k
         FROM tmp_prev_aa_draft p,
              jsonb_array_elements(
                script.fn_available_actions_preventivo(p.id)->'available_actions'
              ) AS elem
        WHERE elem->>'label_key' IS NOT NULL
       UNION ALL
       -- reason_key da capability (push + genera_ordine, ACCETTATO senza BA)
       SELECT script.fn_available_actions_preventivo(p.id)->>'can_push_commessa_reason_key'
         FROM tmp_prev_aa_accettato p
       UNION ALL
       SELECT script.fn_available_actions_preventivo(p.id)->>'can_genera_ordine_reason_key'
         FROM tmp_prev_aa_accettato p
     ) q
    WHERE k IS NOT NULL),
  '8) label_key (seed) e reason_key (capability) sotto vendite.preventivi.*'
);

SELECT * FROM finish();
ROLLBACK;
