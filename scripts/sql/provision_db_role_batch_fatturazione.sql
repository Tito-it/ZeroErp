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
\echo [ZeroErp] Required vars: batch_role; batch_password (obbligatoria solo se il ruolo NON esiste)
\echo [ZeroErp] Optional vars: migrator_role (default: titodb), db_name (default: current db)

\if :{?batch_role}
\else
\echo ERROR: missing -v batch_role=...
\quit 1
\endif

-- ⭐ La password e' OBBLIGATORIA solo per CREARE il ruolo. Se il ruolo esiste
--   gia' e la password non viene passata, resta quella che ha (dal 2026-09-14).
--   Perche': i ruoli sono di CLUSTER, i privilegi di DATABASE. Sul server di
--   sviluppo il ruolo serve al worker con la SUA password; per dare a un
--   database nuovo dello stesso cluster (lo scratch di scripts/ci-local.sh)
--   la stessa postura della CI, i GRANT servono e la password no — e una
--   password inventata romperebbe il worker. Fino a oggi lo scratch per questo
--   saltava il provisioning e dava al batch il DML su tutto: la postura non era
--   misurabile la'. In CI non cambia niente: passa `batch_password=secret`.
\if :{?batch_password}
\else
SELECT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'batch_role') AS _ruolo_esiste \gset
\if :_ruolo_esiste
\echo [ZeroErp] batch_password non data: il ruolo esiste, la password NON si tocca
\else
\echo ERROR: missing -v batch_password=... (il ruolo non esiste: per crearlo la password serve)
\quit 1
\endif
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
\if :{?batch_password}
SELECT format('CREATE ROLE %I LOGIN PASSWORD %L', :'batch_role', :'batch_password')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'batch_role')
\gexec

SELECT format('ALTER ROLE %I LOGIN PASSWORD %L', :'batch_role', :'batch_password')
\gexec
\else
-- Senza password: il ruolo esiste (verificato sopra), si ribadisce solo LOGIN.
SELECT format('ALTER ROLE %I LOGIN', :'batch_role')
\gexec
\endif

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
-- DML concesso SOLO qui, con privilege-set GRADUATO per tabella:
--   * iud -> full DML (INSERT/UPDATE/DELETE): tabelle dominio fattura/lotto.
--   * iu  -> INSERT+UPDATE: run-log (start->complete) e upsert ON CONFLICT DO UPDATE.
--   * i   -> INSERT only: append-only (audit/log) o upsert ON CONFLICT DO NOTHING.
--   * u   -> UPDATE only: tabelle che il batch SOLO aggiorna (es. stato_emissione),
--            senza inserirle/cancellarle (l'INSERT e' del flusso operatore/push).
--   * d   -> DELETE only: tabelle che il batch SOLO ripulisce (rollback/cleanup),
--            senza mai crearne le righe.
-- Tutte le tabelle scritte anche INDIRETTAMENTE dai trigger/upsert della pipeline.
-- Una tabella nuova non concessa fallisce RUMOROSAMENTE (permission denied):
-- quando la pipeline scrive una nuova tabella, aggiungere la riga nel grado giusto.
-- ------------------------------------------------------------------
CREATE TEMP TABLE _perimeter (nspname TEXT, relname TEXT, grade TEXT);
INSERT INTO _perimeter (nspname, relname, grade) VALUES
    -- full DML (INSERT/UPDATE/DELETE)
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
    -- INSERT+UPDATE: run-log task (start->complete) + upsert ON CONFLICT DO UPDATE
    ('vendite', 'fatturazione_lotti_task_runs',     'iu'),
    ('vendite', 'fatture_arrotondamenti_scope',     'iu'),
    -- snapshot indirizzi fattura (task DRAFT): upsert ON CONFLICT (fattura_id,
    -- tipo_indirizzo_id) DO UPDATE, mai DELETE — la pulizia arriva dalla CASCADE
    -- sulla testata, che non richiede il privilegio sul figlio.
    ('vendite', 'fatture_indirizzi',                'iu'),
    -- INSERT only: append-only (audit/log) o upsert ON CONFLICT DO NOTHING
    ('vendite', 'event_log',                        'i'),
    ('vendite', 'attivita_fatturabili_log',         'i'),
    ('pagamenti', 'vendite_contabili_lotti',        'i'),
    -- render documentale (C-2b, documenti.DocumentGenerationService, contesto
    -- sistema): il worker fa solo INSERT append (no UPDATE/DELETE). Le identity
    -- sequence si auto-concedono via il join pg_depend piu' sotto.
    ('documenti', 'documenti_generati',             'i'),
    ('documenti', 'documenti_generati_file',        'i'),
    ('documenti', 'documenti_generati_eventi',      'i'),
    -- DELETE only: il cleanup del rollback automatico (fn_cleanup_fatture_by_ids)
    -- cancella le note della fattura. Il batch non le crea mai: l'INSERT e' del
    -- flusso operatore. Il perimetro conteneva 'note_fatture', tabella del
    -- modello precedente all'unificazione delle note (0 righe, nessuna funzione
    -- la scrive): il grant era rimasto sulla tabella vecchia.
    ('vendite', 'note',                             'd'),
    -- UPDATE only: il batch aggiorna stato_emissione, non inserisce/cancella
    ('vendite', 'commesse_attivita',                'u'),
    -- coda stampa (C-2b): il drainer fa SOLO claim/marca/reaper (UPDATE).
    -- l'accodamento (fn_accoda_stampe_lotto) e' flusso operatore/app, non batch.
    ('vendite', 'fatture_stampa_coda',              'u');

