-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: il canale fuori transazione del giornale dei job
-- ChangeSet: 20260905-35 / -36 / -38 · Brief: brief-db-storicizzazione-bersagli-spariti §2.3
--
-- Elenco test (plan 7):
--  1) la funzione c'e', ed e' SECURITY DEFINER
--  2) ⛔ il suo owner e' un SUPERUSER — senza, dblink rifiuta la connessione
--  3) ⛔ l'utente del canale puo' entrare in `maintenance`
--  4) ⛔ e puo' scrivere sul giornale…
--  5) ✅ …ma NON leggerlo
--  6) ⭐ `fn_run_and_log` la chiama, e continua a RILANCIARE
--  7) ⭐ agent_host del verbale e' l'indirizzo del client (inet_client_addr()),
--     come per le righe nate col default, non il nome del cluster. PRESIDIO SUL
--     TESTO del corpo: provarlo davvero vuole il canale dblink, che committa
--     fuori transazione. 20261103-66, brief-db-revisione-maintenance M17.
--
-- ────────────────────────────────────────────────────────────────
-- ⛔ CHE COSA QUESTO FILE NON PROVA, ED E' LA COSA PIU' IMPORTANTE DA SAPERE.
--   Non prova che la riga venga scritta davvero. Non per pigrizia: perche' una
--   scrittura fuori transazione **sopravvive al ROLLBACK del test**, e questo
--   file lascerebbe una riga nel giornale a ogni giro. Un test che sporca cio'
--   che presidia non e' un test.
--   ⇒ La prova end-to-end si fa a mano, una volta, dopo ogni cambio del canale:
--     far fallire un job e guardare `maintenance.vw_job_run_da_guardare`.
--
-- ⭐ MA I SEI TEST QUI SOTTO PRENDONO ENTRAMBI I GUASTI CHE SONO SUCCESSI DAVVERO
--   il 2026-09-05, e nessuno dei due si vedeva dal lato del chiamante:
--     * la funzione era di `titodb`, non superuser -> dblink rifiutava la
--       connessione («password or GSSAPI delegated credentials required»);
--     * `zeroerp_log` non aveva `USAGE` su `maintenance` -> «permesso negato».
--   ⚠️ In entrambi i casi la funzione **non solleva**: emette un WARNING e
--   tira dritto, perche' e' fatta per non rompere un job che sta gia' fallendo.
--   ⇒ Un test che guardasse solo «la chiamata non esplode» sarebbe stato verde
--     tutte e due le volte. Questi guardano i PRESUPPOSTI, che e' l'unica cosa
--     che si puo' guardare da qui.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(7);

-- ============================================================
-- 1..2. La funzione, e il privilegio che la fa funzionare
-- ============================================================
SELECT is(
    (SELECT p.prosecdef
       FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'maintenance'
        AND p.proname = 'fn_job_run_log_failure'),
    true,
    '1. maintenance.fn_job_run_log_failure esiste ed e'' SECURITY DEFINER'
);

-- ⛔ IL PRIMO GUASTO VERO. `dblink` rifiuta a un non-superuser una connessione
--   senza password: e' la sua difesa contro chi si farebbe prestare le
--   credenziali del server. Finche' l'owner era `titodb`, la funzione apriva e
--   veniva respinta — con un WARNING che nessuno leggeva.
-- ⚠️ Non si chiede «l'owner e' postgres» ma «l'owner e' un superuser»: il nome
--   dell'utente amministrativo e' una scelta di installazione, il privilegio no.
SELECT is(
    (SELECT r.rolsuper
       FROM pg_proc p
       JOIN pg_namespace n ON n.oid = p.pronamespace
       JOIN pg_roles r ON r.oid = p.proowner
      WHERE n.nspname = 'maintenance'
        AND p.proname = 'fn_job_run_log_failure'),
    true,
    '2. l''owner della funzione e'' un superuser: senza, dblink rifiuta'
);

-- ============================================================
-- 3..5. I permessi dell'utente che sta dall'altro capo
-- ============================================================
-- ⛔ IL SECONDO GUASTO VERO. Dall'altro capo non c'e' `titodb`: c'e'
--   `zeroerp_log`, un ruolo che nasce per scrivere in `dbops.error_log`. Su
--   `maintenance` non aveva niente, e la scrittura moriva li'.
-- ⚠️ Se il ruolo non esiste il caso non e' costruibile: si dichiara e si salta,
--   invece di fingere un verde.
SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'zeroerp_log')
        THEN skip('3. ruolo zeroerp_log assente su questo database', 1)
    ELSE ok(
        has_schema_privilege('zeroerp_log', 'maintenance', 'USAGE'),
        '3. l''utente del canale puo'' entrare nello schema maintenance')
END;

SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'zeroerp_log')
        THEN skip('4. ruolo zeroerp_log assente su questo database', 1)
    ELSE ok(
        has_table_privilege('zeroerp_log', 'maintenance.job_run_log', 'INSERT'),
        '4. e puo'' scrivere sul giornale dei job')
END;

-- ⭐ Il verso opposto, e non e' pignoleria: chi redige un verbale non ha bisogno
--   di rileggerlo, e un `SELECT` in piu' su un giornale e' un `SELECT` su tutto
--   cio' che il giornale racconta.
SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'zeroerp_log')
        THEN skip('5. ruolo zeroerp_log assente su questo database', 1)
    ELSE ok(
        NOT has_table_privilege('zeroerp_log', 'maintenance.job_run_log', 'SELECT'),
        '5. ma NON puo'' leggerlo: il minimo indispensabile')
END;

-- ============================================================
-- 6. ⭐ Il chiamante la usa, e continua a rilanciare
-- ============================================================
-- ⛔ Le due meta' di una stessa decisione. Chiamarla senza rilanciare farebbe
--   risultare RIUSCITO a chi l'ha chiesto un lavoro che non lo e'; rilanciare
--   senza chiamarla riporterebbe al difetto di partenza — il verbale scritto e
--   distrutto nello stesso istante.
-- ⚠️ Si legge il CORPO della funzione: e' un presidio sul testo, quindi ha per
--   perimetro questa funzione sola. Vale finche' il canale passa di li'.
SELECT ok(
    (SELECT p.prosrc LIKE '%fn_job_run_log_failure%'
        AND p.prosrc LIKE '%RAISE;%'
       FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'maintenance'
        AND p.proname = 'fn_run_and_log'),
    '6. fn_run_and_log scrive il verbale fuori transazione E continua a rilanciare'
);

SELECT ok(
    (SELECT p.prosrc LIKE '%inet_client_addr()%' AND p.prosrc NOT LIKE '%cluster_name%'
       FROM pg_proc p
       JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'maintenance'
        AND p.proname = 'fn_job_run_log_failure'),
    '7. il verbale scrive in agent_host l''indirizzo del client, non il nome del cluster'
);

SELECT * FROM finish();

ROLLBACK;
