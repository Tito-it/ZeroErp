-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: runtime task-runs lotto/attivita + helper condiviso (changeset 20260222-12..13)
-- ------------------------------------------------------------
-- Indice test (1..27):
-- 1) Riferimenti minimi presenti
-- 2) Tabella attivita_fatturabili_pipeline_task_policy presente
-- 3) Tabella attivita_fatturabili_lotti_task_runs presente
-- 4) Funzione fn_set_runtime_task_run_esito presente
-- 5) Funzione fn_get_attivita_pipeline_task_policy presente
-- 6) fn_start_lotto_task_run crea run lotto
-- 7) fn_complete_lotto_task_run eseguita
-- 8) fn_complete_lotto_task_run -> COMPLETATO
-- 9) fn_fail_lotto_task_run eseguita
-- 10) fn_fail_lotto_task_run -> ERRORE + default errori lotto
-- 11) fn_cancel_lotto_task_run eseguita
-- 12) fn_cancel_lotto_task_run -> ANNULLATO
-- 13) fn_get_or_create_lotto_attivita crea lotto attivita
-- 14) Policy branch DEFAULT recuperata
-- 15) Policy branch specifica PREVENTIVI sovrascrive DEFAULT
-- 16) Branch senza policy specifica fa fallback su DEFAULT
-- 17) fn_start_attivita_lotto_task_run crea run attivita
-- 18) fn_complete_attivita_lotto_task_run eseguita
-- 19) fn_complete_attivita_lotto_task_run -> COMPLETATO + reset errori
-- 20) fn_fail_attivita_lotto_task_run eseguita
-- 21) fn_fail_attivita_lotto_task_run -> ERRORE + default error_code attivita
-- 22) fn_cancel_attivita_lotto_task_run eseguita
-- 23) fn_cancel_attivita_lotto_task_run -> ANNULLATO
-- 24) fn_list_attivita_lotto_task_runs elenca i run creati
-- 25) fn_set_runtime_task_run_esito blocca scope non valido
-- 26) fn_set_runtime_task_run_esito aggiorna run attivita
-- 27) fn_set_runtime_task_run_esito aggiorna run attivita in COMPLETATO
-- ------------------------------------------------------------

BEGIN;
SELECT plan(27);

CREATE TEMP TABLE tmp_costanti_atr AS
SELECT
  ('pgtap_atr_' || to_char(clock_timestamp(), 'YYMMDDHH24MISSMS'))::text AS test_scope,
  ('TSK_' || substr(md5(clock_timestamp()::text), 1, 16))::varchar(64) AS task_code,
  ('TSK_' || substr(md5((clock_timestamp() + interval '1 second')::text), 1, 16))::varchar(64) AS task_code_lotto;

CREATE TEMP TABLE tmp_refs_atr AS
SELECT
  (
    SELECT m.registro_id
    FROM vendite.tipi_doc_fiscale_registri m
    JOIN config.tipi_doc_fiscale t ON t.id = m.tipo_doc_fiscale_id
    WHERE t.attivo IS TRUE
    ORDER BY m.id
    LIMIT 1
  ) AS registro_id,
  (
    SELECT m.tipo_doc_fiscale_id
    FROM vendite.tipi_doc_fiscale_registri m
    JOIN config.tipi_doc_fiscale t ON t.id = m.tipo_doc_fiscale_id
    WHERE t.attivo IS TRUE
    ORDER BY m.id
    LIMIT 1
  ) AS tipo_doc_fiscale_id,
  (
    SELECT ba.id
    FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL
      AND anagrafiche.fn_get_emittente_fiscale_id(ba.id) IS NOT NULL
    ORDER BY ba.id
    LIMIT 1
  ) AS billing_account_id,
  (
    SELECT ba.utility_id
    FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL
      AND anagrafiche.fn_get_emittente_fiscale_id(ba.id) IS NOT NULL
    ORDER BY ba.id
    LIMIT 1
  ) AS utility_id,
  (
    SELECT anagrafiche.fn_get_emittente_fiscale_id(ba.id)
    FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL
      AND anagrafiche.fn_get_emittente_fiscale_id(ba.id) IS NOT NULL
    ORDER BY ba.id
    LIMIT 1
  ) AS emittente_soggetto_ruolo_id,
  (
    SELECT s.id
    FROM config.stati_doc_fiscale s
    WHERE s.codice_interno = 'DRAFT'
      AND s.attivo IS TRUE
    ORDER BY s.id
    LIMIT 1
  ) AS stato_draft_id,
  (
    SELECT p.id
    FROM vendite.fatturazione_pipeline p
    WHERE p.attivo IS TRUE
    ORDER BY p.id
    LIMIT 1
  ) AS fatt_pipeline_id,
  (
    SELECT p.id
    FROM vendite.attivita_fatturabili_pipeline p
    WHERE p.attivo IS TRUE
    ORDER BY p.id
    LIMIT 1
  ) AS att_pipeline_id;

