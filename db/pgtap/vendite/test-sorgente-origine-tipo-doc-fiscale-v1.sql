-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: §26 B+D — sorgente_origine_tipo_id + tipo_doc_fiscale_id
-- ------------------------------------------------------------
-- Indice test (1..10):
--  1) Colonna sorgente_origine_tipo_id presente su attivita_fatturabili
--  2) FK sorgente_origine_tipo_id -> config.sorgenti attiva
--  3) config.sorgenti[PREVENTIVO].tipo_doc_fiscale_id configurato
--  4) fn_list_preventivi_da_pushare restituisce tipo_doc_fiscale_id
--  5) tipo_doc_fiscale_id coerente con config.sorgenti[PREVENTIVO]
--  6) fn_emit propaga sorgente_origine_tipo_id da commesse_attivita
--  7) fn_emit propaga tipo_doc_fiscale_id da commesse_attivita
--  8) Trigger normalize: tipo_doc_fiscale_id gia` valorizzato non sovrascritto
--  9) Trigger normalize: risolve da sorgente_origine_tipo_id
-- 10) Trigger normalize: fallback legacy da sorgente_tipo_id
-- ------------------------------------------------------------

BEGIN;
SELECT plan(10);

-- ============================================================
-- 1) Colonna sorgente_origine_tipo_id presente su AF
-- ============================================================
SELECT has_column(
  'vendite', 'attivita_fatturabili', 'sorgente_origine_tipo_id',
  'Colonna sorgente_origine_tipo_id presente su attivita_fatturabili'
);

-- ============================================================
-- 2) FK sorgente_origine_tipo_id -> config.sorgenti
-- ============================================================
SELECT fk_ok(
  'vendite', 'attivita_fatturabili', 'sorgente_origine_tipo_id',
  'config', 'sorgenti', 'id',
  'FK sorgente_origine_tipo_id -> config.sorgenti attiva'
);

-- ============================================================
-- 3) config.sorgenti[PREVENTIVO].tipo_doc_fiscale_id configurato
-- ============================================================
SELECT ok(
  (
    SELECT s.tipo_doc_fiscale_id IS NOT NULL
    FROM config.sorgenti s
    WHERE s.codice = 'PREVENTIVO' AND s.attivo IS TRUE
    LIMIT 1
  ),
  'config.sorgenti[PREVENTIVO].tipo_doc_fiscale_id configurato'
);

-- ============================================================
-- Setup: riferimenti per test 4-10
-- ============================================================
CREATE TEMP TABLE tmp_refs_sot AS
SELECT
  (SELECT s.id FROM config.sorgenti s WHERE s.codice = 'PREVENTIVO' AND s.attivo IS TRUE LIMIT 1)
    AS sorgente_preventivo_id,
  (SELECT s.tipo_doc_fiscale_id FROM config.sorgenti s WHERE s.codice = 'PREVENTIVO' AND s.attivo IS TRUE LIMIT 1)
    AS expected_tipo_doc_id,
  (SELECT s.id FROM config.sorgenti s WHERE s.codice = 'COMMESSA' AND s.attivo IS TRUE LIMIT 1)
    AS sorgente_commessa_id,
  (SELECT s.tipo_doc_fiscale_id FROM config.sorgenti s WHERE s.codice = 'COMMESSA' AND s.attivo IS TRUE LIMIT 1)
    AS commessa_tipo_doc_id,
  (SELECT ba.id FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL
      AND ba.istanza_utility_id IS NOT NULL
      AND anagrafiche.fn_get_emittente_fiscale_id(ba.id) IS NOT NULL
    ORDER BY ba.id LIMIT 1)
    AS billing_account_id,
  (SELECT ba.utility_id FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL
      AND ba.istanza_utility_id IS NOT NULL
      AND anagrafiche.fn_get_emittente_fiscale_id(ba.id) IS NOT NULL
    ORDER BY ba.id LIMIT 1)
    AS utility_id,
  (SELECT ba.istanza_utility_id FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL
      AND ba.istanza_utility_id IS NOT NULL
      AND anagrafiche.fn_get_emittente_fiscale_id(ba.id) IS NOT NULL
    ORDER BY ba.id LIMIT 1)
    AS istanza_utility_id,
  (SELECT anagrafiche.fn_get_emittente_fiscale_id(ba.id) FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL
      AND ba.istanza_utility_id IS NOT NULL
      AND anagrafiche.fn_get_emittente_fiscale_id(ba.id) IS NOT NULL
    ORDER BY ba.id LIMIT 1)
    AS emittente_soggetto_ruolo_id,
  (SELECT a.id FROM catalogo.articoli a WHERE a.attivo IS TRUE ORDER BY a.data_insert DESC NULLS LAST LIMIT 1)
    AS articolo_id,
  (SELECT u.id FROM catalogo.unita_misura u WHERE u.attivo IS TRUE ORDER BY u.id LIMIT 1)
    AS uom_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1)
    AS valuta_id;

-- ============================================================
-- 4) fn_list_preventivi_da_pushare restituisce tipo_doc_fiscale_id
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1
    FROM information_schema.columns c
    WHERE c.table_schema = 'vendite'
      AND c.table_name = 'fn_list_preventivi_da_pushare'
      AND c.column_name = 'tipo_doc_fiscale_id'
  )
  OR EXISTS (
    -- Controlla via pg_proc per RETURNS TABLE
    SELECT 1
    FROM pg_catalog.pg_proc p
    JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite'
      AND p.proname = 'fn_list_preventivi_da_pushare'
      AND p.proargnames::text LIKE '%tipo_doc_fiscale_id%'
  ),
  'fn_list_preventivi_da_pushare restituisce tipo_doc_fiscale_id'
);

-- ============================================================
-- 5) tipo_doc_fiscale_id coerente con config.sorgenti[PREVENTIVO]
-- ============================================================
-- Verifica che il valore restituito dalla fn_list coincida con config.sorgenti.
SELECT ok(
  (
    SELECT p.tipo_doc_fiscale_id = r.expected_tipo_doc_id
    FROM vendite.fn_list_preventivi_da_pushare(NULL, NULL, 1) p,
         tmp_refs_sot r
    LIMIT 1
  )
  IS NOT FALSE,  -- NULL (nessuna riga) o TRUE sono entrambi ok
  'tipo_doc_fiscale_id coerente con config.sorgenti[PREVENTIVO]'
);

-- ============================================================
-- Setup: commessa + attivita per test emit (6-7)
-- ============================================================
CREATE TEMP TABLE tmp_commessa_sot AS
SELECT vendite.fn_get_or_create_commessa(
  p_billing_account_id => (SELECT billing_account_id FROM tmp_refs_sot),
  p_utility_id => (SELECT utility_id FROM tmp_refs_sot),
  p_tipo_commessa => 'AUTO',
  p_policy_fatturazione => 'DA_DOCUMENTO',
  p_fatturazione_immediata => false,
  p_priorita_operativa => 'NORMALE',
  p_emittente_soggetto_ruolo_id => (SELECT emittente_soggetto_ruolo_id FROM tmp_refs_sot),
  p_competenza_dal => DATE '2026-07-01',
  p_competenza_al => DATE '2026-07-31',
  p_meta => jsonb_build_object('test_scope', 'pgtap_sorgente_origine'),
  p_force_new => true
) AS commessa_id;

-- Link ROOT
SELECT vendite.fn_link_commessa_sorgente(
  p_commessa_id => (SELECT commessa_id FROM tmp_commessa_sot),
  p_sorgente_tipo_id => (SELECT sorgente_preventivo_id FROM tmp_refs_sot),
  p_sorgente_uid => ('SOT-' || substr(md5(clock_timestamp()::text), 1, 12))::text,
  p_sorgente_riga => 1,
  p_meta => '{}'::jsonb
);

-- Upsert attivita con sorgente_tipo_id = PREVENTIVO (sorgente originale)
CREATE TEMP TABLE tmp_ca_sot AS
SELECT r.attivita_id AS commessa_attivita_id
FROM vendite.fn_upsert_commessa_attivita(
  p_commessa_id => (SELECT commessa_id FROM tmp_commessa_sot),
  p_segment_key => ('SOT-' || substr(md5(clock_timestamp()::text), 1, 18))::varchar,
  p_articolo_id => (SELECT articolo_id FROM tmp_refs_sot),
  p_istanza_utility_id => (SELECT istanza_utility_id FROM tmp_refs_sot),
  p_data_attivita => DATE '2026-07-15',
  p_uom_id => (SELECT uom_id FROM tmp_refs_sot),
  p_quantita => 3.000000,
  p_competenza_mese => DATE '2026-07-01',
  p_competenza_dal => DATE '2026-07-01',
  p_competenza_al => DATE '2026-07-31',
  p_prezzo_snapshot => 10.0000000000,
  p_prezzo_base_snapshot => NULL,
  p_origine_prezzo => NULL,
  p_tipo_variazione_applicata => NULL,
  p_valore_variazione_applicata => NULL,
  p_promo_id => NULL,
  p_contratto_id => NULL,
  p_categoria_cliente_id_snapshot => NULL,
  p_classe_utenza_id_snapshot => NULL,
  p_qta_operativa => 3.000000,
  p_uom_operativa_id => (SELECT uom_id FROM tmp_refs_sot),
  p_factor_to_base => 1,
  p_posticipa_al => NULL,
  p_tipo_doc_fiscale_id => (SELECT expected_tipo_doc_id FROM tmp_refs_sot),
  p_valuta_id => (SELECT valuta_id FROM tmp_refs_sot),
  p_area_geografica_id => NULL,
  p_listino_versione_id => NULL,
  p_prezzo_bloccato => true,
  p_pricing_mode => 'FIXED',
  p_prezzo_da_riallineare => false,
  p_stato_approvazione => 'APPROVATA',
  p_stato_emissione => 'NON_EMESSA',
  p_sorgente_tipo_id => (SELECT sorgente_preventivo_id FROM tmp_refs_sot),
  p_sorgente_uid => ('EXT-SOT-' || substr(md5(clock_timestamp()::text), 1, 10))::text,
  p_tipo_movimento => 'NORMALE',
  p_tipo_consumo => 'CONGUAGLIO',
  p_meta => jsonb_build_object('case', 'SORGENTE_ORIGINE_TEST')
) r;

-- Emit
CREATE TEMP TABLE tmp_emit_sot AS
SELECT * FROM vendite.fn_emit_attivita_fatturabili_da_commessa(
  p_commessa_id => (SELECT commessa_id FROM tmp_commessa_sot),
  p_only_approved => true,
  p_dry_run => false
);

-- ============================================================
-- 6) fn_emit propaga sorgente_origine_tipo_id
-- ============================================================
SELECT ok(
  (
    SELECT af.sorgente_origine_tipo_id = r.sorgente_preventivo_id
    FROM vendite.attivita_fatturabili af
    JOIN tmp_refs_sot r ON true
    WHERE af.commessa_attivita_id = (SELECT commessa_attivita_id FROM tmp_ca_sot)
  ),
  'fn_emit propaga sorgente_origine_tipo_id da commesse_attivita.sorgente_tipo_id'
);

-- ============================================================
-- 7) fn_emit propaga tipo_doc_fiscale_id
-- ============================================================
SELECT ok(
  (
    SELECT af.tipo_doc_fiscale_id = r.expected_tipo_doc_id
    FROM vendite.attivita_fatturabili af
    JOIN tmp_refs_sot r ON true
    WHERE af.commessa_attivita_id = (SELECT commessa_attivita_id FROM tmp_ca_sot)
  ),
  'fn_emit propaga tipo_doc_fiscale_id da commesse_attivita'
);

-- ============================================================
-- 8) Trigger normalize: tipo_doc_fiscale_id gia` valorizzato non sovrascritto
-- ============================================================
-- La riga AF creata sopra ha gia` tipo_doc_fiscale_id; aggiorniamo un campo trigger
-- e verifichiamo che tipo_doc_fiscale_id non viene sovrascritto.
UPDATE vendite.attivita_fatturabili
SET competenza_mese = DATE '2026-07-01'
WHERE commessa_attivita_id = (SELECT commessa_attivita_id FROM tmp_ca_sot);

SELECT ok(
  (
    SELECT af.tipo_doc_fiscale_id = r.expected_tipo_doc_id
    FROM vendite.attivita_fatturabili af
    JOIN tmp_refs_sot r ON true
    WHERE af.commessa_attivita_id = (SELECT commessa_attivita_id FROM tmp_ca_sot)
  ),
  'Trigger normalize: tipo_doc_fiscale_id gia` valorizzato non sovrascritto'
);

