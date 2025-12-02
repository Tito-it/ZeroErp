-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test:
--   - Guard anagrafiche.trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo
--     su RES/SEDELEG per Gestore
--   - Fallback fn_get_indirizzo per SEDEOP → SEDELEG
-- ------------------------------------------------------------

SELECT plan(8);

-- =========================================================
-- 0) Costanti per indirizzo_dettaglio di test
-- =========================================================
CREATE TEMP TABLE tmp_costanti_indirizzo_guard AS
SELECT
    'VIA TEST GUARD'::text AS via_norm_test,
    '1'::text              AS civico_norm_test,
    NULL::text             AS interno_test,
    NULL::text             AS piano_test,
    NULL::text             AS palazzina_test;

-- =========================================================
-- 1) Recupero Gestore e soggetto_ruolo
-- =========================================================
CREATE TEMP TABLE tmp_first_gestore_guard AS
SELECT MIN(id) AS gestore_id
FROM anagrafiche.gestori;

CREATE TEMP TABLE tmp_gestore_guard AS
SELECT
    g.id                AS gestore_id,
    g.soggetto_ruolo_id AS soggetto_ruolo_id,
    sr.soggetto_id      AS soggetto_id
FROM anagrafiche.gestori g
JOIN tmp_first_gestore_guard fg
  ON g.id = fg.gestore_id
JOIN anagrafiche.soggetti_ruoli sr
  ON sr.id = g.soggetto_ruolo_id;

SELECT ok(
    (SELECT count(*) FROM tmp_gestore_guard) = 1,
    'Esiste almeno un Gestore (tmp_gestore_guard valorizzata)'
);

-- =========================================================
-- 2) Recupero tipi indirizzo RES / SEDELEG / SEDEOP
-- =========================================================
CREATE TEMP TABLE tmp_tipi_indirizzo_guard AS
SELECT
    ti.id,
    ti.codice_interno,
    ti.codice,
    ti.descrizione
FROM config.tipi_indirizzi ti
WHERE ti.codice_interno IN ('RES', 'SEDELEG', 'SEDEOP');

SELECT ok(
    (SELECT count(*) FROM tmp_tipi_indirizzo_guard) >= 2,
    'Esistono almeno RES e SEDELEG in config.tipi_indirizzi (eventualmente anche SEDEOP)'
);

-- comodo avere le 3 righe “esplicite”
CREATE TEMP TABLE tmp_tipo_res_guard AS
SELECT * FROM tmp_tipi_indirizzo_guard WHERE codice_interno = 'RES';

CREATE TEMP TABLE tmp_tipo_sedeleg_guard AS
SELECT * FROM tmp_tipi_indirizzo_guard WHERE codice_interno = 'SEDELEG';

CREATE TEMP TABLE tmp_tipo_sedeop_guard AS
SELECT * FROM tmp_tipi_indirizzo_guard WHERE codice_interno = 'SEDEOP';

-- =========================================================
-- 3) Upsert indirizzo_dettaglio di test
-- =========================================================
CREATE TEMP TABLE tmp_stradario_guard AS
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
    FROM tmp_stradario_guard s,
         tmp_costanti_indirizzo_guard k
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
        'Indirizzo test GUARD (pgTAP)',
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
INTO TEMP TABLE tmp_indirizzo_dettaglio_guard
FROM upsert;

SELECT is(
    (SELECT count(*)::int FROM tmp_indirizzo_dettaglio_guard),
    1,
    'Upsert indirizzo_dettaglio_guard: ottenuto esattamente 1 id (nuovo o esistente)'
);

-- =========================================================
-- 4) Pulizia pre-test: elimino RES / SEDELEG / SEDEOP per il soggetto_ruolo del Gestore
-- =========================================================
DELETE FROM anagrafiche.indirizzi i
USING tmp_gestore_guard g, tmp_tipi_indirizzo_guard t
WHERE i.soggetto_ruolo_id = g.soggetto_ruolo_id
  AND i.tipo_indirizzo_id = t.id;

SELECT is(
    (
        SELECT count(*)::int
        FROM anagrafiche.indirizzi i
        JOIN tmp_gestore_guard g
          ON g.soggetto_ruolo_id = i.soggetto_ruolo_id
        JOIN tmp_tipi_indirizzo_guard t
          ON t.id = i.tipo_indirizzo_id
    ),
    0,
    'Pre-condizione: nessun indirizzo RES/SEDELEG/SEDEOP per il soggetto_ruolo del Gestore'
);

-- =========================================================
-- 5) Inserimento RES per Gestore: deve FALLIRE (guard)
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
    FROM tmp_gestore_guard g
    JOIN tmp_tipo_res_guard t
      ON TRUE
    JOIN tmp_indirizzo_dettaglio_guard idd
      ON TRUE;
    $$,
    NULL,  -- errcode: qualsiasi
    NULL,  -- errmsg: qualsiasi
    'Guard blocca RES per il Gestore (tipo non ammesso in matrice)'
);

-- Nessun indirizzo RES deve essere stato inserito
SELECT is(
    (
        SELECT count(*)::int
        FROM anagrafiche.indirizzi i
        JOIN tmp_gestore_guard g
          ON g.soggetto_ruolo_id = i.soggetto_ruolo_id
        JOIN tmp_tipo_res_guard t
          ON t.id = i.tipo_indirizzo_id
    ),
    0,
    'Dopo tentativo RES fallito: ancora nessun indirizzo RES per il Gestore'
);

-- =========================================================
-- 6) Inserimento SEDELEG per Gestore: deve andare a buon fine
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
FROM tmp_gestore_guard g
JOIN tmp_tipo_sedeleg_guard t
  ON TRUE
JOIN tmp_indirizzo_dettaglio_guard idd
  ON TRUE;

SELECT is(
    (
        SELECT count(*)::int
        FROM anagrafiche.indirizzi i
        JOIN tmp_gestore_guard g
          ON g.soggetto_ruolo_id = i.soggetto_ruolo_id
        JOIN tmp_tipo_sedeleg_guard t
          ON t.id = i.tipo_indirizzo_id
    ),
    1,
    'Inserimento SEDELEG per Gestore riuscito: 1 indirizzo SEDELEG presente'
);

-- =========================================================
-- 7) Test fallback fn_get_indirizzo: richiesta SEDEOP → ritorna SEDELEG
-- =========================================================

-- Se non hai configurato SEDEOP in tipi_indirizzi / matrice, puoi saltare questo step.
-- Qui assumiamo:
--   - in config.tipi_ruolo_tipi_indirizzo per GE:
--       SEDEOP has fallback_tipo_indirizzo_id = SEDELEG

SELECT results_eq(
    $$
    SELECT tipo_indirizzo
    FROM script.fn_get_indirizzo(
        (SELECT soggetto_ruolo_id FROM tmp_gestore_guard),
        'SEDEOP'
    )
    ORDER BY tipo_indirizzo
    $$,
    $$
    VALUES ('SEDELEG'::varchar)
    $$,
    'fn_get_indirizzo: richiesta SEDEOP per Gestore usa fallback SEDELEG'
);

-- Fine test
SELECT * FROM finish();
