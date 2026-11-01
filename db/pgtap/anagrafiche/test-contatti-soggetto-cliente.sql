-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test soggetto: un cliente COSTRUITO da dbops.fn_pgtap_crea_cliente.
--
-- Scenario:
--   - Costruzione del cliente (soggetto + ruolo CL)
--   - Ruolo CL del cliente come ruolo dei contatti
--   - Pulizia SOLO dei contatti legati a quel ruolo
--   - Inserimento contatto di ruolo is_default = TRUE
--   - Verifica:
--       * default_context = 'ruolo'
--       * fn_get_contatti(soggetto, ruolo, tipo) → contatto di ruolo
--       * fn_get_contatto_default(soggetto, ruolo, tipo) → contatto di ruolo
--       * fn_get_contatto_default(soggetto) → contatto default di soggetto
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

SELECT plan(12);

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
-- 1) Precondizione: esiste almeno una unita_organizzativa
-- =========================================================
CREATE TEMP TABLE tmp_unita_organizzativa_test AS
SELECT id AS unita_organizzativa_id
FROM config.unita_organizzative
ORDER BY id
LIMIT 1;

SELECT ok(
    (SELECT count(*) FROM tmp_unita_organizzativa_test) >= 1,
    'Esiste almeno una unita_organizzativa in config.unita_organizzative'
);

-- =========================================================
-- 2) Il soggetto del test: un cliente COSTRUITO
-- =========================================================
-- ⛔ 2026-11-01: il file cercava il soggetto per il codice fiscale di una
--   persona vera del database di sviluppo. Su un database ricostruito dai
--   changelog non c'era (rosso in CI), e un dato personale non sta in un
--   repository pubblico. Stessa cura di test-risorse-umane (2026-09-23).
-- ⚠️ BASE e non GAS: le utility con richiede_pdp pretendono un punto di
--   prelievo, estraneo a cio' che questo file verifica.
CREATE TEMP TABLE tmp_cliente_test AS
SELECT *
FROM dbops.fn_pgtap_crea_cliente(
         'contatti di ruolo',
         (SELECT u.id FROM config.utilities u WHERE u.codice_interno = 'BASE'));

CREATE TEMP TABLE tmp_soggetto_test AS
SELECT soggetto_id AS id
FROM tmp_cliente_test;

SELECT is(
    (SELECT count(*)::int FROM tmp_soggetto_test WHERE id IS NOT NULL),
    1,
    'Costruito il soggetto cliente del test'
);

-- =========================================================
-- 3) Il ruolo dei contatti: il ruolo CL del cliente
-- =========================================================
CREATE TEMP TABLE tmp_soggetto_ruolo_test AS
SELECT
    soggetto_ruolo_id,
    soggetto_id
FROM tmp_cliente_test;

SELECT ok(
    (SELECT count(*) FROM tmp_soggetto_ruolo_test WHERE soggetto_ruolo_id IS NOT NULL) = 1,
    'Il cliente costruito ha il suo ruolo CL'
);

-- =========================================================
-- 4) Pulizia pre-test:
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
-- 5) Inserimento contatto di RUOLO (is_default = TRUE)
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
        'ruolo.pgtap@example.com',
        NULL,
        NULL,
        NULL,
        'PGTAP – contatto default di ruolo per il cliente del test',
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
-- 6) Inserimento contatto di RUOLO con unita_organizzativa
--    e un secondo tipo_contatto (tipo_contatto_id NOT NULL dal 20260324-01)
-- =========================================================
CREATE TEMP TABLE tmp_tipo_contatto_test_2 AS
SELECT id AS tipo_contatto_id
FROM config.tipi_contatti
WHERE id <> (SELECT tipo_contatto_id FROM tmp_tipo_contatto_test)
ORDER BY id
LIMIT 1;

WITH ins AS (
    INSERT INTO anagrafiche.contatti (
        tipo_contatto_id,
        soggetto_id,
        soggetto_ruolo_id,
        unita_organizzativa_id,
        nominativo,
        email,
        note,
        is_default
    )
    SELECT
        tc2.tipo_contatto_id,
        sr.soggetto_id,
        sr.soggetto_ruolo_id,
        uo.unita_organizzativa_id,
        'Contatto RUOLO UO PGTAP',
        'ruolo.uo.pgtap@example.com',
        'PGTAP – contatto ruolo con unita_organizzativa e secondo tipo_contatto',
        FALSE
    FROM tmp_soggetto_ruolo_test sr,
         tmp_unita_organizzativa_test uo,
         tmp_tipo_contatto_test_2 tc2
    RETURNING id
)
SELECT id
INTO TEMP TABLE tmp_contatto_ruolo_unita
FROM ins;

