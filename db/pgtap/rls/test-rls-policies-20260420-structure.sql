-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgtap-contesto: escluso — la ragione e' scritta per esteso piu' sotto in
--   questo stesso file. Dichiarazione leggibile dal cancello
--   scripts/guardrail_pgtap_preambolo.py: distingue «escluso apposta» da
--   «dimenticato», che una nota in prosa non fa.
--   ⚠️ Da riguardare: le esclusioni `rls/` furono fatte IN BLOCCO, e almeno
--   una non ne aveva diritto (brief pgtap-runner-rls-baseline §30.2).
-- pgTAP test per Zero ERP
--
-- Test: struttura delle policy RLS create/aggiornate dalle migration
-- 20260420-07 (3 nuove policy shop) e 20260420-08 (4 split policy
-- portale — esclude SHOP_CUSTOMER dal gate originale).
--
-- Simmetrico a test-rls-policies-structure.sql (coverage PR1.5): qui
-- verifichiamo che il modello multi-veste + asimmetria portale/shop
-- (§5.1 guida multi-face v2.0) sia riflesso nelle USING clause.
--
-- Tutte le policy restano DRY-RUN (no ENABLE / FORCE) — l'attivazione
-- e' rinviata post-PR-B stabile.
--
-- Indice test (1..28):
--    Gruppo A — policy shop nuove (07):
--      1-4:   rls_shop_ricevute_self_ownership
--      5-8:   rls_billing_account_shop
--      9-12:  rls_ordini_shop
--    Gruppo B — policy portale aggiornate (08):
--      13-16: rls_billing_account_self_ownership (ricreata, solo CLIENTE_PORTALE)
--      17-20: rls_ordini_cliente_ownership      (ricreata, solo CLIENTE_PORTALE)
--      21-24: rls_fatture_ba_ownership          (ricreata, solo CLIENTE_PORTALE)
--      25-28: rls_fatture_scadenze_ba_ownership (ricreata, solo CLIENTE_PORTALE)
--
-- Per ogni policy i 4 assert sono:
--   .1 policy esiste
--   .2 comando = SELECT
--   .3 permissive = PERMISSIVE
--   .4 USING expression contiene pattern atteso (fn scope + gate ruolo)
--
-- BEGIN; + rollback a fine file (no-op: test sono read-only, ma
-- manteniamo isolamento completo pgTAP).
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

SELECT plan(28);

-- =============================================================
-- GRUPPO A — Policy shop nuove (migration 20260420-07)
-- =============================================================

-- -------- 1-4: rls_shop_ricevute_self_ownership --------
SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_policies
         WHERE schemaname = 'shop' AND tablename = 'ricevute'
           AND policyname = 'rls_shop_ricevute_self_ownership'
    ),
    '1. Policy rls_shop_ricevute_self_ownership esiste su shop.ricevute'
);

SELECT is(
    (SELECT cmd FROM pg_policies
      WHERE schemaname = 'shop' AND tablename = 'ricevute'
        AND policyname = 'rls_shop_ricevute_self_ownership'),
    'SELECT',
    '2. rls_shop_ricevute_self_ownership: comando = SELECT'
);

SELECT is(
    (SELECT permissive FROM pg_policies
      WHERE schemaname = 'shop' AND tablename = 'ricevute'
        AND policyname = 'rls_shop_ricevute_self_ownership'),
    'PERMISSIVE',
    '3. rls_shop_ricevute_self_ownership: PERMISSIVE'
);

SELECT ok(
    (SELECT qual FROM pg_policies
      WHERE schemaname = 'shop' AND tablename = 'ricevute'
        AND policyname = 'rls_shop_ricevute_self_ownership')
    -- Rev 2026-10-21 (20261021-35): la forma col perimetro, nella veste del gate.
    --   Lo schema e' facoltativo: come app `script` e' nel search_path e il
    --   catalogo stampa il nome senza.
    ~ 'SHOP_CUSTOMER.*fn_scope_sr_perimetro\(\( SELECT (script\.)?fn_get_identita_sr_perimetro\(.*ARRAY\[''SHOP_CUSTOMER''.*, soggetto_ruolo_id\)',
    '4. rls_shop_ricevute_self_ownership: USING gate SHOP_CUSTOMER + perimetro del cliente shop'
);

-- -------- 5-8: rls_billing_account_shop --------
SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_policies
         WHERE schemaname = 'anagrafiche' AND tablename = 'billing_account'
           AND policyname = 'rls_billing_account_shop'
    ),
    '5. Policy rls_billing_account_shop esiste su anagrafiche.billing_account'
);

