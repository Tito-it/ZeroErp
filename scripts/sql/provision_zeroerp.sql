\set ON_ERROR_STOP on
-- ============================================================================
-- ZeroErp — Provisioning dei RUOLI DI SISTEMA (modello unico)
-- ----------------------------------------------------------------------------
-- Brief: docs/it/dev/work-done/brief-db-ruoli-di-sistema.md §3, §4
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
--   zeroerp_app    il backend. La sua postura la da' la fase post.
--   zeroerp_log    il canale dei registri fuori transazione (dblink). Nasce
--                  qui, PRIMA delle migrazioni: 90_end/20260905-38 gli da' il
--                  giornale dei job solo se il ruolo c'e' gia'. I suoi diritti
--                  su dbops.error_log e i parametri del canale li da'
--                  scripts/sql/provision_dblink_log_channel.sql, dopo.
--
-- ── Le tre fasi (variabile `fase`), da SUPERUSER ─────────────────────────────
--   ruoli  sul database `postgres`: crea i ruoli che mancano e il database
--          `db_name` con owner zeroerp_owner. Prima delle migrazioni.
--   pre    sul database del progetto, DOPO il provision-pre di Liquibase (che
--          gira da superuser e crea le sue tabelle e `internal`): le passa a
--          zeroerp_owner; da' i diritti su `pgagent`.
--   post   sul database del progetto, alla fine (dopo Liquibase, provision-post,
--          ci_apply, `manage.py migrate`): la postura di zeroerp_app, EXECUTE di
--          zeroerp_job sulle procedure dei job, l'AMBIENTE dell'installazione
--          (-v ambiente=SVILUPPO|PRODUZIONE, vedi sotto), ripassa la proprieta',
--          e VERIFICA che l'owner sia uno solo — se no si ferma, nominando gli
--          oggetti.
--
-- ── ⛔ L'ambiente (dal 2026-10-16) ───────────────────────────────────────────
--   Si sceglie all'installazione, come le password: -v ambiente=SVILUPPO oppure
--   -v ambiente=PRODUZIONE alla fase post. Nessun default (decisione di Tid,
--   brief-db-processi-accensione-per-ambiente R-2): la prima volta, se manca, lo
--   script si ferma e chiede di scegliere. Poi e' IMMUTABILE: il parametro
--   diventa facoltativo, ma se c'e' deve coincidere col valore scritto.
--
-- ── ⛔ Le password (D-3) ──────────────────────────────────────────────────────
--   Nessun default. Si passano con -v owner_password=… -v job_password=…
--   -v app_password=… -v log_password=…, e servono SOLO per creare un ruolo che
--   manca: se manca il ruolo e manca la sua password, lo script si ferma.
--   ⚠️ Di un ruolo che ESISTE la password non si tocca mai: i ruoli sono di
--   CLUSTER, e lo stesso ruolo puo' servire un altro database (lo sviluppo).
--
-- Esempio (fase ruoli):
--   sudo -u postgres psql -d postgres -v fase=ruoli -v db_name=zeroerp_ruoli \
--        -v owner_password=… -v job_password=… -v app_password=… \
--        -v log_password=… \
--        < scripts/sql/provision_zeroerp.sql
-- Esempio (fase post, prima volta):
--   sudo -u postgres psql -d zeroerp_ruoli -v fase=post -v ambiente=SVILUPPO \
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
\if :{?log_password}
SELECT set_config('zeroerp.prov_log_password', :'log_password', false) \gset _x_
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
         'Il backend di ZeroERP: NOBYPASSRLS, non proprietario, la RLS lo filtra. Ruolo di sistema: il nome non si cambia.'),
        ('zeroerp_log',   'zeroerp.prov_log_password',
         'Il canale dei registri di ZeroERP: scrive dbops.error_log e il giornale dei job su una connessione separata (dblink), cosi'' il verbale di un errore sopravvive al rollback. Solo INSERT. Ruolo di sistema: il nome non si cambia.')
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

