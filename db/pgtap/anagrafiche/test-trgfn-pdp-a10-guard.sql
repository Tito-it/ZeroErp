-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: guard su anagrafiche.pdp
--       blocco update su pdp e indirizzo_dettaglio_id
--
-- Indice test:
-- 0) Precondizioni
-- 1) Indirizzi di test (A/B)
-- 2) PDP di test
-- 3) Aggiornamenti vietati
-- 4) Verifica che i valori non siano cambiati
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
-- 0) Precondizioni
-- =========================================================

-- 0.1: Esiste la utility GAS
CREATE TEMP TABLE tmp_utility_gas AS
SELECT id AS utility_id
FROM config.utilities
WHERE codice_interno = 'GAS';

SELECT is(
    (SELECT count(*)::int FROM tmp_utility_gas),
    1,
    'Esiste esattamente 1 utility con codice_interno = GAS'
);

-- 0.2: Esiste almeno uno stradario
CREATE TEMP TABLE tmp_stradario_any AS
SELECT id AS stradario_id
FROM config.stradario
ORDER BY id
LIMIT 1;

SELECT is(
    (SELECT count(*)::int FROM tmp_stradario_any),
    1,
    'Esiste almeno uno stradario in config.stradario'
);

-- =========================================================
-- 1) Indirizzi di test (A/B)
-- =========================================================
CREATE TEMP TABLE tmp_guard_suffix AS
SELECT upper(substring(md5(random()::text || clock_timestamp()::text), 1, 6)) AS suffix;

WITH addr_params AS (
    SELECT (SELECT stradario_id FROM tmp_stradario_any) AS stradario_id,
           1 AS civico,
           ('T' || (SELECT suffix FROM tmp_guard_suffix) || '1')::varchar(10) AS estensione_civico
    UNION ALL
    SELECT (SELECT stradario_id FROM tmp_stradario_any),
           2,
           ('T' || (SELECT suffix FROM tmp_guard_suffix) || '2')::varchar(10)
),
ins AS (
    INSERT INTO anagrafiche.indirizzi_dettaglio (
        stradario_id,
        civico,
        estensione_civico
    )
    SELECT
        p.stradario_id,
        p.civico,
        p.estensione_civico
    FROM addr_params p
    WHERE NOT EXISTS (
        SELECT 1
        FROM anagrafiche.indirizzi_dettaglio idd
        WHERE idd.stradario_id = p.stradario_id
          AND idd.civico       = p.civico
          AND COALESCE(
                CASE
                  WHEN idd.estensione_civico IS NULL OR idd.estensione_civico = '' THEN ''
                  WHEN LEFT(idd.estensione_civico, 1) = '/' THEN idd.estensione_civico
                  ELSE '/' || idd.estensione_civico
                END,
                ''
              ) = COALESCE(
                CASE
                  WHEN p.estensione_civico IS NULL OR p.estensione_civico = '' THEN ''
                  WHEN LEFT(p.estensione_civico, 1) = '/' THEN p.estensione_civico
                  ELSE '/' || p.estensione_civico
                END,
                ''
              )
    )
    RETURNING id, stradario_id, civico, estensione_civico
),
all_addr AS (
    SELECT i.id, i.stradario_id, i.civico, i.estensione_civico
    FROM ins i
    UNION ALL
    SELECT idd.id, idd.stradario_id, idd.civico, idd.estensione_civico
    FROM anagrafiche.indirizzi_dettaglio idd
    JOIN addr_params p
      ON idd.stradario_id = p.stradario_id
     AND idd.civico       = p.civico
     AND COALESCE(
           CASE
             WHEN idd.estensione_civico IS NULL OR idd.estensione_civico = '' THEN ''
             WHEN LEFT(idd.estensione_civico, 1) = '/' THEN idd.estensione_civico
             ELSE '/' || idd.estensione_civico
           END,
           ''
         ) = COALESCE(
           CASE
             WHEN p.estensione_civico IS NULL OR p.estensione_civico = '' THEN ''
             WHEN LEFT(p.estensione_civico, 1) = '/' THEN p.estensione_civico
             ELSE '/' || p.estensione_civico
           END,
           ''
         )
)
SELECT *
INTO TEMP TABLE tmp_indirizzi_guard
FROM all_addr;

