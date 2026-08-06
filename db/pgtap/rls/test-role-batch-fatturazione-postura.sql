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
--   8   : nessun DML OLTRE il grado atteso (over-grant; include sopra-grado)
--   9   : nessuna tabella del perimetro ESISTENTE priva dei privilegi del suo grado (buchi)
--   10  : SELECT ampio su tabella RLS fuori perimetro (vendite.ordini)
--   11  : controprova fail-loud: NESSUN DML su vendite.ordini
--   12-13: EXECUTE sulle funzioni run-log (script.fn_job_run_start/end)
--   14  : NESSUN DML diretto su maintenance.job_run_log
--   15  : USAGE sulle sequenze-codice standalone del perimetro (code-seq)
--   16  : controprova append-only: NESSUN DELETE su vendite.event_log
--   17  : shadow storico.* del perimetro con INSERT+UPDATE (trigger trgfn_storico_generic)
--   18  : controprova: NESSUN DELETE sulla shadow storico (snapshot SCD)
--
-- Perimetro GRADUATO (privilege-set per tabella): iud=full DML, iu=INSERT+UPDATE,
-- i=INSERT only (append-only / upsert DO NOTHING), u=UPDATE only (es. commesse_attivita
-- stato_emissione). Test 8/9 sono privilege-set-aware via _perimeter_priv, che include
-- anche lo shadow storico.* (INSERT+UPDATE) derivato dai trigger.
--
-- Prerequisito: il ruolo dev'essere stato provisionato (D1/D3). Asserzioni
-- aggregate -> plan fisso anche su DB parziali. Read-only: BEGIN;/ROLLBACK;.
-- ------------------------------------------------------------

BEGIN;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file sarebbe verde per sottrazione. IMMEDIATE li riporta a scattare a fine
--   di ogni istruzione. In testa e non in coda: in coda scatterebbero dopo il
--   cleanup, su righe ormai cancellate.
--   Brief: brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(18);

-- Perimetro di scrittura atteso (allineato al provisioning), GRADUATO per privilege-set:
--   iud = full DML (INSERT/UPDATE/DELETE), iu = INSERT+UPDATE, i = INSERT only (append-only).
CREATE TEMP TABLE _perimeter (nspname TEXT, relname TEXT, grade TEXT) ON COMMIT DROP;
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

-- Espansione grado -> privilegi attesi (single source per test 8/9)
CREATE TEMP TABLE _perimeter_priv ON COMMIT DROP AS
SELECT p.nspname, p.relname, unnest(
    CASE p.grade
        WHEN 'iud' THEN ARRAY['INSERT', 'UPDATE', 'DELETE']
        WHEN 'iu'  THEN ARRAY['INSERT', 'UPDATE']
        WHEN 'i'   THEN ARRAY['INSERT']
        WHEN 'u'   THEN ARRAY['UPDATE']
    END
) AS privilege_type
FROM _perimeter p;

-- Shadow storico.* del perimetro (derivato dai trigger script.trgfn_storico_generic,
-- SECURITY INVOKER): l'UPDATE delle tabelle del perimetro storicizzate scrive in
-- storico.<tabella> -> INSERT (nuovo snapshot) + UPDATE (chiusura valid_to). NO DELETE.
-- Aggiunti all'allow-set: test 8 (over-grant) li sancisce, test 9 (buchi) li pretende.
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

-- Sequenze-codice standalone attese (USAGE): usate da fn_generate_codice via nextval
-- dinamico, non legate a colonna -> non coperte dal grant pg_depend identity/serial.
CREATE TEMP TABLE _perimeter_seq (nspname TEXT, relname TEXT) ON COMMIT DROP;
INSERT INTO _perimeter_seq (nspname, relname) VALUES
    ('vendite', 'fatturazione_lotti_codice_seq');

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

-- 8: nessun DML OLTRE il grado atteso (over-grant). Cattura sia il DML fuori perimetro
--    sia il privilegio sopra-grado (es. DELETE su una tabella append-only INSERT-only).
SELECT is(
    (SELECT count(*)::int
     FROM information_schema.role_table_grants g
     WHERE g.grantee = 'zeroerp_batch_fatturazione'
       AND g.privilege_type IN ('INSERT', 'UPDATE', 'DELETE')
       AND NOT EXISTS (
           SELECT 1 FROM _perimeter_priv pp
           WHERE pp.nspname = g.table_schema AND pp.relname = g.table_name
             AND pp.privilege_type = g.privilege_type
       )),
    0,
    'zeroerp_batch_fatturazione: nessun DML oltre il grado atteso (no over-grant)'
);

