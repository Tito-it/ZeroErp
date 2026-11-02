-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
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
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file sarebbe verde per sottrazione. IMMEDIATE li riporta a scattare a fine
--   di ogni istruzione. In testa e non in coda: in coda scatterebbero dopo il
--   cleanup, su righe ormai cancellate.
--   Brief: brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(7);
CREATE TEMP TABLE tmp_costanti_lgd AS
SELECT (
    'pgtap_lgd_' || to_char(clock_timestamp(), 'YYMMDDHH24MISS')
  )::text AS test_scope;
-- rev 2026-10-27 (lotto 4 di D7): il cliente si COSTRUISCE
--   (dbops.fn_pgtap_crea_cliente_ba) e l'emittente e' quello di chi agisce
--   (script.fn_pgtap_emittente_sr_operatore); il tipo documento si legge dal
--   catalogo di seed config.tipi_doc_fiscale. Prima BA, utility ed emittente
--   si pescavano dal primo billing account con un emittente, e tipo/registro
--   dalla prima mappatura tipi_doc_fiscale_registri: da zero non c'erano.
CREATE TEMP TABLE tmp_cli_lgd AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('logs guard delete');

-- ⛔ IL REGISTRO SI ALLINEA ALL'EMITTENTE: dal 2026-08-30
--   vendite.trgfn_fatture_guard_registro_emittente non ammette «un registro
--   qualunque». L'helper risponde con il registro di QUESTO emittente,
--   creandolo se non ce n'e' uno — la riga vive nella transazione del test.
CREATE TEMP TABLE tmp_refs_lgd AS
SELECT script.fn_pgtap_registro_fattura(script.fn_pgtap_emittente_sr_operatore()) AS registro_id,
  (
    SELECT t.id
    FROM config.tipi_doc_fiscale t
    WHERE t.attivo IS TRUE
    ORDER BY t.id
    LIMIT 1
  ) AS tipo_doc_fiscale_id,
  (SELECT billing_account_id FROM tmp_cli_lgd) AS billing_account_id,
  (SELECT utility_id FROM tmp_cli_lgd) AS utility_id,
  script.fn_pgtap_emittente_sr_operatore() AS emittente_soggetto_ruolo_id,
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
    p_competenza_mese => date_trunc('month', script.fn_data_operativa())::date,
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
    script.fn_data_operativa(),
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
