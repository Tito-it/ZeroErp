-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: ALTER TABLE pratiche.sospensioni DROP CONSTRAINT + riapplicazione via
--   dbops.fn_apply_automazione_overlap(): il soggetto del test E' l'automazione
--   che ricostruisce il vincolo EXCLUDE.
-- pgTAP test per Zero ERP
--
-- Test: anti-overlap + guard data non futura su pratiche.sospensioni
--       (brief-db-sospensioni-anti-overlap-data-manuale_db).
--
-- Oggetti sotto test:
--   - EXCLUDE ex_sospensioni_no_overlap (20260626-01): scope
--     (pratica_id, COALESCE(flusso_id,-1)) su periodo_sospensione, vincolo totale
--   - trgfn_sospensioni_guard_data_non_futura (20260626-02): a10, tolleranza 2 min
--   - registrazione framework dbops.automazione_overlap (20260626-04)
--
-- Indice test:
-- 0)  Precondizioni
-- 1)  Baseline: sospensione pratica storica [now-10d, now-5d) -> ammessa
-- 2)  Overlap pratica [now-7d, now-3d) -> 23P01
-- 3)  Non-overlap pratica [now-20d, now-15d) -> ammessa
-- 4)  Contiguita' [now-5d, now-2d) adiacente alla baseline -> ammessa (bound [))
-- 5)  Sospensione flusso sovrapposta al periodo pratica -> ammessa (scope diverso)
-- 6)  Overlap stesso flusso [now-6d, now-4d) -> 23P01
-- 7)  data_inizio futura -> E_SOSPENSIONE_DATA_FUTURA
-- 8)  UPDATE data_fine futura -> E_SOSPENSIONE_DATA_FUTURA
-- 9)  data_riattivazione_prevista futura -> ammessa (non bloccata)
-- 10) storicizza=true sovrapposta -> 23P01 (vincolo totale, non esenta)
-- 11) anti-regressione: fn_apply ricrea l'EXCLUDE (skip se non registrato)
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

SELECT plan(12);

-- Cleanup preventivo idempotente
DO $$
DECLARE
  v_tp_id INTEGER;
BEGIN
  SELECT id INTO v_tp_id FROM pratiche.tipi_prestazione WHERE codice_interno = 'TEST_SOSP_OVL';
  IF v_tp_id IS NOT NULL THEN
    DELETE FROM pratiche.sospensioni WHERE pratica_id IN (SELECT id FROM pratiche.pratiche WHERE tipo_prestazione_id = v_tp_id);
    DELETE FROM pratiche.giornale    WHERE pratica_id IN (SELECT id FROM pratiche.pratiche WHERE tipo_prestazione_id = v_tp_id);
    DELETE FROM pratiche.flussi      WHERE pratica_id IN (SELECT id FROM pratiche.pratiche WHERE tipo_prestazione_id = v_tp_id);
    DELETE FROM pratiche.pratiche    WHERE tipo_prestazione_id = v_tp_id;
    DELETE FROM pratiche.template_flussi WHERE tipo_prestazione_id = v_tp_id;
    DELETE FROM pratiche.tipi_prestazione WHERE id = v_tp_id;
  END IF;
END $$;

-- =========================================================
-- 0) Precondizioni
-- =========================================================
CREATE TEMP TABLE tmp_so_refs AS
SELECT
  script.fn_pgtap_emittente_operatore() AS emittente_id,
  (SELECT id FROM anagrafiche.soggetti ORDER BY id LIMIT 1) AS soggetto_id,
  (SELECT id FROM config.stati_pratiche WHERE codice_interno = 'BOZZA')  AS st_bozza,
  (SELECT id FROM config.stati_pratiche WHERE codice_interno = 'APERTA') AS st_aperta,
  (SELECT id FROM config.stati_flussi_pratiche WHERE codice_interno = 'DA_ESEGUIRE') AS sf_da_eseguire,
  (SELECT id FROM config.priorita_pratiche WHERE codice_interno = 'NORMALE') AS priorita_id;

SELECT ok(
  (SELECT emittente_id IS NOT NULL AND soggetto_id IS NOT NULL
      AND st_bozza IS NOT NULL AND st_aperta IS NOT NULL
      AND sf_da_eseguire IS NOT NULL AND priorita_id IS NOT NULL
   FROM tmp_so_refs),
  '0. Precondizioni soddisfatte'
);

-- Setup: tipo_prestazione + 2 template_flussi + pratica APERTA + 2 flussi
CREATE TEMP TABLE tmp_so_tp AS
WITH ins AS (
  INSERT INTO pratiche.tipi_prestazione (codice, codice_interno, descrizione, attivo)
  VALUES ('TEST_SOSP_OVL', 'TEST_SOSP_OVL', 'Tipo test sospensioni anti-overlap', true)
  ON CONFLICT (codice_interno) DO UPDATE SET descrizione = EXCLUDED.descrizione
  RETURNING id
)
SELECT id AS tp_id FROM ins;

