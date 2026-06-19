-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: fn_emit_attivita_fatturabili_da_commessa propaga lo snapshot
--       audit pricing v5 (8 colonne) da commesse_attivita ad attivita_fatturabili
-- (changeset 20260616-01)
-- ------------------------------------------------------------
-- Indice test (1..5):
--  1) emit inserisce 1 riga
--  2) prezzo_base_snapshot propagato su attivita_fatturabili
--  3) origine_prezzo propagato
--  4) tipo_variazione_applicata + valore_variazione_applicata propagati
--  5) re-run idempotente: la riga ora EMESSA non e' piu' candidata
-- ------------------------------------------------------------

BEGIN;

SELECT plan(5);

-- ============================================================
-- SETUP: riferimenti minimi
-- ============================================================
CREATE TEMP TABLE tmp_refs_au AS
SELECT
  (
    SELECT ba.id FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL AND ba.istanza_utility_id IS NOT NULL
      AND anagrafiche.fn_get_emittente_fiscale_id(ba.id) IS NOT NULL
    ORDER BY ba.id LIMIT 1
  ) AS billing_account_id,
  (
    SELECT ba.utility_id FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL AND ba.istanza_utility_id IS NOT NULL
      AND anagrafiche.fn_get_emittente_fiscale_id(ba.id) IS NOT NULL
    ORDER BY ba.id LIMIT 1
  ) AS utility_id,
  (
    SELECT ba.istanza_utility_id FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL AND ba.istanza_utility_id IS NOT NULL
      AND anagrafiche.fn_get_emittente_fiscale_id(ba.id) IS NOT NULL
    ORDER BY ba.id LIMIT 1
  ) AS istanza_utility_id,
  (
    SELECT a.id FROM catalogo.articoli a
    WHERE a.attivo IS TRUE ORDER BY a.data_insert DESC NULLS LAST LIMIT 1
  ) AS articolo_id,
  (
    SELECT u.id FROM catalogo.unita_misura u
    WHERE u.attivo IS TRUE ORDER BY u.id LIMIT 1
  ) AS uom_id,
  (
    SELECT s.id FROM config.sorgenti s
    WHERE s.codice = 'PREVENTIVO' LIMIT 1
  ) AS root_sorgente_tipo_id,
  (
    SELECT t.id FROM config.tipi_doc_fiscale t
    WHERE t.attivo IS TRUE ORDER BY t.id LIMIT 1
  ) AS tipo_doc_fiscale_id;

-- Commessa di test isolata
CREATE TEMP TABLE tmp_commessa_au AS
SELECT vendite.fn_get_or_create_commessa(
  p_billing_account_id => (SELECT billing_account_id FROM tmp_refs_au),
  p_utility_id => (SELECT utility_id FROM tmp_refs_au),
  p_tipo_commessa => 'AUTO',
  p_policy_fatturazione => 'DA_DOCUMENTO',
  p_fatturazione_immediata => false,
  p_priorita_operativa => 'NORMALE',
  p_competenza_dal => DATE '2026-07-01',
  p_competenza_al => DATE '2026-07-31',
  p_meta => jsonb_build_object('test_scope', 'pgtap_emit_audit'),
  p_force_new => true
) AS commessa_id;

-- Sorgente ROOT obbligatoria per l'emit (il primo link diventa ROOT)
CREATE TEMP TABLE tmp_link_au AS
SELECT vendite.fn_link_commessa_sorgente(
  p_commessa_id => (SELECT commessa_id FROM tmp_commessa_au),
  p_sorgente_tipo_id => (SELECT root_sorgente_tipo_id FROM tmp_refs_au),
  p_sorgente_uid => ('SRC-AU-' || substr(md5(clock_timestamp()::text), 1, 12))::text,
  p_sorgente_riga => 1,
  p_meta => jsonb_build_object('test_scope', 'pgtap_emit_audit')
) AS link_id;

