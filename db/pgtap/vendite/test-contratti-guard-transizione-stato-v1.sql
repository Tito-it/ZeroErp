-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: guard transizione stato su vendite.contratti
--       (migration 20260426-05-create-trgfn-contratti-guard-transizione-stato).
--
-- Indice test (1..7):
--   1) DRAFT -> ATTIVO ammesso
--   2) ATTIVO -> DRAFT vietato (E_CONTRATTO_STATO_TRANSIZIONE_INVALIDA)
--   3) ATTIVO -> CESSATO con valido_al NULL vietato
--   4) ATTIVO -> CESSATO con valido_al futuro vietato
--   5) ATTIVO -> CESSATO con valido_al scaduto ammesso
--   6) CESSATO -> ATTIVO vietato (stato terminale)
--   7) ATTIVO -> ATTIVO no-op ammesso (WHEN distinct filter)
--
-- Strategia fixture:
--   - Clona BA da seed esistente (utility commercio, no tipi_utenze)
--     per non incrociare il guard tipo_classe (vedi test-contratti-
--     modalita-pricing-v1).
--   - Crea contratti modalita' C (no listino, no variazione) con
--     periodi disgiunti per non violare ex_contratti_no_overlap.
--   - SOSPESO escluso dai test: non in scope per il guard attuale.
-- ------------------------------------------------------------

BEGIN;
SELECT plan(7);

-- ============================================================
-- Setup fixture: BA + lookup stati
-- ============================================================
CREATE TEMP TABLE tmp_ctx_ba AS
SELECT ba.id AS billing_account_id,
       ba.istanza_utility_id,
       ba.utility_id
  FROM anagrafiche.billing_account ba
 WHERE NOT EXISTS (
     SELECT 1 FROM config.tipi_utenze tu WHERE tu.utility_id = ba.utility_id
 )
 ORDER BY ba.id
 LIMIT 1;

CREATE TEMP TABLE tmp_ctx_stati AS
SELECT
    (SELECT id FROM config.stati_doc_contratti WHERE codice_interno = 'DRAFT')   AS id_draft,
    (SELECT id FROM config.stati_doc_contratti WHERE codice_interno = 'ATTIVO')  AS id_attivo,
    (SELECT id FROM config.stati_doc_contratti WHERE codice_interno = 'CESSATO') AS id_cessato;

CREATE TEMP TABLE tmp_ctx_listino AS
SELECT id AS listino_id FROM vendite.listini WHERE attivo IS TRUE ORDER BY id LIMIT 1;

-- ============================================================
-- Slot fixture: 5 contratti modalita' A su periodi disgiunti.
--   _A   DRAFT  2080-01-01..2080-12-31 (test 1: DRAFT->ATTIVO)
--   _B   ATTIVO 2081-01-01..2081-12-31 (test 2,3,4)
--   _C   ATTIVO 2020-01-01..2020-12-31 (test 5: valido_al scaduto)
--   _D   CESSATO 2019-01-01..2019-12-31 (test 6, storica)
--   _E   ATTIVO 2082-01-01..2082-12-31 (test 7, no-op)
--
-- Tutti in modalita' A (listino + variazione globale) per evitare il
-- guard trgfn_contratti_guard_modalita_c_activation che richiederebbe
-- righe contratti_righe con prezzo_unitario sia all'attivazione (test 1)
-- sia all'INSERT diretto in ATTIVO (test 2-7).
-- ============================================================

INSERT INTO vendite.contratti(
    numero, billing_account_id, istanza_utility_id, utility_id,
    stato_doc_contratto_id, valido_dal, valido_al,
    listino_id, tipo_variazione_globale, valore_variazione_globale
)
SELECT 'PGTAP_GUARD_A', ba.billing_account_id, ba.istanza_utility_id, ba.utility_id,
       s.id_draft, DATE '2080-01-01', DATE '2080-12-31',
       l.listino_id, 'PERCENTUALE', -10
  FROM tmp_ctx_ba ba, tmp_ctx_stati s, tmp_ctx_listino l;

INSERT INTO vendite.contratti(
    numero, billing_account_id, istanza_utility_id, utility_id,
    stato_doc_contratto_id, valido_dal, valido_al,
    listino_id, tipo_variazione_globale, valore_variazione_globale
)
SELECT 'PGTAP_GUARD_B', ba.billing_account_id, ba.istanza_utility_id, ba.utility_id,
       s.id_attivo, DATE '2081-01-01', DATE '2081-12-31',
       l.listino_id, 'PERCENTUALE', -10
  FROM tmp_ctx_ba ba, tmp_ctx_stati s, tmp_ctx_listino l;

INSERT INTO vendite.contratti(
    numero, billing_account_id, istanza_utility_id, utility_id,
    stato_doc_contratto_id, valido_dal, valido_al,
    listino_id, tipo_variazione_globale, valore_variazione_globale
)
SELECT 'PGTAP_GUARD_C', ba.billing_account_id, ba.istanza_utility_id, ba.utility_id,
       s.id_attivo, DATE '2020-01-01', DATE '2020-12-31',
       l.listino_id, 'PERCENTUALE', -10
  FROM tmp_ctx_ba ba, tmp_ctx_stati s, tmp_ctx_listino l;

