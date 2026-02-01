-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
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
          AND COALESCE(idd.estensione_civico, '') =
              COALESCE(p.estensione_civico, '')
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
     AND COALESCE(idd.estensione_civico, '') =
         COALESCE(p.estensione_civico, '')
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
-- =========================================================
DELETE FROM anagrafiche.pdp
WHERE pdp = 'TEST-PDP-GUARD-0001';

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
        utilities_id,
        indirizzo_dettaglio_id,
        cliente_id
    )
    SELECT
        'TEST-PDP-GUARD-0001',
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
       SET pdp = 'TEST-PDP-GUARD-0002'
     WHERE pdp = 'TEST-PDP-GUARD-0001';
    $$,
    NULL,
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
     WHERE pdp = 'TEST-PDP-GUARD-0001';
    $$,
    NULL,
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
        WHERE pdp = 'TEST-PDP-GUARD-0001'
    ),
    'TEST-PDP-GUARD-0001',
    'Il codice PDP resta invariato dopo tentativi di update'
);

SELECT is(
    (
        SELECT indirizzo_dettaglio_id
        FROM anagrafiche.pdp
        WHERE pdp = 'TEST-PDP-GUARD-0001'
    ),
    (SELECT indirizzo_dettaglio_id FROM tmp_pdp_guard),
    'L''indirizzo_dettaglio_id resta invariato dopo tentativi di update'
);

SELECT * FROM finish();
