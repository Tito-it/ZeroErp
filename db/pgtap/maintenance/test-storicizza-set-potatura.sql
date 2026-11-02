-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- pgtap-runner: owner
-- pgtap-runner-motivo: il test fa DDL (crea una tabella con la colonna
--   `storicizza` per esercitare la DERIVAZIONE, e le toglie il DEFAULT) e
--   scrive su `config.storico_set_storicizza`, che a runtime scrivono solo due
--   procedure di manutenzione chiamate da pgAgent. Il ruolo applicativo non la
--   tocca. Verificato cercando gli scrittori, non dedotto.
--
-- Test: la potatura del set di storicizzazione (R-12)
-- Brief: brief-db-storicizzazione-bersagli-spariti.md §2.1 e §2.2
--
-- Elenco test (plan 7):
--  1) ⭐ l'invariante: nessuna riga DERIVATA senza referente
--  2) ⛔ COSTRUITO: una riga derivata che punta a niente viene POTATA
--  3) ⛔ COSTRUITO: una riga MANUALE che punta a niente NON viene potata
--  4) ⚠️ una tabella VIVA che ha perso il DEFAULT non viene potata
--  5) ✅ il sync continua ad AGGIUNGERE cio' che la derivazione produce
--  6) ⭐ l'apply non muore su una riga stantia: la salta e finisce il giro
--  7) ⚠️ i nomi del set sono tutti schema-qualificati
--
-- ────────────────────────────────────────────────────────────────
-- ⭐ PERCHE' QUESTO FILE ESISTE.
--   `apply_storicizza_weekly` e' morto ogni settimana per SEI MESI, e nessuno
--   se n'e' accorto. La causa immediata erano tre righe che puntavano a tabelle
--   ritirate; la causa vera e' che il set si popolava da solo e **non si potava
--   da solo** — mezza sincronizzazione.
--   ⇒ Togliere le tre righe sarebbe stato il tampone. Questi test fissano il
--     meccanismo, cosi' la prossima tabella ritirata non rifa' lo stesso guasto.
--
-- ⛔ I TEST 2, 3 e 4 SONO TRE RISPOSTE DIVERSE ALLA STESSA DOMANDA, e vanno
--   letti insieme. «La riga non e' piu' prodotta dalla derivazione» ha tre
--   cause, e solo UNA giustifica la potatura:
--     2. il nome non risolve a niente, ed e' derivata   → si pota
--     3. il nome non risolve a niente, ma e' MANUALE    → ⛔ non si tocca:
--        e' una decisione, e va detta a una persona
--     4. la tabella c'e' ma ha perso il DEFAULT         → ⛔ non si pota: e' il
--        caso transitorio che `apply_storicizza_weekly` ripara, e potarlo
--        spegnerebbe la storicizzazione di una tabella viva
--   ⚠️ Provare solo il 2 lascerebbe passare una potatura che cancella troppo —
--   e cancellerebbe **in silenzio**, che e' il difetto da cui si parte.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(7);

-- ============================================================
-- 1. L'invariante
-- ============================================================
-- ⚠️ Si misura PRIMA della fixture: dopo si misurerebbe il proprio rumore.
--   ⛔ E riguarda le sole righe DERIVATE: una riga manuale senza bersaglio e'
--   un fatto da guardare, non un difetto del meccanismo — il test 3 dice
--   perche'.
SELECT is_empty(
    $$SELECT table_name FROM config.storico_set_storicizza
       WHERE NOT insert_manuale AND to_regclass(table_name) IS NULL$$,
    '1. nessuna riga derivata del set punta a un oggetto inesistente'
);

-- ============================================================
-- Fixture: i tre casi, costruiti
-- ============================================================
DO $fixture$
BEGIN
    -- Una tabella VERA, con la colonna che la derivazione cerca.
    CREATE TABLE dbops.pgtap_storicizza_prova (
        id          integer PRIMARY KEY,
        storicizza  boolean NOT NULL DEFAULT true
    );

    INSERT INTO config.storico_set_storicizza (table_name, insert_manuale)
    VALUES ('config.pgtap_tabella_sparita_derivata', false),
           ('config.pgtap_tabella_sparita_manuale',  true);
