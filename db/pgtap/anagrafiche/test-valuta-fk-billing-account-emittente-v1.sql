-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: la valuta del billing account e dell'emittente fiscale esiste.
-- Oggetti: fk_billing_account_valute, fk_emittenti_fiscali_valute (20261126-38).
-- Riferimento: brief-db-revisione-anagrafiche §24.5 (S29).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - billing_account.valuta_id ed emittenti_fiscali.valuta_id puntano a
--     config.valute(id), come le gemelle di fornitori e gestori;
--   - una valuta che non esiste e' rifiutata dal vincolo (23503).
--
-- Elenco test (plan 3):
--   1) le due FK esistono e puntano a config.valute(id)
--   2) un billing account con una valuta inesistente -> 23503
--   3) un emittente con una valuta inesistente -> 23503
-- ------------------------------------------------------------

BEGIN;

-- pgtap-contesto: escluso — il contesto lo apre dbops.fn_pgtap_crea_mondo_cliente.
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(3);

CREATE TEMP TABLE _t_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('valuta fk');

-- Una valuta che non esiste: oltre il massimo dei vivi.
CREATE TEMP TABLE _t_ref AS
SELECT (SELECT COALESCE(max(id), 0) + 1000 FROM config.valute) AS valuta_inesistente;

-- ⚠️ La tabella puntata si confronta per OID, non per testo: regclass::text
--   dipende dal search_path (col runner esce «valute», da owner «config.valute»).
SELECT results_eq(
    $$SELECT c.conname::text COLLATE "default", c.confrelid = 'config.valute'::regclass
        FROM pg_catalog.pg_constraint c
       WHERE c.contype = 'f'
         AND c.conname IN ('fk_billing_account_valute', 'fk_emittenti_fiscali_valute')
       ORDER BY 1$$,
    $$VALUES ('fk_billing_account_valute', true),
             ('fk_emittenti_fiscali_valute', true)$$,
    '1) le due FK della valuta puntano a config.valute');

SELECT throws_ok(
    format($$UPDATE anagrafiche.billing_account SET valuta_id = %s WHERE id = %s$$,
           (SELECT valuta_inesistente FROM _t_ref), (SELECT billing_account_id FROM _t_mondo)),
    '23503',
    NULL,
    '2) un billing account con una valuta inesistente -> 23503');

SELECT throws_ok(
    format($$UPDATE anagrafiche.emittenti_fiscali SET valuta_id = %s
              WHERE soggetto_ruolo_id = %s$$,
           (SELECT valuta_inesistente FROM _t_ref), (SELECT emittente_soggetto_ruolo_id FROM _t_mondo)),
    '23503',
    NULL,
    '3) un emittente fiscale con una valuta inesistente -> 23503');

SELECT * FROM finish();
ROLLBACK;
