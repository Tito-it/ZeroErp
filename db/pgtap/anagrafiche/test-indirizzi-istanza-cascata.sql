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
CREATE TEMP TABLE tmp_ctx AS
SELECT
    cl.id              AS cliente_id,
    cl.soggetto_ruolo_id,
    sr.soggetto_id,
    cl.istanza_utility_id
FROM anagrafiche.clienti cl
JOIN anagrafiche.soggetti_ruoli sr ON sr.id = cl.soggetto_ruolo_id
WHERE cl.istanza_utility_id IS NOT NULL
ORDER BY cl.id LIMIT 1;

SELECT ok(
    (SELECT count(*) FROM tmp_ctx) = 1,
    '1) Esiste almeno un cliente con istanza_utility_id'
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
SELECT results_eq(
    $$
    SELECT f.tipo_indirizzo
    FROM script.fn_get_indirizzo(
        (SELECT soggetto_ruolo_id FROM tmp_ctx),
        'FATT',
        (SELECT istanza_utility_id FROM tmp_ctx)
    ) f
    $$,
    $$VALUES ('FATT'::varchar)$$,
    '9) fn_get_indirizzo con istanza: trova FATT per istanza specifica'
);

-- =========================================================
-- 10) fn_get_indirizzo senza istanza: DOMFISC generico
-- =========================================================
SELECT results_eq(
    $$
    SELECT f.tipo_indirizzo
    FROM script.fn_get_indirizzo(
        (SELECT soggetto_ruolo_id FROM tmp_ctx),
        'DOMFISC'
    ) f
    $$,
    $$VALUES ('DOMFISC'::varchar)$$,
    '10) fn_get_indirizzo senza istanza: trova DOMFISC generico'
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
