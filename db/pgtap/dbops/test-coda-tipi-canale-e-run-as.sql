-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: il canale del processo e il run_as del tipo di coda si ACCORDANO
-- Brief: brief-db-avvio-manuale-di-un-processo §8.3 (domanda 3 del §7)
--
-- Elenco test (plan 6):
--  1) dbops.coda_lavori_tipi non e' vuota (protegge 2..4 dal verde a vuoto)
--  2) ⭐ ogni tipo sotto un processo CODA ha run_as_default = OPERATORE
--  3) ⭐ ogni tipo sotto un processo PGAGENT ha run_as_default = SISTEMA
--  4) ⛔ nessun tipo di coda sta sotto un processo COMMAND
--  5) il tipo ESEGUI_PROCESSO: handler, OPERATORE, un tentativo, avvio_manuale
--  6) il processo avvio_manuale: MANUTENZIONE, CODA, nessun contratto
--
-- Scopo:
--  - il brief chiedeva «un test che il tipo sia sotto un processo CODA e non
--    PGAGENT». Quello pinnerebbe UNA riga; qui si presidia l'INVARIANTE da cui
--    la riga discende, e vale per ogni tipo presente e futuro:
--      · CODA = «lo accoda una persona, e l'identita' e' la sua» — e' la
--        DEFINIZIONE del canale (processi.md, processi_repository
--        `_CANALI_CON_IDENTITA`, test-processi-coda-automatica test 6). Un
--        tipo SISTEMA sotto un CODA contraddice la definizione: il lavoro
--        girerebbe senza il nome di chi ha premuto, e l'audit lo perderebbe
--        in silenzio;
--      · PGAGENT = il lavoro lo fa pgAgent; se il lavoro passa dal drenatore e
--        vuole un'identita', il canale e' CODA_AUTOMATICA (correzione R-E:
--        «un processo di coda accodato da una MACCHINA vuole l'identita'
--        come gli altri»). Un tipo OPERATORE sotto un PGAGENT e' il difetto
--        che CODA_AUTOMATICA e' nato per correggere;
--      · COMMAND = un comando che sveglia systemd, con il proprio run sul
--        giornale. Un tipo di coda sotto di lui attribuirebbe al comando un
--        lavoro che esegue il drenatore. E' la ragione per cui il brief conia
--        `avvio_manuale` invece di appendere ESEGUI_PROCESSO a
--        `draina_coda_lavori`;
--  - 5 e 6 sono il seed pin delle righe di questo brief — SENZA `attivo` sul
--    tipo, che nasce spento (regola del binding) e si accende a release BE
--    avvenuta: un test che lo pinnasse sarebbe rosso sulla riparazione.
--
-- ⚠️ Non c'e' un guard a DB per 2..4, ed e' una scelta (brief §8.3): la posta
--    e' l'audit, non il perimetro come per il guard di CLASSE di
--    fn_accoda_lavoro. Questo file e' il presidio del SEED; l'enqueue con il
--    run_as giusto lo scrive il backend, con il suo test.
--
-- Gira come l'applicazione: legge due cataloghi (nessuna RLS su dbops) e non
-- scrive niente.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(6);

-- ============================================================
-- 1. Il catalogo non e' vuoto — altrimenti 2..4 passerebbero a vuoto
-- ============================================================
SELECT isnt_empty(
    $$SELECT 1 FROM dbops.coda_lavori_tipi$$,
    '1. dbops.coda_lavori_tipi ha almeno un tipo: i test 2..4 hanno materia'
);

-- ============================================================
-- 2..4. L'invariante, per canale
-- ============================================================
-- ⚠️ Si guardano TUTTI i tipi, anche quelli spenti e quelli il cui processo e'
--   ritirato: la coerenza fra canale e run_as e' un fatto del catalogo, non
--   dello stato. Un tipo spento con il run_as sbagliato si accende sbagliato.
SELECT is_empty(
    $$SELECT t.codice, t.run_as_default
        FROM dbops.coda_lavori_tipi t
        JOIN dbops.processi p ON p.codice = t.processo_codice
       WHERE p.canale = 'CODA'
         AND t.run_as_default <> 'OPERATORE'$$,
    '2. ogni tipo sotto un processo CODA e'' OPERATORE: lo accoda una persona, l''identita'' e'' la sua'
);

SELECT is_empty(
    $$SELECT t.codice, t.run_as_default
        FROM dbops.coda_lavori_tipi t
        JOIN dbops.processi p ON p.codice = t.processo_codice
       WHERE p.canale = 'PGAGENT'
         AND t.run_as_default <> 'SISTEMA'$$,
    '3. ogni tipo sotto un processo PGAGENT e'' SISTEMA: se vuole un''identita'', il canale e'' CODA_AUTOMATICA'
);

SELECT is_empty(
    $$SELECT t.codice, p.codice AS processo
        FROM dbops.coda_lavori_tipi t
        JOIN dbops.processi p ON p.codice = t.processo_codice
       WHERE p.canale = 'COMMAND'$$,
    '4. nessun tipo di coda sta sotto un COMMAND: il drenatore non e'' l''attore di un comando systemd'
);

-- ============================================================
-- 5..6. Il seed di questo brief (senza `attivo`)
-- ============================================================
SELECT results_eq(
    $$SELECT handler_code, run_as_default, max_tentativi_default, processo_codice
        FROM dbops.coda_lavori_tipi
       WHERE codice = 'ESEGUI_PROCESSO'$$,
    $$VALUES ('esegui_processo_default', 'OPERATORE', 1, 'avvio_manuale')$$,
    '5. ESEGUI_PROCESSO: handler dichiarato, OPERATORE, UN tentativo (non idempotente), sotto avvio_manuale'
);

SELECT results_eq(
    $$SELECT classe, canale, tolleranza_minuti, segno_di_vita
        FROM dbops.processi
       WHERE codice = 'avvio_manuale'$$,
    $$VALUES ('MANUTENZIONE', 'CODA', NULL::integer, 'GIORNALE')$$,
    '6. avvio_manuale: MANUTENZIONE (niente utente tecnico), CODA (SU_RICHIESTA nel panorama), nessun contratto'
);

SELECT * FROM finish();
ROLLBACK;
