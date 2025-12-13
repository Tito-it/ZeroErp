-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: creazione indirizzi_dettaglio + PDP di esempio (GAS)
--       partendo da config.stradario.id IN (1,3,4)
-- ------------------------------------------------------------

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
          AND COALESCE(idd.estensione_civico, '') =
              COALESCE(p.estensione_civico, '')
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
     AND COALESCE(idd.estensione_civico, '') =
         COALESCE(p.estensione_civico, '')
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

-- 2.1: Cleanup eventuali vecchi PDP di test con quei codici
DELETE FROM anagrafiche.pdp
WHERE pdp IN ('GAS-PDP-0001', 'GAS-PDP-0002', 'GAS-PDP-0003');

-- 2.2: Inserimento PDP, uno per ciascun indirizzo di test
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
        CASE rn
            WHEN 1 THEN 'GAS-PDP-0001'
            WHEN 2 THEN 'GAS-PDP-0002'
            WHEN 3 THEN 'GAS-PDP-0003'
        END AS pdp_code,
        a.indirizzo_dettaglio_id
    FROM addr_ordered a
),
ins AS (
    INSERT INTO anagrafiche.pdp (
        pdp,
        utilities_id,
        indirizzo_dettaglio_id,
        cliente_id
    )
    SELECT
        p.pdp_code,
        g.utility_id,
        p.indirizzo_dettaglio_id,
        NULL::bigint
    FROM pdp_params p,
         gas g
    RETURNING id, pdp, utilities_id, indirizzo_dettaglio_id, cliente_id, stato_pdp_id
)
SELECT *
INTO TEMP TABLE tmp_pdp_test
FROM ins;

SELECT is(
    (SELECT count(*)::int FROM tmp_pdp_test),
    3,
    'Inseriti esattamente 3 PDP di test (GAS-PDP-0001..0003)'
);

-- Verifica che siano tutti GAS
SELECT is(
    (
        SELECT count(DISTINCT utilities_id)::int
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
    ),
    3,
    'Tutti i PDP di test sono inizialmente in stato DISPONIBILE'
);

-- ============================================================
-- Fine test
-- ============================================================

SELECT * FROM finish();
