-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
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

-- ⛔ 2026-09-23: QUESTO FILE E' UN TEST, E ORA SI COMPORTA COME TALE.
--   Fino a oggi apriva la transazione TARDI, chiamava la riga di contesto in
--   AUTOCOMMIT e chiudeva in COMMIT. Le conseguenze erano tre, e nessuna era
--   voluta:
--     1. su un database ricostruito la riga di contesto, fuori da una
--        transazione, COSTRUIVA e COMMITTAVA azienda + operatore (rev
--        20260920-01): un residuo per corsa, e soprattutto una MASCHERA —
--        da li' in poi ogni altro file trovava un operatore e non percorreva
--        piu' il ramo che costruisce. Misurato il 23-09: quella maschera
--        teneva verdi SEI file del lotto che senza di lei cadono;
--     2. il conto creato restava nel database a fine corsa;
--     3. i vincoli differiti scattavano al COMMIT su dati che restano, non
--        sul mondo del test.
--   Ora: transazione subito, contesto dentro, chiusura in ROLLBACK.
BEGIN;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
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

-- ---------------------------------------------------------
-- 1) Il Gestore: si PRENDE se c'e', si costruisce se non c'e'
-- ---------------------------------------------------------
-- ⛔ `anagrafiche.gestori` e' dato di MACCHINA: su un database ricostruito e'
--   vuota, e «il primo Gestore» non esiste. L'helper risponde quello che c'e'
--   (dbdev) o lo costruisce (CI) — non ne crea mai un secondo, che un guard
--   rifiuterebbe.
CREATE TEMP TABLE tmp_gestore_soggetto AS
SELECT gestore_id,
       gestore_soggetto_ruolo_id AS soggetto_ruolo_id,
       gestore_soggetto_id       AS soggetto_id
  FROM dbops.fn_pgtap_crea_gestore('conto soggetto');

-- Test 1: il Gestore c'e', col suo soggetto collegato
SELECT ok(
    (SELECT count(*) = 1 AND bool_and(soggetto_id IS NOT NULL)
       FROM tmp_gestore_soggetto),
    'Il Gestore c''e'', con relativo soggetto collegato'
);

-- ---------------------------------------------------------
-- 2) Recupero di una filiale bancaria (bank_branch) da usare
-- ---------------------------------------------------------
-- ⛔ Anche la filiale e' dato di MACCHINA: da zero `bank_branches` e' vuota.
-- ⚠️ E il verbo sta in un'istruzione SUA: un builder che scrive e un JOIN che
--   legge nella stessa istruzione condividono la snapshot, e la riga appena
--   scritta non si vede. Prima si costruisce, poi si legge.
CREATE TEMP TABLE tmp_bank_branch_id AS
SELECT bank_branch_id FROM dbops.fn_pgtap_crea_filiale_bancaria('gestore conto soggetto');

CREATE TEMP TABLE tmp_bank_branch AS
SELECT bb.id, bb.bank_code, bb.branch_code
  FROM anagrafiche.bank_branches bb
  JOIN tmp_bank_branch_id f ON f.bank_branch_id = bb.id;

-- Test 2: la filiale c'e', da collegare al conto del soggetto Gestore
SELECT ok(
    (SELECT count(*) FROM tmp_bank_branch) = 1,
    'La filiale bancaria c''e'', da collegare al conto del soggetto Gestore'
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
        script.fn_data_operativa(),
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

SELECT * FROM finish();

-- ⛔ ROLLBACK, non COMMIT (2026-09-23): questo file e' un test, e un test non
--   lascia dietro di se' il conto che ha creato.
ROLLBACK;
