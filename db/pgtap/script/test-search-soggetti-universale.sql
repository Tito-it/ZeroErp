-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Elenco test (plan 12):
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
-- ------------------------------------------------------------
SELECT plan(15);

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

SELECT * FROM finish();
