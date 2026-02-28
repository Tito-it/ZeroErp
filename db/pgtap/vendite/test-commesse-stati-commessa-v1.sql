-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: stati_commessa lookup + refactor FK + fn_list_commesse_emittibili
-- (changeset 20260226-01..06)
-- ------------------------------------------------------------
-- Indice test (1..18):
--  1) Tabella vendite.stati_commessa presente
--  2) FK commesse.stato_commessa_id presente
--  3) Vecchia colonna commesse.stato_commessa rimossa
--  4) 6 stati_commessa presenti e attivi
--  5) Flag chiude_commessa corretto (CHIUSA/ANNULLATA=true, altri=false)
--  6) Flag emittibile corretto (solo PRONTA_FATTURAZIONE=true)
--  7) Flag modificabile corretto (CHIUSA/ANNULLATA=false, altri=true)
--  8) Trigger lock codice_interno presente
--  9) Trigger child_requires_active_parent presente
-- 10) Trigger prevent_deactivate presente
-- 11) fn_list_commesse_emittibili presente
-- 12) fn_get_commessa_stato restituisce stato_commessa_id e flag
-- 13) Commessa creata in stato BOZZA (stato_commessa_id=1)
-- 14) fn_get_or_create_commessa riusa commessa aperta (chiude=false)
-- 15) fn_upsert_commessa_attivita funziona su commessa modificabile
-- 16) fn_upsert_commessa_attivita bloccata su commessa non modificabile
-- 17) fn_list_commesse_emittibili esclude commesse non emittibili
-- 18) fn_list_commesse_emittibili include commesse emittibili (senza filtro mese)
-- 19) fn_list_commesse_emittibili filtra per competenza_mese corretto
-- 20) fn_list_commesse_emittibili esclude mese non corrispondente
-- ------------------------------------------------------------

BEGIN;
SELECT plan(20);

-- ============================================================
-- STRUTTURA DDL
-- ============================================================

SELECT ok(
  EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'vendite' AND table_name = 'stati_commessa'
  ),
  'Tabella vendite.stati_commessa presente'
);

SELECT ok(
  EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'vendite'
      AND table_name = 'commesse'
      AND column_name = 'stato_commessa_id'
  ),
  'FK commesse.stato_commessa_id presente'
);

SELECT ok(
  NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'vendite'
      AND table_name = 'commesse'
      AND column_name = 'stato_commessa'
  ),
  'Vecchia colonna commesse.stato_commessa rimossa'
);

-- ============================================================
-- SEED DATA
-- ============================================================

SELECT is(
  (SELECT count(*)::integer FROM vendite.stati_commessa WHERE attivo = true),
  6,
  '6 stati_commessa presenti e attivi'
);

SELECT ok(
  (
    SELECT count(*) = 2
    FROM vendite.stati_commessa
    WHERE chiude_commessa = true
      AND codice_interno IN ('CHIUSA', 'ANNULLATA')
  )
  AND NOT EXISTS (
    SELECT 1
    FROM vendite.stati_commessa
    WHERE chiude_commessa = true
      AND codice_interno NOT IN ('CHIUSA', 'ANNULLATA')
  ),
  'Flag chiude_commessa corretto (CHIUSA/ANNULLATA=true, altri=false)'
);

SELECT ok(
  (
    SELECT count(*) = 1
    FROM vendite.stati_commessa
    WHERE emittibile = true
      AND codice_interno = 'PRONTA_FATTURAZIONE'
  )
  AND NOT EXISTS (
    SELECT 1
    FROM vendite.stati_commessa
    WHERE emittibile = true
      AND codice_interno <> 'PRONTA_FATTURAZIONE'
  ),
  'Flag emittibile corretto (solo PRONTA_FATTURAZIONE=true)'
);

