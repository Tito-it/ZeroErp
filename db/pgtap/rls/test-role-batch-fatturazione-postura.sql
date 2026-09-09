-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgtap-contesto: escluso — la ragione e' scritta per esteso piu' sotto in
--   questo stesso file. Dichiarazione leggibile dal cancello
--   scripts/guardrail_pgtap_preambolo.py: distingue «escluso apposta» da
--   «dimenticato», che una nota in prosa non fa.
--   ⚠️ Da riguardare: le esclusioni `rls/` furono fatte IN BLOCCO, e almeno
--   una non ne aveva diritto (brief pgtap-runner-rls-baseline §30.2).
-- pgTAP test STRUTTURALE — postura ruolo batch per-job zeroerp_batch_fatturazione
--
-- Canale di sistema headless per il batch di fatturazione sotto RLS (Path A).
-- Vedi: brief-db-contesto-sistema-batch-fatturazione-rls.md
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
--   9   : gemello «esiste» dell'8 — la lente sui grant vede davvero (2026-09-02)
--   10  : nessuna tabella del perimetro ESISTENTE priva dei privilegi del suo grado (buchi)
--   11  : SELECT ampio su tabella RLS fuori perimetro (vendite.ordini)
--   12  : controprova fail-loud: NESSUN DML su vendite.ordini
--   13-14: EXECUTE sulle funzioni run-log (script.fn_job_run_start/end)
--   15  : NESSUN DML diretto su maintenance.job_run_log
--   16  : USAGE sulle sequenze-codice standalone del perimetro (code-seq)
--   17  : controprova append-only: NESSUN DELETE su vendite.event_log
--   18  : shadow storico.* del perimetro con INSERT+UPDATE (trigger trgfn_storico_generic)
--   19  : controprova: NESSUN DELETE sulla shadow storico (snapshot SCD)
--
-- Perimetro GRADUATO (privilege-set per tabella): iud=full DML, iu=INSERT+UPDATE,
-- i=INSERT only (append-only / upsert DO NOTHING), u=UPDATE only (es. commesse_attivita
-- stato_emissione). Test 8/10 sono privilege-set-aware via _perimeter_priv, che include
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

SELECT plan(19);

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
    ('vendite', 'fatture_indirizzi',                'iu'),
    ('vendite', 'event_log',                        'i'),
    ('vendite', 'attivita_fatturabili_log',         'i'),
    ('pagamenti', 'vendite_contabili_lotti',        'i'),
    -- render documentale (C-2b): il worker fa solo INSERT append.
    ('documenti', 'documenti_generati',             'i'),
    ('documenti', 'documenti_generati_file',        'i'),
    ('documenti', 'documenti_generati_eventi',      'i'),
    -- DELETE only: il cleanup del rollback automatico cancella le note della
    -- fattura; l'INSERT e' del flusso operatore, non del batch.
    ('vendite', 'note',                             'd'),
    ('vendite', 'commesse_attivita',                'u'),
    -- coda stampa: il drainer fa SOLO claim/marca/reaper (UPDATE).
    ('vendite', 'fatture_stampa_coda',              'u');

-- Espansione grado -> privilegi attesi (single source per test 8 e 10)
-- ⚠️ Il CASE dev'essere COMPLETO sui gradi in uso: un grado non previsto cade
--   nell'ELSE implicito, `unnest(NULL)` non produce righe e la tabella sparisce
--   dal perimetro IN SILENZIO — ne' over-grant (test 8) ne' buco (test 10). Il
--   grado 'd' e' esistito nel provisioning senza esistere qui.
CREATE TEMP TABLE _perimeter_priv ON COMMIT DROP AS
SELECT p.nspname, p.relname, unnest(
    CASE p.grade
        WHEN 'iud' THEN ARRAY['INSERT', 'UPDATE', 'DELETE']
        WHEN 'iu'  THEN ARRAY['INSERT', 'UPDATE']
        WHEN 'i'   THEN ARRAY['INSERT']
        WHEN 'u'   THEN ARRAY['UPDATE']
        WHEN 'd'   THEN ARRAY['DELETE']
    END
) AS privilege_type
FROM _perimeter p;

-- Shadow storico.* del perimetro (derivato dai trigger script.trgfn_storico_generic,
-- SECURITY INVOKER): l'UPDATE delle tabelle del perimetro storicizzate scrive in
-- storico.<tabella> -> INSERT (nuovo snapshot) + UPDATE (chiusura valid_to). NO DELETE.
-- Aggiunti all'allow-set: test 8 (over-grant) li sancisce, test 10 (buchi) li pretende.
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
--
-- ⛔ LA SORGENTE E' `pg_class.relacl`, NON `information_schema.role_table_grants`.
--    Quella vista mostra solo i grant in cui il ruolo CONNESSO e' concedente o
--    beneficiario: girando come `zeroerp_app` — il default dal 2026-08-07 —
--    rispondeva ZERO righe per un ruolo batch di cui `zeroerp_app` non sa
--    niente, e il test era verde per SOTTRAZIONE. Non un caso di bordo: non
--    poteva vedere NIENTE, quindi non poteva accorgersi di NIENTE.
--    `relacl` sta nel catalogo ed e' leggibile da chiunque, e `has_table_privilege`
--    (test 9, 10, 11, 14, 16, 17, 18) non ha mai avuto il problema — e' per
--    questo che 9 e 17 segnalavano mentre 8 taceva.
--    ⚠️ `relacl` e' NULL quando la tabella ha i soli privilegi di default: li'
--    `aclexplode` non produce righe, ed e' corretto — nessun grant al batch.
SELECT is(
    (SELECT count(*)::int
     FROM pg_class c
     JOIN pg_namespace n ON n.oid = c.relnamespace
     CROSS JOIN LATERAL aclexplode(c.relacl) a
     JOIN pg_roles r ON r.oid = a.grantee
     WHERE c.relkind IN ('r', 'p')
       AND r.rolname = 'zeroerp_batch_fatturazione'
       AND a.privilege_type IN ('INSERT', 'UPDATE', 'DELETE')
       AND NOT EXISTS (
           SELECT 1 FROM _perimeter_priv pp
           WHERE pp.nspname = n.nspname AND pp.relname = c.relname
             AND pp.privilege_type = a.privilege_type
       )),
    0,
    'zeroerp_batch_fatturazione: nessun DML oltre il grado atteso (no over-grant)'
);

