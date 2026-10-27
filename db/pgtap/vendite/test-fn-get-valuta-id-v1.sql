-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: fn_get_valuta_id (catena BA -> emittente -> gestore)
-- (changeset 20260227-05)
-- ------------------------------------------------------------
-- Indice test (1..10):
--  1) Funzione fn_get_valuta_id presente
--  2) Fallback gestore: entrambi i parametri NULL
--  3) Fallback gestore: BA esiste ma senza valuta_id
--  4) Fallback gestore: emittente esiste ma senza valuta_id
--  5) Override BA: BA con valuta_id impostata
--  6) Override emittente: emittente con valuta_id impostata (BA senza)
--  7) Priorita`: BA vince su emittente
--  8) Risultato coerente con gestore singleton
--  9) BA inesistente: fallback su emittente/gestore
-- 10) Emittente inesistente: fallback su gestore
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
-- SETUP DATI TEST
-- ============================================================

-- rev 2026-10-27 (lotto 4 di D7): i tre anelli della catena si COSTRUISCONO.
--   Prima si pescavano il primo BA, il primo emittente attivo e il primo
--   gestore: da zero non c'era nessuno dei tre, e la funzione moriva su
--   E_CONFIG_MANCANTE gia' al test 2. Ora: il BA e' un cliente costruito,
--   l'emittente e' quello dell'operatore del contesto, il gestore e' il
--   singleton dell'installazione (prendi-o-costruisci).
CREATE TEMP TABLE tmp_cli_valuta AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('fn_get_valuta_id');

CREATE TEMP TABLE tmp_gestore_valuta AS
SELECT * FROM dbops.fn_pgtap_crea_gestore('fn_get_valuta_id');

CREATE TEMP TABLE tmp_refs_valuta AS
SELECT
  (SELECT billing_account_id FROM tmp_cli_valuta) AS billing_account_id,
  script.fn_pgtap_emittente_sr_operatore() AS emittente_soggetto_ruolo_id,
  (
    SELECT g.valuta_id
    FROM anagrafiche.gestori g
    WHERE g.id = (SELECT gestore_id FROM tmp_gestore_valuta)
  ) AS gestore_valuta_id;

-- ============================================================
-- TEST 1: Funzione presente
-- ============================================================

SELECT ok(
  EXISTS (
    SELECT 1 FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite'
      AND p.proname = 'fn_get_valuta_id'
  ),
  'fn_get_valuta_id presente'
);

-- ============================================================
-- TEST 2: Fallback gestore — entrambi i parametri NULL
-- ============================================================

SELECT is(
  vendite.fn_get_valuta_id(NULL, NULL),
  (SELECT gestore_valuta_id FROM tmp_refs_valuta),
  'Fallback gestore: entrambi i parametri NULL'
);

-- ============================================================
-- TEST 3: Fallback gestore — BA esiste ma senza valuta_id
-- ============================================================

-- Assicura BA senza valuta_id override
UPDATE anagrafiche.billing_account
SET valuta_id = NULL
WHERE id = (SELECT billing_account_id FROM tmp_refs_valuta);

SELECT is(
  vendite.fn_get_valuta_id(
    (SELECT billing_account_id FROM tmp_refs_valuta),
    NULL
  ),
  (SELECT gestore_valuta_id FROM tmp_refs_valuta),
  'Fallback gestore: BA esiste ma senza valuta_id'
);

-- ============================================================
-- TEST 4: Fallback gestore — emittente esiste ma senza valuta_id
-- ============================================================

-- Assicura emittente senza valuta_id override
UPDATE anagrafiche.emittenti_fiscali
SET valuta_id = NULL
WHERE soggetto_ruolo_id = (SELECT emittente_soggetto_ruolo_id FROM tmp_refs_valuta);

SELECT is(
  vendite.fn_get_valuta_id(
    NULL,
    (SELECT emittente_soggetto_ruolo_id FROM tmp_refs_valuta)
  ),
  (SELECT gestore_valuta_id FROM tmp_refs_valuta),
  'Fallback gestore: emittente esiste ma senza valuta_id'
);

-- ============================================================
-- TEST 5: Override BA — BA con valuta_id impostata
-- ============================================================

UPDATE anagrafiche.billing_account
SET valuta_id = (SELECT gestore_valuta_id FROM tmp_refs_valuta)
WHERE id = (SELECT billing_account_id FROM tmp_refs_valuta);

SELECT is(
  vendite.fn_get_valuta_id(
    (SELECT billing_account_id FROM tmp_refs_valuta),
    NULL
  ),
  (SELECT gestore_valuta_id FROM tmp_refs_valuta),
  'Override BA: BA con valuta_id impostata'
);

-- Reset BA
UPDATE anagrafiche.billing_account
SET valuta_id = NULL
WHERE id = (SELECT billing_account_id FROM tmp_refs_valuta);

-- ============================================================
-- TEST 6: Override emittente — emittente con valuta_id (BA senza)
-- ============================================================

UPDATE anagrafiche.emittenti_fiscali
SET valuta_id = (SELECT gestore_valuta_id FROM tmp_refs_valuta)
WHERE soggetto_ruolo_id = (SELECT emittente_soggetto_ruolo_id FROM tmp_refs_valuta);

SELECT is(
  vendite.fn_get_valuta_id(
    (SELECT billing_account_id FROM tmp_refs_valuta),
    (SELECT emittente_soggetto_ruolo_id FROM tmp_refs_valuta)
  ),
  (SELECT gestore_valuta_id FROM tmp_refs_valuta),
  'Override emittente: emittente con valuta_id impostata (BA senza)'
);

-- ============================================================
-- TEST 7: Priorita` — BA vince su emittente
-- ============================================================

