-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: script.fn_get_billing_account_by_istanza(istanza_utility_id)
-- Resolver di lettura (no raise): il billing account dell'istanza SE e' uno,
-- NULL se l'istanza ne ha piu' d'uno o l'input non e' valido.
-- ⚠️ rev 2026-10-08 (brief-db-istanza-nasce-col-ba, R-8): leggeva il BA del
--   cliente dell'istanza (LIMIT 1) e dava NULL al «prospect senza cliente»;
--   ora il BA nasce con l'istanza e i clienti sono uno per BA. La funzione e'
--   in ritiro (il backend passa a pratiche.billing_account_id); la gemella
--   fn_get_stato_cliente_by_istanza e' ritirata. Il caso «due BA -> NULL» e'
--   costruito in anagrafiche/test-un-ba-un-cliente-v1.sql.
--
-- Indice test (1..7):
--    1. param NULL              -> NULL
--    2. param 0                 -> NULL
--    3. param negativo (-1)     -> NULL
--    4. istanza inesistente     -> NULL
--    5. istanza con cliente     -> billing_account_id del cliente
--    6. coerenza: il BA ritornato appartiene a quella istanza
--    7. istanza senza cliente -> il suo BA se e' uno, NULL altrimenti
--       (il «prospect senza BA» non esiste piu': rev 2026-10-08)
--
-- 5/6/7 sono data-dependent: skip-safe via OR (no fixture manuale,
-- usa i dati seed/esistenti, pattern test-fn-check-utility-istanza-coerenza).
-- BEGIN; + ROLLBACK finale: nessuna manipolazione persiste.
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
-- 7) istanza senza cliente -> il suo BA se e' uno, NULL altrimenti
--    rev 2026-10-08: il «prospect senza BA» non esiste piu' (il BA nasce con
--    l'istanza), quindi un'istanza senza cliente ha comunque il suo BA.
-- ============================================================
SELECT ok(
    (SELECT count(*) FROM _t_prospect) = 0
    OR script.fn_get_billing_account_by_istanza(
           (SELECT istanza_utility_id FROM _t_prospect)
       ) IS NOT DISTINCT FROM (
           SELECT min(ba.id) FROM anagrafiche.billing_account ba
            WHERE ba.istanza_utility_id = (SELECT istanza_utility_id FROM _t_prospect)
           HAVING count(*) = 1),
    '7. istanza senza cliente -> il suo BA se e'' uno, NULL altrimenti (skip se nessuna)'
);

SELECT * FROM finish();
ROLLBACK;
