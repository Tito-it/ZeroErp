-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
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
--  9) Risultato per EF ha campo codice e attivo
-- 10) Risultato per tipo ruolo senza tabella ha meta in righe
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
-- Test 9: EF ha campo codice e attivo
--
-- ⚠️ Asseriva `codice` + `descrizione`. La funzione e' GENERICA:
--    introspeziona config.tipi_ruoli.entita_tabella ed emette tutte le
--    colonne non di sistema, quindi questo test non descriveva un
--    contratto ma la FORMA della tabella. Dal 2026-08-02
--    anagrafiche.emittenti_fiscali.descrizione non esiste piu' (cantiere
--    emittente, Fase 4 / 20260802-22) e la chiave giustamente non compare.
--    Sostituita con `attivo`, che e' della tabella e non e' fra le colonne
--    escluse. Da rileggere se un giorno la lista di esclusione cambia.
-- =========================================================

SELECT ok(
  CASE
    WHEN (SELECT count(*) FROM tmp_sr_ef) = 0 THEN true
    ELSE (
      SELECT (result->'righe'->0) ? 'codice'
         AND (result->'righe'->0) ? 'attivo'
      FROM (
        SELECT script.fn_get_entita_ruolo_detail(
          (SELECT soggetto_ruolo_id FROM tmp_sr_ef)
        ) AS result
      ) sub
    )
  END,
  'Risultato per EF ha campo codice e attivo in righe (o skip se nessun EF)'
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

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia nulla dietro di se'. Le DELETE del cleanup restano
-- perche' dove sono un'asserzione devono girare davvero.
ROLLBACK;