SELECT ok(
  (
    SELECT registro_id IS NOT NULL
      AND tipo_doc_fiscale_id IS NOT NULL
      AND billing_account_id IS NOT NULL
      AND utility_id IS NOT NULL
      AND emittente_soggetto_ruolo_id IS NOT NULL
      AND stato_draft_id IS NOT NULL
      AND fatt_pipeline_id IS NOT NULL
      AND att_pipeline_id IS NOT NULL
    FROM tmp_refs_atr
  ),
  'Riferimenti minimi presenti'
);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM information_schema.tables t
    WHERE t.table_schema = 'vendite'
      AND t.table_name = 'attivita_fatturabili_pipeline_task_policy'
  ),
  'Tabella attivita_fatturabili_pipeline_task_policy presente'
);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM information_schema.tables t
    WHERE t.table_schema = 'vendite'
      AND t.table_name = 'attivita_fatturabili_lotti_task_runs'
  ),
  'Tabella attivita_fatturabili_lotti_task_runs presente'
);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite'
      AND p.proname = 'fn_set_runtime_task_run_esito'
  ),
  'Funzione fn_set_runtime_task_run_esito presente'
);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite'
      AND p.proname = 'fn_get_attivita_pipeline_task_policy'
  ),
  'Funzione fn_get_attivita_pipeline_task_policy presente'
);

CREATE TEMP TABLE tmp_lotto_fat_atr AS
SELECT vendite.fn_create_fatturazione_lotto(
  p_competenza_mese => date_trunc('month', current_date)::date,
  p_tipo_doc_fiscale_id => (SELECT tipo_doc_fiscale_id FROM tmp_refs_atr),
  p_utility_id => (SELECT utility_id FROM tmp_refs_atr),
  p_billing_account_id => (SELECT billing_account_id FROM tmp_refs_atr),
  p_lock_batch_id => NULL,
  p_meta => jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_atr), 'case', 'lotto_task_runs_runtime'),
  p_emittente_soggetto_ruolo_id => (SELECT emittente_soggetto_ruolo_id FROM tmp_refs_atr)
) AS lotto_id;

CREATE TEMP TABLE tmp_run_lotto_1 AS
SELECT *
FROM vendite.fn_start_lotto_task_run(
  p_lotto_id => (SELECT lotto_id FROM tmp_lotto_fat_atr),
  p_pipeline_id => (SELECT fatt_pipeline_id FROM tmp_refs_atr),
  p_stato_doc_fiscale_id => (SELECT stato_draft_id FROM tmp_refs_atr),
  p_task_code => (SELECT task_code_lotto FROM tmp_costanti_atr),
  p_fase => 'test complete',
  p_meta => jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_atr), 'step', 'start_lotto_1')
);

SELECT ok(
  (SELECT task_run_id IS NOT NULL AND tentativo = 1 FROM tmp_run_lotto_1),
  'fn_start_lotto_task_run crea run lotto'
);

SELECT lives_ok(
  $$
  SELECT vendite.fn_complete_lotto_task_run(
    p_task_run_id => (SELECT task_run_id FROM tmp_run_lotto_1),
    p_meta => jsonb_build_object('case','complete_lotto_1')
  );
  $$,
  'fn_complete_lotto_task_run eseguita'
);

SELECT is(
  (
    SELECT r.task_stato::text
    FROM vendite.fatturazione_lotti_task_runs r
    WHERE r.id = (SELECT task_run_id FROM tmp_run_lotto_1)
  ),
  'COMPLETATO'::text,
  'fn_complete_lotto_task_run -> COMPLETATO'
);

