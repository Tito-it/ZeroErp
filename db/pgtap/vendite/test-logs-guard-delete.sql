-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: guard DELETE su fatture_log / fatturazione_lotti_log
-- ------------------------------------------------------------
-- Indice test
-- 1) Riferimenti minimi presenti
-- 2) Setup record log completato
-- 3) DELETE fatture_log bloccato senza GUC
-- 4) DELETE fatture_log consentito con GUC allow_delete_logs
-- 5) Reinserimento fatture_log completato
-- 6) DELETE fatturazione_lotti_log bloccato senza GUC
-- 7) DELETE fatturazione_lotti_log consentito con GUC allow_delete_logs
-- ------------------------------------------------------------
BEGIN;
SELECT plan(7);
CREATE TEMP TABLE tmp_costanti_lgd AS
SELECT (
    'pgtap_lgd_' || to_char(clock_timestamp(), 'YYMMDDHH24MISS')
  )::text AS test_scope;
CREATE TEMP TABLE tmp_refs_lgd AS
SELECT (
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
    WHERE --ba.attivo IS TRUE and
      ba.utility_id IS NOT NULL
      AND anagrafiche.fn_get_emittente_fiscale_id(ba.id) IS NOT NULL
    ORDER BY ba.id
    LIMIT 1
  ) AS billing_account_id,
  (
    SELECT ba.utility_id
    FROM anagrafiche.billing_account ba
    WHERE -- ba.attivo IS TRUE and
      ba.utility_id IS NOT NULL
      AND anagrafiche.fn_get_emittente_fiscale_id(ba.id) IS NOT NULL
    ORDER BY ba.id
    LIMIT 1
  ) AS utility_id,
  (
    SELECT anagrafiche.fn_get_emittente_fiscale_id(ba.id)
    FROM anagrafiche.billing_account ba
    WHERE -- ba.attivo IS TRUE and
      ba.utility_id IS NOT NULL
      AND anagrafiche.fn_get_emittente_fiscale_id(ba.id) IS NOT NULL
    ORDER BY ba.id
    LIMIT 1
  ) AS emittente_soggetto_ruolo_id,
  (
    SELECT v.id
    FROM config.valute v --WHERE v.attivo IS TRUE
    ORDER BY v.id
    LIMIT 1
  ) AS valuta_id;
SELECT ok(
    (
      SELECT registro_id IS NOT NULL
        AND tipo_doc_fiscale_id IS NOT NULL
        AND billing_account_id IS NOT NULL
        AND utility_id IS NOT NULL
        AND emittente_soggetto_ruolo_id IS NOT NULL
        AND valuta_id IS NOT NULL
      FROM tmp_refs_lgd
    ),
    'Riferimenti minimi presenti'
  );
CREATE TEMP TABLE tmp_lotto_lgd AS
SELECT vendite.fn_create_fatturazione_lotto(
    p_competenza_mese => date_trunc('month', current_date)::date,
    p_tipo_doc_fiscale_id => (
      SELECT tipo_doc_fiscale_id
      FROM tmp_refs_lgd
    ),
    p_utility_id => (
      SELECT utility_id
      FROM tmp_refs_lgd
    ),
    p_billing_account_id => (
      SELECT billing_account_id
      FROM tmp_refs_lgd
    ),
    p_lock_batch_id => NULL,
    p_meta => jsonb_build_object(
      'test_scope',
      (
        SELECT test_scope
        FROM tmp_costanti_lgd
      )
    ),
    p_emittente_soggetto_ruolo_id => (
      SELECT emittente_soggetto_ruolo_id
      FROM tmp_refs_lgd
    )
  ) AS lotto_id;
