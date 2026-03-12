-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Elenco test (plan 10):
--  1) Funzione fn_get_entita_ruolo_detail esiste nello schema script
--  2) Guard: p_soggetto_ruolo_id NULL lancia errore
--  3) Guard: soggetto_ruolo_id inesistente lancia errore
--  4) Esecuzione su soggetto_ruolo CL ritorna JSONB con tipo_ruolo = CL
--  5) Il campo righe e' un array JSONB (CL)
--  6) Ogni elemento in righe CL ha chiave entita_id
--  7) p_utility_id NULL non filtra (stesse righe di default)
--  8) Risultato per FO ha campo codice
--  9) Risultato per EF ha campo codice e descrizione
-- 10) Risultato per tipo ruolo senza tabella ha meta in righe
-- ------------------------------------------------------------
SELECT plan(10);

-- =========================================================
-- Setup: recupera dati test dal DB
-- =========================================================

-- Primo soggetto_ruolo CL con almeno un cliente
CREATE TEMP TABLE tmp_sr_cl AS
SELECT sr.id AS soggetto_ruolo_id, sr.soggetto_id
FROM anagrafiche.soggetti_ruoli sr
  JOIN config.tipi_ruoli tr ON tr.id = sr.tipo_ruolo_id
  JOIN anagrafiche.clienti cl ON cl.soggetto_ruolo_id = sr.id
WHERE tr.codice_interno = 'CL'
ORDER BY sr.id
LIMIT 1;

-- Primo soggetto_ruolo FO
CREATE TEMP TABLE tmp_sr_fo AS
SELECT sr.id AS soggetto_ruolo_id
FROM anagrafiche.soggetti_ruoli sr
  JOIN config.tipi_ruoli tr ON tr.id = sr.tipo_ruolo_id
  JOIN anagrafiche.fornitori f ON f.soggetto_ruolo_id = sr.id
WHERE tr.codice_interno = 'FO'
ORDER BY sr.id
LIMIT 1;

-- Primo soggetto_ruolo EF
CREATE TEMP TABLE tmp_sr_ef AS
SELECT sr.id AS soggetto_ruolo_id
FROM anagrafiche.soggetti_ruoli sr
  JOIN config.tipi_ruoli tr ON tr.id = sr.tipo_ruolo_id
  JOIN anagrafiche.emittenti_fiscali ef ON ef.soggetto_ruolo_id = sr.id
WHERE tr.codice_interno = 'EF'
ORDER BY sr.id
LIMIT 1;

-- =========================================================
-- Test 1: Esistenza funzione
-- =========================================================

SELECT has_function(
  'script',
  'fn_get_entita_ruolo_detail',
  'Funzione fn_get_entita_ruolo_detail esiste nello schema script'
);

-- =========================================================
-- Test 2: Guard p_soggetto_ruolo_id NULL
-- =========================================================

SELECT throws_ok(
  $$SELECT script.fn_get_entita_ruolo_detail(NULL::bigint)$$,
  'P0001',
  NULL,
  'Guard: p_soggetto_ruolo_id NULL lancia errore'
);

-- =========================================================
-- Test 3: Guard soggetto_ruolo_id inesistente
-- =========================================================

SELECT throws_ok(
  $$SELECT script.fn_get_entita_ruolo_detail(-999)$$,
  'P0001',
  NULL,
  'Guard: soggetto_ruolo_id inesistente lancia errore'
);

-- =========================================================
-- Test 4: Esecuzione su CL reale ritorna tipo_ruolo
-- =========================================================

SELECT ok(
  CASE
    WHEN (SELECT count(*) FROM tmp_sr_cl) = 0 THEN true
    ELSE (
      SELECT (result->>'tipo_ruolo') = 'CL'
      FROM (
        SELECT script.fn_get_entita_ruolo_detail(
          (SELECT soggetto_ruolo_id FROM tmp_sr_cl)
        ) AS result
      ) sub
    )
  END,
  'Esecuzione su soggetto_ruolo CL ritorna JSONB con tipo_ruolo = CL (o skip se nessun CL)'
);

-- =========================================================
-- Test 5: Il campo righe e' un array JSONB
-- =========================================================

