-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: script.fn_pgtap_emittente_operatore — l'emittente di chi agisce, da una sede sola
-- Riferimento: brief-db-revisione-dbops D66 e Q11 di Tid (giro 8, blocco 8b);
--   changeSet 20261108-45.
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - la risposta e' quella di dbops.fn_pgtap_azienda_di_chi_agisce: stessa
--     regola, stessa sede;
--   - senza contesto solleva, nominando questo helper: non sceglie un
--     emittente al posto di chi agisce;
--   - con un utente di contesto che non ha un'azienda solleva: un emittente
--     su cui chi agisce non puo' scrivere non e' una risposta.
--
-- Elenco test (plan 3):
--   1) senza contesto: solleva e nomina script.fn_pgtap_emittente_operatore
--   2) col contesto dell'operatore: lo stesso emittente di dbops.fn_pgtap_azienda_di_chi_agisce
--   3) utente di contesto senza azienda: solleva (prima ripiegava su un emittente qualunque)
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: in testa.
SET CONSTRAINTS ALL IMMEDIATE;

-- pgtap-contesto: escluso — il test 1 prova l'helper SENZA contesto, come lo
--   incontra un file su un database ricostruito; il contesto si apre dopo.

SELECT plan(3);

-- 1) Senza contesto.
SELECT set_config('app.current_user_id', '', true);

SELECT throws_like(
    $$SELECT script.fn_pgtap_emittente_operatore()$$,
    'script.fn_pgtap_emittente_operatore: nessun contesto aperto%',
    '1) senza contesto solleva, nominando l''helper');

-- 2) Col contesto dell'operatore.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT is(
    script.fn_pgtap_emittente_operatore(),
    (SELECT a.emittente_fiscale_id FROM dbops.fn_pgtap_azienda_di_chi_agisce() a),
    '2) col contesto: lo stesso emittente di dbops.fn_pgtap_azienda_di_chi_agisce');

-- 3) Un utente di contesto che non ha un'azienda (nessun utente ha questo id).
--   Per ultimo: cambia il contesto.
SELECT set_config('app.current_user_id', '999999999', true);

SELECT throws_like(
    $$SELECT script.fn_pgtap_emittente_operatore()$$,
    'script.fn_pgtap_emittente_operatore: l''utente di contesto (auth_user_id = 999999999) non ha un''azienda%',
    '3) utente di contesto senza azienda: solleva');

SELECT * FROM finish();
ROLLBACK;
