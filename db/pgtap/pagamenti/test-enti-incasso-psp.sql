-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: guard PSP su pagamenti.enti_incasso
-- ------------------------------------------------------------
-- Indice test
-- 1) Presenza trigger function trgfn_enti_incasso_guard_psp
-- 2) Presenza ruolo PSP in config.tipi_ruoli
-- 3) Presenza centro_riscossione attivo
-- 4) Esiste soggetto candidabile per PSP di test
-- 5) Inserimento anagrafiche.psp di test
-- 6) Inserimento enti_incasso tipo PSP valido
-- 7) Blocco tipo PSP senza soggetto_ruolo_id
-- 8) Esiste soggetto_ruolo non-PSP candidabile
-- 9) Blocco tipo PSP con soggetto_ruolo_id non-PSP
-- 10) Blocco tipo PSP con ruolo PSP non censito in anagrafiche.psp
-- 11) Cleanup completato
-- ------------------------------------------------------------

BEGIN;

SELECT plan(11);

-- ============================================================
-- 0) Costanti e cleanup idempotente
-- ============================================================
CREATE TEMP TABLE tmp_costanti_eip AS
SELECT
  'pgtap_enti_incasso_psp'::text AS test_scope,
  ('EIP_PSP_' || to_char(clock_timestamp(), 'YYMMDDHH24MISSMS'))::text AS codice_psp,
  ('EIP_ENTE_' || to_char(clock_timestamp(), 'YYMMDDHH24MISSMS'))::text AS codice_ente;

DELETE FROM pagamenti.enti_incasso
WHERE meta ->> 'test_scope' = (SELECT test_scope FROM tmp_costanti_eip);

DELETE FROM anagrafiche.psp
WHERE meta ->> 'test_scope' = (SELECT test_scope FROM tmp_costanti_eip);

-- ============================================================
-- 1) Presenza trigger function
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'pagamenti'
      AND p.proname = 'trgfn_enti_incasso_guard_psp'
  ),
  'Presenza trigger function trgfn_enti_incasso_guard_psp'
);

-- ============================================================
-- 2) Presenza ruolo PSP
-- ============================================================
CREATE TEMP TABLE tmp_ruolo_psp AS
SELECT id
FROM config.tipi_ruoli
WHERE codice_interno = 'PSP';

SELECT is(
  (SELECT count(*)::int FROM tmp_ruolo_psp),
  1,
  'Presenza ruolo PSP in config.tipi_ruoli'
);

-- ============================================================
-- 3) Centro riscossione attivo
-- ============================================================
CREATE TEMP TABLE tmp_centro AS
WITH existing AS (
  SELECT c.id
  FROM pagamenti.centri_riscossione c
  WHERE c.attivo IS TRUE
  ORDER BY c.id
  LIMIT 1
), ins AS (
  INSERT INTO pagamenti.centri_riscossione (
    codice,
    codice_interno,
    descrizione,
    is_compensazione,
    is_fondo_fattura,
    attivo,
    meta
  )
  SELECT
    'EIP_CENTRO_' || to_char(clock_timestamp(), 'YYMMDDHH24MISSMS'),
    'EIP_TEST',
    'Centro riscossione test pgTAP enti_incasso PSP',
    false,
    false,
    true,
    jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_eip))
  WHERE NOT EXISTS (SELECT 1 FROM existing)
  RETURNING id
)
SELECT id FROM existing
UNION ALL
SELECT id FROM ins;

SELECT is(
  (SELECT count(*)::int FROM tmp_centro),
  1,
  'Presenza centro_riscossione attivo'
);

-- ============================================================
-- 4) Soggetto candidabile (senza PSP anagrafico)
-- ============================================================
CREATE TEMP TABLE tmp_soggetto_ok AS
SELECT s.id AS soggetto_id
FROM anagrafiche.soggetti s
WHERE NOT EXISTS (
  SELECT 1
  FROM anagrafiche.soggetti_ruoli sr
  JOIN config.tipi_ruoli tr
    ON tr.id = sr.tipo_ruolo_id
   AND tr.codice_interno = 'PSP'
  JOIN anagrafiche.psp p
    ON p.soggetto_ruolo_id = sr.id
  WHERE sr.soggetto_id = s.id
)
ORDER BY s.id
LIMIT 1;

