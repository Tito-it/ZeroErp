-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: trigger sync automatico da vendite.fatture_log
-- ------------------------------------------------------------
-- Indice test
-- 1) Riferimenti minimi presenti
-- 2) Lotto aperto creato
-- 3) Fattura test creata e collegata al lotto
-- 4) Inserimento log critical attivo -> fattura.critical = true
-- 5) Inserimento log critical attivo -> stato_esecuzione = ERRORE
-- 6) Disabilitazione log critical -> fattura.critical = false
-- 7) Disabilitazione log critical -> stato_esecuzione = RUNNING
-- 8) Lotto fuori perimetro + log critical -> stato_esecuzione non cambia
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

SELECT plan(8);
CREATE TEMP TABLE tmp_costanti_flts AS
SELECT (
    'pgtap_flts_' || to_char(clock_timestamp(), 'YYMMDDHH24MISS')
  )::text AS test_scope;
-- rev 2026-10-27 (lotto 4 di D7): il cliente si COSTRUISCE
--   (dbops.fn_pgtap_crea_cliente_ba) e l'emittente e' quello di chi agisce
--   (script.fn_pgtap_emittente_sr_operatore); il tipo documento si legge dal
--   catalogo di seed config.tipi_doc_fiscale. Prima BA, utility ed emittente
--   si pescavano dal primo billing account con un emittente, e tipo/registro
--   dalla prima mappatura tipi_doc_fiscale_registri: da zero non c'erano.
CREATE TEMP TABLE tmp_cli_flts AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('fatture log trigger sync');

-- ⛔ IL REGISTRO SI ALLINEA ALL'EMITTENTE: dal 2026-08-30
--   vendite.trgfn_fatture_guard_registro_emittente non ammette «un registro
--   qualunque». L'helper risponde con il registro di QUESTO emittente,
--   creandolo se non ce n'e' uno — la riga vive nella transazione del test.
CREATE TEMP TABLE tmp_refs_flts AS
SELECT script.fn_pgtap_registro_fattura(script.fn_pgtap_emittente_sr_operatore()) AS registro_id,
  (
    SELECT t.id
    FROM config.tipi_doc_fiscale t
    WHERE t.attivo IS TRUE
    ORDER BY t.id
    LIMIT 1
  ) AS tipo_doc_fiscale_id,
  (SELECT billing_account_id FROM tmp_cli_flts) AS billing_account_id,
  (SELECT utility_id FROM tmp_cli_flts) AS utility_id,
  script.fn_pgtap_emittente_sr_operatore() AS emittente_soggetto_ruolo_id,
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
        AND tipo_doc_fiscale_id IS NOT NULL
        AND billing_account_id IS NOT NULL
        AND utility_id IS NOT NULL
        AND emittente_soggetto_ruolo_id IS NOT NULL
        AND valuta_id IS NOT NULL
        AND stato_draft_id IS NOT NULL
      FROM tmp_refs_flts
    ),
    'Riferimenti minimi presenti'
  );
CREATE TEMP TABLE tmp_lotto_flts AS
SELECT vendite.fn_create_fatturazione_lotto(
    p_competenza_mese => date_trunc('month', script.fn_data_operativa())::date,
    p_tipo_doc_fiscale_id => (
      SELECT tipo_doc_fiscale_id
      FROM tmp_refs_flts
    ),
    p_utility_id => (
      SELECT utility_id
      FROM tmp_refs_flts
    ),
    p_billing_account_id => (
      SELECT billing_account_id
      FROM tmp_refs_flts
    ),
    p_lock_batch_id => NULL,
    p_meta => jsonb_build_object(
      'test_scope',
      (
        SELECT test_scope
        FROM tmp_costanti_flts
      )
    ),
    p_emittente_soggetto_ruolo_id => (
      SELECT emittente_soggetto_ruolo_id
      FROM tmp_refs_flts
    )
  ) AS lotto_id;
SELECT ok(
    (
      SELECT lotto_id IS NOT NULL
        AND lotto_id > 0
      FROM tmp_lotto_flts
    ),
    'Lotto aperto creato'
  );
