\echo [ZeroErp] Checking runtime role access
\echo [ZeroErp] Optional var: app_role (default: zeroerp_app)

-- Il ruolo applicativo e' di SISTEMA, zeroerp_app (brief-db-ruoli-di-sistema):
-- la variabile resta per guardare un altro ruolo, per esempio un utente
-- personale che ne sia membro.
\if :{?app_role}
\else
\set app_role zeroerp_app
\endif

SELECT :'app_role' AS app_role, current_database() AS db_name;

-- USAGE su tutti gli schemi non di sistema: mostra cosa vede e cosa non vede.
-- Non ha bisogno di una lista hardcoded: copre automaticamente tutti gli schemi
-- presenti nel DB, inclusi quelli aggiunti di recente come ui, documenti, pratiche.
-- ⭐ `django` NON e' escluso, dal 2026-09-13: e' lo schema in testa al
--    search_path del ruolo applicativo e sedici funzioni INVOKER attraversano
--    `django.auth_user`. Escluderlo qui e nel provisioning e' il modo in cui
--    quel privilegio e' rimasto per mesi un GRANT dato a mano su dev
--    (vedi scripts/sql/provision_zeroerp.sql, fase post, la whitelist _app_schemas).
SELECT n.nspname                                                  AS schema_name,
       has_schema_privilege(:'app_role', n.nspname, 'USAGE')     AS can_use_schema
FROM pg_namespace n
WHERE n.nspname NOT LIKE 'pg_%'
  AND n.nspname NOT IN ('information_schema', 'maintenance')
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
      AND n2.nspname NOT IN ('information_schema', 'maintenance')
    ORDER BY n2.nspname, c2.relname
) c
JOIN pg_namespace n ON n.nspname = c.nspname
ORDER BY n.nspname;