CREATE TEMP TABLE tmp_fattura_lgd AS WITH ins AS (
  INSERT INTO vendite.fatture (
      registro_id,
      data,
      emittente_soggetto_ruolo_id,
      billing_account_id,
      tipo_doc_fiscale_id,
      valuta_id,
      totale_a_pagare,
      meta
    )
  SELECT (
      SELECT registro_id
      FROM tmp_refs_lgd
    ),
    current_date,
    (
      SELECT emittente_soggetto_ruolo_id
      FROM tmp_refs_lgd
    ),
    (
      SELECT billing_account_id
      FROM tmp_refs_lgd
    ),
    (
      SELECT tipo_doc_fiscale_id
      FROM tmp_refs_lgd
    ),
    (
      SELECT valuta_id
      FROM tmp_refs_lgd
    ),
    5.00,
    jsonb_build_object(
      'test_scope',
      (
        SELECT test_scope
        FROM tmp_costanti_lgd
      )
    )
  RETURNING id
)
SELECT id
FROM ins;
CREATE TEMP TABLE tmp_log_fattura_lgd AS WITH ins AS (
  INSERT INTO vendite.fatture_log (
      fattura_id,
      data_ora,
      messaggio,
      status,
      disabilitato,
      meta
    )
  SELECT (
      SELECT id
      FROM tmp_fattura_lgd
    ),
    now(),
    'Log guard delete fattura',
    'W',
    false,
    jsonb_build_object(
      'test_scope',
      (
        SELECT test_scope
        FROM tmp_costanti_lgd
      )
    )
  RETURNING id
)
SELECT id
FROM ins;
CREATE TEMP TABLE tmp_log_lotto_lgd AS WITH ins AS (
  INSERT INTO vendite.fatturazione_lotti_log (
      lotto_id,
      data_ora,
      messaggio,
      status,
      disabilitato,
      meta
    )
  SELECT (
      SELECT lotto_id
      FROM tmp_lotto_lgd
    ),
    now(),
    'Log guard delete lotto',
    'I',
    false,
    jsonb_build_object(
      'test_scope',
      (
        SELECT test_scope
        FROM tmp_costanti_lgd
      )
    )
  RETURNING id
)
SELECT id
FROM ins;
SELECT ok(
    (
      SELECT EXISTS (
          SELECT 1
          FROM tmp_log_fattura_lgd
        )
        AND EXISTS (
          SELECT 1
          FROM tmp_log_lotto_lgd
        )
    ),
    'Setup record log completato'
  );
SELECT throws_ok(
    $$
    DELETE FROM vendite.fatture_log
    WHERE id = (
        SELECT id
        FROM tmp_log_fattura_lgd
      );
$$,
'P0001',
NULL,
'DELETE fatture_log bloccato senza GUC'
);
SELECT lives_ok(
    $$
    SELECT set_config(
        'zeroerp.maintenance_allow_delete_logs',
        'on',
        true
      );
DELETE FROM vendite.fatture_log
WHERE id = (
    SELECT id
    FROM tmp_log_fattura_lgd
  );
$$,
'DELETE fatture_log consentito con GUC allow_delete_logs'
);
CREATE TEMP TABLE tmp_log_fattura_lgd_2 AS WITH ins AS (
  INSERT INTO vendite.fatture_log (
      fattura_id,
      data_ora,
      messaggio,
      status,
      disabilitato,
      meta
    )
  SELECT (
      SELECT id
      FROM tmp_fattura_lgd
    ),
    now(),
    'Log guard delete fattura 2',
    'W',
    false,
    jsonb_build_object(
      'test_scope',
      (
        SELECT test_scope
        FROM tmp_costanti_lgd
      )
    )
  RETURNING id
)
SELECT id
FROM ins;
SELECT ok(
    (
      SELECT EXISTS (
          SELECT 1
          FROM tmp_log_fattura_lgd_2
        )
    ),
    'Reinserimento fatture_log completato'
  );
-- Reset esplicito GUC nello stesso transaction scope del test:
-- la set_config(..., true) precedente resta attiva fino a fine transazione.
SELECT set_config('zeroerp.maintenance_allow_delete_logs', 'off', true);
SELECT throws_ok(
    $$
    DELETE FROM vendite.fatturazione_lotti_log
    WHERE id = (
        SELECT id
        FROM tmp_log_lotto_lgd
      );
$$,
'P0001',
NULL,
'DELETE fatturazione_lotti_log bloccato senza GUC'
);
SELECT lives_ok(
    $$
    SELECT set_config(
        'zeroerp.maintenance_allow_delete_logs',
        'on',
        true
      );
DELETE FROM vendite.fatturazione_lotti_log
WHERE id = (
    SELECT id
    FROM tmp_log_lotto_lgd
  );
$$,
'DELETE fatturazione_lotti_log consentito con GUC allow_delete_logs'
);
SELECT *
FROM finish();
ROLLBACK;