SELECT ok(
    (SELECT count(*) FROM tmp_contatto_ruolo_unita) = 1,
    'Inserito contatto di ruolo con unita_organizzativa e tipo_contatto NULL'
);

-- =========================================================
-- 7) Verifica che il default_contatto_id del soggetto,
--    se presente, NON coincida con il contatto di ruolo
-- =========================================================
SELECT ok(
    (
        SELECT default_contatto_id IS NULL
           OR default_contatto_id::bigint <> (SELECT id::bigint FROM tmp_contatto_ruolo_default)
        FROM anagrafiche.soggetti
        WHERE id = (SELECT id FROM tmp_soggetto_test)
    ),
    'default_contatto_id (se presente) e'' diverso dal contatto di ruolo'
);

-- =========================================================
-- 8) fn_get_contatti:
--    (a) soggetto + soggetto_ruolo + tipo_contatto → contatto di ruolo
-- =========================================================
SELECT results_eq(
    $$
    SELECT id::bigint
    FROM script.fn_get_contatti(
        (SELECT soggetto_id       FROM tmp_soggetto_ruolo_test),
        (SELECT soggetto_ruolo_id FROM tmp_soggetto_ruolo_test),
        NULL,
        (SELECT tipo_contatto_id  FROM tmp_tipo_contatto_test),
        NULL
    )
    $$,
    $$
    SELECT id::bigint
    FROM tmp_contatto_ruolo_default
    $$,
    'fn_get_contatti(soggetto, ruolo, NULL, tipo): ritorna il contatto di ruolo'
);

-- =========================================================
-- 9) fn_get_contatto_default:
--    (b) soggetto + soggetto_ruolo + tipo_contatto → contatto di ruolo
-- =========================================================
SELECT results_eq(
    $$
    SELECT id::bigint
    FROM script.fn_get_contatto_default(
        (SELECT soggetto_id       FROM tmp_soggetto_ruolo_test),
        (SELECT soggetto_ruolo_id FROM tmp_soggetto_ruolo_test),
        NULL,
        (SELECT tipo_contatto_id  FROM tmp_tipo_contatto_test),
        NULL
    )
    $$,
    $$
    SELECT id::bigint
    FROM tmp_contatto_ruolo_default
    $$,
    'fn_get_contatto_default(soggetto, ruolo, NULL, tipo): ritorna il contatto default di ruolo'
);

-- =========================================================
-- 10) fn_get_contatto_default:
--    (c) SOLO soggetto → contatto default di soggetto (default_contatto_id)
-- =========================================================
SELECT ok(
    (
        SELECT count(*)
        FROM script.fn_get_contatto_default(
            (SELECT id FROM tmp_soggetto_test),
            NULL,
            NULL,
            NULL,
            NULL
        )
    ) <= 1
    AND NOT EXISTS (
        SELECT 1
        FROM script.fn_get_contatto_default(
            (SELECT id FROM tmp_soggetto_test),
            NULL,
            NULL,
            NULL,
            NULL
        ) f
        JOIN anagrafiche.contatti c
          ON c.id = f.id
        WHERE c.soggetto_id <> (SELECT id FROM tmp_soggetto_test)
    ),
    'fn_get_contatto_default(soggetto, NULL, NULL, NULL): al massimo 1 riga e del soggetto'
);

-- =========================================================
-- 11) fn_get_contatti:
--    (d) soggetto + ruolo + unita_organizzativa + tipo_contatto_2
--        → contatto ruolo con unita_organizzativa
-- =========================================================
SELECT ok(
    EXISTS (
        SELECT 1
        FROM script.fn_get_contatti(
            (SELECT soggetto_id            FROM tmp_soggetto_ruolo_test),
            (SELECT soggetto_ruolo_id      FROM tmp_soggetto_ruolo_test),
            NULL,
            (SELECT tipo_contatto_id       FROM tmp_tipo_contatto_test_2),
            (SELECT unita_organizzativa_id FROM tmp_unita_organizzativa_test)
        ) AS f
        JOIN anagrafiche.contatti c
          ON c.id = f.id
        WHERE c.soggetto_ruolo_id = (SELECT soggetto_ruolo_id FROM tmp_soggetto_ruolo_test)
          AND c.unita_organizzativa_id = (SELECT unita_organizzativa_id FROM tmp_unita_organizzativa_test)
    ),
    'fn_get_contatti(soggetto, ruolo, NULL, tipo_2, unita_org): ritorna contatto con unita_organizzativa'
);

-- Fine test
SELECT * FROM finish();

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia nulla dietro di se'. Le DELETE del cleanup restano
-- perche' dove sono un'asserzione devono girare davvero.
ROLLBACK;
