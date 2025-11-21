-- ---------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- Liquibase changelog per Zero ERP
-- Copyright (C) 2025 Tid (Michele Carlo Titini)
--
-- Rilasciato sotto GNU GPLv3 o versione successiva.
-- Vedi LICENSE.md per il testo completo della licenza.
-- ------------------------------------------------------------




-- Numero di test
SELECT plan(7);

-- =========================================================
-- Costanti di test
-- =========================================================
-- TODO: adatta piva/cf/codici a tuo piacere, basta che siano univoci e finti
WITH costanti AS (
    SELECT
        '01677080440'::text   AS piva_test,
        'TTNMHL68E07D042Z'::text  AS cf_test,
        NULL  AS codice_istanza_test,
        NULL   AS codice_ba_test,
        'CL'::varchar              AS codice_ruolo_cliente,   -- config.tipi_ruoli.codice
        'GAS'::varchar             AS codice_utility_test     -- config.utilities.codice
)
-- Cleanup iniziale: CLIENTI
DELETE FROM anagrafiche.clienti cli
USING anagrafiche.soggetti_ruoli sr,
      anagrafiche.soggetti s,
      costanti k
WHERE cli.soggetto_ruolo_id = sr.id
  AND sr.soggetto_id = s.id
  AND s.codice_fiscale = k.cf_test;

WITH costanti AS (
    SELECT
        '01677080440'::text   AS piva_test,
        'TTNMHL68E07D042Z'::text  AS cf_test,
        NULL  AS codice_istanza_test,
        NULL   AS codice_ba_test,
        'CL'::varchar              AS codice_ruolo_cliente,
        'GAS'::varchar             AS codice_utility_test
)
-- Cleanup: BILLING ACCOUNT
DELETE FROM anagrafiche.billing_account ba
USING anagrafiche.istanze_utilities iu,
      anagrafiche.soggetti_ruoli sr,
      anagrafiche.soggetti s,
      costanti k
WHERE ba.istanza_utility_id = iu.id
  AND ba.soggetto_ruolo_id = sr.id
  AND sr.soggetto_id = s.id
  AND s.codice_fiscale = k.cf_test;
  
WITH costanti AS (
    SELECT
        '01677080440'::text   AS piva_test,
        'TTNMHL68E07D042Z'::text  AS cf_test,
        NULL  AS codice_istanza_test,
        NULL   AS codice_ba_test,
        'CL'::varchar              AS codice_ruolo_cliente,
        'GAS'::varchar             AS codice_utility_test
)
-- Cleanup: ISTANZE
DELETE FROM anagrafiche.istanze_utilities iu
USING anagrafiche.soggetti s,
      costanti k
WHERE iu.soggetto_id = s.id
  AND s.codice_fiscale = k.cf_test;

WITH costanti AS (
    SELECT
        '01677080440'::text   AS piva_test,
        'TTNMHL68E07D042Z'::text  AS cf_test,
        NULL  AS codice_istanza_test,
        NULL   AS codice_ba_test,
        'CL'::varchar              AS codice_ruolo_cliente,
        'GAS'::varchar             AS codice_utility_test
)
-- Cleanup: SOGGETTI_RUOLI
DELETE FROM anagrafiche.soggetti_ruoli sr
USING anagrafiche.soggetti s,
      config.tipi_ruoli tr,
      costanti k
WHERE sr.soggetto_id = s.id
  AND sr.ruolo_id = tr.id
    AND s.codice_fiscale = k.cf_test
  AND tr.codice_interno = k.codice_ruolo_cliente;

WITH costanti AS (
    SELECT
        '01677080440'::text   AS piva_test,
        'TTNMHL68E07D042Z'::text  AS cf_test,
        NULL  AS codice_istanza_test,
        NULL   AS codice_ba_test,
        'CL'::varchar              AS codice_ruolo_cliente,
        'GAS'::varchar             AS codice_utility_test
)
-- Cleanup: CONTATTI
DELETE FROM anagrafiche.contatti c
USING anagrafiche.soggetti s,
      costanti k
WHERE c.soggetto_id = s.id
  AND s.codice_fiscale = k.cf_test;