-- ⭐ pg_read_all_stats a zeroerp_owner (D-6, Tid 2026-10-15). pg_stat_activity
--   maschera backend_start/state/query delle sessioni di un ALTRO ruolo, e il
--   ruolo che conta e' chi LEGGE (current_user), non il proprietario della vista.
--   Chi legge come proprietario — il digest (fn_conta_presidio, DEFINER), una
--   psql di un utente personale che lavora come owner — vedrebbe vuoto l'orario
--   delle sessioni di zeroerp_app in dbops.vw_processi_programmazione. Sola
--   lettura delle statistiche; ruolo di cluster, quindi qui e mai in un changeSet.
GRANT pg_read_all_stats TO zeroerp_owner;

\if :{?db_name}
SELECT format('CREATE DATABASE %I OWNER zeroerp_owner', :'db_name')
 WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = :'db_name')
\gexec
SELECT format('ALTER DATABASE %I OWNER TO zeroerp_owner', :'db_name')
\gexec
SELECT format('GRANT CONNECT ON DATABASE %I TO zeroerp_job, zeroerp_app, zeroerp_log', :'db_name')
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

\echo [ZeroErp] fase post: la postura di zeroerp_app
-- ⭐ Era scripts/sql/provision_db_roles.sql, con tre variabili (app_role,
--   app_password, migrator_role con default `titodb`): unificato qui il
--   2026-10-15 (brief-db-ruoli-di-sistema, fase 4). I nomi sono di SISTEMA e
--   non si passano piu'; la password di zeroerp_app serve solo a CREARE il
--   ruolo, ed e' la fase ruoli a farlo: qui il ruolo deve esistere, e la sua
--   password non si tocca mai (i ruoli sono di cluster: D-3).
-- ⚠️ Gira DOPO ENTRAMBI i migratori (Liquibase e `manage.py migrate`): i
--   `GRANT … ON ALL TABLES IN SCHEMA` sono una fotografia, e devono vedere
--   anche le tabelle di `django` e le shadow `storico.*` di `ci_apply`.
\set app_role zeroerp_app
\set migrator_role zeroerp_owner
SELECT current_database() AS db_name \gset
DO $app$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'zeroerp_app') THEN
        RAISE EXCEPTION 'Il ruolo zeroerp_app manca: lo crea la fase ruoli, prima delle migrazioni.';
    END IF;
