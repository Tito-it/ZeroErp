-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: le colonne di audit dei seed di config.iva_natura e di
--   vendite.fatturazione_pipeline_task_policy
-- Riferimento: brief-db-token-null-dei-seed (D2); changeSet 90_end/20261112-54
--   (iva_natura) e 20261112-56 (task_policy), e i mirror 80_data/20250816-01 e
--   20260218-05 (senza le colonne di audit).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - iva_natura.user_insert e' NOT NULL con default CURRENT_USER (linee-guida-
--     sql §7): chi inserisce senza dichiararla (il pannello, il seed) scrive il
--     ruolo che inserisce;
--   - i due seed non lasciano colonne di audit vuote.
--   ⚠️ Il test non costruisce una natura IVA: la scrive il pannello (SECURITY
--     DEFINER). Il contratto e' la struttura della colonna, e la legge da li'.
--
-- Elenco test (plan 4):
--   1) iva_natura.user_insert e' NOT NULL
--   2) iva_natura.user_insert ha default CURRENT_USER
--   3) il seed di iva_natura: nessuna colonna di audit vuota
--   4) il seed di fatturazione_pipeline_task_policy: nessuna colonna di audit vuota
-- ------------------------------------------------------------

BEGIN;
-- Contesto applicativo (preambolo, guardrail_pgtap_preambolo).
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(4);

SELECT col_not_null('config', 'iva_natura', 'user_insert',
                    '1) iva_natura.user_insert e'' NOT NULL');

SELECT col_default_is('config', 'iva_natura', 'user_insert', 'CURRENT_USER',
                      '2) iva_natura.user_insert ha default CURRENT_USER');

-- Il seed e' contratto (80_data): lo si legge, non si conta una popolazione.
SELECT is(
  (SELECT count(*) FROM config.iva_natura n
    WHERE NULLIF(btrim(n.user_insert), '') IS NULL
       OR btrim(n.user_update) = '')::int,
  0,
  '3) il seed di iva_natura: nessuna colonna di audit vuota');

SELECT is(
  (SELECT count(*) FROM vendite.fatturazione_pipeline_task_policy tp
    WHERE btrim(tp.user_insert) = ''
       OR btrim(tp.user_update) = '')::int,
  0,
  '4) il seed di fatturazione_pipeline_task_policy: nessuna colonna di audit vuota');

SELECT * FROM finish();
ROLLBACK;
