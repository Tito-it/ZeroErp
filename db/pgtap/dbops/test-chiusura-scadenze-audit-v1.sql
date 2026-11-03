-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: la chiusura per scadenza scrive l'audit della sua esecuzione
--   dbops.fn_apply_chiusura_scadenze · dbops.audit_log
-- ChangeSet: 20261103-71 · Brief: brief-db-revisione-maintenance R5
--
-- Elenco test (plan 2):
--  1) ⭐ un giro (senza righe di configurazione attive) scrive UNA riga di
--     audit con status OK
--  2) ✅ ... e i params sono il JSONB che la funzione restituisce (_total)
--
-- ⚠️ IL DIFETTO ERA MUTO. Con status INFO, fuori da chk_audit_status, il
--   23514 lo inghiottiva il WHEN OTHERS best-effort: la funzione restituiva i
--   conteggi e l'audit non c'era. Solo contare le righe lo vede.
-- ⚠️ Le righe seed di automazione_chiusura_scadenze si spengono (il ROLLBACK
--   le riaccende), come in test-fn-apply-chiusura-scadenze-v1: il giro non
--   tocca dati e arriva all'audit.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(2);

UPDATE dbops.automazione_chiusura_scadenze SET attivo = false WHERE attivo;

CREATE TEMP TABLE tmp_prima AS
SELECT coalesce(max(id), 0) AS max_id FROM dbops.audit_log;

CREATE TEMP TABLE tmp_esito AS
SELECT dbops.fn_apply_chiusura_scadenze() AS esito;

SELECT is(
    (SELECT count(*)::integer
       FROM dbops.audit_log a
      WHERE a.id > (SELECT max_id FROM tmp_prima)
        AND a.function_name = 'dbops.fn_apply_chiusura_scadenze'
        AND a.status = 'OK'),
    1,
    'Un giro della chiusura per scadenza scrive una riga di audit OK'
);

SELECT is(
    (SELECT (a.params ->> '_total')::integer
       FROM dbops.audit_log a
      WHERE a.id > (SELECT max_id FROM tmp_prima)
        AND a.function_name = 'dbops.fn_apply_chiusura_scadenze'
      ORDER BY a.id DESC
      LIMIT 1),
    (SELECT (esito ->> '_total')::integer FROM tmp_esito),
    'I params dell''audit sono il riepilogo restituito'
);

SELECT * FROM finish();

ROLLBACK;