END
$app$;

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
-- a runtime. Escluso intenzionalmente: maintenance — l'app NON ne scrive
-- le tabelle (la porta è `script.fn_job_run_start/end`, SECURITY DEFINER)
-- e non deve ricevere il SIUD pieno che questa whitelist concede.
-- ⚠️ `maintenance` resta fuori di qui, ma riceve `USAGE` e il SOLO `SELECT`
--    sul giornale dei job in fondo allo script: il perché sta lì, e non è un
--    ripensamento su questa riga. ⛔ Fino al 2026-09-19 questa riga diceva
--    «l'app non ne legge né scrive le tabelle», ed era falsa a metà: cinque
--    lettori BE (`maintenance_repository`, `processi_repository`, la pipeline)
--    fanno SELECT diretta su `maintenance.job_run_log`, e il privilegio
--    esisteva solo su dev, dato a mano. Vedi il blocco in fondo.
--
-- ⭐ `django` STA QUI, dal 2026-09-13 — e fino a quel giorno era escluso con
--    la dicitura «gestito da Django». Django gestisce il DDL di quelle tabelle
--    (`manage.py migrate` le crea), NON i privilegi: nessun changeSet, nessun
--    passo di Django e nessuno script concedeva a `zeroerp_app` un solo
--    privilegio su `django.auth_user`. Eppure il ruolo applicativo ci passa a
--    ogni login (search_path = django,…) e SEDICI funzioni plpgsql SECURITY
--    INVOKER la leggono e la scrivono — `anagrafiche.fn_crea_auth_user`,
--    `script.fn_crea_utente_tecnico`, `fn_sync_auth_user_is_active`…
--    Sul database di sviluppo il privilegio c'era su tutti e 23 gli oggetti,
--    dato A MANO (`zeroerp_app=arwd/titodb`): esisteva su quella sola macchina.
--    Su un database ricostruito da zero — la CI — `manage.py migrate` crea le
--    tabelle e l'app non può nemmeno leggerle: 47 «permission denied for table
--    auth_user» nel log Postgres della corsa 34723456630 (12-09), ogni pgTAP che
--    crea un operatore morto nel fixture, e lo scratch di ci-local.sh non lo
--    vedeva perché COPIAVA le ACL di dev insieme allo schema.
--    È la stessa forma del `GRANT USAGE` su `maintenance` raccontato in fondo.
-- ⚠️ Vale anche l'ALTER DEFAULT PRIVILEGES qui sotto: le tabelle di Django
--    nascono DOPO Liquibase, quindi il `GRANT … ON ALL TABLES` le copre solo
--    se questo script gira dopo ENTRAMBI i migratori (in ci-validate.yaml sta
--    dopo `manage.py migrate` dal 2026-09-13); il default per il migratore
--    copre quelle che una migration Django futura creerà. Il pgTAP che pinna
--    la postura: db/pgtap/dbops/test-app-postura-schema-django-v1.sql.
-- ------------------------------------------------------------------
-- La tabella temporanea c'e' gia' se la fase post gira due volte nella stessa
-- sessione (converti_db_al_modello_ruoli.sql la include).
SELECT 'DROP TABLE pg_temp._app_schemas' WHERE to_regclass('pg_temp._app_schemas') IS NOT NULL
\gexec
CREATE TEMP TABLE _app_schemas (nspname TEXT);
INSERT INTO _app_schemas (nspname) VALUES
    ('acquisti'),
    ('anagrafiche'),
    ('catalogo'),
    ('config'),
    ('contabilita'),
    ('dbops'),
    ('django'),
    ('documenti'),
    ('magazzino'),
    ('pagamenti'),
    ('pratiche'),
    ('public'),
    ('script'),
    -- Dal 2026-11-08 (brief-db-revisione-dbops §22): shop.ricevute ha le policy
    -- dell'app; anche nel loop ci_apply 20260205-41.
    ('shop'),
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
-- ⛔ POSTURA DICHIARATA: i registri APPEND-ONLY (dal 2026-09-11)
--   Brief: brief-db-rls-storico-scope-congelato.md §8.4
--
-- I `GRANT ... ON ALL TABLES / ON ALL FUNCTIONS` qui sopra sono una FOTOGRAFIA
-- larga: danno all'applicazione anche ciò che il modello le NEGA. Due registri
-- — `dbops.audit_log`, `dbops.error_log` — raccontano ciò che l'applicazione fa
-- e sbaglia: il ruolo raccontato li legge e li aggiunge, non li riscrive né li
-- cancella: scrive con la sola `fn_audit_log_once` (la modalità sessione
-- `fn_audit_begin` → `fn_audit_end` è ritirata).
--
-- 🔴 PERCHÉ STA QUI, e non basta che stia nel changeSet e nel loop ci_apply.
--   Questo script è l'ULTIMA parola: in `ci-validate.yaml` e in `ci-local.sh`
--   gira DOPO il migrate e DOPO `--contexts=ci_apply`. Il changeSet
--   `90_end/20260911-09` revoca, il loop `90_end/ci_apply/20260205-41` porta
--   l'eccezione — e poi questo script rifaceva `GRANT UPDATE, DELETE` e
--   `GRANT EXECUTE` su tutto, riaprendo la postura in silenzio. Su dev non si
--   vede: il provisioning non si rilancia dopo ogni migrate. Trovato il
--   2026-09-11 da `db/pgtap/dbops/test-registri-append-only-postura-v1.sql`,
--   verde su dev e rosso sul database ricostruito da zero — che è il presidio
--   che tiene allineate le TRE sedi di questa postura.
--
-- ⚠️ Gli elenchi rispecchiano quelli del loop 20260205-41: chi ne cambia uno
--   cambia anche l'altro, e quel pgTAP lo dice se non lo fa.
-- Idempotente e difensivo: dove l'oggetto non esiste (DB parziale) salta.
-- ------------------------------------------------------------------
SELECT format('REVOKE UPDATE, DELETE ON TABLE %s FROM %I', t.nome, :'app_role')
FROM (VALUES ('dbops.audit_log'), ('dbops.error_log')) AS t(nome)
WHERE to_regclass(t.nome) IS NOT NULL
\gexec

