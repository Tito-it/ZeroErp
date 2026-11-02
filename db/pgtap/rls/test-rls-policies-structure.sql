-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-contesto: escluso — la ragione e' scritta per esteso piu' sotto in
--   questo stesso file. Dichiarazione leggibile dal cancello
--   scripts/guardrail_pgtap_preambolo.py: distingue «escluso apposta» da
--   «dimenticato», che una nota in prosa non fa.
--   ⚠️ Da riguardare: le esclusioni `rls/` furono fatte IN BLOCCO, e almeno
--   una non ne aveva diritto (brief pgtap-runner-rls-baseline §30.2).
-- pgTAP test per Zero ERP
--
-- Test: struttura delle policy RLS create in PR1.5 (§4.9 WIP
-- multi-face-auth, migrations 20260419-62..67).
--
-- Copre §7.1.7 + §7.1.8 del WIP: verifica che le 7 policy siano
-- presenti con il binding corretto a fn_scope_* e il gate corretto
-- sul GUC `app.ruolo_applicativo`. Le policy sono attualmente DORMIENTI
-- (nessun ENABLE ROW LEVEL SECURITY) ma pg_policies le enumera comunque.
--
-- Strategia: sanity strutturale + semantica sull'espressione USING.
-- La correttezza funzionale delle fn_scope_* e' gia' coperta dai test
-- PR1.5 (test-fn-scope-*.sql). La correttezza degli accessi end-to-end
-- (utente vede/non vede con RLS attiva) sara' coperta dai test
-- runtime che verranno scritti dopo l'attivazione RLS in PR-C, quando
-- sara' disponibile un ruolo DB non-BYPASSRLS utilizzabile nei test.
--
-- Tabelle coperte:
--   - vendite.fatture (dual policy: BA + EF_WHITELIST)
--   - vendite.ordini (CLIENTE_OWNERSHIP)
--   - vendite.fatture_scadenze (BA via fattura)
--   - acquisti.ordini (FORNITORE_OWNERSHIP)
--   - acquisti.ddt (FORNITORE_OWNERSHIP)
--   - anagrafiche.billing_account (BA self)
--
-- Indice test (1..28):
--    Esistenza + struttura base (4 test per policy):
--      1-4:   rls_fatture_ba_ownership
--      5-8:   rls_fatture_ef_whitelist
--      9-12:  rls_ordini_cliente_ownership
--      13-16: rls_fatture_scadenze_ba_ownership
--      17-20: rls_acquisti_ordini_fornitore_ownership
--      21-24: rls_acquisti_ddt_fornitore_ownership
--      25-28: rls_billing_account_self_ownership
--
-- Per ogni policy i 4 assert sono:
--   .1  policy esiste
--   .2  comando = SELECT (nessuna policy FOR ALL/INSERT/UPDATE/DELETE)
--   .3  permissive = true (PERMISSIVE per combinazione OR)
--   .4  USING expression contiene la fn_scope attesa + gate ruolo
--
-- BEGIN; + ROLLBACK a fine file (isolamento completo).
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

-- =========================================================
-- Policy 1: rls_fatture_ba_ownership (vendite.fatture, portale/shop)
-- =========================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_policies
         WHERE schemaname = 'vendite' AND tablename = 'fatture'
           AND policyname = 'rls_fatture_ba_ownership'
    ),
    '1. Policy rls_fatture_ba_ownership esiste su vendite.fatture'
);

SELECT is(
    (SELECT cmd FROM pg_policies
      WHERE schemaname = 'vendite' AND tablename = 'fatture'
        AND policyname = 'rls_fatture_ba_ownership'),
    'SELECT',
    '2. rls_fatture_ba_ownership: comando = SELECT'
);

SELECT is(
    (SELECT permissive FROM pg_policies
      WHERE schemaname = 'vendite' AND tablename = 'fatture'
        AND policyname = 'rls_fatture_ba_ownership'),
    'PERMISSIVE',
    '3. rls_fatture_ba_ownership: permissive (OR-combinazione con EF whitelist)'
);

