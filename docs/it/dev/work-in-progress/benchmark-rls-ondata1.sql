-- ============================================================
-- SPDX-License-Identifier: GPL-3.0-or-later
-- ZeroErp — Benchmark gate RLS Ondata 1 (brief §12)
--
-- Scopo: misurare l'overhead RLS sulle list-view operatore delle tabelle
-- Ondata 1 (fatture, fatture_scadenze, fatturazione_lotti), PRIMA e DOPO
-- l'ENABLE (changeSet 20260601-38). Soglia: regressione latenza <= 10% e
-- NESSUNA transizione index-scan -> seq-scan indotta dalla RLS.
--
-- COME ESEGUIRE (importante):
--   1. Connettersi come il RUNTIME role **zeroerp_app** (NOBYPASSRLS), NON
--      come titodb/postgres (owner/superuser = esenti, non misurano la RLS).
--        psql "host=... dbname=... user=zeroerp_app" -v op_id=<AUTH_USER_ID>
--   2. Scegliere un :op_id di un OPERATORE **con whitelist popolata**
--      (config.user_emittenti_fiscali) per misurare il filtro reale.
--   3. Eseguire questo file UNA VOLTA come BASELINE (RLS ancora OFF),
--      salvare i piani.
--   4. Applicare la migration -38 (ENABLE), poi eseguirlo di nuovo.
--   5. Confrontare "Execution Time" e la forma del piano (Index vs Seq Scan).
--
-- Nota: con RLS OFF zeroerp_app vede tutto (baseline); con RLS ON il
-- predicato di scope diventa un Filter. Differenza = overhead RLS.
-- ============================================================

\set ON_ERROR_STOP on

-- Contesto operatore simulato (come lo popola il backend per richiesta).
SELECT set_config('app.ruolo_applicativo', 'OPERATORE', false);
SELECT set_config('app.current_user_id', :'op_id', false);

\echo '== fatture: lista operatore =='
EXPLAIN (ANALYZE, BUFFERS)
SELECT f.id, f.registro_id, f.data, f.emittente_soggetto_ruolo_id, f.billing_account_id
  FROM vendite.fatture f
 ORDER BY f.id DESC
 LIMIT 100;

\echo '== fatture_scadenze: lista operatore (via fattura) =='
EXPLAIN (ANALYZE, BUFFERS)
SELECT s.id, s.fattura_id
  FROM vendite.fatture_scadenze s
 ORDER BY s.id DESC
 LIMIT 100;

\echo '== fatturazione_lotti: lista operatore =='
EXPLAIN (ANALYZE, BUFFERS)
SELECT l.id, l.emittente_soggetto_ruolo_id, l.billing_account_id
  FROM vendite.fatturazione_lotti l
 ORDER BY l.id DESC
 LIMIT 100;

-- Reset contesto (igienico).
SELECT set_config('app.ruolo_applicativo', '', false);
SELECT set_config('app.current_user_id', '', false);
