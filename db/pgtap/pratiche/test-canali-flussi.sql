-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: collegamento template_flussi ↔ canali (template_flussi_canali)
--       Verifica UNIQUE constraint e FK
--
-- Indice test:
-- 0) Precondizioni (provisioning canali + verifica)
-- 1) Setup tipo_prestazione e template_flusso
-- 2) INSERT collegamento template_flusso ↔ canale: successo
-- 3) INSERT duplicato (stesso template + canale): violazione UNIQUE
-- 4) Secondo canale per stesso template: successo
-- 5) Verifica FK: canale inesistente → violazione FK
-- 6) Verifica attivo default = true
-- 7) Cleanup
-- ------------------------------------------------------------

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
-- ⚠️ Questo file non apre una transazione propria: la riga va prima di plan().
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(7);

-- =========================================================
-- 0) Precondizioni: provisioning config data (idempotente)
-- =========================================================

INSERT INTO config.canali_pratiche (codice, codice_interno, descrizione, attivo)
VALUES
  ('WEB_CLIENTI',  'WEB_CLIENTI',  'Portale web clienti',  true),
  ('APP_TECNICA',  'APP_TECNICA',  'App tecnica mobile',   true)
ON CONFLICT (codice_interno) DO NOTHING;

CREATE TEMP TABLE tmp_tc_refs AS
SELECT
  (SELECT id FROM config.canali_pratiche WHERE codice_interno = 'WEB_CLIENTI' AND attivo = true LIMIT 1) AS canale1_id,
  (SELECT id FROM config.canali_pratiche WHERE codice_interno = 'APP_TECNICA' AND attivo = true LIMIT 1) AS canale2_id;

SELECT ok(
    (SELECT canale1_id IS NOT NULL AND canale2_id IS NOT NULL FROM tmp_tc_refs),
    '0. Precondizioni soddisfatte: canali WEB_CLIENTI e APP_TECNICA presenti'
);

-- =========================================================
-- 1) Setup tipo_prestazione e template_flusso
-- =========================================================

CREATE TEMP TABLE tmp_tc_tp AS
WITH ins AS (
  INSERT INTO pratiche.tipi_prestazione (codice, codice_interno, descrizione, attivo)
  VALUES ('TEST_CANALI', 'TEST_CANALI', 'Tipo test canali flussi', true)
  ON CONFLICT (codice_interno) DO UPDATE SET descrizione = EXCLUDED.descrizione
  RETURNING id
)
SELECT id AS tp_id FROM ins;

CREATE TEMP TABLE tmp_tc_tf AS
WITH ins AS (
  INSERT INTO pratiche.template_flussi (tipo_prestazione_id, codice, descrizione, attivo)
  VALUES ((SELECT tp_id FROM tmp_tc_tp), 'TF_CANALI_TEST', 'Template test canali', true)
  ON CONFLICT (definizione_id, codice) DO UPDATE SET descrizione = EXCLUDED.descrizione
  RETURNING id
)
SELECT id AS tf_id FROM ins;

SELECT ok(
    (SELECT tf_id IS NOT NULL FROM tmp_tc_tf),
    '1. Setup completato: tipo_prestazione e template_flusso creati'
);

-- =========================================================
-- 2) INSERT collegamento template_flusso ↔ canale: successo
-- =========================================================

CREATE TEMP TABLE tmp_tc_link AS
WITH ins AS (
  INSERT INTO pratiche.template_flussi_canali (template_flusso_id, canale_id)
  VALUES (
    (SELECT tf_id FROM tmp_tc_tf),
    (SELECT canale1_id FROM tmp_tc_refs)
  )
  RETURNING id
)
SELECT id AS link_id FROM ins;

SELECT ok(
    (SELECT link_id IS NOT NULL FROM tmp_tc_link),
    '2. Collegamento template ↔ canale WEB_CLIENTI inserito'
);

-- =========================================================
-- 3) INSERT duplicato (stesso template + canale): violazione UNIQUE
-- =========================================================

SELECT throws_ok(
    format(
      'INSERT INTO pratiche.template_flussi_canali (template_flusso_id, canale_id)
       VALUES (%s, %s)',
      (SELECT tf_id FROM tmp_tc_tf),
      (SELECT canale1_id FROM tmp_tc_refs)
    ),
    '23505',
    NULL,
    '3. Duplicato template + canale bloccato da vincolo UNIQUE'
);

-- =========================================================
-- 4) Secondo canale per stesso template: successo
-- =========================================================

SELECT lives_ok(
    format(
      'INSERT INTO pratiche.template_flussi_canali (template_flusso_id, canale_id)
       VALUES (%s, %s)',
      (SELECT tf_id FROM tmp_tc_tf),
      (SELECT canale2_id FROM tmp_tc_refs)
    ),
    '4. Secondo canale (APP_TECNICA) per stesso template: successo'
);

-- =========================================================
-- 5) Verifica FK: canale inesistente → violazione FK
-- =========================================================

SELECT throws_ok(
    format(
      'INSERT INTO pratiche.template_flussi_canali (template_flusso_id, canale_id)
       VALUES (%s, -999)',
      (SELECT tf_id FROM tmp_tc_tf)
    ),
    '23503',
    NULL,
    '5. FK canale_id violata con canale inesistente'
);

-- =========================================================
-- 6) Verifica attivo default = true
-- =========================================================

SELECT is(
    (SELECT attivo FROM pratiche.template_flussi_canali
      WHERE id = (SELECT link_id FROM tmp_tc_link)),
    true,
    '6. Campo attivo ha default true'
);

-- =========================================================
-- 7) Cleanup
-- =========================================================

DELETE FROM pratiche.template_flussi_canali
 WHERE template_flusso_id = (SELECT tf_id FROM tmp_tc_tf);
DELETE FROM pratiche.template_flussi WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_tc_tp);
DELETE FROM pratiche.tipi_prestazione WHERE id = (SELECT tp_id FROM tmp_tc_tp);

SELECT * FROM finish();
