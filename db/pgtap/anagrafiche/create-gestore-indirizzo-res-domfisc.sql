-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: ruolo Gestore + abbinamento indirizzi RES e DOMFISC
--       che condividono lo stesso indirizzo_dettaglio
--
-- Scenario:
--   - Legge il primo Gestore da anagrafiche.gestori
--   - Recupera i tipi indirizzo RES e DOMFISC da config.tipi_indirizzi
--   - Upsert di un indirizzo_dettaglio normalizzato di test
--   - Upsert indirizzo RES per il Gestore collegato a quell'indirizzo_dettaglio
--   - Upsert indirizzo DOMFISC per il Gestore usando lo stesso indirizzo_dettaglio
--   - Verifica:
--       * 1 solo indirizzo_dettaglio
--       * 1 indirizzo RES e 1 DOMFISC per il Gestore
--       * entrambi puntano allo stesso indirizzo_dettaglio_id

--  Aggiunta del 2024-06-11  utilizzo di fn_search_indirizzi_dettaglio
--  per verificare che l'indirizzo_dettaglio creato sia effettivamente
--  reperibile tramite la funzione di ricerca indirizzi_dettaglio 3-bis)

-- ------------------------------------------------------------

SELECT plan(10);

-- =========================================================
-- Costanti per il test (stesso pattern del test RES)
-- =========================================================
CREATE TEMP TABLE tmp_costanti_indirizzo_gestore AS
SELECT
    'VIA TEST RES/DOMFISC GESTORE'::text AS via_norm_test,
    '1'::text                            AS civico_norm_test,
    NULL::text                           AS interno_test,
    NULL::text                           AS piano_test,
    NULL::text                           AS palazzina_test;

-- =========================================================
-- 0) Recupero Gestore
-- =========================================================
CREATE TEMP TABLE tmp_first_gestore AS
SELECT MIN(id) AS gestore_id
FROM anagrafiche.gestori;

CREATE TEMP TABLE tmp_gestore AS
SELECT
    g.id                AS gestore_id,
    g.soggetto_ruolo_id AS soggetto_ruolo_id,
    sr.soggetto_id      AS soggetto_id,
    s.stato_id          AS soggetto_stato_id,
    s.comune_id         AS soggetto_comune_id
FROM anagrafiche.gestori g
JOIN tmp_first_gestore fg
  ON g.id = fg.gestore_id
JOIN anagrafiche.soggetti_ruoli sr
  ON sr.id = g.soggetto_ruolo_id
JOIN anagrafiche.soggetti s
  ON s.id = sr.soggetto_id;

SELECT ok(
    (SELECT count(*) FROM tmp_gestore) = 1,
    'Esiste almeno un Gestore (tmp_gestore valorizzata)'
);

-- =========================================================
-- 1) Recupero tipi indirizzo RES e DOMFISC
-- =========================================================
CREATE TEMP TABLE tmp_tipi_indirizzo AS
SELECT
    ti.id,
    ti.codice_interno,
    ti.codice,
    ti.descrizione
FROM config.tipi_indirizzi ti
WHERE ti.codice_interno IN ('RES', 'DOMFISC');

SELECT ok(
    (SELECT count(*) FROM tmp_tipi_indirizzo WHERE codice_interno = 'RES') = 1
    AND
    (SELECT count(*) FROM tmp_tipi_indirizzo WHERE codice_interno = 'DOMFISC') = 1,
    'Esistono i tipi indirizzo RES e DOMFISC in config.tipi_indirizzi'
);

-- =========================================================
-- 2) Recupero uno stradario per indirizzi_dettaglio
-- =========================================================
CREATE TEMP TABLE tmp_stradario AS
SELECT
    s.id
FROM config.stradario s
ORDER BY s.id
LIMIT 1;

SELECT ok(
    (SELECT count(*) FROM tmp_stradario) = 1,
    'Esiste almeno un record in config.stradario per indirizzi_dettaglio'
);

