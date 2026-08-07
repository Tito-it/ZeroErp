-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: generazione conto bancario a livello SOGGETTO
--       per il soggetto collegato al Gestore
--
-- Scenario:
--   - Legge il primo Gestore da anagrafiche.gestori
--   - Legge una bank_branch da anagrafiche.bank_branches
--   - Crea un conto in anagrafiche.conti_bancari collegato
--     alla filiale (bank_branch_id NOT NULL)
--   - Collega il conto al SOGGETTO del Gestore in
--     anagrafiche.soggetti_conti_bancari (uso=INCASSO)
-- ------------------------------------------------------------

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
-- ⚠️ Questo file non apre una transazione propria: la riga va prima di plan().
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(4);

-- =========================================================
-- Costanti per il test (TEMP TABLE)
-- =========================================================
CREATE TEMP TABLE tmp_costanti_gestore_conto_soggetto AS
SELECT
    'IT66Z0000000000000000000000'::varchar AS iban_test,   -- IBAN fittizio valido
    'BGSOGIT2XXX'::varchar                     AS bic_swift_test,
    'INCASSO'::varchar                         AS uso_test;

BEGIN;

-- ---------------------------------------------------------
-- 1) Recupero del Gestore e del suo soggetto
-- ---------------------------------------------------------
CREATE TEMP TABLE tmp_gestore_soggetto AS
SELECT
    g.id                AS gestore_id,
    g.soggetto_ruolo_id AS soggetto_ruolo_id,
    sr.soggetto_id      AS soggetto_id
FROM anagrafiche.gestori g
JOIN anagrafiche.soggetti_ruoli sr
  ON sr.id = g.soggetto_ruolo_id
ORDER BY g.id
LIMIT 1;

-- Test 1: esiste almeno un Gestore
SELECT ok(
    (SELECT count(*) FROM tmp_gestore_soggetto) = 1,
    'Esiste almeno un Gestore, con relativo soggetto collegato'
);

-- ---------------------------------------------------------
-- 2) Recupero di una filiale bancaria (bank_branch) da usare
-- ---------------------------------------------------------
CREATE TEMP TABLE tmp_bank_branch AS
SELECT
    bb.id,
    bb.bank_code,
    bb.branch_code
FROM anagrafiche.bank_branches bb
ORDER BY bb.id
LIMIT 1;

-- Test 2: esiste almeno una bank_branch
SELECT ok(
    (SELECT count(*) FROM tmp_bank_branch) = 1,
    'Esiste almeno una bank_branch da collegare al conto del soggetto Gestore'
);

-- =========================================================
-- Pulizia preventiva:
--   - eventuali legami esistenti per l’IBAN di test
--   - eventuale predefinito INCASSO per il soggetto del Gestore
-- =========================================================
-- 2.1) Rimuovo eventuali legami soggetto_conti_bancari legati all’IBAN di test
DELETE FROM anagrafiche.soggetti_conti_bancari scb
USING anagrafiche.conti_bancari cb,
      tmp_costanti_gestore_conto_soggetto k,
      tmp_gestore_soggetto g
WHERE scb.conto_bancario_id = cb.id
  AND cb.iban = k.iban_test
  AND scb.soggetto_id = g.soggetto_id;

-- 2.2) Rimuovo eventuale conto con IBAN di test
DELETE FROM anagrafiche.conti_bancari cb
USING tmp_costanti_gestore_conto_soggetto k
WHERE cb.iban = k.iban_test;

-- 2.3) Per evitare violazioni dell'unico predefinito per uso,
--      disattivo eventuali predefiniti esistenti per (soggetto, uso_test)
UPDATE anagrafiche.soggetti_conti_bancari scb
SET predefinito = FALSE
FROM tmp_gestore_soggetto g,
     tmp_costanti_gestore_conto_soggetto k
WHERE scb.soggetto_id  = g.soggetto_id
  AND scb.uso          = k.uso_test
  AND scb.predefinito  = TRUE;

-- ---------------------------------------------------------
-- 3) Inserimento conto bancario a livello globale (conti_bancari)
--    con bank_branch_id obbligatorio
-- ---------------------------------------------------------
CREATE TEMP TABLE tmp_conto_soggetto_gestore AS
WITH nuovo_conto AS (
    INSERT INTO anagrafiche.conti_bancari (
        iban,
        bic_swift,
        intestatario_predefinito,
        paese,
        attivo,
        verificato,
        meta,
        bank_branch_id
    )
    SELECT
        k.iban_test,
        k.bic_swift_test,
        'Conto Soggetto Gestore Test pgTAP',
        'IT',
        TRUE,
        FALSE,
        jsonb_build_object('test_scope', 'gestore_conto_soggetto'),
        bb.id      -- filiale obbligatoria
    FROM tmp_costanti_gestore_conto_soggetto k,
         tmp_bank_branch bb
    RETURNING id
)
SELECT id
FROM nuovo_conto;

-- Test 3: conto bancario inserito
SELECT is(
    (SELECT count(*)::int FROM tmp_conto_soggetto_gestore),
    1,
    'Inserito esattamente 1 conto bancario per il soggetto del Gestore (con bank_branch_id valorizzato)'
);

-- ---------------------------------------------------------
-- 4) Associazione conto ↔ SOGGETTO in soggetti_conti_bancari
-- ---------------------------------------------------------
CREATE TEMP TABLE tmp_link_soggetto_conto AS
WITH link AS (
    INSERT INTO anagrafiche.soggetti_conti_bancari (
        soggetto_id,
        conto_bancario_id,
        uso,
        predefinito,
        valido_dal,
        valido_al,
        intestazione_dichiarata,
        verificato,
        bloccato,
        meta
    )
    SELECT
        g.soggetto_id,
        c.id,
        k.uso_test,
        TRUE,                       -- predefinito per uso INCASSO a livello soggetto
        CURRENT_DATE,
        NULL,                       -- open-ended
        NULL,                       -- intestazione_dichiarata non specificata
        FALSE,                      -- non ancora verificato
        FALSE,                      -- non bloccato
        jsonb_build_object('test_scope', 'gestore_conto_soggetto')
    FROM tmp_gestore_soggetto g,
         tmp_conto_soggetto_gestore c,
         tmp_costanti_gestore_conto_soggetto k
    RETURNING id
)
SELECT id
FROM link;

-- Test 4: legame soggetto↔conto creato
SELECT is(
    (SELECT count(*)::int FROM tmp_link_soggetto_conto),
    1,
    'Creato esattamente 1 legame soggetto↔conto in anagrafiche.soggetti_conti_bancari per il soggetto del Gestore'
);

-- (verifica immediata di eventuali constraint deferrable)
SET CONSTRAINTS ALL IMMEDIATE;

COMMIT;

SELECT * FROM finish();
