-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture scrive su maintenance.job_run_log e su
--   dbops.processi, che a runtime scrivono solo i job (come titodb/postgres) e
--   le funzioni DEFINER del giornale. Il ruolo applicativo ha SELECT e basta.
--
-- Test: una corsa SALTATA non e' una corsa riuscita
--   maintenance.job_run_log.saltata · chk_job_run_log_saltata
--   script.fn_job_run_start · maintenance.fn_run_and_log · script.fn_job_run_end
--   maintenance.vw_job_run_da_guardare · dbops.vw_processi_programmazione
-- ChangeSet: 20261010-20 … -25 · Brief: brief-db-corsa-saltata-non-e-una-corsa §8
--
-- Elenco test (plan 11):
--  1) la colonna `saltata`: boolean, NOT NULL, default false
--  2) ⛔ il CHECK rifiuta una riga saltata CON un esito (la skip «riuscita» di prima)
--  3) ⛔ e una riga saltata APERTA (la skip «mai chiusa» di fn_run_and_log)
--  4) ✅ fn_job_run_start senza lock: corsa vera, saltata = false
--  5) ✅ fn_run_and_log senza lock: corsa vera, saltata = false, ok
--  6) ⛔ fn_job_run_end su una corsa saltata: E_JOB_RUN_SALTATA_NON_CHIUDIBILE
--  7) ⭐ vw_job_run_da_guardare: una corsa aperta da tre ore SEGUITA da una skip
--     resta «presa e mai chiusa» — il caso del §2.2
--  8) ⭐ vw_processi_programmazione: ultimo_esito e' quello della corsa VERA
--     (fallita), non della skip piu' recente
--  9) ⭐ vw_processi_programmazione: una skip nella tolleranza tiene OK il
--     timer — la sveglia e' viva (D3), niente TIMER_FERMO
-- 10) ⭐ il ramo skip VERO di fn_job_run_start: lock tenuto da un'altra sessione
-- 11) ⭐ il ramo skip VERO di fn_run_and_log: idem
--
-- ⚠️ I TEST 10-11 VOGLIONO UNA SECONDA SESSIONE. Un advisory lock e'
--   RIENTRANTE nella stessa sessione: pg_try_advisory_lock sul lock gia'
--   posseduto ritorna true, e il ramo skip non si raggiunge mai (per questo
--   test-job-run-attore.sql lo dichiarava «non collaudabile qui»). La seconda
--   sessione si apre con dblink sul DSN del canale di log
--   (myapp.dblink_log_connection) e TIENE il lock; la funzione, da qui, lo
--   trova occupato. Dove la sessione non si apre (su dev il DSN e' service= e
--   un non-superuser non lo apre) i due test vanno in skip CON il motivo.
-- ⭐ I test 6-9 non ne hanno bisogno: la riga saltata si COSTRUISCE con un
--   INSERT, nella forma che il CHECK ammette.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(11);

-- ============================================================
-- Fixture: tre processi di prova, uno per domanda
-- ============================================================
-- ⚠️ processo_codice e' obbligatorio sulle righe nuove
--   (chk_job_run_log_processo_dichiarato) e ha una FK: i processi si
--   costruiscono qui, separati, perche' le viste ragionano per processo e una
--   corsa scritta per un test non deve diventare «l'ultima» di un altro.
-- 20261016-20: un processo con una sveglia dichiara l'accensione.
INSERT INTO dbops.processi (id, codice, descrizione, classe, canale,
                            jobname_pgagent, tolleranza_minuti, segno_di_vita,
                            acceso_in_sviluppo, acceso_in_produzione, spegnibile, causa_fallimento, accendibile_in_produzione)
VALUES
    (9921, 'PGTAP-SALTATA-ATTORE', 'prova corsa saltata', 'MANUTENZIONE', 'COMMAND', NULL, 30, 'GIORNALE', true, true, true, 'PROGRAMMA', true),
    (9922, 'PGTAP-SALTATA-ESITO',  'prova corsa saltata', 'MANUTENZIONE', 'COMMAND', NULL, 30, 'GIORNALE', true, true, true, 'PROGRAMMA', true),
    (9923, 'PGTAP-SALTATA-TIMER',  'prova corsa saltata', 'MANUTENZIONE', 'COMMAND', NULL, 30, 'GIORNALE', true, true, true, 'PROGRAMMA', true);