INSERT INTO vendite.contratti(
    numero, billing_account_id, istanza_utility_id, utility_id,
    stato_doc_contratto_id, valido_dal, valido_al,
    listino_id, tipo_variazione_globale, valore_variazione_globale
)
SELECT 'PGTAP_GUARD_D', ba.billing_account_id, ba.istanza_utility_id, ba.utility_id,
       s.id_cessato, DATE '2019-01-01', DATE '2019-12-31',
       l.listino_id, 'PERCENTUALE', -10
  FROM tmp_ctx_ba ba, tmp_ctx_stati s, tmp_ctx_listino l;

INSERT INTO vendite.contratti(
    numero, billing_account_id, istanza_utility_id, utility_id,
    stato_doc_contratto_id, valido_dal, valido_al,
    listino_id, tipo_variazione_globale, valore_variazione_globale
)
SELECT 'PGTAP_GUARD_E', ba.billing_account_id, ba.istanza_utility_id, ba.utility_id,
       s.id_attivo, DATE '2082-01-01', DATE '2082-12-31',
       l.listino_id, 'PERCENTUALE', -10
  FROM tmp_ctx_ba ba, tmp_ctx_stati s, tmp_ctx_listino l;

-- ============================================================
-- 1) DRAFT -> ATTIVO ammesso
-- ============================================================
SELECT lives_ok(
    $$UPDATE vendite.contratti
         SET stato_doc_contratto_id = (SELECT id_attivo FROM tmp_ctx_stati)
       WHERE numero = 'PGTAP_GUARD_A'$$,
    'DRAFT -> ATTIVO e'' una transizione ammessa dal workflow contratti'
);

-- ============================================================
-- 2) ATTIVO -> DRAFT vietato (PGTAP_GUARD_B e'' ATTIVO)
-- ============================================================
SELECT throws_ok(
    $$UPDATE vendite.contratti
         SET stato_doc_contratto_id = (SELECT id_draft FROM tmp_ctx_stati)
       WHERE numero = 'PGTAP_GUARD_B'$$,
    'P0001',
    NULL,
    'ATTIVO -> DRAFT deve essere bloccato (irreversibile)'
);

-- ============================================================
-- 3) ATTIVO -> CESSATO con valido_al NULL vietato (PGTAP_GUARD_B)
-- ============================================================
SELECT throws_ok(
    $$UPDATE vendite.contratti
         SET stato_doc_contratto_id = (SELECT id_cessato FROM tmp_ctx_stati),
             valido_al = NULL
       WHERE numero = 'PGTAP_GUARD_B'$$,
    'P0001',
    NULL,
    'ATTIVO -> CESSATO con valido_al NULL deve essere bloccato'
);

-- ============================================================
-- 4) ATTIVO -> CESSATO con valido_al futuro vietato (PGTAP_GUARD_B
--    ha valido_al = 2081-12-31 nel futuro; UPDATE solo dello stato)
-- ============================================================
SELECT throws_ok(
    $$UPDATE vendite.contratti
         SET stato_doc_contratto_id = (SELECT id_cessato FROM tmp_ctx_stati)
       WHERE numero = 'PGTAP_GUARD_B'$$,
    'P0001',
    NULL,
    'ATTIVO -> CESSATO con valido_al futuro deve essere bloccato'
);

-- ============================================================
-- 5) ATTIVO -> CESSATO con valido_al scaduto ammesso (PGTAP_GUARD_C
--    ha valido_al = 2020-12-31 nel passato)
-- ============================================================
SELECT lives_ok(
    $$UPDATE vendite.contratti
         SET stato_doc_contratto_id = (SELECT id_cessato FROM tmp_ctx_stati)
       WHERE numero = 'PGTAP_GUARD_C'$$,
    'ATTIVO -> CESSATO con valido_al scaduto e'' ammessa'
);

-- ============================================================
-- 6) CESSATO -> ATTIVO vietato (PGTAP_GUARD_D)
-- ============================================================
SELECT throws_ok(
    $$UPDATE vendite.contratti
         SET stato_doc_contratto_id = (SELECT id_attivo FROM tmp_ctx_stati)
       WHERE numero = 'PGTAP_GUARD_D'$$,
    'P0001',
    NULL,
    'CESSATO -> ATTIVO deve essere bloccato (stato terminale)'
);

-- ============================================================
-- 7) ATTIVO -> ATTIVO no-op ammesso (WHEN distinct filter skippa il guard)
-- ============================================================
SELECT lives_ok(
    $$UPDATE vendite.contratti
         SET stato_doc_contratto_id = (SELECT id_attivo FROM tmp_ctx_stati)
       WHERE numero = 'PGTAP_GUARD_E'$$,
    'ATTIVO -> ATTIVO (no-op) non deve invocare il guard'
);

SELECT * FROM finish();
ROLLBACK;