-- ⭐ E lo schema `storico` è SENZA DELETE (brief-db-rls-storico-scope-congelato
--   §4b.2, passo 7): le shadow le scrive il trigger — INSERT della versione,
--   UPDATE che chiude la precedente — e uno snapshot non si cancella mai; la
--   retention è del proprietario. Stessa regola di fn_grant_storico_shadows e
--   dello stesso elenco `v_schemi_senza_delete` nel loop 20260205-41.
SELECT format('REVOKE DELETE ON ALL TABLES IN SCHEMA %I FROM %I', 'storico', :'app_role')
WHERE EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = 'storico')
\gexec

-- ⭐ LA PORTA DEL LEDGER DI MAGAZZINO (dal 2026-09-18): brief
--   brief-db-magazzino-lotto-2-motore, sezione 4.1 (D-L2-b) e 6-ter C2.
--   `magazzino.movimenti` e `magazzino.valore_giacenza` sono in SOLA LETTURA
--   per l'applicazione: scrive solo la primitiva `magazzino.fn_scrivi_movimento`
--   (SECURITY DEFINER del proprietario) e il ricalcolo del valore. È la sola
--   forma in cui «scrive solo la primitiva» è un fatto. `magazzino.movimenti_attesi`
--   resta scrivibile ma SENZA DELETE: un blocco si chiude, non si cancella.
--   Stesso elenco delle liste `v_tabelle_sola_lettura_app` e
--   `v_tabelle_senza_delete` del loop 20260205-41 e del forward 90_end/20260918-15;
--   chi ne cambia uno cambia gli altri, e `db/pgtap/magazzino/test-porta-ledger-v1.sql`
--   lo dice se non lo fa.
SELECT format('REVOKE INSERT, UPDATE, DELETE ON TABLE %s FROM %I', t.nome, :'app_role')
FROM (VALUES ('magazzino.movimenti'), ('magazzino.valore_giacenza')) AS t(nome)
WHERE to_regclass(t.nome) IS NOT NULL
\gexec

-- ⭐ Dal 2026-09-28 (Lotto 3, D-L3-j) `magazzino.movimenti_attesi` e' in SOLA
--   LETTURA: i blocchi li aprono e li liberano i verbi fn_apri_blocco /
--   fn_libera_blocco. Fino a quel giorno era senza DELETE soltanto. Stesso
--   elenco di `v_tabelle_sola_lettura_app` nel loop 20260205-41 e del forward
--   90_end/20260928-83; `db/pgtap/magazzino/test-blocco-manuale-e-porta-lotto3-v1.sql`
--   lo dice se non lo fa.
SELECT format('REVOKE INSERT, UPDATE, DELETE ON TABLE %s FROM %I', t.nome, :'app_role')
FROM (VALUES ('magazzino.movimenti_attesi')) AS t(nome)
WHERE to_regclass(t.nome) IS NOT NULL
\gexec

