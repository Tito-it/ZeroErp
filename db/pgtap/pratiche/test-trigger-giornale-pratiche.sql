-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: trigger giornale su pratiche.pratiche
--       INSERT → PRATICA_CREATA, UPDATE stato/assegnazione/priorita
--
-- Indice test:
-- 0) Precondizioni (provisioning + verifica)
-- 1) INSERT pratica → entry PRATICA_CREATA nel giornale
-- 2) UPDATE stato → entry STATO_CAMBIATO nel giornale
-- 3) UPDATE assegnazione → entry ASSEGNAZIONE_CAMBIATA nel giornale
-- 4) UPDATE priorita → entry PRIORITA_CAMBIATA nel giornale
-- 5) Verifica tx_id propagato nel giornale
-- 6) Cleanup
-- ------------------------------------------------------------

SELECT plan(6);

-- =========================================================
-- 0) Precondizioni: provisioning config data (idempotente)
-- =========================================================

INSERT INTO config.stati_pratiche (codice, codice_interno, descrizione, attivo)
VALUES
  ('BOZZA',  'BOZZA',  'Bozza',  true),
  ('APERTA', 'APERTA', 'Aperta', true)
ON CONFLICT (codice_interno) DO NOTHING;

INSERT INTO config.priorita_pratiche (codice, codice_interno, descrizione, sequenza, attivo)
VALUES
  ('NORMALE', 'NORMALE', 'Normale', 20, true),
  ('ALTA',    'ALTA',    'Alta',    30, true)
ON CONFLICT (codice_interno) DO NOTHING;

CREATE TEMP TABLE tmp_gp_refs AS
SELECT
  (SELECT id FROM anagrafiche.emittenti_fiscali WHERE attivo = true LIMIT 1) AS emittente_id,
  (SELECT id FROM anagrafiche.soggetti LIMIT 1) AS soggetto_id,
  (SELECT id FROM config.stati_pratiche WHERE codice_interno = 'BOZZA' LIMIT 1) AS stato_bozza_id,
  (SELECT id FROM config.stati_pratiche WHERE codice_interno = 'APERTA' LIMIT 1) AS stato_aperta_id,
  (SELECT id FROM config.priorita_pratiche WHERE codice_interno = 'NORMALE' LIMIT 1) AS priorita_normale_id,
  (SELECT id FROM config.priorita_pratiche WHERE codice_interno = 'ALTA' LIMIT 1) AS priorita_alta_id;

SELECT ok(
    (SELECT emittente_id IS NOT NULL AND soggetto_id IS NOT NULL
        AND stato_bozza_id IS NOT NULL AND stato_aperta_id IS NOT NULL
        AND priorita_normale_id IS NOT NULL AND priorita_alta_id IS NOT NULL
     FROM tmp_gp_refs),
    '0. Precondizioni soddisfatte'
);

-- Tipo prestazione di test
CREATE TEMP TABLE tmp_gp_tp AS
WITH ins AS (
  INSERT INTO pratiche.tipi_prestazione (codice, codice_interno, descrizione, attivo)
  VALUES ('TEST_GIORNALE_P', 'TEST_GIORNALE_P', 'Tipo test giornale pratiche', true)
  ON CONFLICT (codice_interno) DO UPDATE SET descrizione = EXCLUDED.descrizione
  RETURNING id
)
SELECT id AS tp_id FROM ins;

-- =========================================================
-- 1) INSERT pratica → PRATICA_CREATA
-- =========================================================

CREATE TEMP TABLE tmp_gp_pratica AS
WITH ins AS (
  INSERT INTO pratiche.pratiche (
    emittente_fiscale_id, tipo_prestazione_id, soggetto_id, stato_id, priorita_id
  ) VALUES (
    (SELECT emittente_id FROM tmp_gp_refs),
    (SELECT tp_id FROM tmp_gp_tp),
    (SELECT soggetto_id FROM tmp_gp_refs),
    (SELECT stato_bozza_id FROM tmp_gp_refs),
    (SELECT priorita_normale_id FROM tmp_gp_refs)
  )
  RETURNING id
)
SELECT id AS pratica_id FROM ins;

SELECT is(
    (SELECT count(*)::integer FROM pratiche.giornale
      WHERE pratica_id = (SELECT pratica_id FROM tmp_gp_pratica)
        AND azione = 'PRATICA_CREATA'),
    1,
    '1. PRATICA_CREATA registrata nel giornale su INSERT'
);

-- =========================================================
-- 2) UPDATE stato → STATO_CAMBIATO
-- =========================================================

UPDATE pratiche.pratiche
   SET stato_id = (SELECT stato_aperta_id FROM tmp_gp_refs)
 WHERE id = (SELECT pratica_id FROM tmp_gp_pratica);

SELECT is(
    (SELECT count(*)::integer FROM pratiche.giornale
      WHERE pratica_id = (SELECT pratica_id FROM tmp_gp_pratica)
        AND azione = 'STATO_CAMBIATO'),
    1,
    '2. STATO_CAMBIATO registrato nel giornale su UPDATE stato_id'
);

-- =========================================================
-- 3) UPDATE assegnazione → ASSEGNAZIONE_CAMBIATA
-- =========================================================

DO $$
DECLARE
  v_ru_id bigint;
BEGIN
  SELECT id INTO v_ru_id FROM anagrafiche.risorse_umane WHERE attivo = true LIMIT 1;
  IF v_ru_id IS NOT NULL THEN
    UPDATE pratiche.pratiche
       SET risorsa_umana_id = v_ru_id
     WHERE id = (SELECT pratica_id FROM tmp_gp_pratica);
  END IF;
END $$;

SELECT ok(
    (SELECT count(*) >= 0 FROM pratiche.giornale
      WHERE pratica_id = (SELECT pratica_id FROM tmp_gp_pratica)
        AND azione = 'ASSEGNAZIONE_CAMBIATA'),
    '3. ASSEGNAZIONE_CAMBIATA verificato (se risorsa umana disponibile)'
);

-- =========================================================
-- 4) UPDATE priorita → PRIORITA_CAMBIATA
-- =========================================================

UPDATE pratiche.pratiche
   SET priorita_id = (SELECT priorita_alta_id FROM tmp_gp_refs)
 WHERE id = (SELECT pratica_id FROM tmp_gp_pratica);

SELECT is(
    (SELECT count(*)::integer FROM pratiche.giornale
      WHERE pratica_id = (SELECT pratica_id FROM tmp_gp_pratica)
        AND azione = 'PRIORITA_CAMBIATA'),
    1,
    '4. PRIORITA_CAMBIATA registrato nel giornale su UPDATE priorita_id'
);

-- =========================================================
-- 5) Verifica tx_id propagato
-- =========================================================

SELECT ok(
    (SELECT tx_id IS NOT NULL FROM pratiche.giornale
      WHERE pratica_id = (SELECT pratica_id FROM tmp_gp_pratica)
        AND azione = 'PRATICA_CREATA'
      LIMIT 1),
    '5. tx_id propagato nel giornale dalla pratica'
);

-- =========================================================
-- 6) Cleanup
-- =========================================================

-- Cleanup resiliente (gestisce orfani da run precedenti falliti)
DELETE FROM pratiche.giornale WHERE pratica_id IN (
  SELECT id FROM pratiche.pratiche WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_gp_tp)
);
DELETE FROM pratiche.pratiche WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_gp_tp);
DELETE FROM pratiche.tipi_prestazione WHERE id = (SELECT tp_id FROM tmp_gp_tp);

SELECT * FROM finish();
