-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: coerenza vendite_movimenti con contabile_riga_id
-- ------------------------------------------------------------
-- Indice test
-- 1) Presenza trigger function trgfn_vendite_movimenti_sync_contabile_from_riga
-- 2) Riferimenti minimi presenti (fattura/BA/centro/stati)
-- 3) Inserimento testate/righe contabili di test
-- 4) Derivazione contabile_id da contabile_riga_id
-- 5) Inserimento coerente con contabile_id manuale == contabile riga
-- 6) Blocco incoerenza contabile_id manuale vs riga
-- 7) Unicita parziale: primo aggancio contabile_riga_id ok
-- 8) Unicita parziale: blocco secondo aggancio stessa contabile_riga_id
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

-- ============================================================
-- 0) Costanti
-- ============================================================
CREATE TEMP TABLE tmp_costanti_vmcr AS
SELECT
  'pgtap_vm_contabile_riga'::text AS test_scope,
  ('VMCR_C1_' || to_char(clock_timestamp(), 'YYMMDDHH24MISSMS'))::text AS codice_contabile_1,
  ('VMCR_C2_' || to_char(clock_timestamp(), 'YYMMDDHH24MISSMS'))::text AS codice_contabile_2;

-- ============================================================
-- 1) Presenza trigger function
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'pagamenti'
      AND p.proname = 'trgfn_vendite_movimenti_sync_contabile_from_riga'
  ),
  'Presenza trigger function trgfn_vendite_movimenti_sync_contabile_from_riga'
);

-- ============================================================
-- 2) Riferimenti minimi
-- ============================================================
-- ⛔ LA FATTURA SI COSTRUISCE, TUTTA (2026-09-23). Questo blocco faceva gia'
--   la cosa giusta a meta': se una fattura non c'era la scriveva. Ma i suoi
--   mattoni li PESCAVA — il billing account «piu' recente», il registro, il
--   tipo documento, la valuta — e su un database ricostruito `anagrafiche` e
--   `vendite` sono a zero: tutte le colonne uscivano NULL, il ramo `ins`
--   inseriva zero righe per via dei suoi stessi `IS NOT NULL`, e il file
--   moriva sulla RLS di `vendite_contabili_righe` con una fattura che non
--   esisteva.
-- ⭐ Resta la lezione che il blocco portava e che il BB ha ereditato: il
--   registro si ALLINEA all'emittente (`script.fn_pgtap_registro_fattura`),
--   perche' dal 2026-08-30 `trgfn_fatture_guard_registro_emittente` non ammette
--   piu' che i due coincidano per caso.
CREATE TEMP TABLE tmp_fattura_ref AS
SELECT fattura_id, billing_account_id
  FROM dbops.fn_pgtap_crea_fattura('vendite movimenti contabile riga');

-- L'importo e' il caso del test, non del builder.
UPDATE vendite.fatture
   SET totale_a_pagare = 1.00,
       minimo = false,
       meta = meta || jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_vmcr))
 WHERE id = (SELECT fattura_id FROM tmp_fattura_ref);

CREATE TEMP TABLE tmp_centro_ref AS
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
    'VMCR_CENTRO_' || to_char(clock_timestamp(), 'YYMMDDHH24MISSMS'),
    'VMCR_TEST',
    'Centro riscossione test VM contabile riga',
    false,
    false,
    true,
    jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_vmcr))
  WHERE NOT EXISTS (SELECT 1 FROM existing)
  RETURNING id
)
SELECT id FROM existing
UNION ALL
SELECT id FROM ins;

