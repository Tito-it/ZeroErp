-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- pgtap-runner: owner
-- pgtap-runner-motivo: il test 6 scrive su dbops.messaggi_errore_codici_legacy,
--   registro che lo scrive solo il seed (l'app non ha INSERT).
--
-- Test: la convenzione dei codici d'errore in un posto solo (D22).
-- Brief: brief-db-revisione-dbops, giro 9, blocco 9b (§24, N5).
--   changeSet 20261109-53 (dbops.fn_codice_errore_conforme), 90_end/20261109-57
--   (il CHECK del registro la chiama); il guardrail di CI
--   scripts/sql/guardrail_codice_errore_strutturato.sql la chiama anche lui.
--
-- Elenco test (plan 6):
--   1) la funzione e' IMMUTABLE (entra in un CHECK)
--   2) E_ e W_ conformi
--   3) minuscole, prefisso diverso, trattino: non conformi
--   4) NULL -> NULL
--   5) il CHECK del registro chiama la funzione (nessuna regex ricopiata)
--   6) il registro rifiuta un codice conforme
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(6);

SELECT is((SELECT provolatile FROM pg_proc
            WHERE oid = 'dbops.fn_codice_errore_conforme(text)'::regprocedure)::text,
          'i', '1) dbops.fn_codice_errore_conforme e'' IMMUTABLE');

SELECT ok(dbops.fn_codice_errore_conforme('E_DOC_RIGA_NON_AMMESSA')
          AND dbops.fn_codice_errore_conforme('W_TXID_NOT_REGISTERED'),
          '2) E_ e W_ sono conformi');

SELECT ok(NOT dbops.fn_codice_errore_conforme('e_minuscolo')
          AND NOT dbops.fn_codice_errore_conforme('X_ALTRO')
          AND NOT dbops.fn_codice_errore_conforme('E_CON-TRATTINO')
          AND NOT dbops.fn_codice_errore_conforme('CODICE_NON_MODIFICABILE'),
          '3) minuscole, prefisso diverso, trattino, senza prefisso: non conformi');

SELECT is(dbops.fn_codice_errore_conforme(NULL), NULL::boolean, '4) NULL -> NULL');

SELECT matches(
    (SELECT pg_get_constraintdef(oid) FROM pg_constraint
      WHERE conname = 'chk_messaggi_errore_codici_legacy_non_conforme'),
    'fn_codice_errore_conforme\(codice\)',
    '5) il CHECK del registro chiama la funzione: la regola ha una sede sola');

SELECT throws_ok(
    $$INSERT INTO dbops.messaggi_errore_codici_legacy (codice) VALUES ('E_PGTAP_CONFORME')$$,
    '23514', NULL,
    '6) il registro dei codici fuori convenzione rifiuta un codice conforme');

SELECT * FROM finish();

ROLLBACK;
