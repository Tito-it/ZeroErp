-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: indice unico uq_indirizzi_ruolo_tipo_no_istanza su anagrafiche.indirizzi
--       (non è possibile avere due indirizzi con stesso
--        soggetto_ruolo_id + tipo_indirizzo_id, fuori da un'istanza)
--
-- Scenario:
--   - Costruisce un soggetto con ruolo CLIENTE (CL), senza indirizzi di ruolo
--   - Recupera il tipo indirizzo RES
--   - Crea un indirizzo_dettaglio di test
--   - Inserisce un indirizzo RES (OK)
--   - Tenta un secondo inserimento RES per lo stesso soggetto_ruolo
--     → deve fallire per violazione dell'indice unico (23505)
-- ------------------------------------------------------------

-- ============================================================================
-- rev 2026-09-23 — riscritto sul modello (brief-db-fixture-che-costruiscono-
-- giro-2, lotto 2). Il file usava il GESTORE, e aveva tre difetti in fila:
--   1. leggeva MIN(id) da anagrafiche.gestori, dato di MACCHINA: su un
--      database ricostruito (la CI) e' vuota;
--   2. RES NON e' ammesso per il ruolo GE (config.tipi_ruolo_tipi_indirizzo:
--      SEDELEG, FATT, SEDEOP), e create-gestore-indirizzo-res.sql asserisce
--      proprio che viene respinto: il primo INSERT non poteva riuscire, e il
--      23505 atteso non arrivava mai;
--   3. la «pulizia pre-test» cancellava i RES del gestore VERO (su dbdev),
--      salvato solo dal ROLLBACK.
-- Il soggetto del test — l'unicita' per (ruolo, tipo) — e' intatto. Cambia il
-- veicolo: un ruolo CL costruito, che RES lo ammette e non lo ha obbligatorio,
-- quindi nasce senza e non c'e' niente da pulire. Il vincolo ha cambiato nome:
-- oggi e' l'indice PARZIALE uq_indirizzi_ruolo_tipo_no_istanza
-- (WHERE istanza_utility_id IS NULL).
-- ============================================================================

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

SELECT plan(6);

-- =========================================================
-- 0) Costanti per indirizzo_dettaglio di test
-- =========================================================
-- ⚠️ Civico UNICO PER CORSA: con un civico fisso l'indirizzo_dettaglio
--   sarebbe di qualcun altro (uq_indirizzi_dettaglio_norm_v2).
CREATE TEMP TABLE tmp_costanti_indirizzo_unique AS
SELECT
    'VIA TEST UNIQUE RES'::text AS via_norm_test,
    (100000 + (abs(hashtext(clock_timestamp()::text)) % 800000))::text AS civico_norm_test,
    NULL::text                  AS interno_test,
    NULL::text                  AS piano_test,
    NULL::text                  AS palazzina_test;

-- =========================================================
-- 1) Il ruolo del test: un soggetto nuovo con ruolo CL.
--    Dopo la riga di contesto (il mondo c'e' gia'); cio' che i builder
--    scrivono si legge in un'istruzione SEPARATA.
-- =========================================================
CREATE TEMP TABLE tmp_soggetto_unique AS
SELECT dbops.fn_pgtap_crea_soggetto_pg('Cliente UNIQUE RES pgTAP') AS soggetto_id;

CREATE TEMP TABLE tmp_ruolo_unique_id AS
SELECT dbops.fn_pgtap_crea_soggetto_ruolo(t.soggetto_id, 'CL') AS soggetto_ruolo_id
FROM tmp_soggetto_unique t;

CREATE TEMP TABLE tmp_ruolo_unique AS
SELECT
    sr.id          AS soggetto_ruolo_id,
    sr.soggetto_id AS soggetto_id
FROM tmp_ruolo_unique_id r
JOIN anagrafiche.soggetti_ruoli sr
  ON sr.id = r.soggetto_ruolo_id;

SELECT ok(
    (SELECT count(*) FROM tmp_ruolo_unique) = 1,
    'Il ruolo CL del test e'' costruito e si legge'
);

-- =========================================================
-- 2) Recupero tipo indirizzo RES
-- =========================================================
CREATE TEMP TABLE tmp_tipo_indirizzo_res AS
SELECT
    ti.id,
    ti.codice_interno,
    ti.codice,
    ti.descrizione
FROM config.tipi_indirizzi ti
WHERE ti.codice_interno = 'RES';

SELECT ok(
    (SELECT count(*) FROM tmp_tipo_indirizzo_res) = 1,
    'Esiste il tipo indirizzo RES in config.tipi_indirizzi'
);

