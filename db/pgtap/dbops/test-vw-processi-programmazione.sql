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
-- ChangeSet: 20260906-03 / -04 / -05 / -06 · 20260907-01
--
-- Elenco test (plan 10):
--  1) la colonna `jobname_pgagent` c'e', ed e' nullable
--  2) ⛔ due processi non possono dichiarare lo stesso job
--  3) ⚠️ un nome vuoto non e' «nessun job»
--  4) ⭐ la funzione su pgAgent torna ZERO righe dove non sa: non esplode
--  5) ⭐ il panorama nomina GIRA_E_NON_REGISTRA su un caso COSTRUITO
--  6) ✅ e NON lo nomina quando le due date coincidono
--  7) ⚠️ i COMMAND sono FUORI_PORTATA, non OK
--  8) ⭐ e i CODA sono SU_RICHIESTA: una cadenza non ce l'hanno affatto
--  9) ⛔ ogni canale ammesso dal CHECK ha un verdetto DICHIARATO qui
-- 10) ⛔ e la vista lo classifica come il verdetto dice
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
-- ⛔ I TEST 7 E 8 TENGONO ONESTA LA VISTA, e sono DUE perche' dicono cose
--   diverse. Dire `OK` su un processo che non si vede sarebbe una bugia, e una
--   bugia rassicurante e' il modo piu' efficace di non far guardare piu'
--   nessuno. Ma i due modi di «non vedere» non sono lo stesso: di un COMMAND il
--   database non sa (e chi sa e' il backend), mentre un CODA una cadenza non ce
--   l'ha proprio. ⚠️ Una parola sola per due fatti faceva contare insieme cose
--   diverse — brief-db-sveglia-dei-processi §8.6.
--
-- ⛔ IL TEST 9 GUARDA UN VOCABOLARIO CHIUSO SCRITTO IN DUE POSTI: i canali li
--   dichiara `chk_processi_canale`, che cosa farne lo dichiara il `CASE` della
--   vista. L'elenco lo legge da `pg_constraint`; i verdetti stanno qui, ed e'
--   voluto: un canale nuovo non ha un verdetto, quindi il test lo NOMINA invece
--   di dargli un default silenzioso.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(10);

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
       WHERE canale = 'COMMAND'
         AND stato <> 'FUORI_PORTATA'$$,
    '7. i COMMAND, che sveglia systemd, sono FUORI_PORTATA — mai OK'
);

-- ============================================================
-- 8. ⭐ E i CODA sono un'altra cosa, non la stessa
-- ============================================================
-- ⛔ Fino al 20260907-01 stavano sotto la stessa parola, e «otto scoperti»
--   contava insieme due fatti opposti:
--     FUORI_PORTATA  una cadenza ESISTE, ma vive fuori: e' un limite di VISTA,
--                    e dal 2026-09-06 la presidia il backend;
--     SU_RICHIESTA   una cadenza NON esiste: lo sveglia una persona. E' la
--                    natura del processo, e non cambiera' mai.
-- ⚠️ Il test 7 da solo passerebbe anche se `SU_RICHIESTA` non esistesse: dice
--   solo che i COMMAND non sono OK. Serve il verso che nomina l'altro stato.
SELECT is_empty(
    $$SELECT processo_codice FROM dbops.vw_processi_programmazione
       WHERE canale = 'CODA'
         AND stato <> 'SU_RICHIESTA'$$,
    '8. i CODA li sveglia una persona: SU_RICHIESTA, non FUORI_PORTATA'
);

