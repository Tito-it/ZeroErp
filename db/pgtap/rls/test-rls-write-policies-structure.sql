-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-contesto: escluso — la ragione e' scritta per esteso piu' sotto in
--   questo stesso file. Dichiarazione leggibile dal cancello
--   scripts/guardrail_pgtap_preambolo.py: distingue «escluso apposta» da
--   «dimenticato», che una nota in prosa non fa.
--   ⚠️ Da riguardare: le esclusioni `rls/` furono fatte IN BLOCCO, e almeno
--   una non ne aveva diritto (brief pgtap-runner-rls-baseline §30.2).
-- pgTAP test STRUTTURALE — copertura scrittura policy RLS ef_whitelist
--
-- Brief RLS Ondata 2 ("insert bloccati"): dopo l'ENABLE (20260601-38..41)
-- le 10 policy ef_whitelist erano FOR SELECT -> ogni INSERT/UPDATE operatore
-- falliva ("new row violates row-level security policy"). Le migration
-- 20260603-16..25 le estendono a FOR ALL con WITH CHECK.
--
-- Questo test verifica la STRUTTURA (cheap, robusto, regression guard):
--   - ogni policy ef_whitelist e' ora cmd = ALL
--   - ogni policy ef_whitelist ha WITH CHECK NON nullo
--   - billing_account ha la policy gemella _ins (FOR INSERT, gate-only,
--     NON via_efba — vedi caso speciale migration 20260603-25)
--
-- La correttezza funzionale (insert in-scope OK / fuori-scope rifiutato) e'
-- coperta da test-rls-preventivi-ef-whitelist-write.sql.
--
-- Indice test (1..33):
--   1-10   : ogni ef_whitelist esiste
--   11-20  : ogni ef_whitelist ha cmd = ALL
--   21-30  : ogni ef_whitelist ha WITH CHECK NON nullo
--   31     : rls_billing_account_ef_whitelist_ins esiste
--   32     : ...ed e' FOR INSERT
--   33     : ...con WITH CHECK gate-only (ruolo, NON via_efba)
--
-- BEGIN; + ROLLBACK a fine file (nessun ENABLE: pg_policies enumera comunque).
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

SELECT plan(33);

-- Elenco canonico delle 10 policy ef_whitelist con copertura scrittura.
CREATE TEMP TABLE _pol (sch text, tbl text, pol text) ON COMMIT DROP;
INSERT INTO _pol (sch, tbl, pol) VALUES
    ('vendite',    'preventivi',          'rls_preventivi_ef_whitelist'),
    ('vendite',    'offerte_commerciali', 'rls_offerte_commerciali_ef_whitelist'),
    ('vendite',    'ordini',              'rls_ordini_ef_whitelist'),
    ('vendite',    'contratti',           'rls_contratti_ef_whitelist'),
    ('pratiche',   'pratiche',            'rls_pratiche_ef_whitelist'),
    ('documenti',  'documenti_generati',  'rls_documenti_generati_ef_whitelist'),
    ('vendite',    'fatture',             'rls_fatture_ef_whitelist'),
    ('vendite',    'fatturazione_lotti',  'rls_fatturazione_lotti_ef_whitelist'),
    ('vendite',    'fatture_scadenze',    'rls_fatture_scadenze_ef_whitelist'),
    ('anagrafiche','billing_account',     'rls_billing_account_ef_whitelist');

-- 1-10: esistenza
SELECT ok(
    EXISTS (SELECT 1 FROM pg_policies
             WHERE schemaname = p.sch AND tablename = p.tbl AND policyname = p.pol),
    format('Policy %s esiste su %s.%s', p.pol, p.sch, p.tbl)
) FROM _pol p ORDER BY p.tbl;

-- 11-20: cmd = ALL (copre INSERT/UPDATE/DELETE oltre SELECT)
SELECT is(
    (SELECT cmd FROM pg_policies
      WHERE schemaname = p.sch AND tablename = p.tbl AND policyname = p.pol),
    'ALL',
    format('%s: cmd = ALL', p.pol)
) FROM _pol p ORDER BY p.tbl;

-- 21-30: WITH CHECK NON nullo (altrimenti INSERT/UPDATE rifiutati)
SELECT ok(
    (SELECT with_check FROM pg_policies
      WHERE schemaname = p.sch AND tablename = p.tbl AND policyname = p.pol) IS NOT NULL,
    format('%s: WITH CHECK presente', p.pol)
) FROM _pol p ORDER BY p.tbl;

-- 31-33: billing_account policy INSERT gate-only (caso speciale)
SELECT ok(
    EXISTS (SELECT 1 FROM pg_policies
             WHERE schemaname = 'anagrafiche' AND tablename = 'billing_account'
               AND policyname = 'rls_billing_account_ef_whitelist_ins'),
    '31. rls_billing_account_ef_whitelist_ins esiste'
);

SELECT is(
    (SELECT cmd FROM pg_policies
      WHERE schemaname = 'anagrafiche' AND tablename = 'billing_account'
        AND policyname = 'rls_billing_account_ef_whitelist_ins'),
    'INSERT',
    '32. rls_billing_account_ef_whitelist_ins: cmd = INSERT'
);

-- Gate-only: la WITH CHECK referenzia il ruolo ma NON via_efba (il mapping
-- efba e' creato da trigger AFTER INSERT, quindi via_efba qui rifiuterebbe
-- i BA nuovi).
SELECT ok(
    (SELECT with_check FROM pg_policies
      WHERE schemaname = 'anagrafiche' AND tablename = 'billing_account'
        AND policyname = 'rls_billing_account_ef_whitelist_ins') ~ 'ruolo_applicativo'
    AND (SELECT with_check FROM pg_policies
          WHERE schemaname = 'anagrafiche' AND tablename = 'billing_account'
            AND policyname = 'rls_billing_account_ef_whitelist_ins') !~ 'efba',
    '33. rls_billing_account_ef_whitelist_ins: WITH CHECK gate-only (no via_efba)'
);

SELECT * FROM finish();
ROLLBACK;