SELECT ok(
  (
    SELECT count(*) = 2
    FROM vendite.stati_commessa
    WHERE modificabile = false
      AND codice_interno IN ('CHIUSA', 'ANNULLATA')
  )
  AND NOT EXISTS (
    SELECT 1
    FROM vendite.stati_commessa
    WHERE modificabile = false
      AND codice_interno NOT IN ('CHIUSA', 'ANNULLATA')
  ),
  'Flag modificabile corretto (CHIUSA/ANNULLATA=false, altri=true)'
);

-- ============================================================
-- TRIGGER
-- ============================================================

SELECT ok(
  EXISTS (
    SELECT 1 FROM pg_trigger
    WHERE tgrelid = 'vendite.stati_commessa'::regclass
      AND tgname LIKE '%lock_columns%'
  ),
  'Trigger lock codice_interno presente'
);

SELECT ok(
  EXISTS (
    SELECT 1 FROM pg_trigger
    WHERE tgrelid = 'vendite.commesse'::regclass
      AND tgname LIKE '%stati_commessa_require_attivo%'
  ),
  'Trigger child_requires_active_parent presente'
);

SELECT ok(
  EXISTS (
    SELECT 1 FROM pg_trigger
    WHERE tgrelid = 'vendite.stati_commessa'::regclass
      AND tgname LIKE '%commesse_block_deact%'
  ),
  'Trigger prevent_deactivate presente'
);

-- ============================================================
-- FUNZIONI
-- ============================================================

SELECT ok(
  EXISTS (
    SELECT 1
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite'
      AND p.proname = 'fn_list_commesse_emittibili'
  ),
  'fn_list_commesse_emittibili presente'
);

-- ============================================================
-- SETUP DATI TEST
-- ============================================================

-- Recupera riferimenti minimi per test funzionali
CREATE TEMP TABLE tmp_refs_sc AS
SELECT
  (
    SELECT ba.id
    FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL
      AND ba.istanza_utility_id IS NOT NULL
      AND anagrafiche.fn_get_emittente_fiscale_id(ba.id) IS NOT NULL
    ORDER BY ba.id
    LIMIT 1
  ) AS billing_account_id,
  (
    SELECT ba.utility_id
    FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL
      AND ba.istanza_utility_id IS NOT NULL
      AND anagrafiche.fn_get_emittente_fiscale_id(ba.id) IS NOT NULL
    ORDER BY ba.id
    LIMIT 1
  ) AS utility_id,
  (
    SELECT ba.istanza_utility_id
    FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL
      AND ba.istanza_utility_id IS NOT NULL
      AND anagrafiche.fn_get_emittente_fiscale_id(ba.id) IS NOT NULL
    ORDER BY ba.id
    LIMIT 1
  ) AS istanza_utility_id,
  (
    SELECT a.id
    FROM catalogo.articoli a
    WHERE a.attivo IS TRUE
    ORDER BY a.data_insert DESC NULLS LAST
    LIMIT 1
  ) AS articolo_id,
  (
    SELECT u.id
    FROM catalogo.unita_misura u
    WHERE u.attivo IS TRUE
    ORDER BY u.id
    LIMIT 1
  ) AS uom_id,
  (
    SELECT t.id
    FROM config.tipi_doc_fiscale t
    WHERE t.attivo IS TRUE
    ORDER BY t.id
    LIMIT 1
  ) AS tipo_doc_fiscale_id,
  (
    SELECT v.id
    FROM config.valute v
    ORDER BY v.id
    LIMIT 1
  ) AS valuta_id,
  (
    SELECT s.id
    FROM config.sorgenti s
    WHERE s.codice = 'PREVENTIVO'
    LIMIT 1
  ) AS root_sorgente_tipo_id;