-- ⭐ LA PORTA DELLO STATO DELLA CREDENZIALE (dal 2026-09-25): brief
--   brief-db-blocco-login-per-credenziale, sezione 2.2. `config.credenziali` e
--   `config.credenziali_provenienze` sono in SOLA LETTURA per l'applicazione:
--   tentativi, freni, blocco dell'admin e cambio password obbligatorio li
--   scrivono solo le funzioni DEFINER del proprietario. Stesso elenco di
--   `v_tabelle_sola_lettura_app` nel loop 20260205-41 e del forward
--   90_end/20260925-24; `db/pgtap/config/test-credenziali-porta-v1.sql` lo dice
--   se non lo fa. Dal 2026-09-25 anche le gemelle del NOME TENTATO (R-7):
--   `config.nomi_tentati` e `config.nomi_tentati_provenienze`, forward
--   90_end/20260925-62. Dal 2026-09-29 anche il DEVICE DEL SECONDO FATTORE,
--   `config.auth_totp_device` (brief-db-secondo-fattore-totp §3): lo scrivono
--   solo i verbi script.fn_totp_*; forward 90_end/20260929-24, pgTAP
--   `db/pgtap/config/test-totp-porta-v1.sql`. Dal 2026-10-06 anche la TRACCIA
--   DELLE CREDENZIALI ELIMINATE, `config.credenziali_eliminate`
--   (brief-db-elimina-credenziale-senza-veste §4.2): la scrive solo
--   script.fn_elimina_credenziale; forward 90_end/20261006-15, pgTAP
--   `db/pgtap/config/test-elimina-credenziale-v1.sql`.
SELECT format('REVOKE INSERT, UPDATE, DELETE ON TABLE %s FROM %I', t.nome, :'app_role')
FROM (VALUES ('config.credenziali'), ('config.credenziali_provenienze'),
             ('config.nomi_tentati'), ('config.nomi_tentati_provenienze'),
             ('config.auth_totp_device'), ('config.credenziali_eliminate')) AS t(nome)
WHERE to_regclass(t.nome) IS NOT NULL
\gexec

-- ⭐ UNA CREDENZIALE SI ELIMINA SOLO DAL VERBO (dal 2026-10-06): brief
--   brief-db-elimina-credenziale-senza-veste §4.2. Su `django.auth_user`
--   l'applicazione perde il DELETE che la whitelist di `django` le concede qui
--   sopra: la sola porta e' script.fn_elimina_credenziale (SECURITY DEFINER),
--   che chiede SUPER_ADMIN, controlla vesti e storia e lascia la traccia.
--   Nessuna funzione e nessun punto del backend cancellava auth_user.
--   ⚠️ QUI e' la sede che conta: `django` non e' fra gli schemi del loop
--   20260205-41, e in CI il forward 90_end/20261006-15 gira prima di
--   manage.py migrate, quando la tabella non c'e' ancora (§11.9).
--   `db/pgtap/config/test-elimina-credenziale-v1.sql` lo dice se non lo fa.
SELECT format('REVOKE DELETE ON TABLE %s FROM %I', t.nome, :'app_role')
FROM (VALUES ('django.auth_user')) AS t(nome)
WHERE to_regclass(t.nome) IS NOT NULL
\gexec

-- ⭐ LA PORTA DEI DATI SOCIETARI (dal 2026-10-11): brief
--   brief-db-dati-fiscali-e-societari-del-soggetto, B-5.
--   `anagrafiche.dati_societari` e' in SOLA LETTURA per l'applicazione: la
--   scrive solo il verbo anagrafiche.fn_scrivi_dati_societari (SECURITY
--   DEFINER del proprietario). Il permesso resta al backend, come per
--   anagrafiche.soggetti. Stesso elenco di `v_tabelle_sola_lettura_app` nel loop
--   20260205-41 e del forward 90_end/20261011-04;
--   `db/pgtap/anagrafiche/test-fn-scrivi-dati-societari-v1.sql` lo dice se non lo fa.
SELECT format('REVOKE INSERT, UPDATE, DELETE ON TABLE %s FROM %I', t.nome, :'app_role')
FROM (VALUES ('anagrafiche.dati_societari')) AS t(nome)
WHERE to_regclass(t.nome) IS NOT NULL
\gexec

-- ⭐ L'AMBIENTE DELL'INSTALLAZIONE (dal 2026-10-16): brief
--   brief-db-processi-accensione-per-ambiente, R-3. `dbops.installazione` e' in
--   SOLA LETTURA per l'applicazione: lo scrive solo questa fase, una volta
--   (blocco «L'ambiente» piu' sotto). Se l'app lo potesse cambiare, il
--   provisioning di sviluppo si accenderebbe in produzione con un giro di
--   UPDATE. Stesso elenco di `v_tabelle_sola_lettura_app` nel loop 20260205-41
--   e del forward 90_end/20261016-32;
--   `db/pgtap/dbops/test-installazione-ambiente-v1.sql` lo dice se non lo fa.
SELECT format('REVOKE INSERT, UPDATE, DELETE ON TABLE %s FROM %I', t.nome, :'app_role')
FROM (VALUES ('dbops.installazione')) AS t(nome)
WHERE to_regclass(t.nome) IS NOT NULL
\gexec