-- Post 20-04-2026 (migration 20260420-08-03): la policy ammette solo
-- CLIENTE_PORTALE (lo shop non vede fatture B2B — vede solo
-- shop.ricevute). Il gate SHOP_CUSTOMER originale e' stato rimosso.
SELECT ok(
    (SELECT qual FROM pg_policies
      WHERE schemaname = 'vendite' AND tablename = 'fatture'
        AND policyname = 'rls_fatture_ba_ownership') ~ 'fn_scope_sr_perimetro\(\( SELECT (script\.)?fn_get_identita_sr_perimetro\(.*fn_resolve_controparte_sr_id\(''billing_account'''
    AND (SELECT qual FROM pg_policies
          WHERE schemaname = 'vendite' AND tablename = 'fatture'
            AND policyname = 'rls_fatture_ba_ownership') ~ 'CLIENTE_PORTALE'
    AND (SELECT qual FROM pg_policies
          WHERE schemaname = 'vendite' AND tablename = 'fatture'
            AND policyname = 'rls_fatture_ba_ownership') !~ 'SHOP_CUSTOMER',
    -- Rev 2026-10-21 (20261021-32): la regola BA_OWNERSHIP nella forma col perimetro.
    '4. rls_fatture_ba_ownership: USING perimetro del cliente + cliente del BA della riga, gate solo CLIENTE_PORTALE (no SHOP_CUSTOMER post 20-04-2026)'
);

-- =========================================================
-- Policy 2: rls_fatture_ef_whitelist (vendite.fatture, operatore)
-- =========================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_policies
         WHERE schemaname = 'vendite' AND tablename = 'fatture'
           AND policyname = 'rls_fatture_ef_whitelist'
    ),
    '5. Policy rls_fatture_ef_whitelist esiste su vendite.fatture'
);

-- Dal 2026-06-03 (migration 20260603-22) la policy operatore copre anche la
-- scrittura: FOR ALL con WITH CHECK (brief RLS Ondata 2 "insert bloccati").
SELECT is(
    (SELECT cmd FROM pg_policies
      WHERE schemaname = 'vendite' AND tablename = 'fatture'
        AND policyname = 'rls_fatture_ef_whitelist'),
    'ALL',
    '6. rls_fatture_ef_whitelist: comando = ALL (copertura scrittura)'
);

SELECT is(
    (SELECT permissive FROM pg_policies
      WHERE schemaname = 'vendite' AND tablename = 'fatture'
        AND policyname = 'rls_fatture_ef_whitelist'),
    'PERMISSIVE',
    '7. rls_fatture_ef_whitelist: permissive'
);

SELECT ok(
    (SELECT qual FROM pg_policies
      WHERE schemaname = 'vendite' AND tablename = 'fatture'
        AND policyname = 'rls_fatture_ef_whitelist') ~ 'fn_scope_ef_perimetro'
    AND (SELECT qual FROM pg_policies
          WHERE schemaname = 'vendite' AND tablename = 'fatture'
            AND policyname = 'rls_fatture_ef_whitelist') ~ 'OPERATORE',
    '8. rls_fatture_ef_whitelist: USING chiama fn_scope_ef_perimetro (rev 2026-10-18) + gate OPERATORE'
);

-- =========================================================
-- Policy 3: rls_ordini_cliente_ownership (vendite.ordini)
-- =========================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_policies
         WHERE schemaname = 'vendite' AND tablename = 'ordini'
           AND policyname = 'rls_ordini_cliente_ownership'
    ),
    '9. Policy rls_ordini_cliente_ownership esiste su vendite.ordini'
);

SELECT is(
    (SELECT cmd FROM pg_policies
      WHERE schemaname = 'vendite' AND tablename = 'ordini'
        AND policyname = 'rls_ordini_cliente_ownership'),
    'SELECT',
    '10. rls_ordini_cliente_ownership: comando = SELECT'
);

SELECT is(
    (SELECT permissive FROM pg_policies
      WHERE schemaname = 'vendite' AND tablename = 'ordini'
        AND policyname = 'rls_ordini_cliente_ownership'),
    'PERMISSIVE',
    '11. rls_ordini_cliente_ownership: permissive'
);

SELECT ok(
    (SELECT qual FROM pg_policies
      WHERE schemaname = 'vendite' AND tablename = 'ordini'
        AND policyname = 'rls_ordini_cliente_ownership') ~ 'fn_scope_sr_perimetro\(\( SELECT (script\.)?fn_get_identita_sr_perimetro\(.*, soggetto_ruolo_id\)'
    AND (SELECT qual FROM pg_policies
          WHERE schemaname = 'vendite' AND tablename = 'ordini'
            AND policyname = 'rls_ordini_cliente_ownership') ~ 'CLIENTE_PORTALE',
    -- Rev 2026-10-21 (20261021-35): la forma col perimetro; l'ordine porta il suo cliente.
    '12. rls_ordini_cliente_ownership: USING perimetro del cliente + soggetto dell''ordine, gate CLIENTE_PORTALE'
);

