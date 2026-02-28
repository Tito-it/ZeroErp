-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: guardrail anti-bypass commessa su vendite.attivita_fatturabili
-- ------------------------------------------------------------
-- Indice test (1..13):
-- 1) funzione trgfn_attivita_fatturabili_guard_commessa presente
-- 2) trigger guard_commessa presente su attivita_fatturabili
-- 3) parametro attivita_fatturabili_require_commessa presente
-- 4) riferimenti minimi disponibili
-- 5) commessa A creata
-- 6) commessa_attivita A creata
-- 7) emit da commessa A inserisce attivita_fatturabile
-- 8) guard OFF: update con pair coerente consentito
-- 9) guard ON: blocca link commessa null (vincolo NOT NULL)
-- 10) guard ON: blocca pair incompleta (vincolo NOT NULL)
-- 11) guard ON: blocca mismatch tra commessa_id e commessa_attivita_id
-- 12) guard ON: pair coerente accettata
-- 13) guard ON: emit da commessa resta operativo (no regressione pipeline)
-- ------------------------------------------------------------

BEGIN;
SELECT plan(13);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite'
      AND p.proname = 'trgfn_attivita_fatturabili_guard_commessa'
  ),
  'funzione trgfn_attivita_fatturabili_guard_commessa presente'
);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM pg_trigger t
    JOIN pg_class c ON c.oid = t.tgrelid
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'vendite'
      AND c.relname = 'attivita_fatturabili'
      AND t.tgname = 'trg_attivita_fatturabili_a10_guard_commessa_ins_upd'
      AND NOT t.tgisinternal
  ),
  'trigger guard_commessa presente su attivita_fatturabili'
);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM config.parameters p
    WHERE p.code = 'attivita_fatturabili_require_commessa'
  ),
  'parametro attivita_fatturabili_require_commessa presente'
);

CREATE TEMP TABLE tmp_guard_refs AS
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
    SELECT anagrafiche.fn_get_emittente_fiscale_id(ba.id)
    FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL
      AND ba.istanza_utility_id IS NOT NULL
      AND anagrafiche.fn_get_emittente_fiscale_id(ba.id) IS NOT NULL
    ORDER BY ba.id
    LIMIT 1
  ) AS emittente_soggetto_ruolo_id,
  (SELECT id FROM catalogo.articoli WHERE attivo IS TRUE ORDER BY data_insert DESC NULLS LAST LIMIT 1) AS articolo_id,
  (SELECT id FROM catalogo.unita_misura WHERE attivo IS TRUE ORDER BY id LIMIT 1) AS uom_id,
  (SELECT id FROM config.tipi_doc_fiscale WHERE attivo IS TRUE ORDER BY id LIMIT 1) AS tipo_doc_fiscale_id,
  (SELECT id FROM config.valute ORDER BY id LIMIT 1) AS valuta_id,
  (SELECT id FROM config.sorgenti WHERE codice = 'PREVENTIVO' LIMIT 1) AS src_preventivo_id;

SELECT ok(
  (
    SELECT billing_account_id IS NOT NULL
      AND utility_id IS NOT NULL
      AND istanza_utility_id IS NOT NULL
      AND emittente_soggetto_ruolo_id IS NOT NULL
      AND articolo_id IS NOT NULL
      AND uom_id IS NOT NULL
      AND tipo_doc_fiscale_id IS NOT NULL
      AND valuta_id IS NOT NULL
      AND src_preventivo_id IS NOT NULL
    FROM tmp_guard_refs
  ),
  'riferimenti minimi disponibili'
);

