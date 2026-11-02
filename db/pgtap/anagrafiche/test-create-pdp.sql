-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Elenco test:
-- 1) Esiste esattamente 1 utility con codice_interno = GAS
-- 2) Sono presenti in config.stradario gli id 1, 3, 4
-- 3) Generati/riusati 3 indirizzi_dettaglio (stradario_id 1,3,4 con estensioni T1/T2/T3)
-- 4) Gli indirizzi_dettaglio di test coprono esattamente i 3 stradario_id richiesti
-- 5) Inseriti/riusati esattamente 3 PDP di test
-- 6) Tutti i PDP di test appartengono alla stessa utility (GAS)
-- 7) Esiste lo stato tecnico DISP (DISPONIBILE) in config.stati_pdp
-- 8) Tutti i PDP creati dal test sono inizialmente in stato DISPONIBILE
--
-- Test: creazione indirizzi_dettaglio + PDP di esempio (GAS)
--       partendo da config.stradario.id IN (1,3,4)
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

-- ============================================================
-- 0) Precondizioni di base
-- ============================================================

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

-- 0.2: Gli id di stradario che useremo esistono
CREATE TEMP TABLE tmp_stradario_ids AS
SELECT unnest(ARRAY[1,3,4]) AS stradario_id;

CREATE TEMP TABLE tmp_stradario_presenti AS
SELECT s.id AS stradario_id
FROM config.stradario s
JOIN tmp_stradario_ids t
  ON t.stradario_id = s.id;

SELECT is(
    (SELECT count(*)::int FROM tmp_stradario_presenti),
    3,
    'Sono presenti in config.stradario gli id 1, 3, 4'
);

-- ============================================================
-- 1) Generazione / riuso indirizzi_dettaglio (T1/T2/T3)
-- ============================================================

-- Useremo civico = 1, estensioni T1 / T2 / T3
--  - stradario_id = 1 → T1
--  - stradario_id = 3 → T2
--  - stradario_id = 4 → T3

WITH addr_params AS (
    SELECT 1 AS stradario_id, 1 AS civico, 'T1'::varchar(10) AS estensione_civico
    UNION ALL
    SELECT 3, 1, 'T2'
    UNION ALL
    SELECT 4, 1, 'T3'
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
    -- appena inseriti
    SELECT
        i.id,
        i.stradario_id,
        i.civico,
        i.estensione_civico
    FROM ins i

    UNION ALL

    -- già esistenti, riusati
    SELECT
        idd.id,
        idd.stradario_id,
        idd.civico,
        idd.estensione_civico
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
INTO TEMP TABLE tmp_indirizzi_test
FROM all_addr;




SELECT is(
    (SELECT count(*)::int FROM tmp_indirizzi_test),
    3,
    'Generati/riusati 3 indirizzi_dettaglio (stradario_id 1,3,4 con estensioni T1/T2/T3)'
);

-- Verifica che tutti gli stradario_id desiderati siano coperti
SELECT is(
    (
        SELECT count(DISTINCT stradario_id)::int
        FROM tmp_indirizzi_test
    ),
    3,
    'Gli indirizzi_dettaglio di test coprono esattamente i 3 stradario_id richiesti'
);

-- ============================================================
-- 2) Generazione PDP GAS (GAS-PDP-0001/0002/0003)
-- ============================================================

-- 2.1: Inserimento/riuso PDP, uno per ciascun indirizzo di test
--      (idempotente: non elimina record esistenti referenziati da istanze_utilities)
WITH gas AS (
    SELECT utility_id
    FROM tmp_utility_gas
),
addr_ordered AS (
    -- Ordiniamo per stradario_id per avere un mapping stabile 1→0001, 3→0002, 4→0003
    SELECT
        id                AS indirizzo_dettaglio_id,
        stradario_id,
        row_number() OVER (ORDER BY stradario_id) AS rn
    FROM tmp_indirizzi_test
),
pdp_params AS (
    SELECT
        ('GAS-PDP-I' || a.indirizzo_dettaglio_id::text) AS pdp_code,
        a.indirizzo_dettaglio_id
    FROM addr_ordered a
),
ins AS (
    INSERT INTO anagrafiche.pdp (
        pdp,
        utility_id,
        indirizzo_dettaglio_id,
        cliente_id
    )
    SELECT
        p.pdp_code,
        g.utility_id,
        p.indirizzo_dettaglio_id,
        NULL::bigint
    FROM pdp_params p
    CROSS JOIN gas g
    WHERE NOT EXISTS (
        SELECT 1
        FROM anagrafiche.pdp px
        WHERE px.indirizzo_dettaglio_id = p.indirizzo_dettaglio_id
          AND px.utility_id = g.utility_id
    )
    RETURNING
        id,
        pdp,
        utility_id,
        indirizzo_dettaglio_id,
        cliente_id,
        stato_pdp_id,
        TRUE AS created_now
),
all_pdp AS (
    -- appena inseriti
    SELECT
        i.id,
        i.pdp,
        i.utility_id,
        i.indirizzo_dettaglio_id,
        i.cliente_id,
        i.stato_pdp_id,
        i.created_now
    FROM ins i

    UNION ALL

    -- già esistenti, riusati per coppia (indirizzo, utility)
    SELECT
        px.id,
        px.pdp,
        px.utility_id,
        px.indirizzo_dettaglio_id,
        px.cliente_id,
        px.stato_pdp_id,
        FALSE AS created_now
    FROM anagrafiche.pdp px
    JOIN pdp_params p
      ON p.indirizzo_dettaglio_id = px.indirizzo_dettaglio_id
    JOIN gas g
      ON g.utility_id = px.utility_id
)
SELECT *
INTO TEMP TABLE tmp_pdp_test
FROM all_pdp;

SELECT is(
    (SELECT count(*)::int FROM tmp_pdp_test),
    3,
    'Inseriti/riusati esattamente 3 PDP di test'
);

-- Verifica che siano tutti GAS
SELECT is(
    (
        SELECT count(DISTINCT utility_id)::int
        FROM tmp_pdp_test
    ),
    1,
    'Tutti i PDP di test appartengono alla stessa utility (GAS)'
);

-- ============================================================
-- 3) Verifica stato tecnico di default (DISPONIBILE)
--     (richiede che trgfn_pdp_set_default_stato imposti DISP)
-- ============================================================

-- Recupera l'id dello stato DISPONIBILE
CREATE TEMP TABLE tmp_stato_disp AS
SELECT id AS stato_id
FROM config.stati_pdp
WHERE codice_interno = 'DISP';

SELECT ok(
    (SELECT count(*) FROM tmp_stato_disp) = 1,
    'Esiste lo stato tecnico DISP (DISPONIBILE) in config.stati_pdp'
);

-- Verifica che tutti i PDP di test siano in stato DISPONIBILE
SELECT is(
    (
        SELECT count(*)::int
        FROM tmp_pdp_test p
        JOIN tmp_stato_disp d
          ON p.stato_pdp_id = d.stato_id
        WHERE p.created_now = TRUE
    ),
    (
        SELECT count(*)::int
        FROM tmp_pdp_test
        WHERE created_now = TRUE
    ),
    'Tutti i PDP creati dal test sono inizialmente in stato DISPONIBILE'
);

-- ============================================================
-- Fine test
-- ============================================================

SELECT * FROM finish();

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia nulla dietro di se'. Le DELETE del cleanup restano
-- perche' dove sono un'asserzione devono girare davvero.
ROLLBACK;