-- Crea commessa di test (force_new per isolamento)
CREATE TEMP TABLE tmp_commessa_sc AS
SELECT vendite.fn_get_or_create_commessa(
  p_billing_account_id => (SELECT billing_account_id FROM tmp_refs_sc),
  p_utility_id => (SELECT utility_id FROM tmp_refs_sc),
  p_tipo_commessa => 'AUTO',
  p_policy_fatturazione => 'DA_DOCUMENTO',
  p_fatturazione_immediata => false,
  p_priorita_operativa => 'NORMALE',
  p_competenza_dal => DATE '2026-07-01',
  p_competenza_al => DATE '2026-07-31',
  p_meta => jsonb_build_object('test_scope', 'pgtap_stati_commessa'),
  p_force_new => true
) AS commessa_id;

-- ============================================================
-- TEST fn_get_commessa_stato con nuovi campi
-- ============================================================

SELECT ok(
  EXISTS (
    SELECT 1
    FROM vendite.fn_get_commessa_stato((SELECT commessa_id FROM tmp_commessa_sc)) x
    WHERE x.stato_commessa_id = 1
      AND x.stato_commessa = 'BOZZA'
      AND x.chiude_commessa = false
      AND x.emittibile = false
      AND x.modificabile = true
  ),
  'fn_get_commessa_stato restituisce stato_commessa_id e flag'
);

-- ============================================================
-- TEST: commessa creata in BOZZA (default stato_commessa_id=1)
-- ============================================================

SELECT ok(
  EXISTS (
    SELECT 1
    FROM vendite.commesse c
    WHERE c.id = (SELECT commessa_id FROM tmp_commessa_sc)
      AND c.stato_commessa_id = 1
  ),
  'Commessa creata in stato BOZZA (stato_commessa_id=1)'
);

-- ============================================================
-- TEST: fn_get_or_create_commessa riusa commessa chiude=false
-- ============================================================

CREATE TEMP TABLE tmp_commessa_sc_reuse AS
SELECT vendite.fn_get_or_create_commessa(
  p_billing_account_id => (SELECT billing_account_id FROM tmp_refs_sc),
  p_utility_id => (SELECT utility_id FROM tmp_refs_sc),
  p_tipo_commessa => 'AUTO',
  p_policy_fatturazione => 'DA_DOCUMENTO',
  p_fatturazione_immediata => false,
  p_priorita_operativa => 'NORMALE',
  p_competenza_dal => DATE '2026-07-01',
  p_competenza_al => DATE '2026-07-31',
  p_meta => jsonb_build_object('test_scope', 'pgtap_stati_commessa_reuse'),
  p_force_new => false
) AS commessa_id;

SELECT is(
  (SELECT commessa_id::text FROM tmp_commessa_sc_reuse),
  (SELECT commessa_id::text FROM tmp_commessa_sc),
  'fn_get_or_create_commessa riusa commessa aperta (chiude=false)'
);

-- ============================================================
-- TEST: upsert funziona su commessa modificabile (BOZZA)
-- ============================================================

CREATE TEMP TABLE tmp_upsert_sc AS
SELECT r.attivita_id AS commessa_attivita_id
FROM vendite.fn_upsert_commessa_attivita(
  p_commessa_id => (SELECT commessa_id FROM tmp_commessa_sc),
  p_segment_key => ('SEG-SC-' || substr(md5(clock_timestamp()::text), 1, 16))::varchar,
  p_articolo_id => (SELECT articolo_id FROM tmp_refs_sc),
  p_istanza_utility_id => (SELECT istanza_utility_id FROM tmp_refs_sc),
  p_data_attivita => DATE '2026-07-15',
  p_uom_id => (SELECT uom_id FROM tmp_refs_sc),
  p_quantita => 1.000000,
  p_competenza_mese => DATE '2026-07-01',
  p_competenza_dal => DATE '2026-07-01',
  p_competenza_al => DATE '2026-07-31',
  p_prezzo_snapshot => 10.0000000000,
  p_stato_approvazione => 'APPROVATA',
  p_stato_emissione => 'NON_EMESSA',
  p_tipo_movimento => 'NORMALE',
  p_tipo_consumo => 'CONGUAGLIO',
  p_meta => jsonb_build_object('case', 'SC_UPSERT')
) r;