-- ⭐ LE ETICHETTE DI PROVA (dal 2026-10-18): brief
--   brief-db-processi-accensione-per-ambiente, R-4. `dbops.credenziali_di_prova`
--   e `dbops.soggetti_di_prova` sono in SOLA LETTURA per l'applicazione: le
--   scrive solo il verbo dei dati di sviluppo (DEFINER). Stesso elenco di
--   `v_tabelle_sola_lettura_app` nel loop 20260205-41 e del forward
--   90_end/20261018-61; `db/pgtap/dbops/test-etichette-di-prova-v1.sql` lo dice
--   se non lo fa.
SELECT format('REVOKE INSERT, UPDATE, DELETE ON TABLE %s FROM %I', t.nome, :'app_role')
FROM (VALUES ('dbops.credenziali_di_prova'), ('dbops.soggetti_di_prova')) AS t(nome)
WHERE to_regclass(t.nome) IS NOT NULL
\gexec

-- ⭐ LA PORTA DEL PANNELLO DI CONFIGURAZIONE (dal 2026-09-25): brief
--   brief-db-pannello-config-verbo-generico, sezione 3.5. `magazzino.causali` la
--   scrive solo il verbo config.fn_pannello_scrivi; `config.tabelle_gestibili` e'
--   la lista del verbo, e la scrive solo il seed. Stesso elenco di
--   `v_tabelle_sola_lettura_app` nel loop 20260205-41 e del forward
--   90_end/20260925-34; `db/pgtap/config/test-pannello-porta-v1.sql` lo dice se
--   non lo fa. Dal 2026-09-28 anche `config.aree_funzionali` (D-P9, §4.2): la
--   possiede il CSV, nome e ordine si cambiano li'. Forward 90_end/20260928-30.
--   Dal 2026-09-30 anche `ui.misure_pagina` (brief-db-misure-pagina-catalogo §2):
--   le misure «righe per pagina», possedute dal CSV. Forward 90_end/20260930-13,
--   pgTAP `db/pgtap/ui/test-misure-pagina-v1.sql`.
SELECT format('REVOKE INSERT, UPDATE, DELETE ON TABLE %s FROM %I', t.nome, :'app_role')
FROM (VALUES ('magazzino.causali'), ('config.tabelle_gestibili'),
             ('config.aree_funzionali'), ('ui.misure_pagina')) AS t(nome)
WHERE to_regclass(t.nome) IS NOT NULL
\gexec

-- ⭐ IL REGISTRO DEGLI OWNER (dal 2026-09-26): brief
--   brief-db-registro-owner-e-sync-riservati-al-migratore, sezione 2.2.
--   `dbops.sec_functions_owner` dichiara chi possiede le DEFINER di postgres, e
--   la sync la applica: chi scrive il registro sceglie il proprietario. Lo scrive
--   solo il migratore; l'app legge. La sync NON si revoca qui (D-3): e' di
--   postgres, la difende la guardia nel suo corpo (20_code/dbops/20260926-11), e
--   il `GRANT ... ON ALL FUNCTIONS` sopra resta innocuo. Stesso elenco di
--   `v_tabelle_sola_lettura_app` nel loop 20260205-41 e del forward
--   90_end/20260926-12; `db/pgtap/dbops/test-sec-functions-owner-riservato-v1.sql`
--   lo dice se non lo fa.
SELECT format('REVOKE INSERT, UPDATE, DELETE ON TABLE %s FROM %I', t.nome, :'app_role')
FROM (VALUES ('dbops.sec_functions_owner')) AS t(nome)
WHERE to_regclass(t.nome) IS NOT NULL
\gexec

