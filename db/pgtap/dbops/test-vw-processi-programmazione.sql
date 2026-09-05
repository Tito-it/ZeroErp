-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- pgtap-runner: owner
-- pgtap-runner-motivo: per costruire il caso «e' girato e non l'ha detto» il
--   test deve TOGLIERE righe da maintenance.job_run_log (in transazione, e poi
--   annullate). E' una scrittura che il ruolo applicativo non fa e non deve
--   fare: quel giornale lo scrivono i job.
--
-- Test: dbops.vw_processi_programmazione — la programmazione e l'ultima corsa
-- ChangeSet: 20260906-03 / -04 / -05 / -06
--
-- Elenco test (plan 7):
--  1) la colonna `jobname_pgagent` c'e', ed e' nullable
--  2) ⛔ due processi non possono dichiarare lo stesso job
--  3) ⚠️ un nome vuoto non e' «nessun job»
--  4) ⭐ la funzione su pgAgent torna ZERO righe dove non sa: non esplode
--  5) ⭐ il panorama nomina GIRA_E_NON_REGISTRA su un caso COSTRUITO
--  6) ✅ e NON lo nomina quando le due date coincidono
--  7) ⚠️ COMMAND e CODA sono FUORI_PORTATA, non OK
--
-- ────────────────────────────────────────────────────────────────
-- ⭐ IL TEST 5 E' LA RAGIONE PER CUI LA VISTA ESISTE.
--   «pgAgent dice che e' girato, il giornale non lo sa» e' la firma di un
--   lavoro che muore prima di riuscire a raccontarlo — cioe' di R-12, il job
--   morto per sei mesi con l'ultimo verdetto agli atti a «done».
--   ⚠️ Il caso si COSTRUISCE togliendo le righe di giornale di un job sano: e'
--   l'unico modo, perche' `pgagent.pga_job` e' una tabella di un'estensione e
--   non si semina.
--
-- ⛔ IL TEST 7 TIENE ONESTA LA VISTA. Di otto processi su ventidue il database
--   NON PUO' sapere se stanno partendo: la loro sveglia vive in crontab o nel
--   backend. Dire `OK` sarebbe una bugia — e una bugia rassicurante e' il modo
--   piu' efficace di non far guardare piu' nessuno.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(7);

-- ============================================================
-- 1..3. La colonna e i suoi cancelli
-- ============================================================
-- ⚠️ Nullable, ed e' un dato: `NULL` significa «questo processo non lo sveglia
--   pgAgent», che per un COMMAND e' la verita'.
SELECT col_is_null('dbops', 'processi', 'jobname_pgagent',
    '1. jobname_pgagent e'' nullable: NULL vuol dire «non lo sveglia pgAgent»');

-- ⛔ Due processi sullo stesso job renderebbero ambiguo di chi e' la corsa che
--   quel job produce.
SELECT throws_ok(
    $$INSERT INTO dbops.processi (id, codice, descrizione, classe, canale, jobname_pgagent)
      VALUES (9701, 'PGTAP-JOB-DOPPIO', 'prova', 'MANUTENZIONE', 'PGAGENT',
              (SELECT jobname_pgagent FROM dbops.processi
                WHERE jobname_pgagent IS NOT NULL ORDER BY codice LIMIT 1))$$,
    '23505',
    NULL,
    '2. due processi non possono dichiarare lo stesso job pgAgent'
);

-- ⚠️ Una stringa vuota passerebbe per un legame dichiarato e non lo e'.
SELECT throws_ok(
    $$INSERT INTO dbops.processi (id, codice, descrizione, classe, canale, jobname_pgagent)
      VALUES (9702, 'PGTAP-JOB-VUOTO', 'prova', 'MANUTENZIONE', 'PGAGENT', '   ')$$,
    '23514',
    NULL,
    '3. un nome vuoto non e'' «nessun job»: si rifiuta'
);