-- Riga commessa APPROVATA + NON_EMESSA
CREATE TEMP TABLE tmp_ca_au AS
SELECT r.attivita_id AS commessa_attivita_id
FROM vendite.fn_upsert_commessa_attivita(
  p_commessa_id => (SELECT commessa_id FROM tmp_commessa_au),
  p_segment_key => ('SEG-AU-' || substr(md5(clock_timestamp()::text), 1, 14))::varchar,
  p_articolo_id => (SELECT articolo_id FROM tmp_refs_au),
  p_istanza_utility_id => (SELECT istanza_utility_id FROM tmp_refs_au),
  p_data_attivita => DATE '2026-07-15',
  p_uom_id => (SELECT uom_id FROM tmp_refs_au),
  p_quantita => 1.000000,
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
  -- tipo_doc valorizzato: il guard tipo_doc emittibile (20260619-05) richiede
  -- tipo_doc_fiscale_id NOT NULL sulle righe APPROVATA+NON_EMESSA.
  p_tipo_doc_fiscale_id => (SELECT tipo_doc_fiscale_id FROM tmp_refs_au),
  p_stato_approvazione => 'APPROVATA',
  p_stato_emissione => 'NON_EMESSA',
  p_tipo_movimento => 'NORMALE',
  p_tipo_consumo => 'CONGUAGLIO',
  p_meta => jsonb_build_object('case', 'AUDIT')
) r;

-- Valorizza lo snapshot audit sulla riga commessa (isola la logica di emit:
-- colonne non-FK, nessun fixture promo/contratto/categoria/classe).
UPDATE vendite.commesse_attivita
   SET prezzo_base_snapshot = 12.5000000000,
       origine_prezzo = 'MANUALE',
       tipo_variazione_applicata = 'NESSUNA',
       valore_variazione_applicata = 3.5000000000
 WHERE id = (SELECT commessa_attivita_id FROM tmp_ca_au);

-- Porta in PRONTA_FATTURAZIONE (emittibile)
SELECT * FROM vendite.fn_cambia_stato_commessa(
  (SELECT commessa_id FROM tmp_commessa_au), 'PRONTA_FATTURAZIONE');

-- ============================================================
-- EMIT (pull commessa -> attivita_fatturabili)
-- ============================================================
CREATE TEMP TABLE tmp_emit_au AS
SELECT * FROM vendite.fn_emit_attivita_fatturabili_da_commessa(
  (SELECT commessa_id FROM tmp_commessa_au)
);

SELECT is(
  (SELECT inserted_rows FROM tmp_emit_au),
  1,
  'emit inserisce 1 riga'
);

-- Riga AF emessa, individuata via commessa_attivita_id
SELECT is(
  (SELECT a.prezzo_base_snapshot FROM vendite.attivita_fatturabili a
    WHERE a.commessa_attivita_id = (SELECT commessa_attivita_id FROM tmp_ca_au)),
  12.5000000000::numeric,
  'prezzo_base_snapshot propagato su attivita_fatturabili'
);

SELECT is(
  (SELECT a.origine_prezzo FROM vendite.attivita_fatturabili a
    WHERE a.commessa_attivita_id = (SELECT commessa_attivita_id FROM tmp_ca_au)),
  'MANUALE',
  'origine_prezzo propagato'
);

SELECT ok(
  (
    SELECT a.tipo_variazione_applicata = 'NESSUNA'
       AND a.valore_variazione_applicata = 3.5000000000
    FROM vendite.attivita_fatturabili a
    WHERE a.commessa_attivita_id = (SELECT commessa_attivita_id FROM tmp_ca_au)
  ),
  'tipo_variazione_applicata + valore_variazione_applicata propagati'
);

-- ============================================================
-- Re-run idempotente: la riga e' ora EMESSA, non piu' candidata
-- ============================================================
CREATE TEMP TABLE tmp_emit_au2 AS
SELECT * FROM vendite.fn_emit_attivita_fatturabili_da_commessa(
  (SELECT commessa_id FROM tmp_commessa_au)
);

SELECT is(
  (SELECT total_candidate FROM tmp_emit_au2),
  0,
  're-run idempotente: la riga ora EMESSA non e'' piu'' candidata'
);

SELECT * FROM finish();

ROLLBACK;
