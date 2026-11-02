-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture scrive su maintenance.job_run_log, che a
--   runtime scrivono solo i job (come titodb/postgres) e i command del backend.
--   Il ruolo applicativo ha SELECT e basta. Verificato cercando gli scrittori.
--
-- Test: maintenance.vw_job_run_da_guardare — il posto dove guardare
-- ChangeSet: 20260905-39 · Brief: brief-db-storicizzazione-bersagli-spariti §2.3
--
-- Elenco test (plan 6):
--  1) ⛔ un job la cui ULTIMA corsa e' fallita compare, e il motivo lo dice
--  2) ⭐ e passati sette giorni senza rossi ESCE DA SOLO
--  3) ⛔ una corsa aperta da tre ore compare: il job e' morto senza dire niente
--  4) ✅ una corsa aperta ADESSO non compare: la soglia esiste davvero
--  5) ⭐ INTERMITTENZA: ultima corsa verde, ma un rosso negli ultimi 7 giorni
--  6) ⚠️ la vista non ha row level security, ed e' una scelta
--
-- ────────────────────────────────────────────────────────────────
-- ⭐ IL TEST 2 E' LA RAGIONE DELLA FORMA DELLA VISTA.
--   Elencare tutti i rossi avrebbe reso la vista incapace di tornare vuota:
--   sarebbe cresciuta per sempre, e un elenco che non cala nessuno lo apre —
--   la lezione pagata con `dbops.vw_coda_lavori_da_guardare`, dove i quattro
--   lavori falliti da 45 giorni erano diventati rumore di fondo.
--   ⇒ Si guarda l'ULTIMA corsa di ogni job, e il rientro e' automatico.
--
-- ⛔ IL TEST 5 E' IL BUCO CHE QUELLA SCELTA APRIVA, e va letto col 2.
--   Con la sola «ultima corsa», un job che fallisce e passa, fallisce e passa,
--   sarebbe INVISIBILE — ed e' il guasto piu' insidioso di tutti.
--   ⚠️ Misurato il 2026-09-05, prima che il ramo esistesse:
--   `sync_auth_user_active` aveva 29 fallimenti in un giorno e l'ultima corsa
--   VERDE. La vista, cosi' com'era, non lo nominava.
--
-- ⚠️ Rev 2026-10-18 (brief-db-intermittente-e-verdetto-completo): la fixture
--   usava un processo VERO, apply_storicizza_weekly, che dal 20261018-01 e' un
--   verdetto completo — e per lui un rosso rientrato una volta non e' piu'
--   intermittente. Il test descriveva il processo a verdetto PARZIALE senza
--   dirlo: ora usa un processo suo, dichiarato a false. Il verdetto completo e'
--   provato in test-vw-job-run-da-guardare-verdetto-completo-v1.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(6);

-- ============================================================
-- Fixture: i casi, costruiti
-- ============================================================
-- ⚠️ `processo_codice` e' obbligatorio e ha una FK: si usa un processo di prova,
--   a verdetto parziale (rev 2026-10-18: la natura del processo decide il ramo
--   dell'intermittenza, e un processo vero la puo' cambiare). CODA: niente
--   sveglia, quindi niente colonne di accensione. I jobname portano un prefisso
--   che li rende inconfondibili.
INSERT INTO dbops.processi
    (id, codice, descrizione, classe, canale, causa_fallimento, corsa_verdetto_completo)
VALUES (9981, 'PGTAP-DA-GUARDARE', 'prova presidio dei job', 'MANUTENZIONE', 'CODA', 'PROGRAMMA', false);

DO $fixture$
DECLARE
    v_proc dbops.processi.codice%TYPE := 'PGTAP-DA-GUARDARE';
BEGIN
    -- 1) ultima corsa fallita
    INSERT INTO maintenance.job_run_log
        (jobname, stepname, processo_codice, origine, started_at, ended_at, ok, message, error_code)
    VALUES ('PGTAP-ROSSO', 's', v_proc, 'PGAGENT',
            now() - interval '10 minutes', now(), false, 'rotto', 'P0001');

    -- 2) fallita OTTO GIORNI FA e poi rientrata: fuori dalla finestra
    --    dell'intermittenza, quindi deve sparire davvero.
    INSERT INTO maintenance.job_run_log
        (jobname, stepname, processo_codice, origine, started_at, ended_at, ok, message, error_code)
    VALUES ('PGTAP-RIENTRATO', 's', v_proc, 'PGAGENT',
            now() - interval '8 days', now() - interval '8 days', false, 'rotto', 'P0001');

    -- 3) presa e mai chiusa (tre ore fa)
    INSERT INTO maintenance.job_run_log
        (jobname, stepname, processo_codice, origine, started_at)
    VALUES ('PGTAP-MAI-CHIUSA', 's', v_proc, 'PGAGENT', now() - interval '3 hours');

    -- 4) in corso adesso
    INSERT INTO maintenance.job_run_log
        (jobname, stepname, processo_codice, origine, started_at)
    VALUES ('PGTAP-IN-CORSO', 's', v_proc, 'PGAGENT', now());

    -- 5) intermittente: un rosso vecchio di due giorni, ultima corsa VERDE
    INSERT INTO maintenance.job_run_log
        (jobname, stepname, processo_codice, origine, started_at, ended_at, ok, message, error_code)
    VALUES ('PGTAP-INTERMITTENTE', 's', v_proc, 'PGAGENT',
            now() - interval '2 days', now() - interval '2 days', false, 'rotto', 'P0001');
    INSERT INTO maintenance.job_run_log
        (jobname, stepname, processo_codice, origine, started_at, ended_at, ok, message)
    VALUES ('PGTAP-INTERMITTENTE', 's', v_proc, 'PGAGENT',
            now() - interval '5 minutes', now(), true, 'done');