CREATE TEMP TABLE tmp_run_lotto_2 AS
SELECT *
FROM vendite.fn_start_lotto_task_run(
  p_lotto_id => (SELECT lotto_id FROM tmp_lotto_fat_atr),
  p_pipeline_id => (SELECT fatt_pipeline_id FROM tmp_refs_atr),
  p_stato_doc_fiscale_id => (SELECT stato_draft_id FROM tmp_refs_atr),
  p_task_code => (SELECT task_code_lotto FROM tmp_costanti_atr),
  p_fase => 'test fail',
  p_meta => jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_atr), 'step', 'start_lotto_2')
);

SELECT lives_ok(
  $$
  SELECT vendite.fn_fail_lotto_task_run(
    p_task_run_id => (SELECT task_run_id FROM tmp_run_lotto_2),
    p_error_code => NULL,
    p_error_message => NULL,
    p_meta => jsonb_build_object('case','fail_lotto_2')
  );
  $$,
  'fn_fail_lotto_task_run eseguita'
);

SELECT ok(
  (
    SELECT r.task_stato = 'ERRORE'
       AND r.error_code = 'E_GENERICO'
       AND r.error_message = 'Errore task'
    FROM vendite.fatturazione_lotti_task_runs r
    WHERE r.id = (SELECT task_run_id FROM tmp_run_lotto_2)
  ),
  'fn_fail_lotto_task_run -> ERRORE + default errori lotto'
);

CREATE TEMP TABLE tmp_run_lotto_3 AS
SELECT *
FROM vendite.fn_start_lotto_task_run(
  p_lotto_id => (SELECT lotto_id FROM tmp_lotto_fat_atr),
  p_pipeline_id => (SELECT fatt_pipeline_id FROM tmp_refs_atr),
  p_stato_doc_fiscale_id => (SELECT stato_draft_id FROM tmp_refs_atr),
  p_task_code => (SELECT task_code_lotto FROM tmp_costanti_atr),
  p_fase => 'test cancel',
  p_meta => jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_atr), 'step', 'start_lotto_3')
);

SELECT lives_ok(
  $$
  SELECT vendite.fn_cancel_lotto_task_run(
    p_task_run_id => (SELECT task_run_id FROM tmp_run_lotto_3),
    p_meta => jsonb_build_object('case','cancel_lotto_3')
  );
  $$,
  'fn_cancel_lotto_task_run eseguita'
);

SELECT is(
  (
    SELECT r.task_stato::text
    FROM vendite.fatturazione_lotti_task_runs r
    WHERE r.id = (SELECT task_run_id FROM tmp_run_lotto_3)
  ),
  'ANNULLATO'::text,
  'fn_cancel_lotto_task_run -> ANNULLATO'
);

CREATE TEMP TABLE tmp_lotto_att_atr AS
SELECT vendite.fn_get_or_create_lotto_attivita(
  p_lotto_id => NULL,
  p_competenza_mese => date_trunc('month', current_date)::date,
  p_utility_id => NULL,
  p_billing_account_id => (SELECT billing_account_id FROM tmp_refs_atr),
  p_sorgente_tipo_id => NULL,
  p_lock_batch_id => NULL,
  p_meta => jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_atr), 'case', 'attivita_task_runs_runtime'),
  p_emittente_soggetto_ruolo_id => NULL
) AS lotto_id;

SELECT ok(
  (SELECT lotto_id IS NOT NULL AND lotto_id > 0 FROM tmp_lotto_att_atr),
  'fn_get_or_create_lotto_attivita crea lotto attivita'
);

WITH next_ids AS (
  SELECT COALESCE(MAX(p.id), 0) + 1 AS id_base
  FROM vendite.attivita_fatturabili_pipeline_task_policy p
)
INSERT INTO vendite.attivita_fatturabili_pipeline_task_policy (
  id,
  pipeline_id,
  branch_code,
  task_code,
  annullabile,
  resume_mode,
  block_scope,
  depends_on,
  attivo,
  meta
)
SELECT
  n.id_base,
  (SELECT att_pipeline_id FROM tmp_refs_atr),
  'DEFAULT',
  (SELECT task_code FROM tmp_costanti_atr),
  true,
  'RESUME_BRANCH',
  'BRANCH',
  '[]'::jsonb,
  true,
  jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_atr), 'policy', 'default')
