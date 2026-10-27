-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: vendite.fn_sync_lotto_fatture_stato
-- ------------------------------------------------------------
-- Indice test
-- 1) Riferimenti minimi presenti
-- 2) Lotto creato
-- 3) Fatture test create
-- 4) Link lotto-fatture creati
-- 5) Sync eseguita senza errore
-- 6) Fattura non critical => stato_esecuzione COMPLETED
-- 7) Fattura critical => stato_esecuzione ERRORE
-- 8) stato_doc_fiscale ponte allineato alla fattura (critical)
-- 9) stato_doc_fiscale ponte allineato alla fattura (non critical)
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

SELECT plan(9);
CREATE TEMP TABLE tmp_costanti_sls AS
SELECT (
    'pgtap_sync_lotto_stato_' || to_char(clock_timestamp(), 'YYMMDDHH24MISS')
  )::text AS test_scope;
-- rev 2026-10-27 (lotto 4 di D7): il cliente si COSTRUISCE
--   (dbops.fn_pgtap_crea_cliente_ba) e l'emittente e' quello di chi agisce
--   (script.fn_pgtap_emittente_sr_operatore); il tipo documento si legge dal
--   catalogo di seed config.tipi_doc_fiscale. Prima BA, utility ed emittente
--   si pescavano dal primo billing account con un emittente, e tipo/registro
--   dalla prima mappatura tipi_doc_fiscale_registri: da zero non c'erano.
CREATE TEMP TABLE tmp_cli_sls AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('sync lotto fatture stato');

-- ⛔ IL REGISTRO SI ALLINEA ALL'EMITTENTE: dal 2026-08-30
--   vendite.trgfn_fatture_guard_registro_emittente non ammette «un registro
--   qualunque». L'helper risponde con il registro di QUESTO emittente,
--   creandolo se non ce n'e' uno — la riga vive nella transazione del test.
CREATE TEMP TABLE tmp_refs_sls AS
SELECT script.fn_pgtap_registro_fattura(script.fn_pgtap_emittente_sr_operatore()) AS registro_id,
  (SELECT billing_account_id FROM tmp_cli_sls) AS billing_account_id,
  (SELECT utility_id FROM tmp_cli_sls) AS utility_id,
  (
    SELECT t.id
    FROM config.tipi_doc_fiscale t
    WHERE t.attivo IS TRUE
    ORDER BY t.id
    LIMIT 1
  ) AS tipo_doc_fiscale_id,
  (
    SELECT v.id
    -- config.valute NON ha la colonna `attivo` (come altre 45 tabelle di
    -- config): il filtro qui era commentato, e un filtro commentato invita a
    -- riattivarlo. Si sceglie EUR e si ripiega sull'id piu' basso: deterministico
    -- in ogni caso, senza presupporre una colonna che non esiste.
    FROM config.valute v
    ORDER BY (v.iso_code <> 'EUR'), v.id
    LIMIT 1
  ) AS valuta_id,
  script.fn_pgtap_emittente_sr_operatore() AS emittente_soggetto_ruolo_id,
  (
    SELECT s.id
    FROM config.stati_doc_fiscale s
    WHERE s.codice_interno = 'DRAFT'
      AND s.attivo IS TRUE
    ORDER BY s.id
    LIMIT 1
  ) AS stato_draft_id;

SELECT ok(
    (
      SELECT registro_id IS NOT NULL
        AND billing_account_id IS NOT NULL
        AND utility_id IS NOT NULL
        AND tipo_doc_fiscale_id IS NOT NULL
        AND valuta_id IS NOT NULL
        AND emittente_soggetto_ruolo_id IS NOT NULL
        AND stato_draft_id IS NOT NULL
      FROM tmp_refs_sls
    ),
    'Riferimenti minimi presenti'
  );
CREATE TEMP TABLE tmp_lotto_sls AS
SELECT vendite.fn_create_fatturazione_lotto(
    p_competenza_mese => date_trunc('month', script.fn_data_operativa())::date,
    p_tipo_doc_fiscale_id => (
      SELECT tipo_doc_fiscale_id
      FROM tmp_refs_sls
    ),
    p_utility_id => (
      SELECT utility_id
      FROM tmp_refs_sls
    ),
    p_billing_account_id => (
      SELECT billing_account_id
      FROM tmp_refs_sls
    ),
    p_lock_batch_id => NULL,
    p_meta => jsonb_build_object(
      'test_scope',
      (
        SELECT test_scope
        FROM tmp_costanti_sls
      )
    ),
    p_emittente_soggetto_ruolo_id => (
      SELECT emittente_soggetto_ruolo_id
      FROM tmp_refs_sls
    )
  ) AS lotto_id;
SELECT ok(
    (
      SELECT lotto_id IS NOT NULL
        AND lotto_id > 0
      FROM tmp_lotto_sls
    ),
    'Lotto creato'
  );
