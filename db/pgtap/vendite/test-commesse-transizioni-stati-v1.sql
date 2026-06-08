-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: macchina di transizioni stato commessa
--   (changeset 20260607-01..06)
--   - vendite.transizioni_stati_commessa (matrice + seed 11 righe)
--   - vendite.trgfn_commesse_guard_transizione (guard BEFORE UPDATE)
--   - vendite.fn_cambia_stato_commessa (entrypoint)
--   - vendite.fn_approva_commessa_attivita (approvazione righe)
-- ------------------------------------------------------------
-- Indice test (1..12):
--  1) Tabella vendite.transizioni_stati_commessa presente
--  2) Trigger guard transizione presente su vendite.commesse
--  3) fn_cambia_stato_commessa presente
--  4) fn_approva_commessa_attivita presente
--  5) Seed: 11 transizioni presenti
--  6) Seed: BOZZA->PRONTA_FATTURAZIONE (1->4) presente e attiva
--  7) Transizione non in matrice rifiutata (BOZZA->CHIUSA)
--  8) ->PRONTA_FATTURAZIONE senza righe approvate rifiutata
--  9) fn_approva_commessa_attivita approva la riga BOZZA (ritorna 1)
-- 10) fn_approva_commessa_attivita idempotente (seconda chiamata ritorna 0)
-- 11) ->PRONTA_FATTURAZIONE ammessa dopo approvazione righe
-- 12) Commessa ora inclusa in fn_list_commesse_emittibili
-- ------------------------------------------------------------

BEGIN;
SELECT plan(12);

-- ============================================================
-- STRUTTURA
-- ============================================================

SELECT has_table(
  'vendite', 'transizioni_stati_commessa',
  'Tabella vendite.transizioni_stati_commessa presente'
);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM pg_trigger tg
    JOIN pg_class c ON c.oid = tg.tgrelid
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'vendite'
      AND c.relname = 'commesse'
      AND tg.tgname = 'trg_commesse_a10_guard_transizione_upd'
  ),
  'Trigger trg_commesse_a10_guard_transizione_upd presente su vendite.commesse'
);

SELECT ok(
  EXISTS (
    SELECT 1 FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite' AND p.proname = 'fn_cambia_stato_commessa'
  ),
  'vendite.fn_cambia_stato_commessa presente'
);

SELECT ok(
  EXISTS (
    SELECT 1 FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite' AND p.proname = 'fn_approva_commessa_attivita'
  ),
  'vendite.fn_approva_commessa_attivita presente'
);

-- ============================================================
-- SEED MATRICE
-- ============================================================

SELECT is(
  (SELECT count(*)::int FROM vendite.transizioni_stati_commessa),
  11,
  'Seed: 11 transizioni presenti'
);

SELECT ok(
  EXISTS (
    SELECT 1 FROM vendite.transizioni_stati_commessa t
    WHERE t.stato_da_id = 1 AND t.stato_a_id = 4 AND t.attivo IS TRUE
  ),
  'Seed: BOZZA->PRONTA_FATTURAZIONE (1->4) presente e attiva'
);

-- ============================================================
-- SETUP DATI TEST
-- ============================================================

CREATE TEMP TABLE tmp_refs_tsc AS
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

-- Commessa di test (force_new per isolamento), nasce in BOZZA
CREATE TEMP TABLE tmp_commessa_tsc AS
SELECT vendite.fn_get_or_create_commessa(
  p_billing_account_id => (SELECT billing_account_id FROM tmp_refs_tsc),
  p_utility_id => (SELECT utility_id FROM tmp_refs_tsc),
  p_tipo_commessa => 'AUTO',
  p_policy_fatturazione => 'DA_DOCUMENTO',
  p_fatturazione_immediata => false,
  p_priorita_operativa => 'NORMALE',
  p_competenza_dal => DATE '2026-08-01',
  p_competenza_al => DATE '2026-08-31',
  p_meta => jsonb_build_object('test_scope', 'pgtap_transizioni_commessa'),
  p_force_new => true
) AS commessa_id;