-- 9: gemello «esiste» del test 8. Un test che CONTA I CATTIVI risponde zero
--    anche quando i candidati sono zero: e' esattamente cosi' che il test 8 e'
--    stato verde per mesi leggendo una vista che non gli mostrava niente.
--    Questa riga pretende che la lente veda davvero dei grant DML del ruolo.
SELECT cmp_ok(
    (SELECT count(*)::int
     FROM pg_class c
     JOIN pg_namespace n ON n.oid = c.relnamespace
     CROSS JOIN LATERAL aclexplode(c.relacl) a
     JOIN pg_roles r ON r.oid = a.grantee
     WHERE c.relkind IN ('r', 'p')
       AND r.rolname = 'zeroerp_batch_fatturazione'
       AND a.privilege_type IN ('INSERT', 'UPDATE', 'DELETE')),
    '>=', 20,
    'zeroerp_batch_fatturazione: la lente sui grant DML vede davvero (test 8 non e'' muto)'
);

-- 10: nessuna tabella del perimetro ESISTENTE priva dei privilegi del proprio grado (buchi)
SELECT is(
    (SELECT count(*)::int
     FROM _perimeter_priv pp
     JOIN pg_class c ON c.relname = pp.relname AND c.relkind IN ('r', 'p')
     JOIN pg_namespace n ON n.oid = c.relnamespace AND n.nspname = pp.nspname
     WHERE NOT has_table_privilege('zeroerp_batch_fatturazione', format('%I.%I', pp.nspname, pp.relname), pp.privilege_type)),
    0,
    'zeroerp_batch_fatturazione: tutte le tabelle del perimetro presenti hanno i privilegi del grado'
);

-- 11: SELECT ampio su tabella RLS fuori perimetro (vendite.ordini)
SELECT ok(
    has_table_privilege('zeroerp_batch_fatturazione', 'vendite.ordini', 'SELECT'),
    'zeroerp_batch_fatturazione: SELECT ampio su vendite.ordini (fuori perimetro)'
);

-- 12: controprova fail-loud: NESSUN DML su vendite.ordini
SELECT ok(
    NOT has_table_privilege('zeroerp_batch_fatturazione', 'vendite.ordini', 'INSERT'),
    'zeroerp_batch_fatturazione: NESSUN INSERT su vendite.ordini (fail-loud)'
);

-- 13..14: canale run-log (J2/J3) — EXECUTE sulle funzioni SECURITY DEFINER in script
-- (il ruolo le ottiene via il broad GRANT EXECUTE su schema script del provisioning)
SELECT ok(
    has_function_privilege('zeroerp_batch_fatturazione',
        -- ⚠️ Funzione cercata per NOME, non per firma letterale: la firma
        --   cambia quando si aggiungono parametri (2026-09-04: +attore), e
        --   un test che la scrive a mano fallisce per il MOTIVO SBAGLIATO —
        --   segnala la firma invece del privilegio che deve presidiare.
        (SELECT p.oid
           FROM pg_catalog.pg_proc p
           JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
          WHERE n.nspname = 'script' AND p.proname = 'fn_job_run_start'),
        'EXECUTE'),
    'zeroerp_batch_fatturazione: EXECUTE su script.fn_job_run_start'
);
SELECT ok(
    has_function_privilege('zeroerp_batch_fatturazione',
        'script.fn_job_run_end(bigint,boolean,text,bigint,text,text,jsonb,text)', 'EXECUTE'),
    'zeroerp_batch_fatturazione: EXECUTE su script.fn_job_run_end'
);

-- 15: NESSUN DML diretto su maintenance.job_run_log (scrive solo via le funzioni)
SELECT ok(
    NOT has_table_privilege('zeroerp_batch_fatturazione', 'maintenance.job_run_log', 'INSERT'),
    'zeroerp_batch_fatturazione: NESSUN INSERT diretto su maintenance.job_run_log'
);

-- 16: USAGE sulla sequenza-codice standalone del perimetro (fn_generate_codice -> nextval).
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

-- 17: controprova append-only: NESSUN DELETE su vendite.event_log (grado INSERT-only)
SELECT ok(
    NOT has_table_privilege('zeroerp_batch_fatturazione', 'vendite.event_log', 'DELETE'),
    'zeroerp_batch_fatturazione: NESSUN DELETE su vendite.event_log (append-only)'
);

-- 18: shadow storico.* del perimetro -> INSERT+UPDATE su tutte (derivato dai trigger,
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

-- 19: controprova: NESSUN DELETE sulla shadow storico (gli snapshot SCD non si cancellano)
SELECT ok(
    NOT has_table_privilege('zeroerp_batch_fatturazione', 'storico.fatturazione_lotti', 'DELETE'),
    'zeroerp_batch_fatturazione: NESSUN DELETE su storico.fatturazione_lotti (snapshot SCD)'
);

SELECT * FROM finish();
ROLLBACK;