END
$fixture$;

-- ============================================================
-- 1..2. Compare, e poi esce da solo
-- ============================================================
SELECT is(
    (SELECT motivo FROM maintenance.vw_job_run_da_guardare
      WHERE jobname = 'PGTAP-ROSSO'),
    'l''ultima corsa e'' FALLITA',
    '1. un job la cui ultima corsa e'' fallita compare, e il motivo lo dice'
);

-- ⭐ La corsa buona arriva DOPO, e il job deve sparire senza che nessuno tocchi
--   niente: e' cio' che tiene la vista una lista di cose da fare.
-- ⚠️ E il rientro NON e' immediato, ed e' giusto cosi': il fallimento di questo
--   job e' di OTTO giorni fa, cioe' fuori dalla finestra dell'intermittenza. Un
--   job che ha fallito CINQUE MINUTI fa e adesso passa resta a video — ha appena
--   fallito, e dirlo sano sarebbe una bugia. Quel caso e' il test 5.
DO $rientro$
BEGIN
    INSERT INTO maintenance.job_run_log
        (jobname, stepname, processo_codice, origine, started_at, ended_at, ok, message)
    VALUES ('PGTAP-RIENTRATO', 's', 'apply_storicizza_weekly', 'PGAGENT',
            now() - interval '1 minute', now(), true, 'done');
END
$rientro$;

SELECT is_empty(
    $$SELECT jobname FROM maintenance.vw_job_run_da_guardare
       WHERE jobname = 'PGTAP-RIENTRATO'$$,
    '2. passati sette giorni senza rossi, il job esce da solo'
);

-- ============================================================
-- 3..4. La corsa che non finisce, e la soglia
-- ============================================================
-- ⛔ E' il caso che il canale fuori transazione NON copre: per scrivere il
--   verbale bisogna almeno arrivare al gestore d'eccezione. Un processo ucciso
--   di colpo lascia solo la riga d'avvio, aperta per sempre.
SELECT matches(
    (SELECT motivo FROM maintenance.vw_job_run_da_guardare
      WHERE jobname = 'PGTAP-MAI-CHIUSA'),
    'mai chiusa',
    '3. una corsa aperta da tre ore compare: il job e'' morto senza dire niente'
);

-- ⚠️ Senza questo test la soglia potrebbe essere zero e nessuno se ne
--   accorgerebbe: ogni job in esecuzione comparirebbe come guasto.
SELECT is_empty(
    $$SELECT jobname FROM maintenance.vw_job_run_da_guardare
       WHERE jobname = 'PGTAP-IN-CORSO'$$,
    '4. una corsa aperta adesso non compare: la soglia esiste davvero'
);

-- ============================================================
-- 5. ⭐ L'intermittenza
-- ============================================================
-- L'ultima corsa e' VERDE: guardando solo quella, questo job sarebbe sano.
SELECT is(
    (SELECT motivo || ' | rossi=' || falliti_ultimi_7_giorni::text
       FROM maintenance.vw_job_run_da_guardare
      WHERE jobname = 'PGTAP-INTERMITTENTE'),
    'ultima corsa OK, ma ha fallito di recente: intermittente | rossi=1',
    '5. un job che fallisce e passa compare lo stesso, e dice quante volte'
);

-- ============================================================
-- 6. ⚠️ Niente row level security, ed e' dichiarato
-- ============================================================
-- Un giro di manutenzione non appartiene a un'azienda: un perimetro qui non
-- vorrebbe dire niente. ⇒ Chi vede il pannello lo decide il backend, non il
-- database. Il test fissa la scelta, cosi' non la si cambia per distrazione.
SELECT is(
    (SELECT relrowsecurity FROM pg_class
      WHERE oid = 'maintenance.job_run_log'::regclass),
    false,
    '6. maintenance.job_run_log non ha row level security: la scelta e'' dichiarata'
);

SELECT * FROM finish();

ROLLBACK;