SELECT is(
  (SELECT count(*)::int FROM tmp_soggetto_ok),
  1,
  'Esiste soggetto candidabile per PSP di test'
);

CREATE TEMP TABLE tmp_ruolo_psp_ok AS
SELECT script.fn_get_or_create_soggetto_ruolo(
         p_soggetto_id := (SELECT soggetto_id FROM tmp_soggetto_ok),
         p_cd_int_ruolo := 'PSP'
       ) AS soggetto_ruolo_id;

-- ============================================================
-- 5) Inserimento PSP anagrafico
-- ============================================================
CREATE TEMP TABLE tmp_psp_ok AS
WITH ins AS (
  INSERT INTO anagrafiche.psp (
    soggetto_ruolo_id,
    codice,
    descrizione,
    meta
  )
  SELECT
    (SELECT soggetto_ruolo_id FROM tmp_ruolo_psp_ok),
    (SELECT codice_psp FROM tmp_costanti_eip),
    'PSP test pgTAP',
    jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_eip))
  RETURNING id
)
SELECT * FROM ins;

SELECT is(
  (SELECT count(*)::int FROM tmp_psp_ok),
  1,
  'Inserimento anagrafiche.psp di test'
);

-- ============================================================
-- 6) Inserimento enti_incasso tipo PSP valido
-- ============================================================
CREATE TEMP TABLE tmp_ente_ok AS
WITH ins AS (
  INSERT INTO pagamenti.enti_incasso (
    codice,
    codice_interno,
    descrizione,
    tipo,
    attivo,
    centro_riscossione_id,
    soggetto_ruolo_id,
    bank_branch_id,
    formato_flusso,
    regole_match,
    meta
  )
  SELECT
    (SELECT codice_ente FROM tmp_costanti_eip),
    'EIP_PSP',
    'Ente incasso PSP test pgTAP',
    'PSP',
    true,
    (SELECT id FROM tmp_centro),
    (SELECT soggetto_ruolo_id FROM tmp_ruolo_psp_ok),
    NULL,
    'JSON',
    '{}'::jsonb,
    jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_eip))
  RETURNING id
)
SELECT * FROM ins;

SELECT is(
  (SELECT count(*)::int FROM tmp_ente_ok),
  1,
  'Inserimento enti_incasso tipo PSP valido'
);

-- ============================================================
-- 7) Blocco PSP senza soggetto_ruolo_id
-- ============================================================
SELECT throws_ok(
  $$
  INSERT INTO pagamenti.enti_incasso (
    codice,
    descrizione,
    tipo,
    attivo,
    centro_riscossione_id,
    soggetto_ruolo_id,
    bank_branch_id,
    regole_match,
    meta
  )
  VALUES (
    'EIP_NULL_ROLE_' || to_char(clock_timestamp(), 'YYMMDDHH24MISSMS'),
    'Ente PSP senza ruolo',
    'PSP',
    true,
    (SELECT id FROM tmp_centro),
    NULL,
    NULL,
    '{}'::jsonb,
    jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_eip))
  );
  $$,
  'P0001',
  NULL,
  'Blocco tipo PSP senza soggetto_ruolo_id'
);

-- ============================================================
-- 8) Ruolo non-PSP candidabile
-- ============================================================
CREATE TEMP TABLE tmp_ruolo_non_psp AS
SELECT sr.id AS soggetto_ruolo_id
FROM anagrafiche.soggetti_ruoli sr
JOIN config.tipi_ruoli tr
  ON tr.id = sr.tipo_ruolo_id
WHERE tr.codice_interno <> 'PSP'
ORDER BY sr.id
LIMIT 1;

