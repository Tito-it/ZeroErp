-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: guard transizione stato su vendite.contratti
--       (migration 20260426-05, aggiornato 20260514-02).
--
-- Indice test (1..9):
--   1) DRAFT -> ATTIVO ammesso
--   2) ATTIVO -> DRAFT vietato (E_CONTRATTO_STATO_TRANSIZIONE_INVALIDA)
--   3) ATTIVO -> CESSATO con valido_al NULL vietato
--   4) ATTIVO -> CESSATO con valido_al futuro AMMESSO  [invertito 20260514]
--   5) ATTIVO -> CESSATO con valido_al passato VIETATO (E_CONTRATTO_VALIDO_AL_RETROATTIVO) [invertito]
--   6) CESSATO -> ATTIVO vietato (stato terminale)
--   7) ATTIVO -> ATTIVO no-op ammesso (WHEN distinct filter)
--   8) ATTIVO -> CESSATO con valido_al = CURRENT_DATE ammesso  [nuovo]
--   9) Job automatico (GUC app.cessazione_automatica=true): valido_al passato ammesso [nuovo]
--
-- Strategia fixture:
--   - Clona BA da seed esistente (utility commercio, no tipi_utenze)
--     per non incrociare il guard tipo_classe.
--   - Crea contratti modalita' A (listino + variazione globale) con
--     periodi disgiunti per non violare ex_contratti_no_overlap.
--   - SOSPESO escluso dai test: non in scope per il guard attuale.
-- ------------------------------------------------------------

BEGIN;
-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(9);

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
-- Slot fixture: 6 contratti modalita' A su periodi disgiunti.
--   _A   DRAFT  2080-01-01..2080-12-31 (test 1: DRAFT->ATTIVO)
--   _B   ATTIVO 2081-01-01..2081-12-31 (test 2,3; valido_al futuro per test 4)
--   _C   ATTIVO 2020-01-01..2020-12-31 (test 5: valido_al passato; test 9: GUC bypass)
--   _D   CESSATO 2019-01-01..2019-12-31 (test 6: terminale)
--   _E   ATTIVO 2082-01-01..2082-12-31 (test 7: no-op)
--   _F   ATTIVO CURRENT_DATE-30..CURRENT_DATE (test 8: valido_al = oggi)
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

INSERT INTO vendite.contratti(
    numero, billing_account_id, istanza_utility_id, utility_id,
    stato_doc_contratto_id, valido_dal, valido_al,
    listino_id, tipo_variazione_globale, valore_variazione_globale
)
SELECT 'PGTAP_GUARD_F', ba.billing_account_id, ba.istanza_utility_id, ba.utility_id,
       s.id_attivo, CURRENT_DATE - 30, CURRENT_DATE,
       l.listino_id, 'PERCENTUALE', -10
  FROM tmp_ctx_ba ba, tmp_ctx_stati s, tmp_ctx_listino l;

-- ============================================================
-- 1) DRAFT -> ATTIVO ammesso
-- ============================================================
SELECT lives_ok(
    $$UPDATE vendite.contratti
         SET stato_doc_contratto_id = (SELECT id_attivo FROM tmp_ctx_stati)
       WHERE numero = 'PGTAP_GUARD_A'$$,
    '1) DRAFT -> ATTIVO e'' una transizione ammessa dal workflow contratti'
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
    '2) ATTIVO -> DRAFT bloccato (irreversibile)'
);

-- ============================================================
-- 3) ATTIVO -> CESSATO con valido_al NULL vietato
-- ============================================================
SELECT throws_ok(
    $$UPDATE vendite.contratti
         SET stato_doc_contratto_id = (SELECT id_cessato FROM tmp_ctx_stati),
             valido_al = NULL
       WHERE numero = 'PGTAP_GUARD_B'$$,
    'P0001',
    NULL,
    '3) ATTIVO -> CESSATO con valido_al NULL bloccato (E_CONTRATTO_STATO_TRANSIZIONE_INVALIDA)'
);

