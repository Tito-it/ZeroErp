-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: guard transizione stato su vendite.listini_versioni
--       (migration 20260424-01-create-trgfn-listini-versioni-guard-transizione-stato)
--       + funzione batch vendite.fn_listini_versioni_close_scadute
--       (migration 20260424-02-create-fn-listini-versioni-close-scadute).
--
-- Indice test (1..10):
--   1) BOZZA  -> ATTIVA ammesso
--   2) ATTIVA -> BOZZA  vietato (E_VERSIONE_STATO_TRANSIZIONE_INVALIDA)
--   3) ATTIVA -> CHIUSA con valido_al NULL vietato
--   4) ATTIVA -> CHIUSA con valido_al futuro vietato
--   5) ATTIVA -> CHIUSA con valido_al scaduto ammesso
--   6) BOZZA  -> CHIUSA vietato
--   7) CHIUSA -> ATTIVA vietato
--   8) fn_listini_versioni_close_scadute chiude ATTIVA con valido_al scaduto
--   9) fn_listini_versioni_close_scadute NON tocca ATTIVA con valido_al futuro
--  10) ATTIVA -> ATTIVA no-op ammesso (WHEN distinct filter)
--
-- Strategia fixture:
--   - Creo un nuovo listino clonando i FK (utility_id, tipologia_id,
--     emittente_soggetto_ruolo_id) da un listino esistente; codice
--     random via md5(clock_timestamp). Garantisce zero collisioni con
--     seed / altre ATTIVE sullo stesso listino.
--   - Ogni test usa la propria versione (codice_versione univoco
--     A..H) con intervalli temporali non sovrapposti per non violare
--     l'EXCLUDE ex_listini_versioni_no_overlap (filtro ATTIVA).
--   - Versioni CHIUSA e BOZZA non partecipano al no-overlap, quindi
--     nessun vincolo di range per loro.
--   - BEGIN + ROLLBACK finale: nessun dato persiste.
--
-- Nota: il trigger scatta solo su UPDATE OF stato; INSERT e' libero
-- e non viene vincolato dal guard (regola esplicita: consentire
-- seed/import con stato diretto).
-- ------------------------------------------------------------

BEGIN;
-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(10);

-- ============================================================
-- Setup: listino nuovo con FK clonati da listino seedato
-- ============================================================
CREATE TEMP TABLE tmp_listino AS
WITH ins AS (
    INSERT INTO vendite.listini (
        codice, descrizione, utility_id, tipologia_id, emittente_soggetto_ruolo_id
    )
    SELECT 'PGTAP_LV_TRANS_' || substr(md5(clock_timestamp()::text), 1, 10),
           'Listino pgtap guard transizione stato v1',
           utility_id, tipologia_id, emittente_soggetto_ruolo_id
      FROM vendite.listini
     ORDER BY id
     LIMIT 1
    RETURNING id
)
SELECT id AS listino_id FROM ins;

-- Inserisco tutte le versioni up-front. L'INSERT e' libero (nessun
-- guard transizione). Intervalli scelti per non sovrapporsi fra ATTIVE:
--   Slot_A  BOZZA   2080-01-01..2080-12-31   (test 1,2)
--   Slot_B  ATTIVA  2081-01-01..2081-12-31   (test 3,4)
--   Slot_C  ATTIVA  2020-01-01..2020-12-31   (test 5, scaduta)
--   Slot_D  BOZZA   NULL..NULL               (test 6)
--   Slot_E  CHIUSA  2019-01-01..2019-12-31   (test 7)
--   Slot_F  ATTIVA  2022-01-01..2022-12-31   (test 8, scaduta)
--   Slot_H  ATTIVA  2083-01-01..2083-12-31   (test 9, futura)
--   Slot_I  ATTIVA  2084-01-01..2084-12-31   (test 10, no-op)

INSERT INTO vendite.listini_versioni (listino_id, codice_versione, valido_dal, valido_al, stato)
SELECT listino_id, 'A', DATE '2080-01-01', DATE '2080-12-31', 'BOZZA'  FROM tmp_listino;

INSERT INTO vendite.listini_versioni (listino_id, codice_versione, valido_dal, valido_al, stato)
SELECT listino_id, 'B', DATE '2081-01-01', DATE '2081-12-31', 'ATTIVA' FROM tmp_listino;

INSERT INTO vendite.listini_versioni (listino_id, codice_versione, valido_dal, valido_al, stato)
SELECT listino_id, 'C', DATE '2020-01-01', DATE '2020-12-31', 'ATTIVA' FROM tmp_listino;

INSERT INTO vendite.listini_versioni (listino_id, codice_versione, valido_dal, valido_al, stato)
SELECT listino_id, 'D', DATE '2082-01-01', NULL,              'BOZZA'  FROM tmp_listino;

INSERT INTO vendite.listini_versioni (listino_id, codice_versione, valido_dal, valido_al, stato)
SELECT listino_id, 'E', DATE '2019-01-01', DATE '2019-12-31', 'CHIUSA' FROM tmp_listino;

INSERT INTO vendite.listini_versioni (listino_id, codice_versione, valido_dal, valido_al, stato)
SELECT listino_id, 'F', DATE '2022-01-01', DATE '2022-12-31', 'ATTIVA' FROM tmp_listino;

INSERT INTO vendite.listini_versioni (listino_id, codice_versione, valido_dal, valido_al, stato)
SELECT listino_id, 'H', DATE '2083-01-01', DATE '2083-12-31', 'ATTIVA' FROM tmp_listino;

INSERT INTO vendite.listini_versioni (listino_id, codice_versione, valido_dal, valido_al, stato)
SELECT listino_id, 'I', DATE '2084-01-01', DATE '2084-12-31', 'ATTIVA' FROM tmp_listino;

