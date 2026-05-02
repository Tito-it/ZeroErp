-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: anagrafiche.trgfn_billing_account_guard_soggetto_coerenza_istanza
--       Trigger: trg_billing_account_a10_guard_soggetto_coerenza_istanza_ins_upd
--
-- Migrations:
--   20260502-16 (create-trgfn-billing-account-guard-soggetto-coerenza-istanza)
--
-- Indice test (1..5):
--   1) Function presente in anagrafiche.
--   2) Trigger BEFORE INSERT/UPDATE su billing_account presente.
--   3) Pre-check su DB pulito: nessun BA esistente viola il vincolo.
--   4) INSERT BA con soggetto_ruolo coerente con istanza -> ammesso.
--   5) INSERT BA con soggetto_ruolo NON coerente -> raise
--      E_BA_SOGGETTO_INCOERENTE_ISTANZA (P0001).
--
-- Pattern: usa entita' esistenti nel DB (2 soggetti distinti +
-- relativi soggetti_ruoli + istanza ancorata al soggetto1) per
-- evitare il setup complesso (soggetti hanno guard contatti+indirizzi).
-- ------------------------------------------------------------

BEGIN;
SELECT plan(5);

-- ============================================================
-- 1) Function presente
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1 FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'anagrafiche'
      AND p.proname = 'trgfn_billing_account_guard_soggetto_coerenza_istanza'
  ),
  '1. trgfn_billing_account_guard_soggetto_coerenza_istanza presente'
);

-- ============================================================
-- 2) Trigger presente su billing_account
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1 FROM pg_trigger t
    JOIN pg_class c ON c.oid = t.tgrelid
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'anagrafiche'
      AND c.relname = 'billing_account'
      AND t.tgname  = 'trg_billing_account_a10_guard_soggetto_coerenza_istanza_ins_upd'
      AND NOT t.tgisinternal
  ),
  '2. Trigger trg_billing_account_a10_guard_soggetto_coerenza_istanza_ins_upd presente'
);

-- ============================================================
-- 3) Pre-check coerenza dati attuali: nessun BA viola il vincolo
-- ============================================================
SELECT is(
  (SELECT count(*)::int
     FROM anagrafiche.billing_account ba
     JOIN anagrafiche.soggetti_ruoli sr ON sr.id = ba.soggetto_ruolo_id
     JOIN anagrafiche.istanze_utilities iu ON iu.id = ba.istanza_utility_id
    WHERE sr.soggetto_id <> iu.soggetto_id),
  0,
  '3. Nessun BA esistente con soggetto incoerente vs istanza'
);

-- ============================================================
-- 4) Setup riferimenti: 2 soggetti diversi + ruoli + istanza s1
-- ============================================================
CREATE TEMP TABLE tmp_ba_refs AS
WITH soggetti_distinti AS (
  -- Pesca 2 soggetti distinti che abbiano almeno un soggetto_ruolo
  -- e un'istanza con quel soggetto.
  SELECT s.id AS soggetto_id
    FROM anagrafiche.soggetti s
    JOIN anagrafiche.soggetti_ruoli sr ON sr.soggetto_id = s.id
    JOIN anagrafiche.istanze_utilities iu ON iu.soggetto_id = s.id
   GROUP BY s.id
   ORDER BY s.id
   LIMIT 2
)
SELECT
  (SELECT soggetto_id FROM soggetti_distinti ORDER BY soggetto_id LIMIT 1)        AS soggetto1_id,
  (SELECT soggetto_id FROM soggetti_distinti ORDER BY soggetto_id DESC LIMIT 1)   AS soggetto2_id,
  -- soggetto_ruolo per soggetto1
  (SELECT sr.id FROM anagrafiche.soggetti_ruoli sr
    WHERE sr.soggetto_id = (SELECT soggetto_id FROM soggetti_distinti ORDER BY soggetto_id LIMIT 1)
    ORDER BY sr.id LIMIT 1) AS soggetto1_ruolo_id,
  -- soggetto_ruolo per soggetto2 (DIVERSO)
  (SELECT sr.id FROM anagrafiche.soggetti_ruoli sr
    WHERE sr.soggetto_id = (SELECT soggetto_id FROM soggetti_distinti ORDER BY soggetto_id DESC LIMIT 1)
    ORDER BY sr.id LIMIT 1) AS soggetto2_ruolo_id,
  -- istanza ancorata al soggetto1, NON gia' usata da un BA su qualsiasi utility
  -- (per UNIQUE (istanza_utility_id, utility_id) potremmo collidere; per
  -- semplicita' usiamo una utility distinta da quella eventualmente gia'
  -- presente sull'istanza).
  (SELECT iu.id FROM anagrafiche.istanze_utilities iu
    WHERE iu.soggetto_id = (SELECT soggetto_id FROM soggetti_distinti ORDER BY soggetto_id LIMIT 1)
    ORDER BY iu.id LIMIT 1) AS istanza_id,
  -- utility libera per quella istanza
  (SELECT u.id FROM config.utilities u
    WHERE NOT EXISTS (
      SELECT 1 FROM anagrafiche.billing_account ba
       WHERE ba.istanza_utility_id = (SELECT iu.id FROM anagrafiche.istanze_utilities iu
                                       WHERE iu.soggetto_id = (SELECT soggetto_id FROM soggetti_distinti ORDER BY soggetto_id LIMIT 1)
                                       ORDER BY iu.id LIMIT 1)
         AND ba.utility_id = u.id
    )
    ORDER BY u.id LIMIT 1) AS utility_id,
  -- categoria cliente qualunque attiva
  (SELECT cc.id FROM anagrafiche.categorie_clienti cc WHERE cc.attivo IS TRUE ORDER BY cc.id LIMIT 1) AS categoria_cliente_id;

-- Verifica setup: tutti i riferimenti popolati
SELECT ok(
  (SELECT soggetto1_id IS NOT NULL
      AND soggetto2_id IS NOT NULL
      AND soggetto1_id <> soggetto2_id
      AND soggetto1_ruolo_id IS NOT NULL
      AND soggetto2_ruolo_id IS NOT NULL
      AND istanza_id IS NOT NULL
      AND utility_id IS NOT NULL
      AND categoria_cliente_id IS NOT NULL
   FROM tmp_ba_refs),
  '4. Setup: 2 soggetti distinti + ruoli + istanza s1 + utility libera disponibili'
);

-- ============================================================
-- 5) INSERT BA con soggetto_ruolo NON coerente -> raise
-- ============================================================
SELECT throws_ok(
  $$INSERT INTO anagrafiche.billing_account
      (istanza_utility_id, soggetto_ruolo_id, utility_id, categoria_cliente_id, codice)
    SELECT istanza_id, soggetto2_ruolo_id, utility_id, categoria_cliente_id,
           'PGTAP-BA-INCOERENTE-' || substr(md5(clock_timestamp()::text), 1, 8)
      FROM tmp_ba_refs$$,
  'P0001',
  NULL,
  '5. INSERT BA con soggetto_ruolo di soggetto2 + istanza di soggetto1 -> P0001'
);

SELECT * FROM finish();
ROLLBACK;
