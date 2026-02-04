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

DO $$
DECLARE
    v_app_role text := :'app_role';
    v_app_password text := :'app_password';
    v_db_name text := :'db_name';
    v_migrator_role text := :'migrator_role';
    v_schema text;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = v_app_role) THEN
        EXECUTE format('CREATE ROLE %I LOGIN PASSWORD %L', v_app_role, v_app_password);
    ELSE
        EXECUTE format('ALTER ROLE %I LOGIN PASSWORD %L', v_app_role, v_app_password);
    END IF;

    EXECUTE format('GRANT CONNECT, TEMP ON DATABASE %I TO %I', v_db_name, v_app_role);
    EXECUTE format(
        'ALTER ROLE %I SET search_path = django,public,config,dbops,script,anagrafiche',
        v_app_role
    );

    FOR v_schema IN
        SELECT nspname
        FROM pg_namespace
        WHERE nspname IN (
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
    LOOP
        EXECUTE format('GRANT USAGE ON SCHEMA %I TO %I', v_schema, v_app_role);
        EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA %I TO %I', v_schema, v_app_role);
        EXECUTE format('GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA %I TO %I', v_schema, v_app_role);
        EXECUTE format('GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA %I TO %I', v_schema, v_app_role);

        -- Oggetti futuri creati dal ruolo migrator (CI/deploy).
        EXECUTE format(
            'ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA %I GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO %I',
            v_migrator_role, v_schema, v_app_role
        );
        EXECUTE format(
            'ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA %I GRANT USAGE, SELECT ON SEQUENCES TO %I',
            v_migrator_role, v_schema, v_app_role
        );
        EXECUTE format(
            'ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA %I GRANT EXECUTE ON FUNCTIONS TO %I',
            v_migrator_role, v_schema, v_app_role
        );
    END LOOP;
END$$;

\echo [ZeroErp] OK: role provisioning completed