SELECT is(
    (SELECT count(*)::int FROM tmp_indirizzi_guard),
    2,
    'Disponibili 2 indirizzi_dettaglio per il test guard'
);

-- =========================================================
-- 2) PDP di test
--
-- ⚠️ rev 2026-08-18 (bonifica baseline): qui c'era un
--   `DELETE FROM anagrafiche.pdp WHERE pdp = 'TEST-PDP-GUARD-0001'`, cioe' la
--   pulizia del residuo lasciato da una corsa precedente. Non funziona piu':
--   quel PDP nel frattempo e' referenziato da anagrafiche.clienti
--   (fk_clienti_pdp) e il DELETE muore li', portandosi dietro tutto il file.
--   Il rimedio non e' cancellare il residuo, e' non averne bisogno: il codice
--   PDP e' UNICO PER CORSA, quindi non collide con niente e il ROLLBACK non
--   lascia nulla.
-- =========================================================
CREATE TEMP TABLE tmp_codici_pdp AS
-- ⚠️ ::varchar e non text: la colonna anagrafiche.pdp.pdp e' varchar, e
--   pgTAP is() risolve la funzione sui tipi esatti degli argomenti.
SELECT ('TEST-PDP-GUARD-'     || substr(md5(clock_timestamp()::text), 1, 10))::varchar AS pdp_ok,
       ('TEST-PDP-GUARD-ALT-' || substr(md5(clock_timestamp()::text), 1, 10))::varchar AS pdp_alt;

CREATE TEMP TABLE tmp_pdp_guard AS
WITH addr AS (
    SELECT id
    FROM tmp_indirizzi_guard
    ORDER BY id
    LIMIT 1
),
ins AS (
    INSERT INTO anagrafiche.pdp (
        pdp,
        utility_id,
        indirizzo_dettaglio_id,
        cliente_id
    )
    SELECT
        (SELECT pdp_ok FROM tmp_codici_pdp),
        (SELECT utility_id FROM tmp_utility_gas),
        (SELECT id FROM addr),
        NULL::bigint
    RETURNING id, pdp, indirizzo_dettaglio_id
)
SELECT *
FROM ins;

SELECT is(
    (SELECT count(*)::int FROM tmp_pdp_guard),
    1,
    'Inserito 1 PDP di test per la guard'
);

-- =========================================================
-- 3) Aggiornamenti vietati
-- =========================================================
SELECT throws_ok(
    $$
    UPDATE anagrafiche.pdp
       SET pdp = (SELECT pdp_alt FROM tmp_codici_pdp)
     WHERE pdp = (SELECT pdp_ok FROM tmp_codici_pdp);
    $$,
    -- ⚠️ rev 2026-08-18: era `NULL`, cioe' «un errore qualunque va bene» —
    --   compreso il crash del guard che questo test dovrebbe verificare.
    'P0001',
    NULL,
    'Update su pdp deve essere bloccato dalla guard'
);

SELECT throws_ok(
    $$
    UPDATE anagrafiche.pdp
       SET indirizzo_dettaglio_id = (
           SELECT id
           FROM tmp_indirizzi_guard
           ORDER BY id DESC
           LIMIT 1
       )
     WHERE pdp = (SELECT pdp_ok FROM tmp_codici_pdp);
    $$,
    'P0001',
    NULL,
    'Update su indirizzo_dettaglio_id deve essere bloccato dalla guard'
);

-- =========================================================
-- 4) Verifica che i valori non siano cambiati
-- =========================================================
SELECT is(
    (
        SELECT pdp
        FROM anagrafiche.pdp
        WHERE pdp = (SELECT pdp_ok FROM tmp_codici_pdp)
    ),
    (SELECT pdp_ok FROM tmp_codici_pdp),
    'Il codice PDP resta invariato dopo tentativi di update'
);

SELECT is(
    (
        SELECT indirizzo_dettaglio_id
        FROM anagrafiche.pdp
        WHERE pdp = (SELECT pdp_ok FROM tmp_codici_pdp)
    ),
    (SELECT indirizzo_dettaglio_id FROM tmp_pdp_guard),
    'L''indirizzo_dettaglio_id resta invariato dopo tentativi di update'
);

SELECT * FROM finish();

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia nulla dietro di se'. Le DELETE del cleanup restano
-- perche' dove sono un'asserzione devono girare davvero.
ROLLBACK;
