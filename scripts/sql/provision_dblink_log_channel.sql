\set ON_ERROR_STOP on

\echo [ZeroErp] Provisioning dblink log channel (service + .pgpass, no password in GUC)
\echo [ZeroErp] Required vars: log_password
\echo [ZeroErp] Optional vars:
\echo [ZeroErp]   log_role (default: zeroerp_log)
\echo [ZeroErp]   log_service (default: zeroerp_log)
\echo [ZeroErp]   migrator_role (default: titodb)
\echo [ZeroErp]   app_role (default: zeroerp_app)

-- ⛔ Un fermo e' un ERRORE VERO: `\quit 1` esce con 0 (psql ignora il codice),
--   quindi chi lancia lo script da una pipeline lo crederebbe riuscito.
--   Corretto il 2026-10-15 (brief-db-ruoli-di-sistema, fase 4).
\if :{?log_password}
\else
\echo ERROR: missing -v log_password=...
\set ON_ERROR_STOP on
DO $$ BEGIN RAISE EXCEPTION 'ERROR: missing -v log_password=...'; END $$;
\endif

\if :{?log_role}
\else
\set log_role zeroerp_log
\endif

\if :{?log_service}
\else
\set log_service zeroerp_log
\endif

\if :{?migrator_role}
\else
\set migrator_role titodb
\endif

\if :{?app_role}
\else
\set app_role zeroerp_app
\endif

\if :{?log_db}
\else
SELECT current_database() AS _log_db \gset
\set log_db :_log_db
\endif

CREATE EXTENSION IF NOT EXISTS dblink;

-- 1) Ruolo tecnico di logging (privilegi minimi)
SELECT format('CREATE ROLE %I LOGIN PASSWORD %L', :'log_role', :'log_password')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'log_role')
\gexec

SELECT format('ALTER ROLE %I LOGIN PASSWORD %L', :'log_role', :'log_password')
\gexec

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