CREATE TEMP TABLE tmp_fatture_sls AS WITH ins AS (
  INSERT INTO vendite.fatture (
      registro_id,
      data,
      emittente_soggetto_ruolo_id,
      billing_account_id,
      tipo_doc_fiscale_id,
      stato_doc_fiscale_id,
      valuta_id,
      totale_a_pagare,
      critical,
      meta
    )
  SELECT (
      SELECT registro_id
      FROM tmp_refs_sls
    ),
    script.fn_data_operativa(),
    (
      SELECT emittente_soggetto_ruolo_id
      FROM tmp_refs_sls
    ),
    (
      SELECT billing_account_id
      FROM tmp_refs_sls
    ),
    (
      SELECT tipo_doc_fiscale_id
      FROM tmp_refs_sls
    ),
    (
      SELECT stato_draft_id
      FROM tmp_refs_sls
    ),
    (
      SELECT valuta_id
      FROM tmp_refs_sls
    ),
    10.00,
    false,
    jsonb_build_object(
      'test_scope',
      (
        SELECT test_scope
        FROM tmp_costanti_sls
      ),
      'case',
      'ok'
    )
  UNION ALL
  SELECT (
      SELECT registro_id
      FROM tmp_refs_sls
    ),
    script.fn_data_operativa(),
    (
      SELECT emittente_soggetto_ruolo_id
      FROM tmp_refs_sls
    ),
    (
      SELECT billing_account_id
      FROM tmp_refs_sls
    ),
    (
      SELECT tipo_doc_fiscale_id
      FROM tmp_refs_sls
    ),
    (
      SELECT stato_draft_id
      FROM tmp_refs_sls
    ),
    (
      SELECT valuta_id
      FROM tmp_refs_sls
    ),
    12.00,
    true,
    jsonb_build_object(
      'test_scope',
      (
        SELECT test_scope
        FROM tmp_costanti_sls
      ),
      'case',
      'critical'
    )
  RETURNING id,
    critical,
    stato_doc_fiscale_id
)
SELECT *
FROM ins;
SELECT ok(
    (
      SELECT count(*) = 2
      FROM tmp_fatture_sls
    ),
    'Fatture test create'
  );
INSERT INTO vendite.fatturazione_lotti_fatture (
    lotto_id,
    fattura_id,
    stato_doc_fiscale_id,
    stato_esecuzione,
    meta
  )
SELECT (
    SELECT lotto_id
    FROM tmp_lotto_sls
  ),
  f.id,
  f.stato_doc_fiscale_id,
  'PENDING',
  jsonb_build_object(
    'test_scope',
    (
      SELECT test_scope
      FROM tmp_costanti_sls
    )
  )
FROM tmp_fatture_sls f;
SELECT ok(
    (
      SELECT count(*) = 2
      FROM vendite.fatturazione_lotti_fatture lf
      WHERE lf.lotto_id = (
          SELECT lotto_id
          FROM tmp_lotto_sls
        )
    ),
    'Link lotto-fatture creati'
  );
SELECT lives_ok(
    $$
    SELECT vendite.fn_sync_lotto_fatture_stato(
        p_lotto_id => (
          SELECT lotto_id
          FROM tmp_lotto_sls
        ),
        p_target_stato_doc_fiscale_id => (
          SELECT stato_draft_id
          FROM tmp_refs_sls
        )
      );
$$,
'Sync eseguita senza errore'
);
SELECT ok(
    (
      SELECT lf.stato_esecuzione = 'COMPLETED'
      FROM vendite.fatturazione_lotti_fatture lf
        JOIN tmp_fatture_sls f ON f.id = lf.fattura_id
      WHERE lf.lotto_id = (
          SELECT lotto_id
          FROM tmp_lotto_sls
        )
        AND f.critical IS FALSE
      LIMIT 1
    ), 'Fattura non critical => stato_esecuzione COMPLETED'
  );
SELECT ok(
    (
      SELECT lf.stato_esecuzione = 'ERRORE'
      FROM vendite.fatturazione_lotti_fatture lf
        JOIN tmp_fatture_sls f ON f.id = lf.fattura_id
      WHERE lf.lotto_id = (
          SELECT lotto_id
          FROM tmp_lotto_sls
        )
        AND f.critical IS TRUE
      LIMIT 1
    ), 'Fattura critical => stato_esecuzione ERRORE'
  );
SELECT ok(
    (
      SELECT lf.stato_doc_fiscale_id = fa.stato_doc_fiscale_id
      FROM vendite.fatturazione_lotti_fatture lf
        JOIN vendite.fatture fa ON fa.id = lf.fattura_id
        JOIN tmp_fatture_sls f ON f.id = lf.fattura_id
      WHERE lf.lotto_id = (
          SELECT lotto_id
          FROM tmp_lotto_sls
        )
        AND f.critical IS TRUE
      LIMIT 1
    ), 'stato_doc_fiscale ponte allineato alla fattura (critical)'
  );
SELECT ok(
    (
      SELECT lf.stato_doc_fiscale_id = fa.stato_doc_fiscale_id
      FROM vendite.fatturazione_lotti_fatture lf
        JOIN vendite.fatture fa ON fa.id = lf.fattura_id
        JOIN tmp_fatture_sls f ON f.id = lf.fattura_id
      WHERE lf.lotto_id = (
          SELECT lotto_id
          FROM tmp_lotto_sls
        )
        AND f.critical IS FALSE
      LIMIT 1
    ), 'stato_doc_fiscale ponte allineato alla fattura (non critical)'
  );
SELECT *
FROM finish();
ROLLBACK;
