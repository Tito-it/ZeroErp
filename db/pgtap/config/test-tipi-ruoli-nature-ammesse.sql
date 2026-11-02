-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test tabella config.tipi_ruoli_nature_ammesse
-- Verifica: struttura, seed data, vincoli UNIQUE, CHECK, FK
--
-- Indice test:
--   1) Tabella config.tipi_ruoli_nature_ammesse esiste
--   2) Seed data: 19 righe totali
--   3) GE ammette solo PG (1 riga)
--   4) EF ammette solo PG (1 riga)
--   5) RIS_UMANA ammette solo PF (1 riga)
--   6) CL ammette PF, PG, ENC (3 righe)
--   7) FO ammette PF, PG, ENC (3 righe)
--   8) VT ammette PF, PG (2 righe)
--   9) UNIQUE constraint: duplicato (tipo_ruolo_id, tipo_soggetto_id) bloccato
--  10) CHECK: valido_al < valido_dal bloccato
--  11) FK tipo_ruolo_id: valore invalido bloccato
--  12) FK tipo_soggetto_id: valore invalido bloccato
-- ------------------------------------------------------------

-- ⚠️ Transazione, e non e' una formalita'. Il cleanup di questo file sta in
--   coda: col runner vero (pg_prove gira con ON_ERROR_STOP) un fallimento a
--   meta' non ci arriva mai, e i dati di prova restano nel database a rompere
--   la corsa successiva — che vede un rosso non suo.
--   Brief: brief-db-pgtap-runner-rls-baseline §15.3.
BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file diventerebbe verde per sottrazione. Nel DB ce ne sono 365.
--   IMMEDIATE li riporta a scattare a fine di OGNI istruzione — cioe' esatta-
--   mente come si comportavano prima, quando il file girava in autocommit e
--   ogni istruzione era una transazione a se'. In testa e non in coda apposta:
--   in coda scatterebbero tutti insieme DOPO il cleanup, su righe ormai
--   cancellate. Brief: brief-db-pgtap-runner-rls-baseline §17.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(12);

-- =========================================================
-- 1) La tabella esiste
-- =========================================================
SELECT has_table('config', 'tipi_ruoli_nature_ammesse', 'Tabella config.tipi_ruoli_nature_ammesse esiste');

-- =========================================================
-- 2) Seed data: 19 righe totali
-- =========================================================
SELECT is(
    (SELECT count(*)::int FROM config.tipi_ruoli_nature_ammesse),
    19,
    'Seed data: 19 righe totali in tipi_ruoli_nature_ammesse'
);

-- =========================================================
-- 3) GE ammette solo PG
-- =========================================================
SELECT is(
    (SELECT count(*)::int FROM config.tipi_ruoli_nature_ammesse
     WHERE tipo_ruolo_id = 3 AND attivo = true),
    1,
    'GE (id=3): ammette solo 1 natura (PG)'
);

-- =========================================================
-- 4) EF ammette solo PG
-- =========================================================
SELECT is(
    (SELECT count(*)::int FROM config.tipi_ruoli_nature_ammesse
     WHERE tipo_ruolo_id = 7 AND attivo = true),
    1,
    'EF (id=7): ammette solo 1 natura (PG)'
);

-- =========================================================
-- 5) RIS_UMANA ammette solo PF
-- =========================================================
SELECT is(
    (SELECT count(*)::int FROM config.tipi_ruoli_nature_ammesse
     WHERE tipo_ruolo_id = 14 AND attivo = true),
    1,
    'RIS_UMANA (id=14): ammette solo 1 natura (PF)'
);

-- =========================================================
-- 6) CL ammette PF, PG, ENC (3 righe)
-- =========================================================
SELECT is(
    (SELECT count(*)::int FROM config.tipi_ruoli_nature_ammesse
     WHERE tipo_ruolo_id = 1 AND attivo = true),
    3,
    'CL (id=1): ammette 3 nature (PF, PG, ENC)'
);

-- =========================================================
-- 7) FO ammette PF, PG, ENC (3 righe)
-- =========================================================
SELECT is(
    (SELECT count(*)::int FROM config.tipi_ruoli_nature_ammesse
     WHERE tipo_ruolo_id = 2 AND attivo = true),
    3,
    'FO (id=2): ammette 3 nature (PF, PG, ENC)'
);

-- =========================================================
-- 8) VT ammette PF, PG (2 righe)
-- =========================================================
SELECT is(
    (SELECT count(*)::int FROM config.tipi_ruoli_nature_ammesse
     WHERE tipo_ruolo_id = 9 AND attivo = true),
    2,
    'VT (id=9): ammette 2 nature (PF, PG)'
);

