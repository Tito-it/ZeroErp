-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test cascata indirizzi con istanza_utility_id:
--   - Partial unique index (istanza NULL e valorizzato)
--   - fn_get_indirizzi_by_ruolo con p_istanza_utility_id
--   - fn_get_indirizzo cascata 3 livelli: istanza -> generico -> soggetto
--   - Viste resolved espongono istanza_utility_id
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
--   ogni istruzione era una transazione a se'. Messa in testa e non in coda
--   apposta: in coda scatterebbero tutti insieme DOPO il cleanup, su righe
--   ormai cancellate, e fallirebbero per un motivo che non riguarda il test.
--   Brief: brief-db-pgtap-runner-rls-baseline §17.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(14);

-- Indice test (14):
--  1) Esiste almeno un cliente con istanza_utility_id
--  2) Upsert indirizzo_dettaglio di test
--  3) Pre-condizione: pulizia indirizzi DOMFISC/FATT per il ruolo test
--  4) Inserimento DOMFISC generico (istanza NULL) riuscito
--  5) Inserimento FATT per istanza specifica riuscito
--  6) Partial unique: blocco duplicato DOMFISC generico
--  7) fn_get_indirizzi_by_ruolo senza istanza: restituisce tutti
--  8) fn_get_indirizzi_by_ruolo con istanza: restituisce istanza + generici
--  9) fn_get_indirizzo con istanza: priorita FATT istanza > DOMFISC generico
-- 10) fn_get_indirizzo senza istanza: restituisce DOMFISC generico
-- 11) fn_get_indirizzo fallback soggetto: se ruolo vuoto, usa soggetto
-- 12) vw_indirizzi_resolved_ruolo espone istanza_utility_id
-- 13) vw_indirizzi_resolved_all espone istanza_utility_id per riga istanza
-- 14) Pulizia post-test

-- =========================================================
-- 0) Setup: stradario, cliente con istanza
-- =========================================================
CREATE TEMP TABLE tmp_stradario_ut AS
SELECT s.id FROM config.stradario s ORDER BY s.id LIMIT 1;

-- Cliente di test (ruolo CLIENTE, ha istanza_utility_id)
-- DOMFISC e FATT sono ammessi per tipo_ruolo CL
--
-- rev 2026-09-23 (brief-db-fixture-che-costruiscono-giro-2, lotto 2).
--   Il cliente si PESCAVA («il primo di anagrafiche.clienti con istanza»):
--   su un database ricostruito (la CI) la tabella e' vuota, e il file
--   restava con dieci asserzioni rosse su quattordici. Al test serve la
--   terna (ruolo CL, soggetto, istanza), non la riga di clienti — il suo
--   id non era usato da nessuna asserzione, e la colonna cliente_id esce.
--   Ora la terna viene da dbops.fn_pgtap_crea_cliente_ba; ruolo e soggetto
--   sono nuovi, quindi le DELETE di «pulizia» sul ruolo non trovano niente.
--   ⛔ Cio' che il builder scrive si legge in un'istruzione SEPARATA.
CREATE TEMP TABLE tmp_cli_ind AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('indirizzi istanza cascata');

CREATE TEMP TABLE tmp_ctx AS
SELECT
    c.soggetto_ruolo_id,
    c.soggetto_id,
    c.istanza_utility_id
FROM tmp_cli_ind c;

SELECT ok(
    (SELECT count(*) FROM tmp_ctx) = 1,
    '1) Cliente con istanza_utility_id costruito'
);

-- =========================================================
-- Upsert indirizzo_dettaglio di test
-- =========================================================
WITH upsert AS (
    INSERT INTO anagrafiche.indirizzi_dettaglio (
        stradario_id, civico, estensione_civico, palazzina, interno, piano,
        altro, via_norm, civico_norm, attivo, storicizza
    )
    SELECT s.id, 998, NULL, NULL, NULL, NULL,
        'Test istanza cascata (pgTAP)', 'VIA TEST ISTANZA', '998', TRUE, FALSE
    FROM tmp_stradario_ut s
    ON CONFLICT (stradario_id, civico, estensione_civico, palazzina, scala, piano, interno)
    DO UPDATE SET data_update = now(), user_update = CURRENT_USER
    RETURNING id
)
SELECT id INTO TEMP TABLE tmp_idd_ut FROM upsert;

SELECT is(
    (SELECT count(*)::int FROM tmp_idd_ut), 1,
    '2) Upsert indirizzo_dettaglio: ottenuto esattamente 1 id'
);

-- =========================================================
-- Pulizia pre-test
-- =========================================================
DELETE FROM anagrafiche.indirizzi i
USING tmp_ctx g
WHERE i.soggetto_ruolo_id = g.soggetto_ruolo_id
  AND i.tipo_indirizzo_id IN (
    SELECT ti.id FROM config.tipi_indirizzi ti
    WHERE ti.codice_interno IN ('DOMFISC', 'FATT')
  );

