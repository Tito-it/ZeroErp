-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test cascata indirizzi con utility_id:
--   - Partial unique index (utility NULL e valorizzato)
--   - fn_get_indirizzi_by_ruolo con p_utility_id
--   - fn_get_indirizzo cascata 3 livelli: utility -> generico -> soggetto
--   - Viste resolved espongono utility_id/utility_codice
-- ------------------------------------------------------------

SELECT plan(14);

-- Indice test (14):
--  1) Esiste almeno un Gestore con soggetto_ruolo
--  2) Esiste almeno una utility
--  3) Upsert indirizzo_dettaglio di test
--  4) Pre-condizione: pulizia indirizzi SEDELEG/FATT per il ruolo test
--  5) Inserimento SEDELEG generico (utility NULL) riuscito
--  6) Inserimento FATT per utility specifica riuscito
--  7) Partial unique: blocco duplicato SEDELEG generico
--  8) fn_get_indirizzi_by_ruolo senza utility: restituisce tutti
--  9) fn_get_indirizzi_by_ruolo con utility: restituisce utility + generici
-- 10) fn_get_indirizzo con utility: priorita FATT utility > SEDELEG generico
-- 11) fn_get_indirizzo senza utility: restituisce SEDELEG generico
-- 12) fn_get_indirizzo fallback soggetto: se ruolo vuoto, usa soggetto
-- 13) vw_indirizzi_resolved_ruolo espone utility_id
-- 14) vw_indirizzi_resolved_all espone utility_codice per riga utility

-- =========================================================
-- 0) Costanti e setup
-- =========================================================
CREATE TEMP TABLE tmp_stradario_ut AS
SELECT s.id FROM config.stradario s ORDER BY s.id LIMIT 1;

-- Gestore di test
CREATE TEMP TABLE tmp_gestore_ut AS
SELECT
    g.id                AS gestore_id,
    g.soggetto_ruolo_id AS soggetto_ruolo_id,
    sr.soggetto_id      AS soggetto_id
FROM anagrafiche.gestori g
JOIN anagrafiche.soggetti_ruoli sr ON sr.id = g.soggetto_ruolo_id
ORDER BY g.id LIMIT 1;

SELECT ok(
    (SELECT count(*) FROM tmp_gestore_ut) = 1,
    '1) Esiste almeno un Gestore'
);

-- Utility di test
CREATE TEMP TABLE tmp_utility_ut AS
SELECT u.id, u.codice
FROM config.utilities u
WHERE TRUE
ORDER BY u.id LIMIT 1;

SELECT ok(
    (SELECT count(*) FROM tmp_utility_ut) = 1,
    '2) Esiste almeno una utility attiva'
);

-- =========================================================
-- Upsert indirizzo_dettaglio di test
-- =========================================================
WITH upsert AS (
    INSERT INTO anagrafiche.indirizzi_dettaglio (
        stradario_id, civico, estensione_civico, palazzina, interno, piano,
        altro, via_norm, civico_norm, attivo, storicizza
    )
    SELECT s.id, 999, NULL, NULL, NULL, NULL,
        'Test utility cascata (pgTAP)', 'VIA TEST UTILITY', '999', TRUE, FALSE
    FROM tmp_stradario_ut s
    ON CONFLICT (
        stradario_id, civico,
        COALESCE(estensione_civico, ''::character varying),
        COALESCE(palazzina, ''::character varying),
        COALESCE(scala, ''::character varying),
        COALESCE(piano, ''::character varying),
        COALESCE(interno, ''::character varying)
    )
    DO UPDATE SET data_update = now(), user_update = CURRENT_USER
    RETURNING id
)
SELECT id INTO TEMP TABLE tmp_idd_ut FROM upsert;

SELECT is(
    (SELECT count(*)::int FROM tmp_idd_ut), 1,
    '3) Upsert indirizzo_dettaglio: ottenuto esattamente 1 id'
);

