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
-- cancella. E la modalità sessione dell'audit (`fn_audit_begin` → `fn_audit_end`)
-- è un UPDATE del registro: riservata a chi possiede la tabella. L'app scrive
-- con la sola `fn_audit_log_once`.
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

-- La chiusura va anche a PUBLIC, che sulle funzioni ha EXECUTE per default
-- (`=X`): revocare al solo ruolo applicativo non toglierebbe niente.
SELECT format('REVOKE EXECUTE ON FUNCTION %I.%I(%s) FROM PUBLIC, %I',
              n.nspname, p.proname, pg_get_function_identity_arguments(p.oid), :'app_role')
FROM pg_proc p
JOIN pg_namespace n ON n.oid = p.pronamespace
WHERE n.nspname = 'dbops'
  AND p.proname IN ('fn_audit_begin', 'fn_audit_end')
  AND p.prokind = 'f'
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
--   `db/pgtap/config/test-totp-porta-v1.sql`.
SELECT format('REVOKE INSERT, UPDATE, DELETE ON TABLE %s FROM %I', t.nome, :'app_role')
FROM (VALUES ('config.credenziali'), ('config.credenziali_provenienze'),
             ('config.nomi_tentati'), ('config.nomi_tentati_provenienze'),
             ('config.auth_totp_device')) AS t(nome)
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
WHERE n.nspname = 'magazzino'
  AND p.proname IN ('fn_scrivi_movimento', 'fn_ricalcola_valore_giacenza',
                    -- ⭐ Dal 2026-09-28 (Lotto 3): le operazioni interne della bolla e
                    --   lo storno. Forward 90_end/20260928-83.
                    'fn_posta_ddt', 'fn_storna_movimenti_sorgente',
                    -- ⭐ Dal 2026-09-28 (Lotto 3-bis): il posting del reso.
                    --   Forward 90_end/20260928-98.
                    'fn_posta_reso')
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

\echo [ZeroErp] OK: role provisioning completed
