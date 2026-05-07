\echo [ZeroErp] Checking runtime role access
\echo [ZeroErp] Required var: app_role

\if :{?app_role}
\else
\echo ERROR: missing -v app_role=...
\quit 1
\endif

SELECT :'app_role' AS app_role, current_database() AS db_name;

-- USAGE su tutti gli schemi non di sistema: mostra cosa vede e cosa non vede.
-- Non ha bisogno di una lista hardcoded: copre automaticamente tutti gli schemi
-- presenti nel DB, inclusi quelli aggiunti di recente come ui, documenti, pratiche.
SELECT n.nspname                                                  AS schema_name,
       has_schema_privilege(:'app_role', n.nspname, 'USAGE')     AS can_use_schema
FROM pg_namespace n
WHERE n.nspname NOT LIKE 'pg_%'
  AND n.nspname NOT IN ('information_schema', 'django', 'maintenance')
ORDER BY n.nspname;

-- SELECT su una tabella campione per ogni schema applicativo presente.
-- Verifica che i grant sugli oggetti (non solo sullo schema) siano effettivi.
SELECT n.nspname                                                          AS schema_name,
       c.relname                                                           AS sample_table,
       has_table_privilege(:'app_role', c.oid, 'SELECT')                  AS can_select
FROM (
    -- Una tabella per schema: la prima in ordine alfabetico
    SELECT DISTINCT ON (n2.nspname) n2.nspname, c2.oid, c2.relname
    FROM pg_class c2
    JOIN pg_namespace n2 ON n2.oid = c2.relnamespace
    WHERE c2.relkind = 'r'
      AND n2.nspname NOT LIKE 'pg_%'
      AND n2.nspname NOT IN ('information_schema', 'django', 'maintenance')
    ORDER BY n2.nspname, c2.relname
) c
JOIN pg_namespace n ON n.nspname = c.nspname
ORDER BY n.nspname;