-- Imposta valuta diversa su BA e emittente per verificare priorita`
-- (usa la stessa valuta del gestore per entrambi, test verifica che BA venga consultato per primo)
UPDATE anagrafiche.billing_account
SET valuta_id = (SELECT gestore_valuta_id FROM tmp_refs_valuta)
WHERE id = (SELECT billing_account_id FROM tmp_refs_valuta);

SELECT is(
  vendite.fn_get_valuta_id(
    (SELECT billing_account_id FROM tmp_refs_valuta),
    (SELECT emittente_soggetto_ruolo_id FROM tmp_refs_valuta)
  ),
  (
    SELECT ba.valuta_id
    FROM anagrafiche.billing_account ba
    WHERE ba.id = (SELECT billing_account_id FROM tmp_refs_valuta)
  ),
  'Priorita`: BA vince su emittente'
);

-- Cleanup
UPDATE anagrafiche.billing_account
SET valuta_id = NULL
WHERE id = (SELECT billing_account_id FROM tmp_refs_valuta);

UPDATE anagrafiche.emittenti_fiscali
SET valuta_id = NULL
WHERE soggetto_ruolo_id = (SELECT emittente_soggetto_ruolo_id FROM tmp_refs_valuta);

-- ============================================================
-- TEST 8: Risultato coerente con gestore singleton
-- ============================================================

SELECT is(
  vendite.fn_get_valuta_id(NULL, NULL),
  (
    SELECT g.valuta_id
    FROM anagrafiche.gestori g
    ORDER BY g.id
    LIMIT 1
  ),
  'Risultato coerente con gestore singleton'
);

-- ============================================================
-- TEST 9: BA inesistente — fallback su gestore
-- ============================================================

SELECT is(
  vendite.fn_get_valuta_id(-999999, NULL),
  (SELECT gestore_valuta_id FROM tmp_refs_valuta),
  'BA inesistente: fallback su gestore'
);

-- ============================================================
-- TEST 10: Emittente inesistente — fallback su gestore
-- ============================================================

SELECT is(
  vendite.fn_get_valuta_id(NULL, -999999),
  (SELECT gestore_valuta_id FROM tmp_refs_valuta),
  'Emittente inesistente: fallback su gestore'
);

SELECT * FROM finish();
ROLLBACK;