-- 🔴 `setval` RIMOSSO il 2026-08-18 — era la causa del rosso storico.
--   La colonna `id` E' GIA' `GENERATED BY DEFAULT AS IDENTITY` (attidentity='d',
--   nessun nextval come default): la convenzione del progetto e' rispettata.
--   Il seed CSV pero' inserisce gli id espliciti (1..19) senza far avanzare la
--   sequenza, quindi le tre INSERT qui sotto — che l'id NON lo passano — se lo
--   facevano assegnare da una sequenza rimasta a 1. Da qui il `setval`.
--
--   ⚠️ Ma `setval` su una sequenza identity vuole UPDATE sulla sequenza, e il
--   ruolo APPLICATIVO non ce l'ha — giustamente: nessuna applicazione deve
--   poter riavvolgere il contatore di una tabella. Il test moriva li'
--   («permesso negato per la sequenza»), 8 asserzioni su 12.
--
--   ⛔ Le due scorciatoie sarebbero state peggio del male: un GRANT darebbe
--   all'applicazione il diritto di resettare una identity, e marcare il file
--   `PGTAP_RUNNER=owner` gli farebbe saltare la RLS su TUTTE le altre
--   asserzioni per colpa di una riga.
--
--   ⭐ Si toglie il bisogno invece del permesso: le tre INSERT passano un `id`
--   esplicito, alto e fuori portata, e la sequenza non serve piu' a nessuno.
--
--   E c'e' un guadagno: il test 9 verifica l'UNIQUE (tipo_ruolo_id,
--   tipo_soggetto_id). Con l'id assegnato da una sequenza indietro poteva
--   sollevare `23505` per collisione di CHIAVE PRIMARIA — lo stesso SQLSTATE,
--   il vincolo sbagliato. Ora il 23505 puo' venire solo dall'UNIQUE che il test
--   dichiara di verificare.

-- =========================================================
-- 9) UNIQUE: duplicato (tipo_ruolo_id, tipo_soggetto_id) bloccato
-- =========================================================
SELECT throws_ok(
    $$
      INSERT INTO config.tipi_ruoli_nature_ammesse (id, tipo_ruolo_id, tipo_soggetto_id)
      VALUES ((SELECT MAX(id) + 1000 FROM config.tipi_ruoli_nature_ammesse), 3, 'PG');
    $$,
    '23505'
);

-- =========================================================
-- 10) Validita' rovesciata bloccata — dal guard comune delle date
--     🔴 SQLSTATE aggiornato il 2026-08-18: 23514 -> 22000.
--     Dalla migrazione a `daterange` nativo (2026-04-12, 18 tabelle) la
--     validita' non e' piu' due colonne con un CHECK sopra: e' un RANGE, e un
--     intervallo rovesciato lo rifiuta il COSTRUTTORE DEL TIPO — prima che
--     qualunque CHECK possa guardarlo.
--     ⭐ La garanzia non si e' indebolita, si e' spostata piu' in basso.
--     (Stessa correzione in test-permessi-user-overrides, tre asserzioni.)
--     ⭐ 2026-09-23 (brief-db-guard-date-validita): a rifiutare e' ora il
--     GUARD COMUNE delle date (script.trgfn_guard_date_validita, montato
--     dall'automazione DATE_VALIDITA). E' un BEFORE ROW, e i BEFORE girano
--     prima del calcolo della colonna generata: l'operatore legge
--     E_DATA_AL_MINORE_DAL invece della frase tecnica del daterange. Il
--     daterange resta sotto, come il CHECK: sono l'ultima difesa.
-- =========================================================
SELECT throws_like(
    $$
      INSERT INTO config.tipi_ruoli_nature_ammesse
        (id, tipo_ruolo_id, tipo_soggetto_id, valido_dal, valido_al)
      VALUES ((SELECT MAX(id) + 1001 FROM config.tipi_ruoli_nature_ammesse),
              3, 'ENC', '2026-06-01', '2026-01-01');
    $$,
    '%è inferiore alla data dal%',
    'Validita'' rovesciata (INSERT): parla il guard comune delle date, E_DATA_AL_MINORE_DAL'
);

-- =========================================================
-- 11) FK: tipo_ruolo_id invalido bloccato
-- =========================================================
SELECT throws_ok(
    $$
      INSERT INTO config.tipi_ruoli_nature_ammesse (id, tipo_ruolo_id, tipo_soggetto_id)
      VALUES ((SELECT MAX(id) + 1002 FROM config.tipi_ruoli_nature_ammesse), 9999, 'PG');
    $$,
    '23503'
);

-- =========================================================
-- 12) FK: tipo_soggetto_id invalido bloccato
-- =========================================================
SELECT throws_ok(
    $$
      INSERT INTO config.tipi_ruoli_nature_ammesse (tipo_ruolo_id, tipo_soggetto_id)
      VALUES (1, 'INVALIDO');
    $$,
    '23503'
);

-- Fine test
SELECT * FROM finish();

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia nulla dietro di se'. Le DELETE del cleanup restano
-- perche' dove sono un'asserzione devono girare davvero.
ROLLBACK;