INSERT INTO config.sorgenti (
  codice_interno, codice, categoria, descrizione, attivo, target_table, key_selector, scope, meta
)
VALUES (
  'COMMESSA', 'COMMESSA', 'DOCUMENTO', 'Commessa test pgtap guardrail', true,
  'vendite.commesse_attivita'::regclass, 'id', 'PIPELINE_MARKER',
  jsonb_build_object('idempotency_key','segment_key')
)
ON CONFLICT (codice)
DO UPDATE
   SET attivo = true,
       target_table = EXCLUDED.target_table,
       key_selector = EXCLUDED.key_selector,
       data_update = now(),
       user_update = current_user;

CREATE TEMP TABLE tmp_commessa_a AS
SELECT vendite.fn_get_or_create_commessa(
  p_billing_account_id => (SELECT billing_account_id FROM tmp_guard_refs),
  p_utility_id => (SELECT utility_id FROM tmp_guard_refs),
  p_tipo_commessa => 'AUTO',
  p_policy_fatturazione => 'DA_DOCUMENTO',
  p_fatturazione_immediata => false,
  p_priorita_operativa => 'NORMALE',
  p_emittente_soggetto_ruolo_id => (SELECT emittente_soggetto_ruolo_id FROM tmp_guard_refs),
  p_competenza_dal => DATE '2026-07-01',
  p_competenza_al => DATE '2026-07-31',
  p_meta => jsonb_build_object('test_scope', 'pgtap_guardrail_commessa_a'),
  p_force_new => true
) AS commessa_id;

SELECT ok(
  (SELECT commessa_id IS NOT NULL FROM tmp_commessa_a),
  'commessa A creata'
);

SELECT vendite.fn_link_commessa_sorgente(
  p_commessa_id => (SELECT commessa_id FROM tmp_commessa_a),
  p_sorgente_tipo_id => (SELECT src_preventivo_id FROM tmp_guard_refs),
  p_sorgente_uid => ('SRC-A-' || substr(md5(clock_timestamp()::text), 1, 10))::text,
  p_sorgente_riga => 1,
  p_meta => '{}'::jsonb
);

CREATE TEMP TABLE tmp_commessa_att_a AS
SELECT r.attivita_id AS commessa_attivita_id
FROM vendite.fn_upsert_commessa_attivita(
  p_commessa_id => (SELECT commessa_id FROM tmp_commessa_a),
  p_segment_key => ('SEG-A-' || substr(md5(clock_timestamp()::text), 1, 18))::varchar,
  p_articolo_id => (SELECT articolo_id FROM tmp_guard_refs),
  p_istanza_utility_id => (SELECT istanza_utility_id FROM tmp_guard_refs),
  p_data_attivita => DATE '2026-07-15',
  p_uom_id => (SELECT uom_id FROM tmp_guard_refs),
  p_quantita => 1.000000,
  p_competenza_mese => DATE '2026-07-01',
  p_competenza_dal => DATE '2026-07-01',
  p_competenza_al => DATE '2026-07-31',
  p_prezzo_snapshot => 22.1000000000,
  p_qta_operativa => 1.000000,
  p_uom_operativa_id => (SELECT uom_id FROM tmp_guard_refs),
  p_factor_to_base => 1,
  p_posticipa_al => NULL,
  p_tipo_doc_fiscale_id => (SELECT tipo_doc_fiscale_id FROM tmp_guard_refs),
  p_valuta_id => (SELECT valuta_id FROM tmp_guard_refs),
  p_area_geografica_id => NULL,
  p_listino_versione_id => NULL,
  p_prezzo_bloccato => true,
  p_pricing_mode => 'FIXED',
  p_prezzo_da_riallineare => false,
  p_stato_approvazione => 'APPROVATA',
  p_stato_emissione => 'NON_EMESSA',
  p_sorgente_tipo_id => (SELECT src_preventivo_id FROM tmp_guard_refs),
  p_sorgente_uid => ('EXT-A-' || substr(md5(clock_timestamp()::text), 1, 10))::text,
  p_tipo_movimento => 'NORMALE',
  p_tipo_consumo => 'ACCONTO',
  p_meta => jsonb_build_object('case', 'GUARD_A')
) r;