-- ⭐ E LA PORTA SULLE FUNZIONI (dal 2026-09-24): brief
--   brief-db-magazzino-verbi-con-permesso, sezione 2.3 (P-4). La primitiva e il
--   ricalcolo del valore sono RISERVATE: l'app li raggiunge solo dai verbi
--   (`fn_posta_inventario`, `fn_posta_rettifica`, SECURITY DEFINER), che
--   applicano registra_magazzino. La revoca va anche a PUBLIC (`=X` per default).
--   Stesso elenco di `v_fn_riservate` nel loop 20260205-41 e del forward
--   90_end/20260924-42; `db/pgtap/magazzino/test-porta-ledger-v1.sql` (17-18) lo
--   dice se non lo fa.
SELECT format('REVOKE EXECUTE ON FUNCTION %I.%I(%s) FROM PUBLIC, %I',
              n.nspname, p.proname, pg_get_function_identity_arguments(p.oid), :'app_role')
FROM pg_proc p
JOIN pg_namespace n ON n.oid = p.pronamespace
WHERE (n.nspname, p.proname) IN (
        ('magazzino', 'fn_scrivi_movimento'), ('magazzino', 'fn_ricalcola_valore_giacenza'),
        -- ⭐ Dal 2026-09-28 (Lotto 3): lo storno. Forward 90_end/20260928-83.
        ('magazzino', 'fn_storna_movimenti_sorgente'),
        -- ⭐ Dal 2026-10-01 i posting della bolla e del reso stanno in vendite
        --   (erano magazzino.fn_posta_ddt / fn_posta_reso dal 28-09): il registro
        --   non legge le tabelle dei documenti. Forward 90_end/20261001-24; brief
        --   brief-db-magazzino-registro-anello-interno (P-5).
        ('vendite', 'fn_posta_ddt'), ('vendite', 'fn_posta_reso'),
        -- ⭐ Dal 2026-11-08 la copia di un'edizione di workflow: ci si arriva solo da
        --   fn_fork_definizione e fn_nuova_versione_definizione (DEFINER). Forward
        --   90_end/20261110-14; presidio pratiche/test-copia-definizione-riservata-v1.
        ('pratiche', 'fn_copia_definizione'))
  AND p.prokind = 'f'
\gexec

-- ------------------------------------------------------------------
-- ⭐ ECCEZIONE: `maintenance` — `USAGE` sullo schema e il SOLO `SELECT` sul
--    giornale dei job. Niente altro.
--
-- `maintenance` resta FUORI dalla whitelist qui sopra, e deve restarci: la
-- whitelist concede SIUD su ogni tabella, e il giornale dei job NON si scrive
-- dall'applicazione. La postura dell'app su questo schema è in DUE righe:
--
--   * `USAGE` sullo schema — serve a RISOLVERE i nomi, e a nient'altro (il
--     perché sta sotto: il presidio dei riferimenti morti);
--   * `SELECT` su `maintenance.job_run_log` e sulla vista di presidio
--     `maintenance.vw_job_run_da_guardare` — l'app LEGGE il giornale: lista
--     dei processi automatici e corse di un processo (`processi_repository`),
--     riepilogo giri e liveness (`maintenance_repository`), esiti delle corsie
--     di fatturazione (`pipeline_service`), `job_liveness` nel digest dei
--     presidi. Cinque lettori, nessuno scrittore: la scrittura passa da
--     `script.fn_job_run_start/end` (SECURITY DEFINER) per l'app e dal ruolo
--     `zeroerp_log` (INSERT, changeSet `20260905-38`) per il canale fuori
--     transazione. Nessuna sequenza, nessuna funzione di `maintenance`.
--
-- ⛔ PERCHÉ IL `SELECT` STA QUI, ed è la QUARTA volta che la stessa regola si
--   scrive (linee-guida-sql §11.6 e §11.9, il `USAGE` qui sotto): fino al 2026-09-19 il
--   privilegio esisteva su dev (`job_run_log` → `zeroerp_app=r/titodb`), dato
--   A MANO, e da nessun'altra parte. Nessuno se n'è accorto per tre motivi che
--   si sommavano: i pgTAP che leggono il giornale come app erano in
--   `baseline-rossi-ci.tsv` come ERRORE_FIXTURE con la causa mai letta
--   (`maintenance/test-job-run-registrazione.sql`), i test Django in CI si
--   connettevano come OWNER (che possiede la tabella), e lo scratch riceve i
--   privilegi da questo script — che il `SELECT` non lo dava. Il 19-09 i test
--   Django in CI sono passati a `zeroerp_app` (ci-validate.yaml, per esercitare
--   la RLS) e SEDICI test sono morti su «permission denied for table
--   job_run_log», tutti sotto `list_processi`/`list_job_runs`. I test rossi
--   sono il presidio che ha funzionato, non il difetto.
--   Un privilegio che esiste su una sola macchina è un ricordo, non una
--   configurazione. Il pgTAP che pinna questa postura:
--   db/pgtap/maintenance/test-app-postura-job-run-log-v1.sql. Il changeSet
--   gemello per i database già provisionati: `90_end/20260919-08`.
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