-- =========================================================
-- Policy 4: rls_fatture_scadenze_ba_ownership (vendite.fatture_scadenze)
-- =========================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_policies
         WHERE schemaname = 'vendite' AND tablename = 'fatture_scadenze'
           AND policyname = 'rls_fatture_scadenze_ba_ownership'
    ),
    '13. Policy rls_fatture_scadenze_ba_ownership esiste su vendite.fatture_scadenze'
);

SELECT is(
    (SELECT cmd FROM pg_policies
      WHERE schemaname = 'vendite' AND tablename = 'fatture_scadenze'
        AND policyname = 'rls_fatture_scadenze_ba_ownership'),
    'SELECT',
    '14. rls_fatture_scadenze_ba_ownership: comando = SELECT'
);

SELECT is(
    (SELECT permissive FROM pg_policies
      WHERE schemaname = 'vendite' AND tablename = 'fatture_scadenze'
        AND policyname = 'rls_fatture_scadenze_ba_ownership'),
    'PERMISSIVE',
    '15. rls_fatture_scadenze_ba_ownership: permissive'
);

SELECT ok(
    (SELECT qual FROM pg_policies
      WHERE schemaname = 'vendite' AND tablename = 'fatture_scadenze'
        AND policyname = 'rls_fatture_scadenze_ba_ownership') ~ 'fn_scope_sr_perimetro\(\( SELECT (script\.)?fn_get_identita_sr_perimetro\(.*fn_resolve_controparte_sr_id\(''fattura''',
    -- Rev 2026-10-21 (20261021-32): era fn_scope_ba_ownership_via_fattura.
    '16. rls_fatture_scadenze_ba_ownership: USING perimetro del cliente + cliente della fattura della riga'
);

-- =========================================================
-- Policy 5: rls_acquisti_ordini_fornitore_ownership (acquisti.ordini)
-- =========================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_policies
         WHERE schemaname = 'acquisti' AND tablename = 'ordini'
           AND policyname = 'rls_acquisti_ordini_fornitore_ownership'
    ),
    '17. Policy rls_acquisti_ordini_fornitore_ownership esiste su acquisti.ordini'
);

SELECT is(
    (SELECT cmd FROM pg_policies
      WHERE schemaname = 'acquisti' AND tablename = 'ordini'
        AND policyname = 'rls_acquisti_ordini_fornitore_ownership'),
    'SELECT',
    '18. rls_acquisti_ordini_fornitore_ownership: comando = SELECT'
);

SELECT is(
    (SELECT permissive FROM pg_policies
      WHERE schemaname = 'acquisti' AND tablename = 'ordini'
        AND policyname = 'rls_acquisti_ordini_fornitore_ownership'),
    'PERMISSIVE',
    '19. rls_acquisti_ordini_fornitore_ownership: permissive'
);

SELECT ok(
    (SELECT qual FROM pg_policies
      WHERE schemaname = 'acquisti' AND tablename = 'ordini'
        AND policyname = 'rls_acquisti_ordini_fornitore_ownership') ~ 'fn_scope_sr_perimetro\(\( SELECT (script\.)?fn_get_identita_sr_perimetro\(.*, soggetto_ruolo_id\)'
    AND (SELECT qual FROM pg_policies
          WHERE schemaname = 'acquisti' AND tablename = 'ordini'
            AND policyname = 'rls_acquisti_ordini_fornitore_ownership') ~ 'FORNITORE_PORTALE',
    -- Rev 2026-10-21 (20261021-43): la forma col perimetro; schema facoltativo (come app non si stampa).
    '20. rls_acquisti_ordini_fornitore_ownership: USING perimetro del fornitore + soggetto dell''ordine, gate FORNITORE_PORTALE'
);

-- =========================================================
-- Policy 6: rls_acquisti_ddt_fornitore_ownership (acquisti.ddt)
-- =========================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_policies
         WHERE schemaname = 'acquisti' AND tablename = 'ddt'
           AND policyname = 'rls_acquisti_ddt_fornitore_ownership'
    ),
    '21. Policy rls_acquisti_ddt_fornitore_ownership esiste su acquisti.ddt'
);

