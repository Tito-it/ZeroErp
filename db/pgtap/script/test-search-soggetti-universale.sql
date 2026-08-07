-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Elenco test (plan 26):
--  1) Funzione fn_search_soggetti_universale esiste nello schema script
--  2) Funzione fn_get_search_detail esiste nello schema script
--  3) Guard: p_tipo_ruolo_id NULL lancia errore
--  4) Guard: p_tipo_ruolo_id <= 0 lancia errore
--  5) Guard: p_search_term NULL lancia errore
--  6) Guard: p_search_term troppo corto (< 3 caratteri) lancia errore
--  7) Ricerca con termine valido su primo tipo ruolo ritorna senza errori
--  8) Ricerca con termine inesistente ritorna zero righe
--  9) Il campo total_count e' coerente con il numero di righe ritornate
-- 10) Guard fn_get_search_detail: p_soggetto_id NULL lancia errore
-- 11) Guard fn_get_search_detail: p_tipo_ruolo_id NULL lancia errore
-- 12) fn_get_search_detail su soggetto esistente ritorna JSONB con chiave tipo_ruolo
-- 13) fn_get_search_detail: tipo_ruolo nel JSONB corrisponde a codice_interno
-- 14) fn_get_search_detail: p_utility_id NULL non cambia il risultato
-- 15) fn_get_search_detail: righe e' un array JSONB
-- 16) Ricerca per codice soggetto trova il soggetto atteso
-- 17) Ricerca per codice entita' (BA) trova il soggetto CL atteso
-- 18) tipi_ruoli con entita_tabella NOT NULL hanno un regclass valido
-- 19) Ordinamento per soggetto_codice non lancia errore
-- 20) Ordinamento con colonna invalida lancia E_PARAMETRO_INVALIDO
-- 21) Ordinamento DESC non lancia errore
-- 22) Chiamata senza ordinamento (default) funziona come prima
-- 23) Filtro emittente NULL non cambia risultato (fn_search)
-- 24) Filtro emittente array vuoto esclude tutto per CL (fn_search)
-- 25) fn_get_search_detail con p_emittente_ids NULL non lancia errore
-- 26) fn_get_search_detail con p_emittente_ids array vuoto CL: righe vuote
-- ------------------------------------------------------------

-- ⚠️ Transazione, e non e' una formalita'. Il cleanup di questo file sta in
--   coda: col runner vero (pg_prove gira con ON_ERROR_STOP) un fallimento a
--   meta' non ci arriva mai, e i dati di prova restano nel database a rompere
--   la corsa successiva — che vede un rosso non suo.
--   Brief: brief-db-pgtap-runner-rls-baseline §15.3.
BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file diventerebbe verde per sottrazione. Nel DB ce ne sono 365.
--   IMMEDIATE li riporta a scattare a fine di OGNI istruzione — cioe' esatta-
--   mente come si comportavano prima, quando il file girava in autocommit e
--   ogni istruzione era una transazione a se'. In testa e non in coda apposta:
--   in coda scatterebbero tutti insieme DOPO il cleanup, su righe ormai
--   cancellate. Brief: brief-db-pgtap-runner-rls-baseline §17.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(26);

-- =========================================================
-- Setup: recupera dati test dal DB
-- =========================================================

-- Primo tipo ruolo disponibile
CREATE TEMP TABLE tmp_ctx AS
SELECT
  (SELECT id FROM config.tipi_ruoli ORDER BY id LIMIT 1)           AS tipo_ruolo_id,
  (SELECT codice_interno FROM config.tipi_ruoli ORDER BY id LIMIT 1) AS tipo_ruolo_codice;

-- Un soggetto attivo con ruolo per il tipo ruolo scelto
CREATE TEMP TABLE tmp_soggetto AS
SELECT
  s.id AS soggetto_id,
  sr.id AS soggetto_ruolo_id,
  s.ragione_sociale_completa
FROM anagrafiche.soggetti_ruoli sr
  JOIN anagrafiche.soggetti s ON s.id = sr.soggetto_id
WHERE sr.tipo_ruolo_id = (SELECT tipo_ruolo_id FROM tmp_ctx)
  AND s.attivo = true
  AND s.ragione_sociale_completa IS NOT NULL
  AND length(s.ragione_sociale_completa) >= 3
ORDER BY sr.id
LIMIT 1;

-- Termine di ricerca: primi 4 caratteri della ragione_sociale
CREATE TEMP TABLE tmp_search AS
SELECT substring(ragione_sociale_completa FROM 1 FOR 4) AS termine
FROM tmp_soggetto;

-- =========================================================
-- Test 1-2: Esistenza funzioni
-- =========================================================

-- 1) fn_search_soggetti_universale esiste
SELECT has_function(
  'script',
  'fn_search_soggetti_universale',
  'Funzione fn_search_soggetti_universale esiste nello schema script'
);

