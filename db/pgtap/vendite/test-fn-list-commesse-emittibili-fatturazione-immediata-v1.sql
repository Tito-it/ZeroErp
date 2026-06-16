-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: filtro fatturazione_immediata in vendite.fn_list_commesse_emittibili
-- (changeset 20260615-11)
-- ------------------------------------------------------------
-- Indice test (1..6):
--  1) filtro true  -> include la commessa immediata
--  2) filtro true  -> esclude la commessa differita
--  3) filtro false -> include la commessa differita
--  4) filtro false -> esclude la commessa immediata
--  5) senza filtro (NULL) -> include entrambe (retro-compat)
--  6) output: colonna fatturazione_immediata coerente per ogni commessa
-- ------------------------------------------------------------

BEGIN;

SELECT plan(6);

-- ============================================================
-- SETUP: riferimenti minimi (billing account con emittente fiscale)
-- ============================================================
CREATE TEMP TABLE tmp_refs_fi AS
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

-- ============================================================
-- SETUP: due commesse stesso perimetro/competenza, una immediata e una differita.
--   fatturazione_immediata e' parte della chiave di dedup di
--   fn_get_or_create_commessa, quindi sono comunque due commesse distinte.
-- ============================================================
CREATE TEMP TABLE tmp_commessa_imm AS
SELECT vendite.fn_get_or_create_commessa(
  p_billing_account_id => (SELECT billing_account_id FROM tmp_refs_fi),
  p_utility_id => (SELECT utility_id FROM tmp_refs_fi),
  p_tipo_commessa => 'AUTO',
  p_policy_fatturazione => 'DA_DOCUMENTO',
  p_fatturazione_immediata => true,
  p_priorita_operativa => 'NORMALE',
  p_competenza_dal => DATE '2026-07-01',
  p_competenza_al => DATE '2026-07-31',
  p_meta => jsonb_build_object('test_scope', 'pgtap_fi_immediata'),
  p_force_new => true
) AS commessa_id;

CREATE TEMP TABLE tmp_commessa_dif AS
SELECT vendite.fn_get_or_create_commessa(
  p_billing_account_id => (SELECT billing_account_id FROM tmp_refs_fi),
  p_utility_id => (SELECT utility_id FROM tmp_refs_fi),
  p_tipo_commessa => 'AUTO',
  p_policy_fatturazione => 'DA_DOCUMENTO',
  p_fatturazione_immediata => false,
  p_priorita_operativa => 'NORMALE',
  p_competenza_dal => DATE '2026-07-01',
  p_competenza_al => DATE '2026-07-31',
  p_meta => jsonb_build_object('test_scope', 'pgtap_fi_differita'),
  p_force_new => true
) AS commessa_id;

-- ============================================================
-- SETUP: una riga APPROVATA + NON_EMESSA per ciascuna commessa
--   (necessaria sia per l'emittibilita' sia per il guard di transizione
--    BOZZA -> PRONTA_FATTURAZIONE).
-- ============================================================
CREATE TEMP TABLE tmp_up_imm AS
SELECT r.attivita_id
FROM vendite.fn_upsert_commessa_attivita(
  p_commessa_id => (SELECT commessa_id FROM tmp_commessa_imm),
  p_segment_key => ('SEG-FI-IMM-' || substr(md5(clock_timestamp()::text), 1, 12))::varchar,
  p_articolo_id => (SELECT articolo_id FROM tmp_refs_fi),
  p_istanza_utility_id => (SELECT istanza_utility_id FROM tmp_refs_fi),
  p_data_attivita => DATE '2026-07-15',
  p_uom_id => (SELECT uom_id FROM tmp_refs_fi),
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
  p_meta => jsonb_build_object('case', 'FI_IMM')
) r;

CREATE TEMP TABLE tmp_up_dif AS
SELECT r.attivita_id
FROM vendite.fn_upsert_commessa_attivita(
  p_commessa_id => (SELECT commessa_id FROM tmp_commessa_dif),
  p_segment_key => ('SEG-FI-DIF-' || substr(md5(clock_timestamp()::text), 1, 12))::varchar,
  p_articolo_id => (SELECT articolo_id FROM tmp_refs_fi),
  p_istanza_utility_id => (SELECT istanza_utility_id FROM tmp_refs_fi),
  p_data_attivita => DATE '2026-07-15',
  p_uom_id => (SELECT uom_id FROM tmp_refs_fi),
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
  p_meta => jsonb_build_object('case', 'FI_DIF')
) r;

-- Porta entrambe in PRONTA_FATTURAZIONE (stato emittibile)
SELECT * FROM vendite.fn_cambia_stato_commessa(
  (SELECT commessa_id FROM tmp_commessa_imm), 'PRONTA_FATTURAZIONE');
SELECT * FROM vendite.fn_cambia_stato_commessa(
  (SELECT commessa_id FROM tmp_commessa_dif), 'PRONTA_FATTURAZIONE');

-- ============================================================
-- TEST 1-2: filtro true -> solo immediata
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1
    FROM vendite.fn_list_commesse_emittibili(p_fatturazione_immediata => true) x
    WHERE x.commessa_id = (SELECT commessa_id FROM tmp_commessa_imm)
  ),
  'filtro true -> include la commessa immediata'
);

SELECT ok(
  NOT EXISTS (
    SELECT 1
    FROM vendite.fn_list_commesse_emittibili(p_fatturazione_immediata => true) x
    WHERE x.commessa_id = (SELECT commessa_id FROM tmp_commessa_dif)
  ),
  'filtro true -> esclude la commessa differita'
);

-- ============================================================
-- TEST 3-4: filtro false -> solo differita
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1
    FROM vendite.fn_list_commesse_emittibili(p_fatturazione_immediata => false) x
    WHERE x.commessa_id = (SELECT commessa_id FROM tmp_commessa_dif)
  ),
  'filtro false -> include la commessa differita'
);

SELECT ok(
  NOT EXISTS (
    SELECT 1
    FROM vendite.fn_list_commesse_emittibili(p_fatturazione_immediata => false) x
    WHERE x.commessa_id = (SELECT commessa_id FROM tmp_commessa_imm)
  ),
  'filtro false -> esclude la commessa immediata'
);

-- ============================================================
-- TEST 5: senza filtro (NULL) -> entrambe (retro-compat)
-- ============================================================
SELECT is(
  (
    SELECT count(*)::int
    FROM vendite.fn_list_commesse_emittibili() x
    WHERE x.commessa_id IN (
      (SELECT commessa_id FROM tmp_commessa_imm),
      (SELECT commessa_id FROM tmp_commessa_dif)
    )
  ),
  2,
  'senza filtro (NULL) -> include entrambe (retro-compat)'
);

-- ============================================================
-- TEST 6: colonna output fatturazione_immediata coerente
-- ============================================================
SELECT ok(
  (
    SELECT x.fatturazione_immediata
    FROM vendite.fn_list_commesse_emittibili() x
    WHERE x.commessa_id = (SELECT commessa_id FROM tmp_commessa_imm)
  ) IS TRUE
  AND (
    SELECT x.fatturazione_immediata
    FROM vendite.fn_list_commesse_emittibili() x
    WHERE x.commessa_id = (SELECT commessa_id FROM tmp_commessa_dif)
  ) IS FALSE,
  'output: colonna fatturazione_immediata coerente per ogni commessa'
);

SELECT * FROM finish();

ROLLBACK;