SELECT ok(
  (SELECT commessa_attivita_id IS NOT NULL FROM tmp_upsert_sc),
  'fn_upsert_commessa_attivita funziona su commessa modificabile'
);

-- ============================================================
-- TEST: upsert bloccata su commessa CHIUSA (modificabile=false)
-- ============================================================

-- Porta la commessa in stato CHIUSA (id=5, modificabile=false)
UPDATE vendite.commesse
SET stato_commessa_id = 5
WHERE id = (SELECT commessa_id FROM tmp_commessa_sc);

SELECT throws_ok(
  $$
    SELECT vendite.fn_upsert_commessa_attivita(
      p_commessa_id => (SELECT commessa_id FROM tmp_commessa_sc),
      p_segment_key => 'SEG-SC-BLOCKED',
      p_articolo_id => (SELECT articolo_id FROM tmp_refs_sc),
      p_istanza_utility_id => (SELECT istanza_utility_id FROM tmp_refs_sc),
      p_data_attivita => DATE '2026-07-15',
      p_uom_id => (SELECT uom_id FROM tmp_refs_sc),
      p_quantita => 1.000000,
      p_competenza_mese => DATE '2026-07-01',
      p_competenza_dal => DATE '2026-07-01',
      p_competenza_al => DATE '2026-07-31',
      p_prezzo_snapshot => 10.0000000000
    );
  $$,
  'P0001',
  NULL,
  'fn_upsert_commessa_attivita bloccata su commessa non modificabile'
);

-- ============================================================
-- TEST: fn_list_commesse_emittibili esclude commesse non emittibili
-- ============================================================

-- CHIUSA non e` emittibile
SELECT ok(
  NOT EXISTS (
    SELECT 1
    FROM vendite.fn_list_commesse_emittibili() x
    WHERE x.commessa_id = (SELECT commessa_id FROM tmp_commessa_sc)
  ),
  'fn_list_commesse_emittibili esclude commesse non emittibili'
);

-- ============================================================
-- TEST: fn_list_commesse_emittibili include commesse emittibili
-- ============================================================

-- Porta in PRONTA_FATTURAZIONE (id=4, emittibile=true)
-- Prima riporta stato_emissione a NON_EMESSA (potrebbe essere stato cambiato)
UPDATE vendite.commesse
SET stato_commessa_id = 4
WHERE id = (SELECT commessa_id FROM tmp_commessa_sc);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM vendite.fn_list_commesse_emittibili() x
    WHERE x.commessa_id = (SELECT commessa_id FROM tmp_commessa_sc)
      AND x.total_non_emesse >= 1
  ),
  'fn_list_commesse_emittibili include commesse emittibili (senza filtro mese)'
);

-- ============================================================
-- TEST: fn_list_commesse_emittibili filtra per competenza_mese
-- ============================================================

-- L'attivita` ha competenza_mese = 2026-07-01, filtro con mese corrispondente
SELECT ok(
  EXISTS (
    SELECT 1
    FROM vendite.fn_list_commesse_emittibili(
      p_competenza_mese => DATE '2026-07-01'
    ) x
    WHERE x.commessa_id = (SELECT commessa_id FROM tmp_commessa_sc)
  ),
  'fn_list_commesse_emittibili filtra per competenza_mese corretto'
);

-- Mese diverso: nessuna attivita` con competenza_mese = 2026-01-01
SELECT ok(
  NOT EXISTS (
    SELECT 1
    FROM vendite.fn_list_commesse_emittibili(
      p_competenza_mese => DATE '2026-01-01'
    ) x
    WHERE x.commessa_id = (SELECT commessa_id FROM tmp_commessa_sc)
  ),
  'fn_list_commesse_emittibili esclude mese non corrispondente'
);

SELECT * FROM finish();
ROLLBACK;
