-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture scrive su maintenance.job_run_log (lo scrivono
--   solo i job e le porte DEFINER del backend), su dbops.processi e su
--   config.codici_errore (cataloghi del migratore). Il ruolo applicativo li legge.
--
-- Test: maintenance.vw_job_run_da_guardare — ogni riga dice la sua causa, e
--   quindi a chi tocca
-- ChangeSet: 00_schema/dbops/20261016-34 · 20261016-35 · 20261016-36 · 20261016-37
--   · 20_code/maintenance/20261016-41 · 80_data/20261016-42 · 90_end/20261016-43
--   · 20_code/script/20261016-44 · 20_code/maintenance/20261016-53
-- Brief: brief-db-presidio-job-run-a-chi-tocca
--
-- Elenco test (plan 15):
--  1) ⭐ le cause del presidio sono ESATTAMENTE il vocabolario dbops.cause_fallimento
--  2) il catalogo dei presidi dichiara la colonna della causa
--  3) le tre colonne nuove stanno IN CODA, nell'ordine
--  4) ⛔ corsa appesa → AMBIENTE, anche se il processo dice PROGRAMMA
--  5) SQLSTATE 53100 (disco pieno) → AMBIENTE, anche se il processo dice PROGRAMMA
--  6) SQLSTATE 08006 → AMBIENTE, anche se il codice dice CONFIGURAZIONE
--  7) ⭐ il codice che dichiara la sua causa batte il processo → CONFIGURAZIONE
--  8) codice non registrato → decide il processo (AMBIENTE)
--  9) codice non registrato → decide il processo (PROGRAMMA)
-- 10) ⭐ INTERMITTENTE: la causa si legge dall'ULTIMO ROSSO, non dall'ultima corsa
-- 11) e la vista dice da quale corsa l'ha letta
-- 12) ⛔ corsa in corso da cinque minuti con rossi recenti: NON e' «presa e mai
--     chiusa», e non diventa AMBIENTE
-- 13) nessuna riga della vista senza causa
-- 14) ogni causa che la vista produce ha chi la spegne in dbops.presidi_cause
-- 15) ⭐ (rev 2026-10-16, D8) SQLSTATE 42501 (privilegio mancante) → AMBIENTE:
--     la lista sta in script.fn_sqlstate_di_ambiente (20261016-44, -53)
--
-- ────────────────────────────────────────────────────────────────
-- ⭐ I CASI SI COSTRUISCONO, non si pescano dal giornale (regola zero,
--   corollario sui test): processi, codice d'errore e corse sono fabbricati
--   qui, cosi' il test vale anche su un database ricostruito da zero.
-- ⚠️ IL RAMO «NESSUN PROCESSO → PROGRAMMA» NON E' COSTRUIBILE, e non si finge:
--   chk_job_run_log_processo_dichiarato (NOT VALID) vieta a una corsa NUOVA di
--   nascere senza processo. Il ramo esiste per le righe di prima del vincolo,
--   che il modello ammette. Lo presidiano il test 13 (nessuna causa NULL,
--   su tutte le righe della vista) e la lettura del CASE.
-- ⚠️ I test 13 e 14 guardano anche le righe vere della vista: sono presidi
--   sulla FORMA (mai NULL, sempre a catalogo), non sul contenuto.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(15);

-- ============================================================
-- Fixture
-- ============================================================
-- Due processi che dichiarano cause diverse, e un codice d'errore che dichiara
-- la sua. CODA: niente sveglia, quindi niente colonne di accensione.
INSERT INTO dbops.processi (id, codice, descrizione, classe, canale, causa_fallimento)
VALUES (9961, 'PGTAP-CAUSA-PROC-PROGRAMMA', 'prova causa del processo', 'MANUTENZIONE', 'CODA', 'PROGRAMMA'),
       (9962, 'PGTAP-CAUSA-PROC-AMBIENTE',  'prova causa del processo', 'MANUTENZIONE', 'CODA', 'AMBIENTE');

INSERT INTO config.codici_errore (codice, classe, causa_fallimento)
VALUES ('E_PGTAP_CAUSA_CONFIGURAZIONE', 'TECNICO', 'CONFIGURAZIONE');

DO $fixture$
DECLARE
    c_prog constant text := 'PGTAP-CAUSA-PROC-PROGRAMMA';
    c_amb  constant text := 'PGTAP-CAUSA-PROC-AMBIENTE';
