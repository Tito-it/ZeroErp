-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture scrive su dbops.processi / processi_bersagli,
--   che a runtime NON scrive nessuno: ne' il backend ne' una funzione DB. Sono
--   catalogo popolato dal seed Liquibase, e il SELECT-only del ruolo
--   applicativo (90_end/20260904-15) e' corretto. Stessa forma gia' accettata
--   per ui.dashboard_definizione. Verificato cercando gli scrittori, non dedotto.
--
-- Test: dbops.processi, dbops.processi_bersagli e le tre viste di presidio
-- Brief: brief-db-processi-automatici-identita-e-perimetro §2, §8
--
-- Elenco test (plan 14):
--  1) dbops.processi esiste
--  2) chk_processi_classe respinge una classe fuori catalogo
--  3) chk_processi_canale respinge un canale fuori catalogo
--  4) uq_processi_codice respinge un codice doppio
--  5) la FK bersagli -> processi respinge un processo inesistente
--  6) chk_processi_bersagli_via respinge un percorso fuori vocabolario
--  7) chk_processi_bersagli_via_colonna respinge un percorso senza colonna
--  8) il seed di catalogo copre tutti e tre i canali
--  9) ogni bersaglio seedato punta a un processo DOMINIO
-- 10) vw_processi_dominio_senza_emittente elenca ESATTAMENTE il debito dichiarato
-- 11) un DOMINIO senza bersagli finisce nella vista (caso COSTRUITO)
-- 12) un percorso su colonna inesistente finisce nella vista (caso COSTRUITO)
-- 13) vw_processi_che_bypassano non ha righe NON_DICHIARATO
-- 14) ⭐ un bersaglio col percorso ma SENZA difesa finisce nel livello 2 (COSTRUITO,
--     non appoggiato a un debito reale: quello prima o poi si paga)
--
-- Scopo:
--  - collaudare i cancelli del registro COSTRUENDO i casi cattivi, non
--    sperando che la popolazione li contenga;
--  - fissare che la vista di livello 1 elenca il debito DICHIARATO e nulla
--    piu': se domani un processo DOMINIO nasce senza percorso, il test rompe.
-- ------------------------------------------------------------

BEGIN;

-- Contesto applicativo: qui non serve alla RLS (dbops non ha policy), ma il
-- preambolo e' presidiato e la riga non costa niente. Toglierla renderebbe il
-- file un'eccezione da dichiarare.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(14);

-- ============================================================
-- 1. La tabella c'e'
-- ============================================================
SELECT has_table('dbops', 'processi', 'dbops.processi esiste');

-- ============================================================
-- 2..7. I cancelli, su casi COSTRUITI
-- ============================================================
SELECT throws_ok(
    $$INSERT INTO dbops.processi (id, codice, descrizione, classe, canale)
      VALUES (9001, 'PGTAP-CLASSE-IGNOTA', 'test', 'FANTASIA', 'COMMAND')$$,
    '23514',
    NULL,
    'chk_processi_classe respinge una classe fuori catalogo'
);

SELECT throws_ok(
    $$INSERT INTO dbops.processi (id, codice, descrizione, classe, canale)
      VALUES (9002, 'PGTAP-CANALE-IGNOTO', 'test', 'DOMINIO', 'PICCIONE')$$,
    '23514',
    NULL,
    'chk_processi_canale respinge un canale fuori catalogo'
);

-- Il codice e' l'attore, e ci si aggancia la FK di job_run_log: un doppione
-- renderebbe ambiguo «chi ha eseguito».
SELECT throws_ok(
    $$INSERT INTO dbops.processi (id, codice, descrizione, classe, canale)
      VALUES (9003, 'run_fatturazione_batch', 'doppione', 'DOMINIO', 'COMMAND')$$,
    '23505',
    NULL,
    'uq_processi_codice respinge un codice gia'' registrato'
);

SELECT throws_ok(
    $$INSERT INTO dbops.processi_bersagli
          (id, processo_id, schema_tabella, nome_tabella, emittente_via, emittente_colonna)
      VALUES (9004, 999999, 'vendite', 'fatture', 'fiscale', 'emittente_fiscale_id')$$,
    '23503',
    NULL,
    'la FK bersagli -> processi respinge un processo inesistente'
);

