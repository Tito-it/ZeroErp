\set ON_ERROR_STOP on
-- ============================================================================
-- ZeroErp — Provisioning dei RUOLI DI SISTEMA (modello unico)
-- ----------------------------------------------------------------------------
-- Brief: docs/it/dev/work-in-progress/brief-db-ruoli-di-sistema.md §3, §4
--
-- I nomi dei ruoli sono di SISTEMA e non si configurano: il database li nomina
-- (grant, policy, presidi). Chi installa e vuole un utente suo lo AGGIUNGE come
-- membro di un ruolo di sistema, non lo rinomina.
--
--   zeroerp_owner  proprietario di TUTTI gli oggetti del progetto, tranne le
--                  funzioni che dbops.sec_functions_owner vuole di un
--                  superuser (il canale dblink le rifiuta altrimenti). Lo usano
--                  Liquibase e `manage.py migrate`.
--   zeroerp_job    il demone pgAgent. Non possiede niente: puo' SOLO chiamare
--                  le procedure dei job (maintenance.proc_*_job), che sono
--                  SECURITY DEFINER di zeroerp_owner (20261014-55).
--   zeroerp_app    il backend. La sua postura la da'
--                  scripts/sql/provision_db_roles.sql (con
--                  -v migrator_role=zeroerp_owner).
--
-- ── Le tre fasi (variabile `fase`), da SUPERUSER ─────────────────────────────
--   ruoli  sul database `postgres`: crea i ruoli che mancano e il database
--          `db_name` con owner zeroerp_owner. Prima delle migrazioni.
--   pre    sul database del progetto, DOPO il provision-pre di Liquibase (che
--          gira da superuser e crea le sue tabelle e `internal`): le passa a
--          zeroerp_owner; da' i diritti su `pgagent`.
--   post   sul database del progetto, alla fine (dopo Liquibase, provision-post,
--          ci_apply, `manage.py migrate`): EXECUTE di zeroerp_job sulle
--          procedure dei job, ripassa la proprieta', e VERIFICA che l'owner sia
--          uno solo — se no si ferma, nominando gli oggetti.
--
-- ── ⛔ Le password (D-3) ──────────────────────────────────────────────────────
--   Nessun default. Si passano con -v owner_password=… -v job_password=…
--   -v app_password=…, e servono SOLO per creare un ruolo che manca: se manca il
--   ruolo e manca la sua password, lo script si ferma.
--   ⚠️ Di un ruolo che ESISTE la password non si tocca mai: i ruoli sono di
--   CLUSTER, e lo stesso ruolo puo' servire un altro database (lo sviluppo).
--
-- Esempio (fase ruoli):
--   sudo -u postgres psql -d postgres -v fase=ruoli -v db_name=zeroerp_ruoli \
--        -v owner_password=… -v job_password=… -v app_password=… \
--        < scripts/sql/provision_zeroerp.sql
-- ============================================================================

-- ⛔ Ogni fermo e' un ERRORE VERO, non `\quit 1`: psql ignora il codice di
--   `\quit` («parametro in eccesso ignorato») ed esce con 0, cioe' un controllo
--   fallito risulterebbe riuscito a chi lo lancia da uno script.
\if :{?fase}
\else
DO $$ BEGIN RAISE EXCEPTION 'manca -v fase=ruoli|pre|post'; END $$;
\endif

SELECT :'fase' IN ('ruoli', 'pre', 'post') AS fase_valida \gset
\if :fase_valida
\else
DO $$ BEGIN RAISE EXCEPTION 'fase sconosciuta (attese: ruoli, pre, post)'; END $$;
\endif

SELECT rolsuper AS sono_superuser FROM pg_roles WHERE rolname = current_user \gset
\if :sono_superuser
\else
DO $$ BEGIN RAISE EXCEPTION 'il provisioning dei ruoli di sistema gira da superuser'; END $$;
\endif

-- Le password viaggiano come GUC di questa sessione, non interpolate nei blocchi
-- DO (psql non interpola dentro $$…$$). Vuoto = non passata.
\if :{?owner_password}
SELECT set_config('zeroerp.prov_owner_password', :'owner_password', false) \gset _x_
\endif
\if :{?job_password}
SELECT set_config('zeroerp.prov_job_password', :'job_password', false) \gset _x_
\endif
\if :{?app_password}
SELECT set_config('zeroerp.prov_app_password', :'app_password', false) \gset _x_
\endif

