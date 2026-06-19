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
--   3a. DML oltre il grado atteso / fuori perimetro: 0 righe (nessun over-grant)
--   3b. tabelle perimetro (esistenti) senza i privilegi del proprio grado: 0 righe (nessun buco)
--   3c. tabelle perimetro non presenti nel DB: solo informativo (DB parziali)
--   3d. sequenze-codice standalone esistenti senza USAGE: 0 righe (nessun buco)
--   3e. shadow storico.* del perimetro senza INSERT+UPDATE: 0 righe (nessun buco)
--   4. SELECT ampio su tabella RLS fuori perimetro (vendite.ordini): true
--   5. controprova fail-loud: NO DML su vendite.ordini: false
--
-- Perimetro GRADUATO: iud=full DML, iu=INSERT+UPDATE (run-log), i=INSERT only (append-only).
-- Shadow storico.*: INSERT+UPDATE (snapshot SCD via trgfn_storico_generic), no DELETE.
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

-- Perimetro di scrittura atteso (allineato a provision_db_role_batch_fatturazione.sql),
-- GRADUATO per privilege-set: iud=full DML, iu=INSERT+UPDATE, i=INSERT only (append-only).
CREATE TEMP TABLE _perimeter (nspname TEXT, relname TEXT, grade TEXT);
INSERT INTO _perimeter (nspname, relname, grade) VALUES
    ('vendite', 'fatturazione_lotti',               'iud'),
    ('vendite', 'fatture',                          'iud'),
    ('vendite', 'fatture_righe',                    'iud'),
    ('vendite', 'fatture_fondi_fattura',            'iud'),
    ('vendite', 'fatture_fondi_fattura_source',     'iud'),
    ('vendite', 'fatture_riepiloghi_iva',           'iud'),
    ('vendite', 'attivita_fatturabili',             'iud'),
    ('vendite', 'registri_fatturazione_progressivi','iud'),
    ('vendite', 'fatturazione_lotti_fatture',       'iud'),
    ('vendite', 'fatture_log',                      'iud'),
    ('vendite', 'fatturazione_lotti_log',           'iud'),
    ('vendite', 'note_fatture',                     'iud'),
    ('vendite', 'fatture_sdi',                      'iud'),
    ('vendite', 'fatture_scadenze',                 'iud'),
    ('pagamenti', 'vendite_contabili',              'iud'),
    ('pagamenti', 'vendite_contabili_righe',        'iud'),
    ('vendite', 'fatturazione_lotti_task_runs',     'iu'),
    ('vendite', 'fatture_arrotondamenti_scope',     'iu'),
    ('vendite', 'event_log',                        'i'),
    ('vendite', 'attivita_fatturabili_log',         'i'),
    ('pagamenti', 'vendite_contabili_lotti',        'i'),
    ('vendite', 'commesse_attivita',                'u');

-- Espansione grado -> privilegi attesi (single source per 3a/3b)
CREATE TEMP TABLE _perimeter_priv AS
SELECT p.nspname, p.relname, unnest(
    CASE p.grade
        WHEN 'iud' THEN ARRAY['INSERT', 'UPDATE', 'DELETE']
        WHEN 'iu'  THEN ARRAY['INSERT', 'UPDATE']
        WHEN 'i'   THEN ARRAY['INSERT']
        WHEN 'u'   THEN ARRAY['UPDATE']
    END
) AS privilege_type
FROM _perimeter p;

-- Shadow storico.* del perimetro (derivato dai trigger script.trgfn_storico_generic):
-- INSERT+UPDATE attesi (snapshot + chiusura valid_to), NO DELETE. Aggiunti all'allow-set.
INSERT INTO _perimeter_priv (nspname, relname, privilege_type)
SELECT DISTINCT hn.nspname, hc.relname, pv.priv
FROM _perimeter p
JOIN pg_class c        ON c.relname = p.relname
JOIN pg_namespace n    ON n.oid = c.relnamespace AND n.nspname = p.nspname
JOIN pg_trigger tg     ON tg.tgrelid = c.oid AND NOT tg.tgisinternal
JOIN pg_proc pr        ON pr.oid = tg.tgfoid AND pr.proname = 'trgfn_storico_generic'
JOIN pg_namespace pn   ON pn.oid = pr.pronamespace AND pn.nspname = 'script'
JOIN pg_class hc       ON hc.relname = c.relname AND hc.relkind IN ('r', 'p')
JOIN pg_namespace hn   ON hn.oid = hc.relnamespace AND hn.nspname = 'storico'
CROSS JOIN (VALUES ('INSERT'), ('UPDATE')) pv(priv);