END
$fixture$;

CALL maintenance.proc_sync_storico_set_storicizza();

-- ============================================================
-- 2..4. Che cosa si pota, e che cosa no
-- ============================================================
SELECT is_empty(
    $$SELECT table_name FROM config.storico_set_storicizza
       WHERE table_name = 'config.pgtap_tabella_sparita_derivata'$$,
    '2. una riga derivata che punta a niente viene potata'
);

-- ⛔ Il verso che tiene la potatura onesta: quella riga l'ha messa una persona
--   (o un changeSet). Se il suo bersaglio sparisce, sparisce una DECISIONE — e
--   va detta a qualcuno, non cancellata di nascosto.
SELECT isnt_empty(
    $$SELECT table_name FROM config.storico_set_storicizza
       WHERE table_name = 'config.pgtap_tabella_sparita_manuale'$$,
    '3. una riga MANUALE che punta a niente NON viene potata'
);

-- ⚠️ Il terzo caso, ed e' quello che si sbaglierebbe piu' facilmente: la
--   tabella c'e', ma il DEFAULT no. Potarla qui vorrebbe dire spegnere la
--   storicizzazione di una tabella viva perche' `apply_storicizza_weekly` non
--   ha ancora fatto il suo giro — le due meta' del meccanismo si
--   combatterebbero.
DO $senza_default$
BEGIN
    ALTER TABLE dbops.pgtap_storicizza_prova ALTER COLUMN storicizza DROP DEFAULT;
END
$senza_default$;

CALL maintenance.proc_sync_storico_set_storicizza();

SELECT isnt_empty(
    $$SELECT table_name FROM config.storico_set_storicizza
       WHERE table_name = 'dbops.pgtap_storicizza_prova'$$,
    '4. una tabella viva che ha perso il DEFAULT non viene potata'
);

-- ============================================================
-- 5. ✅ La meta' che c'era gia' continua a funzionare
-- ============================================================
-- ⭐ Il test 4 lo dimostra solo di rimbalzo: la riga c'e' perche' era stata
--   AGGIUNTA dal primo sync, sulla tabella creata dalla fixture. Senza questa
--   asserzione, una potatura che avesse rotto l'inserimento passerebbe i test
--   2..4 lasciando il set che non si popola piu'.
SELECT is(
    (SELECT insert_manuale FROM config.storico_set_storicizza
      WHERE table_name = 'dbops.pgtap_storicizza_prova'),
    false,
    '5. il sync ha AGGIUNTO la tabella nuova, e l''ha marcata derivata'
);

-- ============================================================
-- 6. ⭐ L'apply sopravvive a una riga stantia
-- ============================================================
-- E' il cuore di R-12: prima una sola riga senza referente sollevava
-- `undefined_table` e fermava il giro per tutte le altre cento.
-- ⚠️ La riga stantia c'e' ancora ed e' quella MANUALE del test 3: il sync non
--   la pota, quindi l'apply la incontra davvero. Il caso non e' simulato.
SELECT lives_ok(
    $$CALL maintenance.proc_apply_storicizza_defaults()$$,
    '6. l''apply non muore su una riga stantia: la salta e finisce il giro'
);

-- ============================================================
-- 7. ⚠️ I nomi sono qualificati
-- ============================================================
-- ⛔ `regclass::text` omette lo schema se quello schema e' nel `search_path` di
--   chi lancia il job: una chiave che cambia col search_path del chiamante e'
--   una chiave che un giorno non ritrova la propria riga — e la potatura, che
--   risolve il nome, sarebbe la prima a inciampare.
SELECT is_empty(
    $$SELECT table_name FROM config.storico_set_storicizza
       WHERE table_name NOT LIKE '%.%'$$,
    '7. ogni nome del set e'' schema-qualificato'
);

SELECT * FROM finish();

ROLLBACK;
