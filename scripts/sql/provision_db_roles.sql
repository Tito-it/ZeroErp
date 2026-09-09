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

-- ------------------------------------------------------------------
-- Sorgente unica della whitelist schemi applicativi.
-- Aggiungere qui i nuovi schemi: tutti i blocchi sottostanti la
-- leggono automaticamente. Solo schemi che zeroerp_app deve usare
-- a runtime. Esclusi intenzionalmente: django (gestito da Django),
-- maintenance (pgAgent: l'app non ne legge né scrive le tabelle).
-- ⚠️ `maintenance` resta fuori di qui, ma riceve il solo `USAGE` in fondo
--    allo script: il perché sta lì, e non è un ripensamento su questa riga.
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

-- Filtra solo gli schemi che esistono nel DB corrente
-- (rende lo script applicabile a DB parziali / ambienti test)
DELETE FROM _app_schemas s
WHERE NOT EXISTS (SELECT 1 FROM pg_namespace n WHERE n.nspname = s.nspname);

SELECT format('GRANT USAGE ON SCHEMA %I TO %I', s.nspname, :'app_role')
FROM _app_schemas s
\gexec

SELECT format('GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA %I TO %I', s.nspname, :'app_role')
FROM _app_schemas s
\gexec

SELECT format('GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA %I TO %I', s.nspname, :'app_role')
FROM _app_schemas s
\gexec

SELECT format('GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA %I TO %I', s.nspname, :'app_role')
FROM _app_schemas s
\gexec

-- Oggetti futuri creati dal ruolo migrator (CI/deploy).
SELECT format(
    'ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA %I GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO %I',
    :'migrator_role', s.nspname, :'app_role'
)
FROM _app_schemas s
\gexec

SELECT format(
    'ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA %I GRANT USAGE, SELECT ON SEQUENCES TO %I',
    :'migrator_role', s.nspname, :'app_role'
)
FROM _app_schemas s
\gexec

SELECT format(
    'ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA %I GRANT EXECUTE ON FUNCTIONS TO %I',
    :'migrator_role', s.nspname, :'app_role'
)
FROM _app_schemas s
\gexec

-- ------------------------------------------------------------------
-- ⭐ ECCEZIONE: `USAGE` — e SOLO `USAGE` — sullo schema `maintenance`.
--
-- `maintenance` resta FUORI dalla whitelist qui sopra, e deve restarci: il
-- ruolo applicativo non legge né scrive le tabelle dei job, quindi non riceve
-- nessun privilegio su tabelle, sequenze o funzioni di quello schema.
-- `USAGE` su uno schema non dà accesso a niente di ciò che contiene: serve a
-- RISOLVERE i nomi, e a nient'altro.
--
-- ⛔ PERCHÉ SERVE, ed è un presidio che senza questa riga mente.
--   `dbops.fn_check_funzioni_riferimenti_morti` gira come ruolo APPLICATIVO —
--   è il solo modo di misurare ciò che l'applicazione vede davvero — e si
--   appoggia a `plpgsql_check`. Sulle funzioni che nominano `maintenance.*`
--   (`script.fn_job_run_start`, `script.fn_job_run_end`,
--   `maintenance.fn_run_and_log`, le `maintenance.proc_*_job`) l'analisi si
--   ferma su «permesso negato per lo schema maintenance» e le classifica come
--   riferimenti morti REALI. Otto funzioni, tutte sane.
--
-- ⚠️ Non è un difetto di esecuzione: quelle funzioni sono `SECURITY DEFINER`,
--   a runtime `maintenance` lo raggiungono comunque. È il PRESIDIO a dare due
--   risposte diverse sulla stessa funzione a seconda della macchina.
--
-- ⭐ COME È SALTATO FUORI, il 2026-09-09: confrontando il database di sviluppo
--   con uno ricostruito da zero. Su dev il grant c'era già
--   (`maintenance` → `zeroerp_app=U/titodb`), dato **a mano**: non lo concede
--   nessun changeSet e non lo concedeva questo script. Esisteva quindi su
--   quella sola macchina, e `db/pgtap/dbops/test-riferimenti-morti-v1.sql` era
--   verde lì e rosso su qualunque installazione nuova — compresa la CI.
--   È esattamente il caso descritto in `docs/it/guide/presidi-e-registri-del-debito.md`
--   §4: verificare solo sul database di sviluppo misura lo stato di UNA
--   macchina, non che le migrazioni sappiano ricostruirla.
--
-- Idempotente e additivo: dove il grant c'è già non cambia nulla.
-- ------------------------------------------------------------------
SELECT format('GRANT USAGE ON SCHEMA maintenance TO %I', :'app_role')
WHERE EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = 'maintenance')
\gexec

\echo [ZeroErp] OK: role provisioning completed