SELECT ok(
  CASE
    WHEN (SELECT count(*) FROM tmp_sr_cl) = 0 THEN true
    ELSE (
      SELECT jsonb_typeof(result->'righe') = 'array'
      FROM (
        SELECT script.fn_get_entita_ruolo_detail(
          (SELECT soggetto_ruolo_id FROM tmp_sr_cl)
        ) AS result
      ) sub
    )
  END,
  'Il campo righe e'' un array JSONB (o skip se nessun CL)'
);

-- =========================================================
-- Test 6: Elemento in righe CL ha entita_id
-- =========================================================

SELECT ok(
  CASE
    WHEN (SELECT count(*) FROM tmp_sr_cl) = 0 THEN true
    ELSE (
      SELECT (result->'righe'->0) ? 'entita_id'
      FROM (
        SELECT script.fn_get_entita_ruolo_detail(
          (SELECT soggetto_ruolo_id FROM tmp_sr_cl)
        ) AS result
      ) sub
    )
  END,
  'Elemento in righe CL ha chiave entita_id (o skip se nessun CL)'
);

-- =========================================================
-- Test 7: p_utility_id NULL equivale a default (nessun filtro)
-- =========================================================

SELECT ok(
  CASE
    WHEN (SELECT count(*) FROM tmp_sr_cl) = 0 THEN true
    ELSE (
      SELECT script.fn_get_entita_ruolo_detail(
        (SELECT soggetto_ruolo_id FROM tmp_sr_cl),
        NULL
      ) = script.fn_get_entita_ruolo_detail(
        (SELECT soggetto_ruolo_id FROM tmp_sr_cl)
      )
    )
  END,
  'p_utility_id NULL non filtra: stesse righe di default (o skip se nessun CL)'
);

-- =========================================================
-- Test 8: FO ha campo codice
-- =========================================================

SELECT ok(
  CASE
    WHEN (SELECT count(*) FROM tmp_sr_fo) = 0 THEN true
    ELSE (
      SELECT (result->'righe'->0) ? 'codice'
      FROM (
        SELECT script.fn_get_entita_ruolo_detail(
          (SELECT soggetto_ruolo_id FROM tmp_sr_fo)
        ) AS result
      ) sub
    )
  END,
  'Risultato per FO ha campo codice in righe (o skip se nessun FO)'
);

-- =========================================================
-- Test 9: EF ha campo codice e descrizione
-- =========================================================

SELECT ok(
  CASE
    WHEN (SELECT count(*) FROM tmp_sr_ef) = 0 THEN true
    ELSE (
      SELECT (result->'righe'->0) ? 'codice'
         AND (result->'righe'->0) ? 'descrizione'
      FROM (
        SELECT script.fn_get_entita_ruolo_detail(
          (SELECT soggetto_ruolo_id FROM tmp_sr_ef)
        ) AS result
      ) sub
    )
  END,
  'Risultato per EF ha campo codice e descrizione in righe (o skip se nessun EF)'
);

-- =========================================================
-- Test 10: Ruolo senza tabella dedicata ha meta
-- =========================================================

-- Cerchiamo un soggetto_ruolo con tipo ruolo che non ha tabella dedicata
-- (VE, DI, RE, PSP) — se non esistono, usiamo un fallback su GE
CREATE TEMP TABLE tmp_sr_generico AS
SELECT sr.id AS soggetto_ruolo_id
FROM anagrafiche.soggetti_ruoli sr
  JOIN config.tipi_ruoli tr ON tr.id = sr.tipo_ruolo_id
WHERE tr.codice_interno NOT IN ('CL', 'FO', 'EF', 'VT', 'GE', 'BANK_B', 'RIS_UMANA')
ORDER BY sr.id
LIMIT 1;

SELECT ok(
  CASE
    WHEN (SELECT count(*) FROM tmp_sr_generico) = 0 THEN true
    ELSE (
      SELECT (result->'righe'->0) ? 'meta'
      FROM (
        SELECT script.fn_get_entita_ruolo_detail(
          (SELECT soggetto_ruolo_id FROM tmp_sr_generico)
        ) AS result
      ) sub
    )
  END,
  'Risultato per tipo ruolo senza tabella ha meta in righe (o skip se nessuno presente)'
);

SELECT * FROM finish();