-- ============================================================================
-- FASE ruoli
-- ============================================================================
SELECT :'fase' = 'ruoli' AS fase_ruoli \gset
\if :fase_ruoli

\echo [ZeroErp] fase ruoli: i ruoli di sistema
DO $ruoli$
DECLARE
    r       record;
    v_pwd   text;
BEGIN
    FOR r IN SELECT * FROM (VALUES
        ('zeroerp_owner', 'zeroerp.prov_owner_password',
         'Proprietario degli oggetti di ZeroERP — progetto di Tid (Michele Carlo Titini). Ruolo di sistema: il nome non si cambia; un utente personale ne diventa membro con ALTER ROLE <utente> SET role = zeroerp_owner.'),
        ('zeroerp_job',   'zeroerp.prov_job_password',
         'Il demone pgAgent di ZeroERP. Non possiede niente: chiama soltanto le procedure dei job (maintenance.proc_*_job), che girano come zeroerp_owner. Ruolo di sistema: il nome non si cambia.'),
        ('zeroerp_app',   'zeroerp.prov_app_password',
         'Il backend di ZeroERP: NOBYPASSRLS, non proprietario, la RLS lo filtra. Ruolo di sistema: il nome non si cambia.')
    ) AS t(ruolo, guc, commento)
    LOOP
        IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r.ruolo) THEN
            v_pwd := nullif(current_setting(r.guc, true), '');
            IF v_pwd IS NULL THEN
                RAISE EXCEPTION 'Il ruolo % manca e non e'' stata passata la sua password: nessun default (D-3).', r.ruolo;
            END IF;
            EXECUTE format('CREATE ROLE %I LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS PASSWORD %L',
                           r.ruolo, v_pwd);
            RAISE NOTICE 'creato il ruolo %', r.ruolo;
        END IF;
        -- ⛔ La postura e' parte del modello: un ruolo di sistema che esiste con
        --   attributi diversi non si «corregge» in silenzio, si segnala.
        IF EXISTS (SELECT 1 FROM pg_roles
                    WHERE rolname = r.ruolo
                      AND (rolsuper OR rolbypassrls OR rolcreaterole OR NOT rolcanlogin)) THEN
            RAISE EXCEPTION 'Il ruolo % esiste ma non ha la postura del modello (superuser, bypassrls, createrole o senza login): va guardato a mano.', r.ruolo;
        END IF;
        EXECUTE format('COMMENT ON ROLE %I IS %L', r.ruolo, r.commento);
    END LOOP;
END
$ruoli$;

\if :{?db_name}
SELECT format('CREATE DATABASE %I OWNER zeroerp_owner', :'db_name')
 WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = :'db_name')
\gexec
SELECT format('ALTER DATABASE %I OWNER TO zeroerp_owner', :'db_name')
\gexec
SELECT format('GRANT CONNECT ON DATABASE %I TO zeroerp_job, zeroerp_app', :'db_name')
\gexec
\endif

\endif

-- ============================================================================
-- Il passaggio di proprieta', condiviso da pre e post
-- ============================================================================
-- Si passano a zeroerp_owner gli SCHEMI e le RELAZIONI del progetto che non sono
-- suoi: esclusi gli schemi di sistema, gli oggetti di un'estensione, gli schemi
-- che ospitano un'estensione, lo schema `public` (lo possiede
-- pg_database_owner, cioe' gia' lui). Anche le FUNZIONI, TRANNE quelle che il
-- registro dbops.sec_functions_owner vuole di un superuser (il canale dblink) e
-- la funzione che lo applica: il provision-pre ne crea una da superuser
-- (internal.trgfn_block_project_metadata), trovata il 2026-10-14.
SELECT :'fase' IN ('pre', 'post') AS fase_db \gset
\if :fase_db

\echo [ZeroErp] fase :fase: proprieta a zeroerp_owner
-- ⚠️ Nessun apostrofo nelle righe \echo: per psql apre una stringa che non si
--   chiude («stringa tra virgolette non terminata», corsa del 2026-10-14).
DO $proprieta$
DECLARE
    r          record;
    -- ⛔ Il registro si legge DINAMICO: nella fase pre la tabella non esiste
    --   ancora, e un riferimento statico fallisce gia' quando la query si
    --   pianifica, anche dietro un `to_regclass(…) IS NOT NULL` (corsa del
    --   2026-10-14).
    v_registro text[] := ARRAY[]::text[];