-- Sequenze-codice standalone attese (USAGE)
CREATE TEMP TABLE _perimeter_seq (nspname TEXT, relname TEXT);
INSERT INTO _perimeter_seq (nspname, relname) VALUES
    ('vendite', 'fatturazione_lotti_codice_seq');

-- 3a) DML concesso OLTRE il grado atteso: over-grant (atteso: 0 righe).
-- Cattura sia il DML fuori perimetro sia il privilegio sopra-grado (es. DELETE su event_log).
\echo [3a] DML oltre il grado atteso / fuori perimetro (atteso: 0 righe)
SELECT g.table_schema, g.table_name,
       string_agg(g.privilege_type, ',' ORDER BY g.privilege_type) AS privs_extra
FROM information_schema.role_table_grants g
WHERE g.grantee = :'batch_role'
  AND g.privilege_type IN ('INSERT', 'UPDATE', 'DELETE')
  AND NOT EXISTS (
      SELECT 1 FROM _perimeter_priv pp
      WHERE pp.nspname = g.table_schema AND pp.relname = g.table_name
        AND pp.privilege_type = g.privilege_type
  )
GROUP BY g.table_schema, g.table_name
ORDER BY 1, 2;

-- 3b) Tabelle del perimetro ESISTENTI senza il privilegio del proprio grado: buchi (atteso: 0 righe)
\echo [3b] Tabelle perimetro senza i privilegi del grado (atteso: 0 righe)
SELECT pp.nspname, pp.relname, pp.privilege_type AS priv_mancante
FROM _perimeter_priv pp
JOIN pg_class c ON c.relname = pp.relname AND c.relkind IN ('r', 'p')
JOIN pg_namespace n ON n.oid = c.relnamespace AND n.nspname = pp.nspname
WHERE NOT has_table_privilege(:'batch_role', format('%I.%I', pp.nspname, pp.relname), pp.privilege_type)
ORDER BY 1, 2, 3;

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

-- 3d) Sequenze-codice standalone ESISTENTI senza USAGE: buchi (atteso: 0 righe)
\echo [3d] Sequenze-codice senza USAGE (atteso: 0 righe)
SELECT s.nspname, s.relname
FROM _perimeter_seq s
JOIN pg_class c ON c.relname = s.relname AND c.relkind = 'S'
JOIN pg_namespace n ON n.oid = c.relnamespace AND n.nspname = s.nspname
WHERE NOT has_sequence_privilege(:'batch_role', format('%I.%I', s.nspname, s.relname), 'USAGE')
ORDER BY 1, 2;

-- 3e) Shadow storico.* del perimetro senza INSERT+UPDATE: buchi (atteso: 0 righe).
-- Derivato indipendentemente dai trigger trgfn_storico_generic (controprova del 3b).
\echo [3e] Shadow storico senza INSERT+UPDATE (atteso: 0 righe)
SELECT hn.nspname, hc.relname,
       has_table_privilege(:'batch_role', format('%I.%I', hn.nspname, hc.relname), 'INSERT') AS ins,
       has_table_privilege(:'batch_role', format('%I.%I', hn.nspname, hc.relname), 'UPDATE') AS upd
FROM _perimeter p
JOIN pg_class c        ON c.relname = p.relname
JOIN pg_namespace n    ON n.oid = c.relnamespace AND n.nspname = p.nspname
JOIN pg_trigger tg     ON tg.tgrelid = c.oid AND NOT tg.tgisinternal
JOIN pg_proc pr        ON pr.oid = tg.tgfoid AND pr.proname = 'trgfn_storico_generic'
JOIN pg_namespace pn   ON pn.oid = pr.pronamespace AND pn.nspname = 'script'
JOIN pg_class hc       ON hc.relname = c.relname AND hc.relkind IN ('r', 'p')
JOIN pg_namespace hn   ON hn.oid = hc.relnamespace AND hn.nspname = 'storico'
WHERE NOT (
       has_table_privilege(:'batch_role', format('%I.%I', hn.nspname, hc.relname), 'INSERT')
   AND has_table_privilege(:'batch_role', format('%I.%I', hn.nspname, hc.relname), 'UPDATE')
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