-- ============================================================
-- 9. ⛔ IL VOCABOLARIO DEI CANALI E' CHIUSO, E STA IN DUE POSTI
-- ============================================================
-- `chk_processi_canale` dice quali canali esistono; il `CASE` della vista dice
-- che cosa farne. Sono due elenchi, e oggi tornano per coincidenza: sia i
-- PGAGENT sia l'unico CODA_AUTOMATICA portano un jobname, quindi nessuno cade
-- dove non dovrebbe.
--
-- ⭐ L'ELENCO DEI CANALI NON E' SCRITTO QUI: si legge da `pg_constraint`. Le
--   ATTESE si', ed e' il punto — un canale nuovo non ha un'attesa, quindi il
--   test lo NOMINA invece di dargli un default silenzioso. E' la forma «il
--   presidio dichiara i suoi debiti»: l'invariante non e' «vuoto», e'
--   «nessun canale NON DICHIARATO».
--
-- ⚠️ Il caso costruito e' `jobname_pgagent = NULL`, cioe' la forma di un canale
--   la cui sveglia NON e' pgAgent. E' l'unico modo in cui un canale nuovo
--   arriverebbe davvero alla vista.
DO $canali$
DECLARE
    -- ⚠️ `true` su PGAGENT e CODA_AUTOMATICA non e' una svista: senza un job
    --   dichiarato NESSUNO sa chi li sveglia, e guardarli e' giusto. Su
    --   CODA_AUTOMATICA e' un DEBITO DICHIARATO — oggi quel canale passa da un
    --   job pgAgent, e il giorno in cui lo accodera' un trigger la risposta
    --   andra' ripensata QUI, con questo test rosso davanti.
    v_attese CONSTANT jsonb := jsonb_build_object(
        'PGAGENT',         true,
        'COMMAND',         false,
        'CODA',            false,
        'CODA_AUTOMATICA', true
    );
    v_canale       text;
    v_ottenuto     boolean;
    v_id           integer := 9800;
    v_non_dichiarati text[] := '{}';
    v_dissenzienti   text[] := '{}';
BEGIN
    FOR v_canale IN
        SELECT DISTINCT m[1]
          FROM pg_constraint c,
               LATERAL regexp_matches(pg_get_constraintdef(c.oid),
                                      '''([A-Z_]+)''::text', 'g') m
         WHERE c.conname = 'chk_processi_canale'
         ORDER BY 1
    LOOP
        IF NOT v_attese ? v_canale THEN
            v_non_dichiarati := v_non_dichiarati || v_canale;
            CONTINUE;
        END IF;

        v_id := v_id + 1;
        INSERT INTO dbops.processi (id, codice, descrizione, classe, canale,
                                    jobname_pgagent)
        VALUES (v_id, 'PGTAP-CANALE-' || v_canale, 'prova vocabolario chiuso',
                'MANUTENZIONE', v_canale, NULL);

        SELECT da_guardare INTO v_ottenuto
          FROM dbops.vw_processi_programmazione
         WHERE processo_codice = 'PGTAP-CANALE-' || v_canale;

        IF v_ottenuto IS DISTINCT FROM (v_attese ->> v_canale)::boolean THEN
            v_dissenzienti := v_dissenzienti
                || (v_canale || ': atteso ' || (v_attese ->> v_canale)
                    || ', ottenuto ' || COALESCE(v_ottenuto::text, 'NULL'));
        END IF;
    END LOOP;

    -- ⛔ Si tolgono subito: i test che seguono non devono vedere processi che
    --   non esistono.
    DELETE FROM dbops.processi WHERE codice LIKE 'PGTAP-CANALE-%';

    PERFORM set_config('pgtap.canali_non_dichiarati',
                       array_to_string(v_non_dichiarati, ', '), true);
    PERFORM set_config('pgtap.canali_dissenzienti',
                       array_to_string(v_dissenzienti, '; '), true);
END
$canali$;

SELECT is(
    current_setting('pgtap.canali_non_dichiarati', true), '',
    '9. ogni canale ammesso dal CHECK ha un verdetto dichiarato in questo test'
);

SELECT is(
    current_setting('pgtap.canali_dissenzienti', true), '',
    '10. e la vista lo classifica come il verdetto dichiarato dice'
);

SELECT * FROM finish();

ROLLBACK;
