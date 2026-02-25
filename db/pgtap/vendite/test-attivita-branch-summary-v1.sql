-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: vendite.fn_get_attivita_branch_summary (changeset 20260223-01)
-- ------------------------------------------------------------
-- Indice test (1..8):
-- 1) Funzione fn_get_attivita_branch_summary presente
-- 2) Riferimenti minimi per creare lotto attivita presenti
-- 3) Lotto attivita creato
-- 4) Summary restituisce 3 bucket aggregati
-- 5) Bucket DEFAULT/COMPLETATO = 2
-- 6) Bucket PREVENTIVI/ERRORE = 1
-- 7) Bucket PREVENTIVI/IN_ESECUZIONE = 1
-- 8) Lotto inesistente restituisce 0 righe
-- ------------------------------------------------------------

BEGIN;
SELECT plan(8);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite'
      AND p.proname = 'fn_get_attivita_branch_summary'
  ),
  'Funzione fn_get_attivita_branch_summary presente'
);

CREATE TEMP TABLE tmp_refs_abs AS
SELECT
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
  ) AS emittente_soggetto_ruolo_id;

SELECT ok(
  (
    SELECT billing_account_id IS NOT NULL
       AND utility_id IS NOT NULL
       AND emittente_soggetto_ruolo_id IS NOT NULL
    FROM tmp_refs_abs
  ),
  'Riferimenti minimi per creare lotto attivita presenti'
);

CREATE TEMP TABLE tmp_lotto_abs AS
SELECT vendite.fn_get_or_create_lotto_attivita(
  p_lotto_id => NULL,
  p_competenza_mese => date_trunc('month', current_date)::date,
  p_utility_id => (SELECT utility_id FROM tmp_refs_abs),
  p_billing_account_id => (SELECT billing_account_id FROM tmp_refs_abs),
  p_sorgente_tipo_id => NULL,
  p_lock_batch_id => NULL,
  p_meta => jsonb_build_object('test_scope', 'pgtap_attivita_branch_summary'),
  p_emittente_soggetto_ruolo_id => (SELECT emittente_soggetto_ruolo_id FROM tmp_refs_abs)
) AS lotto_id;

SELECT ok(
  (SELECT lotto_id IS NOT NULL FROM tmp_lotto_abs),
  'Lotto attivita creato'
);

INSERT INTO vendite.attivita_fatturabili_lotti_task_runs (
  lotto_attivita_id,
  branch_code,
  task_code,
  tentativo,
  task_stato,
  block_scope,
  depends_on,
  meta
)
VALUES
  ((SELECT lotto_id FROM tmp_lotto_abs), 'DEFAULT', 'pgtap_task_default_1', 1, 'COMPLETATO', 'BRANCH', '[]'::jsonb, '{}'::jsonb),
  ((SELECT lotto_id FROM tmp_lotto_abs), 'DEFAULT', 'pgtap_task_default_2', 1, 'COMPLETATO', 'BRANCH', '[]'::jsonb, '{}'::jsonb),
  ((SELECT lotto_id FROM tmp_lotto_abs), 'PREVENTIVI', 'pgtap_task_prev_1', 1, 'ERRORE', 'BRANCH', '[]'::jsonb, '{}'::jsonb),
  ((SELECT lotto_id FROM tmp_lotto_abs), 'PREVENTIVI', 'pgtap_task_prev_2', 1, 'IN_ESECUZIONE', 'BRANCH', '[]'::jsonb, '{}'::jsonb);

SELECT is(
  (
    SELECT COUNT(*)
    FROM vendite.fn_get_attivita_branch_summary((SELECT lotto_id FROM tmp_lotto_abs))
  ),
  3::bigint,
  'Summary restituisce 3 bucket aggregati'
);

SELECT is(
  (
    SELECT cnt
    FROM vendite.fn_get_attivita_branch_summary((SELECT lotto_id FROM tmp_lotto_abs))
    WHERE branch_code = 'DEFAULT'
      AND task_stato = 'COMPLETATO'
  ),
  2::bigint,
  'Bucket DEFAULT/COMPLETATO = 2'
);

SELECT is(
  (
    SELECT cnt
    FROM vendite.fn_get_attivita_branch_summary((SELECT lotto_id FROM tmp_lotto_abs))
    WHERE branch_code = 'PREVENTIVI'
      AND task_stato = 'ERRORE'
  ),
  1::bigint,
  'Bucket PREVENTIVI/ERRORE = 1'
);

SELECT is(
  (
    SELECT cnt
    FROM vendite.fn_get_attivita_branch_summary((SELECT lotto_id FROM tmp_lotto_abs))
    WHERE branch_code = 'PREVENTIVI'
      AND task_stato = 'IN_ESECUZIONE'
  ),
  1::bigint,
  'Bucket PREVENTIVI/IN_ESECUZIONE = 1'
);

SELECT is(
  (
    SELECT COUNT(*)
    FROM vendite.fn_get_attivita_branch_summary(999999999)
  ),
  0::bigint,
  'Lotto inesistente restituisce 0 righe'
);

SELECT * FROM finish();
ROLLBACK;