SELECT ok(
  (SELECT commessa_attivita_id IS NOT NULL FROM tmp_commessa_att_a),
  'commessa_attivita A creata'
);

CREATE TEMP TABLE tmp_emit_a AS
SELECT *
FROM vendite.fn_emit_attivita_fatturabili_da_commessa(
  p_commessa_id => (SELECT commessa_id FROM tmp_commessa_a),
  p_only_approved => true,
  p_dry_run => false
);

CREATE TEMP TABLE tmp_af_a AS
SELECT a.id
FROM vendite.attivita_fatturabili a
WHERE a.commessa_id = (SELECT commessa_id FROM tmp_commessa_a)
ORDER BY a.id DESC
LIMIT 1;

SELECT ok(
  (SELECT count(*) = 1 FROM tmp_af_a),
  'emit da commessa A inserisce attivita_fatturabile'
);

UPDATE config.parameters
SET default_value = 'false'
WHERE code = 'attivita_fatturabili_require_commessa';

UPDATE vendite.attivita_fatturabili
SET commessa_id = (SELECT commessa_id FROM tmp_commessa_a),
    commessa_attivita_id = (SELECT commessa_attivita_id FROM tmp_commessa_att_a)
WHERE id = (SELECT id FROM tmp_af_a);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM vendite.attivita_fatturabili a
    WHERE a.id = (SELECT id FROM tmp_af_a)
      AND a.commessa_id = (SELECT commessa_id FROM tmp_commessa_a)
      AND a.commessa_attivita_id = (SELECT commessa_attivita_id FROM tmp_commessa_att_a)
  ),
  'guard OFF: update con pair coerente consentito'
);

UPDATE config.parameters
SET default_value = 'true'
WHERE code = 'attivita_fatturabili_require_commessa';

SELECT throws_ok(
  $$
    UPDATE vendite.attivita_fatturabili
    SET commessa_id = NULL,
        commessa_attivita_id = NULL
    WHERE id = (SELECT id FROM tmp_af_a);
  $$,
  'P0001',
  NULL,
  'guard ON: blocca link commessa null (vincolo NOT NULL)'
);

SELECT throws_ok(
  $$
    UPDATE vendite.attivita_fatturabili
    SET commessa_id = (SELECT commessa_id FROM tmp_commessa_a),
        commessa_attivita_id = NULL
    WHERE id = (SELECT id FROM tmp_af_a);
  $$,
  'P0001',
  NULL,
  'guard ON: blocca pair incompleta (vincolo NOT NULL)'
);

CREATE TEMP TABLE tmp_commessa_b AS
SELECT vendite.fn_get_or_create_commessa(
  p_billing_account_id => (SELECT billing_account_id FROM tmp_guard_refs),
  p_utility_id => (SELECT utility_id FROM tmp_guard_refs),
  p_tipo_commessa => 'AUTO',
  p_policy_fatturazione => 'DA_DOCUMENTO',
  p_fatturazione_immediata => false,
  p_priorita_operativa => 'NORMALE',
  p_emittente_soggetto_ruolo_id => (SELECT emittente_soggetto_ruolo_id FROM tmp_guard_refs),
  p_competenza_dal => DATE '2026-08-01',
  p_competenza_al => DATE '2026-08-31',
  p_meta => jsonb_build_object('test_scope', 'pgtap_guardrail_commessa_b'),
  p_force_new => true
) AS commessa_id;

SELECT vendite.fn_link_commessa_sorgente(
  p_commessa_id => (SELECT commessa_id FROM tmp_commessa_b),
  p_sorgente_tipo_id => (SELECT src_preventivo_id FROM tmp_guard_refs),
  p_sorgente_uid => ('SRC-B-' || substr(md5(clock_timestamp()::text), 1, 10))::text,
  p_sorgente_riga => 2,
  p_meta => '{}'::jsonb
);

