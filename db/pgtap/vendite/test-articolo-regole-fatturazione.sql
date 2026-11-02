-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: vincoli e regole base su vendite.articolo_regole_fatturazione
--       con riferimento a catalogo.articoli
--
-- Elenco test:
-- 1) Inserimento articolo di test
-- 2) Inserimento regola per articolo (1:1)
-- 3) FK su articolo_id inesistente
-- 4) Check calcolo_qta_padre
-- 5) Check decimali importi
-- 6) Unicità articolo_id
--
-- Nota: il caso "Check visibilita_componenti" è stato rimosso il 2026-07-28
-- (colonna e CHECK eliminati dal changeset 20260728-18).
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

SELECT plan(6);

-- ============================================================
-- 0) Costanti
-- ============================================================
CREATE TEMP TABLE tmp_costanti_arf AS
SELECT
    'pgtap_articolo_regole_fatturazione'::text AS test_scope,
    ('PGTAP-ARF-' || to_char(clock_timestamp(), 'YYYYMMDDHH24MISSMS'))::text AS codice_articolo,
    -- catalogo.articoli.uom_id e' NOT NULL: senza, la fixture esplode alla
    -- prima INSERT e il file non esegue NESSUNA asserzione (era il rosso
    -- ERRORE_FIXTURE in baseline-rossi.tsv). Stesso pattern degli altri pgTAP
    -- vendite: si prende la prima UoM attiva, ordinata per id perche' il test
    -- non dipende da QUALE unita' sia — serve solo che la FK sia soddisfatta.
    (SELECT id
       FROM catalogo.unita_misura
      WHERE attivo IS TRUE
      ORDER BY id
      LIMIT 1) AS uom_id;

-- ============================================================
-- 1) Inserimento articolo di test
-- ============================================================
CREATE TEMP TABLE tmp_articolo AS
WITH ins AS (
    INSERT INTO catalogo.articoli (
        codice,
        descrizione,
        uom_id,
        meta
    )
    SELECT
        k.codice_articolo,
        'Articolo test regole fatturazione',
        k.uom_id,
        jsonb_build_object('test_scope', k.test_scope)
    FROM tmp_costanti_arf k
    RETURNING id
)
SELECT id FROM ins;

SELECT is(
    (SELECT count(*)::int FROM tmp_articolo),
    1,
    'Inserito articolo di test in catalogo.articoli'
);

-- ============================================================
-- 2) Inserimento regole fatturazione
-- ============================================================
CREATE TEMP TABLE tmp_regola AS
WITH ins AS (
    INSERT INTO vendite.articolo_regole_fatturazione (
        articolo_id,
        meta
    )
    SELECT
        a.id,
        jsonb_build_object('test_scope', k.test_scope)
    FROM tmp_articolo a,
         tmp_costanti_arf k
    RETURNING id
)
SELECT id FROM ins;

SELECT is(
    (SELECT count(*)::int FROM tmp_regola),
    1,
    'Inserita regola per articolo (1:1)'
);

-- ============================================================
-- 3) FK: articolo_id inesistente
-- ============================================================
SELECT throws_ok(
    $$
    INSERT INTO vendite.articolo_regole_fatturazione (
        articolo_id
    )
    VALUES (uuidv7());
    $$,
    '23503',
    NULL,
    'FK violation su articolo_id inesistente'
);

-- Qui stava il caso "Check visibilita_componenti". La colonna e il suo CHECK
-- sono usciti dal modello con il changeset 20260728-18: non era la regola di
-- esposizione dei componenti in fattura (lo è `esposizione_in_fattura` per
-- componente, booleano `esposto_in_fattura` fino al 2026-10-01) e nessun consumatore vivo la applicava.
-- Rimosso il 2026-07-28 — brief-db-ritiro-generatore-righe-fattura-sql §5-bis.

-- ============================================================
-- 4) Check calcolo_qta_padre
-- ============================================================
SELECT throws_ok(
    $$
    UPDATE vendite.articolo_regole_fatturazione
       SET calcolo_qta_padre = 'non_valido'
     WHERE id = (SELECT id FROM tmp_regola);
    $$,
    '23514',
    NULL,
    'Check calcolo_qta_padre non valido'
);

-- ============================================================
-- 5) Check decimali importi
-- ============================================================
SELECT throws_ok(
    $$
    UPDATE vendite.articolo_regole_fatturazione
       SET arrotondamento_importi_dec = 7
     WHERE id = (SELECT id FROM tmp_regola);
    $$,
    '23514',
    NULL,
    'Check decimali importi fuori range'
);

-- ============================================================
-- 6) Unicità articolo_id
-- ============================================================
SELECT throws_ok(
    $$
    INSERT INTO vendite.articolo_regole_fatturazione (
        articolo_id
    )
    VALUES ((SELECT id FROM tmp_articolo));
    $$,
    '23505',
    NULL,
    'Unicità su articolo_id (1:1)'
);

-- Cleanup
DELETE FROM vendite.articolo_regole_fatturazione
WHERE meta ->> 'test_scope' = (SELECT test_scope FROM tmp_costanti_arf);

DELETE FROM catalogo.articoli
WHERE meta ->> 'test_scope' = (SELECT test_scope FROM tmp_costanti_arf);

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia nulla dietro di se'. Le DELETE del cleanup restano
-- perche' dove sono un'asserzione devono girare davvero.
ROLLBACK;