BEGIN
    -- 4) appesa da tre ore
    INSERT INTO maintenance.job_run_log (jobname, stepname, processo_codice, origine, started_at)
    VALUES ('PGTAP-CAUSA-APPESA', 's', c_prog, 'PGAGENT', now() - interval '3 hours');

    -- 5) disco pieno
    INSERT INTO maintenance.job_run_log
        (jobname, stepname, processo_codice, origine, started_at, ended_at, ok, message, error_code, sqlstate)
    VALUES ('PGTAP-CAUSA-DISCO', 's', c_prog, 'PGAGENT',
            now() - interval '10 minutes', now(), false, 'disco pieno', '53100', '53100');

    -- 15) privilegio mancante (rev 2026-10-16, D8)
    INSERT INTO maintenance.job_run_log
        (jobname, stepname, processo_codice, origine, started_at, ended_at, ok, message, error_code, sqlstate)
    VALUES ('PGTAP-CAUSA-PRIVILEGIO', 's', c_prog, 'PGAGENT',
            now() - interval '10 minutes', now(), false, 'permesso negato', '42501', '42501');

    -- 6) connessione caduta, con un codice che direbbe CONFIGURAZIONE
    INSERT INTO maintenance.job_run_log
        (jobname, stepname, processo_codice, origine, started_at, ended_at, ok, message, error_code, sqlstate)
    VALUES ('PGTAP-CAUSA-CONNESSIONE', 's', c_prog, 'PGAGENT',
            now() - interval '10 minutes', now(), false, 'connessione', 'E_PGTAP_CAUSA_CONFIGURAZIONE', '08006');

    -- 7) errore di dominio col codice che dichiara la causa, processo AMBIENTE
    INSERT INTO maintenance.job_run_log
        (jobname, stepname, processo_codice, origine, started_at, ended_at, ok, message, error_code, sqlstate)
    VALUES ('PGTAP-CAUSA-CODICE', 's', c_amb, 'PGAGENT',
            now() - interval '10 minutes', now(), false, 'impostazione', 'E_PGTAP_CAUSA_CONFIGURAZIONE', 'P0001');

    -- 8) codice non registrato, processo AMBIENTE
    INSERT INTO maintenance.job_run_log
        (jobname, stepname, processo_codice, origine, started_at, ended_at, ok, message, error_code)
    VALUES ('PGTAP-CAUSA-DAL-PROC-AMB', 's', c_amb, 'COMMAND',
            now() - interval '10 minutes', now(), false, 'rotto', 'PGTAP_CODICE_CHE_NON_ESISTE');

    -- 9) codice non registrato, processo PROGRAMMA
    INSERT INTO maintenance.job_run_log
        (jobname, stepname, processo_codice, origine, started_at, ended_at, ok, message, error_code)
    VALUES ('PGTAP-CAUSA-DAL-PROC-PROG', 's', c_prog, 'COMMAND',
            now() - interval '10 minutes', now(), false, 'rotto', 'PGTAP_CODICE_CHE_NON_ESISTE');

    -- 10-11) intermittente: rosso di ieri per shutdown, ultima corsa VERDE
    INSERT INTO maintenance.job_run_log
        (jobname, stepname, processo_codice, origine, started_at, ended_at, ok, message, error_code, sqlstate)
    VALUES ('PGTAP-CAUSA-INTERMITTENTE', 's', c_prog, 'PGAGENT',
            now() - interval '1 day', now() - interval '1 day', false, 'shutdown', '57P01', '57P01');
    INSERT INTO maintenance.job_run_log
        (jobname, stepname, processo_codice, origine, started_at, ended_at, ok, message)
    VALUES ('PGTAP-CAUSA-INTERMITTENTE', 's', c_prog, 'PGAGENT',
            now() - interval '5 minutes', now(), true, 'done');

    -- 12) rosso di ieri (dominio), e adesso una corsa partita cinque minuti fa
    INSERT INTO maintenance.job_run_log
        (jobname, stepname, processo_codice, origine, started_at, ended_at, ok, message, error_code, sqlstate)
    VALUES ('PGTAP-CAUSA-IN-CORSO', 's', c_prog, 'PGAGENT',
            now() - interval '1 day', now() - interval '1 day', false, 'rotto', 'PGTAP_CODICE_CHE_NON_ESISTE', 'P0001');
    INSERT INTO maintenance.job_run_log (jobname, stepname, processo_codice, origine, started_at)
    VALUES ('PGTAP-CAUSA-IN-CORSO', 's', c_prog, 'PGAGENT', now() - interval '5 minutes');
END
$fixture$;

-- ============================================================
-- 1..3. Il catalogo e la forma
-- ============================================================
-- ⭐ La terza sede del vocabolario: non puo' essere una FK (presidi_cause e'
--   chiavata (vista, causa)), quindi la coincidenza la tiene questo test.
SELECT set_eq(
    $$SELECT causa FROM dbops.presidi_cause
       WHERE vista = 'maintenance.vw_job_run_da_guardare'$$,
    $$SELECT codice FROM dbops.cause_fallimento$$,
    '1. le cause del presidio sono esattamente il vocabolario dbops.cause_fallimento'
);

SELECT is(
    (SELECT colonna_variante FROM dbops.presidi
      WHERE vista = 'maintenance.vw_job_run_da_guardare'),
    'causa',
    '2. il catalogo dei presidi dichiara la colonna della causa'
);

-- ⚠️ columns_are confronta INSIEMI: la posizione si legge da attnum.
SELECT results_eq(
    $$SELECT a.attname::text COLLATE "default" || '/' || a.attnum
        FROM pg_attribute a
       WHERE a.attrelid = 'maintenance.vw_job_run_da_guardare'::regclass
         AND a.attname IN ('sqlstate', 'causa', 'ultimo_rosso_job_run_id')
       ORDER BY a.attnum$$,
    $$VALUES ('sqlstate/14'), ('causa/15'), ('ultimo_rosso_job_run_id/16')$$,
    '3. le tre colonne nuove stanno in coda, nell''ordine'
);

