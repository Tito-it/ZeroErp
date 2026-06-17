-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: script.fn_available_actions_commessa (capability ciclo di vita commessa)
-- (changeset 20260616-03 + seed transizioni manuali 20260607-05 arricchito)
-- ------------------------------------------------------------
-- Indice test (1..6):
--  1) BOZZA: azione 'annulla' disponibile
--  2) BOZZA: solo 1 azione manuale (automatiche ->APERTA/->PRONTA escluse)
--  3) BOZZA: can_edit_righe = true (stato modificabile)
--  4) PRONTA: azioni = {chiudi, riapri, annulla}
--  5) PRONTA: is_emittibile = true
--  6) CHIUSA (terminale): available_actions=[], can_change_state=false, can_edit_righe=false
-- ------------------------------------------------------------

BEGIN;

SELECT plan(6);

-- ============================================================
-- SETUP
-- ============================================================
CREATE TEMP TABLE tmp_refs_aa AS
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
  ) AS uom_id;

CREATE TEMP TABLE tmp_commessa_aa AS
SELECT vendite.fn_get_or_create_commessa(
  p_billing_account_id => (SELECT billing_account_id FROM tmp_refs_aa),
  p_utility_id => (SELECT utility_id FROM tmp_refs_aa),
  p_tipo_commessa => 'AUTO',
  p_policy_fatturazione => 'DA_DOCUMENTO',
  p_fatturazione_immediata => false,
  p_priorita_operativa => 'NORMALE',
  p_competenza_dal => DATE '2026-07-01',
  p_competenza_al => DATE '2026-07-31',
  p_meta => jsonb_build_object('test_scope', 'pgtap_aa_commessa'),
  p_force_new => true
) AS commessa_id;

-- ============================================================
-- STATO BOZZA (1)
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1 FROM jsonb_array_elements(
      script.fn_available_actions_commessa((SELECT commessa_id FROM tmp_commessa_aa)) -> 'available_actions'
    ) e WHERE e->>'key' = 'annulla'
  ),
  'BOZZA: azione annulla disponibile'
);

SELECT is(
  jsonb_array_length(
    script.fn_available_actions_commessa((SELECT commessa_id FROM tmp_commessa_aa)) -> 'available_actions'
  ),
  1,
  'BOZZA: solo 1 azione manuale (automatiche ->APERTA/->PRONTA escluse)'
);

SELECT is(
  (script.fn_available_actions_commessa((SELECT commessa_id FROM tmp_commessa_aa)) ->> 'can_edit_righe')::boolean,
  true,
  'BOZZA: can_edit_righe = true'
);

-- ============================================================
-- Porta in PRONTA_FATTURAZIONE: serve >=1 riga APPROVATA + NON_EMESSA
-- ============================================================
CREATE TEMP TABLE tmp_ca_aa AS
SELECT r.attivita_id
FROM vendite.fn_upsert_commessa_attivita(
  p_commessa_id => (SELECT commessa_id FROM tmp_commessa_aa),
  p_segment_key => ('SEG-AA-' || substr(md5(clock_timestamp()::text), 1, 14))::varchar,
  p_articolo_id => (SELECT articolo_id FROM tmp_refs_aa),
  p_istanza_utility_id => (SELECT istanza_utility_id FROM tmp_refs_aa),
  p_data_attivita => DATE '2026-07-15',
  p_uom_id => (SELECT uom_id FROM tmp_refs_aa),
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
  p_stato_approvazione => 'APPROVATA',
  p_stato_emissione => 'NON_EMESSA',
  p_tipo_movimento => 'NORMALE',
  p_tipo_consumo => 'CONGUAGLIO',
  p_meta => jsonb_build_object('case', 'AA')
) r;

SELECT * FROM vendite.fn_cambia_stato_commessa(
  (SELECT commessa_id FROM tmp_commessa_aa), 'PRONTA_FATTURAZIONE');

-- ============================================================
-- STATO PRONTA_FATTURAZIONE (4)
-- ============================================================
SELECT is(
  (
    SELECT count(*)::int FROM jsonb_array_elements(
      script.fn_available_actions_commessa((SELECT commessa_id FROM tmp_commessa_aa)) -> 'available_actions'
    ) e WHERE e->>'key' IN ('chiudi', 'riapri', 'annulla')
  ),
  3,
  'PRONTA: azioni = {chiudi, riapri, annulla}'
);

SELECT is(
  (script.fn_available_actions_commessa((SELECT commessa_id FROM tmp_commessa_aa)) ->> 'is_emittibile')::boolean,
  true,
  'PRONTA: is_emittibile = true'
);

-- ============================================================
-- Porta in CHIUSA (terminale) e verifica
-- ============================================================
SELECT * FROM vendite.fn_cambia_stato_commessa(
  (SELECT commessa_id FROM tmp_commessa_aa), 'CHIUSA');

SELECT ok(
  (
    SELECT jsonb_array_length(r -> 'available_actions') = 0
       AND (r ->> 'can_change_state')::boolean = false
       AND (r ->> 'can_edit_righe')::boolean = false
    FROM (SELECT script.fn_available_actions_commessa((SELECT commessa_id FROM tmp_commessa_aa)) AS r) s
  ),
  'CHIUSA: available_actions=[], can_change_state=false, can_edit_righe=false'
);

SELECT * FROM finish();

ROLLBACK;