-- 2) fn_get_search_detail esiste
SELECT has_function(
  'script',
  'fn_get_search_detail',
  'Funzione fn_get_search_detail esiste nello schema script'
);

-- =========================================================
-- Test 3-6: Guard fn_search_soggetti_universale
-- =========================================================

-- 3) Guard: p_tipo_ruolo_id NULL
SELECT throws_ok(
  $$SELECT * FROM script.fn_search_soggetti_universale('test', NULL)$$,
  'P0001',
  NULL,
  'Guard: p_tipo_ruolo_id NULL lancia errore'
);

-- 4) Guard: p_tipo_ruolo_id <= 0
SELECT throws_ok(
  $$SELECT * FROM script.fn_search_soggetti_universale('test', 0)$$,
  'P0001',
  NULL,
  'Guard: p_tipo_ruolo_id <= 0 lancia errore'
);

-- 5) Guard: p_search_term NULL
SELECT throws_ok(
  format(
    $$SELECT * FROM script.fn_search_soggetti_universale(NULL, %s)$$,
    (SELECT tipo_ruolo_id FROM tmp_ctx)
  ),
  'P0001',
  NULL,
  'Guard: p_search_term NULL lancia errore'
);

-- 6) Guard: p_search_term troppo corto
SELECT throws_ok(
  format(
    $$SELECT * FROM script.fn_search_soggetti_universale('ab', %s)$$,
    (SELECT tipo_ruolo_id FROM tmp_ctx)
  ),
  'P0001',
  NULL,
  'Guard: p_search_term troppo corto (< 3 caratteri) lancia errore'
);

-- =========================================================
-- Test 7-9: Esecuzione corretta fn_search_soggetti_universale
-- =========================================================

-- 7) Ricerca con termine valido: nessun errore
SELECT lives_ok(
  format(
    $$SELECT * FROM script.fn_search_soggetti_universale(%L, %s, NULL, 10, 0)$$,
    (SELECT termine FROM tmp_search),
    (SELECT tipo_ruolo_id FROM tmp_ctx)
  ),
  'Ricerca con termine valido su primo tipo ruolo ritorna senza errori'
);

-- 8) Ricerca con termine inesistente: zero righe
SELECT is(
  (
    SELECT count(*)::int
    FROM script.fn_search_soggetti_universale(
      'XYZQWRTNPGTAP999',
      (SELECT tipo_ruolo_id FROM tmp_ctx)
    )
  ),
  0,
  'Ricerca con termine inesistente ritorna zero righe'
);

-- 9) Coerenza total_count con righe ritornate
-- Cerca con termine reale, limita a 5; total_count >= righe ritornate
CREATE TEMP TABLE tmp_result AS
SELECT total_count, soggetto_id
FROM script.fn_search_soggetti_universale(
  (SELECT termine FROM tmp_search),
  (SELECT tipo_ruolo_id FROM tmp_ctx),
  NULL, 5, 0
);

SELECT ok(
  (SELECT COALESCE(
    (SELECT total_count FROM tmp_result LIMIT 1) >= (SELECT count(*) FROM tmp_result),
    true  -- se zero righe, ok
  )),
  'Il campo total_count e'' coerente con il numero di righe ritornate'
);

-- =========================================================
-- Test 10-12: Guard e esecuzione fn_get_search_detail
-- =========================================================

-- 10) Guard: p_soggetto_id NULL
SELECT throws_ok(
  format(
    $$SELECT script.fn_get_search_detail(NULL::uuid, %s)$$,
    (SELECT tipo_ruolo_id FROM tmp_ctx)
  ),
  'P0001',
  NULL,
  'Guard fn_get_search_detail: p_soggetto_id NULL lancia errore'
);

-- 11) Guard: p_tipo_ruolo_id NULL
SELECT throws_ok(
  $$SELECT script.fn_get_search_detail('00000000-0000-0000-0000-000000000001'::uuid, NULL)$$,
  'P0001',
  NULL,
  'Guard fn_get_search_detail: p_tipo_ruolo_id NULL lancia errore'
);

-- 12) Esecuzione su soggetto reale: ritorna JSONB con chiave tipo_ruolo
SELECT ok(
  (
    SELECT (result->>'tipo_ruolo') = (SELECT tipo_ruolo_codice FROM tmp_ctx)
    FROM (
      SELECT script.fn_get_search_detail(
        (SELECT soggetto_id FROM tmp_soggetto),
        (SELECT tipo_ruolo_id FROM tmp_ctx)
      ) AS result
    ) sub
  ),
  'fn_get_search_detail su soggetto esistente ritorna JSONB con chiave tipo_ruolo'
);

-- =========================================================
-- Test 13: tipo_ruolo nel JSONB corrisponde a codice_interno
-- =========================================================

