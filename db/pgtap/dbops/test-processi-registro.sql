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
-- Elenco test (plan 15):
--  1) dbops.processi esiste
--  2) chk_processi_classe respinge una classe fuori catalogo
--  3) chk_processi_canale respinge un canale fuori catalogo
--  4) uq_processi_codice respinge un codice doppio
--  5) la FK bersagli -> processi respinge un processo inesistente
--  6) chk_processi_bersagli_via respinge un percorso fuori vocabolario
--  7) chk_processi_bersagli_via_colonna respinge un percorso senza colonna
--  8) ogni canale DICHIARATO dal CHECK e' usato da almeno un processo
--  9) ogni bersaglio seedato punta a un processo DOMINIO
-- 10) vw_processi_dominio_senza_emittente non ha righe NON_DICHIARATO
-- 11) un DOMINIO senza bersagli finisce nella vista (caso COSTRUITO)
-- 12) un percorso su colonna inesistente finisce nella vista (caso COSTRUITO)
-- 13) vw_processi_che_bypassano non ha righe NON_DICHIARATO
-- 14) ⭐ un bersaglio col percorso ma SENZA difesa finisce nel livello 2 (COSTRUITO,
--     non appoggiato a un debito reale: quello prima o poi si paga)
-- 15) ⛔ due righe di catalogo per lo STESSO lavoro: solo una puo' essere viva
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

SELECT plan(15);

-- ============================================================
-- 1. La tabella c'e'
-- ============================================================
SELECT has_table('dbops', 'processi', 'dbops.processi esiste');

-- ============================================================
-- 2..7. I cancelli, su casi COSTRUITI
-- ============================================================
SELECT throws_ok(
    -- ⚠️ 20261016-20: le righe con una sveglia dichiarano l'accensione, altrimenti
    --   il 23514 verrebbe da chk_processi_accensione (verde per il vincolo sbagliato).
    $$INSERT INTO dbops.processi (id, codice, descrizione, classe, canale,
                                  acceso_in_sviluppo, acceso_in_produzione, spegnibile, causa_fallimento, accendibile_in_produzione)
      VALUES (9001, 'PGTAP-CLASSE-IGNOTA', 'test', 'FANTASIA', 'COMMAND', true, true, true, 'PROGRAMMA', true)$$,
    '23514',
    NULL,
    'chk_processi_classe respinge una classe fuori catalogo'
);

SELECT throws_ok(
    $$INSERT INTO dbops.processi (id, codice, descrizione, classe, canale,
                                  acceso_in_sviluppo, acceso_in_produzione, spegnibile, causa_fallimento, accendibile_in_produzione)
      VALUES (9002, 'PGTAP-CANALE-IGNOTO', 'test', 'DOMINIO', 'PICCIONE', true, true, true, 'PROGRAMMA', true)$$,
    '23514',
    NULL,
    'chk_processi_canale respinge un canale fuori catalogo'
);

