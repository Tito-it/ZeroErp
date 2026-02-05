\set ON_ERROR_STOP on

\echo [ZeroErp] Provisioning DB roles (runtime + migrator policy)
\echo [ZeroErp] Required vars: app_role, app_password
\echo [ZeroErp] Optional vars: migrator_role (default: titodb), db_name (default: current db)

\if :{?app_role}
\else
\echo ERROR: missing -v app_role=...
\quit 1
\endif

\if :{?app_password}
\else
\echo ERROR: missing -v app_password=...
\quit 1
\endif

\if :{?migrator_role}
\else
\set migrator_role titodb
\endif

\if :{?db_name}
\else
SELECT current_database() AS _db_name \gset
\set db_name :_db_name
\endif

SELECT format('CREATE ROLE %I LOGIN PASSWORD %L', :'app_role', :'app_password')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'app_role')
\gexec

SELECT format('ALTER ROLE %I LOGIN PASSWORD %L', :'app_role', :'app_password')
\gexec

SELECT format('GRANT CONNECT, TEMP ON DATABASE %I TO %I', :'db_name', :'app_role')
\gexec

SELECT format(
    'ALTER ROLE %I SET search_path = django,public,config,dbops,script,anagrafiche',
    :'app_role'
)
\gexec

SELECT format('GRANT USAGE ON SCHEMA %I TO %I', n.nspname, :'app_role')
FROM pg_namespace n
WHERE n.nspname IN (
    'public',
    'script',
    'dbops',
    'config',
    'anagrafiche',
    'catalogo',
    'vendite',
    'acquisti',
    'magazzino',
    'pagamenti',
    'contabilita',
    'storico'
)
\gexec

SELECT format('GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA %I TO %I', n.nspname, :'app_role')
FROM pg_namespace n
WHERE n.nspname IN (
    'public',
    'script',
    'dbops',
    'config',
    'anagrafiche',
    'catalogo',
    'vendite',
    'acquisti',
    'magazzino',
    'pagamenti',
    'contabilita',
    'storico'
)
\gexec

SELECT format('GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA %I TO %I', n.nspname, :'app_role')
FROM pg_namespace n
WHERE n.nspname IN (
    'public',
    'script',
    'dbops',
    'config',
    'anagrafiche',
    'catalogo',
    'vendite',
    'acquisti',
    'magazzino',
    'pagamenti',
    'contabilita',
    'storico'
)
\gexec

SELECT format('GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA %I TO %I', n.nspname, :'app_role')
FROM pg_namespace n
WHERE n.nspname IN (
    'public',
    'script',
    'dbops',
    'config',
    'anagrafiche',
    'catalogo',
    'vendite',
    'acquisti',
    'magazzino',
    'pagamenti',
    'contabilita',
    'storico'
)
\gexec

-- Oggetti futuri creati dal ruolo migrator (CI/deploy).
SELECT format(
    'ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA %I GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO %I',
    :'migrator_role', n.nspname, :'app_role'
)
FROM pg_namespace n
WHERE n.nspname IN (
    'public',
    'script',
    'dbops',
    'config',
    'anagrafiche',
    'catalogo',
    'vendite',
    'acquisti',
    'magazzino',
    'pagamenti',
    'contabilita',
    'storico'
)
\gexec

SELECT format(
    'ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA %I GRANT USAGE, SELECT ON SEQUENCES TO %I',
    :'migrator_role', n.nspname, :'app_role'
)
FROM pg_namespace n
WHERE n.nspname IN (
    'public',
    'script',
    'dbops',
    'config',
    'anagrafiche',
    'catalogo',
    'vendite',
    'acquisti',
    'magazzino',
    'pagamenti',
    'contabilita',
    'storico'
)
\gexec

SELECT format(
    'ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA %I GRANT EXECUTE ON FUNCTIONS TO %I',
    :'migrator_role', n.nspname, :'app_role'
)
FROM pg_namespace n
WHERE n.nspname IN (
    'public',
    'script',
    'dbops',
    'config',
    'anagrafiche',
    'catalogo',
    'vendite',
    'acquisti',
    'magazzino',
    'pagamenti',
    'contabilita',
    'storico'
)
\gexec

\echo [ZeroErp] OK: role provisioning completed
