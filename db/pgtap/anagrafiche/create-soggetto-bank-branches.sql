-- ---------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: creazione soggetto "Banca Zero" come ISTITUTO DI CREDITO
--       + inserimento di una filiale in anagrafiche.bank_branches
-- ------------------------------------------------------------

-- Numero di test che ci aspettiamo di eseguire
SELECT plan(4);

-- =========================================================
-- Costanti per il test (TEMP TABLE)
-- =========================================================
CREATE TEMP TABLE tmp_costanti_banca_zero AS
SELECT
    '05555555555'::text      AS piva_test,              -- P.IVA fittizia
    'BANK_B'::varchar        AS codice_ruolo_istituto,  -- config.tipi_ruoli.codice_interno (da adattare)
    'EUR'::varchar           AS codice_valuta,          -- se servirà in futuro
    'ZEROERP'::varchar       AS codice_prod_software,   -- se servirà in futuro
    '03069'::varchar         AS bank_code_test,         -- es. ABI fittizio
    '01234'::varchar         AS branch_code_test,       -- es. CAB fittizio
    'BZEROIT2XXX'::varchar   AS bic_swift_test;         -- BIC/SWIFT fittizio 8+3

-- =========================================================
-- Pulizia preventiva di eventuali residui
-- =========================================================

-- bank_branches → soggetti_ruoli → soggetti
DELETE FROM anagrafiche.bank_branches bb
USING anagrafiche.soggetti_ruoli sr,
      anagrafiche.soggetti s,
      tmp_costanti_banca_zero k
WHERE bb.soggetto_ruolo_id = sr.id
  AND sr.soggetto_id = s.id
  AND s.partita_iva = k.piva_test;

DELETE FROM anagrafiche.soggetti_ruoli sr
USING anagrafiche.soggetti s,
      config.tipi_ruoli tr,
      tmp_costanti_banca_zero k
WHERE sr.soggetto_id = s.id
  AND sr.tipo_ruolo_id = tr.id
  AND s.partita_iva = k.piva_test
  AND tr.codice_interno = k.codice_ruolo_istituto;

DELETE FROM anagrafiche.soggetti s
USING tmp_costanti_banca_zero k
WHERE s.partita_iva = k.piva_test;

-- =========================================================
-- Inizio transazione “applicativa”
-- =========================================================
BEGIN;

-- ---------------------------------------------------------
-- 1) Inserimento soggetto "Banca Zero Test pgTAP"
-- ---------------------------------------------------------
WITH nuovo_soggetto AS (
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
        'Banca Zero Test pgTAP',
        NULL,
        NULL,
        'S',
        1,                 -- stato_id IT (adatta se diverso)
        k.piva_test,
        3,                 -- tipo_soggetto_dettaglio_id (PG IT, adatta se diverso)
        TRUE,
        TRUE
    FROM tmp_costanti_banca_zero k
    RETURNING id, codice
)
SELECT *
INTO TEMP TABLE tmp_soggetto_banca
FROM nuovo_soggetto;

-- Test 1: soggetto inserito
SELECT is(
    (SELECT count(*)::int FROM tmp_soggetto_banca),
    1,
    'Inserito esattamente 1 soggetto di tipo Banca Zero'
);

-- Contatto minimo per il soggetto
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
    (SELECT id FROM tmp_soggetto_banca),
    'Referente Banca Zero Test pgTAP',
    'bancazero.pgtap@example.com',
    TRUE,
    'soggetto'
);

-- ---------------------------------------------------------
-- 2) Assegnazione ruolo ISTITUTO_CREDITO (es. codice 'IC')
--    tramite fn_get_or_create_soggetto_ruolo
-- ---------------------------------------------------------
WITH soggetto_ruolo_istituto AS (
    SELECT
        script.fn_get_or_create_soggetto_ruolo(
            p_soggetto_id   := s.id,
            p_cd_int_ruolo  := k.codice_ruolo_istituto
        ) AS id
    FROM tmp_soggetto_banca s,
         tmp_costanti_banca_zero k
)
SELECT id
INTO TEMP TABLE tmp_soggetto_ruolo_istituto
FROM soggetto_ruolo_istituto;

-- Test 2: ruolo istituto di credito assegnato
SELECT is(
    (SELECT count(*)::int FROM tmp_soggetto_ruolo_istituto),
    1,
    'Assegnato esattamente 1 ruolo ISTITUTO_CREDITO al soggetto Banca Zero'
);

-- ---------------------------------------------------------
-- 3) Inserimento filiale in anagrafiche.bank_branches
-- ---------------------------------------------------------
WITH ins_filiale AS (
    INSERT INTO anagrafiche.bank_branches (
        soggetto_ruolo_id,
        bank_code,
        branch_code,
        bic_swift,
        name
    )
    SELECT
        sr.id,
        k.bank_code_test,
        k.branch_code_test,
        k.bic_swift_test,
        'Banca Zero - Filiale Test pgTAP'
    FROM tmp_soggetto_ruolo_istituto sr,
         tmp_costanti_banca_zero k
    RETURNING id
)
SELECT id
INTO TEMP TABLE tmp_bank_branch
FROM ins_filiale;

-- Test 3: filiale inserita
SELECT is(
    (SELECT count(*)::int FROM tmp_bank_branch),
    1,
    'Inserita esattamente 1 filiale in anagrafiche.bank_branches per Banca Zero'
);

-- Test 4: verifica base su bank_code/branch_code e attivo
SELECT ok(
    EXISTS (
        SELECT 1
        FROM anagrafiche.bank_branches bb
        JOIN tmp_bank_branch tbb ON bb.id = tbb.id
        JOIN tmp_costanti_banca_zero k ON TRUE
        WHERE bb.bank_code   = k.bank_code_test
          AND bb.branch_code = k.branch_code_test
          AND bb.attivo      = TRUE
    ),
    'La filiale ha bank_code/branch_code attesi ed è attiva'
);

-- Forzo la verifica dei constraint DEFERRABLE
SET CONSTRAINTS ALL IMMEDIATE;

COMMIT;

-- (Opzionale) pulizia della temp table, non strettamente necessaria
-- DROP TABLE IF EXISTS tmp_costanti_banca_zero;

-- Fine test
SELECT * FROM finish();
