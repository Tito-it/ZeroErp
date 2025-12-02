-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test soggetto: codice_fiscale = 'TTNMHL68E07D042Z'
--
-- Scenario:
--   - Recupero soggetto per codice_fiscale
--   - Recupero primo ruolo (anagrafiche.soggetti_ruoli) per quel soggetto
--   - Pulizia SOLO dei contatti legati a quel ruolo
--   - Inserimento contatto di ruolo is_default = TRUE
--   - Verifica:
--       * default_context = 'ruolo'
--       * fn_get_contatti(soggetto, ruolo, tipo) → contatto di ruolo
--       * fn_get_contatto_default(soggetto, ruolo, tipo) → contatto di ruolo
--       * fn_get_contatto_default(soggetto) → contatto default di soggetto
-- ------------------------------------------------------------

SELECT plan(9);

-- =========================================================
-- 0) Precondizione: esiste almeno un tipo_contatto
-- =========================================================
CREATE TEMP TABLE tmp_tipo_contatto_test AS
SELECT id AS tipo_contatto_id
FROM config.tipi_contatti
ORDER BY id
LIMIT 1;

SELECT ok(
    (SELECT count(*) FROM tmp_tipo_contatto_test) >= 1,
    'Esiste almeno un tipo_contatto in config.tipi_contatti'
);

-- =========================================================
-- 1) Recupero soggetto per codice_fiscale = 'TTNMHL68E07D042Z'
-- =========================================================
CREATE TEMP TABLE tmp_soggetto_test AS
SELECT id
FROM anagrafiche.soggetti
WHERE codice_fiscale = 'TTNMHL68E07D042Z';

SELECT is(
    (SELECT count(*)::int FROM tmp_soggetto_test),
    1,
    'Trovato esattamente 1 soggetto con codice_fiscale = ''TTNMHL68E07D042Z'''
);

-- =========================================================
-- 2) Recupero primo ruolo per il soggetto (es. CL)
-- =========================================================
CREATE TEMP TABLE tmp_soggetto_ruolo_test AS
SELECT
    id          AS soggetto_ruolo_id,
    soggetto_id AS soggetto_id
FROM anagrafiche.soggetti_ruoli
WHERE soggetto_id = (SELECT id FROM tmp_soggetto_test)
ORDER BY id
LIMIT 1;

SELECT ok(
    (SELECT count(*) FROM tmp_soggetto_ruolo_test) = 1,
    'Trovato almeno un ruolo per il soggetto (uso il primo in soggetti_ruoli)'
);

-- =========================================================
-- 3) Pulizia pre-test:
--    elimino SOLO i contatti per questo soggetto_ruolo
--    (non tocco i contatti generici del soggetto)
-- =========================================================
DELETE FROM anagrafiche.contatti c
USING tmp_soggetto_ruolo_test sr
WHERE c.soggetto_id       = sr.soggetto_id
  AND c.soggetto_ruolo_id = sr.soggetto_ruolo_id;

SELECT is(
    (
        SELECT count(*)::int
        FROM anagrafiche.contatti c
        JOIN tmp_soggetto_ruolo_test sr
          ON c.soggetto_id       = sr.soggetto_id
         AND c.soggetto_ruolo_id = sr.soggetto_ruolo_id
    ),
    0,
    'Pre-condizione: nessun contatto associato al soggetto_ruolo di test'
);

-- =========================================================
-- 4) Inserimento contatto di RUOLO (is_default = TRUE)
-- =========================================================
WITH ins AS (
    INSERT INTO anagrafiche.contatti (
        tipo_contatto_id,
        soggetto_id,
        soggetto_ruolo_id,
        nominativo,
        email,
        telefono,
        cellulare,
        pec,
        note,
        is_default
    )
    SELECT
        tc.tipo_contatto_id,
        sr.soggetto_id,
        sr.soggetto_ruolo_id,
        'Contatto RUOLO PGTAP',
        'ruolo.titnmhl@example.com',
        NULL,
        NULL,
        NULL,
        'PGTAP – contatto default di ruolo per soggetto TTNMHL68E07D042Z',
        TRUE
    FROM tmp_soggetto_ruolo_test sr,
         tmp_tipo_contatto_test tc
    RETURNING id
)
SELECT id
INTO TEMP TABLE tmp_contatto_ruolo_default
FROM ins;

SELECT is(
    (
        SELECT default_context
        FROM anagrafiche.contatti
        WHERE id = (SELECT id FROM tmp_contatto_ruolo_default)
    ),
    'ruolo',
    'Contatto di ruolo: default_context = ''ruolo'''
);

-- =========================================================
-- 5) Verifica che il default_contatto_id del soggetto
--    sia valorizzato e NON coincida con il contatto di ruolo
-- =========================================================
SELECT ok(
    (
        SELECT default_contatto_id IS NOT NULL
           AND default_contatto_id::bigint <> (SELECT id::bigint FROM tmp_contatto_ruolo_default)
        FROM anagrafiche.soggetti
        WHERE id = (SELECT id FROM tmp_soggetto_test)
    ),
    'Il soggetto ha un default_contatto_id valorizzato e diverso dal contatto di ruolo'
);

-- =========================================================
-- 6) fn_get_contatti:
--    (a) soggetto + soggetto_ruolo + tipo_contatto → contatto di ruolo
-- =========================================================
SELECT results_eq(
    $$
    SELECT id::bigint
    FROM script.fn_get_contatti(
        (SELECT soggetto_id       FROM tmp_soggetto_ruolo_test),
        (SELECT soggetto_ruolo_id FROM tmp_soggetto_ruolo_test),
        NULL,
        (SELECT tipo_contatto_id  FROM tmp_tipo_contatto_test)
    )
    $$,
    $$
    SELECT id::bigint
    FROM tmp_contatto_ruolo_default
    $$,
    'fn_get_contatti(soggetto, ruolo, NULL, tipo): ritorna il contatto di ruolo'
);

-- =========================================================
-- 7) fn_get_contatto_default:
--    (b) soggetto + soggetto_ruolo + tipo_contatto → contatto di ruolo
-- =========================================================
SELECT results_eq(
    $$
    SELECT id::bigint
    FROM script.fn_get_contatto_default(
        (SELECT soggetto_id       FROM tmp_soggetto_ruolo_test),
        (SELECT soggetto_ruolo_id FROM tmp_soggetto_ruolo_test),
        NULL,
        (SELECT tipo_contatto_id  FROM tmp_tipo_contatto_test)
    )
    $$,
    $$
    SELECT id::bigint
    FROM tmp_contatto_ruolo_default
    $$,
    'fn_get_contatto_default(soggetto, ruolo, NULL, tipo): ritorna il contatto default di ruolo'
);

-- =========================================================
-- 8) fn_get_contatto_default:
--    (c) SOLO soggetto → contatto default di soggetto (default_contatto_id)
-- =========================================================
SELECT results_eq(
    $$
    SELECT id::bigint
    FROM script.fn_get_contatto_default(
        (SELECT id FROM tmp_soggetto_test),
        NULL,
        NULL,
        NULL
    )
    $$,
    $$
    SELECT default_contatto_id::bigint
    FROM anagrafiche.soggetti
    WHERE id = (SELECT id FROM tmp_soggetto_test)
    $$,
    'fn_get_contatto_default(soggetto, NULL, NULL, NULL): ritorna il contatto default di soggetto'
);

-- Fine test
SELECT * FROM finish();