SELECT throws_ok(
    $$INSERT INTO dbops.processi_bersagli
          (id, processo_id, schema_tabella, nome_tabella, emittente_via, emittente_colonna)
      VALUES (9005, 20, 'vendite', 'fatture', 'telepatia', 'emittente_fiscale_id')$$,
    '23514',
    NULL,
    'chk_processi_bersagli_via respinge un percorso fuori vocabolario'
);

-- Un percorso senza colonna non sarebbe verificabile dalla vista: passerebbe a
-- vuoto, che e' il modo in cui un presidio smette di presidiare.
SELECT throws_ok(
    $$INSERT INTO dbops.processi_bersagli
          (id, processo_id, schema_tabella, nome_tabella, emittente_via, emittente_colonna)
      VALUES (9006, 20, 'vendite', 'fatture', 'fiscale', NULL)$$,
    '23514',
    NULL,
    'chk_processi_bersagli_via_colonna respinge un percorso senza colonna'
);

-- ============================================================
-- 8..9. Il seed di catalogo
-- ============================================================
SELECT is(
    (SELECT count(DISTINCT canale)::int FROM dbops.processi WHERE attivo),
    3,
    'il seed copre tutti e tre i canali (PGAGENT, COMMAND, CODA)'
);

-- I bersagli si dichiarano per la sola classe DOMINIO: e' quella su cui il
-- presidio guarda. Una riga su un processo di manutenzione sarebbe rumore che
-- nessuno terrebbe aggiornato.
SELECT is_empty(
    $$SELECT p.codice
        FROM dbops.processi_bersagli b
        JOIN dbops.processi p ON p.id = b.processo_id
       WHERE p.classe <> 'DOMINIO'$$,
    'ogni bersaglio seedato punta a un processo DOMINIO'
);

-- ============================================================
-- 10. Il debito dichiarato, e nulla di piu'
-- ============================================================
-- ⚠️ Questa NON e' una vista «che deve restare vuota»: config.email_outbox non
--   porta l'emittente ed e' un Caso B DICHIARATO. Il test fissa l'insieme: se
--   domani un processo DOMINIO nasce senza percorso, questo rosso lo dice.
SELECT set_eq(
    $$SELECT DISTINCT processo_codice FROM dbops.vw_processi_dominio_senza_emittente$$,
    ARRAY['send_pending_emails'],
    'vw_processi_dominio_senza_emittente elenca esattamente il debito dichiarato'
);

-- ============================================================
-- 11..12. La vista si accende davvero — casi COSTRUITI
-- ============================================================
-- Senza questi due, il test 10 proverebbe solo che oggi non c'e' altro: non
-- che la vista sappia accorgersi di qualcosa.
DO $mancante$
DECLARE
    v_id dbops.processi.id%TYPE := 9101;
BEGIN
    INSERT INTO dbops.processi (id, codice, descrizione, classe, canale)
    VALUES (v_id, 'PGTAP-DOMINIO-SENZA-BERSAGLI',
            'processo di prova senza bersagli dichiarati', 'DOMINIO', 'COMMAND');
END
$mancante$;

SELECT is(
    (SELECT motivo
       FROM dbops.vw_processi_dominio_senza_emittente
      WHERE processo_codice = 'PGTAP-DOMINIO-SENZA-BERSAGLI'),
    'nessun bersaglio dichiarato',
    'un processo DOMINIO senza bersagli finisce nella vista'
);

DO $colonna$
DECLARE
    v_processo_id dbops.processi_bersagli.processo_id%TYPE := 9102;
    v_bersaglio   dbops.processi_bersagli.id%TYPE          := 9102;