CREATE TEMP TABLE tmp_stato_contabile_ref AS
WITH existing AS (
  SELECT s.id
  FROM pagamenti.vendite_contabili_stati s
  WHERE s.attivo IS TRUE
  ORDER BY s.id
  LIMIT 1
), ins AS (
  INSERT INTO pagamenti.vendite_contabili_stati (
    codice,
    codice_interno,
    descrizione,
    is_final,
    ordine,
    attivo,
    meta
  )
  SELECT
    'VMCR_STATO_CONT_' || to_char(clock_timestamp(), 'YYMMDDHH24MISSMS'),
    'VMCR_ST_CONT',
    'Stato contabile test VMCR',
    false,
    10,
    true,
    jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_vmcr))
  WHERE NOT EXISTS (SELECT 1 FROM existing)
  RETURNING id
)
SELECT id FROM existing
UNION ALL
SELECT id FROM ins;

CREATE TEMP TABLE tmp_stato_riga_ref AS
WITH existing AS (
  SELECT s.id
  FROM pagamenti.vendite_contabili_righe_stati s
  WHERE s.attivo IS TRUE
  ORDER BY s.id
  LIMIT 1
), ins AS (
  INSERT INTO pagamenti.vendite_contabili_righe_stati (
    codice,
    codice_interno,
    descrizione,
    is_postabile,
    is_final,
    ordine,
    attivo,
    meta
  )
  SELECT
    'VMCR_STATO_RIGA_' || to_char(clock_timestamp(), 'YYMMDDHH24MISSMS'),
    'VMCR_ST_RIGA',
    'Stato riga test VMCR',
    true,
    false,
    10,
    true,
    jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_vmcr))
  WHERE NOT EXISTS (SELECT 1 FROM existing)
  RETURNING id
)
SELECT id FROM existing
UNION ALL
SELECT id FROM ins;

SELECT ok(
  (SELECT count(*) = 1 FROM tmp_fattura_ref)
  AND (SELECT fattura_id IS NOT NULL AND billing_account_id IS NOT NULL
       FROM tmp_fattura_ref)
  AND (SELECT count(*) = 1 FROM tmp_centro_ref)
  AND (SELECT count(*) = 1 FROM tmp_stato_contabile_ref)
  AND (SELECT count(*) = 1 FROM tmp_stato_riga_ref),
  'Riferimenti minimi presenti (fattura/BA/centro/stati)'
);

-- ============================================================
-- 3) Setup contabili e righe
-- ============================================================
CREATE TEMP TABLE tmp_contabili AS
WITH c1 AS (
  INSERT INTO pagamenti.vendite_contabili (
    codice,
    centro_riscossione_id,
    data_contabile,
    data_registrazione,
    stato_id,
    meta
  )
  SELECT
    (SELECT codice_contabile_1 FROM tmp_costanti_vmcr),
    (SELECT id FROM tmp_centro_ref),
    script.fn_data_operativa(),
    script.fn_data_operativa(),
    (SELECT id FROM tmp_stato_contabile_ref),
    jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_vmcr), 'case', 'contabile_1')
  RETURNING id
), c2 AS (
  INSERT INTO pagamenti.vendite_contabili (
    codice,
    centro_riscossione_id,
    data_contabile,
    data_registrazione,
    stato_id,
    meta
  )
  SELECT
    (SELECT codice_contabile_2 FROM tmp_costanti_vmcr),
    (SELECT id FROM tmp_centro_ref),
    script.fn_data_operativa(),
    script.fn_data_operativa(),
    (SELECT id FROM tmp_stato_contabile_ref),
    jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_vmcr), 'case', 'contabile_2')
  RETURNING id
), r1 AS (
  INSERT INTO pagamenti.vendite_contabili_righe (
    contabile_id,
    riferimento_ente,
    data_pagamento,
    data_valuta,
    data_operazione,
    importo,
    fattura_id,
    billing_account_id,
    stato_id,
    meta
  )
  SELECT
    (SELECT id FROM c1),
    'VMCR_R1',
    script.fn_data_operativa(),
    script.fn_data_operativa(),
    script.fn_data_operativa(),
    10.00,
    (SELECT fattura_id FROM tmp_fattura_ref),
    (SELECT billing_account_id FROM tmp_fattura_ref),
    (SELECT id FROM tmp_stato_riga_ref),
    jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_vmcr), 'case', 'riga_1')
  RETURNING id
), r2 AS (
  INSERT INTO pagamenti.vendite_contabili_righe (
    contabile_id,
    riferimento_ente,
    data_pagamento,
    data_valuta,
    data_operazione,
    importo,
    fattura_id,
    billing_account_id,
    stato_id,
    meta
  )
  SELECT
    (SELECT id FROM c1),
    'VMCR_R2',
    script.fn_data_operativa(),
    script.fn_data_operativa(),
    script.fn_data_operativa(),
    20.00,
    (SELECT fattura_id FROM tmp_fattura_ref),
    (SELECT billing_account_id FROM tmp_fattura_ref),
    (SELECT id FROM tmp_stato_riga_ref),
    jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_vmcr), 'case', 'riga_2')
  RETURNING id
)
SELECT
  (SELECT id FROM c1) AS contabile_1_id,
  (SELECT id FROM c2) AS contabile_2_id,
  (SELECT id FROM r1) AS riga_1_id,
  (SELECT id FROM r2) AS riga_2_id;