WITH costanti AS (
    SELECT
        '01677080440'::text   AS piva_test,
        'TTNMHL68E07D042Z'::text  AS cf_test,
        NULL  AS codice_istanza_test,
        NULL   AS codice_ba_test,
        'CL'::varchar              AS codice_ruolo_cliente,
        'GAS'::varchar             AS codice_utility_test
)
-- Cleanup: SOGGETTI
DELETE FROM anagrafiche.soggetti s
USING costanti k
WHERE s.codice_fiscale = k.cf_test;

-- =========================================================
-- Inizio transazione applicativa
-- =========================================================
BEGIN;

-- ---------------------------------------------------------
-- 1) Recupero ruolo CLIENTE (config.tipi_ruoli)
-- ---------------------------------------------------------
WITH costanti AS (
    SELECT
        '01677080440'::text   AS piva_test,
        'TTNMHL68E07D042Z'::text  AS cf_test,
        NULL  AS codice_istanza_test,
        NULL   AS codice_ba_test,
        'CL'::varchar              AS codice_ruolo_cliente,
        'GAS'::varchar             AS codice_utility_test
),
ruolo_cliente AS (
    SELECT tr.id
    FROM config.tipi_ruoli tr, costanti k
    WHERE tr.codice_interno = k.codice_ruolo_cliente
)
SELECT *
INTO TEMP TABLE tmp_ruolo_cliente
FROM ruolo_cliente;

SELECT is(
    (SELECT count(*)::int FROM tmp_ruolo_cliente),
    1,
    'Trovato esattamente 1 ruolo cliente (config.tipi_ruoli.codice = CL)'
);

-- ---------------------------------------------------------
-- 2) Recupero utility (config.utilities)
-- ---------------------------------------------------------
WITH costanti AS (
    SELECT
        '01677080440'::text   AS piva_test,
        'TTNMHL68E07D042Z'::text  AS cf_test,
        NULL  AS codice_istanza_test,
        NULL   AS codice_ba_test,
        'CL'::varchar              AS codice_ruolo_cliente,
        'GAS'::varchar             AS codice_utility_test
),
utility_sel AS (
    SELECT u.id
    FROM config.utilities u, costanti k
    WHERE u.codice_interno = k.codice_utility_test
)
SELECT *
INTO TEMP TABLE tmp_utility
FROM utility_sel;

SELECT is(
    (SELECT count(*)::int FROM tmp_utility),
    1,
    'Trovata esattamente 1 utility di test (config.utilities.codice = GAS)'
);

-- ---------------------------------------------------------
-- 3) Inserimento soggetto (PG) e contatto
-- ---------------------------------------------------------
WITH costanti AS (
    SELECT
        '01677080440'::text   AS piva_test,
        'TTNMHL68E07D042Z'::text  AS cf_test,
        NULL  AS codice_istanza_test,
        NULL   AS codice_ba_test,
        'CL'::varchar              AS codice_ruolo_cliente,
        'GAS'::varchar             AS codice_utility_test
),
nuovo_soggetto AS (
    INSERT INTO anagrafiche.soggetti (
        ragione_sociale,
        cognome,
        nome,
        sesso,
        stato_id,
       -- partita_iva,
        codice_fiscale,
        tipo_soggetto_dettaglio_id,
        storicizza,
        attivo
    )
    SELECT
        NULL,
        'Titini',
        'Michele Carlo',
        'M',
        1,                 -- TODO: stato_id IT, adatta se diverso
       -- k.piva_test,
        k.cf_test,
        3,                 -- TODO: tipo_soggetto_dettaglio_id (PG IT), adatta se diverso
        TRUE,
        TRUE
    FROM costanti k
    RETURNING id, codice
)
SELECT *
INTO TEMP TABLE tmp_soggetto
FROM nuovo_soggetto;

SELECT is(
    (SELECT count(*)::int FROM tmp_soggetto),
    1,
    'Inserito esattamente 1 soggetto di test (PG)'
);

-- Contatto minimo valido per soddisfare il constraint sui soggetti
INSERT INTO anagrafiche.contatti (
    tipo_contatto_id,
    soggetto_id,
    nominativo,
    email,
    is_default,
    default_context
)
VALUES (
    1,  -- TODO: tipo_contatto_id valido da config.tipi_contatti
    (SELECT id FROM tmp_soggetto),
    'Referente Cliente Test pgTAP',
    'cliente.happypath@example.com',
    TRUE,
    'soggetto'
);


