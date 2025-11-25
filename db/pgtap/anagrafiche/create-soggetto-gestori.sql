-- ---------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Copyright (C) 2025 Tid
--
-- Test: generazione soggetto + ruolo GESTORE e verifica
--       che anagrafiche.gestori sia singleton.
-- ------------------------------------------------------------

-- Numero di test che ci aspettiamo di eseguire
SELECT plan(5);

-- =========================================================
-- Costanti per il test (P.IVA riservata ai test)
-- Cambiale se ti servono valori diversi
-- =========================================================
WITH costanti AS (
    SELECT
        '09999999999'::text  AS piva_test,
        'GE'::varchar        AS codice_ruolo_gestore,  -- config.tipi_ruoli.codice_interno
        'EUR'::varchar       AS codice_valuta,         -- config.valute.codice_interno
        'ZEROERP'::varchar   AS codice_prod_software   -- codice prodotto software
)

-- Pulizia preventiva di eventuali residui
DELETE FROM anagrafiche.gestori g
USING anagrafiche.soggetti_ruoli sr,
      anagrafiche.soggetti s,
      costanti k
WHERE g.soggetto_ruolo_id = sr.id
  AND sr.soggetto_id = s.id
  AND s.partita_iva = k.piva_test;


WITH costanti AS (
    SELECT
        '09999999999'::text  AS piva_test,
        'GE'::varchar        AS codice_ruolo_gestore,
        'EUR'::varchar       AS codice_valuta,
        'ZEROERP'::varchar   AS codice_prod_software
)
DELETE FROM anagrafiche.soggetti_ruoli sr
USING anagrafiche.soggetti s,
      config.tipi_ruoli tr,
      costanti k
WHERE sr.soggetto_id = s.id
  AND sr.tipo_ruolo_id = tr.id
  AND s.partita_iva = k.piva_test
  AND tr.codice_interno = k.codice_ruolo_gestore;


WITH costanti AS (
    SELECT
        '09999999999'::text  AS piva_test,
        'GE'::varchar        AS codice_ruolo_gestore,
        'EUR'::varchar       AS codice_valuta,
        'ZEROERP'::varchar   AS codice_prod_software
)
DELETE FROM anagrafiche.soggetti s
USING costanti k
WHERE s.partita_iva = k.piva_test;


WITH costanti AS (
    SELECT
        '09999999999'::text  AS piva_test,
        'GE'::varchar        AS codice_ruolo_gestore,
        'EUR'::varchar       AS codice_valuta,
        'ZEROERP'::varchar   AS codice_prod_software
)
DELETE FROM anagrafiche.contatti c
USING anagrafiche.soggetti s,
      costanti k
WHERE c.soggetto_id = s.id
  AND s.partita_iva = k.piva_test;


-- =========================================================
-- Inizio transazione “applicativa”
-- =========================================================
BEGIN;

-- ---------------------------------------------------------
-- 1) Inserimento soggetto (PG con P.IVA) + contatto
-- ---------------------------------------------------------
WITH costanti AS (
    SELECT
        '09999999999'::text  AS piva_test,
        'GE'::varchar        AS codice_ruolo_gestore,
        'EUR'::varchar       AS codice_valuta,
        'ZEROERP'::varchar   AS codice_prod_software
),
nuovo_soggetto AS (
    INSERT INTO anagrafiche.soggetti (
        ragione_sociale,
        cognome,
        nome,
        sesso,
        stato_id,
        partita_iva,
        tipo_soggetto_dettaglio_id,
        storicizza,
        attivo
    )
    SELECT
        'Gestore Test pgTAP',
        NULL,
        NULL,
        'S',
        1,                 -- stato_id IT (adatta se diverso)
        k.piva_test,
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
    'Inserito esattamente 1 soggetto di test (gestore)'
);

-- Contatto minimo valido per soddisfare eventuali constraint sui soggetti
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
    'Referente Gestore Test pgTAP',
    'gestore.pgtap@example.com',
    TRUE,
    'soggetto'
);

-- ---------------------------------------------------------
-- 2) Assegnazione ruolo GESTORE (soggetti_ruoli)
--    tramite fn_get_or_create_soggetto_ruolo
-- ---------------------------------------------------------
WITH costanti AS (
    SELECT
        '09999999999'::text  AS piva_test,
        'GE'::varchar        AS codice_ruolo_gestore,
        'EUR'::varchar       AS codice_valuta,
        'ZEROERP'::varchar   AS codice_prod_software
),
soggetto_ruolo AS (
    SELECT
        script.fn_get_or_create_soggetto_ruolo(
            p_soggetto_id   := s.id,
            p_cd_int_ruolo  := k.codice_ruolo_gestore
        ) AS id
    FROM tmp_soggetto s,
         costanti k
)
SELECT id
INTO TEMP TABLE tmp_soggetto_ruolo
FROM soggetto_ruolo;

SELECT is(
    (SELECT count(*)::int FROM tmp_soggetto_ruolo),
    1,
    'Assegnato esattamente 1 ruolo GESTORE al soggetto di test'
);