-- ============================================================
-- 1. La colonna
-- ============================================================
SELECT is(
    (SELECT format_type(a.atttypid, a.atttypmod) || '/' || a.attnotnull::text || '/'
            || pg_get_expr(d.adbin, d.adrelid)
       FROM pg_attribute a
       LEFT JOIN pg_attrdef d ON d.adrelid = a.attrelid AND d.adnum = a.attnum
      WHERE a.attrelid = 'maintenance.job_run_log'::regclass
        AND a.attname = 'saltata' AND NOT a.attisdropped),
    'boolean/true/false',
    '1. job_run_log.saltata: boolean, NOT NULL, default false'
);

-- ============================================================
-- 2-3. Il CHECK: una riga saltata e' chiusa e senza esito
-- ============================================================
SELECT throws_like(
    $$INSERT INTO maintenance.job_run_log
          (jobname, processo_codice, origine, saltata, ended_at, ok, message)
      VALUES ('PGTAP-SALTATA-CHECK', 'PGTAP-SALTATA-ATTORE', 'COMMAND',
              TRUE, now(), TRUE, 'skip: another run in progress')$$,
    '%chk_job_run_log_saltata%',
    '2. una riga saltata con un esito si rifiuta: era la skip «riuscita» di prima'
);

SELECT throws_like(
    $$INSERT INTO maintenance.job_run_log
          (jobname, processo_codice, origine, saltata, ended_at, ok, message)
      VALUES ('PGTAP-SALTATA-CHECK', 'PGTAP-SALTATA-ATTORE', 'PGAGENT',
              TRUE, NULL, NULL, 'skip: another run in progress')$$,
    '%chk_job_run_log_saltata%',
    '3. una riga saltata aperta si rifiuta: era la skip «mai chiusa» di fn_run_and_log'
);

-- ============================================================
-- 4-5. Le corse vere restano corse vere
-- ============================================================
-- ⚠️ Chiamata e lettura in DUE istruzioni: la riga che la funzione inserisce
--   non e' visibile a una JOIN della stessa istruzione (stessa snapshot).
CREATE TEMP TABLE _t_start ON COMMIT DROP AS
SELECT 'vera'::text AS caso, s.id, s.acquired
  FROM script.fn_job_run_start(
           p_jobname         => 'PGTAP-SALTATA-START-VERA',
           p_origine         => 'COMMAND',
           p_processo_codice => 'PGTAP-SALTATA-ATTORE') s;

SELECT is(
    (SELECT l.saltata::text || '/' || s.acquired::text
       FROM _t_start s
       JOIN maintenance.job_run_log l ON l.id = s.id
      WHERE s.caso = 'vera'),
    'false/true',
    '4. fn_job_run_start senza lock: corsa vera (saltata = false, acquired)'
);

SELECT maintenance.fn_run_and_log(
    p_jobname         => 'PGTAP-SALTATA-RAL-VERA',
    p_stepname        => 'pgtap-step',
    p_sql             => 'SELECT 1',
    p_processo_codice => 'PGTAP-SALTATA-ATTORE');

SELECT is(
    (SELECT string_agg(l.saltata::text || '/' || l.ok::text, ',')
       FROM maintenance.job_run_log l
      WHERE l.jobname = 'PGTAP-SALTATA-RAL-VERA'),
    'false/true',
    '5. fn_run_and_log senza lock: corsa vera, riuscita (saltata = false, ok)'
);

-- ============================================================
-- 6. Una corsa saltata non si chiude
-- ============================================================
INSERT INTO maintenance.job_run_log
    (jobname, processo_codice, origine, started_at, saltata, ended_at, ok, message)
VALUES ('PGTAP-SALTATA-NON-CHIUDERE', 'PGTAP-SALTATA-ATTORE', 'COMMAND',
        now(), TRUE, now(), NULL, 'skip: another run in progress');

