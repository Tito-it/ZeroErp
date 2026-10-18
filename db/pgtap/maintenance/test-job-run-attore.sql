-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture semina su dbops.processi, che a runtime NON
--   scrive nessuno (catalogo popolato dal seed Liquibase, e il ruolo
--   applicativo ha SELECT-only per 90_end/20260904-15). Stessa forma gia'
--   accettata per ui.dashboard_definizione. Verificato cercando gli scrittori.
--
-- Test: l'attore su maintenance.job_run_log
--       script.fn_job_run_start, maintenance.fn_run_and_log
-- Brief: brief-db-processi-automatici-identita-e-perimetro §3
--
-- Elenco test (plan 12):
--  1) job_run_log ha la colonna processo_codice
--  2) job_run_log ha la colonna auth_user_id
--  3) la FK respinge un codice di processo non registrato
--  4) fn_job_run_start scrive l'attore sul run
--  5) fn_job_run_start sul ramo «skip» — SKIP dichiarato (serve una 2a sessione)
--  6) fn_run_and_log gira senza che il chiamante passi il codice
--  7) fn_run_and_log DERIVA il codice dal jobname
--  8) fn_run_and_log NON inventa: un jobname sconosciuto resta senza attore
--  9) nessun overload residuo di fn_job_run_start
-- 10) nessun overload residuo di fn_run_and_log
-- 11) vw_run_senza_attore elenca il job la cui ultima corsa e' senza attore
-- 12) fn_job_run_start non e' aperta a PUBLIC dopo il DROP+CREATE
--
-- Scopo:
--  - fissare che l'attore arriva sul giornale per ENTRAMBI i canali;
--  - fissare che la derivazione dal jobname copre i job pgAgent e NON maschera
--    il caso non derivabile (che resta NULL e finisce nel presidio);
--  - fissare che dopo il DROP non e' rimasta la firma vecchia: e' il difetto
--    che si vedrebbe solo come «l'attore non arriva mai», mesi dopo;
--  - fissare la POSTURA DEI PRIVILEGI dopo un DROP+CREATE (test 12), che e'
--    la regressione realmente accaduta il 2026-09-04.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(12);

-- ============================================================
-- 1..2. Le colonne
-- ============================================================
SELECT has_column('maintenance', 'job_run_log', 'processo_codice',
                  'job_run_log ha la colonna processo_codice (l''attore)');
SELECT has_column('maintenance', 'job_run_log', 'auth_user_id',
                  'job_run_log ha la colonna auth_user_id');

-- ============================================================
-- 3. La FK e' un cancello, non un referto
-- ============================================================
-- Un processo non dichiarato non deve poter nemmeno registrare un run: se
-- passasse, lo scopriremmo da una vista il giorno dopo invece che subito.
SELECT throws_ok(
    $$INSERT INTO maintenance.job_run_log (jobname, processo_codice)
      VALUES ('pgtap-fk', 'PGTAP-PROCESSO-INESISTENTE')$$,
    '23503',
    NULL,
    'la FK respinge un codice di processo non registrato'
);

-- ============================================================
-- Fixture: un processo di prova, registrato
-- ============================================================
DO $fixture$
DECLARE
    v_id dbops.processi.id%TYPE := 9201;
BEGIN
    -- 20261016-20: un processo con una sveglia dichiara l'accensione.
    INSERT INTO dbops.processi (id, codice, descrizione, classe, canale,
                                acceso_in_sviluppo, acceso_in_produzione, spegnibile, causa_fallimento, accendibile_in_produzione)
    VALUES (v_id, 'PGTAP-PROC-DERIVA',
            'processo di prova per la derivazione dell''attore',
            'MANUTENZIONE', 'PGAGENT', true, true, true, 'PROGRAMMA', true);
END
$fixture$;

-- ============================================================
-- 4. Il canale headless scrive l'attore
-- ============================================================
DO $headless$
DECLARE
    v_run_id maintenance.job_run_log.id%TYPE;
