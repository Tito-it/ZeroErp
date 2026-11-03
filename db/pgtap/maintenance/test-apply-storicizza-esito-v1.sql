-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- pgtap-runner: owner
-- pgtap-runner-motivo: il test fa DDL (crea una tabella senza la colonna
--   storicizza) e l'apply fa ALTER TABLE su ogni tabella del set: serve il
--   proprietario delle tabelle, come al job.
--
-- Test: l'apply della storicizzazione dice quante tabelle ha fallito
--   maintenance.fn_apply_storicizza_defaults · maintenance.proc_apply_storicizza_defaults_job
--   maintenance.fn_run_and_log (contratto «riuscita con scarti»)
-- ChangeSet: 20261103-67 · Brief: brief-db-revisione-maintenance D11
--
-- Elenco test (plan 6):
--  1) ✅ la procedura vecchia e' ritirata, la funzione c'e'
--  2) ⭐ una tabella del set senza la colonna storicizza e' contata in _falliti
--  3) ⭐ ... con il dettaglio della riga (FALLITA, il nome)
--  4) ✅ ... e le altre tabelle sono applicate lo stesso (_applicate > 0)
--  5) ⭐ dal job, la corsa con una tabella fallita e' ROSSA,
--     error_code E_JOB_ESITO_CON_SCARTI
--  6) ⭐ ... e il riepilogo e' in meta.esito
--
-- ⚠️ La tabella che fallisce si FABBRICA: esiste (to_regclass la risolve) ma
--   non ha la colonna storicizza, quindi l'ALTER COLUMN fallisce. E' la forma
--   di una tabella che ha perso la colonna dopo essere entrata nel set.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(6);

CREATE TABLE dbops.pgtap_apply_senza_colonna (id integer);

INSERT INTO config.storico_set_storicizza (table_name, insert_manuale)
VALUES ('dbops.pgtap_apply_senza_colonna', true);

-- ============================================================
-- 1. Il ritiro
-- ============================================================
SELECT ok(
    to_regprocedure('maintenance.proc_apply_storicizza_defaults()') IS NULL
    AND to_regprocedure('maintenance.fn_apply_storicizza_defaults()') IS NOT NULL,
    'La procedura vecchia e'' ritirata, la funzione dell''apply c''e'''
);

-- ============================================================
-- 2-4. La funzione conta la tabella fallita
-- ============================================================
CREATE TEMP TABLE tmp_esito AS
SELECT maintenance.fn_apply_storicizza_defaults() AS esito;

SELECT ok(
    (SELECT (esito ->> '_falliti')::integer >= 1 FROM tmp_esito),
    'Una tabella del set senza la colonna storicizza e'' contata in _falliti'
);

SELECT ok(
    (SELECT EXISTS (
        SELECT 1 FROM jsonb_array_elements(esito -> '_dettaglio') d
         WHERE d ->> 'tabella' = 'dbops.pgtap_apply_senza_colonna'
           AND d ->> 'esito'   = 'FALLITA')
       FROM tmp_esito),
    'Il dettaglio nomina la tabella fallita'
);

SELECT ok(
    (SELECT (esito ->> '_applicate')::integer > 0 FROM tmp_esito),
    'Le altre tabelle del set sono applicate lo stesso'
);

-- ============================================================
-- 5-6. Dal job: la corsa e' rossa, il lavoro fatto resta
-- ============================================================
CALL maintenance.proc_apply_storicizza_defaults_job();

SELECT is(
    (SELECT ok::text || ':' || coalesce(error_code, '')
       FROM maintenance.job_run_log
      WHERE jobname = 'apply_storicizza_weekly'
      ORDER BY id DESC LIMIT 1),
    'false:E_JOB_ESITO_CON_SCARTI',
    'Dal job, una corsa con una tabella fallita e'' rossa con E_JOB_ESITO_CON_SCARTI'
);

SELECT ok(
    (SELECT (meta -> 'esito' ->> '_falliti')::integer >= 1
       FROM maintenance.job_run_log
      WHERE jobname = 'apply_storicizza_weekly'
      ORDER BY id DESC LIMIT 1),
    'Il riepilogo dell''apply e'' in meta.esito'
);

SELECT * FROM finish();

ROLLBACK;