-- ============================================================
-- 4..9. La regola, ramo per ramo
-- ============================================================
SELECT is(
    (SELECT motivo || ' | ' || causa FROM maintenance.vw_job_run_da_guardare
      WHERE jobname = 'PGTAP-CAUSA-APPESA'),
    'presa e mai chiusa: il job e'' morto senza dire niente | AMBIENTE',
    '4. corsa appesa: AMBIENTE, anche se il processo dice PROGRAMMA'
);

SELECT is(
    (SELECT causa FROM maintenance.vw_job_run_da_guardare
      WHERE jobname = 'PGTAP-CAUSA-DISCO'),
    'AMBIENTE',
    '5. SQLSTATE 53100: AMBIENTE, anche se il processo dice PROGRAMMA'
);

SELECT is(
    (SELECT causa FROM maintenance.vw_job_run_da_guardare
      WHERE jobname = 'PGTAP-CAUSA-CONNESSIONE'),
    'AMBIENTE',
    '6. SQLSTATE 08006: AMBIENTE, anche se il codice dice CONFIGURAZIONE'
);

SELECT is(
    (SELECT causa FROM maintenance.vw_job_run_da_guardare
      WHERE jobname = 'PGTAP-CAUSA-CODICE'),
    'CONFIGURAZIONE',
    '7. il codice che dichiara la sua causa batte il processo'
);

SELECT is(
    (SELECT causa FROM maintenance.vw_job_run_da_guardare
      WHERE jobname = 'PGTAP-CAUSA-DAL-PROC-AMB'),
    'AMBIENTE',
    '8. codice non registrato: decide il processo (AMBIENTE)'
);

SELECT is(
    (SELECT causa FROM maintenance.vw_job_run_da_guardare
      WHERE jobname = 'PGTAP-CAUSA-DAL-PROC-PROG'),
    'PROGRAMMA',
    '9. codice non registrato: decide il processo (PROGRAMMA)'
);

-- ============================================================
-- 10..12. ⭐ Intermittenti e corse in corso
-- ============================================================
-- L'ultima corsa e' verde e non ha errore: guardando lei, la causa sarebbe
-- quella del processo (PROGRAMMA). Il rosso di ieri dice shutdown.
SELECT is(
    (SELECT causa FROM maintenance.vw_job_run_da_guardare
      WHERE jobname = 'PGTAP-CAUSA-INTERMITTENTE'),
    'AMBIENTE',
    '10. intermittente: la causa si legge dall''ultimo rosso, non dall''ultima corsa'
);

SELECT is(
    (SELECT v.ultimo_rosso_job_run_id = l.id
       FROM maintenance.vw_job_run_da_guardare v
       JOIN maintenance.job_run_log l
         ON l.jobname = v.jobname AND l.ok IS FALSE
      WHERE v.jobname = 'PGTAP-CAUSA-INTERMITTENTE'),
    true,
    '11. e la vista dice da quale corsa l''ha letta'
);

-- ⛔ Il difetto visto scrivendo la causa: una corsa partita cinque minuti fa
--   era detta «presa e mai chiusa», e con la causa sarebbe diventata AMBIENTE.
SELECT is(
    (SELECT motivo || ' | ' || causa FROM maintenance.vw_job_run_da_guardare
      WHERE jobname = 'PGTAP-CAUSA-IN-CORSO'),
    'in corso adesso, ma ha fallito di recente: intermittente | PROGRAMMA',
    '12. una corsa in corso con rossi recenti non e'' «presa e mai chiusa», e non e'' AMBIENTE'
);

-- ============================================================
-- 13..14. Sulla forma, su tutte le righe
-- ============================================================
SELECT is(
    (SELECT count(*) FROM maintenance.vw_job_run_da_guardare WHERE causa IS NULL),
    0::bigint,
    '13. nessuna riga della vista senza causa'
);

-- ⭐ E' cio' che tiene il digest fuori da «senza indicazione di chi agisce».
SELECT is(
    (SELECT count(*)
       FROM maintenance.vw_job_run_da_guardare v
      WHERE NOT EXISTS (SELECT 1 FROM dbops.presidi_cause pc
                         WHERE pc.vista = 'maintenance.vw_job_run_da_guardare'
                           AND pc.causa = v.causa)),
    0::bigint,
    '14. ogni causa che la vista produce ha chi la spegne in dbops.presidi_cause'
);

-- ============================================================
-- 15. ⭐ Il privilegio mancante e' dell'ambiente (rev 2026-10-16, D8)
-- ============================================================
SELECT is(
    (SELECT causa FROM maintenance.vw_job_run_da_guardare
      WHERE jobname = 'PGTAP-CAUSA-PRIVILEGIO'),
    'AMBIENTE',
    '15. SQLSTATE 42501 (privilegio mancante): AMBIENTE, anche se il processo dice PROGRAMMA'
);

SELECT * FROM finish();

ROLLBACK;