BEGIN
    SELECT s.id INTO v_run_id
      FROM script.fn_job_run_start(
               p_jobname         => 'PGTAP-PROC-DERIVA',
               p_origine         => 'COMMAND',
               p_processo_codice => 'PGTAP-PROC-DERIVA',
               p_auth_user_id    => 4242) AS s;
    -- L'id serve solo a non lasciare la riga anonima nelle asserzioni sotto.
    PERFORM set_config('pgtap.run_id', v_run_id::text, true);
END
$headless$;

SELECT is(
    (SELECT jrl.processo_codice
       FROM maintenance.job_run_log jrl
      WHERE jrl.id = current_setting('pgtap.run_id')::bigint),
    'PGTAP-PROC-DERIVA',
    'fn_job_run_start scrive l''attore sul run'
);

-- ============================================================
-- 5. Il ramo «skip» — dichiarato, non finto
-- ============================================================
-- ⚠️ Non collaudabile qui, e la ragione e' strutturale: un advisory lock e'
--   RIENTRANTE nella stessa sessione (pg_try_advisory_lock sullo stesso lock
--   gia' posseduto ritorna true). Servirebbe una seconda connessione, che una
--   transazione pgTAP non ha. Fingere il caso con un lock diverso proverebbe
--   un altro ramo, non questo.
--   ⇒ Il ramo scrive l'attore (rev 2026-09-04) e resta coperto dalla lettura
--     del codice, non da questo file. Dichiarato per non contarlo fra i verdi.
SELECT skip('ramo «skip» di fn_job_run_start: serve una seconda sessione '
            '(advisory lock rientrante nella stessa)', 1);

-- ============================================================
-- 6..8. La derivazione dal jobname, e il suo limite
-- ============================================================
-- I 12 job pgAgent passano p_jobname := '<codice>' dai wrapper proc_*_job:
-- se la derivazione funziona, diventano conformi senza toccare 85_pgagent.
SELECT lives_ok(
    $$SELECT maintenance.fn_run_and_log(
          p_jobname  => 'PGTAP-PROC-DERIVA',
          p_stepname => 'pgtap-step',
          p_sql      => 'SELECT 1')$$,
    'fn_run_and_log gira senza che il chiamante passi il codice'
);

SELECT is(
    (SELECT jrl.processo_codice
       FROM maintenance.job_run_log jrl
      WHERE jrl.jobname = 'PGTAP-PROC-DERIVA'
        AND jrl.stepname = 'pgtap-step'),
    'PGTAP-PROC-DERIVA',
    'fn_run_and_log deriva l''attore dal jobname'
);

-- ⭐ E il contro-caso: la derivazione NON deve inventare. Un jobname che non
--   corrisponde a nessun processo non riceve un attore a caso.
--
-- ⛔ 2026-09-05 — LA CONSEGUENZA E' CAMBIATA, il principio no. Fino a DB-5 un
--   jobname sconosciuto lasciava l'attore NULL: la riga entrava MUTA e finiva
--   nel presidio. Adesso `chk_job_run_log_processo_dichiarato` la rifiuta,
--   quindi **il job si ferma**.
--   ⭐ E' la scelta, non un effetto collaterale: un processo che non sa dire chi
--     e' non deve girare, e fallire rumorosamente e' meglio che lasciare una
--     riga muta — che e' il difetto per cui questo cantiere esiste.
--   ⚠️ Il principio resta identico: la funzione non INVENTA un attore. Cambia
--     che adesso non lo fa passare nemmeno vuoto.
SELECT throws_ok(
    $$SELECT maintenance.fn_run_and_log(
          p_jobname  => 'PGTAP-JOBNAME-SCONOSCIUTO',
          p_stepname => 'pgtap-step',
          p_sql      => 'SELECT 1')$$,
    '23514',
    NULL,
    'fn_run_and_log non inventa: un jobname sconosciuto non entra affatto'
);

-- ============================================================
-- 9..10. Nessun overload residuo
-- ============================================================
-- ⛔ E' il difetto piu' silenzioso di tutta la fase: se la firma vecchia
--   sopravvivesse, i chiamanti non aggiornati continuerebbero a risolverla e
--   l'attore non arriverebbe MAI — senza nessun errore, e senza che la vista
--   di presidio sappia distinguerlo da un job non ancora migrato.
SELECT is(
    (SELECT count(*)::int
       FROM pg_catalog.pg_proc p
       JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'script' AND p.proname = 'fn_job_run_start'),
    1,
    'script.fn_job_run_start ha una sola firma (nessun overload residuo)'
);

SELECT is(
    (SELECT count(*)::int
       FROM pg_catalog.pg_proc p
       JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'maintenance' AND p.proname = 'fn_run_and_log'),
    1,
    'maintenance.fn_run_and_log ha una sola firma (nessun overload residuo)'
);

-- ============================================================
-- 11. ⭐ Che cosa E' DIVENTATO il presidio, dopo DB-5
-- ============================================================
-- ⛔ 2026-09-05 — QUESTO TEST NON POTEVA PIU' ESSERE VERDE, e la ragione vale
--   piu' del test. Chiedeva che la vista contasse un run rimasto senza attore.
--   Dopo `chk_job_run_log_processo_dichiarato` **un run senza attore non puo'
--   piu' nascere**: l'INSERT viene rifiutato (test 8).
--
-- ⇒ La vista ha cambiato natura, e va detto perche' nessuno la legga piu' come
--   prima. Non e' piu' «chi non si e' ancora dichiarato», che era una domanda
--   sul presente: e' **il residuo storico che non si dichiarera' mai**, scritto
--   prima che la colonna esistesse. ⭐ Una volta che quei job saranno girati di
--   nuovo, si svuota — e resta vuota per costruzione, non per disciplina.
--
-- ⚠️ Quindi il test giusto non e' «la vista vede una riga nuova» — non ce ne
--   saranno piu' — ma «la vista guarda l'ULTIMA corsa». E' la proprieta' che le
--   permette di arrivare a zero: contando tutte le righe storiche non sarebbe
--   mai stata vuota, e un presidio che non puo' arrivare a zero e' rumore.
SELECT is_empty(
    $$SELECT v.jobname
        FROM dbops.vw_run_senza_attore v
        JOIN maintenance.job_run_log l ON l.jobname = v.jobname
       WHERE l.processo_codice IS NOT NULL
         AND l.started_at > v.ultimo_run$$,
    'vw_run_senza_attore guarda l''ULTIMA corsa: un job che si e'' dichiarato dopo non compare'
);

-- ============================================================
-- 12. La postura dei privilegi sopravvive al DROP+CREATE
-- ============================================================
-- ⛔ E' la regressione realmente accaduta scrivendo questa fase, il 2026-09-04.
--   `DROP FUNCTION` cancella anche l'ACL: la CREATE successiva riparte dal
--   default di PostgreSQL, che per le funzioni e' EXECUTE a PUBLIC. Il REVOKE
--   del 20260618-02 e' sparito insieme alla firma vecchia, e una funzione
--   SECURITY DEFINER e' rimasta aperta a chiunque (corretta da 20260904-21).
--   ⚠️ L'ha trovata un pgTAP di un'altra area, non questo file. Ora sta anche
--   qui, dove il difetto nasce: chi tocca di nuovo la firma se ne accorge nel
--   test della propria fase.
SELECT ok(
    NOT has_function_privilege('public',
        (SELECT p.oid
           FROM pg_catalog.pg_proc p
           JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
          WHERE n.nspname = 'script' AND p.proname = 'fn_job_run_start'),
        'EXECUTE'),
    'fn_job_run_start: PUBLIC resta senza EXECUTE dopo il DROP+CREATE'
);

SELECT * FROM finish();

ROLLBACK;