-- 4) Assegnazione ruolo CLIENTE (soggetti_ruoli)
WITH ins_soggetto_ruolo AS (
    INSERT INTO anagrafiche.soggetti_ruoli (
        soggetto_id,
        ruolo_id,
        extra
    )
    SELECT
        s.id,
        rc.id,
        '{}'::jsonb
    FROM tmp_soggetto s,
         tmp_ruolo_cliente rc
    RETURNING id
)
SELECT id
INTO TEMP TABLE tmp_soggetto_ruolo
FROM ins_soggetto_ruolo;

SELECT is(
    (SELECT count(*)::int FROM tmp_soggetto_ruolo),
    1,
    'Assegnato esattamente 1 ruolo cliente al soggetto di test'
);



-- ---------------------------------------------------------
-- 5) Creazione istanza_utility (fittizia = TRUE, senza indirizzo)
--     ⚠ Richiede che il modello permetta indirizzo_dettaglio_id NULL
--        quando fittizia = TRUE, come da guida.
-- ---------------------------------------------------------
--WITH costanti AS (
--    SELECT
--        '01677080440'::text   AS piva_test,
--        'TTNMHL68E07D042Z'::text  AS cf_test,
--        NULL  AS codice_istanza_test,
--        NULL   AS codice_ba_test,
--        'CL'::varchar              AS codice_ruolo_cliente,
--        'GAS'::varchar             AS codice_utility_test
--)

WITH ins_istanze_utilities AS (

    INSERT INTO anagrafiche.istanze_utilities (
        fittizia,
    -- codice,
        proprietario_inquilino,
        soggetto_id,
        indirizzo_dettaglio_id
    )
    SELECT
        TRUE,                            -- fittizia
    -- k.codice_istanza_test,           -- codice istanza
        'I',                             -- proprietario_inquilino (I = inquilino? Adatta se serve)
        s.id,
        NULL                             -- nessun indirizzo_dettaglio per istanza fittizia
    FROM tmp_soggetto s
        -- costanti k
    RETURNING id
)

SELECT id
INTO TEMP TABLE tmp_istanza
FROM ins_istanze_utilities;

SELECT is(
    (SELECT count(*)::int FROM tmp_istanza),
    1,
    'Inserita esattamente 1 istanza_utility di test'
);

-- ---------------------------------------------------------
-- 6) Creazione billing_account per l’istanza
-- ---------------------------------------------------------
WITH costanti AS (
    SELECT
        '01677080440'::text   AS piva_test,
        'TTNMHL68E07D042Z'::text  AS cf_test,
        NULL  AS codice_istanza_test,
        NULL   AS codice_ba_test,
        'CL'::varchar              AS codice_ruolo_cliente,
        'GAS'::varchar             AS codice_utility_test
), 
tmp_billing_account AS (
INSERT INTO anagrafiche.billing_account (
    istanza_utility_id,
    soggetto_ruolo_id,
    utility_id,
    codice
)
SELECT
    i.id,
    sr.id,
    u.id,
    k.codice_ba_test
FROM tmp_istanza i,
     tmp_soggetto_ruolo sr,
     tmp_utility u,
     costanti k
RETURNING id
-- INTO TEMP TABLE tmp_billing_account;
)

SELECT is(
    (SELECT count(*)::int FROM tmp_billing_account),
    1,
    'Inserito esattamente 1 billing_account per l’istanza di test'
);

-- ---------------------------------------------------------
-- 7) Creazione cliente (clienti)
-- ---------------------------------------------------------
WITH ins AS (
    INSERT INTO anagrafiche.clienti (
        soggetto_ruolo_id,
        istanza_utility_id
        -- tipo_gg_scadenza_ft, nr_giorni_scadenza, cliente_pa
        -- hanno default, usiamo quelli
    )
    SELECT
        sr.id,
        i.id
    FROM tmp_soggetto_ruolo sr,
         tmp_istanza i
    RETURNING id
)
SELECT id
INTO TEMP TABLE tmp_cliente
FROM ins;