-- ============================================================
-- 4. ⭐ La funzione non esplode dove non sa
-- ============================================================
-- ⛔ E' il motivo per cui e' una funzione plpgsql e non un JOIN: dove
--   l'estensione manca — in CI `85_pgagent` e' MARK_RAN — una vista che nomina
--   `pgagent.*` non si creerebbe affatto. Qui la risposta e' «zero righe», che
--   in un LEFT JOIN LATERAL diventa una colonna vuota.
SELECT is_empty(
    $$SELECT abilitato FROM dbops.fn_get_pgagent_job_stato('PGTAP-JOB-CHE-NON-ESISTE')$$,
    '4. su un job sconosciuto la funzione torna zero righe, non un errore'
);

-- ============================================================
-- 5..6. ⭐ Il confronto, costruito
-- ============================================================
-- Si sceglie un processo che oggi risulta sano, gli si tolgono le righe di
-- giornale, e si guarda che il panorama se ne accorga.
-- ⚠️ Se pgAgent non c'e' (CI) il caso non e' costruibile: si dichiara e si
--   salta, invece di fingere un verde.
DO $confronto$
DECLARE
    v_proc dbops.processi.codice%TYPE;
BEGIN
    SELECT processo_codice INTO v_proc
      FROM dbops.vw_processi_programmazione
     WHERE stato = 'OK'
     ORDER BY processo_codice
     LIMIT 1;

    PERFORM set_config('pgtap.proc_sano', COALESCE(v_proc, ''), true);
    IF v_proc IS NULL THEN
        RETURN;
    END IF;

    -- Prima: deve risultare sano.
    PERFORM set_config('pgtap.stato_prima',
        (SELECT stato FROM dbops.vw_processi_programmazione
          WHERE processo_codice = v_proc), true);

    -- ⭐ Gli si toglie la memoria: pgAgent continua a dire che e' girato, il
    --   giornale non lo sa piu'. E' esattamente cio' che succedeva quando il
    --   RAISE annullava il verbale.
    DELETE FROM maintenance.job_run_log
     WHERE processo_codice = v_proc OR jobname = v_proc;

    PERFORM set_config('pgtap.stato_dopo',
        (SELECT stato FROM dbops.vw_processi_programmazione
          WHERE processo_codice = v_proc), true);
END
$confronto$;

SELECT CASE
    WHEN NULLIF(current_setting('pgtap.proc_sano', true), '') IS NULL
        THEN skip('5. nessun processo sano su questo database (pgAgent assente?)', 1)
    ELSE is(
        current_setting('pgtap.stato_dopo', true),
        'GIRA_E_NON_REGISTRA',
        '5. tolte le righe di giornale, il panorama dice «e'' girato e non l''ha detto»'
    )
END;

-- ⛔ Il verso che rende il 5 una misura: senza, un panorama che gridasse sempre
--   passerebbe il test precedente a pieni voti.
SELECT CASE
    WHEN NULLIF(current_setting('pgtap.proc_sano', true), '') IS NULL
        THEN skip('6. nessun processo sano su questo database (pgAgent assente?)', 1)
    ELSE is(
        current_setting('pgtap.stato_prima', true),
        'OK',
        '6. e con le due date che coincidono lo stesso processo era OK'
    )
END;

-- ============================================================
-- 7. ⚠️ Cio' che non e' misurabile lo dice
-- ============================================================
-- ⛔ `FUORI_PORTATA` non significa «tutto bene»: significa che la sveglia di
--   quel processo vive fuori dal database. Dire OK sarebbe una bugia
--   rassicurante, ed e' il modo piu' efficace di non far guardare piu' nessuno.
SELECT is_empty(
    $$SELECT processo_codice FROM dbops.vw_processi_programmazione
       WHERE canale IN ('COMMAND', 'CODA')
         AND stato <> 'FUORI_PORTATA'$$,
    '7. i processi che pgAgent non sveglia sono FUORI_PORTATA, mai OK'
);

SELECT * FROM finish();

ROLLBACK;