SELECT is(
    (
        SELECT count(*)::int FROM anagrafiche.indirizzi i
        JOIN tmp_ctx g ON g.soggetto_ruolo_id = i.soggetto_ruolo_id
        WHERE i.tipo_indirizzo_id IN (
            SELECT ti.id FROM config.tipi_indirizzi ti
            WHERE ti.codice_interno IN ('DOMFISC', 'FATT')
        )
    ),
    0,
    '3) Pre-condizione: nessun DOMFISC/FATT per il ruolo test'
);

-- =========================================================
-- 4) Inserimento DOMFISC generico (istanza NULL)
-- =========================================================
INSERT INTO anagrafiche.indirizzi (
    soggetto_ruolo_id, tipo_indirizzo_id, indirizzo_dettaglio_id,
    istanza_utility_id, storicizza
)
SELECT
    g.soggetto_ruolo_id,
    (SELECT id FROM config.tipi_indirizzi WHERE codice_interno = 'DOMFISC'),
    idd.id,
    NULL,
    FALSE
FROM tmp_ctx g, tmp_idd_ut idd;

SELECT is(
    (
        SELECT count(*)::int FROM anagrafiche.indirizzi i
        JOIN tmp_ctx g ON g.soggetto_ruolo_id = i.soggetto_ruolo_id
        WHERE i.tipo_indirizzo_id = (SELECT id FROM config.tipi_indirizzi WHERE codice_interno = 'DOMFISC')
          AND i.istanza_utility_id IS NULL
    ),
    1,
    '4) DOMFISC generico (istanza NULL) inserito'
);

-- =========================================================
-- 5) Inserimento FATT per istanza specifica
-- =========================================================
INSERT INTO anagrafiche.indirizzi (
    soggetto_ruolo_id, tipo_indirizzo_id, indirizzo_dettaglio_id,
    istanza_utility_id, storicizza
)
SELECT
    g.soggetto_ruolo_id,
    (SELECT id FROM config.tipi_indirizzi WHERE codice_interno = 'FATT'),
    idd.id,
    g.istanza_utility_id,
    FALSE
FROM tmp_ctx g, tmp_idd_ut idd;

SELECT is(
    (
        SELECT count(*)::int FROM anagrafiche.indirizzi i
        JOIN tmp_ctx g ON g.soggetto_ruolo_id = i.soggetto_ruolo_id
        WHERE i.tipo_indirizzo_id = (SELECT id FROM config.tipi_indirizzi WHERE codice_interno = 'FATT')
          AND i.istanza_utility_id = g.istanza_utility_id
    ),
    1,
    '5) FATT per istanza specifica inserito'
);

-- =========================================================
-- 6) Partial unique: duplicato DOMFISC generico bloccato
-- =========================================================
SELECT throws_ok(
    $$
    INSERT INTO anagrafiche.indirizzi (
        soggetto_ruolo_id, tipo_indirizzo_id, indirizzo_dettaglio_id,
        istanza_utility_id, storicizza
    )
    SELECT
        g.soggetto_ruolo_id,
        (SELECT id FROM config.tipi_indirizzi WHERE codice_interno = 'DOMFISC'),
        idd.id,
        NULL,
        FALSE
    FROM tmp_ctx g, tmp_idd_ut idd;
    $$,
    '23505',
    NULL,
    '6) Partial unique blocca duplicato DOMFISC generico (istanza NULL)'
);

-- =========================================================
-- 7) fn_get_indirizzi_by_ruolo senza istanza: tutti gli indirizzi
-- =========================================================
SELECT ok(
    (
        SELECT count(*)::int
        FROM script.fn_get_indirizzi_by_ruolo(
            (SELECT soggetto_ruolo_id FROM tmp_ctx)
        )
    ) >= 2,
    '7) fn_get_indirizzi_by_ruolo senza istanza: almeno 2 indirizzi (DOMFISC + FATT)'
);

-- =========================================================
-- 8) fn_get_indirizzi_by_ruolo con istanza: istanza + generici
-- =========================================================
SELECT ok(
    (
        SELECT count(*)::int
        FROM script.fn_get_indirizzi_by_ruolo(
            (SELECT soggetto_ruolo_id FROM tmp_ctx),
            (SELECT istanza_utility_id FROM tmp_ctx)
        )
    ) >= 2,
    '8) fn_get_indirizzi_by_ruolo con istanza: FATT istanza + DOMFISC generico'
);