CREATE TEMP TABLE tmp_so_tpl AS
WITH t1 AS (
  INSERT INTO pratiche.template_flussi (tipo_prestazione_id, codice, descrizione, sequenza, attivo)
  VALUES ((SELECT tp_id FROM tmp_so_tp), 'STEP_1', 'Step 1', 1, true)
  ON CONFLICT (definizione_id, codice) DO UPDATE SET descrizione = EXCLUDED.descrizione
  RETURNING id
),
t2 AS (
  INSERT INTO pratiche.template_flussi (tipo_prestazione_id, codice, descrizione, sequenza, attivo)
  VALUES ((SELECT tp_id FROM tmp_so_tp), 'STEP_2', 'Step 2', 2, true)
  ON CONFLICT (definizione_id, codice) DO UPDATE SET descrizione = EXCLUDED.descrizione
  RETURNING id
)
SELECT (SELECT id FROM t1) AS tpl1_id, (SELECT id FROM t2) AS tpl2_id;

CREATE TEMP TABLE tmp_so_pratica AS
WITH ins AS (
  INSERT INTO pratiche.pratiche (emittente_fiscale_id, tipo_prestazione_id, soggetto_id, stato_id, priorita_id)
  VALUES (
    (SELECT emittente_id FROM tmp_so_refs),
    (SELECT tp_id FROM tmp_so_tp),
    (SELECT soggetto_id FROM tmp_so_refs),
    (SELECT st_bozza FROM tmp_so_refs),
    (SELECT priorita_id FROM tmp_so_refs)
  )
  RETURNING id
)
SELECT id AS pratica_id FROM ins;

UPDATE pratiche.pratiche
SET stato_id = (SELECT st_aperta FROM tmp_so_refs)
WHERE id = (SELECT pratica_id FROM tmp_so_pratica);

CREATE TEMP TABLE tmp_so_flussi AS
WITH f1 AS (
  INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id, sequenza)
  VALUES ((SELECT pratica_id FROM tmp_so_pratica), (SELECT tpl1_id FROM tmp_so_tpl),
          (SELECT sf_da_eseguire FROM tmp_so_refs), 1)
  RETURNING id
),
f2 AS (
  INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id, sequenza)
  VALUES ((SELECT pratica_id FROM tmp_so_pratica), (SELECT tpl2_id FROM tmp_so_tpl),
          (SELECT sf_da_eseguire FROM tmp_so_refs), 2)
  RETURNING id
)
SELECT (SELECT id FROM f1) AS flusso1_id, (SELECT id FROM f2) AS flusso2_id;

-- =========================================================
-- 1) Baseline: sospensione pratica storica [now-10d, now-5d) -> ammessa
-- =========================================================
SELECT lives_ok(
  format(
    $$INSERT INTO pratiche.sospensioni (pratica_id, flusso_id, data_inizio, data_fine, motivo)
      VALUES (%s, NULL, now() - interval '10 days', now() - interval '5 days', 'test baseline')$$,
    (SELECT pratica_id FROM tmp_so_pratica)),
  '1. Baseline: sospensione pratica storica ammessa'
);

-- =========================================================
-- 2) Overlap pratica [now-7d, now-3d) -> 23P01
-- =========================================================
SELECT throws_ok(
  format(
    $$INSERT INTO pratiche.sospensioni (pratica_id, flusso_id, data_inizio, data_fine, motivo)
      VALUES (%s, NULL, now() - interval '7 days', now() - interval '3 days', 'test overlap')$$,
    (SELECT pratica_id FROM tmp_so_pratica)),
  '23P01', NULL,
  '2. Overlap pratica stesso scope -> exclusion_violation'
);

-- =========================================================
-- 3) Non-overlap pratica [now-20d, now-15d) -> ammessa
-- =========================================================
SELECT lives_ok(
  format(
    $$INSERT INTO pratiche.sospensioni (pratica_id, flusso_id, data_inizio, data_fine, motivo)
      VALUES (%s, NULL, now() - interval '20 days', now() - interval '15 days', 'test disgiunta')$$,
    (SELECT pratica_id FROM tmp_so_pratica)),
  '3. Sospensione pratica disgiunta ammessa'
);

-- =========================================================
-- 4) Contiguita' [now-5d, now-2d) adiacente alla baseline -> ammessa (bound [))
-- =========================================================
SELECT lives_ok(
  format(
    $$INSERT INTO pratiche.sospensioni (pratica_id, flusso_id, data_inizio, data_fine, motivo)
      VALUES (%s, NULL, now() - interval '5 days', now() - interval '2 days', 'test contigua')$$,
    (SELECT pratica_id FROM tmp_so_pratica)),
  '4. Periodi contigui [A,B)/[B,C) ammessi (no overlap su bound esclusivo)'
);

-- =========================================================
-- 5) Sospensione flusso sovrapposta al periodo pratica -> ammessa (scope diverso)
-- =========================================================
SELECT lives_ok(
  format(
    $$INSERT INTO pratiche.sospensioni (pratica_id, flusso_id, data_inizio, data_fine, motivo)
      VALUES (%s, %s, now() - interval '7 days', now() - interval '3 days', 'test flusso vs pratica')$$,
    (SELECT pratica_id FROM tmp_so_pratica),
    (SELECT flusso1_id FROM tmp_so_flussi)),
  '5. Sospensione flusso sovrapposta a quella di pratica -> ammessa (assi indipendenti)'
);

