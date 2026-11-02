-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- Copyright (C) 2026 Tid (Michele Carlo Titini)
-- ------------------------------------------------------------
-- Test pgTAP — dbops.coda_lavori / coda_lavori_tipi / fn_accoda_lavoro
-- Brief: brief-db-coda-lavori-generica (§1 tabella, §2 registry, §3 enqueue,
--        §4 seed, §6 verifica attesa).
--
-- Indice test (1..57):
--   A) Struttura coda_lavori_tipi ......... 1..9
--      1 has_table; 2-5 colonne; 6 PK; 7 unique codice; 8-9 trigger audit/tx_id
--   B) Struttura coda_lavori .............. 10..39
--      10 has_table; 11-26 colonne; 27 PK; 28-31 indici (uid, claim, vivo, stato);
--      32 FK; 33 col_is_fk job_type; 34 has_check; 35-37 CHECK stato/run_as/origine;
--      38-39 trigger audit/tx_id
--   C) Seed FATTURAZIONE_GIRO presente e attivo .. 40
--   D) Esistenza fn_accoda_lavoro ......... 41
--   E) Enqueue base (default dal tipo) .... 42..46
--      42 id non NULL; 43 stato PENDING; 44 run_as OPERATORE (default tipo);
--      45 max_tentativi 5 (default tipo); 46 origine API (default)
--   F) Idempotenza job vivi ............... 47..48
--      47 2a chiamata stessa chiave -> stesso id; 48 un solo job vivo per chiave
--   G) Guard (raise P0001) ................ 49..52
--      49 job_type inesistente; 50 job_type inattivo; 51 OPERATORE senza scope;
--      52 job_type NULL
--   H) Enqueue SISTEMA (scope NULL ammesso) 53..54
--   I) CHECK run_as<->scope (raise 23514) . 55..56
--   J) Unique parziale vivo (raise 23505) . 57
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

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(57);

-- ============================================================
-- A) Struttura dbops.coda_lavori_tipi
-- ============================================================
SELECT has_table('dbops', 'coda_lavori_tipi', '1) tabella dbops.coda_lavori_tipi esiste');
SELECT has_column('dbops', 'coda_lavori_tipi', 'codice', '2) colonna codice');
SELECT has_column('dbops', 'coda_lavori_tipi', 'handler_code', '3) colonna handler_code');
SELECT has_column('dbops', 'coda_lavori_tipi', 'run_as_default', '4) colonna run_as_default');
SELECT has_column('dbops', 'coda_lavori_tipi', 'attivo', '5) colonna attivo');
SELECT has_pk('dbops', 'coda_lavori_tipi', '6) PK pk_coda_lavori_tipi');
SELECT ok(
    EXISTS (SELECT 1 FROM pg_indexes
             WHERE schemaname = 'dbops' AND tablename = 'coda_lavori_tipi'
               AND indexname = 'uq_coda_lavori_tipi_codice'),
    '7) unique uq_coda_lavori_tipi_codice esiste');
SELECT has_trigger('dbops', 'coda_lavori_tipi',
    'trg_coda_lavori_tipi_audit_data_user_ins_upd', '8) trigger audit registrato');
SELECT has_trigger('dbops', 'coda_lavori_tipi',
    'trg_coda_lavori_tipi_gen_tx_id_ins_upd', '9) trigger tx_id registrato');

-- ============================================================
-- B) Struttura dbops.coda_lavori
-- ============================================================
SELECT has_table('dbops', 'coda_lavori', '10) tabella dbops.coda_lavori esiste');
SELECT has_column('dbops', 'coda_lavori', 'id', '11) colonna id');
SELECT has_column('dbops', 'coda_lavori', 'uid', '12) colonna uid');
SELECT has_column('dbops', 'coda_lavori', 'job_type', '13) colonna job_type');
SELECT has_column('dbops', 'coda_lavori', 'payload', '14) colonna payload');
SELECT has_column('dbops', 'coda_lavori', 'run_as', '15) colonna run_as');
SELECT has_column('dbops', 'coda_lavori', 'scope', '16) colonna scope');
SELECT has_column('dbops', 'coda_lavori', 'origine', '17) colonna origine');
SELECT has_column('dbops', 'coda_lavori', 'priorita', '18) colonna priorita');
SELECT has_column('dbops', 'coda_lavori', 'stato', '19) colonna stato');
SELECT has_column('dbops', 'coda_lavori', 'tentativi', '20) colonna tentativi');
SELECT has_column('dbops', 'coda_lavori', 'max_tentativi', '21) colonna max_tentativi');
SELECT has_column('dbops', 'coda_lavori', 'run_after', '22) colonna run_after');
SELECT has_column('dbops', 'coda_lavori', 'claimed_at', '23) colonna claimed_at');
SELECT has_column('dbops', 'coda_lavori', 'idempotency_key', '24) colonna idempotency_key');
SELECT has_column('dbops', 'coda_lavori', 'result', '25) colonna result');
SELECT has_column('dbops', 'coda_lavori', 'tx_id', '26) colonna tx_id');
SELECT has_pk('dbops', 'coda_lavori', '27) PK pk_coda_lavori');
SELECT ok(
    EXISTS (SELECT 1 FROM pg_indexes
             WHERE schemaname = 'dbops' AND tablename = 'coda_lavori'
               AND indexname = 'uq_coda_lavori_uid'),
    '28) unique uq_coda_lavori_uid esiste');
