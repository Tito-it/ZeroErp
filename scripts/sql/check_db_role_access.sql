\echo [ZeroErp] Checking runtime role access
\echo [ZeroErp] Required var: app_role

\if :{?app_role}
\else
\echo ERROR: missing -v app_role=...
\quit 1
\endif

SELECT :'app_role' AS app_role, current_database() AS db_name;

SELECT n.nspname AS schema_name,
       has_schema_privilege(:'app_role', n.nspname, 'USAGE') AS can_use_schema
FROM pg_namespace n
WHERE n.nspname IN ('vendite', 'config', 'anagrafiche', 'catalogo')
ORDER BY n.nspname;

SELECT p.proname AS function_name,
       has_function_privilege(
           :'app_role',
           p.oid,
           'EXECUTE'
       ) AS can_execute
FROM pg_proc p
JOIN pg_namespace n ON n.oid = p.pronamespace
WHERE n.nspname = 'vendite'
  AND p.proname IN ('fn_get_or_create_lotto', 'fn_log_pipeline_fase', 'fn_close_giornaliero_lotto')
ORDER BY p.proname;