SELECT ok(
  (SELECT contabile_1_id IS NOT NULL
      AND contabile_2_id IS NOT NULL
      AND riga_1_id IS NOT NULL
      AND riga_2_id IS NOT NULL
   FROM tmp_contabili),
  'Inserimento testate/righe contabili di test'
);

-- ============================================================
-- 4) Derivazione contabile_id da contabile_riga_id
-- ============================================================
CREATE TEMP TABLE tmp_mov_derivato AS
WITH ins AS (
  INSERT INTO pagamenti.vendite_movimenti (
    fattura_id,
    billing_account_id,
    data_effettiva,
    data_registrazione,
    data_valuta,
    importo,
    centro_riscossione_id,
    contabile_riga_id,
    contabile_id,
    meta
  )
  SELECT
    (SELECT fattura_id FROM tmp_fattura_ref),
    (SELECT billing_account_id FROM tmp_fattura_ref),
    script.fn_data_operativa(),
    script.fn_data_operativa(),
    script.fn_data_operativa(),
    10.00,
    (SELECT id FROM tmp_centro_ref),
    (SELECT riga_1_id FROM tmp_contabili),
    NULL,
    jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_vmcr), 'case', 'derivato')
  RETURNING id, contabile_id
)
SELECT * FROM ins;

SELECT is(
  (SELECT contabile_id::bigint FROM tmp_mov_derivato),
  (SELECT contabile_1_id::bigint FROM tmp_contabili),
  'Derivazione contabile_id da contabile_riga_id'
);

-- ============================================================
-- 5) Inserimento coerente con contabile_id manuale uguale a riga
-- ============================================================
CREATE TEMP TABLE tmp_mov_coerente AS
WITH ins AS (
  INSERT INTO pagamenti.vendite_movimenti (
    fattura_id,
    billing_account_id,
    data_effettiva,
    data_registrazione,
    data_valuta,
    importo,
    centro_riscossione_id,
    contabile_riga_id,
    contabile_id,
    meta
  )
  SELECT
    (SELECT fattura_id FROM tmp_fattura_ref),
    (SELECT billing_account_id FROM tmp_fattura_ref),
    script.fn_data_operativa(),
    script.fn_data_operativa(),
    script.fn_data_operativa(),
    20.00,
    (SELECT id FROM tmp_centro_ref),
    (SELECT riga_2_id FROM tmp_contabili),
    (SELECT contabile_1_id FROM tmp_contabili),
    jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_vmcr), 'case', 'coerente')
  RETURNING id
)
SELECT * FROM ins;

SELECT is(
  (SELECT count(*)::int FROM tmp_mov_coerente),
  1,
  'Inserimento coerente con contabile_id manuale == contabile riga'
);