SELECT ok(
    EXISTS (SELECT 1 FROM pg_indexes
             WHERE schemaname = 'dbops' AND tablename = 'coda_lavori'
               AND indexname = 'ix_coda_lavori_da_lavorare'),
    '29) indice claim ix_coda_lavori_da_lavorare esiste');
SELECT ok(
    EXISTS (SELECT 1 FROM pg_indexes
             WHERE schemaname = 'dbops' AND tablename = 'coda_lavori'
               AND indexname = 'uq_coda_lavori_vivo_idem'),
    '30) unique parziale uq_coda_lavori_vivo_idem esiste');
SELECT ok(
    EXISTS (SELECT 1 FROM pg_indexes
             WHERE schemaname = 'dbops' AND tablename = 'coda_lavori'
               AND indexname = 'ix_coda_lavori_stato'),
    '31) indice monitoraggio ix_coda_lavori_stato esiste');
SELECT has_fk('dbops', 'coda_lavori', '32) FK presente su coda_lavori');
SELECT col_is_fk('dbops', 'coda_lavori', 'job_type', '33) job_type e'' FK');
SELECT has_check('dbops', 'coda_lavori', '34) CHECK presenti su coda_lavori');
SELECT col_has_check('dbops', 'coda_lavori', 'stato', '35) CHECK su stato');
SELECT col_has_check('dbops', 'coda_lavori', 'run_as', '36) CHECK su run_as');
SELECT col_has_check('dbops', 'coda_lavori', 'origine', '37) CHECK su origine');
SELECT has_trigger('dbops', 'coda_lavori',
    'trg_coda_lavori_audit_data_user_ins_upd', '38) trigger audit registrato');
SELECT has_trigger('dbops', 'coda_lavori',
    'trg_coda_lavori_gen_tx_id_ins_upd', '39) trigger tx_id registrato');

-- ============================================================
-- C) Seed FATTURAZIONE_GIRO
-- ============================================================
SELECT ok(
    EXISTS (SELECT 1 FROM dbops.coda_lavori_tipi
             WHERE codice = 'FATTURAZIONE_GIRO' AND attivo IS TRUE
               AND handler_code = 'fatturazione_giro_default'),
    '40) seed FATTURAZIONE_GIRO presente e attivo');

-- ============================================================
-- D) Esistenza funzione
-- ============================================================
SELECT ok(
    EXISTS (SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
             WHERE n.nspname = 'dbops' AND p.proname = 'fn_accoda_lavoro'),
    '41) funzione dbops.fn_accoda_lavoro esiste');

-- ------------------------------------------------------------
-- Fixtures (rollback a fine test): un tipo SISTEMA e un tipo INATTIVO.
-- ------------------------------------------------------------
-- ⚠️ 2026-09-04: `dbops.coda_lavori_tipi.processo_codice` e' NOT NULL — ogni
--   tipo di coda dichiara di quale PROCESSO e', e da li' il guard di classe in
--   dbops.fn_accoda_lavoro legge se il lavoro e' di dominio. Un tipo senza
--   processo non avrebbe una classe, quindi niente da controllare.
--   ⇒ La fixture si fabbrica il proprio processo invece di appoggiarsi a uno
--     del catalogo: MANUTENZIONE, cosi' il guard di classe non entra in gioco e
--     questo file continua a collaudare cio' che collaudava.
INSERT INTO dbops.processi (id, codice, descrizione, classe, canale, causa_fallimento)
VALUES (9702, 'PGTAP_PROC_CODA_LAVORI', 'processo di prova per test-coda-lavori', 'MANUTENZIONE', 'CODA', 'PROGRAMMA');

INSERT INTO dbops.coda_lavori_tipi
  (codice, handler_code, run_as_default, attivo, processo_codice)
VALUES ('PGTAP_CL_SISTEMA',  'pgtap_noop', 'SISTEMA',   TRUE,  'PGTAP_PROC_CODA_LAVORI'),
       ('PGTAP_CL_INATTIVO', 'pgtap_noop', 'OPERATORE', FALSE, 'PGTAP_PROC_CODA_LAVORI');

-- Side-effect: enqueue base (OPERATORE, scope obbligatorio) + 2a chiamata
-- idempotente stessa chiave + enqueue SISTEMA. Id catturati in tmp_enq.
CREATE TEMP TABLE tmp_enq AS
SELECT dbops.fn_accoda_lavoro(
           'FATTURAZIONE_GIRO', '{}'::jsonb, NULL,
           '{"emittente_ids":[1],"auth_user_id":1}'::jsonb, 'pgtap-key-1'
       ) AS id1;