-- Il giornale dei job e la sua vista di presidio: SOLA LETTURA. Additivo; su
-- una macchina dove il grant c'è già non cambia nulla. `to_regclass` perché
-- lo script deve poter girare anche prima che la vista esista.
SELECT format('GRANT SELECT ON TABLE %s TO %I', t.nome, :'app_role')
FROM (VALUES ('maintenance.job_run_log'),
             ('maintenance.vw_job_run_da_guardare')) AS t(nome)
WHERE to_regclass(t.nome) IS NOT NULL
\gexec

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

\echo [ZeroErp] fase post: l'ambiente dell'installazione
-- ⛔ Si sceglie qui, una volta: -v ambiente=SVILUPPO|PRODUZIONE. Nessun default
--   (brief-db-processi-accensione-per-ambiente, R-2): un valore scritto da solo
--   dichiarerebbe un database al posto di chi lo conosce — dbdev, nato prima di
--   questa regola, sarebbe diventato PRODUZIONE per sempre. Poi e' immutabile:
--   il parametro diventa facoltativo, e se c'e' deve coincidere.
-- ⚠️ La riga la scrive zeroerp_owner (SET ROLE), proprietario della tabella:
--   l'audit dice chi l'ha scritta, e non e' un superuser.
SELECT set_config('zeroerp.prov_ambiente', '', false) \gset _x_
\if :{?ambiente}
SELECT set_config('zeroerp.prov_ambiente', :'ambiente', false) \gset _x_
\endif
SET ROLE zeroerp_owner;
DO $ambiente$
DECLARE
    v_chiesto  text := NULLIF(btrim(current_setting('zeroerp.prov_ambiente', true)), '');
    v_scritto  text;
BEGIN
    IF to_regclass('dbops.installazione') IS NULL THEN
        RAISE EXCEPTION 'dbops.installazione non c''e'': la fase post va dopo le migrazioni.';
    END IF;

    IF v_chiesto IS NOT NULL AND v_chiesto NOT IN ('SVILUPPO', 'PRODUZIONE') THEN
        RAISE EXCEPTION 'ambiente «%» non valido: -v ambiente=SVILUPPO oppure -v ambiente=PRODUZIONE.', v_chiesto;
    END IF;

    SELECT i.ambiente INTO v_scritto FROM dbops.installazione i WHERE i.id = 1;

    IF v_scritto IS NULL THEN
        IF v_chiesto IS NULL THEN
            RAISE EXCEPTION 'L''ambiente di questa installazione non e'' dichiarato: rilancia la fase post con -v ambiente=SVILUPPO oppure -v ambiente=PRODUZIONE. Si sceglie una volta e non si cambia piu''.';
        END IF;
        INSERT INTO dbops.installazione (ambiente) VALUES (v_chiesto);
        RAISE NOTICE 'ambiente dichiarato: %', v_chiesto;
    ELSIF v_chiesto IS NOT NULL AND v_chiesto <> v_scritto THEN
        RAISE EXCEPTION 'L''ambiente di questa installazione e'' % e non si cambia (chiesto: %).',
                        v_scritto, v_chiesto;
    ELSE
        RAISE NOTICE 'ambiente: % (gia'' dichiarato)', v_scritto;
    END IF;
END
$ambiente$;
RESET ROLE;

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
