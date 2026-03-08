-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: funzioni scope emittente e ruolo sistema
--       script.fn_get_ruolo_sistema,
--       script.fn_get_emittenti_scope,
--       script.fn_check_user_emittente_scope
--
-- Elenco test:
--  1) Riferimento risorse_umane_auth_user presente
--  2) Riferimento emittenti_fiscali (1) presente
--  3) Emittente fittizio (2) diverso da emittente reale (1)
--  4) fn_get_ruolo_sistema: utente esistente → ruolo non NULL
--  5) fn_get_ruolo_sistema: utente inesistente → NULL
--  6) fn_check_user_emittente_scope: NULL user → true (batch)
--  7) fn_check_user_emittente_scope: ADMIN → true qualunque emittente
--  8) fn_check_user_emittente_scope: OPERATIVO senza whitelist → true
--  9) fn_get_emittenti_scope: senza whitelist → NULL
-- 10) Aggiunta whitelist per emittente_1
-- 11) fn_check_user_emittente_scope: emittente_1 in whitelist → true
-- 12) fn_check_user_emittente_scope: emittente_2 non in whitelist → false
-- 13) fn_get_emittenti_scope: con whitelist → array contenente emittente_1
-- ------------------------------------------------------------

BEGIN;

SELECT plan(13);

-- ============================================================
-- 0. Raccolta riferimenti
-- ============================================================

CREATE TEMP TABLE tmp_refs_scope AS
SELECT
    rau.auth_user_id                                   AS user_id,
    rau.ruolo_sistema::text                            AS ruolo_originale
FROM anagrafiche.risorse_umane_auth_user rau
ORDER BY rau.id
LIMIT 1;

-- Forza OPERATIVO per il test (ROLLBACK ripristina)
UPDATE anagrafiche.risorse_umane_auth_user
   SET ruolo_sistema = 'OPERATIVO'
 WHERE auth_user_id = (SELECT user_id FROM tmp_refs_scope);

-- Pulisce eventuali whitelist pre-esistenti per l'utente di test
DELETE FROM config.user_emittenti_fiscali
 WHERE auth_user_id = (SELECT user_id FROM tmp_refs_scope);

CREATE TEMP TABLE tmp_emittenti AS
SELECT
    ef.id       AS emittente_id_1,
    -1::bigint  AS emittente_id_2   -- fittizio: fn_check verifica solo whitelist
FROM anagrafiche.emittenti_fiscali ef
WHERE ef.attivo = true
ORDER BY ef.id
LIMIT 1;

-- 1) Riferimenti presenti
SELECT ok(
    (SELECT user_id FROM tmp_refs_scope) IS NOT NULL,
    'Riferimento risorse_umane_auth_user presente'
);

SELECT ok(
    (SELECT emittente_id_1 FROM tmp_emittenti) IS NOT NULL,
    'Riferimento emittenti_fiscali (1) presente'
);

SELECT ok(
    (SELECT emittente_id_2 FROM tmp_emittenti) IS NOT NULL
    AND (SELECT emittente_id_2 FROM tmp_emittenti) <>
        (SELECT emittente_id_1 FROM tmp_emittenti),
    'Emittente fittizio (2) diverso da emittente reale (1)'
);

-- ============================================================
-- 1. fn_get_ruolo_sistema
-- ============================================================

-- 4) Utente esistente → ruolo non NULL
SELECT ok(
    script.fn_get_ruolo_sistema(
        (SELECT user_id FROM tmp_refs_scope)
    ) IS NOT NULL,
    'fn_get_ruolo_sistema: utente esistente ritorna ruolo non NULL'
);

-- 5) Utente inesistente → NULL
SELECT is(
    script.fn_get_ruolo_sistema(99999999),
    NULL::config.ruolo_sistema,
    'fn_get_ruolo_sistema: utente inesistente ritorna NULL'
);

-- ============================================================
-- 2. fn_check_user_emittente_scope — casi base
-- ============================================================

-- 6) NULL user_id → true (batch job)
SELECT is(
    script.fn_check_user_emittente_scope(
        NULL,
        (SELECT emittente_id_1 FROM tmp_emittenti)
    ),
    true,
    'fn_check_user_emittente_scope: NULL user → true (batch job)'
);

-- 7) ADMIN → true per qualunque emittente
UPDATE anagrafiche.risorse_umane_auth_user
   SET ruolo_sistema = 'ADMIN'
 WHERE auth_user_id = (SELECT user_id FROM tmp_refs_scope);

SELECT is(
    script.fn_check_user_emittente_scope(
        (SELECT user_id FROM tmp_refs_scope),
        (SELECT emittente_id_1 FROM tmp_emittenti)
    ),
    true,
    'fn_check_user_emittente_scope: ADMIN → true qualunque emittente'
);

-- Ripristina OPERATIVO per i test successivi
UPDATE anagrafiche.risorse_umane_auth_user
   SET ruolo_sistema = 'OPERATIVO'
 WHERE auth_user_id = (SELECT user_id FROM tmp_refs_scope);

-- 8) OPERATIVO senza whitelist → true (nessuna restrizione)
SELECT is(
    script.fn_check_user_emittente_scope(
        (SELECT user_id FROM tmp_refs_scope),
        (SELECT emittente_id_1 FROM tmp_emittenti)
    ),
    true,
    'fn_check_user_emittente_scope: OPERATIVO senza whitelist → true'
);

-- ============================================================
-- 3. fn_get_emittenti_scope — senza whitelist
-- ============================================================

-- 9) Senza whitelist → NULL
SELECT is(
    script.fn_get_emittenti_scope(
        (SELECT user_id FROM tmp_refs_scope)
    ),
    NULL::bigint[],
    'fn_get_emittenti_scope: senza whitelist → NULL'
);

-- ============================================================
-- 4. Aggiunta whitelist e verifica scope
-- ============================================================

-- 10) Aggiunta whitelist per emittente_1
SELECT lives_ok(
    format(
        $$INSERT INTO config.user_emittenti_fiscali
              (auth_user_id, emittente_fiscale_id, meta)
          VALUES (%s, %s,
                  '{"test_scope":"pgtap_fn_check_emittente_scope"}'::jsonb)$$,
        (SELECT user_id FROM tmp_refs_scope),
        (SELECT emittente_id_1 FROM tmp_emittenti)
    ),
    'Whitelist: aggiunta emittente_1 per utente test'
);

-- 11) Emittente_1 in whitelist → true
SELECT is(
    script.fn_check_user_emittente_scope(
        (SELECT user_id FROM tmp_refs_scope),
        (SELECT emittente_id_1 FROM tmp_emittenti)
    ),
    true,
    'fn_check_user_emittente_scope: emittente in whitelist → true'
);

-- 12) Emittente_2 NON in whitelist → false
SELECT is(
    script.fn_check_user_emittente_scope(
        (SELECT user_id FROM tmp_refs_scope),
        (SELECT emittente_id_2 FROM tmp_emittenti)
    ),
    false,
    'fn_check_user_emittente_scope: emittente NON in whitelist → false'
);

-- 13) fn_get_emittenti_scope: array contenente emittente_1
SELECT ok(
    (SELECT emittente_id_1 FROM tmp_emittenti) = ANY(
        script.fn_get_emittenti_scope(
            (SELECT user_id FROM tmp_refs_scope)
        )
    ),
    'fn_get_emittenti_scope: con whitelist → array contiene emittente_1'
);

SELECT * FROM finish();

ROLLBACK;
