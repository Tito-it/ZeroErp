-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test STRUTTURALE — postura ruolo batch per-job zeroerp_batch_fatturazione
--
-- Canale di sistema headless per il batch di fatturazione sotto RLS (Path A).
-- Vedi: docs/it/dev/work-in-progress/brief-db-contesto-sistema-batch-fatturazione-rls.md
--       scripts/sql/provision_db_role_batch_fatturazione.sql (provisioning)
--       scripts/sql/check_db_role_batch_fatturazione.sql (verifica manuale)
--
-- Verifica la POSTURA (cheap, regression guard), non il comportamento runtime
-- cross-emittente (coperto lato BE):
--   1   : il ruolo esiste
--   2   : LOGIN
--   3   : BYPASSRLS
--   4   : NOT SUPERUSER
--   5   : NOT CREATEDB
--   6   : NOT CREATEROLE
--   7   : nessuna membership (NON membro di zeroerp_app)
--   8   : nessun DML concesso FUORI dal perimetro (over-grant)
--   9   : nessuna tabella del perimetro ESISTENTE priva di DML completo (buchi)
--   10  : SELECT ampio su tabella RLS fuori perimetro (vendite.ordini)
--   11  : controprova fail-loud: NESSUN DML su vendite.ordini
--
-- Prerequisito: il ruolo dev'essere stato provisionato (D1/D3). Asserzioni
-- aggregate -> plan fisso anche su DB parziali. Read-only: BEGIN;/ROLLBACK;.
-- ------------------------------------------------------------

BEGIN;
SELECT plan(11);

-- Perimetro di scrittura atteso (allineato al provisioning)
CREATE TEMP TABLE _perimeter (nspname TEXT, relname TEXT) ON COMMIT DROP;
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

-- 1: esistenza ruolo
SELECT ok(
    EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'zeroerp_batch_fatturazione'),
    'Il ruolo zeroerp_batch_fatturazione esiste'
);

-- 2..6: attributi
SELECT ok(
    (SELECT rolcanlogin FROM pg_roles WHERE rolname = 'zeroerp_batch_fatturazione'),
    'zeroerp_batch_fatturazione: LOGIN'
);
SELECT ok(
    (SELECT rolbypassrls FROM pg_roles WHERE rolname = 'zeroerp_batch_fatturazione'),
    'zeroerp_batch_fatturazione: BYPASSRLS'
);
SELECT ok(
    NOT (SELECT rolsuper FROM pg_roles WHERE rolname = 'zeroerp_batch_fatturazione'),
    'zeroerp_batch_fatturazione: NOT SUPERUSER'
);
SELECT ok(
    NOT (SELECT rolcreatedb FROM pg_roles WHERE rolname = 'zeroerp_batch_fatturazione'),
    'zeroerp_batch_fatturazione: NOT CREATEDB'
);
SELECT ok(
    NOT (SELECT rolcreaterole FROM pg_roles WHERE rolname = 'zeroerp_batch_fatturazione'),
    'zeroerp_batch_fatturazione: NOT CREATEROLE'
);

-- 7: nessuna membership (in particolare NON membro di zeroerp_app)
SELECT is(
    (SELECT count(*)::int
     FROM pg_auth_members m
     JOIN pg_roles u ON u.oid = m.member
     WHERE u.rolname = 'zeroerp_batch_fatturazione'),
    0,
    'zeroerp_batch_fatturazione: nessuna membership (no zeroerp_app)'
);

-- 8: nessun DML FUORI dal perimetro (over-grant)
SELECT is(
    (SELECT count(*)::int
     FROM information_schema.role_table_grants g
     WHERE g.grantee = 'zeroerp_batch_fatturazione'
       AND g.privilege_type IN ('INSERT', 'UPDATE', 'DELETE')
       AND NOT EXISTS (
           SELECT 1 FROM _perimeter p
           WHERE p.nspname = g.table_schema AND p.relname = g.table_name
       )),
    0,
    'zeroerp_batch_fatturazione: nessun DML fuori dal perimetro'
);

-- 9: nessuna tabella del perimetro ESISTENTE priva di DML completo (buchi)
SELECT is(
    (SELECT count(*)::int
     FROM _perimeter p
     JOIN pg_class c ON c.relname = p.relname AND c.relkind IN ('r', 'p')
     JOIN pg_namespace n ON n.oid = c.relnamespace AND n.nspname = p.nspname
     WHERE NOT (
            has_table_privilege('zeroerp_batch_fatturazione', format('%I.%I', p.nspname, p.relname), 'INSERT')
        AND has_table_privilege('zeroerp_batch_fatturazione', format('%I.%I', p.nspname, p.relname), 'UPDATE')
        AND has_table_privilege('zeroerp_batch_fatturazione', format('%I.%I', p.nspname, p.relname), 'DELETE')
     )),
    0,
    'zeroerp_batch_fatturazione: tutte le tabelle del perimetro presenti hanno DML completo'
);

-- 10: SELECT ampio su tabella RLS fuori perimetro (vendite.ordini)
SELECT ok(
    has_table_privilege('zeroerp_batch_fatturazione', 'vendite.ordini', 'SELECT'),
    'zeroerp_batch_fatturazione: SELECT ampio su vendite.ordini (fuori perimetro)'
);

-- 11: controprova fail-loud: NESSUN DML su vendite.ordini
SELECT ok(
    NOT has_table_privilege('zeroerp_batch_fatturazione', 'vendite.ordini', 'INSERT'),
    'zeroerp_batch_fatturazione: NESSUN INSERT su vendite.ordini (fail-loud)'
);

SELECT * FROM finish();
ROLLBACK;