-- 9: nessuna tabella del perimetro ESISTENTE priva dei privilegi del proprio grado (buchi)
SELECT is(
    (SELECT count(*)::int
     FROM _perimeter_priv pp
     JOIN pg_class c ON c.relname = pp.relname AND c.relkind IN ('r', 'p')
     JOIN pg_namespace n ON n.oid = c.relnamespace AND n.nspname = pp.nspname
     WHERE NOT has_table_privilege('zeroerp_batch_fatturazione', format('%I.%I', pp.nspname, pp.relname), pp.privilege_type)),
    0,
    'zeroerp_batch_fatturazione: tutte le tabelle del perimetro presenti hanno i privilegi del grado'
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

-- 12..13: canale run-log (J2/J3) — EXECUTE sulle funzioni SECURITY DEFINER in script
-- (il ruolo le ottiene via il broad GRANT EXECUTE su schema script del provisioning)
SELECT ok(
    has_function_privilege('zeroerp_batch_fatturazione',
        'script.fn_job_run_start(text,text,text,text,text)', 'EXECUTE'),
    'zeroerp_batch_fatturazione: EXECUTE su script.fn_job_run_start'
);
SELECT ok(
    has_function_privilege('zeroerp_batch_fatturazione',
        'script.fn_job_run_end(bigint,boolean,text,bigint,text,text,jsonb,text)', 'EXECUTE'),
    'zeroerp_batch_fatturazione: EXECUTE su script.fn_job_run_end'
);

-- 14: NESSUN DML diretto su maintenance.job_run_log (scrive solo via le funzioni)
SELECT ok(
    NOT has_table_privilege('zeroerp_batch_fatturazione', 'maintenance.job_run_log', 'INSERT'),
    'zeroerp_batch_fatturazione: NESSUN INSERT diretto su maintenance.job_run_log'
);

-- 15: USAGE sulla sequenza-codice standalone del perimetro (fn_generate_codice -> nextval).
-- E' il grant che mancava e faceva fallire l'INSERT in fatturazione_lotti (codice).
SELECT is(
    (SELECT count(*)::int
     FROM _perimeter_seq s
     JOIN pg_class c ON c.relname = s.relname AND c.relkind = 'S'
     JOIN pg_namespace n ON n.oid = c.relnamespace AND n.nspname = s.nspname
     WHERE NOT has_sequence_privilege('zeroerp_batch_fatturazione', format('%I.%I', s.nspname, s.relname), 'USAGE')),
    0,
    'zeroerp_batch_fatturazione: USAGE su tutte le sequenze-codice del perimetro'
);

-- 16: controprova append-only: NESSUN DELETE su vendite.event_log (grado INSERT-only)
SELECT ok(
    NOT has_table_privilege('zeroerp_batch_fatturazione', 'vendite.event_log', 'DELETE'),
    'zeroerp_batch_fatturazione: NESSUN DELETE su vendite.event_log (append-only)'
);

-- 17: shadow storico.* del perimetro -> INSERT+UPDATE su tutte (derivato dai trigger,
-- indipendente da _perimeter_priv). I trigger di storicizzazione scrivono qui all'UPDATE.
SELECT is(
    (SELECT count(*)::int
     FROM _perimeter p
     JOIN pg_class c        ON c.relname = p.relname
     JOIN pg_namespace n    ON n.oid = c.relnamespace AND n.nspname = p.nspname
     JOIN pg_trigger tg     ON tg.tgrelid = c.oid AND NOT tg.tgisinternal
     JOIN pg_proc pr        ON pr.oid = tg.tgfoid AND pr.proname = 'trgfn_storico_generic'
     JOIN pg_namespace pn   ON pn.oid = pr.pronamespace AND pn.nspname = 'script'
     JOIN pg_class hc       ON hc.relname = c.relname AND hc.relkind IN ('r', 'p')
     JOIN pg_namespace hn   ON hn.oid = hc.relnamespace AND hn.nspname = 'storico'
     WHERE NOT (
            has_table_privilege('zeroerp_batch_fatturazione', format('%I.%I', hn.nspname, hc.relname), 'INSERT')
        AND has_table_privilege('zeroerp_batch_fatturazione', format('%I.%I', hn.nspname, hc.relname), 'UPDATE')
     )),
    0,
    'zeroerp_batch_fatturazione: shadow storico del perimetro con INSERT+UPDATE'
);

-- 18: controprova: NESSUN DELETE sulla shadow storico (gli snapshot SCD non si cancellano)
SELECT ok(
    NOT has_table_privilege('zeroerp_batch_fatturazione', 'storico.fatturazione_lotti', 'DELETE'),
    'zeroerp_batch_fatturazione: NESSUN DELETE su storico.fatturazione_lotti (snapshot SCD)'
);

SELECT * FROM finish();
ROLLBACK;