SELECT is(
    (SELECT cmd FROM pg_policies
      WHERE schemaname = 'anagrafiche' AND tablename = 'billing_account'
        AND policyname = 'rls_billing_account_shop'),
    'SELECT',
    '6. rls_billing_account_shop: comando = SELECT'
);

SELECT is(
    (SELECT permissive FROM pg_policies
      WHERE schemaname = 'anagrafiche' AND tablename = 'billing_account'
        AND policyname = 'rls_billing_account_shop'),
    'PERMISSIVE',
    '7. rls_billing_account_shop: PERMISSIVE'
);

SELECT ok(
    (SELECT qual FROM pg_policies
      WHERE schemaname = 'anagrafiche' AND tablename = 'billing_account'
        AND policyname = 'rls_billing_account_shop')
    ~ 'SHOP_CUSTOMER'
    AND (SELECT qual FROM pg_policies
          WHERE schemaname = 'anagrafiche' AND tablename = 'billing_account'
            AND policyname = 'rls_billing_account_shop')
    ~ 'canale_origine.*SHOP|SHOP.*canale_origine',
    '8. rls_billing_account_shop: USING gate SHOP_CUSTOMER + filtro canale_origine=SHOP'
);

-- -------- 9-12: rls_ordini_shop --------
SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_policies
         WHERE schemaname = 'vendite' AND tablename = 'ordini'
           AND policyname = 'rls_ordini_shop'
    ),
    '9. Policy rls_ordini_shop esiste su vendite.ordini'
);

SELECT is(
    (SELECT cmd FROM pg_policies
      WHERE schemaname = 'vendite' AND tablename = 'ordini'
        AND policyname = 'rls_ordini_shop'),
    'SELECT',
    '10. rls_ordini_shop: comando = SELECT'
);

SELECT is(
    (SELECT permissive FROM pg_policies
      WHERE schemaname = 'vendite' AND tablename = 'ordini'
        AND policyname = 'rls_ordini_shop'),
    'PERMISSIVE',
    '11. rls_ordini_shop: PERMISSIVE'
);

SELECT ok(
    (SELECT qual FROM pg_policies
      WHERE schemaname = 'vendite' AND tablename = 'ordini'
        AND policyname = 'rls_ordini_shop')
    ~ 'SHOP_CUSTOMER'
    AND (SELECT qual FROM pg_policies
          WHERE schemaname = 'vendite' AND tablename = 'ordini'
            AND policyname = 'rls_ordini_shop')
    ~ 'canale_origine.*SHOP|SHOP.*canale_origine',
    '12. rls_ordini_shop: USING gate SHOP_CUSTOMER + filtro canale_origine=SHOP'
);

-- =============================================================
-- GRUPPO B — Policy portale aggiornate (migration 20260420-08)
-- =============================================================

-- -------- 13-16: rls_billing_account_self_ownership (ricreata) --------
SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_policies
         WHERE schemaname = 'anagrafiche' AND tablename = 'billing_account'
           AND policyname = 'rls_billing_account_self_ownership'
    ),
    '13. Policy rls_billing_account_self_ownership ancora presente (ricreata per solo CLIENTE_PORTALE)'
);

SELECT is(
    (SELECT cmd FROM pg_policies
      WHERE schemaname = 'anagrafiche' AND tablename = 'billing_account'
        AND policyname = 'rls_billing_account_self_ownership'),
    'SELECT',
    '14. rls_billing_account_self_ownership: comando = SELECT'
);

SELECT is(
    (SELECT permissive FROM pg_policies
      WHERE schemaname = 'anagrafiche' AND tablename = 'billing_account'
        AND policyname = 'rls_billing_account_self_ownership'),
    'PERMISSIVE',
    '15. rls_billing_account_self_ownership: PERMISSIVE'
);

SELECT ok(
    (SELECT qual FROM pg_policies
      WHERE schemaname = 'anagrafiche' AND tablename = 'billing_account'
        AND policyname = 'rls_billing_account_self_ownership')
    ~ 'CLIENTE_PORTALE'
    AND (SELECT qual FROM pg_policies
          WHERE schemaname = 'anagrafiche' AND tablename = 'billing_account'
            AND policyname = 'rls_billing_account_self_ownership')
    !~ 'SHOP_CUSTOMER',
    '16. rls_billing_account_self_ownership: USING gate solo CLIENTE_PORTALE (no SHOP_CUSTOMER)'
);

-- -------- 17-20: rls_ordini_cliente_ownership (ricreata) --------
SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_policies
         WHERE schemaname = 'vendite' AND tablename = 'ordini'
           AND policyname = 'rls_ordini_cliente_ownership'
    ),
    '17. Policy rls_ordini_cliente_ownership ancora presente (ricreata per solo CLIENTE_PORTALE)'
);

