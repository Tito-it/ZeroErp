-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: vendite.trgfn_preventivi_default_emittente (BEFORE INSERT)
--   +   vendite.trgfn_preventivi_guard_utility_istanza_coerenza
-- Riferimento brief preventivi rev2 (sessione 2026-05-01).
--
-- Indice test (1..6):
--    1. Trigger preflight: entrambi i trigger esistono
--    2. GUC valida (operatore con EF) + payload senza emittente
--       -> trigger valorizza emittente_fiscale_id
--    3. Payload con emittente esplicito + GUC valida
--       -> trigger NON sovrascrive
--    4. Coppia (istanza, utility) coerente -> INSERT ok (lives_ok)
--    5. GUC vuota + payload senza emittente -> raise P0001
--    6. Coppia (istanza, utility) incoerente -> raise P0001
--
-- IMPORTANTE: nessun SAVEPOINT/ROLLBACK TO SAVEPOINT.
-- pgTAP traccia lo stato test in una temp table interna; un rollback
-- a savepoint cancellerebbe le righe di stato dei test gia' eseguiti
-- e finish() farebbe "No tests run!". Tutto in una sola tx con
-- ROLLBACK finale (BEGIN/ROLLBACK del file) ripulisce le manipolazioni.
--
-- Le GUC sono settate con is_local=true per scope tx (rollback puliro).
-- Ogni INSERT usa numero random per evitare collisioni UNIQUE
-- (uq_preventivi_numero_rev) tra i test successo.
-- ------------------------------------------------------------

BEGIN;
SELECT plan(6);

SET LOCAL zeroerp.allow_lock_columns_override = 'on';

-- ============================================================
-- Setup: contesto comune
-- ============================================================
CREATE TEMP TABLE _t_stato AS
SELECT id AS stato_id FROM config.stati_doc_preventivi
 WHERE attivo = true ORDER BY id LIMIT 1;

CREATE TEMP TABLE _t_ba AS
SELECT ba.id AS ba_id, ba.istanza_utility_id, ba.utility_id
  FROM anagrafiche.billing_account ba
 WHERE ba.istanza_utility_id IS NOT NULL
   AND ba.utility_id IS NOT NULL
 ORDER BY ba.id LIMIT 1;

CREATE TEMP TABLE _t_user_with_ef AS
SELECT au.id AS user_id, uef.emittente_fiscale_id AS ef_id
  FROM django.auth_user au
  JOIN config.user_emittenti_fiscali uef ON uef.auth_user_id = au.id
 WHERE au.is_active = true
 ORDER BY au.id LIMIT 1;

CREATE TEMP TABLE _t_ef AS
SELECT ef.id AS ef_id FROM anagrafiche.emittenti_fiscali ef
 WHERE ef.attivo = true ORDER BY ef.id LIMIT 1;

-- ============================================================
-- 1) Preflight: entrambi i trigger esistono.
--    Senza, gli altri test passerebbero come falsi positivi.
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_trigger t
          JOIN pg_class c   ON c.oid = t.tgrelid
          JOIN pg_namespace n ON n.oid = c.relnamespace
         WHERE n.nspname = 'vendite'
           AND c.relname = 'preventivi'
           AND t.tgname IN (
               'trg_preventivi_a10_default_emittente_ins',
               'trg_preventivi_a10_guard_utility_istanza_coerenza_ins_upd'
           )
        GROUP BY 1 HAVING count(*) = 2
    ),
    '1. Entrambi i trigger (default_emittente, guard_coerenza) esistono'
);

-- ============================================================
-- 2) GUC valida + no emittente nel payload -> auto-fill
-- ============================================================
SELECT set_config('app.current_user_id',
                   (SELECT user_id::text FROM _t_user_with_ef),
                   true);

CREATE TEMP TABLE _t_t2_result AS
WITH ins AS (
  INSERT INTO vendite.preventivi (
    numero, data, stato_doc_preventivo_id, billing_account_id,
    istanza_utility_id, utility_id
  )
  SELECT
    'PGT_T2_' || substring(md5(clock_timestamp()::text) from 1 for 8),
    CURRENT_DATE,
    (SELECT stato_id FROM _t_stato),
    (SELECT ba_id FROM _t_ba),
    (SELECT istanza_utility_id FROM _t_ba),
    (SELECT utility_id FROM _t_ba)
  WHERE (SELECT user_id FROM _t_user_with_ef) IS NOT NULL
  RETURNING emittente_fiscale_id
)
SELECT emittente_fiscale_id FROM ins;

