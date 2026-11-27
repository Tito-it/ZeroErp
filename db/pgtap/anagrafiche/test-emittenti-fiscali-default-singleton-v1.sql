-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: il soggetto del test e' una rete che nessuna scrittura legittima
--   raggiunge: la riga dell'azienda predefinita non si cancella e non si sposta, senza
--   porte nemmeno per il proprietario. La fixture la toglie con ALTER TABLE … DISABLE
--   TRIGGER sul rifiuto della cancellazione, che solo il proprietario puo' fare, e solo
--   per quell'istruzione.
-- pgTAP test per Zero ERP
--
-- Test: l'azienda predefinita e' una e una sola (E_EMITTENTE_DEFAULT_SINGLETON).
-- Oggetti: anagrafiche.trgfn_emittenti_fiscali_default_guard,
--   trg_emittenti_fiscali_ba_a10_default_guard_ins_upd_dlt,
--   uq_emittenti_fiscali_ba_default.
-- Riferimento: brief-db-revisione-anagrafiche §25.3 (§15.2), §25.9 (D-T8b-4).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - con almeno un'azienda, il collegamento predefinito c'e' sempre: un
--     collegamento predefinito che manca e' rifiutato dal guard differito,
--     E_EMITTENTE_DEFAULT_SINGLETON;
--   - il secondo collegamento predefinito lo ferma l'indice unico parziale,
--     prima del guard.
--   La via di servizio che toglie la riga si COSTRUISCE: il rifiuto della
--   cancellazione si spegne per una istruzione, dentro un'eccezione che la
--   annulla, e si riaccende subito.
--
-- Elenco test (plan 4):
--   1) PRECONDIZIONE: un'azienda c'e', e il collegamento predefinito e' uno
--   2) il guard e' un trigger differito su emittenti_fiscali_billing_account
--   3) il collegamento predefinito tolto -> E_EMITTENTE_DEFAULT_SINGLETON
--   4) un secondo collegamento predefinito -> uq_emittenti_fiscali_ba_default
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Il DDL qui sotto prende un lock esclusivo su una tabella del modello
--   fino al ROLLBACK: un'attesa diventa un errore che si legge.
SET LOCAL lock_timeout = '10s';

-- pgtap-contesto: escluso — runner owner; l'azienda la costruisce l'helper.
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(4);

-- Un'azienda: su un database vuoto la prima nasce predefinita.
CREATE TEMP TABLE _m AS
SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();

SELECT ok(
    (SELECT count(*) FROM _m) = 1
    AND (SELECT count(*) FROM anagrafiche.emittenti_fiscali_billing_account
          WHERE is_default) = 1,
    '1) PRECONDIZIONE: un''azienda c''e'', e il collegamento predefinito e'' uno');

SELECT ok(
    EXISTS (SELECT 1 FROM pg_trigger t
             WHERE t.tgrelid = 'anagrafiche.emittenti_fiscali_billing_account'::regclass
               AND t.tgname  = 'trg_emittenti_fiscali_ba_a10_default_guard_ins_upd_dlt'
               AND t.tgfoid  = 'anagrafiche.trgfn_emittenti_fiscali_default_guard()'::regprocedure
               AND t.tgdeferrable AND t.tginitdeferred),
    '2) il guard e'' un trigger differito su emittenti_fiscali_billing_account');

-- La via di servizio: il rifiuto della cancellazione spento per una
-- istruzione. L'istruzione gira dentro fn_pgtap_codice_errore, cioe' in un
-- blocco con eccezione: il rifiuto del guard la annulla, e la riga resta.
ALTER TABLE anagrafiche.emittenti_fiscali_billing_account
    DISABLE TRIGGER trg_emittenti_fiscali_ba_a05_block_delete_dlt;

SELECT is(
    dbops.fn_pgtap_codice_errore(
        $$DELETE FROM anagrafiche.emittenti_fiscali_billing_account WHERE is_default$$),
    'E_EMITTENTE_DEFAULT_SINGLETON',
    '3) il collegamento predefinito tolto -> E_EMITTENTE_DEFAULT_SINGLETON');

ALTER TABLE anagrafiche.emittenti_fiscali_billing_account
    ENABLE TRIGGER trg_emittenti_fiscali_ba_a05_block_delete_dlt;

SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        $$INSERT INTO anagrafiche.emittenti_fiscali_billing_account
              (billing_account_id, emittente_soggetto_ruolo_id, is_default, meta)
          VALUES (NULL, %s, true, '{}'::jsonb)$$,
        (SELECT soggetto_ruolo_id FROM _m))),
    'uq_emittenti_fiscali_ba_default',
    '4) un secondo collegamento predefinito -> lo ferma l''indice uq_emittenti_fiscali_ba_default');

SELECT * FROM finish();
ROLLBACK;
