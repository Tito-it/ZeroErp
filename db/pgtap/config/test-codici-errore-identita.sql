-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Elenco test (plan 8):
-- 1) un codice SENZA classe non puo' nascere            (NOT NULL, 23502)
-- 2) una classe inventata non passa                     (FK, 23503)
-- 3) un messaggio per un codice senza padre non passa   (FK, 23503)
-- 4) lo stesso messaggio passa se il padre esiste
-- 5) un codice RITIRATO risolve ancora il suo messaggio
-- 6) `note` con un a capo non passa                     (CHECK, 23514)
-- 7) un codice con spazi ai bordi non passa             (CHECK, 23514)
-- 8) ogni codice del catalogo ha il suo padre           (invariante sui dati veri)
--
-- Scopo:
--   Collaudare il MECCANISMO del cantiere «classe dei codici errore», non i
--   suoi dati. Il disegno promette una cosa sola:
--
--     ⭐ una FRASE non puo' nascere senza che qualcuno abbia deciso CHE COSA E'
--        l'errore che descrive.
--
--   Quella promessa non sta in un documento: sta in tre vincoli — `classe`
--   NOT NULL senza default, la FK verso il vocabolario, la FK dal catalogo dei
--   messaggi. I test 1-4 sono quei tre vincoli, uno per uno. Senza, il
--   `NOT NULL` sarebbe un'etichetta rassicurante — la cosa peggiore, perche'
--   nessuno la ricontrolla.
--
--   Piano: docs/it/dev/work-done/piano-db-classe-codici-errore.md (D-8)
--   Tabelle: 20260807-11, -12 · FK: 20260807-14
-- ------------------------------------------------------------

BEGIN;

-- Contesto applicativo: il test gira come `zeroerp_app` con la RLS attiva.
-- Guida: docs/it/guide/pgtap-come-si-scrive-un-test.md
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(8);

-- ============================================================
-- Fixture
--   id fissi nel range 99xx, come gli altri test del catalogo: la sequenza di
--   messaggi_errore e' disallineata rispetto al MAX(id) seminato. Il ROLLBACK
--   finale ripulisce.
--   ⚠️ L'ordine e' obbligato dalla FK: prima il CODICE, poi la FRASE. E' la
--   stessa cosa che il seed 20260614-08 fa coi tre loader.
-- ============================================================
INSERT INTO config.codici_errore (codice, classe, note)
VALUES ('TEST_CE_VIVO',     'DATO_ERRATO',     'Fixture del test D-8: codice in servizio.');

INSERT INTO config.codici_errore (codice, classe, obsoleto_dal)
VALUES ('TEST_CE_RITIRATO', 'CONFLITTO_STATO', DATE '2026-01-01');

INSERT INTO config.messaggi_errore (id, codice, lingua, messaggio, causa, soluzione)
VALUES (9941, 'TEST_CE_RITIRATO', 'it', 'Messaggio di un codice ritirato.', '', '');

-- ============================================================
-- 1) Un codice senza classe non puo' nascere
--    E' IL meccanismo anti-ricaduta del cantiere: prima il ripiego a 400 di
--    `ErrorPolicyRegistry.resolve` decideva al posto tuo, in silenzio.
-- ============================================================
SELECT throws_ok(
    $$INSERT INTO config.codici_errore (codice, classe) VALUES ('TEST_CE_NOCLASSE', NULL)$$,
    '23502',
    NULL,
    '1. Un codice SENZA classe non passa (NOT NULL, e senza DEFAULT che decida al posto tuo)'
);

-- ============================================================
-- 2) Una classe inventata non passa
--    Il vocabolario e' una tabella, non un CHECK: la FK e' cio' che lo rende
--    un vocabolario e non un suggerimento.
-- ============================================================
SELECT throws_ok(
    $$INSERT INTO config.codici_errore (codice, classe)
      VALUES ('TEST_CE_CLASSEFINTA', 'CLASSE_CHE_NON_ESISTE')$$,
    '23503',
    NULL,
    '2. Una classe fuori vocabolario non passa (FK verso config.classi_errore)'
);