-- ---------------------------------------------------------
-- 3) Creazione gestore in anagrafiche.gestori
-- ---------------------------------------------------------
WITH costanti AS (
    SELECT
        '09999999999'::text  AS piva_test,
        'GE'::varchar        AS codice_ruolo_gestore,
        'EUR'::varchar       AS codice_valuta,
        'ZEROERP'::varchar   AS codice_prod_software
),
valuta_sel AS (
    SELECT v.id
    FROM config.valute v, costanti k
    WHERE v.iso_code = k.codice_valuta
    LIMIT 1
),
ins_gestore AS (
    INSERT INTO anagrafiche.gestori (
        soggetto_ruolo_id,
        descrizione,
        cd_prod_software,
        valuta_id
    )
    SELECT
        sr.id,
        'Gestore Zero ERP - Test pgTAP',
        k.codice_prod_software,
        v.id
    FROM tmp_soggetto_ruolo sr,
         valuta_sel v,
         costanti k
    RETURNING id
)
SELECT id
INTO TEMP TABLE tmp_gestore
FROM ins_gestore;

SELECT is(
    (SELECT count(*)::int FROM tmp_gestore),
    1,
    'Inserito esattamente 1 gestore collegato al soggetto_ruolo GESTORE'
);

-- ---------------------------------------------------------
-- 4) Verifica che non sia possibile creare un secondo gestore
--    (singleton) tramite trigger di guard
-- ---------------------------------------------------------
SELECT throws_ok(
    $$
    WITH costanti AS (
        SELECT
            '09999999999'::text  AS piva_test,
            'GE'::varchar        AS codice_ruolo_gestore,
            'EUR'::varchar       AS codice_valuta,
            'ZEROERP'::varchar   AS codice_prod_software
    ),
    valuta_sel AS (
        SELECT v.id
        FROM config.valute v, costanti k
        WHERE v.iso_code = k.codice_valuta
        LIMIT 1
    )
    INSERT INTO anagrafiche.gestori (
        soggetto_ruolo_id,
        descrizione,
        cd_prod_software,
        valuta_id
    )
    SELECT
        sr.id,
        'Secondo Gestore Illegale - Test pgTAP',
        k.codice_prod_software,
        v.id
    FROM tmp_soggetto_ruolo sr,
         valuta_sel v,
         costanti k;
    $$,
    'P0001',  -- codice SQLSTATE atteso
    NULL,
    'Il tentativo di creare un secondo gestore genera un errore (regola singleton)'
);



-- ---------------------------------------------------------
-- 5) Verifica che non sia possibile creare un secondo soggetto
--    con stessa P.iva
-- ---------------------------------------------------------
SELECT throws_ok(
        $$
        WITH costanti AS (
            SELECT
                '09999999999'::text  AS piva_test,
                'GE'::varchar        AS codice_ruolo_gestore,
                'EUR'::varchar       AS codice_valuta,
                'ZEROERP'::varchar   AS codice_prod_software
        ),
       nuovo_soggetto AS (
        INSERT INTO anagrafiche.soggetti (
            ragione_sociale,
            cognome,
            nome,
            sesso,
            stato_id,
            partita_iva,
            tipo_soggetto_dettaglio_id,
            storicizza,
            attivo
        )
        SELECT
            'Gestore Test Doppio pgTAP',
            NULL,
            NULL,
            'S',
            1,                 -- stato_id IT (adatta se diverso)
            k.piva_test,
            3,                 -- tipo_soggetto_dettaglio_id (PG IT, adatta se diverso)
            TRUE,
            TRUE
        FROM costanti k
         RETURNING id, codice
    )
    SELECT *
    FROM nuovo_soggetto;
    $$,
    NULL,  -- codice SQLSTATE atteso
    NULL,
    'Il tentativo di creare un secondo soggetto con stessa P.IVA genera un errore (unique constraint)'
);



-- Forzo la valutazione dei constraint DEFERRABLE
SET CONSTRAINTS ALL IMMEDIATE;

COMMIT;


-- =========================================================
-- Pulizia finale (idempotenza)
-- =========================================================
/*
WITH costanti AS (
    SELECT
        '09999999999'::text  AS piva_test,
        'GE'::varchar        AS codice_ruolo_gestore,
        'EUR'::varchar       AS codice_valuta,
        'ZEROERP'::varchar   AS codice_prod_software
)
DELETE FROM anagrafiche.gestori g
USING anagrafiche.soggetti_ruoli sr,
      anagrafiche.soggetti s,
      costanti k
WHERE g.soggetto_ruolo_id = sr.id
  AND sr.soggetto_id = s.id
  AND s.partita_iva = k.piva_test;


WITH costanti AS (
    SELECT
        '09999999999'::text  AS piva_test,
        'GE'::varchar        AS codice_ruolo_gestore,
        'EUR'::varchar       AS codice_valuta,
        'ZEROERP'::varchar   AS codice_prod_software
)
DELETE FROM anagrafiche.soggetti_ruoli sr
USING anagrafiche.soggetti s,
      config.tipi_ruoli tr,
      costanti k
WHERE sr.soggetto_id = s.id
  AND sr.tipo_ruolo_id = tr.id
  AND s.partita_iva = k.piva_test
  AND tr.codice_interno = k.codice_ruolo_gestore;


WITH costanti AS (
    SELECT
        '09999999999'::text  AS piva_test,
        'GE'::varchar        AS codice_ruolo_gestore,
        'EUR'::varchar       AS codice_valuta,
        'ZEROERP'::varchar   AS codice_prod_software
)
DELETE FROM anagrafiche.contatti c
USING anagrafiche.soggetti s,
      costanti k
WHERE c.soggetto_id = s.id
  AND s.partita_iva = k.piva_test;

  */

-- Fine test
SELECT * FROM finish();
