-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: switch operativo COMMESSA_ONLY su attivita_fatturabili
-- ------------------------------------------------------------
-- Indice test (1..7):
-- 1) parametro attivita_fatturabili_require_commessa=true
-- 2) nessuna sorgente legacy abilitata in attivita_fatturabili_sorgenti_branch_policy
-- 3) nessuno step legacy attivo in attivita_fatturabili_pipeline
-- 4) nessuna task policy legacy attiva in attivita_fatturabili_pipeline_task_policy
-- 5) fn_list_attivita_sorgenti_abilitate restituisce 0 righe
-- 6) sorgente COMMESSA attiva in config.sorgenti
-- 7) trigger guard commessa presente su attivita_fatturabili
-- ------------------------------------------------------------

BEGIN;
SELECT plan(7);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM config.parameters p
    WHERE p.code = 'attivita_fatturabili_require_commessa'
      AND lower(COALESCE(p.default_value, 'false')) = 'true'
  ),
  'parametro attivita_fatturabili_require_commessa=true'
);

SELECT is(
  (
    SELECT count(*)::bigint
    FROM vendite.attivita_fatturabili_sorgenti_branch_policy p
    WHERE p.attivo IS TRUE
      AND p.abilitata IS TRUE
  ),
  0::bigint,
  'nessuna sorgente legacy abilitata in attivita_fatturabili_sorgenti_branch_policy'
);

SELECT is(
  (
    SELECT count(*)::bigint
    FROM vendite.attivita_fatturabili_pipeline p
    WHERE p.attivo IS TRUE
  ),
  0::bigint,
  'nessuno step legacy attivo in attivita_fatturabili_pipeline'
);

SELECT is(
  (
    SELECT count(*)::bigint
    FROM vendite.attivita_fatturabili_pipeline_task_policy p
    WHERE p.attivo IS TRUE
  ),
  0::bigint,
  'nessuna task policy legacy attiva in attivita_fatturabili_pipeline_task_policy'
);

SELECT is(
  (
    SELECT count(*)::bigint
    FROM vendite.fn_list_attivita_sorgenti_abilitate(NULL)
  ),
  0::bigint,
  'fn_list_attivita_sorgenti_abilitate restituisce 0 righe'
);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM config.sorgenti s
    WHERE s.codice = 'COMMESSA'
      AND s.attivo IS TRUE
  ),
  'sorgente COMMESSA attiva in config.sorgenti'
);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM pg_trigger t
    JOIN pg_class c ON c.oid = t.tgrelid
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'vendite'
      AND c.relname = 'attivita_fatturabili'
      AND t.tgname = 'trg_attivita_fatturabili_a10_guard_commessa_ins_upd'
      AND NOT t.tgisinternal
  ),
  'trigger guard commessa presente su attivita_fatturabili'
);

SELECT * FROM finish();
ROLLBACK;