-- =========================================================
-- 6) Overlap stesso flusso [now-6d, now-4d) -> 23P01
-- =========================================================
SELECT throws_ok(
  format(
    $$INSERT INTO pratiche.sospensioni (pratica_id, flusso_id, data_inizio, data_fine, motivo)
      VALUES (%s, %s, now() - interval '6 days', now() - interval '4 days', 'test overlap flusso')$$,
    (SELECT pratica_id FROM tmp_so_pratica),
    (SELECT flusso1_id FROM tmp_so_flussi)),
  '23P01', NULL,
  '6. Overlap stesso flusso -> exclusion_violation'
);

-- =========================================================
-- 7) data_inizio futura -> E_SOSPENSIONE_DATA_FUTURA
-- =========================================================
SELECT throws_ok(
  format(
    $$INSERT INTO pratiche.sospensioni (pratica_id, flusso_id, data_inizio, data_fine, motivo)
      VALUES (%s, %s, now() + interval '2 days', NULL, 'test data inizio futura')$$,
    (SELECT pratica_id FROM tmp_so_pratica),
    (SELECT flusso2_id FROM tmp_so_flussi)),
  NULL, NULL,
  '7. data_inizio nel futuro -> errore data futura'
);

-- =========================================================
-- 8) UPDATE data_fine futura -> E_SOSPENSIONE_DATA_FUTURA
--    (setup: sospensione flusso2 aperta storica, poi chiusura nel futuro)
-- =========================================================
CREATE TEMP TABLE tmp_so_aperta AS
WITH ins AS (
  INSERT INTO pratiche.sospensioni (pratica_id, flusso_id, data_inizio, data_fine, motivo)
  VALUES ((SELECT pratica_id FROM tmp_so_pratica), (SELECT flusso2_id FROM tmp_so_flussi),
          now() - interval '1 day', NULL, 'test aperta flusso2')
  RETURNING id
)
SELECT id AS sosp_id FROM ins;

SELECT throws_ok(
  format(
    $$UPDATE pratiche.sospensioni SET data_fine = now() + interval '10 days' WHERE id = %s$$,
    (SELECT sosp_id FROM tmp_so_aperta)),
  NULL, NULL,
  '8. UPDATE data_fine nel futuro -> errore data futura'
);

-- =========================================================
-- 9) data_riattivazione_prevista futura -> ammessa
-- =========================================================
SELECT lives_ok(
  format(
    $$INSERT INTO pratiche.sospensioni
        (pratica_id, flusso_id, data_inizio, data_fine, data_riattivazione_prevista, motivo)
      VALUES (%s, NULL, now() - interval '40 days', now() - interval '38 days',
              (script.fn_data_operativa() + 30), 'test prevista futura')$$,
    (SELECT pratica_id FROM tmp_so_pratica)),
  '9. data_riattivazione_prevista nel futuro -> ammessa (previsione, non bloccata)'
);

-- =========================================================
-- 10) storicizza=true sovrapposta -> 23P01 (vincolo totale)
-- =========================================================
SELECT throws_ok(
  format(
    $$INSERT INTO pratiche.sospensioni (pratica_id, flusso_id, data_inizio, data_fine, storicizza, motivo)
      VALUES (%s, NULL, now() - interval '9 days', now() - interval '6 days', true, 'test storicizza overlap')$$,
    (SELECT pratica_id FROM tmp_so_pratica)),
  '23P01', NULL,
  '10. storicizza=true non esenta dall''overlap -> exclusion_violation'
);

-- =========================================================
-- 11) Anti-regressione framework: fn_apply ricrea l'EXCLUDE
--     (skip se la riga non e' registrata in questo ambiente)
-- =========================================================
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM dbops.automazione_overlap
     WHERE target_schema = 'pratiche' AND target_table = 'sospensioni' AND active
  ) THEN
    ALTER TABLE pratiche.sospensioni DROP CONSTRAINT ex_sospensioni_no_overlap;
    PERFORM dbops.fn_apply_automazione_overlap('SCHEDULED', false);
  END IF;
END $$;

SELECT CASE
  WHEN EXISTS (
    SELECT 1 FROM dbops.automazione_overlap
     WHERE target_schema = 'pratiche' AND target_table = 'sospensioni' AND active
  )
  THEN is(
    (SELECT COUNT(*)::int
       FROM pg_constraint con
       JOIN pg_class c     ON c.oid = con.conrelid
       JOIN pg_namespace n ON n.oid = c.relnamespace
      WHERE n.nspname = 'pratiche' AND c.relname = 'sospensioni'
        AND con.conname = 'ex_sospensioni_no_overlap' AND con.contype = 'x'),
    1,
    '11. Anti-regressione: fn_apply_automazione_overlap ricrea l''EXCLUDE'
  )
  ELSE skip('11. automazione_overlap non registrato in questo ambiente', 1)
END;

SELECT * FROM finish();
ROLLBACK;