-- ⚠️ Il discriminante e' la FRASE (P0001 e' di tutti i codici di dominio), e
--   il pattern non attraversa i due segnaposto (id e processo).
SELECT throws_like(
    format('SELECT script.fn_job_run_end(%s, TRUE, %L)',
           (SELECT l.id FROM maintenance.job_run_log l
             WHERE l.jobname = 'PGTAP-SALTATA-NON-CHIUDERE'),
           'done'),
    '%stata saltata e non si può chiudere%',
    '6. fn_job_run_end su una corsa saltata: E_JOB_RUN_SALTATA_NON_CHIUDIBILE'
);

-- ============================================================
-- 7. La corsa appesa non sparisce dietro la skip (brief §2.2)
-- ============================================================
INSERT INTO maintenance.job_run_log
    (jobname, processo_codice, origine, started_at, saltata, ended_at, ok, message)
VALUES
    -- la corsa vera: presa tre ore fa e mai chiusa (processo bloccato)
    ('PGTAP-SALTATA-APPESA', 'PGTAP-SALTATA-ATTORE', 'COMMAND',
     now() - interval '3 hours', FALSE, NULL, NULL, NULL),
    -- la sveglia di un minuto fa, che ha trovato il lock occupato
    ('PGTAP-SALTATA-APPESA', 'PGTAP-SALTATA-ATTORE', 'COMMAND',
     now() - interval '1 minute', TRUE, now() - interval '1 minute', NULL,
     'skip: another run in progress');

SELECT is(
    (SELECT v.motivo FROM maintenance.vw_job_run_da_guardare v
      WHERE v.jobname = 'PGTAP-SALTATA-APPESA'),
    'presa e mai chiusa: il job e'' morto senza dire niente',
    '7. una corsa aperta da tre ore seguita da una skip resta «presa e mai chiusa»'
);

-- ============================================================
-- 8-9. Il panorama dei processi: l'esito e' del lavoro, la sveglia e' viva
-- ============================================================
INSERT INTO maintenance.job_run_log
    (jobname, processo_codice, origine, started_at, saltata, ended_at, ok, message)
VALUES
    -- 8: l'ultima corsa vera e' FALLITA, poi una skip
    ('PGTAP-SALTATA-ESITO', 'PGTAP-SALTATA-ESITO', 'COMMAND',
     now() - interval '5 minutes', FALSE, now() - interval '4 minutes', FALSE, 'rotto'),
    ('PGTAP-SALTATA-ESITO', 'PGTAP-SALTATA-ESITO', 'COMMAND',
     now() - interval '1 minute', TRUE, now() - interval '1 minute', NULL,
     'skip: another run in progress'),
    -- 9: l'ultima corsa vera e' piu' vecchia della tolleranza (30'), poi una
    --    skip dentro la tolleranza
    ('PGTAP-SALTATA-TIMER', 'PGTAP-SALTATA-TIMER', 'COMMAND',
     now() - interval '2 hours', FALSE, now() - interval '2 hours', TRUE, 'done'),
    ('PGTAP-SALTATA-TIMER', 'PGTAP-SALTATA-TIMER', 'COMMAND',
     now() - interval '1 minute', TRUE, now() - interval '1 minute', NULL,
     'skip: another run in progress');

SELECT is(
    (SELECT v.ultimo_esito FROM dbops.vw_processi_programmazione v
      WHERE v.processo_codice = 'PGTAP-SALTATA-ESITO'),
    FALSE,
    '8. ultimo_esito e'' quello dell''ultima corsa VERA (fallita), non della skip'
);

SELECT is(
    (SELECT v.stato || '/' || COALESCE(v.causa, '-')
       FROM dbops.vw_processi_programmazione v
      WHERE v.processo_codice = 'PGTAP-SALTATA-TIMER'),
    'OK/-',
    '9. una skip nella tolleranza tiene OK il timer: la sveglia e'' viva (D3)'
);

-- ============================================================
-- 10-11. I rami skip VERI: il lock lo tiene un'altra sessione
-- ============================================================
CREATE TEMP TABLE _t_altra ON COMMIT DROP AS
SELECT false AS connessa, ''::text AS motivo;

