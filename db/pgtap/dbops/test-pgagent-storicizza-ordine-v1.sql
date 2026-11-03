-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- pgtap-runner: owner
-- pgtap-runner-motivo: legge pgagent.pga_job e pgagent.pga_schedule, su cui
--   il ruolo applicativo non ha USAGE (lo schema e' del migratore e del job).
--
-- Test: su pgAgent il sync della storicizzazione suona prima dell'apply
--   pgagent.pga_schedule · dbops.processi.ci_ordine
-- ChangeSet: 20261103-61 · Brief: brief-db-revisione-maintenance D7
--
-- Elenco test (plan 1):
--  1) ⭐ la sveglia di sync_storico_set_storicizza viene prima di quella di
--     apply_storicizza_weekly, nello stesso ordine della convergenza in CI
--     (ci_ordine del sync minore di quello dell'apply)
--
-- ⚠️ Dove pgAgent non e' installato il test va in skip, col motivo: l'ordine
--   della CI lo presidia gia' dbops/test-processi-convergenza-ci.
-- ⚠️ Il confronto e' sulla PRIMA sveglia della settimana di ciascun job
--   (giorno, ora, minuto): i due job hanno una sveglia sola.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(1);

CREATE TEMP TABLE tmp_pga AS
SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pgagent') AS presente;

CREATE TEMP TABLE tmp_sveglia (jobname text, quando integer);

DO $fx$
BEGIN
  IF (SELECT presente FROM tmp_pga) THEN
    EXECUTE $q$
      INSERT INTO tmp_sveglia
      SELECT j.jobname,
             (array_positions(s.jscweekdays, true))[1] * 10000
           + (array_positions(s.jschours,    true))[1] * 100
           + (array_positions(s.jscminutes,  true))[1]
        FROM pgagent.pga_job j
        JOIN pgagent.pga_schedule s ON s.jscjobid = j.jobid
       WHERE j.jobname IN ('sync_storico_set_storicizza', 'apply_storicizza_weekly')
    $q$;
  END IF;
END
$fx$;

SELECT CASE
    WHEN NOT (SELECT presente FROM tmp_pga) THEN
        skip('pgAgent non installato: l''ordine della CI lo presidia test-processi-convergenza-ci', 1)
    ELSE
        ok(
            (SELECT quando FROM tmp_sveglia WHERE jobname = 'sync_storico_set_storicizza')
          < (SELECT quando FROM tmp_sveglia WHERE jobname = 'apply_storicizza_weekly')
            AND (SELECT ci_ordine FROM dbops.processi WHERE codice = 'sync_storico_set_storicizza')
              < (SELECT ci_ordine FROM dbops.processi WHERE codice = 'apply_storicizza_weekly'),
            'Su pgAgent il sync della storicizzazione suona prima dell''apply, come in CI'
        )
END;

SELECT * FROM finish();

ROLLBACK;
