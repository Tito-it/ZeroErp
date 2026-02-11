-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: generazione e applicazione fondi fattura
-- ------------------------------------------------------------
-- Indice test
-- 1) Riferimenti minimi presenti
-- 2) Inserimento tipo_fondo_fattura
-- 3) Inserimento fattura sorgente (minimo)
-- 4) Generazione fondi source
-- 5) Inserimento fattura figlia
-- 6) Applicazione fondi fattura
-- 7) Source aggiornata e righe fondi presenti
-- 8) Reset fondi fattura
-- 9) Source ripristinata e righe fondi rimosse
-- ------------------------------------------------------------

BEGIN;

SELECT plan(9);

-- ============================================================
-- 0) Riferimenti e costanti
-- ============================================================
CREATE TEMP TABLE tmp_costanti_ff AS
SELECT
  'pgtap_fondi_fattura'::text AS test_scope;

CREATE TEMP TABLE tmp_refs_ff AS
SELECT
  (SELECT id
     FROM vendite.registri_fatturazione
    WHERE attivo IS TRUE
    ORDER BY data_insert DESC NULLS LAST
    LIMIT 1) AS registro_id,
  (SELECT id
     FROM anagrafiche.billing_account
    ORDER BY data_insert DESC NULLS LAST
    LIMIT 1) AS billing_account_id,
  (SELECT utility_id
     FROM anagrafiche.billing_account
    ORDER BY data_insert DESC NULLS LAST
    LIMIT 1) AS utility_id,
  (SELECT id
     FROM config.tipi_doc_fiscale
    WHERE attivo IS TRUE
    ORDER BY id
    LIMIT 1) AS tipo_doc_fiscale_id,
  (SELECT id
     FROM config.valute
    ORDER BY id
    LIMIT 1) AS valuta_id,
  (SELECT emittente_soggetto_ruolo_id
     FROM vendite.fatture
    WHERE emittente_soggetto_ruolo_id IS NOT NULL
    ORDER BY data_insert DESC NULLS LAST
    LIMIT 1) AS emittente_soggetto_ruolo_id;

SELECT ok(
  (SELECT registro_id IS NOT NULL
     AND billing_account_id IS NOT NULL
     AND utility_id IS NOT NULL
     AND tipo_doc_fiscale_id IS NOT NULL
     AND valuta_id IS NOT NULL
     AND emittente_soggetto_ruolo_id IS NOT NULL
   FROM tmp_refs_ff),
  'Riferimenti minimi presenti'
);

-- ============================================================
-- 1) Tipo fondo fattura
-- ============================================================
CREATE TEMP TABLE tmp_tipo_fondo AS
WITH ins AS (
  INSERT INTO vendite.tipi_fondi_fattura (
    codice,
    codice_interno,
    descrizione,
    meta
  )
  SELECT
    'TEST_FONDO',
    'F_F_ADD_ACC',
    'Fondo test pgtap',
    jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_ff))
  RETURNING id
)
SELECT * FROM ins;

SELECT ok(
  (SELECT id IS NOT NULL FROM tmp_tipo_fondo),
  'Inserimento tipo_fondo_fattura'
);

-- ============================================================
-- 2) Fattura sorgente con minimo
-- ============================================================
CREATE TEMP TABLE tmp_fattura_src AS
WITH ins AS (
  INSERT INTO vendite.fatture (
    registro_id,
    data,
    emittente_soggetto_ruolo_id,
    billing_account_id,
    tipo_doc_fiscale_id,
    valuta_id,
    minimo,
    totale_a_pagare,
    meta
  )
  SELECT
    (SELECT registro_id FROM tmp_refs_ff),
    current_date,
    (SELECT emittente_soggetto_ruolo_id FROM tmp_refs_ff),
    (SELECT billing_account_id FROM tmp_refs_ff),
    (SELECT tipo_doc_fiscale_id FROM tmp_refs_ff),
    (SELECT valuta_id FROM tmp_refs_ff),
    true,
    100.00,
    jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_ff))
  RETURNING id
)
SELECT * FROM ins;

SELECT ok(
  (SELECT id IS NOT NULL FROM tmp_fattura_src),
  'Inserimento fattura sorgente (minimo)'
);

-- ============================================================
-- 3) Generazione fondi source
-- ============================================================
SELECT is(
  vendite.fn_genera_fondi_fattura_source(
    p_billing_account_id => (SELECT billing_account_id FROM tmp_refs_ff),
    p_utility_id => (SELECT utility_id FROM tmp_refs_ff),
    p_tipo_doc_fiscale_id => (SELECT tipo_doc_fiscale_id FROM tmp_refs_ff),
    p_emittente_soggetto_ruolo_id => (SELECT emittente_soggetto_ruolo_id FROM tmp_refs_ff),
    p_valuta_id => (SELECT valuta_id FROM tmp_refs_ff),
    p_tipo_fondo_fattura_id => (SELECT id FROM tmp_tipo_fondo)
  ),
  1,
  'Generazione fondi source'
);

