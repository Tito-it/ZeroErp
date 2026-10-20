-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13.5-ter, 2d/2e): chiavi del push e ambito degli indirizzi col codice della sorgente.
-- pgTAP test per Zero ERP
-- Test: drop uq_commesse_attivita_src_uid_partial
-- ------------------------------------------------------------
-- Indice test (1..4):
-- 1) Indice uq_commesse_attivita_src_uid_partial non esiste piu`
-- 2) Indice uq_commesse_attivita_commessa_segment esiste (constraint corretto rimasto)
-- 3) Smoke multi-riga: 2 commesse_attivita con stessa sorgente ma segment_key diversi → accettati
-- 4) uq_commesse_sorgenti_src_uid_ruolo ancora attivo (semantica 1-doc → 1-commessa ROOT)
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

-- ============================================================
-- Setup riferimenti minimi
-- ============================================================
CREATE TEMP TABLE tmp_refs_srcuid AS
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
  (SELECT u.id
     FROM catalogo.unita_misura u
    WHERE u.attivo IS TRUE
    ORDER BY u.id LIMIT 1
  ) AS uom_id,
  (SELECT t.id
     FROM config.tipi_doc_fiscale t
    WHERE t.attivo IS TRUE
    ORDER BY t.id LIMIT 1
  ) AS tipo_doc_fiscale_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1) AS valuta_id,
  (SELECT sc.id FROM vendite.stati_commessa sc WHERE sc.attivo IS TRUE ORDER BY sc.id LIMIT 1) AS stato_commessa_id,
  (SELECT s.id FROM config.sorgenti s WHERE s.codice = 'PREVENTIVO' AND s.attivo IS TRUE LIMIT 1) AS sorgente_tipo_id,
  -- uid sorgente fisso deterministico per il test (no collision con dati reali)
  '00000000-0000-0000-0001-000000000099'::uuid AS sorgente_uid_test;

-- ============================================================
-- TEST 1) Indice ridondante non esiste piu`
-- ============================================================
SELECT ok(
  NOT EXISTS (
    SELECT 1
    FROM pg_indexes
    WHERE schemaname = 'vendite'
      AND tablename  = 'commesse_attivita'
      AND indexname  = 'uq_commesse_attivita_src_uid_partial'
  ),
  'uq_commesse_attivita_src_uid_partial non esiste (drop eseguito)'
);

-- ============================================================
-- TEST 2) Indice corretto (commessa_id, segment_key) ancora presente
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1
    FROM pg_indexes
    WHERE schemaname = 'vendite'
      AND tablename  = 'commesse_attivita'
      AND indexname  = 'uq_commesse_attivita_commessa_segment'
  ),
  'uq_commesse_attivita_commessa_segment esiste (constraint corretto rimasto)'
);

-- ============================================================
-- TEST 3) Multi-riga: 2 righe con stessa sorgente ma segment_key diversi
-- Verifica che il drop abiliti il pattern 1 documento → N righe commessa.
-- ============================================================
CREATE TEMP TABLE tmp_commessa_srcuid AS
WITH ins AS (
  -- ⚠️ L'emittente NON si omette. La colonna e' nullable, ma l'unico
  -- scrittore reale (vendite.fn_get_or_create_commessa) la risolve sempre
  -- e su 58 commesse in essere zero hanno NULL: una commessa senza
  -- emittente non e' uno stato del dominio, e con la RLS attiva la policy
  -- rls_commesse_ef_whitelist la respinge (fail-closed sull'SR NULL).
  INSERT INTO vendite.commesse (
    codice, billing_account_id, utility_id, stato_commessa_id,
    emittente_soggetto_ruolo_id
  )
  SELECT
    'PGTAP-SRCUID-' || substr(md5(clock_timestamp()::text), 1, 8),
    r.billing_account_id, r.utility_id, r.stato_commessa_id,
    script.fn_pgtap_emittente_sr_operatore()
  FROM tmp_refs_srcuid r
  RETURNING id
)
SELECT id FROM ins;

SELECT lives_ok(
  $$
    INSERT INTO vendite.commesse_attivita (
      commessa_id, segment_key,
      articolo_id, istanza_utility_id, data_attivita, uom_id, quantita,
      competenza_mese, competenza_dal, competenza_al,
      tipo_doc_fiscale_id, valuta_id, prezzo_snapshot,
      pricing_mode, stato_approvazione, stato_emissione,
      sorgente_tipo_id, sorgente_uid
    )
    SELECT
      (SELECT id FROM tmp_commessa_srcuid),
      'PREVENTIVO:' || r.sorgente_uid_test::text || ':R:' || v.riga::text,
      r.articolo_id, r.istanza_utility_id, DATE '2026-06-01', r.uom_id, 1,
      DATE '2026-06-01', DATE '2026-06-01', DATE '2026-06-30',
      r.tipo_doc_fiscale_id, r.valuta_id, 10.00,
      'FIXED', 'BOZZA', 'NON_EMESSA',
      r.sorgente_tipo_id, r.sorgente_uid_test::text
    FROM tmp_refs_srcuid r
    CROSS JOIN (VALUES (1),(2)) AS v(riga);
  $$,
  'Multi-riga: 2 righe con stessa sorgente_uid ma segment_key diversi → inserimento accettato'
);

-- ============================================================
-- TEST 4) uq_commesse_sorgenti_src_uid_ruolo ancora attivo
-- Verifica che la semantica "1 documento → 1 commessa ROOT" sia preservata.
-- ============================================================
-- NOTA 2026-07-18 (brief-db-guard-sorgente-polimorfa): il guard sorgente
-- valida esistenza e formato della chiave, quindi la sorgente del test e' la
-- commessa REALE del fixture (tipo COMMESSA, chiave canonica id::text) — non
-- piu' l'uuid sintetico, che il guard respingerebbe (E_SORG_NOT_FOUND).
SELECT throws_ok(
  $$
    WITH ids AS (SELECT id FROM tmp_commessa_srcuid),
         refs AS (SELECT s.id AS sorgente_tipo_id FROM config.sorgenti s
                   WHERE s.codice_interno = 'COMMESSA' AND s.attivo IS TRUE LIMIT 1)
    INSERT INTO vendite.commesse_sorgenti (commessa_id, sorgente_tipo_id, sorgente_uid, ruolo_link)
    SELECT ids.id, refs.sorgente_tipo_id, ids.id::text, 'ROOT'
    FROM ids, refs
    UNION ALL
    SELECT ids.id, refs.sorgente_tipo_id, ids.id::text, 'ROOT'
    FROM ids, refs;
  $$,
  '23505',
  NULL,
  'uq_commesse_sorgenti_src_uid_ruolo ancora attivo: duplicato ROOT bloccato'
);

SELECT * FROM finish();
ROLLBACK;