-- Il valore tipo_ruolo nel JSON deve essere codice_interno (es. CL, FO)
-- non codice (es. CLIENTE, FORNITORE)
SELECT ok(
  (
    SELECT (result->>'tipo_ruolo') = (SELECT tipo_ruolo_codice FROM tmp_ctx)
       AND length(result->>'tipo_ruolo') <= 10  -- codice_interno e' breve
    FROM (
      SELECT script.fn_get_search_detail(
        (SELECT soggetto_id FROM tmp_soggetto),
        (SELECT tipo_ruolo_id FROM tmp_ctx)
      ) AS result
    ) sub
  ),
  'fn_get_search_detail: tipo_ruolo nel JSONB corrisponde a codice_interno'
);

-- =========================================================
-- Test 14: p_utility_id NULL non cambia il risultato
-- =========================================================

SELECT is(
  (
    SELECT script.fn_get_search_detail(
      (SELECT soggetto_id FROM tmp_soggetto),
      (SELECT tipo_ruolo_id FROM tmp_ctx),
      NULL
    )
  ),
  (
    SELECT script.fn_get_search_detail(
      (SELECT soggetto_id FROM tmp_soggetto),
      (SELECT tipo_ruolo_id FROM tmp_ctx)
    )
  ),
  'fn_get_search_detail: p_utility_id NULL equivale a chiamata senza parametro'
);

-- =========================================================
-- Test 15: righe e' un array JSONB
-- =========================================================

SELECT ok(
  (
    SELECT jsonb_typeof(result->'righe') = 'array'
    FROM (
      SELECT script.fn_get_search_detail(
        (SELECT soggetto_id FROM tmp_soggetto),
        (SELECT tipo_ruolo_id FROM tmp_ctx)
      ) AS result
    ) sub
  ),
  'fn_get_search_detail: righe e'' un array JSONB'
);

-- =========================================================
-- Test 16: Ricerca per codice soggetto
-- =========================================================

-- Cerca un soggetto per il suo codice (primi 4 char)
CREATE TEMP TABLE tmp_soggetto_codice AS
SELECT s.codice, sr.tipo_ruolo_id
FROM anagrafiche.soggetti s
  JOIN anagrafiche.soggetti_ruoli sr ON sr.soggetto_id = s.id
WHERE s.attivo = true
  AND s.codice IS NOT NULL
  AND length(s.codice) >= 4
ORDER BY sr.id
LIMIT 1;

SELECT ok(
  CASE
    WHEN (SELECT count(*) FROM tmp_soggetto_codice) = 0 THEN true
    ELSE (
      SELECT count(*) > 0
      FROM script.fn_search_soggetti_universale(
        (SELECT substring(codice FROM 1 FOR 4) FROM tmp_soggetto_codice),
        (SELECT tipo_ruolo_id FROM tmp_soggetto_codice)
      )
    )
  END,
  'Ricerca per codice soggetto trova il soggetto atteso (o skip se nessun codice)'
);

-- =========================================================
-- Test 17: Ricerca per codice entita' (BA per CL)
-- =========================================================

-- Cerca un cliente tramite codice billing_account
CREATE TEMP TABLE tmp_ba_codice AS
SELECT ba.codice, sr.tipo_ruolo_id
FROM anagrafiche.clienti cl
  JOIN anagrafiche.billing_account ba ON ba.id = cl.billing_account_id
  JOIN anagrafiche.soggetti_ruoli sr ON sr.id = cl.soggetto_ruolo_id
  JOIN anagrafiche.soggetti s ON s.id = sr.soggetto_id
  JOIN config.tipi_ruoli tr ON tr.id = sr.tipo_ruolo_id
WHERE tr.codice_interno = 'CL'
  AND s.attivo = true
  AND ba.codice IS NOT NULL
  AND length(ba.codice) >= 3
ORDER BY cl.id
LIMIT 1;

SELECT ok(
  CASE
    WHEN (SELECT count(*) FROM tmp_ba_codice) = 0 THEN true
    ELSE (
      SELECT count(*) > 0
      FROM script.fn_search_soggetti_universale(
        (SELECT codice FROM tmp_ba_codice),
        (SELECT tipo_ruolo_id FROM tmp_ba_codice)
      )
    )
  END,
  'Ricerca per codice BA trova il soggetto CL atteso (o skip se nessun BA)'
);

-- =========================================================
-- Test 18: Coerenza entita_tabella in tipi_ruoli
-- =========================================================

SELECT ok(
  COALESCE(
    (
      SELECT bool_and(to_regclass(entita_tabella) IS NOT NULL)
      FROM config.tipi_ruoli
      WHERE entita_tabella IS NOT NULL
    ),
    true  -- nessun record con entita_tabella, ok
  ),
  'tipi_ruoli con entita_tabella NOT NULL hanno tutti un regclass valido'
);