-- ============================================================
-- 4) Fattura figlia
-- ============================================================
CREATE TEMP TABLE tmp_fattura_dst AS
WITH ins AS (
  INSERT INTO vendite.fatture (
    registro_id,
    data,
    emittente_soggetto_ruolo_id,
    billing_account_id,
    tipo_doc_fiscale_id,
    valuta_id,
    minimo,
    totale_a_pagare,
    meta
  )
  SELECT
    (SELECT registro_id FROM tmp_refs_ff),
    current_date,
    (SELECT emittente_soggetto_ruolo_id FROM tmp_refs_ff),
    (SELECT billing_account_id FROM tmp_refs_ff),
    (SELECT tipo_doc_fiscale_id FROM tmp_refs_ff),
    (SELECT valuta_id FROM tmp_refs_ff),
    false,
    200.00,
    jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_ff))
  RETURNING id
)
SELECT * FROM ins;

SELECT ok(
  (SELECT id IS NOT NULL FROM tmp_fattura_dst),
  'Inserimento fattura figlia'
);

-- ============================================================
-- 5) Applicazione fondi
-- ============================================================
SELECT is(
  vendite.fn_applica_fondi_fattura(
    p_billing_account_id => (SELECT billing_account_id FROM tmp_refs_ff),
    p_utility_id => (SELECT utility_id FROM tmp_refs_ff),
    p_tipo_doc_fiscale_id => (SELECT tipo_doc_fiscale_id FROM tmp_refs_ff),
    p_emittente_soggetto_ruolo_id => (SELECT emittente_soggetto_ruolo_id FROM tmp_refs_ff),
    p_valuta_id => (SELECT valuta_id FROM tmp_refs_ff),
    p_fattura_figlia_id => (SELECT id FROM tmp_fattura_dst),
    p_tipo_fondo_fattura_id => (SELECT id FROM tmp_tipo_fondo)
  ),
  1,
  'Applicazione fondi fattura'
);

-- ============================================================
-- 6) Verifica stato source e righe
-- ============================================================
SELECT ok(
  (SELECT count(*) = 1
     FROM vendite.fatture_fondi_fattura_source s
     WHERE s.fattura_sorgente_id = (SELECT id FROM tmp_fattura_src)
       AND s.stato = 'ASSEGNATO'
       AND s.fattura_figlia_id = (SELECT id FROM tmp_fattura_dst)
  ),
  'Source aggiornata a ASSEGNATO'
);

SELECT ok(
  (SELECT count(*) = 1
     FROM vendite.fatture_fondi_fattura ff
     WHERE ff.fattura_id = (SELECT id FROM tmp_fattura_dst)
       AND ff.fattura_riferimento_id = (SELECT id FROM tmp_fattura_src)
  ),
  'Righe fondi fattura presenti'
);

-- ============================================================
-- 7) Reset fondi fattura
-- ============================================================
SELECT is(
  (
    SELECT updated_source
    FROM vendite.fn_reset_fondi_fattura(
      p_fattura_id => (SELECT id FROM tmp_fattura_dst)
    )
  ),
  1,
  'Reset fondi fattura (source riaperta)'
);

SELECT ok(
  (SELECT count(*) = 1
     FROM vendite.fatture_fondi_fattura_source s
     WHERE s.fattura_sorgente_id = (SELECT id FROM tmp_fattura_src)
       AND s.stato = 'DISPONIBILE'
       AND s.fattura_figlia_id IS NULL
  ),
  'Source ripristinata a DISPONIBILE'
);

SELECT ok(
  (SELECT count(*) = 0
     FROM vendite.fatture_fondi_fattura ff
     WHERE ff.fattura_id = (SELECT id FROM tmp_fattura_dst)
  ),
  'Righe fondi fattura rimosse'
);

-- ============================================================
-- Cleanup
-- ============================================================
UPDATE vendite.fatture
SET storicizza = false
WHERE meta ->> 'test_scope' = (SELECT test_scope FROM tmp_costanti_ff);

DELETE FROM vendite.fatture_fondi_fattura
WHERE fattura_id IN (SELECT id FROM tmp_fattura_dst)
   OR fattura_riferimento_id IN (SELECT id FROM tmp_fattura_src);

DELETE FROM vendite.fatture_fondi_fattura_source
WHERE fattura_sorgente_id IN (SELECT id FROM tmp_fattura_src);

DELETE FROM vendite.fatture
WHERE meta ->> 'test_scope' = (SELECT test_scope FROM tmp_costanti_ff);

DELETE FROM vendite.tipi_fondi_fattura
WHERE meta ->> 'test_scope' = (SELECT test_scope FROM tmp_costanti_ff);

SELECT ok(true, 'Cleanup completato');

SELECT * FROM finish();

ROLLBACK;