-- ============================================================
-- 3) Una frase per un codice senza identita' non passa
--    E' l'anello che chiude la catena: senza, `codici_errore` sarebbe un
--    elenco parallelo che ci si puo' dimenticare di aggiornare.
-- ============================================================
SELECT throws_ok(
    $$INSERT INTO config.messaggi_errore (id, codice, lingua, messaggio)
      VALUES (9949, 'TEST_CE_SENZA_PADRE', 'it', 'Frase orfana.')$$,
    '23503',
    NULL,
    '3. Un messaggio per un codice SENZA riga in codici_errore non passa (FK)'
);

-- ============================================================
-- 4) …e lo stesso messaggio passa se il padre c'e'
--    ⚠️ Senza questo, il test 3 non distingue «la FK morde» da «l'INSERT e'
--    rotto per un altro motivo»: sarebbe verde anche con una colonna sbagliata.
-- ============================================================
SELECT lives_ok(
    $$INSERT INTO config.messaggi_errore (id, codice, lingua, messaggio)
      VALUES (9948, 'TEST_CE_VIVO', 'it', 'Frase con il suo codice.')$$,
    '4. Lo stesso messaggio passa se il codice esiste: la FK morde sul padre mancante, non sull''INSERT'
);

-- ============================================================
-- 5) Un codice ritirato risolve ancora
--    `obsoleto_dal` NON e' `attivo = false`: e' l'asse «selezionabile per il
--    nuovo». Finche' un percorso non bonificato lo solleva, chi legge deve
--    vedere una frase — non «[MESSAGGIO NON DEFINITO]».
-- ============================================================
SELECT is(
    script.fn_get_messaggio('TEST_CE_RITIRATO', NULL, 'it'),
    'Messaggio di un codice ritirato.',
    '5. Un codice RITIRATO risolve ancora il suo messaggio (obsoleto_dal non e'' attivo=false)'
);

-- ============================================================
-- 6) `note` su una riga sola
--    Il seed passa da un CSV, e le celle multi-riga in questo repo sono 3 in
--    tutto: il CHECK trasforma una raccomandazione in un fatto del dato.
-- ============================================================
SELECT throws_ok(
    $$INSERT INTO config.codici_errore (codice, classe, note)
      VALUES ('TEST_CE_NOTEMULTI', 'TECNICO', 'prima riga' || chr(10) || 'seconda riga')$$,
    '23514',
    NULL,
    '6. Una nota con un a capo non passa (CHECK: il seed passa da un CSV)'
);

-- ============================================================
-- 7) Il codice e' la chiave: niente spazi ai bordi
--    Due stringhe che differiscono per uno spazio sarebbero chiavi diverse che
--    a occhio sono uguali. Su una PK testuale e' la trappola piu' banale.
-- ============================================================
SELECT throws_ok(
    $$INSERT INTO config.codici_errore (codice, classe) VALUES (' TEST_CE_SPAZIO ', 'TECNICO')$$,
    '23514',
    NULL,
    '7. Un codice con spazi ai bordi non passa (CHECK: su una PK testuale sarebbe una chiave gemella invisibile)'
);

-- ============================================================
-- 8) L'invariante sui dati VERI, non sulla fixture
--    ⚠️ I test 1-7 collaudano il meccanismo su righe inventate: passerebbero
--    anche su un catalogo vuoto. Questo guarda i 689 codici seminati e chiede
--    che l'invariante regga sul dato reale — ed e' l'unico che si accorge se
--    un seed futuro dimentica un padre.
--    `bool_and` e non `LIMIT 1`: dice «NESSUNO e' orfano», non «uno a caso va bene».
-- ============================================================
SELECT ok(
    (SELECT bool_and(c.codice IS NOT NULL)
       FROM config.messaggi_errore m
       LEFT JOIN config.codici_errore c ON c.codice = m.codice),
    '8. Ogni codice del catalogo dei messaggi ha la sua riga di identita'' (invariante sui dati veri)'
);

SELECT * FROM finish();
ROLLBACK;
