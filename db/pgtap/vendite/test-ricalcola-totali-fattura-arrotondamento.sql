-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: ricalcolo totali fattura con arrotondamenti/minimo
-- ------------------------------------------------------------
-- Indice test
-- 1) Riferimenti minimi presenti
-- 2) Inserimento config emittente_fiscale_utilities
-- 3) Inserimento fattura e riepilogo IVA
-- 4) Ricalcolo totali con arrotondamento (decimali=0)
-- 5) Aggiornamento minimo su soglia
-- 6) Ricalcolo senza arrotondamento (decimali=NULL)
-- ------------------------------------------------------------

BEGIN;

SELECT plan(6);

-- ============================================================
-- 0) Riferimenti e costanti
-- ============================================================
CREATE TEMP TABLE tmp_costanti_rt AS
SELECT 'pgtap_ricalcola_totali_arrotondamento'::text AS test_scope;

CREATE TEMP TABLE tmp_refs_rt AS
SELECT
  (SELECT id FROM vendite.registri_fatturazione WHERE attivo IS TRUE ORDER BY id LIMIT 1) AS registro_id,
  (SELECT id FROM anagrafiche.billing_account ORDER BY id LIMIT 1) AS billing_account_id,
  (SELECT utility_id FROM anagrafiche.billing_account ORDER BY id LIMIT 1) AS utility_id,
  (SELECT id FROM config.tipi_doc_fiscale WHERE attivo IS TRUE ORDER BY id LIMIT 1) AS tipo_doc_fiscale_id,
  (SELECT id FROM config.valute ORDER BY id LIMIT 1) AS valuta_id,
  (SELECT emittente_soggetto_ruolo_id FROM vendite.fatture WHERE emittente_soggetto_ruolo_id IS NOT NULL ORDER BY id LIMIT 1) AS emittente_soggetto_ruolo_id;

SELECT ok(
  (SELECT registro_id IS NOT NULL
     AND billing_account_id IS NOT NULL
     AND utility_id IS NOT NULL
     AND tipo_doc_fiscale_id IS NOT NULL
     AND valuta_id IS NOT NULL
     AND emittente_soggetto_ruolo_id IS NOT NULL
   FROM tmp_refs_rt),
  'Riferimenti minimi presenti'
);

-- ============================================================
-- 1) Config emittente/utility (decimali=0)
-- ============================================================
CREATE TEMP TABLE tmp_conf_rt AS
WITH ins AS (
  INSERT INTO anagrafiche.emittenti_fiscali_utilities (
    emittente_soggetto_ruolo_id,
    utility_id,
    minimo_soglia_min,
    minimo_soglia_max,
    arrotondamento_importi_dec,
    metodo_arrotondamento_importi,
    meta
  )
  SELECT
    (SELECT emittente_soggetto_ruolo_id FROM tmp_refs_rt),
    (SELECT utility_id FROM tmp_refs_rt),
    9.00,
    12.00,
    0,
    'HALF_UP',
    jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_rt))
  RETURNING id
)
SELECT * FROM ins;

SELECT ok(
  (SELECT id IS NOT NULL FROM tmp_conf_rt),
  'Inserimento config emittente/utility'
);

-- ============================================================
-- 2) Fattura + riepilogo IVA
-- ============================================================
CREATE TEMP TABLE tmp_fattura_rt AS
WITH ins AS (
  INSERT INTO vendite.fatture (
    registro_id,
    data,
    emittente_soggetto_ruolo_id,
    billing_account_id,
    tipo_doc_fiscale_id,
    valuta_id,
    meta
  )
  SELECT
    (SELECT registro_id FROM tmp_refs_rt),
    current_date,
    (SELECT emittente_soggetto_ruolo_id FROM tmp_refs_rt),
    (SELECT billing_account_id FROM tmp_refs_rt),
    (SELECT tipo_doc_fiscale_id FROM tmp_refs_rt),
    (SELECT valuta_id FROM tmp_refs_rt),
    jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_rt))
  RETURNING id
)
SELECT * FROM ins;

INSERT INTO vendite.fatture_riepiloghi_iva (
  fattura_id,
  imponibile,
  imposta,
  arrotondamento
)
SELECT
  (SELECT id FROM tmp_fattura_rt),
  10.50,
  0.71,
  0;

-- ============================================================
-- 3) Ricalcolo con arrotondamento (decimali=0)
-- ============================================================
SELECT ok(
  (SELECT 1 FROM vendite.fn_ricalcola_totali_fattura((SELECT id FROM tmp_fattura_rt)) LIMIT 1) IS NOT NULL,
  'Ricalcolo totali con arrotondamento'
);

SELECT ok(
  (SELECT minimo
     FROM vendite.fatture
    WHERE id = (SELECT id FROM tmp_fattura_rt)) IS TRUE,
  'Minimo impostato in base a soglia'
);

-- ============================================================
-- 4) Ricalcolo senza arrotondamento (decimali=NULL)
-- ============================================================
UPDATE anagrafiche.emittenti_fiscali_utilities
SET arrotondamento_importi_dec = NULL
WHERE id = (SELECT id FROM tmp_conf_rt);

SELECT ok(
  (SELECT 1 FROM vendite.fn_ricalcola_totali_fattura((SELECT id FROM tmp_fattura_rt)) LIMIT 1) IS NOT NULL,
  'Ricalcolo totali senza arrotondamento'
);

-- ============================================================
-- Cleanup
-- ============================================================
UPDATE vendite.fatture
SET storicizza = false
WHERE meta ->> 'test_scope' = (SELECT test_scope FROM tmp_costanti_rt);

DELETE FROM vendite.fatture_riepiloghi_iva
WHERE fattura_id = (SELECT id FROM tmp_fattura_rt);

DELETE FROM vendite.fatture
WHERE meta ->> 'test_scope' = (SELECT test_scope FROM tmp_costanti_rt);

DELETE FROM anagrafiche.emittenti_fiscali_utilities
WHERE meta ->> 'test_scope' = (SELECT test_scope FROM tmp_costanti_rt);

SELECT ok(true, 'Cleanup completato');

SELECT * FROM finish();

ROLLBACK;
