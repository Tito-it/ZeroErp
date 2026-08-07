-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: vincolo uq_indirizzi_ruolo_tipo su anagrafiche.indirizzi
--       (non è possibile avere due indirizzi con stesso
--        soggetto_ruolo_id + tipo_indirizzo_id)
--
-- Scenario:
--   - Recupera il primo Gestore
--   - Recupera il tipo indirizzo RES
--   - Upsert di un indirizzo_dettaglio di test (come negli altri test)
--   - Pulisce eventuali indirizzi RES per quel soggetto_ruolo
--   - Inserisce un indirizzo RES (OK)
--   - Tenta un secondo inserimento RES per lo stesso soggetto_ruolo
--     → deve fallire per violazione del vincolo uq_indirizzi_ruolo_tipo (23505)
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

SELECT plan(6);

-- =========================================================
-- 0) Costanti per indirizzo_dettaglio di test
-- =========================================================
CREATE TEMP TABLE tmp_costanti_indirizzo_unique AS
SELECT
    'VIA TEST UNIQUE RES'::text AS via_norm_test,
    '1'::text                   AS civico_norm_test,
    NULL::text                  AS interno_test,
    NULL::text                  AS piano_test,
    NULL::text                  AS palazzina_test;

-- =========================================================
-- 1) Recupero Gestore e soggetto_ruolo
-- =========================================================
CREATE TEMP TABLE tmp_first_gestore_unique AS
SELECT MIN(id) AS gestore_id
FROM anagrafiche.gestori;

CREATE TEMP TABLE tmp_gestore_unique AS
SELECT
    g.id                AS gestore_id,
    g.soggetto_ruolo_id AS soggetto_ruolo_id,
    sr.soggetto_id      AS soggetto_id
FROM anagrafiche.gestori g
JOIN tmp_first_gestore_unique fg
  ON g.id = fg.gestore_id
JOIN anagrafiche.soggetti_ruoli sr
  ON sr.id = g.soggetto_ruolo_id;

SELECT ok(
    (SELECT count(*) FROM tmp_gestore_unique) = 1,
    'Esiste almeno un Gestore (tmp_gestore_unique valorizzata)'
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
-- 3) Upsert indirizzo_dettaglio di test
-- =========================================================
CREATE TEMP TABLE tmp_stradario_unique AS
SELECT s.id
FROM config.stradario s
ORDER BY s.id
LIMIT 1;

WITH dati AS (
    SELECT
        s.id               AS stradario_id,
        1                  AS civico,
        NULL::text         AS estensione_civico,
        k.palazzina_test   AS palazzina,
        k.interno_test     AS interno,
        k.piano_test       AS piano,
        k.via_norm_test    AS via_norm,
        k.civico_norm_test AS civico_norm
    FROM tmp_stradario_unique s,
         tmp_costanti_indirizzo_unique k
),
upsert AS (
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
    ON CONFLICT (
        stradario_id,
        civico,
        COALESCE(estensione_civico, ''::character varying),
        COALESCE(palazzina, ''::character varying),
        COALESCE(scala, ''::character varying),
        COALESCE(piano, ''::character varying),
        COALESCE(interno, ''::character varying)
    )
    DO UPDATE
       SET data_update = now(),
           user_update = CURRENT_USER
    RETURNING id
)
SELECT id
INTO TEMP TABLE tmp_indirizzo_dettaglio_unique
FROM upsert;

SELECT is(
    (SELECT count(*)::int FROM tmp_indirizzo_dettaglio_unique),
    1,
    'Upsert indirizzo_dettaglio unique: ottenuto esattamente 1 id (nuovo o esistente)'
);

-- =========================================================
-- 4) Pulizia pre-test: elimino eventuali RES per il soggetto_ruolo scelto
-- =========================================================
DELETE FROM anagrafiche.indirizzi i
USING tmp_gestore_unique g, tmp_tipo_indirizzo_res t
WHERE i.soggetto_ruolo_id = g.soggetto_ruolo_id
  AND i.tipo_indirizzo_id = t.id;

-- Verifica che non ci siano più RES per quel soggetto_ruolo
SELECT is(
    (
        SELECT count(*)::int
        FROM anagrafiche.indirizzi i
        JOIN tmp_gestore_unique g
          ON g.soggetto_ruolo_id = i.soggetto_ruolo_id
        JOIN tmp_tipo_indirizzo_res t
          ON t.id = i.tipo_indirizzo_id
    ),
    0,
    'Pre-condizione: nessun indirizzo RES per il soggetto_ruolo del Gestore'
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
    postal_box,
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
FROM tmp_gestore_unique g
JOIN tmp_tipo_indirizzo_res t
  ON TRUE
JOIN tmp_indirizzo_dettaglio_unique idd
  ON TRUE;

SELECT is(
    (
        SELECT count(*)::int
        FROM anagrafiche.indirizzi i
        JOIN tmp_gestore_unique g
          ON g.soggetto_ruolo_id = i.soggetto_ruolo_id
        JOIN tmp_tipo_indirizzo_res t
          ON t.id = i.tipo_indirizzo_id
    ),
    1,
    'Dopo primo insert: esiste esattamente 1 indirizzo RES per il soggetto_ruolo del Gestore'
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
        postal_box,
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
    FROM tmp_gestore_unique g
    JOIN tmp_tipo_indirizzo_res t
      ON TRUE
    JOIN tmp_indirizzo_dettaglio_unique idd
      ON TRUE;
    $$,
    '23505',
    NULL, 
    'Vincolo uq_indirizzi_ruolo_tipo impedisce un secondo indirizzo RES per lo stesso soggetto_ruolo_id'
);

-- Fine test
SELECT * FROM finish();

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia nulla dietro di se'. Le DELETE del cleanup restano
-- perche' dove sono un'asserzione devono girare davvero.
ROLLBACK;