BEGIN
    IF to_regclass('dbops.sec_functions_owner') IS NOT NULL THEN
        EXECUTE 'SELECT coalesce(array_agg(schema_name || ''.'' || function_name), ARRAY[]::text[])
                   FROM dbops.sec_functions_owner'
           INTO v_registro;
    END IF;

    FOR r IN
        SELECT n.nspname
          FROM pg_namespace n
         WHERE n.nspname !~ '^pg_' AND n.nspname NOT IN ('information_schema', 'public')
           AND pg_get_userbyid(n.nspowner) <> 'zeroerp_owner'
           AND NOT EXISTS (SELECT 1 FROM pg_depend d
                            WHERE d.classid = 'pg_namespace'::regclass AND d.objid = n.oid
                              AND d.deptype = 'e')
           -- ⚠️ `pgagent` e `topology` OSPITANO un'estensione senza esserne membri
           --   (pgagent lo crea un changeSet prima dell'estensione): non sono del
           --   progetto, e il loro proprietario non si tocca.
           AND NOT EXISTS (SELECT 1 FROM pg_extension e WHERE e.extnamespace = n.oid)
    LOOP
        EXECUTE format('ALTER SCHEMA %I OWNER TO zeroerp_owner', r.nspname);
    END LOOP;

    FOR r IN
        SELECT c.oid::regclass AS rel, c.relkind
          FROM pg_class c
          JOIN pg_namespace n ON n.oid = c.relnamespace
         WHERE c.relkind IN ('r', 'p', 'v', 'm', 'S', 'f')
           AND n.nspname !~ '^pg_' AND n.nspname <> 'information_schema'
           AND pg_get_userbyid(c.relowner) <> 'zeroerp_owner'
           AND NOT EXISTS (SELECT 1 FROM pg_depend d
                            WHERE d.classid = 'pg_class'::regclass AND d.objid = c.oid
                              AND d.deptype = 'e')
           -- una sequenza posseduta da una colonna segue la sua tabella
           AND NOT (c.relkind = 'S' AND EXISTS (SELECT 1 FROM pg_depend d
                                                  WHERE d.classid = 'pg_class'::regclass
                                                    AND d.objid = c.oid AND d.deptype IN ('a', 'i')))
    LOOP
        EXECUTE format('ALTER %s %s OWNER TO zeroerp_owner',
                       CASE r.relkind WHEN 'S' THEN 'SEQUENCE'
                                      WHEN 'v' THEN 'VIEW'
                                      WHEN 'm' THEN 'MATERIALIZED VIEW'
                                      WHEN 'f' THEN 'FOREIGN TABLE'
                                      ELSE 'TABLE' END,
                       r.rel);
    END LOOP;

    FOR r IN
        SELECT p.oid::regprocedure AS firma, p.prokind
          FROM pg_proc p
          JOIN pg_namespace n ON n.oid = p.pronamespace
         WHERE n.nspname !~ '^pg_' AND n.nspname <> 'information_schema'
           AND pg_get_userbyid(p.proowner) <> 'zeroerp_owner'
           AND NOT EXISTS (SELECT 1 FROM pg_depend d
                            WHERE d.classid = 'pg_proc'::regclass AND d.objid = p.oid
                              AND d.deptype = 'e')
           AND NOT (n.nspname = 'dbops' AND p.proname = 'fn_sync_functions_owner')
           -- Il registro nasce con le migrazioni: nella fase pre e' vuoto.
           AND NOT (n.nspname || '.' || p.proname = ANY (v_registro))
    LOOP
        EXECUTE format('ALTER %s %s OWNER TO zeroerp_owner',
                       CASE r.prokind WHEN 'p' THEN 'PROCEDURE'
                                      WHEN 'a' THEN 'AGGREGATE'
                                      ELSE 'FUNCTION' END,
                       r.firma);
    END LOOP;
END
$proprieta$;

\endif

-- ============================================================================
-- FASE pre
-- ============================================================================
SELECT :'fase' = 'pre' AS fase_pre \gset
\if :fase_pre

\echo [ZeroErp] fase pre: pgagent
-- zeroerp_owner: i changeSet di 85_pgagent creano i job (liquibase-setup-workflow §2).
-- zeroerp_job: il demone legge e scrive le sue tabelle e chiama le sue funzioni.
DO $pgagent$
BEGIN
    IF to_regnamespace('pgagent') IS NULL THEN
        RAISE NOTICE 'pgagent non c''e'' in questo database: niente da dare';
        RETURN;
    END IF;
    GRANT USAGE ON SCHEMA pgagent TO zeroerp_owner, zeroerp_job;
    GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA pgagent TO zeroerp_owner, zeroerp_job;
    GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA pgagent TO zeroerp_owner, zeroerp_job;
    GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA pgagent TO zeroerp_job;
END
$pgagent$;

\endif

-- ============================================================================
-- FASE post
-- ============================================================================
SELECT :'fase' = 'post' AS fase_post \gset
\if :fase_post

\echo [ZeroErp] fase post: zeroerp_job sulle procedure dei job
DO $job$
DECLARE
    r record;
BEGIN
    IF to_regnamespace('maintenance') IS NULL THEN
        RAISE EXCEPTION 'Lo schema maintenance non c''e'': la fase post va dopo le migrazioni.';
    END IF;
    GRANT USAGE ON SCHEMA maintenance TO zeroerp_job;
    FOR r IN
        SELECT p.oid::regprocedure AS firma
          FROM pg_proc p
          JOIN pg_namespace n ON n.oid = p.pronamespace
         WHERE n.nspname = 'maintenance' AND p.prokind = 'p'
           AND p.proname LIKE 'proc\_%\_job'
    LOOP
        EXECUTE format('GRANT EXECUTE ON PROCEDURE %s TO zeroerp_job', r.firma);
    END LOOP;
END
$job$;

\echo [ZeroErp] fase post: verifica «un owner solo»
-- ⛔ Non si corregge: si nomina. Le funzioni di un altro proprietario sono ammesse
--   SOLO se il registro dbops.sec_functions_owner le dichiara (e la funzione che lo
--   applica, dbops.fn_sync_functions_owner).
DO $verifica$
DECLARE
    v_elenco text;
BEGIN
    WITH oggetti AS (
        SELECT 'schema ' || n.nspname AS cosa, n.nspowner AS own, n.oid, 'pg_namespace'::regclass AS cls
          FROM pg_namespace n
         WHERE n.nspname !~ '^pg_' AND n.nspname NOT IN ('information_schema', 'public')
           AND NOT EXISTS (SELECT 1 FROM pg_extension e WHERE e.extnamespace = n.oid)
        UNION ALL
        SELECT 'relazione ' || c.oid::regclass::text, c.relowner, c.oid, 'pg_class'::regclass
          FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
         WHERE c.relkind IN ('r', 'p', 'v', 'm', 'S', 'f')
           AND n.nspname !~ '^pg_' AND n.nspname <> 'information_schema'
        UNION ALL
        SELECT 'funzione ' || p.oid::regprocedure::text, p.proowner, p.oid, 'pg_proc'::regclass
          FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
         WHERE n.nspname !~ '^pg_' AND n.nspname <> 'information_schema'
           AND NOT (n.nspname = 'dbops' AND p.proname = 'fn_sync_functions_owner')
           AND NOT EXISTS (
                 SELECT 1 FROM dbops.sec_functions_owner s
                  WHERE s.schema_name = n.nspname AND s.function_name = p.proname)
    )
    SELECT string_agg(o.cosa || ' (di ' || pg_get_userbyid(o.own) || ')', E'\n  ' ORDER BY o.cosa)
      INTO v_elenco
      FROM oggetti o
     WHERE pg_get_userbyid(o.own) <> 'zeroerp_owner'
       AND NOT EXISTS (SELECT 1 FROM pg_depend d
                        WHERE d.classid = o.cls AND d.objid = o.oid AND d.deptype = 'e');

    IF v_elenco IS NOT NULL THEN
        RAISE EXCEPTION E'Un owner solo: questi oggetti non sono di zeroerp_owner\n  %', v_elenco;
    END IF;
    RAISE NOTICE 'un owner solo: verificato';
END
$verifica$;

\endif

\echo [ZeroErp] provisioning ruoli di sistema: fase :fase completata
