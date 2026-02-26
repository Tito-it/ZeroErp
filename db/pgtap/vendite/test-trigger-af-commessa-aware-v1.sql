-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: trigger attivita_fatturabili commessa-aware
-- (changeset 20260227-01, 20260227-02)
-- ------------------------------------------------------------
-- Indice test (1..8):
--  1) trgfn_attivita_fatturabili_normalize presente
--  2) trgfn_attivita_fatturabili_guard_ba_coerenza presente
--  3) Commessa di test creata
--  4) Attivita` inserita nella commessa
--  5) fn_emit produce righe AF con commessa_attivita_id NOT NULL
--  6) Normalize: competenza_mese AF corretta (non sovrascritta)
--  7) Normalize: tipo_doc_fiscale_id risolto anche su riga da commessa
--  8) Normalize: valuta_id risolta anche su riga da commessa
-- ------------------------------------------------------------

BEGIN;
SELECT plan(8);

-- ============================================================
-- TRIGGER PRESENTI
-- ============================================================

SELECT ok(
  EXISTS (
    SELECT 1 FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite'
      AND p.proname = 'trgfn_attivita_fatturabili_normalize'
  ),
  'trgfn_attivita_fatturabili_normalize presente'
);

SELECT ok(
  EXISTS (
    SELECT 1 FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite'
      AND p.proname = 'trgfn_attivita_fatturabili_guard_ba_coerenza'
  ),
  'trgfn_attivita_fatturabili_guard_ba_coerenza presente'
);

-- ============================================================
-- SETUP DATI TEST
-- ============================================================

CREATE TEMP TABLE tmp_refs_tca AS
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
  ) AS uom_id;

-- Crea commessa di test
CREATE TEMP TABLE tmp_commessa_tca AS
SELECT vendite.fn_get_or_create_commessa(
  p_billing_account_id => (SELECT billing_account_id FROM tmp_refs_tca),
  p_utility_id => (SELECT utility_id FROM tmp_refs_tca),
  p_tipo_commessa => 'AUTO',
  p_policy_fatturazione => 'DA_DOCUMENTO',
  p_fatturazione_immediata => false,
  p_priorita_operativa => 'NORMALE',
  p_competenza_dal => DATE '2026-09-01',
  p_competenza_al => DATE '2026-09-30',
  p_meta => jsonb_build_object('test_scope', 'pgtap_trigger_commessa_aware'),
  p_force_new => true
) AS commessa_id;

SELECT ok(
  (SELECT commessa_id IS NOT NULL FROM tmp_commessa_tca),
  'Commessa di test creata'
);

-- Inserisci attivita` con competenza_mese specifica (senza tipo_doc e valuta su CA)
CREATE TEMP TABLE tmp_att_tca AS
SELECT vendite.fn_upsert_commessa_attivita(
  p_commessa_id => (SELECT commessa_id FROM tmp_commessa_tca),
  p_segment_key => ('SEG-TCA-' || substr(md5(clock_timestamp()::text), 1, 12))::varchar,
  p_articolo_id => (SELECT articolo_id FROM tmp_refs_tca),
  p_istanza_utility_id => (SELECT istanza_utility_id FROM tmp_refs_tca),
  p_data_attivita => DATE '2026-09-15',
  p_uom_id => (SELECT uom_id FROM tmp_refs_tca),
  p_quantita => 1.000000,
  p_competenza_mese => DATE '2026-09-01',
  p_competenza_dal => DATE '2026-09-01',
  p_competenza_al => DATE '2026-09-30',
  p_prezzo_snapshot => 50.0000000000,
  p_stato_approvazione => 'APPROVATA',
  p_stato_emissione => 'NON_EMESSA',
  p_sorgente_tipo_id => (
    SELECT s.id FROM config.sorgenti s
    WHERE s.codice = 'PREVENTIVO' AND s.attivo IS TRUE
    LIMIT 1
  ),
  p_sorgente_uid => 'PGTAP-TCA-SRC-' || substr(md5(clock_timestamp()::text), 1, 12),
  p_tipo_movimento => 'NORMALE',
  p_tipo_consumo => 'CONGUAGLIO',
  p_meta => jsonb_build_object('case', 'TCA_TRIGGER_TEST')
) AS commessa_attivita_id;

SELECT ok(
  (SELECT commessa_attivita_id IS NOT NULL FROM tmp_att_tca),
  'Attivita` inserita nella commessa'
);

-- Collega ROOT source (richiesto da fn_emit)
SELECT vendite.fn_link_commessa_sorgente(
  p_commessa_id => (SELECT commessa_id FROM tmp_commessa_tca),
  p_sorgente_tipo_id => (
    SELECT s.id FROM config.sorgenti s
    WHERE s.codice = 'PREVENTIVO' AND s.attivo IS TRUE
    LIMIT 1
  ),
  p_sorgente_uid => 'PGTAP-TCA-' || (SELECT commessa_id FROM tmp_commessa_tca)::text
);

-- Porta commessa in stato PRONTA_FATTURAZIONE (emittibile=true)
UPDATE vendite.commesse
SET stato_commessa_id = 4
WHERE id = (SELECT commessa_id FROM tmp_commessa_tca);

-- Esegui emit: crea righe AF con commessa_attivita_id NOT NULL
CREATE TEMP TABLE tmp_emit_tca AS
SELECT *
FROM vendite.fn_emit_attivita_fatturabili_da_commessa(
  p_commessa_id => (SELECT commessa_id FROM tmp_commessa_tca),
  p_only_approved => true,
  p_dry_run => false
);

-- ============================================================
-- TEST: emit ha prodotto righe AF
-- ============================================================

SELECT ok(
  (SELECT inserted_rows >= 1 FROM tmp_emit_tca),
  'fn_emit produce righe AF con commessa_attivita_id NOT NULL'
);

-- ============================================================
-- TEST: normalize non ha sovrascritto competenza_mese
-- ============================================================

SELECT ok(
  EXISTS (
    SELECT 1
    FROM vendite.attivita_fatturabili af
    WHERE af.commessa_attivita_id = (SELECT commessa_attivita_id FROM tmp_att_tca)
      AND af.competenza_mese = DATE '2026-09-01'
  ),
  'Normalize: competenza_mese AF corretta (non sovrascritta)'
);

-- ============================================================
-- TEST: tipo_doc_fiscale_id risolto (CA non lo aveva)
-- ============================================================

SELECT ok(
  EXISTS (
    SELECT 1
    FROM vendite.attivita_fatturabili af
    WHERE af.commessa_attivita_id = (SELECT commessa_attivita_id FROM tmp_att_tca)
      AND af.tipo_doc_fiscale_id IS NOT NULL
  ),
  'Normalize: tipo_doc_fiscale_id risolto anche su riga da commessa'
);

-- ============================================================
-- TEST: valuta_id risolta (CA non la aveva)
-- ============================================================

SELECT ok(
  EXISTS (
    SELECT 1
    FROM vendite.attivita_fatturabili af
    WHERE af.commessa_attivita_id = (SELECT commessa_attivita_id FROM tmp_att_tca)
      AND af.valuta_id IS NOT NULL
  ),
  'Normalize: valuta_id risolta anche su riga da commessa'
);

SELECT * FROM finish();
ROLLBACK;