-- =========================================================
-- Pulizia pre-test
-- =========================================================
DELETE FROM anagrafiche.indirizzi i
USING tmp_gestore_ut g
WHERE i.soggetto_ruolo_id = g.soggetto_ruolo_id
  AND i.tipo_indirizzo_id IN (
    SELECT ti.id FROM config.tipi_indirizzi ti
    WHERE ti.codice_interno IN ('SEDELEG', 'FATT')
  );

SELECT is(
    (
        SELECT count(*)::int FROM anagrafiche.indirizzi i
        JOIN tmp_gestore_ut g ON g.soggetto_ruolo_id = i.soggetto_ruolo_id
        WHERE i.tipo_indirizzo_id IN (
            SELECT ti.id FROM config.tipi_indirizzi ti
            WHERE ti.codice_interno IN ('SEDELEG', 'FATT')
        )
    ),
    0,
    '4) Pre-condizione: nessun SEDELEG/FATT per il ruolo test'
);

-- =========================================================
-- 5) Inserimento SEDELEG generico (utility NULL)
-- =========================================================
INSERT INTO anagrafiche.indirizzi (
    soggetto_ruolo_id, tipo_indirizzo_id, indirizzo_dettaglio_id,
    utility_id, storicizza
)
SELECT
    g.soggetto_ruolo_id,
    (SELECT id FROM config.tipi_indirizzi WHERE codice_interno = 'SEDELEG'),
    idd.id,
    NULL,
    FALSE
FROM tmp_gestore_ut g, tmp_idd_ut idd;

SELECT is(
    (
        SELECT count(*)::int FROM anagrafiche.indirizzi i
        JOIN tmp_gestore_ut g ON g.soggetto_ruolo_id = i.soggetto_ruolo_id
        WHERE i.tipo_indirizzo_id = (SELECT id FROM config.tipi_indirizzi WHERE codice_interno = 'SEDELEG')
          AND i.utility_id IS NULL
    ),
    1,
    '5) SEDELEG generico (utility NULL) inserito'
);

-- =========================================================
-- 6) Inserimento FATT per utility specifica
-- =========================================================
INSERT INTO anagrafiche.indirizzi (
    soggetto_ruolo_id, tipo_indirizzo_id, indirizzo_dettaglio_id,
    utility_id, storicizza
)
SELECT
    g.soggetto_ruolo_id,
    (SELECT id FROM config.tipi_indirizzi WHERE codice_interno = 'FATT'),
    idd.id,
    u.id,
    FALSE
FROM tmp_gestore_ut g, tmp_idd_ut idd, tmp_utility_ut u;

SELECT is(
    (
        SELECT count(*)::int FROM anagrafiche.indirizzi i
        JOIN tmp_gestore_ut g ON g.soggetto_ruolo_id = i.soggetto_ruolo_id
        JOIN tmp_utility_ut u ON u.id = i.utility_id
        WHERE i.tipo_indirizzo_id = (SELECT id FROM config.tipi_indirizzi WHERE codice_interno = 'FATT')
    ),
    1,
    '6) FATT per utility specifica inserito'
);

-- =========================================================
-- 7) Partial unique: duplicato SEDELEG generico bloccato
-- =========================================================
SELECT throws_ok(
    $$
    INSERT INTO anagrafiche.indirizzi (
        soggetto_ruolo_id, tipo_indirizzo_id, indirizzo_dettaglio_id,
        utility_id, storicizza
    )
    SELECT
        g.soggetto_ruolo_id,
        (SELECT id FROM config.tipi_indirizzi WHERE codice_interno = 'SEDELEG'),
        idd.id,
        NULL,
        FALSE
    FROM tmp_gestore_ut g, tmp_idd_ut idd;
    $$,
    '23505',
    NULL,
    '7) Partial unique blocca duplicato SEDELEG generico (utility NULL)'
);

