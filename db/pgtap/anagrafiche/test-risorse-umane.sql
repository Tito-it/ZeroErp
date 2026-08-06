-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test risorse_umane:
--   - inserimento con ruolo RIS_UMANA
--   - vincolo date valido_al >= valido_dal
--   - coerenza soggetto_id con soggetto_ruolo_id
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

SELECT plan(8);

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
-- 1) Precondizione: esiste la qualifica DIPENDENTE
-- =========================================================
CREATE TEMP TABLE tmp_qualifica_test AS
SELECT id AS qualifica_id
FROM config.qualifiche
WHERE codice_interno = 'DIPENDENTE'
LIMIT 1;

SELECT ok(
    (SELECT count(*) FROM tmp_qualifica_test) = 1,
    'Esiste la qualifica DIPENDENTE in config.qualifiche'
);

-- =========================================================
-- 2) Recupero soggetto test (codice fiscale noto)
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
-- 3) Ruolo RIS_UMANA per il soggetto
-- =========================================================
CREATE TEMP TABLE tmp_soggetto_ruolo_test AS
SELECT script.fn_get_or_create_soggetto_ruolo(
    p_soggetto_id  := (SELECT id FROM tmp_soggetto_test),
    p_cd_int_ruolo := 'RIS_UMANA'
) AS soggetto_ruolo_id;

SELECT ok(
    (SELECT count(*) FROM tmp_soggetto_ruolo_test) = 1,
    'Creato/recuperato ruolo RIS_UMANA per il soggetto test'
);

-- =========================================================
-- 4) Inserimento risorsa umana coerente
-- =========================================================
WITH ins AS (
    INSERT INTO anagrafiche.risorse_umane (
        soggetto_ruolo_id,
        soggetto_id,
        qualifica_id,
        valido_dal
    )
    SELECT
        sr.soggetto_ruolo_id,
        s.id,
        q.qualifica_id,
        CURRENT_DATE
    FROM tmp_soggetto_ruolo_test sr,
         tmp_soggetto_test s,
         tmp_qualifica_test q
    RETURNING id
)
SELECT id
INTO TEMP TABLE tmp_risorsa_umana_test
FROM ins;

SELECT ok(
    (SELECT count(*) FROM tmp_risorsa_umana_test) = 1,
    'Inserita risorsa umana per il soggetto test'
);

-- =========================================================
-- 5) Vincolo date: valido_al >= valido_dal
-- =========================================================
SELECT throws_ok(
    $$
    UPDATE anagrafiche.risorse_umane
       SET valido_al = valido_dal - INTERVAL '1 day'
     WHERE id = (SELECT id FROM tmp_risorsa_umana_test);
    $$,
    '23514',
    NULL,
    'Vincolo date: valido_al non puo'' essere precedente a valido_dal'
);

-- =========================================================
-- 6) Recupero soggetto alternativo per test mismatch
-- =========================================================
CREATE TEMP TABLE tmp_soggetto_alt AS
SELECT id
FROM anagrafiche.soggetti
WHERE partita_iva = '29878230910';

SELECT ok(
    (SELECT count(*) FROM tmp_soggetto_alt) = 1,
    'Trovato soggetto alternativo con partita_iva = 29878230910'
);

-- =========================================================
-- 7) Guard: soggetto_id deve combaciare con soggetto_ruolo_id
-- =========================================================
SELECT throws_ok(
    $$
    UPDATE anagrafiche.risorse_umane
       SET soggetto_id = (SELECT id FROM tmp_soggetto_alt)
     WHERE id = (SELECT id FROM tmp_risorsa_umana_test);
    $$,
    'P0001',
    NULL,
    'Guard: soggetto_id deve essere coerente con soggetto_ruolo_id'
);

SELECT * FROM finish();

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia nulla dietro di se'. Le DELETE del cleanup restano
-- perche' dove sono un'asserzione devono girare davvero.
ROLLBACK;
