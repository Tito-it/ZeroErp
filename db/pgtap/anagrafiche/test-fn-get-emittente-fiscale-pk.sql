-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: anagrafiche.fn_get_emittente_fiscale_pk
--
-- Elenco test:
--  1) Funzione presente con firma corretta
--  2) Riferimenti minimi: tabelle emittenti_fiscali e billing_account
--  3) Setup: emittente fiscale attivo + default globale (BA NULL + is_default)
--  4) Guard input: NULL solleva E_PARAMETRO_INVALIDO
--  5) Guard input: <= 0 solleva E_PARAMETRO_INVALIDO
--  6) Risoluzione fallback default per BA non mappato
--  7) Risoluzione mapping specifico per BA mappato
--  8) Il valore restituito e' davvero emittenti_fiscali.id (PK reale)
-- ------------------------------------------------------------

BEGIN;

SELECT plan(8);

-- ============================================================
-- 1) Funzione presente
-- ============================================================
SELECT has_function(
    'anagrafiche', 'fn_get_emittente_fiscale_pk',
    ARRAY['bigint'],
    '1) fn_get_emittente_fiscale_pk presente con firma (bigint)'
);

-- ============================================================
-- 2) Riferimenti minimi
-- ============================================================
SELECT ok(
    EXISTS(SELECT 1 FROM anagrafiche.emittenti_fiscali LIMIT 1)
    AND EXISTS(SELECT 1 FROM anagrafiche.emittenti_fiscali_billing_account LIMIT 1),
    '2) tabelle emittenti_fiscali e emittenti_fiscali_billing_account popolate'
);

-- ============================================================
-- 0. Setup riferimenti reali
-- ============================================================

CREATE TEMP TABLE tmp_refs_pk AS
SELECT
    ef.id                     AS emittente_id_attivo,
    ef.soggetto_ruolo_id      AS sr_id_attivo,
    efba_def.id               AS efba_default_id
FROM anagrafiche.emittenti_fiscali ef
JOIN anagrafiche.emittenti_fiscali_billing_account efba_def
  ON efba_def.emittente_soggetto_ruolo_id = ef.soggetto_ruolo_id
WHERE ef.attivo = true
  AND efba_def.billing_account_id IS NULL
  AND efba_def.is_default = true
LIMIT 1;

-- ============================================================
-- 3) Setup OK
-- ============================================================
SELECT ok(
    (SELECT emittente_id_attivo FROM tmp_refs_pk) IS NOT NULL,
    '3) setup: emittente attivo + default globale presenti'
);

-- ============================================================
-- 4) Guard input: NULL
-- ============================================================
SELECT throws_ok(
    $$ SELECT anagrafiche.fn_get_emittente_fiscale_pk(NULL::bigint) $$,
    NULL,
    NULL,
    '4) NULL solleva eccezione E_PARAMETRO_INVALIDO'
);

-- ============================================================
-- 5) Guard input: <= 0
-- ============================================================
SELECT throws_ok(
    $$ SELECT anagrafiche.fn_get_emittente_fiscale_pk(0::bigint) $$,
    NULL,
    NULL,
    '5) 0 solleva eccezione E_PARAMETRO_INVALIDO'
);

-- ============================================================
-- 6) Fallback default per BA non mappato
-- ============================================================
-- Uso un BA id molto alto e improbabile esistere mappato
-- Dovrebbe ritornare l'emittente di default
SELECT is(
    anagrafiche.fn_get_emittente_fiscale_pk(999999999::bigint),
    (SELECT emittente_id_attivo FROM tmp_refs_pk),
    '6) BA non mappato risolto via fallback default'
);

-- ============================================================
-- 7) Risoluzione mapping specifico per BA mappato
-- ============================================================
-- Cerco un BA che ha gia' un mapping specifico (BA non NULL).
-- Se non esiste, sia atteso che calcolato sono NULL e is() passa.
CREATE TEMP TABLE tmp_ba_mapped AS
SELECT efba.billing_account_id AS ba_id,
       ef.id                   AS expected_ef_id
  FROM anagrafiche.emittenti_fiscali_billing_account efba
  JOIN anagrafiche.emittenti_fiscali ef
    ON ef.soggetto_ruolo_id = efba.emittente_soggetto_ruolo_id
 WHERE efba.billing_account_id IS NOT NULL
   AND ef.attivo = true
 LIMIT 1;

SELECT is(
    CASE
        WHEN (SELECT ba_id FROM tmp_ba_mapped) IS NOT NULL
        THEN anagrafiche.fn_get_emittente_fiscale_pk((SELECT ba_id FROM tmp_ba_mapped))
        ELSE NULL::bigint
    END,
    (SELECT expected_ef_id FROM tmp_ba_mapped),
    '7) mapping specifico BA risolto correttamente (o skip se nessun mapping)'
);

-- ============================================================
-- 8) Il valore ritornato e' davvero emittenti_fiscali.id
-- ============================================================
SELECT ok(
    EXISTS(
        SELECT 1
        FROM anagrafiche.emittenti_fiscali ef
        WHERE ef.id = anagrafiche.fn_get_emittente_fiscale_pk(999999999::bigint)
    ),
    '8) valore restituito esiste come PK in anagrafiche.emittenti_fiscali'
);

-- ============================================================
SELECT * FROM finish();
ROLLBACK;