ALTER TABLE tmp_enq ADD COLUMN id2 bigint;
ALTER TABLE tmp_enq ADD COLUMN id3 bigint;
UPDATE tmp_enq SET id2 = dbops.fn_accoda_lavoro(
           'FATTURAZIONE_GIRO', '{}'::jsonb, NULL,
           '{"emittente_ids":[1],"auth_user_id":1}'::jsonb, 'pgtap-key-1');
UPDATE tmp_enq SET id3 = dbops.fn_accoda_lavoro('PGTAP_CL_SISTEMA');

-- ============================================================
-- E) Enqueue base — default risolti dal tipo
-- ============================================================
SELECT isnt((SELECT id1 FROM tmp_enq), NULL::bigint, '42) enqueue base ritorna un id');
SELECT is(
    (SELECT stato FROM dbops.coda_lavori WHERE id = (SELECT id1 FROM tmp_enq)),
    'PENDING', '43) job accodato in stato PENDING');
SELECT is(
    (SELECT run_as FROM dbops.coda_lavori WHERE id = (SELECT id1 FROM tmp_enq)),
    'OPERATORE', '44) run_as risolto dal default del tipo (OPERATORE)');
SELECT is(
    (SELECT max_tentativi FROM dbops.coda_lavori WHERE id = (SELECT id1 FROM tmp_enq)),
    5, '45) max_tentativi risolto dal default del tipo (5)');
SELECT is(
    (SELECT origine FROM dbops.coda_lavori WHERE id = (SELECT id1 FROM tmp_enq)),
    'API', '46) origine default API');

-- ============================================================
-- F) Idempotenza sui job vivi
-- ============================================================
SELECT is((SELECT id2 FROM tmp_enq), (SELECT id1 FROM tmp_enq),
    '47) 2a chiamata stessa idempotency_key viva -> stesso id');
SELECT is(
    (SELECT COUNT(*)::int FROM dbops.coda_lavori
      WHERE job_type = 'FATTURAZIONE_GIRO' AND idempotency_key = 'pgtap-key-1'
        AND stato IN ('PENDING', 'IN_CORSO')),
    1, '48) un solo job vivo per (job_type, idempotency_key)');

-- ============================================================
-- G) Guard — sollevano P0001 (script.fn_log_and_raise_error)
-- ============================================================
SELECT throws_ok(
    $$ SELECT dbops.fn_accoda_lavoro('PGTAP_JOB_INESISTENTE') $$,
    'P0001', NULL, '49) job_type inesistente -> E_JOB_TYPE_NON_TROVATO');
SELECT throws_ok(
    $$ SELECT dbops.fn_accoda_lavoro('PGTAP_CL_INATTIVO', '{}'::jsonb, NULL, '{"x":1}'::jsonb) $$,
    'P0001', NULL, '50) job_type inattivo -> E_JOB_TYPE_NON_ATTIVO');
SELECT throws_ok(
    $$ SELECT dbops.fn_accoda_lavoro('FATTURAZIONE_GIRO') $$,
    'P0001', NULL, '51) run_as OPERATORE senza scope -> E_PARAMETRO_INVALIDO');
SELECT throws_ok(
    $$ SELECT dbops.fn_accoda_lavoro(NULL) $$,
    'P0001', NULL, '52) job_type NULL -> E_PARAMETRO_INVALIDO');

-- ============================================================
-- H) Enqueue SISTEMA — scope NULL ammesso
-- ============================================================
SELECT isnt((SELECT id3 FROM tmp_enq), NULL::bigint, '53) enqueue SISTEMA ritorna un id');
SELECT is(
    (SELECT run_as FROM dbops.coda_lavori WHERE id = (SELECT id3 FROM tmp_enq)),
    'SISTEMA', '54) run_as SISTEMA con scope NULL');

-- ============================================================
-- I) CHECK di coerenza run_as<->scope (raw INSERT -> 23514)
-- ============================================================
SELECT throws_ok(
    $$ INSERT INTO dbops.coda_lavori (job_type, run_as, scope)
       VALUES ('FATTURAZIONE_GIRO', 'OPERATORE', NULL) $$,
    '23514', NULL, '55) OPERATORE con scope NULL viola chk_coda_lavori_run_as_scope');
SELECT throws_ok(
    $$ INSERT INTO dbops.coda_lavori (job_type, run_as, scope)
       VALUES ('FATTURAZIONE_GIRO', 'SISTEMA', '{"x":1}'::jsonb) $$,
    '23514', NULL, '56) SISTEMA con scope NOT NULL viola chk_coda_lavori_run_as_scope');

-- ============================================================
-- J) Unique parziale vivo (raw INSERT doppione vivo -> 23505)
-- ============================================================
SELECT throws_ok(
    $$ INSERT INTO dbops.coda_lavori (job_type, run_as, scope, idempotency_key)
       VALUES ('FATTURAZIONE_GIRO', 'OPERATORE', '{"emittente_ids":[1]}'::jsonb, 'pgtap-key-1') $$,
    '23505', NULL, '57) doppione vivo (job_type, idempotency_key) viola uq_coda_lavori_vivo_idem');

SELECT * FROM finish();
ROLLBACK;