SELECT is(
  (SELECT count(*)::int FROM tmp_ruolo_non_psp),
  1,
  'Esiste soggetto_ruolo non-PSP candidabile'
);

-- ============================================================
-- 9) Blocco PSP con ruolo non-PSP
-- ============================================================
SELECT throws_ok(
  $$
  INSERT INTO pagamenti.enti_incasso (
    codice,
    descrizione,
    tipo,
    attivo,
    centro_riscossione_id,
    soggetto_ruolo_id,
    bank_branch_id,
    regole_match,
    meta
  )
  VALUES (
    'EIP_WRONG_ROLE_' || to_char(clock_timestamp(), 'YYMMDDHH24MISSMS'),
    'Ente PSP con ruolo non-PSP',
    'PSP',
    true,
    (SELECT id FROM tmp_centro),
    (SELECT soggetto_ruolo_id FROM tmp_ruolo_non_psp),
    NULL,
    '{}'::jsonb,
    jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_eip))
  );
  $$,
  'P0001',
  NULL,
  'Blocco tipo PSP con soggetto_ruolo_id non-PSP'
);

-- ============================================================
-- 10) Blocco PSP con ruolo PSP non censito in anagrafiche.psp
-- ============================================================
CREATE TEMP TABLE tmp_soggetto_no_psp_row AS
SELECT s.id AS soggetto_id
FROM anagrafiche.soggetti s
WHERE s.id <> (SELECT soggetto_id FROM tmp_soggetto_ok)
  AND NOT EXISTS (
    SELECT 1
    FROM anagrafiche.soggetti_ruoli sr
    JOIN config.tipi_ruoli tr
      ON tr.id = sr.tipo_ruolo_id
     AND tr.codice_interno = 'PSP'
    JOIN anagrafiche.psp p
      ON p.soggetto_ruolo_id = sr.id
    WHERE sr.soggetto_id = s.id
  )
ORDER BY s.id
LIMIT 1;

CREATE TEMP TABLE tmp_ruolo_psp_senza_riga AS
SELECT script.fn_get_or_create_soggetto_ruolo(
         p_soggetto_id := (SELECT soggetto_id FROM tmp_soggetto_no_psp_row),
         p_cd_int_ruolo := 'PSP'
       ) AS soggetto_ruolo_id;

SELECT throws_ok(
  $$
  INSERT INTO pagamenti.enti_incasso (
    codice,
    descrizione,
    tipo,
    attivo,
    centro_riscossione_id,
    soggetto_ruolo_id,
    bank_branch_id,
    regole_match,
    meta
  )
  VALUES (
    'EIP_NO_PSP_ROW_' || to_char(clock_timestamp(), 'YYMMDDHH24MISSMS'),
    'Ente PSP senza anagrafica PSP',
    'PSP',
    true,
    (SELECT id FROM tmp_centro),
    (SELECT soggetto_ruolo_id FROM tmp_ruolo_psp_senza_riga),
    NULL,
    '{}'::jsonb,
    jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_eip))
  );
  $$,
  'P0001',
  NULL,
  'Blocco tipo PSP con ruolo PSP non censito in anagrafiche.psp'
);

-- ============================================================
-- 11) Cleanup
-- ============================================================
DELETE FROM pagamenti.enti_incasso
WHERE meta ->> 'test_scope' = (SELECT test_scope FROM tmp_costanti_eip);

DELETE FROM anagrafiche.psp
WHERE meta ->> 'test_scope' = (SELECT test_scope FROM tmp_costanti_eip);

DELETE FROM pagamenti.centri_riscossione
WHERE meta ->> 'test_scope' = (SELECT test_scope FROM tmp_costanti_eip);

SELECT is(
  (
    SELECT count(*)::int
    FROM pagamenti.enti_incasso
    WHERE meta ->> 'test_scope' = (SELECT test_scope FROM tmp_costanti_eip)
  ),
  0,
  'Cleanup completato'
);

SELECT * FROM finish();

ROLLBACK;