-- =========================================================
-- 9) fn_get_indirizzo con istanza: FATT istanza ha priorita
-- =========================================================
-- ⚠️ rev 2026-09-23 (20260923-49): si asserisce il TIPO per id, non il
--   testo. La colonna tipo_indirizzo porta il CODICE (display, mutabile:
--   'DOM-FISC'), il parametro e' il CODICE_INTERNO ('DOMFISC'): confrontare
--   il testo misurerebbe un'etichetta. Il 10 era rosso per il difetto vero
--   (fn_get_indirizzo confrontava codice con codice_interno e non trovava mai
--   il DOMFISC di ruolo), corretto da 20260923-49.
SELECT results_eq(
    $$
    SELECT f.tipo_indirizzo_id, f.istanza_utility_id
    FROM script.fn_get_indirizzo(
        (SELECT soggetto_ruolo_id FROM tmp_ctx),
        'FATT',
        (SELECT istanza_utility_id FROM tmp_ctx)
    ) f
    $$,
    $$SELECT ti.id, (SELECT istanza_utility_id FROM tmp_ctx)
        FROM config.tipi_indirizzi ti WHERE ti.codice_interno = 'FATT'$$,
    '9) fn_get_indirizzo con istanza: trova FATT per istanza specifica'
);

-- =========================================================
-- 10) fn_get_indirizzo senza istanza: DOMFISC generico
-- =========================================================
SELECT results_eq(
    $$
    SELECT f.tipo_indirizzo_id, f.istanza_utility_id
    FROM script.fn_get_indirizzo(
        (SELECT soggetto_ruolo_id FROM tmp_ctx),
        'DOMFISC'
    ) f
    $$,
    $$SELECT ti.id, NULL::bigint
        FROM config.tipi_indirizzi ti WHERE ti.codice_interno = 'DOMFISC'$$,
    '10) fn_get_indirizzo senza istanza: trova il DOMFISC generico del RUOLO'
);

-- =========================================================
-- 11) fn_get_indirizzo fallback soggetto: tipo non presente su ruolo
-- =========================================================
SELECT ok(
    (
        SELECT count(*)::int
        FROM script.fn_get_indirizzo(
            (SELECT soggetto_ruolo_id FROM tmp_ctx),
            'RES'
        ) f
    ) >= 0,
    '11) fn_get_indirizzo per RES: 0 o piu righe (fallback soggetto se esiste)'
);

-- =========================================================
-- 12) vw_indirizzi_resolved_ruolo espone istanza_utility_id
-- =========================================================
SELECT ok(
    (
        SELECT count(*)::int
        FROM anagrafiche.vw_indirizzi_resolved_ruolo r
        JOIN tmp_ctx g ON g.soggetto_ruolo_id = r.soggetto_ruolo_id
        WHERE r.tipo_indirizzo_codice = 'FATT'
          AND r.istanza_utility_id = g.istanza_utility_id
    ) = 1,
    '12) vw_indirizzi_resolved_ruolo: FATT con istanza_utility_id valorizzato'
);

-- =========================================================
-- 13) vw_indirizzi_resolved_all espone istanza_utility_id
-- =========================================================
SELECT ok(
    (
        SELECT count(*)::int
        FROM anagrafiche.vw_indirizzi_resolved_all r
        JOIN tmp_ctx g ON g.soggetto_ruolo_id = r.soggetto_ruolo_id
        WHERE r.tipo_indirizzo_codice = 'FATT'
          AND r.istanza_utility_id IS NOT NULL
    ) = 1,
    '13) vw_indirizzi_resolved_all: FATT con istanza_utility_id valorizzato'
);

-- =========================================================
-- 14) Pulizia post-test: rimuove indirizzi di test
-- =========================================================
DELETE FROM anagrafiche.indirizzi i
USING tmp_ctx g
WHERE i.soggetto_ruolo_id = g.soggetto_ruolo_id
  AND i.tipo_indirizzo_id IN (
    SELECT ti.id FROM config.tipi_indirizzi ti
    WHERE ti.codice_interno IN ('DOMFISC', 'FATT')
  );

SELECT ok(
    (
        SELECT count(*)::int FROM anagrafiche.indirizzi i
        JOIN tmp_ctx g ON g.soggetto_ruolo_id = i.soggetto_ruolo_id
        WHERE i.tipo_indirizzo_id IN (
            SELECT ti.id FROM config.tipi_indirizzi ti
            WHERE ti.codice_interno IN ('DOMFISC', 'FATT')
        )
    ) = 0,
    '14) Pulizia post-test: indirizzi DOMFISC/FATT rimossi'
);

-- Fine test
SELECT * FROM finish();

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia nulla dietro di se'. Le DELETE del cleanup restano
-- perche' dove sono un'asserzione devono girare davvero.
ROLLBACK;
