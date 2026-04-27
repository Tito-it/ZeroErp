-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: trigger normalize+guard scadenza fattura cliente
--       (migration 20260427-03 schema + 20_code).
--
-- Pattern: test su UPDATE di cliente esistente (LIMIT 1) in
-- BEGIN/ROLLBACK. Niente fixture INSERT perche' il setup richiederebbe
-- billing_account + istanza_utility + iva + stato_cliente +
-- soggetto_ruolo (10+ FK NOT NULL). Il trigger scatta indistintamente
-- su INSERT e UPDATE: la copertura UPDATE e' equivalente al fine del
-- guard.
--
-- Indice test (1..10):
--   1)  UPDATE ('G', 30) -> ammesso (combinazione valida)
--   2)  UPDATE ('F', 60) -> ammesso
--   3a) UPDATE ('N', 5)  -> ammesso (lives_ok)
--   3b) UPDATE ('N', 5)  -> nr_giorni normalizzato a NULL (is)
--   4a) UPDATE ('M', 10) -> ammesso (lives_ok)
--   4b) UPDATE ('M', 10) -> nr_giorni normalizzato a NULL (is)
--   5)  UPDATE ('G', NULL) -> E_CLIENTI_GIORNI_SCADENZA_OBBLIGATORI
--   6)  UPDATE ('G', 0)    -> E_CLIENTI_GIORNI_SCADENZA_OBBLIGATORI
--   7)  UPDATE ('X', 5)    -> CHECK chk_clienti_tipo_gg_scadenza_ft
--   8)  Backfill verification: zero record incoerenti post-migration
-- ------------------------------------------------------------

BEGIN;
SELECT plan(10);

-- =========================================================
-- Setup: prendi un cliente esistente (qualsiasi)
-- =========================================================
CREATE TEMP TABLE tmp_ctx_cliente AS
SELECT id AS cliente_id
  FROM anagrafiche.clienti
 ORDER BY id
 LIMIT 1;

-- ============================================================
-- 1) UPDATE ('G', 30) -> ammesso
-- ============================================================
SELECT lives_ok(
    $$UPDATE anagrafiche.clienti
         SET tipo_gg_scadenza_ft = 'G',
             nr_giorni_scadenza = 30
       WHERE id = (SELECT cliente_id FROM tmp_ctx_cliente)$$,
    'UPDATE (G, 30) ammesso (combinazione valida giorni)'
);

-- ============================================================
-- 2) UPDATE ('F', 60) -> ammesso
-- ============================================================
SELECT lives_ok(
    $$UPDATE anagrafiche.clienti
         SET tipo_gg_scadenza_ft = 'F',
             nr_giorni_scadenza = 60
       WHERE id = (SELECT cliente_id FROM tmp_ctx_cliente)$$,
    'UPDATE (F, 60) ammesso (combinazione valida fine mese)'
);

-- ============================================================
-- 3a) UPDATE ('N', 5) -> ammesso (lives_ok)
-- ============================================================
SELECT lives_ok(
    $$UPDATE anagrafiche.clienti
         SET tipo_gg_scadenza_ft = 'N',
             nr_giorni_scadenza = 5
       WHERE id = (SELECT cliente_id FROM tmp_ctx_cliente)$$,
    'UPDATE (N, 5) eseguito (normalize silenzioso, no raise)'
);

-- 3b) Verifica normalize: nr_giorni post-UPDATE deve essere NULL
SELECT is(
    (SELECT nr_giorni_scadenza FROM anagrafiche.clienti
      WHERE id = (SELECT cliente_id FROM tmp_ctx_cliente)),
    NULL::integer,
    'UPDATE (N, 5) -> nr_giorni_scadenza normalizzato a NULL'
);

-- ============================================================
-- 4a) UPDATE ('M', 10) -> ammesso
-- ============================================================
SELECT lives_ok(
    $$UPDATE anagrafiche.clienti
         SET tipo_gg_scadenza_ft = 'M',
             nr_giorni_scadenza = 10
       WHERE id = (SELECT cliente_id FROM tmp_ctx_cliente)$$,
    'UPDATE (M, 10) eseguito (normalize silenzioso, no raise)'
);

-- 4b) Verifica normalize
SELECT is(
    (SELECT nr_giorni_scadenza FROM anagrafiche.clienti
      WHERE id = (SELECT cliente_id FROM tmp_ctx_cliente)),
    NULL::integer,
    'UPDATE (M, 10) -> nr_giorni_scadenza normalizzato a NULL'
);

-- ============================================================
-- 5) UPDATE ('G', NULL) -> E_CLIENTI_GIORNI_SCADENZA_OBBLIGATORI
-- ============================================================
SELECT throws_ok(
    $$UPDATE anagrafiche.clienti
         SET tipo_gg_scadenza_ft = 'G',
             nr_giorni_scadenza = NULL
       WHERE id = (SELECT cliente_id FROM tmp_ctx_cliente)$$,
    'P0001',
    NULL,
    'UPDATE (G, NULL) deve sollevare E_CLIENTI_GIORNI_SCADENZA_OBBLIGATORI'
);

-- ============================================================
-- 6) UPDATE ('G', 0) -> E_CLIENTI_GIORNI_SCADENZA_OBBLIGATORI
-- ============================================================
SELECT throws_ok(
    $$UPDATE anagrafiche.clienti
         SET tipo_gg_scadenza_ft = 'G',
             nr_giorni_scadenza = 0
       WHERE id = (SELECT cliente_id FROM tmp_ctx_cliente)$$,
    'P0001',
    NULL,
    'UPDATE (G, 0) deve sollevare E_CLIENTI_GIORNI_SCADENZA_OBBLIGATORI'
);

-- ============================================================
-- 7) UPDATE ('X', 5) -> CHECK chk_clienti_tipo_gg_scadenza_ft
--    Il trigger normalize sposta nr_giorni a NULL (branch 1), poi
--    il CHECK constraint rifiuta 'X' fuori dominio (G,M,F,N).
-- ============================================================
SELECT throws_ok(
    $$UPDATE anagrafiche.clienti
         SET tipo_gg_scadenza_ft = 'X',
             nr_giorni_scadenza = 5
       WHERE id = (SELECT cliente_id FROM tmp_ctx_cliente)$$,
    '23514',
    NULL,
    'UPDATE (X, 5) deve fallire il CHECK chk_clienti_tipo_gg_scadenza_ft'
);

-- ============================================================
-- 8) Backfill verification: zero record incoerenti post-migration
--    Dopo l'applicazione di 20260427-03-01-backfill ogni record con
--    tipo_gg_scadenza_ft NOT IN ('G','F') deve avere nr_giorni_scadenza
--    IS NULL.
-- ============================================================
SELECT is(
    (SELECT count(*)::int
       FROM anagrafiche.clienti
      WHERE tipo_gg_scadenza_ft NOT IN ('G','F')
        AND nr_giorni_scadenza IS NOT NULL),
    0,
    'Backfill: zero record con tipo NOT IN (G,F) e nr_giorni valorizzato'
);

SELECT * FROM finish();
ROLLBACK;