FROM next_ids n
UNION ALL
SELECT
  n.id_base + 1,
  (SELECT att_pipeline_id FROM tmp_refs_atr),
  'PREVENTIVI',
  (SELECT task_code FROM tmp_costanti_atr),
  true,
  'RESUME_TASK',
  'GLOBAL',
  jsonb_build_array('IMPORT_PREVENTIVI'),
  true,
  jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_atr), 'policy', 'branch_specific')
FROM next_ids n;

SELECT ok(
  (
    SELECT p.resume_mode = 'RESUME_BRANCH' AND p.block_scope = 'BRANCH'
    FROM vendite.fn_get_attivita_pipeline_task_policy(
      p_pipeline_id => (SELECT att_pipeline_id FROM tmp_refs_atr),
      p_task_code => (SELECT task_code FROM tmp_costanti_atr),
      p_branch_code => 'DEFAULT'
    ) p
  ),
  'Policy branch DEFAULT recuperata'
);

SELECT ok(
  (
    SELECT p.resume_mode = 'RESUME_TASK' AND p.block_scope = 'GLOBAL'
    FROM vendite.fn_get_attivita_pipeline_task_policy(
      p_pipeline_id => (SELECT att_pipeline_id FROM tmp_refs_atr),
      p_task_code => (SELECT task_code FROM tmp_costanti_atr),
      p_branch_code => 'PREVENTIVI'
    ) p
  ),
  'Policy branch specifica PREVENTIVI sovrascrive DEFAULT'
);

SELECT ok(
  (
    SELECT p.resume_mode = 'RESUME_BRANCH' AND p.block_scope = 'BRANCH'
    FROM vendite.fn_get_attivita_pipeline_task_policy(
      p_pipeline_id => (SELECT att_pipeline_id FROM tmp_refs_atr),
      p_task_code => (SELECT task_code FROM tmp_costanti_atr),
      p_branch_code => 'ORDINI'
    ) p
  ),
  'Branch senza policy specifica fa fallback su DEFAULT'
);

CREATE TEMP TABLE tmp_run_att_1 AS
SELECT *
FROM vendite.fn_start_attivita_lotto_task_run(
  p_lotto_attivita_id => (SELECT lotto_id FROM tmp_lotto_att_atr),
  p_pipeline_id => (SELECT att_pipeline_id FROM tmp_refs_atr),
  p_task_code => (SELECT task_code FROM tmp_costanti_atr),
  p_branch_code => 'PREVENTIVI',
  p_sorgente_tipo_id => NULL,
  p_fase => 'test complete',
  p_block_scope => 'GLOBAL',
  p_depends_on => jsonb_build_array('IMPORT_PREVENTIVI'),
  p_meta => jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_atr), 'step', 'start_att_1')
);

SELECT ok(
  (
    SELECT task_run_id IS NOT NULL AND tentativo = 1
    FROM tmp_run_att_1
  ),
  'fn_start_attivita_lotto_task_run crea run attivita'
);

SELECT lives_ok(
  $$
  SELECT vendite.fn_complete_attivita_lotto_task_run(
    p_task_run_id => (SELECT task_run_id FROM tmp_run_att_1),
    p_meta => jsonb_build_object('case','complete_att_1')
  );
  $$,
  'fn_complete_attivita_lotto_task_run eseguita'
);

SELECT ok(
  (
    SELECT r.task_stato = 'COMPLETATO'
       AND r.error_code IS NULL
       AND r.error_message IS NULL
    FROM vendite.attivita_fatturabili_lotti_task_runs r
    WHERE r.id = (SELECT task_run_id FROM tmp_run_att_1)
  ),
  'fn_complete_attivita_lotto_task_run -> COMPLETATO + reset errori'
);

CREATE TEMP TABLE tmp_run_att_2 AS
SELECT *
FROM vendite.fn_start_attivita_lotto_task_run(
  p_lotto_attivita_id => (SELECT lotto_id FROM tmp_lotto_att_atr),
  p_pipeline_id => (SELECT att_pipeline_id FROM tmp_refs_atr),
  p_task_code => (SELECT task_code FROM tmp_costanti_atr),
  p_branch_code => 'PREVENTIVI',
  p_sorgente_tipo_id => NULL,
  p_fase => 'test fail',
  p_block_scope => 'GLOBAL',
  p_depends_on => '[]'::jsonb,
  p_meta => jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_atr), 'step', 'start_att_2')
);