-- ============================================================
-- 4) ATTIVO -> CESSATO con valido_al futuro AMMESSO
--    (PGTAP_GUARD_B ha valido_al = 2081-12-31 nel futuro)
--    Regola post-fix: valido_al >= CURRENT_DATE ammessa.
--    La cessazione e' immediata; il contratto risulta CESSATO con
--    data fine futura (informativa).
-- ============================================================
SELECT lives_ok(
    $$UPDATE vendite.contratti
         SET stato_doc_contratto_id = (SELECT id_cessato FROM tmp_ctx_stati)
       WHERE numero = 'PGTAP_GUARD_B'$$,
    '4) ATTIVO -> CESSATO con valido_al futuro AMMESSO (cessazione programmata)'
);

-- ============================================================
-- 5) ATTIVO -> CESSATO con valido_al passato VIETATO
--    (PGTAP_GUARD_C ha valido_al = 2020-12-31, nel passato)
--    Regola post-fix: cessazione manuale retroattiva bloccata.
--    Errore specifico: E_CONTRATTO_VALIDO_AL_RETROATTIVO (449).
-- ============================================================
SELECT throws_ok(
    $$UPDATE vendite.contratti
         SET stato_doc_contratto_id = (SELECT id_cessato FROM tmp_ctx_stati)
       WHERE numero = 'PGTAP_GUARD_C'$$,
    'P0001',
    NULL,
    '5) ATTIVO -> CESSATO con valido_al passato BLOCCATO (E_CONTRATTO_VALIDO_AL_RETROATTIVO)'
);

-- ============================================================
-- 6) CESSATO -> ATTIVO vietato (PGTAP_GUARD_D e'' CESSATO)
-- ============================================================
SELECT throws_ok(
    $$UPDATE vendite.contratti
         SET stato_doc_contratto_id = (SELECT id_attivo FROM tmp_ctx_stati)
       WHERE numero = 'PGTAP_GUARD_D'$$,
    'P0001',
    NULL,
    '6) CESSATO -> ATTIVO bloccato (stato terminale)'
);

-- ============================================================
-- 7) ATTIVO -> ATTIVO no-op ammesso (WHEN distinct filter)
-- ============================================================
SELECT lives_ok(
    $$UPDATE vendite.contratti
         SET stato_doc_contratto_id = (SELECT id_attivo FROM tmp_ctx_stati)
       WHERE numero = 'PGTAP_GUARD_E'$$,
    '7) ATTIVO -> ATTIVO (no-op) non deve invocare il guard'
);

-- ============================================================
-- 8) ATTIVO -> CESSATO con valido_al = CURRENT_DATE ammesso
--    (PGTAP_GUARD_F ha valido_al = CURRENT_DATE)
--    Caso "cesso il contratto oggi": valido_al = oggi >= oggi.
-- ============================================================
SELECT lives_ok(
    $$UPDATE vendite.contratti
         SET stato_doc_contratto_id = (SELECT id_cessato FROM tmp_ctx_stati)
       WHERE numero = 'PGTAP_GUARD_F'$$,
    '8) ATTIVO -> CESSATO con valido_al = CURRENT_DATE ammesso (cessazione immediata oggi)'
);

-- ============================================================
-- 9) Job automatico (GUC app.cessazione_automatica = true):
--    valido_al passato ammesso — simula fn_apply_chiusura_scadenze.
--    PGTAP_GUARD_C e'' ancora ATTIVO (test 5 era throws_ok, rollback a savepoint).
-- ============================================================
SELECT lives_ok(
    $body$
    DO $inner$
    BEGIN
        PERFORM set_config('app.cessazione_automatica', 'true', true);
        UPDATE vendite.contratti
           SET stato_doc_contratto_id = (SELECT id_cessato FROM tmp_ctx_stati)
         WHERE numero = 'PGTAP_GUARD_C';
    END
    $inner$
    $body$,
    '9) GUC cessazione_automatica=true: valido_al passato ammesso (simula job pgAgent)'
);

SELECT * FROM finish();
ROLLBACK;
