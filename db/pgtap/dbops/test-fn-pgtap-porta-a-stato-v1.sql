-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: dbops.fn_pgtap_porta_a_stato — lo stato raggiunto e' quello chiesto
-- Riferimento: brief-db-revisione-dbops D70 (giro 8, blocco 8a); changeSet
--   20261108-42.
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - la fixture restituisce lo stato raggiunto, e lo stato raggiunto e'
--     sempre quello chiesto: un verbo che non porta dove deve e' un errore
--     del test, e solleva nominando lo stato rimasto;
--   - il caso che lo produce, costruito: la CHIUSA della versione di listino
--     passa da vendite.fn_chiudi_versioni_listino_scadute(), che chiude solo
--     le versioni scadute e non dice niente sulle altre;
--   - con la fine passata la stessa chiamata arriva a CHIUSA;
--   - una testata gia' nello stato chiesto torna quello stato, senza passi.
--
-- Elenco test (plan 3):
--   1) versione ATTIVA senza fine, chiesta CHIUSA: solleva, rimasta ATTIVA
--   2) versione ATTIVA con la fine passata, chiesta CHIUSA: CHIUSA
--   3) versione ATTIVA chiesta ATTIVA: ATTIVA, senza passi
-- ------------------------------------------------------------

BEGIN;
-- Contesto applicativo (preambolo, guardrail_pgtap_preambolo): il builder del
-- mondo lo riapre poi sul suo operatore.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(3);

-- ============================================================
-- FIXTURE — il mondo apre anche il contesto applicativo
-- ============================================================
CREATE TEMP TABLE tmp_pas_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('porta a stato');

-- Due listini, due versioni ATTIVE: una senza fine, una finita nel 2020.
CREATE TEMP TABLE tmp_pas_aperta AS
SELECT * FROM dbops.fn_pgtap_crea_listino(
    (SELECT utility_id FROM tmp_pas_mondo), 'porta a stato aperta',
    '2020-01-01'::date, NULL::date);

CREATE TEMP TABLE tmp_pas_scaduta AS
SELECT * FROM dbops.fn_pgtap_crea_listino(
    (SELECT utility_id FROM tmp_pas_mondo), 'porta a stato scaduta',
    '2020-01-01'::date, '2020-12-31'::date);

-- ============================================================
-- 1..3
-- ============================================================
SELECT throws_like(
    $$SELECT dbops.fn_pgtap_porta_a_stato('vendite.listini_versioni',
           (SELECT listino_versione_id FROM tmp_pas_aperta), 'CHIUSA')$$,
    'fn_pgtap_porta_a_stato: %chiesta in CHIUSA, e'' rimasta in ATTIVA%',
    '1) versione senza fine chiesta CHIUSA: la chiusura delle scadute non la tocca, e la fixture lo dice');

SELECT is(
    dbops.fn_pgtap_porta_a_stato('vendite.listini_versioni',
        (SELECT listino_versione_id FROM tmp_pas_scaduta), 'CHIUSA'),
    'CHIUSA',
    '2) versione con la fine passata chiesta CHIUSA: arriva a CHIUSA');

SELECT is(
    dbops.fn_pgtap_porta_a_stato('vendite.listini_versioni',
        (SELECT listino_versione_id FROM tmp_pas_aperta), 'ATTIVA'),
    'ATTIVA',
    '3) versione gia'' ATTIVA chiesta ATTIVA: torna ATTIVA, senza passi');

SELECT * FROM finish();
ROLLBACK;