SELECT is(
  (SELECT emittente_fiscale_id FROM _t_t2_result),
  (SELECT ef_id FROM _t_user_with_ef),
  '2. GUC valida + payload senza emittente -> auto-fill da fn_resolve_emittente_for_user'
);

-- ============================================================
-- 3) Payload con emittente esplicito + GUC valida -> NON sovrascritto
-- ============================================================
CREATE TEMP TABLE _t_t3_result AS
WITH ins AS (
  INSERT INTO vendite.preventivi (
    numero, data, stato_doc_preventivo_id, billing_account_id,
    istanza_utility_id, utility_id, emittente_fiscale_id
  )
  SELECT
    'PGT_T3_' || substring(md5(clock_timestamp()::text) from 1 for 8),
    CURRENT_DATE,
    (SELECT stato_id FROM _t_stato),
    (SELECT ba_id FROM _t_ba),
    (SELECT istanza_utility_id FROM _t_ba),
    (SELECT utility_id FROM _t_ba),
    (SELECT ef_id FROM _t_ef)
  WHERE (SELECT ef_id FROM _t_ef) IS NOT NULL
  RETURNING emittente_fiscale_id
)
SELECT emittente_fiscale_id FROM ins;

SELECT is(
  (SELECT emittente_fiscale_id FROM _t_t3_result),
  (SELECT ef_id FROM _t_ef),
  '3. Payload con emittente esplicito -> trigger NON sovrascrive'
);

-- ============================================================
-- 4) Coppia (istanza, utility) coerente via BA -> INSERT ok
--    (combina trigger default_emittente + guard_coerenza in path felice)
-- ============================================================
SELECT lives_ok(
  format($SQL$
    INSERT INTO vendite.preventivi (
      numero, data, stato_doc_preventivo_id, billing_account_id,
      istanza_utility_id, utility_id
    ) VALUES (
      %L, CURRENT_DATE, %s, %s, %s, %s
    )
  $SQL$,
    'PGT_T4_' || substring(md5(clock_timestamp()::text) from 1 for 8),
    (SELECT stato_id FROM _t_stato),
    (SELECT ba_id FROM _t_ba),
    (SELECT istanza_utility_id FROM _t_ba),
    (SELECT utility_id FROM _t_ba)
  ),
  '4. Coppia coerente via BA + GUC valida -> INSERT ok'
);

-- ============================================================
-- 5) GUC vuota + payload senza emittente -> P0001
-- ============================================================
SELECT set_config('app.current_user_id', '', true);

SELECT throws_ok(
  format($SQL$
    INSERT INTO vendite.preventivi (
      numero, data, stato_doc_preventivo_id, billing_account_id,
      istanza_utility_id, utility_id
    ) VALUES (
      %L, CURRENT_DATE, %s, %s, %s, %s
    )
  $SQL$,
    'PGT_T5_' || substring(md5(clock_timestamp()::text) from 1 for 8),
    (SELECT stato_id FROM _t_stato),
    (SELECT ba_id FROM _t_ba),
    (SELECT istanza_utility_id FROM _t_ba),
    (SELECT utility_id FROM _t_ba)
  ),
  'P0001',
  NULL,
  '5. GUC vuota + payload senza emittente -> P0001 (E_PREV_EMITTENTE_NON_RISOLTO)'
);

-- Ripristino GUC valida per test 6 (ha bisogno di emittente per arrivare al guard)
SELECT set_config('app.current_user_id',
                   (SELECT user_id::text FROM _t_user_with_ef),
                   true);

-- ============================================================
-- 6) Coppia (istanza, utility=9999) incoerente -> P0001
-- ============================================================
SELECT throws_ok(
  format($SQL$
    INSERT INTO vendite.preventivi (
      numero, data, stato_doc_preventivo_id, billing_account_id,
      istanza_utility_id, utility_id
    ) VALUES (
      %L, CURRENT_DATE, %s, %s, %s, 9999
    )
  $SQL$,
    'PGT_T6_' || substring(md5(clock_timestamp()::text) from 1 for 8),
    (SELECT stato_id FROM _t_stato),
    (SELECT ba_id FROM _t_ba),
    (SELECT istanza_utility_id FROM _t_ba)
  ),
  'P0001',
  NULL,
  '6. Coppia (istanza, utility=9999) incoerente -> P0001 (E_PREV_UTILITY_ISTANZA_INCOERENTE)'
);

SELECT * FROM finish();
ROLLBACK;