-- =========================================================
-- 3) Upsert indirizzo_dettaglio di test
-- =========================================================
WITH dati AS (
    SELECT
        s.id                    AS stradario_id,
        1                       AS civico,
        NULL::text              AS estensione_civico,
        k.palazzina_test        AS palazzina,
        k.interno_test          AS interno,
        k.piano_test            AS piano,
        k.via_norm_test         AS via_norm,
        k.civico_norm_test      AS civico_norm
    FROM tmp_stradario s,
         tmp_costanti_indirizzo_gestore k
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
        'Indirizzo test RES/DOMFISC Gestore (pgTAP)',
        d.via_norm,
        d.civico_norm,
        TRUE,
        FALSE
    FROM dati d
    ON CONFLICT (
    stradario_id , civico , 
    COALESCE(estensione_civico, ''::character varying) ,
     COALESCE(palazzina, ''::character varying) , 
     COALESCE(scala, ''::character varying) ,
      COALESCE(piano, ''::character varying) , 
      COALESCE(interno, ''::character varying) 
        )
    DO UPDATE
       SET data_update = now(),
           user_update = CURRENT_USER
    RETURNING id
)
SELECT id
INTO TEMP TABLE tmp_indirizzo_dettaglio_gestore
FROM upsert;

SELECT is(
    (SELECT count(*)::int FROM tmp_indirizzo_dettaglio_gestore),
    1,
    'Upsert di indirizzo_dettaglio: ottenuto esattamente 1 id (nuovo o esistente)'
);


-- inserimento del 2024-06-11  --

-- =========================================================
-- 3-bis) Verifica tramite fn_search_indirizzi_dettaglio
--       che l'indirizzo sia reperibile in modo coerente
-- =========================================================

-- Richiamo funzione di ricerca con:
--   - p_stradario_id      = quello scelto nel test
--   - p_civico            = 1
--   - p_palazzina/piano/interno = quelli definiti nelle costanti (tutti NULL nel test attuale)
--   - p_indirizzo_norm    = pattern sulla via normalizzata
--   - p_limit             = 10 (abbondante per il test)

CREATE TEMP TABLE tmp_search_indirizzo_gestore AS
SELECT *
FROM anagrafiche.fn_search_indirizzi_dettaglio(
    p_stradario_id      => (SELECT id FROM tmp_stradario),
    p_civico            => 1,
    p_estensione_civico => NULL,
    p_palazzina         => (SELECT palazzina_test FROM tmp_costanti_indirizzo_gestore),
    p_scala             => NULL,
    p_piano             => (SELECT piano_test FROM tmp_costanti_indirizzo_gestore),
    p_interno           => (SELECT interno_test FROM tmp_costanti_indirizzo_gestore),
    p_indirizzo_norm    => (SELECT via_norm_test FROM tmp_costanti_indirizzo_gestore),
    p_limit             => 10
);

-- Test 4 (nuovo): la funzione trova esattamente 1 indirizzo
SELECT is(
    (SELECT count(*)::int FROM tmp_search_indirizzo_gestore),
    1,
    'fn_search_indirizzi_dettaglio trova esattamente 1 indirizzo per il pattern e i parametri forniti'
);

-- Test 5 (nuovo): l'id trovato dalla funzione coincide con quello dell'upsert
SELECT is(
    (SELECT indirizzo_dettaglio_id FROM tmp_search_indirizzo_gestore),
    (SELECT id FROM tmp_indirizzo_dettaglio_gestore),
    'fn_search_indirizzi_dettaglio restituisce lo stesso indirizzo_dettaglio_id creato/aggiornato dall''upsert'
);


--  Fine agggiornamento 2024-06-11  --

-- =========================================================
-- 4) Upsert indirizzo RES per il Gestore
-- =========================================================
WITH dati_res AS (
    SELECT
        g.soggetto_ruolo_id,
        t.id              AS tipo_indirizzo_id,
        idd.id            AS indirizzo_dettaglio_id,
        g.soggetto_stato_id,
        g.soggetto_comune_id
    FROM tmp_gestore g
    JOIN tmp_tipi_indirizzo t
      ON t.codice_interno = 'RES'
    JOIN tmp_indirizzo_dettaglio_gestore idd
      ON TRUE
),
upsert_res AS (
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
        d.soggetto_ruolo_id,
        d.tipo_indirizzo_id,
        d.indirizzo_dettaglio_id,
        NULL,
        d.soggetto_stato_id,
        NULL,
        NULL,
        NULL,
        NULL,
        NULL,
        d.soggetto_comune_id,
        NULL,
        FALSE
    FROM dati_res d
    ON CONFLICT ON CONSTRAINT uq_indirizzi_ruolo_tipo
    DO UPDATE
       SET indirizzo_dettaglio_id = EXCLUDED.indirizzo_dettaglio_id
    RETURNING id
)
SELECT id
INTO TEMP TABLE tmp_indirizzo_res_gestore
FROM upsert_res;

