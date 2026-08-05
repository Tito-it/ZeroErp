-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: contratti — combinazioni listino/variazione globale (modello unificato).
--       Aggiornato per Fase 2 refactor contratti (20260515-10):
--       i vecchi test 3-7 sui CHECK/trigger modalità A/B/C rimossi
--       (chk_contratti_modalita_pricing, chk_contratti_variazione_globale_coerente,
--        trg_contratti_a10_guard_modalita_c_activation_ins_upd,
--        trg_contratti_righe_a10_guard_modalita_c_ins_upd droppati).
--
-- Indice test (1..3):
--   1) listino + variazione globale in DRAFT -> ok
--   2) listino NULL + variazione NULL in DRAFT -> ok
--   3) Contratto con listino ATTIVO: riga senza prezzo ammessa (DA_LISTINO)
-- ------------------------------------------------------------

BEGIN;
-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(3);

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

CREATE TEMP TABLE tmp_ctx_stato_draft AS
SELECT id AS stato_id FROM config.stati_doc_contratti WHERE codice_interno = 'DRAFT';

CREATE TEMP TABLE tmp_ctx_stato_attivo AS
SELECT id AS stato_id FROM config.stati_doc_contratti WHERE codice_interno = 'ATTIVO';

CREATE TEMP TABLE tmp_ctx_listino AS
SELECT id AS listino_id FROM vendite.listini WHERE attivo IS TRUE ORDER BY id LIMIT 1;

CREATE TEMP TABLE tmp_ctx_articolo AS
SELECT id AS articolo_id, uom_id FROM catalogo.articoli WHERE attivo IS TRUE ORDER BY id LIMIT 1;

-- 1) listino + variazione globale in DRAFT -> ok
SELECT lives_ok(
    $$INSERT INTO vendite.contratti(
          numero, billing_account_id, istanza_utility_id, utility_id, stato_doc_contratto_id,
          valido_dal, valido_al, listino_id, tipo_variazione_globale, valore_variazione_globale)
      SELECT 'PGTAP_CONTR_A', ba.billing_account_id, ba.istanza_utility_id, ba.utility_id,
             sd.stato_id, '2050-01-01', '2050-12-31',
             l.listino_id, 'PERCENTUALE', -10
        FROM tmp_ctx_ba ba, tmp_ctx_stato_draft sd, tmp_ctx_listino l$$,
    '1) listino + variazione globale in DRAFT ammessa'
);

-- 2) listino NULL + variazione NULL in DRAFT -> ok (ex-modalita'' C)
SELECT lives_ok(
    $$INSERT INTO vendite.contratti(
          numero, billing_account_id, istanza_utility_id, utility_id, stato_doc_contratto_id,
          valido_dal, valido_al, listino_id, tipo_variazione_globale, valore_variazione_globale)
      SELECT 'PGTAP_CONTR_C', ba.billing_account_id, ba.istanza_utility_id, ba.utility_id,
             sd.stato_id, '2051-01-01', '2051-12-31',
             NULL, NULL, NULL
        FROM tmp_ctx_ba ba, tmp_ctx_stato_draft sd$$,
    '2) listino NULL + variazione NULL in DRAFT ammessa'
);

-- Setup per test 3: attiva contratto A
UPDATE vendite.contratti
   SET stato_doc_contratto_id = (SELECT stato_id FROM tmp_ctx_stato_attivo)
 WHERE numero = 'PGTAP_CONTR_A';

-- 3) Contratto con listino ATTIVO: riga senza prezzo_unitario ammessa
--    (il prezzo viene risolto via listino — il guard modalita' C e' droppato)
SELECT lives_ok(
    $$INSERT INTO vendite.contratti_righe(contratto_id, articolo_id, prezzo_unitario, attivo, qta_operativa)
      SELECT c.id, a.articolo_id, NULL, TRUE, 1
        FROM vendite.contratti c, tmp_ctx_articolo a
       WHERE c.numero = 'PGTAP_CONTR_A'$$,
    '3) Contratto con listino ATTIVO: riga senza prezzo_unitario ammessa'
);

SELECT * FROM finish();
ROLLBACK;