-- Filtra le tabelle inesistenti (DB parziali / ambienti test)
DELETE FROM _perimeter p
WHERE NOT EXISTS (
    SELECT 1 FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = p.nspname
      AND c.relname = p.relname
      AND c.relkind IN ('r', 'p')
);

-- DML scoped sul perimetro, secondo il grado (SELECT gia' coperto sopra)
SELECT format('GRANT INSERT, UPDATE, DELETE ON TABLE %I.%I TO %I', p.nspname, p.relname, :'batch_role')
FROM _perimeter p WHERE p.grade = 'iud'
\gexec

SELECT format('GRANT INSERT, UPDATE ON TABLE %I.%I TO %I', p.nspname, p.relname, :'batch_role')
FROM _perimeter p WHERE p.grade = 'iu'
\gexec

SELECT format('GRANT INSERT ON TABLE %I.%I TO %I', p.nspname, p.relname, :'batch_role')
FROM _perimeter p WHERE p.grade = 'i'
\gexec

SELECT format('GRANT UPDATE ON TABLE %I.%I TO %I', p.nspname, p.relname, :'batch_role')
FROM _perimeter p WHERE p.grade = 'u'
\gexec

SELECT format('GRANT DELETE ON TABLE %I.%I TO %I', p.nspname, p.relname, :'batch_role')
FROM _perimeter p WHERE p.grade = 'd'
\gexec

-- ------------------------------------------------------------------
-- Shadow storico.* del perimetro. I trigger di storicizzazione
-- (script.trgfn_storico_generic, SECURITY INVOKER -> girano come ruolo batch)
-- scrivono in storico.<tabella> all'UPDATE delle tabelle del perimetro:
--   * INSERT del nuovo snapshot + UPDATE di chiusura (valid_to) del precedente
--     -> servono INSERT+UPDATE. NO DELETE (gli snapshot non si cancellano).
-- Derivato dai TRIGGER (non da liste): ogni tabella del perimetro che e'
-- storicizzata aggancia automaticamente la sua shadow -> niente sync manuale.
-- ------------------------------------------------------------------
CREATE TEMP TABLE _perimeter_hist (nspname TEXT, relname TEXT);
INSERT INTO _perimeter_hist (nspname, relname)
SELECT DISTINCT hn.nspname, hc.relname
FROM _perimeter p
JOIN pg_class c        ON c.relname = p.relname
JOIN pg_namespace n    ON n.oid = c.relnamespace AND n.nspname = p.nspname
JOIN pg_trigger tg     ON tg.tgrelid = c.oid AND NOT tg.tgisinternal
JOIN pg_proc pr        ON pr.oid = tg.tgfoid AND pr.proname = 'trgfn_storico_generic'
JOIN pg_namespace pn   ON pn.oid = pr.pronamespace AND pn.nspname = 'script'
JOIN pg_class hc       ON hc.relname = c.relname AND hc.relkind IN ('r', 'p')
JOIN pg_namespace hn   ON hn.oid = hc.relnamespace AND hn.nspname = 'storico';

SELECT format('GRANT INSERT, UPDATE ON TABLE %I.%I TO %I', h.nspname, h.relname, :'batch_role')
FROM _perimeter_hist h
\gexec

-- Sequenze identity/serial possedute dalle tabelle del perimetro E dalle loro shadow
-- storico (deptype 'a'/'i'): USAGE+SELECT per consentire nextval in INSERT
-- (PK identity delle ancillari e delle shadow, es. storico.<t>_id_seq).
SELECT format('GRANT USAGE, SELECT ON SEQUENCE %I.%I TO %I', seq_ns.nspname, seq.relname, :'batch_role')
FROM (
    SELECT nspname, relname FROM _perimeter
    UNION
    SELECT nspname, relname FROM _perimeter_hist
) tbl
JOIN pg_class t        ON t.relname = tbl.relname
JOIN pg_namespace tn   ON tn.oid = t.relnamespace AND tn.nspname = tbl.nspname
JOIN pg_depend d       ON d.refobjid = t.oid AND d.deptype IN ('a', 'i')
JOIN pg_class seq      ON seq.oid = d.objid AND seq.relkind = 'S'
JOIN pg_namespace seq_ns ON seq_ns.oid = seq.relnamespace
\gexec

-- Sequenze-codice STANDALONE del perimetro: usate da script.fn_generate_codice via
-- nextval dinamico, NON legate a una colonna -> il join pg_depend sopra non le prende.
-- Vanno enumerate esplicitamente (fail-loud: una code-sequence nuova va aggiunta qui).
CREATE TEMP TABLE _perimeter_seq (nspname TEXT, relname TEXT);
INSERT INTO _perimeter_seq (nspname, relname) VALUES
    ('vendite', 'fatturazione_lotti_codice_seq');

DELETE FROM _perimeter_seq s
WHERE NOT EXISTS (
    SELECT 1 FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = s.nspname
      AND c.relname = s.relname
      AND c.relkind = 'S'
);

SELECT format('GRANT USAGE, SELECT ON SEQUENCE %I.%I TO %I', s.nspname, s.relname, :'batch_role')
FROM _perimeter_seq s
\gexec

\echo [ZeroErp] OK: provisioning zeroerp_batch_fatturazione completato