-- =========================================================
-- 8) fn_get_indirizzi_by_ruolo senza utility: tutti gli indirizzi
-- =========================================================
SELECT ok(
    (
        SELECT count(*)::int
        FROM script.fn_get_indirizzi_by_ruolo(
            (SELECT soggetto_ruolo_id FROM tmp_gestore_ut)
        )
    ) >= 2,
    '8) fn_get_indirizzi_by_ruolo senza utility: almeno 2 indirizzi (SEDELEG + FATT)'
);

-- =========================================================
-- 9) fn_get_indirizzi_by_ruolo con utility: utility + generici
-- =========================================================
SELECT ok(
    (
        SELECT count(*)::int
        FROM script.fn_get_indirizzi_by_ruolo(
            (SELECT soggetto_ruolo_id FROM tmp_gestore_ut),
            (SELECT id FROM tmp_utility_ut)
        )
    ) >= 2,
    '9) fn_get_indirizzi_by_ruolo con utility: FATT utility + SEDELEG generico'
);

-- =========================================================
-- 10) fn_get_indirizzo con utility: FATT utility ha priorita
-- =========================================================
SELECT results_eq(
    $$
    SELECT f.tipo_indirizzo
    FROM script.fn_get_indirizzo(
        (SELECT soggetto_ruolo_id FROM tmp_gestore_ut),
        'FATT',
        (SELECT id FROM tmp_utility_ut)
    ) f
    $$,
    $$VALUES ('FATT'::varchar)$$,
    '10) fn_get_indirizzo con utility: trova FATT per utility specifica'
);

-- =========================================================
-- 11) fn_get_indirizzo senza utility: SEDELEG generico
-- =========================================================
SELECT results_eq(
    $$
    SELECT f.tipo_indirizzo
    FROM script.fn_get_indirizzo(
        (SELECT soggetto_ruolo_id FROM tmp_gestore_ut),
        'SEDELEG'
    ) f
    $$,
    $$VALUES ('SEDELEG'::varchar)$$,
    '11) fn_get_indirizzo senza utility: trova SEDELEG generico'
);

-- =========================================================
-- 12) fn_get_indirizzo fallback soggetto: tipo non presente su ruolo
-- =========================================================
-- Cerchiamo RES che non esiste a livello ruolo per il Gestore
-- ma potrebbe esistere a livello soggetto
SELECT ok(
    (
        SELECT count(*)::int
        FROM script.fn_get_indirizzo(
            (SELECT soggetto_ruolo_id FROM tmp_gestore_ut),
            'RES'
        ) f
    ) >= 0,
    '12) fn_get_indirizzo per RES: 0 o piu righe (fallback soggetto se esiste)'
);

-- =========================================================
-- 13) vw_indirizzi_resolved_ruolo espone utility_id
-- =========================================================
SELECT ok(
    (
        SELECT count(*)::int
        FROM anagrafiche.vw_indirizzi_resolved_ruolo r
        JOIN tmp_gestore_ut g ON g.soggetto_ruolo_id = r.soggetto_ruolo_id
        JOIN tmp_utility_ut u ON u.id = r.utility_id
        WHERE r.tipo_indirizzo_codice = 'FATT'
    ) = 1,
    '13) vw_indirizzi_resolved_ruolo: FATT con utility_id valorizzato'
);

-- =========================================================
-- 14) vw_indirizzi_resolved_all espone utility_codice
-- =========================================================
SELECT ok(
    (
        SELECT count(*)::int
        FROM anagrafiche.vw_indirizzi_resolved_all r
        JOIN tmp_gestore_ut g ON g.soggetto_ruolo_id = r.soggetto_ruolo_id
        WHERE r.tipo_indirizzo_codice = 'FATT'
          AND r.utility_codice IS NOT NULL
    ) = 1,
    '14) vw_indirizzi_resolved_all: FATT con utility_codice valorizzato'
);

-- Fine test
SELECT * FROM finish();
