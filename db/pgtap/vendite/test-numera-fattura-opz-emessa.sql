-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: vendite.fn_numera_fattura_opz_emessa
-- ------------------------------------------------------------
-- Indice test
-- 1) Riferimenti minimi presenti
-- 2) Inserimento registro di test
-- 3) Inserimento fattura di test
-- 4) Numerazione fattura (numero=1)
-- 5) Numerazione idempotente (numero invariato)
-- 6) Cleanup completato
-- ------------------------------------------------------------

BEGIN;

SELECT plan(6);

-- ============================================================
-- 0) Riferimenti
-- ============================================================
CREATE TEMP TABLE tmp_costanti_nf AS
SELECT
  'pgtap_numera_fattura'::text AS test_scope;

CREATE TEMP TABLE tmp_refs_nf AS
SELECT
  (SELECT soggetto_ruolo_id
     FROM anagrafiche.emittenti_fiscali
    WHERE attivo IS TRUE
    ORDER BY data_insert DESC NULLS LAST
    LIMIT 1) AS emittente_soggetto_ruolo_id,
  (SELECT id
     FROM anagrafiche.billing_account
    ORDER BY data_insert DESC NULLS LAST
    LIMIT 1) AS billing_account_id;

SELECT ok(
  (SELECT emittente_soggetto_ruolo_id IS NOT NULL
     AND billing_account_id IS NOT NULL
   FROM tmp_refs_nf),
  'Riferimenti minimi presenti'
);

-- ============================================================
-- 1) Registro di test
-- ============================================================
CREATE TEMP TABLE tmp_reg_nf AS
WITH ins AS (
  INSERT INTO vendite.registri_fatturazione (
    codice,
    descrizione,
    reset_policy,
    attivo,
    meta
  )
  SELECT
    left('REGNF_' || (SELECT test_scope FROM tmp_costanti_nf), 16),
    'Registro test numerazione',
    'ANNUALE',
    true,
    jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_nf))
  RETURNING id
)
SELECT * FROM ins;

SELECT ok(
  (SELECT id IS NOT NULL FROM tmp_reg_nf),
  'Inserimento registro di test'
);

-- ============================================================
-- 2) Fattura di test
-- ============================================================
CREATE TEMP TABLE tmp_fattura_nf AS
WITH ins AS (
  INSERT INTO vendite.fatture (
    registro_id,
    data,
    emittente_soggetto_ruolo_id,
    billing_account_id,
    meta
  )
  SELECT
    (SELECT id FROM tmp_reg_nf),
    current_date,
    (SELECT emittente_soggetto_ruolo_id FROM tmp_refs_nf),
    (SELECT billing_account_id FROM tmp_refs_nf),
    jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_nf))
  RETURNING id
)
SELECT * FROM ins;

SELECT ok(
  (SELECT id IS NOT NULL FROM tmp_fattura_nf),
  'Inserimento fattura di test'
);

-- ============================================================
-- 3) Numerazione fattura
-- ============================================================
SELECT is(
  (
    SELECT numero
    FROM vendite.fn_numera_fattura_opz_emessa(
      p_fattura_id => (SELECT id FROM tmp_fattura_nf)
    )
  ),
  1::bigint,
  'Numerazione fattura (numero=1)'
);

SELECT is(
  (
    SELECT numero
    FROM vendite.fn_numera_fattura_opz_emessa(
      p_fattura_id => (SELECT id FROM tmp_fattura_nf)
    )
  ),
  1::bigint,
  'Numerazione idempotente (numero invariato)'
);

-- ============================================================
-- Cleanup
-- ============================================================
UPDATE vendite.fatture
SET storicizza = false
WHERE id = (SELECT id FROM tmp_fattura_nf);

UPDATE vendite.registri_fatturazione
SET storicizza = false
WHERE id = (SELECT id FROM tmp_reg_nf);

DELETE FROM vendite.fatture
WHERE id = (SELECT id FROM tmp_fattura_nf);

DELETE FROM vendite.registri_fatturazione_progressivi
WHERE registro_id = (SELECT id FROM tmp_reg_nf);

DELETE FROM vendite.registri_fatturazione
WHERE id = (SELECT id FROM tmp_reg_nf);

SELECT ok(true, 'Cleanup completato');

SELECT * FROM finish();

ROLLBACK;
