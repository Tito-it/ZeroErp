-- ------------------------------------------------------------
-- Collaudo del presidio dei job: PULIZIA
-- Brief: brief-db-presidio-job-run-a-chi-tocca §5
--
-- Toglie tutto ciò che ha messo collaudo-presidio-job-run-prepara.sql: le corse
-- COLLAUDO-CAUSA-*, il processo COLLAUDO-CAUSA e il codice
-- E_COLLAUDO_CAUSA_CONFIGURAZIONE. Si può lanciare anche più volte.
--
--   set -a; . db/internal.env; set +a
--   psql -X -f docs/it/dev/work-in-progress/allegati/collaudo-presidio-job-run-pulisci.sql
-- ------------------------------------------------------------

\set ON_ERROR_STOP 1
-- ⚠️ Senza paginatore: con la tabella dentro `less` (END) la sessione aspetta, e
--   uscirne con Ctrl+C annulla la transazione prima del COMMIT.
\pset pager off

BEGIN;

-- Prima le corse: hanno la FK verso il processo.
DELETE FROM maintenance.job_run_log WHERE jobname LIKE 'COLLAUDO-CAUSA-%';
DELETE FROM dbops.processi WHERE codice = 'COLLAUDO-CAUSA';
DELETE FROM config.codici_errore WHERE codice = 'E_COLLAUDO_CAUSA_CONFIGURAZIONE';

SELECT 'righe di collaudo rimaste: ' ||
       ((SELECT count(*) FROM maintenance.job_run_log WHERE jobname LIKE 'COLLAUDO-CAUSA-%')
      + (SELECT count(*) FROM dbops.processi WHERE codice = 'COLLAUDO-CAUSA')
      + (SELECT count(*) FROM config.codici_errore WHERE codice = 'E_COLLAUDO_CAUSA_CONFIGURAZIONE'))
       AS esito;

COMMIT;