-- ============================================================
-- 6) Blocco incoerenza contabile_id manuale vs riga
-- ============================================================
SELECT throws_ok(
  $$
  INSERT INTO pagamenti.vendite_movimenti (
    fattura_id,
    billing_account_id,
    data_effettiva,
    data_registrazione,
    data_valuta,
    importo,
    centro_riscossione_id,
    contabile_riga_id,
    contabile_id,
    meta
  )
  SELECT
    (SELECT fattura_id FROM tmp_fattura_ref),
    (SELECT billing_account_id FROM tmp_fattura_ref),
    script.fn_data_operativa(),
    script.fn_data_operativa(),
    script.fn_data_operativa(),
    30.00,
    (SELECT id FROM tmp_centro_ref),
    (SELECT riga_1_id FROM tmp_contabili),
    (SELECT contabile_2_id FROM tmp_contabili),
    jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_vmcr), 'case', 'incoerente');
  $$,
  'P0001',
  NULL,
  'Blocco incoerenza contabile_id manuale vs riga'
);

-- ============================================================
-- 7) Unicita parziale: primo aggancio stessa riga
-- ============================================================
CREATE TEMP TABLE tmp_riga_unica AS
WITH r3 AS (
  INSERT INTO pagamenti.vendite_contabili_righe (
    contabile_id,
    riferimento_ente,
    data_pagamento,
    data_valuta,
    data_operazione,
    importo,
    fattura_id,
    billing_account_id,
    stato_id,
    meta
  )
  SELECT
    (SELECT contabile_1_id FROM tmp_contabili),
    'VMCR_R3',
    script.fn_data_operativa(),
    script.fn_data_operativa(),
    script.fn_data_operativa(),
    40.00,
    (SELECT fattura_id FROM tmp_fattura_ref),
    (SELECT billing_account_id FROM tmp_fattura_ref),
    (SELECT id FROM tmp_stato_riga_ref),
    jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_vmcr), 'case', 'riga_3')
  RETURNING id
), m1 AS (
  INSERT INTO pagamenti.vendite_movimenti (
    fattura_id,
    billing_account_id,
    data_effettiva,
    data_registrazione,
    data_valuta,
    importo,
    centro_riscossione_id,
    contabile_riga_id,
    meta
  )
  SELECT
    (SELECT fattura_id FROM tmp_fattura_ref),
    (SELECT billing_account_id FROM tmp_fattura_ref),
    script.fn_data_operativa(),
    script.fn_data_operativa(),
    script.fn_data_operativa(),
    40.00,
    (SELECT id FROM tmp_centro_ref),
    (SELECT id FROM r3),
    jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_vmcr), 'case', 'unico_1')
  RETURNING id
)
SELECT
  (SELECT id FROM r3) AS riga_3_id,
  (SELECT id FROM m1) AS movimento_1_id;

SELECT is(
  (SELECT count(*)::int FROM tmp_riga_unica WHERE movimento_1_id IS NOT NULL),
  1,
  'Unicita parziale: primo aggancio contabile_riga_id ok'
);

-- ============================================================
-- 8) Unicita parziale: secondo aggancio stessa riga bloccato
-- ============================================================
SELECT throws_ok(
  $$
  INSERT INTO pagamenti.vendite_movimenti (
    fattura_id,
    billing_account_id,
    data_effettiva,
    data_registrazione,
    data_valuta,
    importo,
    centro_riscossione_id,
    contabile_riga_id,
    meta
  )
  SELECT
    (SELECT fattura_id FROM tmp_fattura_ref),
    (SELECT billing_account_id FROM tmp_fattura_ref),
    script.fn_data_operativa(),
    script.fn_data_operativa(),
    script.fn_data_operativa(),
    41.00,
    (SELECT id FROM tmp_centro_ref),
    (SELECT riga_3_id FROM tmp_riga_unica),
    jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_vmcr), 'case', 'unico_2');
  $$,
  '23505',
  NULL,
  'Unicita parziale: blocco secondo aggancio stessa contabile_riga_id'
);

SELECT * FROM finish();

ROLLBACK;
