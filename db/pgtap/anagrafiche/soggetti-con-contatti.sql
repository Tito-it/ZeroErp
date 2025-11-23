-- ---------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- Liquibase changelog per Zero ERP
-- Copyright (C) 2025 Tid (Michele Carlo Titini)
--
-- Rilasciato sotto GNU GPLv3 o versione successiva.
-- Vedi LICENSE.md per il testo completo della licenza.
-- ------------------------------------------------------------



-- tests/pgtap/anagrafiche/soggetti-con-contatti.sql

-- Numero di test che ci aspettiamo di eseguire
SELECT plan(3);

-- Costanti per il test (CF/P.IVA di  riservati ai test)
-- Cambiale se ti servono valori diversi

-- Pulizia preventiva di eventuali residui
--WITH costanti AS (
--    SELECT
--        '01677080440'::text  AS piva_test,
--        'TTNMHL68E07D042Z'::text   AS cf_test
--)
--DELETE FROM anagrafiche.contatti c
--USING anagrafiche.soggetti s, costanti k
--WHERE c.soggetto_id = s.id
--  AND s.partita_iva = k.piva_test;
 -- AND s.codice_fiscale = k.cf_test;

WITH costanti AS (
    SELECT
        '01677080440'::text  AS piva_test,
        'TTNMHL68E07D042Z'::text   AS cf_test
)
DELETE FROM anagrafiche.soggetti s
USING costanti k
WHERE s.partita_iva = k.piva_test;
 --AND s.codice_fiscale = k.cf_test;

-- Inizio transazione “applicativa”
BEGIN;

WITH costanti AS (
    SELECT
        '01677080440'::text  AS piva_test,
        'TTNMHL68E07D042Z'::text   AS cf_test
),
nuovo_soggetto AS (
    INSERT INTO anagrafiche.soggetti (
        -- niente "codice", lo genera il trigger
        ragione_sociale,
        cognome,
        nome,
        sesso,
        stato_id,
        partita_iva,
        --codice_fiscale,
        tipo_soggetto_dettaglio_id,
        storicizza,
        attivo
    )
    SELECT
        'Cliente Test pgTAP',
        NULL,
        NULL,
        'S',
        1,                 -- stato_id IT (adatta se diverso)
        k.piva_test,
        --k.cf_test,
        3,                 -- tipo_soggetto_dettaglio_id (PG IT, adatta se diverso)
        TRUE,
        TRUE
    FROM costanti k
    RETURNING id, codice
)
SELECT *
INTO TEMP TABLE tmp_soggetto
FROM nuovo_soggetto;

-- 1) Verifico che il soggetto sia stato inserito
SELECT is(
    (SELECT count(*)::int FROM tmp_soggetto),
    1,
    'Inserito esattamente 1 soggetto di test'
);

-- 2) Inserisco almeno un contatto valido per quel soggetto
--    Usa un tipo_contatto_id valido dal tuo config.tipi_contatti (qui ipotizzo id = 1)
INSERT INTO anagrafiche.contatti (
    tipo_contatto_id,
    soggetto_id,
    nominativo,
    email,
    is_default,
    default_context
)
VALUES (
    1,  -- tipo_contatto_id da adattare
    (SELECT id FROM tmp_soggetto),
    'Referente Cliente Test pgTAP',
    'cliente.pgtap@example.com',
    TRUE,
    'soggetto'
);


-- 3) Verifico che esista almeno un contatto “valido” per il soggetto
SELECT is(
    (SELECT count(*)
       FROM anagrafiche.contatti c
      WHERE c.soggetto_id = (SELECT id FROM tmp_soggetto)
    )::int,
    1,
    'Inserito esattamente 1 contatto per il soggetto di test'
);


SELECT ok(
    EXISTS (
        SELECT 1
        FROM anagrafiche.contatti c
        WHERE c.soggetto_id = (SELECT id FROM tmp_soggetto)
          AND (
            c.email IS NOT NULL
            OR c.telefono IS NOT NULL
            OR c.cellulare IS NOT NULL
            OR c.pec IS NOT NULL
          )
    ),
    'Il soggetto di test ha almeno un contatto con un recapito valido'
);

-- Forzo la verifica dei constraint DEFERRABLE (incluso il tuo constraint trigger)
SET CONSTRAINTS ALL IMMEDIATE;


COMMIT;

-- Pulizia finale dei dati di test
WITH costanti AS (
    SELECT
        '01677080440'::text  AS piva_test,
        'TTNMHL68E07D042Z'::text   AS cf_test
)
DELETE FROM anagrafiche.contatti c
USING anagrafiche.soggetti s, costanti k
WHERE c.soggetto_id = s.id
  AND s.partita_iva = k.piva_test
  AND s.codice_fiscale = k.cf_test;

WITH costanti AS (
    SELECT
        '01677080440'::text  AS piva_test,
        'TTNMHL68E07D042Z'::text   AS cf_test
)
DELETE FROM anagrafiche.soggetti s
USING costanti k
WHERE s.partita_iva = k.piva_test
  AND s.codice_fiscale = k.cf_test;

-- Fine test
SELECT * FROM finish();
