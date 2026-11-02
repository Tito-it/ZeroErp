-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test script.fn_search_stradario (ricerca vie per autocomplete):
--   1. Precondizioni: stradario e comuni di test esistono
--   2. Ricerca per comune_id restituisce righe
--   3. Ricerca per p_search restituisce righe
--   4. Ricerca combinata comune_id + p_search
--   5. Verifica colonne chiave nel risultato (stradario_id, toponimo, denominazione)
--   6. Rispetto p_limit
--   7. Errore: nessun criterio (entrambi NULL)
--   8. Errore: p_comune_id <= 0
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

SELECT plan(8);

-- =========================================================
-- Setup: trovare un comune con almeno una via
-- =========================================================
CREATE TEMP TABLE tmp_search_str_ctx (
    test_comune_id    integer,
    test_search_term  text,
    result_count      integer
);

INSERT INTO tmp_search_str_ctx (test_comune_id, test_search_term)
SELECT
    s.comune_id,
    SUBSTRING(sg.indirizzo_normalizzato FROM 1 FOR 5)
FROM config.stradario s
JOIN config.stradario_generale sg ON sg.id = s.stradario_generale_id
WHERE sg.indirizzo_normalizzato IS NOT NULL
  AND LENGTH(sg.indirizzo_normalizzato) >= 5
ORDER BY s.id
LIMIT 1;

-- =========================================================
-- 1) Precondizioni: dati di test esistono
-- =========================================================
SELECT ok(
    (SELECT test_comune_id FROM tmp_search_str_ctx) IS NOT NULL
    AND (SELECT test_search_term FROM tmp_search_str_ctx) IS NOT NULL,
    '1. Comune e termine di ricerca di test trovati'
  );

-- =========================================================
-- 2) Ricerca per comune_id restituisce righe
-- =========================================================
SELECT ok(
    (SELECT count(*) FROM script.fn_search_stradario(
        p_comune_id := (SELECT test_comune_id FROM tmp_search_str_ctx),
        p_limit := 5
    )) > 0,
    '2. Ricerca per comune_id restituisce almeno una riga'
  );

-- =========================================================
-- 3) Ricerca per p_search restituisce righe
-- =========================================================
SELECT ok(
    (SELECT count(*) FROM script.fn_search_stradario(
        p_search := (SELECT test_search_term FROM tmp_search_str_ctx),
        p_limit := 5
    )) > 0,
    '3. Ricerca per p_search restituisce almeno una riga'
  );

-- =========================================================
-- 4) Ricerca combinata comune_id + p_search
-- =========================================================
SELECT lives_ok(
    format(
      $$SELECT * FROM script.fn_search_stradario(
        p_comune_id := %s,
        p_search := %L,
        p_limit := 5
      ) $$,
      (SELECT test_comune_id FROM tmp_search_str_ctx),
      (SELECT test_search_term FROM tmp_search_str_ctx)
    ),
    '4. Ricerca combinata comune_id + p_search senza errori'
  );

-- =========================================================
-- 5) Verifica colonne chiave nel risultato
-- =========================================================
SELECT ok(
    (SELECT r.stradario_id FROM script.fn_search_stradario(
        p_comune_id := (SELECT test_comune_id FROM tmp_search_str_ctx),
        p_limit := 1
    ) r LIMIT 1) IS NOT NULL,
    '5. stradario_id non NULL nel risultato'
  );

-- =========================================================
-- 6) Rispetto p_limit
-- =========================================================
SELECT ok(
    (SELECT count(*) FROM script.fn_search_stradario(
        p_comune_id := (SELECT test_comune_id FROM tmp_search_str_ctx),
        p_limit := 2
    )) <= 2,
    '6. Risultati rispettano p_limit = 2'
  );

-- =========================================================
-- 7) Errore: nessun criterio (entrambi NULL)
-- =========================================================
SELECT throws_matching(
    $$SELECT * FROM script.fn_search_stradario(
      p_comune_id := NULL,
      p_search := NULL
    ) $$,
    'Valorizzare almeno',
    '7. Errore nessun criterio fornito'
  );

-- =========================================================
-- 8) Errore: p_comune_id <= 0
-- =========================================================
SELECT throws_matching(
    $$SELECT * FROM script.fn_search_stradario(
      p_comune_id := -1
    ) $$,
    'p_comune_id deve essere',
    '8. Errore p_comune_id negativo'
  );

SELECT * FROM finish();
ROLLBACK;