-- =========================================================
-- Test 19-22: Ordinamento dinamico
-- =========================================================

-- 19) Ordinamento per soggetto_codice non lancia errore
SELECT lives_ok(
  format(
    $$SELECT * FROM script.fn_search_soggetti_universale(%L, %s, NULL, 10, 0, 'soggetto_codice', 'ASC')$$,
    (SELECT termine FROM tmp_search),
    (SELECT tipo_ruolo_id FROM tmp_ctx)
  ),
  'Ordinamento per soggetto_codice non lancia errore'
);

-- 20) Ordinamento con colonna invalida lancia E_PARAMETRO_INVALIDO
SELECT throws_ok(
  format(
    $$SELECT * FROM script.fn_search_soggetti_universale(%L, %s, NULL, 10, 0, 'colonna_falsa', 'ASC')$$,
    (SELECT termine FROM tmp_search),
    (SELECT tipo_ruolo_id FROM tmp_ctx)
  ),
  'P0001',
  NULL,
  'Guard: p_order_by con colonna non in whitelist lancia errore'
);

-- 21) Ordinamento DESC non lancia errore
SELECT lives_ok(
  format(
    $$SELECT * FROM script.fn_search_soggetti_universale(%L, %s, NULL, 10, 0, 'ragione_sociale_completa', 'DESC')$$,
    (SELECT termine FROM tmp_search),
    (SELECT tipo_ruolo_id FROM tmp_ctx)
  ),
  'Ordinamento DESC non lancia errore'
);

-- 22) Chiamata senza parametri ordinamento (default) funziona come prima
SELECT lives_ok(
  format(
    $$SELECT * FROM script.fn_search_soggetti_universale(%L, %s, NULL, 10, 0)$$,
    (SELECT termine FROM tmp_search),
    (SELECT tipo_ruolo_id FROM tmp_ctx)
  ),
  'Chiamata senza ordinamento (default) funziona come prima'
);

-- =========================================================
-- Test 23-24: Filtro scope emittente fn_search_soggetti_universale
-- =========================================================

-- Recupera tipo ruolo CL per test emittente
CREATE TEMP TABLE tmp_cl_ctx AS
SELECT tr.id AS tipo_ruolo_id
FROM config.tipi_ruoli tr
WHERE tr.codice_interno = 'CL'
LIMIT 1;

-- 23) p_emittente_ids NULL non cambia risultato (nessuna restrizione)
SELECT lives_ok(
  format(
    $$SELECT * FROM script.fn_search_soggetti_universale(%L, %s, NULL, 10, 0)$$,
    (SELECT termine FROM tmp_search),
    (SELECT tipo_ruolo_id FROM tmp_ctx)
  ),
  'Filtro emittente NULL non cambia risultato (nessuna restrizione)'
);

-- 24) p_emittente_ids = '{}' (array vuoto) per CL esclude tutto
SELECT ok(
  CASE
    WHEN (SELECT count(*) FROM tmp_cl_ctx) = 0 THEN true
    ELSE (
      SELECT count(*) = 0
      FROM script.fn_search_soggetti_universale(
        (SELECT termine FROM tmp_search),
        (SELECT tipo_ruolo_id FROM tmp_cl_ctx),
        '{}'::bigint[],
        10, 0
      )
    )
  END,
  'Filtro emittente array vuoto per CL esclude tutto'
);

-- =========================================================
-- Test 25-26: Filtro scope emittente fn_get_search_detail
-- =========================================================

-- 25) fn_get_search_detail con p_emittente_ids NULL: nessun errore
SELECT lives_ok(
  format(
    $$SELECT script.fn_get_search_detail(%L::uuid, %s, NULL, NULL)$$,
    (SELECT soggetto_id FROM tmp_soggetto),
    (SELECT tipo_ruolo_id FROM tmp_ctx)
  ),
  'fn_get_search_detail con p_emittente_ids NULL non lancia errore'
);

-- 26) fn_get_search_detail CL con '{}' emittente: righe vuote
SELECT ok(
  CASE
    WHEN (SELECT count(*) FROM tmp_cl_ctx) = 0 THEN true
    ELSE (
      SELECT jsonb_array_length(
        (SELECT script.fn_get_search_detail(
          (SELECT soggetto_id FROM tmp_soggetto),
          (SELECT tipo_ruolo_id FROM tmp_cl_ctx),
          NULL,
          '{}'::bigint[]
        ))->'righe'
      ) = 0
    )
  END,
  'fn_get_search_detail CL con emittente array vuoto: righe vuote'
);

SELECT * FROM finish();

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia nulla dietro di se'. Le DELETE del cleanup restano
-- perche' dove sono un'asserzione devono girare davvero.
ROLLBACK;
