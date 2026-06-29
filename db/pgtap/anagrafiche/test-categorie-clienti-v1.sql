-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test F1-DB-T1 (parte 1/2): categorie cliente
-- Copre:
--   - seed categorie (STANDARD, BASE, SILVER, GOLD, PLATINUM)
--   - UNIQUE su codice
--   - flag partecipa_promo differenziato (STANDARD non partecipa)
--
-- Elenco test (1..7):
--   1) Seed STANDARD presente e non partecipa promo
--   2) Seed BASE presente e partecipa promo
--   3) Seed SILVER presente e partecipa promo
--   4) Seed GOLD presente e partecipa promo
--   5) Seed PLATINUM presente e partecipa promo
--   6) UNIQUE codice: insert duplicato fallisce
--   7) Ogni BA ha categoria NOT NULL dopo backfill
-- ------------------------------------------------------------

BEGIN;
SELECT plan(7);

-- 1..5) seed delle 5 categorie con flag partecipa_promo corretto
SELECT is(
    (SELECT partecipa_promo FROM anagrafiche.categorie_clienti WHERE codice = 'STANDARD'),
    FALSE,
    'Categoria STANDARD presente e non partecipa alle promo'
);

SELECT is(
    (SELECT partecipa_promo FROM anagrafiche.categorie_clienti WHERE codice = 'BASE'),
    TRUE,
    'Categoria BASE presente e partecipa alle promo'
);

SELECT is(
    (SELECT partecipa_promo FROM anagrafiche.categorie_clienti WHERE codice = 'SILVER'),
    TRUE,
    'Categoria SILVER presente e partecipa alle promo'
);

SELECT is(
    (SELECT partecipa_promo FROM anagrafiche.categorie_clienti WHERE codice = 'GOLD'),
    TRUE,
    'Categoria GOLD presente e partecipa alle promo'
);

SELECT is(
    (SELECT partecipa_promo FROM anagrafiche.categorie_clienti WHERE codice = 'PLATINUM'),
    TRUE,
    'Categoria PLATINUM presente e partecipa alle promo'
);

-- 6) UNIQUE su codice
--    codice_interno valorizzato (distinto, NOT NULL da 20260629-06) per
--    superare il NOT NULL e colpire davvero la UNIQUE su codice.
SELECT throws_ok(
    $$INSERT INTO anagrafiche.categorie_clienti(codice, codice_interno, descrizione)
      VALUES ('STANDARD', 'DUP_TEST_STANDARD', 'Duplicato test')$$,
    '23505',
    NULL,
    'Insert con codice duplicato viola uq_categorie_clienti_codice'
);

-- 7) Tutti i BA hanno categoria valorizzata (post-backfill + SET NOT NULL)
SELECT is(
    (SELECT COUNT(*)::int FROM anagrafiche.billing_account WHERE categoria_cliente_id IS NULL),
    0,
    'Nessun billing_account senza categoria_cliente_id dopo il backfill'
);

SELECT * FROM finish();
ROLLBACK;
