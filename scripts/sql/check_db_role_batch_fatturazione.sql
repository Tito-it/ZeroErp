\set ON_ERROR_STOP on

-- ============================================================================
-- ZeroErp — Verifica postura ruolo batch PER-JOB: zeroerp_batch_fatturazione
-- ----------------------------------------------------------------------------
-- Read-only. Controparte di provision_db_role_batch_fatturazione.sql.
-- Vedi: docs/it/dev/work-in-progress/brief-db-contesto-sistema-batch-fatturazione-rls.md
--
-- Atteso (postura corretta):
--   1. attributi: LOGIN=t, BYPASSRLS=t, SUPERUSER=f, CREATEDB=f, CREATEROLE=f
--   2. membership: 0 righe (NON membro di zeroerp_app)
--   3a. DML fuori perimetro: 0 righe (nessun over-grant)
--   3b. tabelle perimetro (esistenti) senza DML completo: 0 righe (nessun buco)
--   3c. tabelle perimetro non presenti nel DB: solo informativo (DB parziali)
--   4. SELECT ampio su tabella RLS fuori perimetro (vendite.ordini): true
--   5. controprova fail-loud: NO DML su vendite.ordini: false
-- ============================================================================

\if :{?batch_role}
\else
\set batch_role zeroerp_batch_fatturazione
\endif

\echo [ZeroErp] Verifica postura ruolo: :batch_role
SELECT :'batch_role' AS batch_role, current_database() AS db_name;

-- 1) Attributi del ruolo + flag riassuntivo
\echo [1] Attributi ruolo (postura_ok atteso = t)
SELECT rolname,
       rolcanlogin,
       rolsuper,
       rolbypassrls,
       rolcreatedb,
       rolcreaterole,
       (rolcanlogin AND rolbypassrls
        AND NOT rolsuper AND NOT rolcreatedb AND NOT rolcreaterole) AS postura_ok
FROM pg_roles
WHERE rolname = :'batch_role';

-- 2) Membership: deve essere VUOTO (no membership di zeroerp_app o altro)
\echo [2] Membership (atteso: 0 righe)
SELECT r.rolname AS membro_di
FROM pg_auth_members m
JOIN pg_roles r ON r.oid = m.roleid
JOIN pg_roles u ON u.oid = m.member
WHERE u.rolname = :'batch_role';

-- Perimetro di scrittura atteso (allineato a provision_db_role_batch_fatturazione.sql)
CREATE TEMP TABLE _perimeter (nspname TEXT, relname TEXT);
INSERT INTO _perimeter (nspname, relname) VALUES
    ('vendite', 'fatturazione_lotti'),
    ('vendite', 'fatture'),
    ('vendite', 'fatture_righe'),
    ('vendite', 'fatture_fondi_fattura'),
    ('vendite', 'fatture_fondi_fattura_source'),
    ('vendite', 'fatture_riepiloghi_iva'),
    ('vendite', 'attivita_fatturabili'),
    ('vendite', 'registri_fatturazione_progressivi'),
    ('vendite', 'fatturazione_lotti_fatture'),
    ('vendite', 'fatture_log'),
    ('vendite', 'fatturazione_lotti_log'),
    ('vendite', 'note_fatture'),
    ('vendite', 'fatture_sdi'),
    ('vendite', 'fatture_scadenze'),
    ('pagamenti', 'vendite_contabili'),
    ('pagamenti', 'vendite_contabili_righe');

-- 3a) DML concesso FUORI dal perimetro: il caso pericoloso (atteso: 0 righe)
\echo [3a] DML fuori perimetro (atteso: 0 righe)
SELECT g.table_schema, g.table_name,
       string_agg(g.privilege_type, ',' ORDER BY g.privilege_type) AS privs
FROM information_schema.role_table_grants g
WHERE g.grantee = :'batch_role'
  AND g.privilege_type IN ('INSERT', 'UPDATE', 'DELETE')
  AND NOT EXISTS (
      SELECT 1 FROM _perimeter p
      WHERE p.nspname = g.table_schema AND p.relname = g.table_name
  )
GROUP BY g.table_schema, g.table_name
ORDER BY 1, 2;

-- 3b) Tabelle del perimetro ESISTENTI senza DML completo: buchi (atteso: 0 righe)
\echo [3b] Tabelle perimetro senza DML completo (atteso: 0 righe)
SELECT p.nspname, p.relname,
       has_table_privilege(:'batch_role', format('%I.%I', p.nspname, p.relname), 'INSERT') AS ins,
       has_table_privilege(:'batch_role', format('%I.%I', p.nspname, p.relname), 'UPDATE') AS upd,
       has_table_privilege(:'batch_role', format('%I.%I', p.nspname, p.relname), 'DELETE') AS del
FROM _perimeter p
JOIN pg_class c ON c.relname = p.relname AND c.relkind IN ('r', 'p')
JOIN pg_namespace n ON n.oid = c.relnamespace AND n.nspname = p.nspname
WHERE NOT (
       has_table_privilege(:'batch_role', format('%I.%I', p.nspname, p.relname), 'INSERT')
   AND has_table_privilege(:'batch_role', format('%I.%I', p.nspname, p.relname), 'UPDATE')
   AND has_table_privilege(:'batch_role', format('%I.%I', p.nspname, p.relname), 'DELETE')
)
ORDER BY 1, 2;

-- 3c) Tabelle del perimetro NON presenti nel DB: solo informativo (DB parziali)
\echo [3c] Tabelle perimetro non presenti nel DB (informativo)
SELECT p.nspname, p.relname
FROM _perimeter p
WHERE NOT EXISTS (
    SELECT 1 FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = p.nspname AND c.relname = p.relname AND c.relkind IN ('r', 'p')
)
ORDER BY 1, 2;

-- 4) SELECT ampio: su una tabella RLS FUORI perimetro deve essere comunque leggibile
\echo [4] SELECT ampio su vendite.ordini (atteso: t)
SELECT has_table_privilege(:'batch_role', 'vendite.ordini', 'SELECT') AS select_ampio_ok
WHERE EXISTS (
    SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'vendite' AND c.relname = 'ordini'
);

-- 5) Controprova fail-loud: NESSUN DML su una tabella RLS fuori perimetro
\echo [5] DML su vendite.ordini (atteso: f)
SELECT has_table_privilege(:'batch_role', 'vendite.ordini', 'INSERT') AS dml_ordini_deve_essere_false
WHERE EXISTS (
    SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'vendite' AND c.relname = 'ordini'
);

\echo [ZeroErp] OK: check postura completato