SELECT lives_ok(
  $$
  SELECT vendite.fn_fail_attivita_lotto_task_run(
    p_task_run_id => (SELECT task_run_id FROM tmp_run_att_2),
    p_error_code => NULL,
    p_error_message => 'errore runtime attivita',
    p_meta => jsonb_build_object('case','fail_att_2')
  );
  $$,
  'fn_fail_attivita_lotto_task_run eseguita'
);

SELECT ok(
  (
    SELECT r.task_stato = 'ERRORE'
       AND r.error_code = 'E_TASK_RUNTIME'
    FROM vendite.attivita_fatturabili_lotti_task_runs r
    WHERE r.id = (SELECT task_run_id FROM tmp_run_att_2)
  ),
  'fn_fail_attivita_lotto_task_run -> ERRORE + default error_code attivita'
);

CREATE TEMP TABLE tmp_run_att_3 AS
SELECT *
FROM vendite.fn_start_attivita_lotto_task_run(
  p_lotto_attivita_id => (SELECT lotto_id FROM tmp_lotto_att_atr),
  p_pipeline_id => (SELECT att_pipeline_id FROM tmp_refs_atr),
  p_task_code => (SELECT task_code FROM tmp_costanti_atr),
  p_branch_code => 'ORDINI',
  p_sorgente_tipo_id => NULL,
  p_fase => 'test cancel',
  p_block_scope => 'BRANCH',
  p_depends_on => '[]'::jsonb,
  p_meta => jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_atr), 'step', 'start_att_3')
);

SELECT lives_ok(
  $$
  SELECT vendite.fn_cancel_attivita_lotto_task_run(
    p_task_run_id => (SELECT task_run_id FROM tmp_run_att_3),
    p_meta => jsonb_build_object('case','cancel_att_3')
  );
  $$,
  'fn_cancel_attivita_lotto_task_run eseguita'
);

SELECT is(
  (
    SELECT r.task_stato::text
    FROM vendite.attivita_fatturabili_lotti_task_runs r
    WHERE r.id = (SELECT task_run_id FROM tmp_run_att_3)
  ),
  'ANNULLATO'::text,
  'fn_cancel_attivita_lotto_task_run -> ANNULLATO'
);

SELECT ok(
  (
    SELECT count(*) >= 3
    FROM vendite.fn_list_attivita_lotto_task_runs(
      p_lotto_attivita_id => (SELECT lotto_id FROM tmp_lotto_att_atr),
      p_branch_code => NULL,
      p_task_code => (SELECT task_code FROM tmp_costanti_atr)
    ) r
  ),
  'fn_list_attivita_lotto_task_runs elenca i run creati'
);

SELECT throws_ok(
  $$
  SELECT vendite.fn_set_runtime_task_run_esito(
    p_scope => 'BAD_SCOPE',
    p_task_run_id => (SELECT task_run_id FROM tmp_run_att_3),
    p_task_stato => 'COMPLETATO',
    p_error_code => NULL,
    p_error_message => NULL,
    p_meta => '{}'::jsonb
  );
  $$,
  'P0001',
  NULL,
  'fn_set_runtime_task_run_esito blocca scope non valido'
);

SELECT lives_ok(
  $$
  SELECT vendite.fn_set_runtime_task_run_esito(
    p_scope => 'ATTIVITA_FATTURABILI',
    p_task_run_id => (SELECT task_run_id FROM tmp_run_att_3),
    p_task_stato => 'COMPLETATO',
    p_error_code => NULL,
    p_error_message => NULL,
    p_meta => jsonb_build_object('case', 'helper_complete')
  );
  $$,
  'fn_set_runtime_task_run_esito aggiorna run attivita'
);

SELECT is(
  (
    SELECT r.task_stato::text
    FROM vendite.attivita_fatturabili_lotti_task_runs r
    WHERE r.id = (SELECT task_run_id FROM tmp_run_att_3)
  ),
  'COMPLETATO'::text,
  'fn_set_runtime_task_run_esito aggiorna run attivita in COMPLETATO'
);

SELECT * FROM finish();
ROLLBACK;