CREATE TEMP TABLE tmp_fattura_flts AS WITH ins AS (
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
      FROM tmp_refs_flts
    ),
    script.fn_data_operativa(),
    (
      SELECT emittente_soggetto_ruolo_id
      FROM tmp_refs_flts
    ),
    (
      SELECT billing_account_id
      FROM tmp_refs_flts
    ),
    (
      SELECT tipo_doc_fiscale_id
      FROM tmp_refs_flts
    ),
    (
      SELECT stato_draft_id
      FROM tmp_refs_flts
    ),
    (
      SELECT valuta_id
      FROM tmp_refs_flts
    ),
    25.00,
    false,
    jsonb_build_object(
      'test_scope',
      (
        SELECT test_scope
        FROM tmp_costanti_flts
      )
    )
  RETURNING id
)
SELECT id
FROM ins;
INSERT INTO vendite.fatturazione_lotti_fatture (
    lotto_id,
    fattura_id,
    stato_doc_fiscale_id,
    stato_esecuzione,
    meta
  )
SELECT (
    SELECT lotto_id
    FROM tmp_lotto_flts
  ),
  (
    SELECT id
    FROM tmp_fattura_flts
  ),
  (
    SELECT stato_draft_id
    FROM tmp_refs_flts
  ),
  'PENDING',
  jsonb_build_object(
    'test_scope',
    (
      SELECT test_scope
      FROM tmp_costanti_flts
    )
  );
SELECT ok(
    (
      SELECT EXISTS (
          SELECT 1
          FROM vendite.fatturazione_lotti_fatture lf
          WHERE lf.lotto_id = (
              SELECT lotto_id
              FROM tmp_lotto_flts
            )
            AND lf.fattura_id = (
              SELECT id
              FROM tmp_fattura_flts
            )
        )
    ),
    'Fattura test creata e collegata al lotto'
  );
CREATE TEMP TABLE tmp_log_flts AS
WITH ins AS (
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
      FROM tmp_fattura_flts
    ),
    now(),
    'Errore test trigger sync',
    'C',
    false,
    jsonb_build_object(
      'test_scope',
      (
        SELECT test_scope
        FROM tmp_costanti_flts
      ),
      'case',
      'critical_insert'
    )
  RETURNING id
)
SELECT id
FROM ins;
SELECT ok(
    (
      SELECT f.critical IS TRUE
      FROM vendite.fatture f
      WHERE f.id = (
          SELECT id
          FROM tmp_fattura_flts
        )
    ),
    'Inserimento log critical attivo -> fattura.critical = true'
  );
SELECT ok(
    (
      SELECT lf.stato_esecuzione = 'ERRORE'
      FROM vendite.fatturazione_lotti_fatture lf
      WHERE lf.lotto_id = (
          SELECT lotto_id
          FROM tmp_lotto_flts
        )
        AND lf.fattura_id = (
          SELECT id
          FROM tmp_fattura_flts
        )
    ),
    'Inserimento log critical attivo -> stato_esecuzione = ERRORE'
  );
UPDATE vendite.fatture_log
SET disabilitato = true,
  data_update = now(),
  user_update = current_user
WHERE id = (
    SELECT id
    FROM tmp_log_flts
  );
SELECT ok(
    (
      SELECT f.critical IS FALSE
      FROM vendite.fatture f
      WHERE f.id = (
          SELECT id
          FROM tmp_fattura_flts
        )
    ),
    'Disabilitazione log critical -> fattura.critical = false'
  );
SELECT ok(
    (
      SELECT lf.stato_esecuzione = 'RUNNING'
      FROM vendite.fatturazione_lotti_fatture lf
      WHERE lf.lotto_id = (
          SELECT lotto_id
          FROM tmp_lotto_flts
        )
        AND lf.fattura_id = (
          SELECT id
          FROM tmp_fattura_flts
        )
    ),
    'Disabilitazione log critical -> stato_esecuzione = RUNNING'
  );
UPDATE vendite.fatturazione_lotti
SET stato_lotto = 'COMPLETATO',
  stato_operativo = 'CHIUSO',
  data_update = now(),
  user_update = current_user
WHERE id = (
    SELECT lotto_id
    FROM tmp_lotto_flts
  );
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
    FROM tmp_fattura_flts
  ),
  now(),
  'Errore fuori perimetro lotto',
  'C',
  false,
  jsonb_build_object(
    'test_scope',
    (
      SELECT test_scope
      FROM tmp_costanti_flts
    ),
    'case',
    'out_of_scope'
  );
SELECT ok(
    (
      SELECT lf.stato_esecuzione = 'RUNNING'
      FROM vendite.fatturazione_lotti_fatture lf
      WHERE lf.lotto_id = (
          SELECT lotto_id
          FROM tmp_lotto_flts
        )
        AND lf.fattura_id = (
          SELECT id
          FROM tmp_fattura_flts
        )
    ),
    'Lotto fuori perimetro + log critical -> stato_esecuzione non cambia'
  );
SELECT *
FROM finish();
ROLLBACK;