-- ============================================================
-- 1) BOZZA -> ATTIVA ammesso (Slot_A)
-- ============================================================
SELECT lives_ok(
    $$UPDATE vendite.listini_versioni
         SET stato = 'ATTIVA'
       WHERE listino_id = (SELECT listino_id FROM tmp_listino)
         AND codice_versione = 'A'$$,
    'BOZZA -> ATTIVA e'' una transizione ammessa dal workflow'
);

-- ============================================================
-- 2) ATTIVA -> BOZZA vietato (Slot_A e'' ora ATTIVA dopo test 1)
-- ============================================================
SELECT throws_ok(
    $$UPDATE vendite.listini_versioni
         SET stato = 'BOZZA'
       WHERE listino_id = (SELECT listino_id FROM tmp_listino)
         AND codice_versione = 'A'$$,
    'P0001',
    NULL,
    'ATTIVA -> BOZZA deve essere bloccato (stato immutabile all''indietro)'
);

-- ============================================================
-- 3) ATTIVA -> CHIUSA con valido_al NULL vietato (Slot_B)
--    Tentativo: UPDATE SET stato='CHIUSA', valido_al=NULL
-- ============================================================
SELECT throws_ok(
    $$UPDATE vendite.listini_versioni
         SET stato = 'CHIUSA',
             valido_al = NULL
       WHERE listino_id = (SELECT listino_id FROM tmp_listino)
         AND codice_versione = 'B'$$,
    'P0001',
    NULL,
    'ATTIVA -> CHIUSA con valido_al NULL deve essere bloccato (precondizione temporale)'
);

-- ============================================================
-- 4) ATTIVA -> CHIUSA con valido_al futuro vietato (Slot_B)
--    Slot_B ha valido_al = 2081-12-31 (futuro); UPDATE solo di stato.
-- ============================================================
SELECT throws_ok(
    $$UPDATE vendite.listini_versioni
         SET stato = 'CHIUSA'
       WHERE listino_id = (SELECT listino_id FROM tmp_listino)
         AND codice_versione = 'B'$$,
    'P0001',
    NULL,
    'ATTIVA -> CHIUSA con valido_al futuro deve essere bloccato'
);

-- ============================================================
-- 5) ATTIVA -> CHIUSA con valido_al scaduto ammesso (Slot_C)
--    Slot_C ha valido_al = 2020-12-31 (passato) -> guard passa.
-- ============================================================
SELECT lives_ok(
    $$UPDATE vendite.listini_versioni
         SET stato = 'CHIUSA'
       WHERE listino_id = (SELECT listino_id FROM tmp_listino)
         AND codice_versione = 'C'$$,
    'ATTIVA -> CHIUSA con valido_al scaduto e'' ammessa'
);

-- ============================================================
-- 6) BOZZA -> CHIUSA vietato (Slot_D)
-- ============================================================
SELECT throws_ok(
    $$UPDATE vendite.listini_versioni
         SET stato = 'CHIUSA'
       WHERE listino_id = (SELECT listino_id FROM tmp_listino)
         AND codice_versione = 'D'$$,
    'P0001',
    NULL,
    'BOZZA -> CHIUSA deve essere bloccato (la bozza si cancella, non si chiude)'
);

-- ============================================================
-- 7) CHIUSA -> ATTIVA vietato (Slot_E)
-- ============================================================
SELECT throws_ok(
    $$UPDATE vendite.listini_versioni
         SET stato = 'ATTIVA'
       WHERE listino_id = (SELECT listino_id FROM tmp_listino)
         AND codice_versione = 'E'$$,
    'P0001',
    NULL,
    'CHIUSA -> ATTIVA deve essere bloccato (stato terminale)'
);

-- ============================================================
-- 8) fn_listini_versioni_close_scadute chiude Slot_F (valido_al scaduto)
-- ============================================================
-- Slot_F e'' ATTIVA con valido_al = 2022-12-31 (scaduto); la funzione
-- deve chiuderla. Nota: anche Slot_C (gia'' chiusa al test 5) non sara''
-- piu'' selezionata (gia'' CHIUSA). Verifichiamo puntualmente Slot_F.
DO $$ BEGIN PERFORM vendite.fn_listini_versioni_close_scadute(); END $$;

SELECT is(
    (SELECT stato FROM vendite.listini_versioni
      WHERE listino_id = (SELECT listino_id FROM tmp_listino)
        AND codice_versione = 'F'),
    'CHIUSA'::varchar,
    'fn_listini_versioni_close_scadute chiude Slot_F (ATTIVA scaduta)'
);

-- ============================================================
-- 9) fn_listini_versioni_close_scadute NON tocca Slot_H (valido_al futuro)
-- ============================================================
SELECT is(
    (SELECT stato FROM vendite.listini_versioni
      WHERE listino_id = (SELECT listino_id FROM tmp_listino)
        AND codice_versione = 'H'),
    'ATTIVA'::varchar,
    'fn_listini_versioni_close_scadute NON tocca Slot_H (ATTIVA con valido_al futuro)'
);

-- ============================================================
-- 10) ATTIVA -> ATTIVA no-op (WHEN distinct filter skippa il guard)
-- ============================================================
-- Il trigger ha WHEN (OLD.stato IS DISTINCT FROM NEW.stato): UPDATE
-- che non cambia stato non deve invocare il guard. Assert: lives.
SELECT lives_ok(
    $$UPDATE vendite.listini_versioni
         SET stato = 'ATTIVA'
       WHERE listino_id = (SELECT listino_id FROM tmp_listino)
         AND codice_versione = 'I'$$,
    'ATTIVA -> ATTIVA (no-op) non deve invocare il guard'
);

SELECT * FROM finish();
ROLLBACK;