-- Il codice e' l'attore, e ci si aggancia la FK di job_run_log: un doppione
-- renderebbe ambiguo «chi ha eseguito».
SELECT throws_ok(
    $$INSERT INTO dbops.processi (id, codice, descrizione, classe, canale,
                                  acceso_in_sviluppo, acceso_in_produzione, spegnibile, causa_fallimento, accendibile_in_produzione)
      VALUES (9003, 'run_fatturazione_batch', 'doppione', 'DOMINIO', 'COMMAND', true, true, true, 'PROGRAMMA', true)$$,
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
-- ⚠️ 2026-09-05 — QUESTA ASSERZIONE E' STATA RIVOLTATA, non riparata.
--   Diceva «il seed copre tutti e TRE i canali» con un 3 scritto a mano. Il
--   giorno in cui il CHECK ne ha ammesso un quarto — `CODA_AUTOMATICA`,
--   changeSet 20260905-09 — il test e' andato rosso pur essendo tutto a posto:
--   il numero non descriveva una regola, fotografava un elenco.
--   ⭐ La regola vera e': **ogni canale che il CHECK dichiara lecito e' usato da
--     almeno un processo**. Un canale ammesso e mai seminato e' un pezzo di
--     vocabolario che nessuno esercita — e il primo processo che ci finira'
--     dentro non troverebbe nessun precedente che lo dice funzionante.
--   ⇒ L'elenco lecito si LEGGE dal vincolo: aggiungerne uno senza seminarlo
--     accende questo test, aggiungerne uno seminandolo no.
SELECT is_empty(
    $$SELECT c.canale
        FROM (SELECT unnest(regexp_matches(pg_get_constraintdef(oid),
                                           '''([A-Z_]+)''::text', 'g')) AS canale
                FROM pg_constraint WHERE conname = 'chk_processi_canale') c
       WHERE NOT EXISTS (SELECT 1 FROM dbops.processi p
                          WHERE p.attivo AND p.canale = c.canale)$$,
    '8. ogni canale dichiarato dal CHECK e'' usato da almeno un processo attivo'
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
-- 10. Il livello 1 non ha righe NON_DICHIARATO
-- ============================================================
-- ⛔ 2026-09-05 — ERA LA TERZA VOLTA CHE SCRIVEVO QUESTO ERRORE, e vale la pena
--   fissarlo qui. Il test pretendeva che la vista elencasse ESATTAMENTE
--   `send_pending_emails`, cioe' fissava un DEBITO come se fosse un'invariante.
--   ⭐ Un presidio ha il compito di arrivare a ZERO: un test che pretende una
--     sua riga si rompe quando ci arriva.
--   ⇒ La regola generale, ormai pagata tre volte: un test SU un presidio
--     asserisce che e' vuoto, e COSTRUISCE il caso che lo deve accendere (test
--     11 e 12 qui sotto). Non si appoggia mai a un debito reale.
--
-- 🔴 2026-09-05, GIRO DOPO — e la correzione era andata un passo TROPPO IN LA'.
--   Riscritto come «la vista e' vuota», il test e' tornato rosso al primo
--   migrate: `send_pending_emails` c'e' ancora.
--   ⚠️ Il debito non era stato pagato: si era SPOSTATO. Il changeSet -18 ha dato
--   l'emittente a `config.email_outbox`, ma quella tabella la scrive
--   l'interfaccia — il processo legge `config.email_log`, che la colonna non ce
--   l'ha. Il censimento ora nomina la tabella giusta, e la vista la mostra
--   perche' e' vero che il percorso non esiste.
--   ⛔ «Vuota» non e' l'invariante: lo sarebbe solo il giorno in cui non esiste
--   piu' nessun debito, e un test che lo pretende e' lo stesso errore di prima
--   girato al contrario — fissa l'ASSENZA di un debito invece della sua
--   presenza, e si rompe lo stesso.
--   ⭐ L'invariante vera e' **«nessuna riga NON_DICHIARATO»**: un debito con un
--   nome e' un lavoro, una riga che nessuno ha dichiarato e' un allarme. E'
--   esattamente cio' che il test 13 qui sotto fa gia' per i bypass RLS, ed e' la
--   ragione per cui la colonna `stato` esiste (changeSet 20260905-19).
--   ⚠️ Il prezzo si dichiara: dichiarare un debito ZITTISCE questo test. Lo
--   tengono onesto i test 11 e 12, che costruiscono un caso NUOVO e non
--   dichiarato e pretendono che compaia.
--   ℹ️ Stessa invariante, dall'altro capo: test 4 di
--   `db/pgtap/dbops/test-presidi-debito-dichiarato.sql`.
SELECT is_empty(
    $$SELECT processo_codice, nome_tabella
        FROM dbops.vw_processi_dominio_senza_emittente
       WHERE stato = 'NON_DICHIARATO'$$,
    'nessun processo DOMINIO senza percorso all''emittente, fuori dal debito dichiarato'
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
    -- 20261016-20: chi ha una sveglia dichiara l'accensione; un CODA no.
    INSERT INTO dbops.processi (id, codice, descrizione, classe, canale,
                                acceso_in_sviluppo, acceso_in_produzione, spegnibile, causa_fallimento, accendibile_in_produzione)
    VALUES (v_id, 'PGTAP-DOMINIO-SENZA-BERSAGLI',
            'processo di prova senza bersagli dichiarati', 'DOMINIO', 'COMMAND', true, true, true, 'PROGRAMMA', true);
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
    -- 20261016-20: chi ha una sveglia dichiara l'accensione; un CODA no.
    INSERT INTO dbops.processi (id, codice, descrizione, classe, canale,
                                acceso_in_sviluppo, acceso_in_produzione, spegnibile, causa_fallimento, accendibile_in_produzione)
    VALUES (v_processo_id, 'PGTAP-PERCORSO-ROTTO',
            'processo di prova con percorso su colonna inesistente',
            'DOMINIO', 'COMMAND', true, true, true, 'PROGRAMMA', true);

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
-- ⚠️ La regola presidiata non e' «la vista e' vuota»: un bypass puo' essere un
--   debito registrato, con la fase in cui si chiude (lo e' stato
--   zeroerp_batch_fatturazione, ritirato il 2026-10-15). La regola e' che non ne
--   compaia uno NUOVO.
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
    -- 20261016-20: chi ha una sveglia dichiara l'accensione; un CODA no.
    INSERT INTO dbops.processi (id, codice, descrizione, classe, canale,
                                acceso_in_sviluppo, acceso_in_produzione, spegnibile, causa_fallimento, accendibile_in_produzione)
    VALUES (v_processo_id, 'PGTAP-BERSAGLIO-SCOPERTO',
            'processo di prova con percorso dichiarato e nessuna difesa',
            'DOMINIO', 'COMMAND', true, true, true, 'PROGRAMMA', true);

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

-- ============================================================
-- 15. ⛔ DUE RIGHE DI CATALOGO PER LO STESSO LAVORO
-- ============================================================
-- Brief: brief-db-sveglia-dei-processi §7 (segnalazione BE) e §8.5 (risposta).
--
-- ⛔ «Stesso lavoro» NON e' una proprieta' che il database possa leggere, ed e'
--   la stessa situazione della `classe`: una DICHIARAZIONE, verificata in un
--   verso solo. Un vincolo che pretendesse di riconoscerla dedurrebbe, e una
--   deduzione sbagliata non si vede. ⇒ Niente CHECK, niente colonna: un elenco
--   DICHIARATO qui, e l'invariante e' «di ogni coppia ne vive al massimo una».
--
-- ⚠️ Perche' serve, visto che «oggi non fa danno»: `fn_sync_auth_user_expired`
--   e' idempotente, quindi il secondo giro non trova nessuno da disattivare.
--   Quello che si perde e' la LEGGIBILITA' del giornale — due attori diversi
--   per lo stesso fatto — e la possibilita' di presidiare: il panorama
--   mostrerebbe uno dei due OK e l'altro fermo, SENZA che ci sia niente di
--   rotto. Un presidio che segnala il sano e' un presidio che si impara a
--   ignorare.
--
-- ⭐ E questo elenco e' un REGISTRO, non una lista di eccezioni: una coppia
--   nuova si aggiunge quando la si scopre, e sparisce quando una delle due
--   righe viene ritirata. Se resta vuoto un giorno, si cancella il test.
--
-- ⚠️ «Viva» qui significa cio' che significa per il panorama — `attivo` E
--   `obsoleto_dal IS NULL` — e non il solo `attivo`: si ritira con
--   `obsoleto_dal`, che non sveglia nessun guard di disattivazione con figlie.
SELECT is_empty(
    $$WITH gemelli (uno, altro, lavoro) AS (
          VALUES ('sync_auth_user_expired_daily', 'sync_auth_user_active',
                  'disattivazione degli utenti la cui finestra e'' scaduta')
      )
      SELECT g.lavoro
        FROM gemelli g
       WHERE (SELECT count(*)
                FROM dbops.processi p
               WHERE p.codice IN (g.uno, g.altro)
                 AND p.attivo
                 AND p.obsoleto_dal IS NULL) > 1$$,
    '15. di due righe di catalogo per lo stesso lavoro ne vive al massimo una'
);

SELECT * FROM finish();

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia nulla dietro di se'.
ROLLBACK;