CREATE TEMP TABLE tmp_commessa_att_b AS
SELECT r.attivita_id AS commessa_attivita_id
FROM vendite.fn_upsert_commessa_attivita(
  p_commessa_id => (SELECT commessa_id FROM tmp_commessa_b),
  p_segment_key => ('SEG-B-' || substr(md5(clock_timestamp()::text), 1, 18))::varchar,
  p_articolo_id => (SELECT articolo_id FROM tmp_guard_refs),
  p_istanza_utility_id => (SELECT istanza_utility_id FROM tmp_guard_refs),
  p_data_attivita => DATE '2026-08-10',
  p_uom_id => (SELECT uom_id FROM tmp_guard_refs),
  p_quantita => 1.000000,
  p_competenza_mese => DATE '2026-08-01',
  p_competenza_dal => DATE '2026-08-01',
  p_competenza_al => DATE '2026-08-31',
  p_prezzo_snapshot => 22.1000000000,
  p_qta_operativa => 1.000000,
  p_uom_operativa_id => (SELECT uom_id FROM tmp_guard_refs),
  p_factor_to_base => 1,
  p_posticipa_al => NULL,
  p_tipo_doc_fiscale_id => (SELECT tipo_doc_fiscale_id FROM tmp_guard_refs),
  p_valuta_id => (SELECT valuta_id FROM tmp_guard_refs),
  p_area_geografica_id => NULL,
  p_listino_versione_id => NULL,
  p_prezzo_bloccato => true,
  p_pricing_mode => 'FIXED',
  p_prezzo_da_riallineare => false,
  p_stato_approvazione => 'APPROVATA',
  p_stato_emissione => 'NON_EMESSA',
  p_sorgente_tipo_id => (SELECT src_preventivo_id FROM tmp_guard_refs),
  p_sorgente_uid => ('EXT-B-' || substr(md5(clock_timestamp()::text), 1, 10))::text,
  p_tipo_movimento => 'NORMALE',
  p_tipo_consumo => 'ACCONTO',
  p_meta => jsonb_build_object('case', 'GUARD_B')
) r;

SELECT throws_ok(
  $$
    UPDATE vendite.attivita_fatturabili
    SET commessa_id = (SELECT commessa_id FROM tmp_commessa_a),
        commessa_attivita_id = (SELECT commessa_attivita_id FROM tmp_commessa_att_b)
    WHERE id = (SELECT id FROM tmp_af_a);
  $$,
  'P0001',
  NULL,
  'guard ON: blocca mismatch tra commessa_id e commessa_attivita_id'
);

UPDATE vendite.attivita_fatturabili
SET commessa_id = (SELECT commessa_id FROM tmp_commessa_a),
    commessa_attivita_id = (SELECT commessa_attivita_id FROM tmp_commessa_att_a)
WHERE id = (SELECT id FROM tmp_af_a);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM vendite.attivita_fatturabili a
    WHERE a.id = (SELECT id FROM tmp_af_a)
      AND a.commessa_id = (SELECT commessa_id FROM tmp_commessa_a)
      AND a.commessa_attivita_id = (SELECT commessa_attivita_id FROM tmp_commessa_att_a)
  ),
  'guard ON: pair coerente accettata'
);

CREATE TEMP TABLE tmp_emit_b AS
SELECT *
FROM vendite.fn_emit_attivita_fatturabili_da_commessa(
  p_commessa_id => (SELECT commessa_id FROM tmp_commessa_b),
  p_only_approved => true,
  p_dry_run => false
);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM vendite.attivita_fatturabili a
    WHERE a.commessa_id = (SELECT commessa_id FROM tmp_commessa_b)
      AND a.commessa_attivita_id = (SELECT commessa_attivita_id FROM tmp_commessa_att_b)
  ),
  'guard ON: emit da commessa resta operativo (no regressione pipeline)'
);

SELECT * FROM finish();
ROLLBACK;