BEGIN
    INSERT INTO dbops.processi (id, codice, descrizione, classe, canale)
    VALUES (v_processo_id, 'PGTAP-PERCORSO-ROTTO',
            'processo di prova con percorso su colonna inesistente',
            'DOMINIO', 'COMMAND');

    -- Padre e figlio in DUE istruzioni: una CTE unica condividerebbe la stessa
    -- snapshot e la FK non troverebbe il padre.
    INSERT INTO dbops.processi_bersagli
        (id, processo_id, schema_tabella, nome_tabella, emittente_via, emittente_colonna)
    VALUES (v_bersaglio, v_processo_id, 'vendite', 'fatture',
            'fiscale', 'colonna_che_non_esiste');
END
$colonna$;

SELECT is(
    (SELECT motivo
       FROM dbops.vw_processi_dominio_senza_emittente
      WHERE processo_codice = 'PGTAP-PERCORSO-ROTTO'),
    'colonna del percorso inesistente',
    'un percorso dichiarato su una colonna inesistente finisce nella vista'
);

-- ============================================================
-- 13. Nessun bypass non dichiarato
-- ============================================================
-- ⚠️ La regola presidiata non e' «la vista e' vuota»: oggi
--   zeroerp_batch_fatturazione ha il bypass ed e' un debito registrato, con la
--   fase in cui si chiude. La regola e' che non ne compaia uno NUOVO.
SELECT is_empty(
    $$SELECT ruolo FROM dbops.vw_processi_che_bypassano
       WHERE stato = 'NON_DICHIARATO'$$,
    'nessun ruolo applicativo bypassa la RLS fuori dall''elenco dichiarato'
);

-- ============================================================
-- 14. Il livello 2 si accende — caso COSTRUITO
-- ============================================================
-- ⛔ 2026-09-05 — QUESTO TEST ERA SCRITTO AL CONTRARIO, e la correzione vale
--   piu' del test. Asseriva che la vista NOMINASSE `vendite.listini_versioni`,
--   cioe' pretendeva la PRESENZA di un debito reale. Il giorno in cui quel
--   debito e' stato pagato — policy e guard, changeSet 20260905-04/-06 — il
--   test e' diventato rosso **per il motivo giusto**, che e' assurdo:
--   ⇒ un presidio ha il compito di arrivare a ZERO, e un test che pretende una
--     sua riga si rompe quando il lavoro riesce.
--   La forma giusta e' la stessa dei test 11 e 12: si COSTRUISCE il caso,
--   cosi' il test misura il MECCANISMO e resta verde qualunque debito reale
--   ci sia — o non ci sia.
DO $senza_difesa$
DECLARE
    v_processo_id dbops.processi_bersagli.processo_id%TYPE := 9103;
    v_bersaglio   dbops.processi_bersagli.id%TYPE          := 9103;
BEGIN
    INSERT INTO dbops.processi (id, codice, descrizione, classe, canale)
    VALUES (v_processo_id, 'PGTAP-BERSAGLIO-SCOPERTO',
            'processo di prova con percorso dichiarato e nessuna difesa',
            'DOMINIO', 'COMMAND');

    -- ⭐ Il bersaglio e' `dbops.processi` stessa: ha la colonna dichiarata,
    --   quindi il percorso e' valido — ed e' una tabella senza RLS e senza
    --   guard di scope, che e' esattamente il caso da intercettare. Sceglierla
    --   fra le tabelle di dominio vere avrebbe legato di nuovo il test a un
    --   debito che qualcuno prima o poi paga.
    -- Padre e figlio in DUE istruzioni: una CTE unica condividerebbe la stessa
    -- snapshot e la FK non troverebbe il padre.
    INSERT INTO dbops.processi_bersagli
        (id, processo_id, schema_tabella, nome_tabella, emittente_via, emittente_colonna)
    VALUES (v_bersaglio, v_processo_id, 'dbops', 'processi', 'fiscale', 'id');
END
$senza_difesa$;

SELECT isnt_empty(
    $$SELECT nome_tabella FROM dbops.vw_processi_dominio_senza_difesa
       WHERE processo_codice = 'PGTAP-BERSAGLIO-SCOPERTO'$$,
    'un bersaglio col percorso ma senza policy ne'' guard finisce nel livello 2'
);

SELECT * FROM finish();

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia nulla dietro di se'.
ROLLBACK;
