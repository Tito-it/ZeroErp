\set ON_ERROR_STOP on

-- ============================================================================
-- ZeroErp — Provisioning ruolo batch PER-JOB: zeroerp_batch_fatturazione
-- ----------------------------------------------------------------------------
-- Canale di sistema headless per il batch di fatturazione sotto RLS.
-- Vedi: docs/it/dev/work-in-progress/brief-db-contesto-sistema-batch-fatturazione-rls.md
--       docs/it/dev/backend/provisioning-db-roles.md
--
-- Modello (Path A, per-job):
--   * BYPASSRLS  -> bypassa l'isolamento per-emittente (semantica corretta per
--                   un processo di sistema che opera su TUTTI gli emittenti);
--                   le invarianti di business (trigger/constraint) restano attive.
--   * SELECT     -> AMPIO, schema-wide (le letture cross-tenant sono basso rischio;
--                   enumerare i lookup della discovery sarebbe fragile).
--   * DML        -> SCOPED al solo perimetro di scrittura del batch (§3 del brief).
--                   Il vettore di danno di un ruolo BYPASSRLS e' la scrittura
--                   cross-tenant: la si limita al perimetro noto. Una tabella nuova
--                   non concessa fallisce RUMOROSAMENTE (permission denied), non in
--                   silenzio. Quando la pipeline scrive una nuova tabella, aggiungere
--                   la riga in _perimeter qui sotto.
--   * NO membership di zeroerp_app (darebbe read+write su TUTTO). Grant espliciti.
--   * Solo processi headless. MAI come DB_USER del web.
--
-- Nuovo job di sistema -> NUOVO script/ruolo scoped (zeroerp_batch_<job>),
-- mai allargare i grant di un ruolo esistente.
-- ============================================================================

\echo [ZeroErp] Provisioning ruolo batch: zeroerp_batch_fatturazione
\echo [ZeroErp] Required vars: batch_role, batch_password
\echo [ZeroErp] Optional vars: migrator_role (default: titodb), db_name (default: current db)

\if :{?batch_role}
\else
\echo ERROR: missing -v batch_role=...
\quit 1
\endif

\if :{?batch_password}
\else
\echo ERROR: missing -v batch_password=...
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

-- ------------------------------------------------------------------
-- Ruolo: create-if-missing, password idempotente, attributi espliciti.
-- BYPASSRLS richiede privilegi di superuser per essere assegnato:
-- lo script va eseguito da un utente amministrativo del DB.
-- ------------------------------------------------------------------
SELECT format('CREATE ROLE %I LOGIN PASSWORD %L', :'batch_role', :'batch_password')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'batch_role')
\gexec

SELECT format('ALTER ROLE %I LOGIN PASSWORD %L', :'batch_role', :'batch_password')
\gexec

SELECT format(
    'ALTER ROLE %I NOSUPERUSER NOCREATEDB NOCREATEROLE INHERIT BYPASSRLS',
    :'batch_role'
)
\gexec

SELECT format('GRANT CONNECT, TEMP ON DATABASE %I TO %I', :'db_name', :'batch_role')
\gexec

SELECT format(
    'ALTER ROLE %I SET search_path = django,public,config,dbops,script,anagrafiche',
    :'batch_role'
)
\gexec

-- ------------------------------------------------------------------
-- Whitelist schemi applicativi (allineata a provision_db_roles.sql).
-- Letture/esecuzioni: ampie su questi schemi.
-- ------------------------------------------------------------------
CREATE TEMP TABLE _app_schemas (nspname TEXT);
INSERT INTO _app_schemas (nspname) VALUES
    ('acquisti'),
    ('anagrafiche'),
    ('catalogo'),
    ('config'),
    ('contabilita'),
    ('dbops'),
    ('documenti'),
    ('magazzino'),
    ('pagamenti'),
    ('pratiche'),
    ('public'),
    ('script'),
    ('storico'),
    ('ui'),
    ('vendite');

DELETE FROM _app_schemas s
WHERE NOT EXISTS (SELECT 1 FROM pg_namespace n WHERE n.nspname = s.nspname);

-- USAGE su schemi
SELECT format('GRANT USAGE ON SCHEMA %I TO %I', s.nspname, :'batch_role')
FROM _app_schemas s
\gexec

-- SELECT AMPIO su tutte le tabelle (read cross-tenant a basso rischio)
SELECT format('GRANT SELECT ON ALL TABLES IN SCHEMA %I TO %I', s.nspname, :'batch_role')
FROM _app_schemas s
\gexec

-- EXECUTE su tutte le funzioni (la pipeline invoca fn_* di vendite/pagamenti/...)
SELECT format('GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA %I TO %I', s.nspname, :'batch_role')
FROM _app_schemas s
\gexec

-- Oggetti FUTURI creati dal migrator: SELECT + EXECUTE (NON DML -> nuove tabelle
-- restano non scrivibili finche' non entrano nel perimetro: fail-loud voluto).
SELECT format(
    'ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA %I GRANT SELECT ON TABLES TO %I',
    :'migrator_role', s.nspname, :'batch_role'
)
FROM _app_schemas s
\gexec

SELECT format(
    'ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA %I GRANT EXECUTE ON FUNCTIONS TO %I',
    :'migrator_role', s.nspname, :'batch_role'
)
FROM _app_schemas s
\gexec

-- ------------------------------------------------------------------
-- Perimetro di SCRITTURA del batch fatturazione (§3 del brief).
-- DML (INSERT/UPDATE/DELETE) concesso SOLO qui. Include le tabelle scritte
-- anche indirettamente dai trigger della pipeline.
-- ------------------------------------------------------------------
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

-- Filtra le tabelle inesistenti (DB parziali / ambienti test)
DELETE FROM _perimeter p
WHERE NOT EXISTS (
    SELECT 1 FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = p.nspname
      AND c.relname = p.relname
      AND c.relkind IN ('r', 'p')
);

-- DML scoped sul perimetro (SELECT gia' coperto dal grant ampio sopra)
SELECT format('GRANT INSERT, UPDATE, DELETE ON TABLE %I.%I TO %I', p.nspname, p.relname, :'batch_role')
FROM _perimeter p
\gexec

-- Sequenze associate alle tabelle del perimetro (serial 'a' / identity 'i'):
-- USAGE+SELECT per consentire nextval/currval in INSERT.
SELECT format('GRANT USAGE, SELECT ON SEQUENCE %I.%I TO %I', seq_ns.nspname, seq.relname, :'batch_role')
FROM _perimeter p
JOIN pg_class t        ON t.relname = p.relname
JOIN pg_namespace tn   ON tn.oid = t.relnamespace AND tn.nspname = p.nspname
JOIN pg_depend d       ON d.refobjid = t.oid AND d.deptype IN ('a', 'i')
JOIN pg_class seq      ON seq.oid = d.objid AND seq.relkind = 'S'
JOIN pg_namespace seq_ns ON seq_ns.oid = seq.relnamespace
\gexec

\echo [ZeroErp] OK: provisioning zeroerp_batch_fatturazione completato