SELECT is(
    (SELECT count(*)::int FROM tmp_indirizzo_res_gestore),
    1,
    'Upsert indirizzo RES per il ruolo Gestore (1 record interessato)'
);

-- =========================================================
-- 5) Upsert indirizzo DOMFISC per il Gestore (stesso indirizzo_dettaglio)
-- =========================================================
WITH dati_domfisc AS (
    SELECT
        g.soggetto_ruolo_id,
        t.id              AS tipo_indirizzo_id,
        idd.id            AS indirizzo_dettaglio_id,
        g.soggetto_stato_id,
        g.soggetto_comune_id
    FROM tmp_gestore g
    JOIN tmp_tipi_indirizzo t
      ON t.codice_interno = 'DOMFISC'
    JOIN tmp_indirizzo_dettaglio_gestore idd
      ON TRUE
),
upsert_domfisc AS (
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
        d.soggetto_ruolo_id,
        d.tipo_indirizzo_id,
        d.indirizzo_dettaglio_id,
        NULL,
        d.soggetto_stato_id,
        NULL,
        NULL,
        NULL,
        NULL,
        NULL,
        d.soggetto_comune_id,
        NULL,
        FALSE
    FROM dati_domfisc d
    ON CONFLICT ON CONSTRAINT uq_indirizzi_ruolo_tipo
    DO UPDATE
       SET indirizzo_dettaglio_id = EXCLUDED.indirizzo_dettaglio_id
    RETURNING id
)
SELECT id
INTO TEMP TABLE tmp_indirizzo_domfisc_gestore
FROM upsert_domfisc;

SELECT is(
    (SELECT count(*)::int FROM tmp_indirizzo_domfisc_gestore),
    1,
    'Upsert indirizzo DOMFISC per il ruolo Gestore (1 record interessato)'
);

-- =========================================================
-- 6) Verifica: 1 RES e 1 DOMFISC per il Gestore
-- =========================================================
SELECT is(
    (
        SELECT count(*)::int
        FROM anagrafiche.indirizzi i
        JOIN tmp_gestore g
          ON g.soggetto_ruolo_id = i.soggetto_ruolo_id
        JOIN tmp_tipi_indirizzo t
          ON t.id = i.tipo_indirizzo_id
        WHERE t.codice_interno IN ('RES', 'DOMFISC')
    ),
    2,
    'Esistono esattamente 2 indirizzi per il Gestore: 1 RES e 1 DOMFISC'
);

-- =========================================================
-- 7) Verifica: RES e DOMFISC condividono lo stesso indirizzo_dettaglio_id
-- =========================================================
SELECT ok(
    EXISTS (
        SELECT 1
        FROM anagrafiche.indirizzi i_res
        JOIN anagrafiche.indirizzi i_dom
          ON i_dom.soggetto_ruolo_id     = i_res.soggetto_ruolo_id
         AND i_dom.indirizzo_dettaglio_id = i_res.indirizzo_dettaglio_id
        JOIN tmp_tipi_indirizzo t_res
          ON t_res.id = i_res.tipo_indirizzo_id
         AND t_res.codice_interno = 'RES'
        JOIN tmp_tipi_indirizzo t_dom
          ON t_dom.id = i_dom.tipo_indirizzo_id
         AND t_dom.codice_interno = 'DOMFISC'
        JOIN tmp_gestore g
          ON g.soggetto_ruolo_id = i_res.soggetto_ruolo_id
        JOIN tmp_indirizzo_dettaglio_gestore idd
          ON idd.id = i_res.indirizzo_dettaglio_id
    ),
    'Indirizzi RES e DOMFISC del Gestore condividono lo stesso indirizzo_dettaglio_id'
);

-- Fine test
SELECT * FROM finish();