SELECT is(
    (SELECT cmd FROM pg_policies
      WHERE schemaname = 'acquisti' AND tablename = 'ddt'
        AND policyname = 'rls_acquisti_ddt_fornitore_ownership'),
    'SELECT',
    '22. rls_acquisti_ddt_fornitore_ownership: comando = SELECT'
);

SELECT is(
    (SELECT permissive FROM pg_policies
      WHERE schemaname = 'acquisti' AND tablename = 'ddt'
        AND policyname = 'rls_acquisti_ddt_fornitore_ownership'),
    'PERMISSIVE',
    '23. rls_acquisti_ddt_fornitore_ownership: permissive'
);

SELECT ok(
    (SELECT qual FROM pg_policies
      WHERE schemaname = 'acquisti' AND tablename = 'ddt'
        AND policyname = 'rls_acquisti_ddt_fornitore_ownership') ~ 'fn_scope_sr_perimetro\(\( SELECT (script\.)?fn_get_identita_sr_perimetro\(.*, mittente_soggetto_ruolo_id\)'
    AND (SELECT qual FROM pg_policies
          WHERE schemaname = 'acquisti' AND tablename = 'ddt'
            AND policyname = 'rls_acquisti_ddt_fornitore_ownership') ~ 'FORNITORE_PORTALE'
    AND (SELECT qual FROM pg_policies
          WHERE schemaname = 'acquisti' AND tablename = 'ddt'
            AND policyname = 'rls_acquisti_ddt_fornitore_ownership') ~ 'mittente_soggetto_ruolo_id',
    -- Rev 2026-10-21 (20261021-43): la forma col perimetro.
    '24. rls_acquisti_ddt_fornitore_ownership: USING perimetro del fornitore + gate + colonna mittente'
);

-- =========================================================
-- Policy 7: rls_billing_account_self_ownership (anagrafiche.billing_account)
-- =========================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_policies
         WHERE schemaname = 'anagrafiche' AND tablename = 'billing_account'
           AND policyname = 'rls_billing_account_self_ownership'
    ),
    '25. Policy rls_billing_account_self_ownership esiste su anagrafiche.billing_account'
);

SELECT is(
    (SELECT cmd FROM pg_policies
      WHERE schemaname = 'anagrafiche' AND tablename = 'billing_account'
        AND policyname = 'rls_billing_account_self_ownership'),
    'SELECT',
    '26. rls_billing_account_self_ownership: comando = SELECT'
);

SELECT is(
    (SELECT permissive FROM pg_policies
      WHERE schemaname = 'anagrafiche' AND tablename = 'billing_account'
        AND policyname = 'rls_billing_account_self_ownership'),
    'PERMISSIVE',
    '27. rls_billing_account_self_ownership: permissive'
);

-- Post 20-04-2026 (migration 20260420-08-01): solo CLIENTE_PORTALE.
-- Lo shop ha policy dedicata rls_billing_account_shop (20260420-07-02)
-- con filtro canale_origine=SHOP.
SELECT ok(
    (SELECT qual FROM pg_policies
      WHERE schemaname = 'anagrafiche' AND tablename = 'billing_account'
        AND policyname = 'rls_billing_account_self_ownership') ~ 'fn_scope_sr_perimetro\(\( SELECT (script\.)?fn_get_identita_sr_perimetro\(.*, soggetto_ruolo_id\)'
    AND (SELECT qual FROM pg_policies
          WHERE schemaname = 'anagrafiche' AND tablename = 'billing_account'
            AND policyname = 'rls_billing_account_self_ownership') ~ 'CLIENTE_PORTALE'
    AND (SELECT qual FROM pg_policies
          WHERE schemaname = 'anagrafiche' AND tablename = 'billing_account'
            AND policyname = 'rls_billing_account_self_ownership') !~ 'SHOP_CUSTOMER',
    -- Rev 2026-10-21 (20261021-32): il BA e' la riga, il suo cliente e' la sua colonna.
    '28. rls_billing_account_self_ownership: USING perimetro del cliente + soggetto del BA, gate solo CLIENTE_PORTALE (no SHOP_CUSTOMER post 20-04-2026)'
);

SELECT * FROM finish();
ROLLBACK;