DO $altra$
DECLARE
    v_dsn text := current_setting('myapp.dblink_log_connection', true);
BEGIN
    IF v_dsn IS NULL OR btrim(v_dsn) = '' THEN
        UPDATE _t_altra SET motivo = 'myapp.dblink_log_connection non impostata: '
                                  || 'nessun DSN con cui aprire la seconda sessione';
        RETURN;
    END IF;
    BEGIN
        PERFORM dblink_connect('pgtap_saltata', v_dsn);
        -- ⚠️ dblink_exec rifiuta un'istruzione che restituisce righe: il lock
        --   si prende dentro un DO. Lock di SESSIONE: resta finche' la
        --   connessione vive, cioe' fino alla dblink_disconnect in fondo.
        PERFORM dblink_exec('pgtap_saltata',
            'DO $l$ BEGIN '
            || 'PERFORM pg_advisory_lock(hashtext(''zeroerp:job_run_log''), hashtext(''PGTAP-SALTATA-CORSIA'')); '
            || 'PERFORM pg_advisory_lock(hashtextextended(''PGTAP-SALTATA-RAL'', 0)); '
            || 'END $l$');
    EXCEPTION WHEN OTHERS THEN
        UPDATE _t_altra SET motivo = 'seconda sessione non costruibile (' || SQLSTATE || '): '
                                  || SQLERRM
                                  || ' — su dev il DSN e'' service= e un non-superuser non lo apre';
        RETURN;
    END;
    UPDATE _t_altra SET connessa = true;
END $altra$;

DO $start$
BEGIN
    IF (SELECT connessa FROM _t_altra) THEN
        INSERT INTO _t_start (caso, id, acquired)
        SELECT 'skip', s.id, s.acquired
          FROM script.fn_job_run_start(
                   p_jobname         => 'PGTAP-SALTATA-START-SKIP',
                   p_origine         => 'COMMAND',
                   p_lock_key        => 'PGTAP-SALTATA-CORSIA',
                   p_processo_codice => 'PGTAP-SALTATA-ATTORE') s;
    END IF;
END $start$;

SELECT CASE WHEN (SELECT connessa FROM _t_altra) THEN
    is(
        (SELECT s.acquired::text || '/' || l.saltata::text || '/' || (l.ok IS NULL)::text
                || '/' || (l.ended_at IS NOT NULL)::text
           FROM _t_start s
           JOIN maintenance.job_run_log l ON l.id = s.id
          WHERE s.caso = 'skip'),
        'false/true/true/true',
        '10. fn_job_run_start col lock occupato: acquired = false, riga saltata, chiusa, senza esito'
    )
ELSE
    skip('10. ' || (SELECT motivo FROM _t_altra))
END;

DO $ral$
BEGIN
    IF (SELECT connessa FROM _t_altra) THEN
        PERFORM maintenance.fn_run_and_log(
            p_jobname         => 'PGTAP-SALTATA-RAL-SKIP',
            p_stepname        => 'pgtap-step',
            p_sql             => 'SELECT 1',
            p_lock_key        => hashtextextended('PGTAP-SALTATA-RAL', 0),
            p_processo_codice => 'PGTAP-SALTATA-ATTORE');
    END IF;
END $ral$;

SELECT CASE WHEN (SELECT connessa FROM _t_altra) THEN
    is(
        (SELECT string_agg(l.saltata::text || '/' || (l.ok IS NULL)::text || '/'
                           || (l.ended_at IS NOT NULL)::text, ',')
           FROM maintenance.job_run_log l
          WHERE l.jobname = 'PGTAP-SALTATA-RAL-SKIP'),
        'true/true/true',
        '11. fn_run_and_log col lock occupato: una riga sola, saltata, senza esito, CHIUSA'
    )
ELSE
    skip('11. ' || (SELECT motivo FROM _t_altra))
END;

-- La connessione altrui NON e' transazionale: si chiude a mano, e chiudendola
-- il suo lock di sessione cade.
SELECT CASE WHEN connessa THEN dblink_disconnect('pgtap_saltata') END FROM _t_altra;

SELECT * FROM finish();

ROLLBACK;
