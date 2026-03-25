-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: vw_conti_bancari_per_ruolo
--       fallback SOGGETTO per il ruolo Gestore (uso=INCASSO)
--
-- Scenario:
--   - Recupera il primo Gestore e il relativo soggetto_ruolo_id/soggetto_id
--   - Rimuove eventuali conti di RUOLO per uso=INCASSO (per forzare il fallback)
--   - Crea un conto a livello soggetto (soggetti_conti_bancari, uso=INCASSO, predefinito=true)
--   - Verifica che la vista anagrafiche.vw_conti_bancari_per_ruolo
--     selezioni il conto dal SOGGETTO (fonte='SOGGETTO')
-- ------------------------------------------------------------

SELECT plan(5);

-- =========================================================
-- Costanti per il test
-- =========================================================
CREATE TEMP TABLE tmp_costanti_vw_conto_gestore AS
SELECT
    'IT77Z0000000000000000000000'::varchar AS iban_test,   -- IBAN fittizio ma valido
    'AGSOGIT2XXX'::varchar                     AS bic_swift_test,
    'INCASSO'::varchar                        AS uso_test;

BEGIN;

-- ---------------------------------------------------------
-- 1) Recupero del Gestore e del suo soggetto_ruolo/soggetto
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
    'Esiste almeno un Gestore, con relativo soggetto_ruolo e soggetto'
);

-- ---------------------------------------------------------
-- 2) Recupero di una bank_branch da usare per il conto
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
-- Pulizia scenario per rendere il test deterministico
-- =========================================================

-- 2.1) Elimino eventuali legami di RUOLO per il Gestore e uso di test

DELETE FROM anagrafiche.soggetti_ruoli_conti_bancari srb
USING tmp_gestore_soggetto g,
      tmp_costanti_vw_conto_gestore k
WHERE srb.soggetto_ruolo_id = g.soggetto_ruolo_id
  AND srb.uso               = k.uso_test;
  
-- 2.2) Elimino eventuali legami soggetto_conti_bancari legati all’IBAN di test
DELETE FROM anagrafiche.soggetti_conti_bancari scb
USING anagrafiche.conti_bancari cb,
      tmp_gestore_soggetto g,
      tmp_costanti_vw_conto_gestore k
WHERE scb.conto_bancario_id = cb.id
  AND cb.iban               = k.iban_test
  AND scb.soggetto_id       = g.soggetto_id;

-- 2.3) Elimino l’eventuale conto con lo stesso IBAN di test
DELETE FROM anagrafiche.conti_bancari cb
USING tmp_costanti_vw_conto_gestore k
WHERE cb.iban = k.iban_test;

-- 2.4) Per evitare problemi con l’unico predefinito per uso a livello soggetto,
--      disattivo eventuali predefiniti esistenti per (soggetto, uso_test)
UPDATE anagrafiche.soggetti_conti_bancari scb
SET predefinito = FALSE
FROM tmp_gestore_soggetto g,
     tmp_costanti_vw_conto_gestore k
WHERE scb.soggetto_id = g.soggetto_id
  AND scb.uso         = k.uso_test
  AND scb.predefinito = TRUE;

-- ---------------------------------------------------------
-- 3) Inserimento conto bancario globale (conti_bancari)
--    con bank_branch_id obbligatorio
-- ---------------------------------------------------------
CREATE TEMP TABLE tmp_conto_vw_gestore AS
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
        'Conto Soggetto Gestore Test vw',
        'IT',
        TRUE,
        FALSE,
        jsonb_build_object('test_scope', 'vw_conti_bancari_per_ruolo_gestore'),
        bb.id
    FROM tmp_costanti_vw_conto_gestore k,
         tmp_bank_branch bb
    RETURNING id
)
SELECT id
FROM nuovo_conto;

-- Sanity: deve esistere 1 solo conto creato
SELECT is(
    (SELECT count(*)::int FROM tmp_conto_vw_gestore),
    1,
    'Creato esattamente 1 conto bancario globale per il soggetto del Gestore'
);

-- ---------------------------------------------------------
-- 4) Legame soggetto ↔ conto in soggetti_conti_bancari (fallback)
-- ---------------------------------------------------------
CREATE TEMP TABLE tmp_link_soggetto_conto_vw AS
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
        TRUE,                       -- predefinito per INCASSO a livello soggetto
        CURRENT_DATE,
        NULL,
        NULL,
        FALSE,
        FALSE,
        jsonb_build_object('test_scope', 'vw_conti_bancari_per_ruolo_gestore')
    FROM tmp_gestore_soggetto g,
         tmp_conto_vw_gestore c,
         tmp_costanti_vw_conto_gestore k
    RETURNING id
)
SELECT id
FROM link;

-- ---------------------------------------------------------
-- 5) Verifica della vista anagrafiche.vw_conti_bancari_per_ruolo
-- ---------------------------------------------------------

-- Test 4: la vista deve restituire almeno una riga per (soggetto_ruolo_id, uso_test)
SELECT ok(
    EXISTS (
        SELECT 1
        FROM anagrafiche.vw_conti_bancari_per_ruolo v
        JOIN tmp_gestore_soggetto g
          ON v.soggetto_ruolo_id = g.soggetto_ruolo_id
        JOIN tmp_costanti_vw_conto_gestore k
          ON v.uso = k.uso_test
    ),
    'vw_conti_bancari_per_ruolo restituisce una riga per il ruolo del Gestore e uso=INCASSO'
);

-- Test 5: la prima riga (per priorita) deve essere il conto SOGGETTO creato
-- Nota: la vista e flat (senza DISTINCT ON), ordina per priorita.
-- La selezione singola e delegata a fn_get_conto_bancario_predefinito.
SELECT is(
    (
        SELECT row(v.fonte, v.conto_bancario_id, v.predefinito)::text
        FROM anagrafiche.vw_conti_bancari_per_ruolo v
        JOIN tmp_gestore_soggetto g
          ON v.soggetto_ruolo_id = g.soggetto_ruolo_id
        JOIN tmp_costanti_vw_conto_gestore k
          ON v.uso = k.uso_test
        ORDER BY
            CASE
                WHEN v.fonte = 'RUOLO' AND v.istanza_utility_id IS NOT NULL THEN 1
                WHEN v.fonte = 'RUOLO' AND v.istanza_utility_id IS NULL     THEN 2
                WHEN v.fonte = 'SOGGETTO'                           THEN 3
            END,
            v.predefinito DESC, v.data_update DESC
        LIMIT 1
    ),
    (
        SELECT row('SOGGETTO'::varchar,
                   c.id,
                   TRUE)::text
        FROM tmp_conto_vw_gestore c
    ),
    'vw_conti_bancari_per_ruolo: prima riga per priorita e fonte=SOGGETTO, predefinito=true'
);

SET CONSTRAINTS ALL IMMEDIATE;

COMMIT;

SELECT * FROM finish();