SELECT is(
    (SELECT count(*)::int FROM tmp_cliente),
    1,
    'Inserito esattamente 1 cliente collegato all’istanza e al ruolo cliente'
);

-- Forzo valutazione dei constraint deferrable
SET CONSTRAINTS ALL IMMEDIATE;

COMMIT;

-- =========================================================
-- Cleanup finale (idempotenza)
-- =========================================================
WITH costanti AS (
    SELECT
        '01677080440'::text   AS piva_test,
        'TTNMHL68E07D042Z'::text  AS cf_test,
        NULL  AS codice_istanza_test,
        NULL   AS codice_ba_test,
        'CL'::varchar              AS codice_ruolo_cliente,
        'GAS'::varchar             AS codice_utility_test
)
DELETE FROM anagrafiche.clienti cli
USING anagrafiche.soggetti_ruoli sr,
      anagrafiche.soggetti s,
      costanti k
WHERE cli.soggetto_ruolo_id = sr.id
  AND sr.soggetto_id = s.id
  AND s.partita_iva = k.piva_test;

WITH costanti AS (
    SELECT
        '01677080440'::text   AS piva_test,
        'TTNMHL68E07D042Z'::text  AS cf_test,
        NULL  AS codice_istanza_test,
        NULL   AS codice_ba_test,
        'CL'::varchar              AS codice_ruolo_cliente,
        'GAS'::varchar             AS codice_utility_test
)
DELETE FROM anagrafiche.billing_account ba
USING anagrafiche.istanze_utilities iu,
      anagrafiche.soggetti_ruoli sr,
      anagrafiche.soggetti s,
      costanti k
WHERE ba.istanza_utility_id = iu.id
  AND ba.soggetto_ruolo_id = sr.id
  AND sr.soggetto_id = s.id
  AND s.partita_iva = k.piva_test;

WITH costanti AS (
    SELECT
        '01677080440'::text   AS piva_test,
        'TTNMHL68E07D042Z'::text  AS cf_test,
        NULL  AS codice_istanza_test,
        NULL   AS codice_ba_test,
        'CL'::varchar              AS codice_ruolo_cliente,
        'GAS'::varchar             AS codice_utility_test
)
DELETE FROM anagrafiche.istanze_utilities iu
USING anagrafiche.soggetti s,
      costanti k
WHERE iu.soggetto_id = s.id
  AND s.partita_iva = k.piva_test;

WITH costanti AS (
    SELECT
        '01677080440'::text   AS piva_test,
        'TTNMHL68E07D042Z'::text  AS cf_test,
        NULL  AS codice_istanza_test,
        NULL   AS codice_ba_test,
        'CL'::varchar              AS codice_ruolo_cliente,
        'GAS'::varchar             AS codice_utility_test
)
DELETE FROM anagrafiche.soggetti_ruoli sr
USING anagrafiche.soggetti s,
      config.tipi_ruoli tr,
      costanti k
WHERE sr.soggetto_id = s.id
  AND sr.ruolo_id = tr.id
  AND s.partita_iva = k.piva_test
  AND tr.codice_interno = k.codice_ruolo_cliente;

WITH costanti AS (
    SELECT
        '01677080440'::text   AS piva_test,
        'TTNMHL68E07D042Z'::text  AS cf_test,
        NULL  AS codice_istanza_test,
        NULL   AS codice_ba_test,
        'CL'::varchar              AS codice_ruolo_cliente,
        'GAS'::varchar             AS codice_utility_test
)
DELETE FROM anagrafiche.contatti c
USING anagrafiche.soggetti s,
      costanti k
WHERE c.soggetto_id = s.id
  AND s.partita_iva = k.piva_test;

WITH costanti AS (
    SELECT
        '01677080440'::text   AS piva_test,
        'TTNMHL68E07D042Z'::text  AS cf_test,
        NULL  AS codice_istanza_test,
        NULL   AS codice_ba_test,
        'CL'::varchar              AS codice_ruolo_cliente,
        'GAS'::varchar             AS codice_utility_test
)
DELETE FROM anagrafiche.soggetti s
USING costanti k
WHERE s.partita_iva = k.piva_test;

-- Fine test
SELECT * FROM finish();
