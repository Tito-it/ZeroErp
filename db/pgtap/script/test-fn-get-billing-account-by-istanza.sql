-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: script.fn_get_billing_account_by_istanza(istanza_utility_id)
-- Resolver di lettura (no raise): billing_account_id del cliente attivo
-- per l'istanza, NULL se prospect / input non valido.
-- Specchio di fn_get_stato_cliente_by_istanza.
--
-- Indice test (1..7):
--    1. param NULL              -> NULL
--    2. param 0                 -> NULL
--    3. param negativo (-1)     -> NULL
--    4. istanza inesistente     -> NULL
--    5. istanza con cliente     -> billing_account_id del cliente
--    6. coerenza: il BA ritornato appartiene a quella istanza
--    7. istanza prospect (senza cliente) -> NULL
--
-- 5/6/7 sono data-dependent: skip-safe via OR (no fixture manuale,
-- usa i dati seed/esistenti, pattern test-fn-check-utility-istanza-coerenza).
-- BEGIN; + ROLLBACK finale: nessuna manipolazione persiste.
-- ------------------------------------------------------------

BEGIN;
SELECT plan(7);

-- ============================================================
-- Setup: una coppia (istanza, BA) reale dai clienti esistenti
-- ============================================================
CREATE TEMP TABLE _t_cli AS
SELECT c.istanza_utility_id, c.billing_account_id
  FROM anagrafiche.clienti c
 WHERE c.istanza_utility_id IS NOT NULL
 ORDER BY c.id
 LIMIT 1;

-- Una istanza SENZA cliente (prospect): se esiste
CREATE TEMP TABLE _t_prospect AS
SELECT iu.id AS istanza_utility_id
  FROM anagrafiche.istanze_utilities iu
 WHERE NOT EXISTS (
        SELECT 1 FROM anagrafiche.clienti c
         WHERE c.istanza_utility_id = iu.id
       )
 ORDER BY iu.id
 LIMIT 1;

-- ============================================================
-- 1) param NULL -> NULL
-- ============================================================
SELECT is(
    script.fn_get_billing_account_by_istanza(NULL::bigint),
    NULL::bigint,
    '1. param NULL -> NULL'
);

-- ============================================================
-- 2) param 0 -> NULL (guard input)
-- ============================================================
SELECT is(
    script.fn_get_billing_account_by_istanza(0::bigint),
    NULL::bigint,
    '2. param 0 -> NULL'
);

-- ============================================================
-- 3) param negativo -> NULL (guard input)
-- ============================================================
SELECT is(
    script.fn_get_billing_account_by_istanza(-1::bigint),
    NULL::bigint,
    '3. param negativo -> NULL'
);

-- ============================================================
-- 4) istanza inesistente -> NULL
-- ============================================================
SELECT is(
    script.fn_get_billing_account_by_istanza(
        (SELECT COALESCE(MAX(id), 0) + 999999 FROM anagrafiche.istanze_utilities)
    ),
    NULL::bigint,
    '4. istanza inesistente -> NULL'
);

-- ============================================================
-- 5) istanza con cliente -> billing_account_id del cliente
-- ============================================================
SELECT ok(
    (SELECT count(*) FROM _t_cli) = 0
    OR script.fn_get_billing_account_by_istanza(
           (SELECT istanza_utility_id FROM _t_cli)
       ) = (SELECT billing_account_id FROM _t_cli),
    '5. istanza con cliente -> billing_account_id atteso (skip se nessun cliente fixture)'
);

-- ============================================================
-- 6) coerenza: il BA ritornato appartiene a quella istanza
--    (garanzia strutturale FK fk_clienti_billing_account)
-- ============================================================
SELECT ok(
    (SELECT count(*) FROM _t_cli) = 0
    OR EXISTS (
        SELECT 1
          FROM anagrafiche.billing_account ba
         WHERE ba.id = script.fn_get_billing_account_by_istanza(
                           (SELECT istanza_utility_id FROM _t_cli)
                       )
           AND ba.istanza_utility_id = (SELECT istanza_utility_id FROM _t_cli)
    ),
    '6. il BA ritornato appartiene all''istanza richiesta (skip se nessun cliente fixture)'
);

-- ============================================================
-- 7) istanza prospect (senza cliente) -> NULL
-- ============================================================
SELECT ok(
    (SELECT count(*) FROM _t_prospect) = 0
    OR script.fn_get_billing_account_by_istanza(
           (SELECT istanza_utility_id FROM _t_prospect)
       ) IS NULL,
    '7. istanza prospect (senza cliente) -> NULL (skip se nessuna istanza prospect)'
);

SELECT * FROM finish();
ROLLBACK;
