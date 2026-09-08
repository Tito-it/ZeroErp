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
-- ChangeSet: 20260906-03 / -04 / -05 / -06 · 20260907-01 / -06
--
-- Elenco test (plan 13):
--  1) la colonna `jobname_pgagent` c'e', ed e' nullable
--  2) ⛔ due processi non possono dichiarare lo stesso job
--  3) ⚠️ un nome vuoto non e' «nessun job»
--  4) ⭐ la funzione su pgAgent torna ZERO righe dove non sa: non esplode
--  5) ⭐ tolto il giornale, il panorama nomina GIRA_E_NON_REGISTRA — costruito
--  6) ✅ e rimessa una corsa di pgAgent torna OK — costruito anche questo
--  7) ⚠️ i COMMAND sono FUORI_PORTATA, non OK
--  8) ⭐ e i CODA sono SU_RICHIESTA: una cadenza non ce l'hanno affatto
--  9) ⛔ ogni canale ammesso dal CHECK ha un verdetto DICHIARATO qui
-- 10) ⛔ e la vista lo classifica come il verdetto dice
-- 11) ⛔ una corsa di un attore che NON e' pgAgent non spegne il rilevatore
-- 12) ⛔ ogni origine ammessa dal CHECK ha un verdetto DICHIARATO qui
-- 13) ⛔ e la vista la tratta come il verdetto dice
--
-- ────────────────────────────────────────────────────────────────
-- ⭐ IL TEST 5 E' LA RAGIONE PER CUI LA VISTA ESISTE.
--   «pgAgent dice che e' girato, il giornale non lo sa» e' la firma di un
--   lavoro che muore prima di riuscire a raccontarlo — cioe' di R-12, il job
--   morto per sei mesi con l'ultimo verdetto agli atti a «done».
--   ⚠️ Il caso si COSTRUISCE togliendo le righe di giornale di un job che
--   pgAgent ha davvero fatto girare: e' l'unico modo, perche' `pgagent.pga_job`
--   e' una tabella di un'estensione e non si semina.
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
--
-- ⛔ I TEST 11 E 12 SONO IL §9.5-bis DEL BRIEF, COSTRUITO.
--   Il confronto a due fonti chiede «la sveglia di pgAgent ha lasciato
--   traccia?». Fino al 20260907-06 leggeva TUTTE le corse registrate sotto quel
--   codice, quindi una riga scritta da un attore qualunque rispondeva di si' al
--   posto di pgAgent — e spegneva il rilevatore di R-12 proprio sul job
--   sorvegliato.
--   ⚠️ Non era un'ipotesi: il 2026-09-07 `sync_auth_user_expired_daily` aveva
--   `giornale_ultima_corsa` alle 11:11 da sei righe di collaudo del backend
--   (origine COMMAND, jobname «x»), contro la corsa pgAgent delle 06:00.
--
-- ⛔ E IL TEST 12 E' LA STESSA FORMA DEL 9, SU UN SECONDO VOCABOLARIO CHIUSO:
--   le origini le dichiara `chk_job_run_log_origine`, quali valgano come
--   risposta di pgAgent lo dichiara la `FILTER` della vista. Un'origine nuova
--   domani non varrebbe come risposta e produrrebbe un falso allarme su un
--   processo sano — che e' esattamente il difetto contro cui il §7 del brief
--   mette in guardia. Il test la NOMINA invece di lasciarle un default.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(13);

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
-- 5..6. ⭐ Il confronto, costruito NEI DUE VERSI
-- ============================================================
-- Si prende un processo su cui il confronto sia POSSIBILE, gli si scrive il
-- giornale che serve, e si guarda che cosa risponde il panorama.
--
-- ⛔ IL SOGGETTO SI SCEGLIE SULLA STRUTTURA, NON SUL VERDETTO DI OGGI, ed e'
--   una correzione del 2026-09-07. Prima diceva `WHERE stato = 'OK'`: cioe'
--   chiedeva alla vista sotto esame di indicare da se' il proprio soggetto.
--   ⚠️ Basta una rottura che tolga di mezzo tutti gli `OK` — provata: la FILTER
--   sull'origine che nomina il valore sbagliato — perche' la SELECT non trovi
--   nessuno e i test 5, 6, 11 e 13 SALTINO invece di diventare rossi. E' la
--   forma classica del verde per sottrazione: il file smette di verificare
--   senza dirlo.
--   ⭐ I tre requisiti sotto vengono tutti da pgAgent (canale dichiarato, job
--   acceso, ha gia' girato almeno una volta): sono le PRECONDIZIONI del ramo, e
--   nessuno di loro dipende dal giornale, cioe' dalla cosa che si sta provando.
--
-- ⚠️ Se pgAgent non c'e' (CI) il caso non e' costruibile davvero: li' si
--   dichiara e si salta, invece di fingere un verde.
DO $confronto$
DECLARE
    v_proc dbops.processi.codice%TYPE;
BEGIN
    SELECT processo_codice INTO v_proc
      FROM dbops.vw_processi_programmazione
     WHERE canale = 'PGAGENT'
       AND job_abilitato IS TRUE
       AND pgagent_ultima_corsa IS NOT NULL
     ORDER BY processo_codice
     LIMIT 1;

    PERFORM set_config('pgtap.proc_sano', COALESCE(v_proc, ''), true);
    IF v_proc IS NULL THEN
        RETURN;
    END IF;

    -- ⭐ Gli si toglie la memoria: pgAgent continua a dire che e' girato, il
    --   giornale non lo sa piu'. E' esattamente cio' che succedeva quando il
    --   RAISE annullava il verbale.
    DELETE FROM maintenance.job_run_log
     WHERE processo_codice = v_proc OR jobname = v_proc;

    PERFORM set_config('pgtap.stato_senza_giornale',
        (SELECT stato FROM dbops.vw_processi_programmazione
          WHERE processo_codice = v_proc), true);

    -- E ora gliela si restituisce: una corsa di pgAgent, recente.
    INSERT INTO maintenance.job_run_log (jobname, processo_codice, origine, ok, message)
    VALUES (v_proc, v_proc, 'PGAGENT', true, 'pgtap: la corsa che risponde');

    PERFORM set_config('pgtap.stato_con_giornale',
        (SELECT stato FROM dbops.vw_processi_programmazione
          WHERE processo_codice = v_proc), true);
END
$confronto$;

SELECT CASE
    WHEN NULLIF(current_setting('pgtap.proc_sano', true), '') IS NULL
        THEN skip('5. pgAgent non e'' interrogabile su questo database (CI?)', 1)
    ELSE is(
        current_setting('pgtap.stato_senza_giornale', true),
        'GIRA_E_NON_REGISTRA',
        '5. tolte le righe di giornale, il panorama dice «e'' girato e non l''ha detto»'
    )
END;

-- ⛔ Il verso che rende il 5 una misura: senza, un panorama che gridasse sempre
--   passerebbe il test precedente a pieni voti.
-- ⚠️ E anche questo e' COSTRUITO, non letto: prima chiedeva che il processo
--   «risultasse OK prima», cioe' faceva della popolazione di oggi la propria
--   asserzione — verde per una ragione che con la vista non c'entrava.
SELECT CASE
    WHEN NULLIF(current_setting('pgtap.proc_sano', true), '') IS NULL
        THEN skip('6. pgAgent non e'' interrogabile su questo database (CI?)', 1)
    ELSE is(
        current_setting('pgtap.stato_con_giornale', true),
        'OK',
        '6. e rimessa una corsa di pgAgent recente, lo stesso processo torna OK'
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

-- ============================================================
-- 11. ⛔ CHI PUO' RISPONDERE PER pgAGENT
-- ============================================================
-- Si riusa il processo dei test 5..6: gli si toglie il giornale e gli si mette
-- UNA corsa recente scritta da un attore che non e' pgAgent.
-- ⚠️ La corsa e' recente per costruzione (`clock_timestamp()` di default),
--   quindi cade dentro l'ora di tolleranza: se contasse, lo stato tornerebbe
--   OK — ed e' esattamente quello che faceva prima del 20260907-06.
-- ⭐ Il verso opposto e' il test 6, che con una corsa di pgAgent pretende OK:
--   senza, una vista che non guardasse affatto il giornale passerebbe questo
--   test a pieni voti.
DO $origine$
DECLARE
    v_proc dbops.processi.codice%TYPE := NULLIF(current_setting('pgtap.proc_sano', true), '');
BEGIN
    IF v_proc IS NULL THEN
        RETURN;
    END IF;

    -- Un attore qualunque registra sotto quel codice. ⛔ Non e' una risposta
    -- alla domanda «pgAgent ha lasciato traccia?».
    DELETE FROM maintenance.job_run_log
     WHERE processo_codice = v_proc OR jobname = v_proc;
    INSERT INTO maintenance.job_run_log (jobname, processo_codice, origine, ok, message)
    VALUES (v_proc, v_proc, 'COMMAND', true, 'pgtap: corsa a mano');

    PERFORM set_config('pgtap.stato_con_command',
        (SELECT stato FROM dbops.vw_processi_programmazione
          WHERE processo_codice = v_proc), true);
END
$origine$;

-- ⛔ IL CASO DEL §9.5-bis: la riga estranea NON deve spegnere il rilevatore.
SELECT CASE
    WHEN NULLIF(current_setting('pgtap.proc_sano', true), '') IS NULL
        THEN skip('11. pgAgent non e'' interrogabile su questo database (CI?)', 1)
    ELSE is(
        current_setting('pgtap.stato_con_command', true),
        'GIRA_E_NON_REGISTRA',
        '11. una corsa registrata da un attore che non e'' pgAgent non vale come risposta'
    )
END;

-- ============================================================
-- 12..13. ⛔ IL VOCABOLARIO DELLE ORIGINI, CHIUSO E IN DUE POSTI
-- ============================================================
-- `chk_job_run_log_origine` dice quali origini esistono; la `FILTER` della
-- vista dice quali valgono come risposta di pgAgent.
--
-- ⭐ L'ELENCO NON E' SCRITTO QUI: si legge da `pg_constraint`. Le ATTESE si',
--   ed e' il punto — un'origine nuova non ha un'attesa, quindi il test la NOMINA
--   invece di darle un default silenzioso. E' la forma «il presidio dichiara i
--   suoi debiti»: l'invariante non e' «vuoto», e' «nessuna origine NON
--   DICHIARATA».
--
-- ⚠️ Il verdetto si prova COSTRUENDO la corsa, non leggendo il testo della
--   vista: una regexp su `pg_get_viewdef` direbbe che la parola c'e', non che
--   la vista si comporta di conseguenza.
DO $origini$
DECLARE
    -- ⚠️ Solo PGAGENT vale, e non e' una svista: `origine` e' la sola colonna
    --   che dica chi ha scritto la riga. ⛔ Il limite e' dichiarato nel commento
    --   della colonna: PGAGENT e' anche il DEFAULT, quindi distingue il backend
    --   (che dichiara CRON o COMMAND) e NON distingue pgAgent da un wrapper
    --   lanciato a mano da psql.
    v_attese CONSTANT jsonb := jsonb_build_object(
        'PGAGENT', true,
        'CRON',    false,
        'COMMAND', false
    );
    v_proc dbops.processi.codice%TYPE := NULLIF(current_setting('pgtap.proc_sano', true), '');
    v_origine        text;
    v_stato          text;
    v_atteso         boolean;
    v_non_dichiarate text[] := '{}';
    v_dissenzienti   text[] := '{}';
BEGIN
    FOR v_origine IN
        SELECT DISTINCT m[1]
          FROM pg_constraint c,
               LATERAL regexp_matches(pg_get_constraintdef(c.oid),
                                      '''([A-Z_]+)''::character varying', 'g') m
         WHERE c.conname = 'chk_job_run_log_origine'
         ORDER BY 1
    LOOP
        IF NOT v_attese ? v_origine THEN
            v_non_dichiarate := v_non_dichiarate || v_origine;
            CONTINUE;
        END IF;

        -- Senza un processo sano il verdetto non e' costruibile: si dichiara
        -- l'origine come vista, e il confronto lo fa il solo test 13.
        CONTINUE WHEN v_proc IS NULL;

        DELETE FROM maintenance.job_run_log
         WHERE processo_codice = v_proc OR jobname = v_proc;
        INSERT INTO maintenance.job_run_log (jobname, processo_codice, origine, ok, message)
        VALUES (v_proc, v_proc, v_origine, true, 'pgtap: vocabolario origini');

        SELECT stato INTO v_stato
          FROM dbops.vw_processi_programmazione
         WHERE processo_codice = v_proc;

        -- «Vale come risposta» = il rilevatore si spegne.
        v_atteso := (v_attese ->> v_origine)::boolean;
        IF (v_stato = 'OK') IS DISTINCT FROM v_atteso THEN
            v_dissenzienti := v_dissenzienti
                || (v_origine || ': atteso ' || CASE WHEN v_atteso THEN 'OK' ELSE 'GIRA_E_NON_REGISTRA' END
                    || ', ottenuto ' || COALESCE(v_stato, 'NULL'));
        END IF;
    END LOOP;

    -- ⛔ Si toglie subito: il seminato non deve sopravvivere al file.
    IF v_proc IS NOT NULL THEN
        DELETE FROM maintenance.job_run_log
         WHERE processo_codice = v_proc OR jobname = v_proc;
    END IF;

    PERFORM set_config('pgtap.origini_non_dichiarate',
                       array_to_string(v_non_dichiarate, ', '), true);
    PERFORM set_config('pgtap.origini_dissenzienti',
                       array_to_string(v_dissenzienti, '; '), true);
END
$origini$;

SELECT is(
    current_setting('pgtap.origini_non_dichiarate', true), '',
    '12. ogni origine ammessa dal CHECK ha un verdetto dichiarato in questo test'
);

SELECT CASE
    WHEN NULLIF(current_setting('pgtap.proc_sano', true), '') IS NULL
        THEN skip('13. pgAgent non e'' interrogabile su questo database (CI?)', 1)
    ELSE is(
        current_setting('pgtap.origini_dissenzienti', true), '',
        '13. e la vista tratta ogni origine come il verdetto dichiarato dice'
    )
END;

SELECT * FROM finish();

ROLLBACK;
