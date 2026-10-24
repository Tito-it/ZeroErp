\set ON_ERROR_STOP on

\echo [ZeroErp] Provisioning dblink log channel (service + .pgpass, no password in GUC)
\echo [ZeroErp] Optional var: log_service (default: zeroerp_log)

-- ⭐ I nomi dei ruoli sono di SISTEMA (brief-db-ruoli-di-sistema, fase 4,
--   2026-10-15): zeroerp_log, e il parametro del canale per zeroerp_owner,
--   zeroerp_app, zeroerp_job. Prima erano variabili, col migratore di default
--   `titodb`. Resta variabile solo il nome del service, che e' dell'ambiente.
-- ⛔ Il ruolo zeroerp_log NON lo crea questo script: lo crea la fase `ruoli` di
--   provision_zeroerp.sql, prima delle migrazioni. Qui si danno i suoi diritti
--   su dbops.error_log e i parametri del canale, che vogliono lo schema.
--
-- ⛔ Un fermo e' un ERRORE VERO: `\quit 1` esce con 0 (psql ignora il codice),
--   quindi chi lancia lo script da una pipeline lo crederebbe riuscito.
--   Corretto il 2026-10-15 (brief-db-ruoli-di-sistema, fase 4).
\set log_role zeroerp_log
\set migrator_role zeroerp_owner
\set app_role zeroerp_app

\if :{?log_service}
\else
\set log_service zeroerp_log
\endif

\if :{?log_db}
\else
SELECT current_database() AS _log_db \gset
\set log_db :_log_db
\endif

CREATE EXTENSION IF NOT EXISTS dblink;

-- 1) Ruolo tecnico di logging (privilegi minimi)
DO $log$
BEGIN
    -- Il ruolo lo crea la fase `ruoli` di provision_zeroerp.sql, PRIMA delle
    -- migrazioni (90_end/20260905-38 gli da' il giornale dei job solo se c'e').
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'zeroerp_log') THEN
        RAISE EXCEPTION 'Il ruolo zeroerp_log manca: lo crea la fase ruoli di provision_zeroerp.sql (-v log_password=…), prima delle migrazioni.';
    END IF;
END
$log$;

SELECT format('GRANT USAGE ON SCHEMA dbops TO %I', :'log_role')
\gexec

SELECT format('GRANT INSERT ON TABLE dbops.error_log TO %I', :'log_role')
\gexec

SELECT format('GRANT USAGE, SELECT ON SEQUENCE dbops.error_log_id_seq TO %I', :'log_role')
\gexec

-- 2) GUC usa solo il nome service (password in pg_service.conf/.pgpass)
SELECT format(
  'ALTER ROLE %I IN DATABASE %I SET myapp.dblink_log_connection = %L',
  :'migrator_role', :'log_db', 'service=' || :'log_service'
)
WHERE EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'migrator_role')
\gexec

SELECT format(
  'ALTER ROLE %I IN DATABASE %I SET myapp.dblink_log_connection = %L',
  :'app_role', :'log_db', 'service=' || :'log_service'
)
WHERE EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'app_role')
\gexec

-- ⭐ E il demone pgAgent (2026-10-15, brief-db-ruoli-di-sistema D-5). Il verbale di
--   un job FALLITO (maintenance.fn_job_run_log_failure) apre il canale leggendo
--   myapp.dblink_log_connection della SESSIONE, cioe' del ruolo che si e'
--   collegato: zeroerp_job, anche se la procedura del job gira come il
--   proprietario. Senza questa riga un job fallito sotto pgAgent non lascia il
--   verbale (WARNING «nessun canale»). Su un database che la imposta per tutti
--   (ALTER DATABASE … SET) e' gia' coperto; questa la rende esplicita.
SELECT format(
  'ALTER ROLE %I IN DATABASE %I SET myapp.dblink_log_connection = %L',
  'zeroerp_job', :'log_db', 'service=' || :'log_service'
)
WHERE EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'zeroerp_job')
\gexec

\echo [ZeroErp] OK: dblink log channel provisioned
\echo [ZeroErp] NOTE: configurare pg_service.conf e .pgpass per il service indicato.