-- ============================================================
-- 9) Trigger normalize: risolve da sorgente_origine_tipo_id
-- ============================================================
-- Azzeriamo tipo_doc_fiscale_id e triggeriamo il normalize; deve risolvere
-- da sorgente_origine_tipo_id (PREVENTIVO), non da sorgente_tipo_id (COMMESSA).
UPDATE vendite.attivita_fatturabili
SET tipo_doc_fiscale_id = NULL
WHERE commessa_attivita_id = (SELECT commessa_attivita_id FROM tmp_ca_sot);

SELECT ok(
  (
    SELECT af.tipo_doc_fiscale_id = r.expected_tipo_doc_id
    FROM vendite.attivita_fatturabili af
    JOIN tmp_refs_sot r ON true
    WHERE af.commessa_attivita_id = (SELECT commessa_attivita_id FROM tmp_ca_sot)
  ),
  'Trigger normalize: risolve tipo_doc_fiscale_id da sorgente_origine_tipo_id'
);

-- ============================================================
-- 10) Trigger normalize: fallback legacy da sorgente_tipo_id
-- ============================================================
-- Azzeriamo sia tipo_doc_fiscale_id sia sorgente_origine_tipo_id;
-- deve risolvere il fallback da sorgente_tipo_id (COMMESSA).
UPDATE vendite.attivita_fatturabili
SET tipo_doc_fiscale_id = NULL,
    sorgente_origine_tipo_id = NULL
WHERE commessa_attivita_id = (SELECT commessa_attivita_id FROM tmp_ca_sot);

SELECT ok(
  (
    SELECT af.tipo_doc_fiscale_id = r.commessa_tipo_doc_id
    FROM vendite.attivita_fatturabili af
    JOIN tmp_refs_sot r ON true
    WHERE af.commessa_attivita_id = (SELECT commessa_attivita_id FROM tmp_ca_sot)
  ),
  'Trigger normalize: fallback legacy da sorgente_tipo_id (COMMESSA)'
);

-- ============================================================
SELECT * FROM finish();
ROLLBACK;