-- Una riga in stato_approvazione BOZZA (NON ancora approvata), NON_EMESSA
CREATE TEMP TABLE tmp_att_tsc AS
SELECT r.attivita_id AS commessa_attivita_id
FROM vendite.fn_upsert_commessa_attivita(
  p_commessa_id => (SELECT commessa_id FROM tmp_commessa_tsc),
  p_segment_key => 'SEG-TSC-1',
  p_articolo_id => (SELECT articolo_id FROM tmp_refs_tsc),
  p_istanza_utility_id => (SELECT istanza_utility_id FROM tmp_refs_tsc),
  p_data_attivita => DATE '2026-08-15',
  p_uom_id => (SELECT uom_id FROM tmp_refs_tsc),
  p_quantita => 1.000000,
  p_competenza_mese => DATE '2026-08-01',
  p_competenza_dal => DATE '2026-08-01',
  p_competenza_al => DATE '2026-08-31',
  p_prezzo_snapshot => 10.0000000000,
  p_prezzo_base_snapshot => NULL,
  p_origine_prezzo => NULL,
  p_tipo_variazione_applicata => NULL,
  p_valore_variazione_applicata => NULL,
  p_promo_id => NULL,
  p_contratto_id => NULL,
  p_categoria_cliente_id_snapshot => NULL,
  p_classe_utenza_id_snapshot => NULL,
  p_stato_approvazione => 'BOZZA',
  p_stato_emissione => 'NON_EMESSA',
  p_tipo_movimento => 'NORMALE',
  p_tipo_consumo => 'CONGUAGLIO',
  p_meta => jsonb_build_object('case', 'TSC')
) r;

-- ============================================================
-- TEST: transizione non in matrice rifiutata
--   BOZZA->CHIUSA non esiste in vendite.transizioni_stati_commessa.
-- ============================================================

SELECT throws_ok(
  $$ SELECT * FROM vendite.fn_cambia_stato_commessa(
       (SELECT commessa_id FROM tmp_commessa_tsc), 'CHIUSA') $$,
  'P0001',
  NULL,
  'Transizione non in matrice (BOZZA->CHIUSA) rifiutata'
);

-- ============================================================
-- TEST: ->PRONTA_FATTURAZIONE senza righe approvate rifiutata
--   La riga e' ancora in stato_approvazione BOZZA: guard di dominio scatta.
-- ============================================================

SELECT throws_ok(
  $$ SELECT * FROM vendite.fn_cambia_stato_commessa(
       (SELECT commessa_id FROM tmp_commessa_tsc), 'PRONTA_FATTURAZIONE') $$,
  'P0001',
  NULL,
  '->PRONTA_FATTURAZIONE senza righe approvate rifiutata'
);

-- ============================================================
-- TEST: fn_approva_commessa_attivita
-- ============================================================

SELECT is(
  (SELECT vendite.fn_approva_commessa_attivita(
     (SELECT commessa_id FROM tmp_commessa_tsc), NULL, 'pgtap')),
  1,
  'fn_approva_commessa_attivita approva la riga BOZZA (ritorna 1)'
);

SELECT is(
  (SELECT vendite.fn_approva_commessa_attivita(
     (SELECT commessa_id FROM tmp_commessa_tsc), NULL, 'pgtap')),
  0,
  'fn_approva_commessa_attivita idempotente (seconda chiamata ritorna 0)'
);

-- ============================================================
-- TEST: ->PRONTA_FATTURAZIONE ammessa dopo approvazione
-- ============================================================

SELECT lives_ok(
  $$ SELECT * FROM vendite.fn_cambia_stato_commessa(
       (SELECT commessa_id FROM tmp_commessa_tsc), 'PRONTA_FATTURAZIONE') $$,
  '->PRONTA_FATTURAZIONE ammessa dopo approvazione righe'
);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM vendite.fn_list_commesse_emittibili() x
    WHERE x.commessa_id = (SELECT commessa_id FROM tmp_commessa_tsc)
  ),
  'Commessa ora inclusa in fn_list_commesse_emittibili'
);

SELECT * FROM finish();
ROLLBACK;