-- =========================================================
-- 3) indirizzo_dettaglio di test
-- =========================================================
CREATE TEMP TABLE tmp_stradario_unique AS
SELECT s.id
FROM config.stradario s
ORDER BY s.id
LIMIT 1;

WITH dati AS (
    SELECT
        s.id               AS stradario_id,
        k.civico_norm_test::integer AS civico,
        NULL::text         AS estensione_civico,
        k.palazzina_test   AS palazzina,
        k.interno_test     AS interno,
        k.piano_test       AS piano,
        k.via_norm_test    AS via_norm,
        k.civico_norm_test AS civico_norm
    FROM tmp_stradario_unique s,
         tmp_costanti_indirizzo_unique k
),
nuovo AS (
    INSERT INTO anagrafiche.indirizzi_dettaglio (
        stradario_id,
        civico,
        estensione_civico,
        palazzina,
        interno,
        piano,
        altro,
        via_norm,
        civico_norm,
        attivo,
        storicizza
    )
    SELECT
        d.stradario_id,
        d.civico,
        d.estensione_civico,
        d.palazzina,
        d.interno,
        d.piano,
        'Indirizzo test UNIQUE RES (pgTAP)',
        d.via_norm,
        d.civico_norm,
        TRUE,
        FALSE
    FROM dati d
    RETURNING id
)
SELECT id
INTO TEMP TABLE tmp_indirizzo_dettaglio_unique
FROM nuovo;

SELECT is(
    (SELECT count(*)::int FROM tmp_indirizzo_dettaglio_unique),
    1,
    'Inserito esattamente 1 indirizzo_dettaglio di test'
);

-- =========================================================
-- 4) Pre-condizione: il ruolo nuovo non ha RES (non e' obbligatorio per CL)
-- =========================================================
SELECT is(
    (
        SELECT count(*)::int
        FROM anagrafiche.indirizzi i
        JOIN tmp_ruolo_unique g
          ON g.soggetto_ruolo_id = i.soggetto_ruolo_id
        JOIN tmp_tipo_indirizzo_res t
          ON t.id = i.tipo_indirizzo_id
    ),
    0,
    'Pre-condizione: nessun indirizzo RES per il ruolo appena costruito'
);

-- =========================================================
-- 5) Primo inserimento RES (deve andare a buon fine)
-- =========================================================
INSERT INTO anagrafiche.indirizzi (
    soggetto_ruolo_id,
    tipo_indirizzo_id,
    indirizzo_dettaglio_id,
    indirizzo_libero,
    stato_id,
    administrative_area,
    locality,
    sublocality,
    postal_code,
    geoloc,
    comune_id,
    codice_postale_id,
    storicizza
)
SELECT
    g.soggetto_ruolo_id,
    t.id,
    idd.id,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    FALSE
FROM tmp_ruolo_unique g
JOIN tmp_tipo_indirizzo_res t
  ON TRUE
JOIN tmp_indirizzo_dettaglio_unique idd
  ON TRUE;

SELECT is(
    (
        SELECT count(*)::int
        FROM anagrafiche.indirizzi i
        JOIN tmp_ruolo_unique g
          ON g.soggetto_ruolo_id = i.soggetto_ruolo_id
        JOIN tmp_tipo_indirizzo_res t
          ON t.id = i.tipo_indirizzo_id
    ),
    1,
    'Dopo primo insert: esiste esattamente 1 indirizzo RES per il ruolo'
);

-- =========================================================
-- 6) Secondo inserimento RES: deve fallire per vincolo UNIQUE
-- =========================================================
SELECT throws_ok(
    $$
    INSERT INTO anagrafiche.indirizzi (
        soggetto_ruolo_id,
        tipo_indirizzo_id,
        indirizzo_dettaglio_id,
        indirizzo_libero,
        stato_id,
        administrative_area,
        locality,
        sublocality,
        postal_code,
        geoloc,
        comune_id,
        codice_postale_id,
        storicizza
    )
    SELECT
        g.soggetto_ruolo_id,
        t.id,
        idd.id,
        NULL,
        NULL,
        NULL,
        NULL,
        NULL,
        NULL,
        NULL,
        NULL,
        NULL,
        FALSE
    FROM tmp_ruolo_unique g
    JOIN tmp_tipo_indirizzo_res t
      ON TRUE
    JOIN tmp_indirizzo_dettaglio_unique idd
      ON TRUE;
    $$,
    '23505',
    NULL, 
    'L''indice unico uq_indirizzi_ruolo_tipo_no_istanza impedisce un secondo indirizzo RES per lo stesso soggetto_ruolo_id'
);

-- Fine test
SELECT * FROM finish();

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia nulla dietro di se'.
ROLLBACK;
