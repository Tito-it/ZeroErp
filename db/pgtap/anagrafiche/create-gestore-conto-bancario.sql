-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: ruolo Gestore + abbinamento conto bancario
--       con associazione obbligatoria a bank_branches
--
-- Scenario:
--   - Legge automaticamente il primo Gestore da anagrafiche.gestori
--   - Legge una filiale da anagrafiche.bank_branches
--   - Crea un conto in anagrafiche.conti_bancari legato alla filiale
--   - Abbina il conto al Gestore in anagrafiche.soggetti_ruoli_conti_bancari
-- ------------------------------------------------------------

-- Numero di test che ci aspettiamo di eseguire

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
-- ⚠️ Questo file non apre una transazione propria: la riga va prima di plan().
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(6);

-- =========================================================
-- Costanti per il test (TEMP TABLE)
-- =========================================================
CREATE TEMP TABLE tmp_costanti_gestore_banca AS
SELECT
    'IT99Z0000000000000000000000'::varchar AS iban_test,       -- IBAN fittizio ma valido per il CHECK
    'BGESTIT2XXX'::varchar                     AS bic_swift_test,
    'INCASSO'::varchar                         AS uso_test;

-- =========================================================
-- Pulizia preventiva di eventuali residui
-- =========================================================
DELETE FROM anagrafiche.soggetti_ruoli_conti_bancari srb
USING anagrafiche.conti_bancari cb,
      tmp_costanti_gestore_banca k
WHERE srb.conto_bancario_id = cb.id
  AND cb.iban = k.iban_test;

DELETE FROM anagrafiche.conti_bancari cb
USING tmp_costanti_gestore_banca k
WHERE cb.iban = k.iban_test;

-- =========================================================
-- Inizio transazione “applicativa”
-- =========================================================
BEGIN;

-- ---------------------------------------------------------
-- 1) Recupero del Gestore
-- ---------------------------------------------------------
CREATE TEMP TABLE tmp_gestore AS
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
    (SELECT count(*) FROM tmp_gestore) = 1,
    'Esiste almeno un Gestore in anagrafiche.gestori (letto il primo disponibile)'
);

-- ---------------------------------------------------------
-- 2) Recupero di una filiale bancaria da usare per il conto
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
    'Esiste almeno una bank_branch da usare per il conto del Gestore'
);

-- ---------------------------------------------------------
-- 3) Inserimento conto bancario per il Gestore
--    con bank_branch_id valorizzato
-- ---------------------------------------------------------
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
        'Conto Gestore Test pgTAP',
        'IT',
        TRUE,
        FALSE,
        jsonb_build_object('test_scope', 'gestore_abbinamento_banca'),
        b.id      -- filiale obbligatoria
    FROM tmp_costanti_gestore_banca k,
         tmp_bank_branch b
    RETURNING id
)
SELECT id
INTO TEMP TABLE tmp_conto_gestore
FROM nuovo_conto;

-- Test 3: conto bancario inserito
SELECT is(
    (SELECT count(*)::int FROM tmp_conto_gestore),
    1,
    'Inserito esattamente 1 conto bancario per il Gestore (con bank_branch_id valorizzato)'
);

-- ---------------------------------------------------------
-- 4) Associazione conto ↔ Gestore in soggetti_ruoli_conti_bancari
-- ---------------------------------------------------------
WITH link AS (
    INSERT INTO anagrafiche.soggetti_ruoli_conti_bancari (
        soggetto_ruolo_id,
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
        g.soggetto_ruolo_id,
        c.id,
        k.uso_test,
        TRUE,                       -- conto predefinito per INCASSO
        CURRENT_DATE,
        NULL,                       -- valido fino a data open-ended
        NULL,                       -- intestazione_dichiarata non specificata
        FALSE,                      -- non ancora verificato
        FALSE,                      -- non bloccato
        jsonb_build_object('test_scope', 'gestore_abbinamento_banca')
    FROM tmp_gestore g,
         tmp_conto_gestore c,
         tmp_costanti_gestore_banca k
    RETURNING id
)
SELECT id
INTO TEMP TABLE tmp_link_gestore_conto
FROM link;

-- Test 4: associazione creata
SELECT is(
    (SELECT count(*)::int FROM tmp_link_gestore_conto),
    1,
    'Creata esattamente 1 associazione soggetto_ruolo↔conto_bancario per il Gestore'
);

-- ---------------------------------------------------------
-- 5) Verifica di coerenza sull’associazione
-- ---------------------------------------------------------
SELECT ok(
    EXISTS (
        SELECT 1
        FROM anagrafiche.soggetti_ruoli_conti_bancari srb
        JOIN tmp_gestore g
          ON srb.soggetto_ruolo_id = g.soggetto_ruolo_id
        JOIN tmp_conto_gestore c
          ON srb.conto_bancario_id = c.id
        JOIN tmp_costanti_gestore_banca k
          ON srb.uso = k.uso_test
        WHERE srb.predefinito = TRUE
          AND srb.bloccato   = FALSE
          AND (srb.valido_al IS NULL OR srb.valido_al >= srb.valido_dal)
    ),
    'L’associazione Gestore↔conto bancario è coerente (uso=INCASSO, predefinito, non bloccato, validità corretta)'
);

-- ---------------------------------------------------------
-- 6) Verifica IBAN, stato del conto e legame con la filiale
-- ---------------------------------------------------------
SELECT ok(
    EXISTS (
        SELECT 1
        FROM anagrafiche.conti_bancari cb
        JOIN tmp_conto_gestore tcg ON cb.id = tcg.id
        JOIN tmp_costanti_gestore_banca k ON cb.iban = k.iban_test
        JOIN tmp_bank_branch bb       ON cb.bank_branch_id = bb.id
        WHERE cb.attivo       = TRUE
          AND cb.verificato   = FALSE
          AND cb.bank_branch_id IS NOT NULL
    ),
    'Il conto bancario del Gestore ha IBAN atteso, è attivo, non verificato e collegato a una bank_branch'
);

-- Forzo la verifica dei constraint DEFERRABLE (se presenti)
SET CONSTRAINTS ALL IMMEDIATE;

COMMIT;

-- Fine test
SELECT * FROM finish();