SELECT is(
    (SELECT cmd FROM pg_policies
      WHERE schemaname = 'vendite' AND tablename = 'ordini'
        AND policyname = 'rls_ordini_cliente_ownership'),
    'SELECT',
    '18. rls_ordini_cliente_ownership: comando = SELECT'
);

SELECT is(
    (SELECT permissive FROM pg_policies
      WHERE schemaname = 'vendite' AND tablename = 'ordini'
        AND policyname = 'rls_ordini_cliente_ownership'),
    'PERMISSIVE',
    '19. rls_ordini_cliente_ownership: PERMISSIVE'
);

SELECT ok(
    (SELECT qual FROM pg_policies
      WHERE schemaname = 'vendite' AND tablename = 'ordini'
        AND policyname = 'rls_ordini_cliente_ownership')
    ~ 'CLIENTE_PORTALE'
    AND (SELECT qual FROM pg_policies
          WHERE schemaname = 'vendite' AND tablename = 'ordini'
            AND policyname = 'rls_ordini_cliente_ownership')
    !~ 'SHOP_CUSTOMER',
    '20. rls_ordini_cliente_ownership: USING gate solo CLIENTE_PORTALE (no SHOP_CUSTOMER)'
);

-- -------- 21-24: rls_fatture_ba_ownership (ricreata) --------
SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_policies
         WHERE schemaname = 'vendite' AND tablename = 'fatture'
           AND policyname = 'rls_fatture_ba_ownership'
    ),
    '21. Policy rls_fatture_ba_ownership ancora presente (ricreata per solo CLIENTE_PORTALE)'
);

SELECT is(
    (SELECT cmd FROM pg_policies
      WHERE schemaname = 'vendite' AND tablename = 'fatture'
        AND policyname = 'rls_fatture_ba_ownership'),
    'SELECT',
    '22. rls_fatture_ba_ownership: comando = SELECT'
);

SELECT is(
    (SELECT permissive FROM pg_policies
      WHERE schemaname = 'vendite' AND tablename = 'fatture'
        AND policyname = 'rls_fatture_ba_ownership'),
    'PERMISSIVE',
    '23. rls_fatture_ba_ownership: PERMISSIVE'
);

SELECT ok(
    (SELECT qual FROM pg_policies
      WHERE schemaname = 'vendite' AND tablename = 'fatture'
        AND policyname = 'rls_fatture_ba_ownership')
    ~ 'CLIENTE_PORTALE'
    AND (SELECT qual FROM pg_policies
          WHERE schemaname = 'vendite' AND tablename = 'fatture'
            AND policyname = 'rls_fatture_ba_ownership')
    !~ 'SHOP_CUSTOMER',
    '24. rls_fatture_ba_ownership: USING gate solo CLIENTE_PORTALE (shop non vede fatture B2B)'
);

-- -------- 25-28: rls_fatture_scadenze_ba_ownership (ricreata) --------
SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_policies
         WHERE schemaname = 'vendite' AND tablename = 'fatture_scadenze'
           AND policyname = 'rls_fatture_scadenze_ba_ownership'
    ),
    '25. Policy rls_fatture_scadenze_ba_ownership ancora presente (ricreata per solo CLIENTE_PORTALE)'
);

SELECT is(
    (SELECT cmd FROM pg_policies
      WHERE schemaname = 'vendite' AND tablename = 'fatture_scadenze'
        AND policyname = 'rls_fatture_scadenze_ba_ownership'),
    'SELECT',
    '26. rls_fatture_scadenze_ba_ownership: comando = SELECT'
);

SELECT is(
    (SELECT permissive FROM pg_policies
      WHERE schemaname = 'vendite' AND tablename = 'fatture_scadenze'
        AND policyname = 'rls_fatture_scadenze_ba_ownership'),
    'PERMISSIVE',
    '27. rls_fatture_scadenze_ba_ownership: PERMISSIVE'
);

SELECT ok(
    (SELECT qual FROM pg_policies
      WHERE schemaname = 'vendite' AND tablename = 'fatture_scadenze'
        AND policyname = 'rls_fatture_scadenze_ba_ownership')
    ~ 'CLIENTE_PORTALE'
    AND (SELECT qual FROM pg_policies
          WHERE schemaname = 'vendite' AND tablename = 'fatture_scadenze'
            AND policyname = 'rls_fatture_scadenze_ba_ownership')
    !~ 'SHOP_CUSTOMER',
    '28. rls_fatture_scadenze_ba_ownership: USING gate solo CLIENTE_PORTALE (no SHOP_CUSTOMER)'
);

SELECT * FROM finish();
ROLLBACK;
