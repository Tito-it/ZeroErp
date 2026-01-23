-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: snapshot precontrattuali su vendite.contratti_utilities
--       e blocco update su anagrafiche.istanze_dati_precontrattuali
--
-- Elenco test:
-- 1) Precondizioni: billing_account senza precontrattuali
-- 2) Precondizioni: esiste almeno una classe_utenza
-- 3) Precondizioni: esiste almeno uno stato_doc_contratto attivo
-- 4) Inserimento precontrattuale di test
-- 5) Creazione contratto di test
-- 6) Snapshot creato in contratti_utilities
-- 7) Snapshot collegato al precontrattuale sorgente
-- 8) Classe utenza snapshot coerente
-- 9) param_1_num snapshot coerente
-- 10) param_2_txt snapshot coerente
-- 11) meta snapshot coerente
-- 12) Update precontrattuale bloccato dopo snapshot
-- ------------------------------------------------------------

SELECT plan(12);

-- ============================================================
-- 0) Costanti e precondizioni
-- ============================================================
CREATE TEMP TABLE tmp_costanti_cu AS
SELECT
    'pgtap_contratti_utilities'::text AS test_scope;

-- 0.1: Seleziona un billing_account con istanza/utility senza precontrattuali
CREATE TEMP TABLE tmp_ba AS
SELECT
    ba.id AS billing_account_id,
    ba.istanza_utility_id,
    ba.utility_id
FROM anagrafiche.billing_account ba
LEFT JOIN anagrafiche.istanze_dati_precontrattuali idp
  ON idp.istanza_utility_id = ba.istanza_utility_id
 AND idp.utility_id = ba.utility_id
WHERE idp.id IS NULL
ORDER BY ba.id
LIMIT 1;

SELECT is(
    (SELECT count(*)::int FROM tmp_ba),
    1,
    'Esiste almeno un billing_account con istanza/utility senza precontrattuali'
);

-- 0.2: Esiste almeno una classe_utenza
CREATE TEMP TABLE tmp_classe_utenza AS
SELECT id AS classe_utenza_id
FROM config.classi_utenze
ORDER BY id
LIMIT 1;

SELECT is(
    (SELECT count(*)::int FROM tmp_classe_utenza),
    1,
    'Esiste almeno una classe_utenza'
);

-- 0.3: Esiste almeno uno stato_doc_contratto attivo
CREATE TEMP TABLE tmp_stato_doc AS
SELECT id AS stato_doc_contratto_id
FROM config.stati_doc_contratti
WHERE attivo IS TRUE
ORDER BY id
LIMIT 1;

SELECT is(
    (SELECT count(*)::int FROM tmp_stato_doc),
    1,
    'Esiste almeno uno stato_doc_contratto attivo'
);

-- ============================================================
-- 1) Inserimento precontrattuale di test
-- ============================================================
CREATE TEMP TABLE tmp_idp_test AS
WITH ins AS (
    INSERT INTO anagrafiche.istanze_dati_precontrattuali (
        istanza_utility_id,
        utility_id,
        classe_utenza_id,
        param_1_num,
        param_2_txt,
        meta
    )
    SELECT
        ba.istanza_utility_id,
        ba.utility_id,
        cu.classe_utenza_id,
        10.50,
        'TEST-SNAPSHOT',
        jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_cu))
    FROM tmp_ba ba,
         tmp_classe_utenza cu
    RETURNING id, classe_utenza_id, param_1_num, param_2_txt, meta
)
SELECT * FROM ins;

SELECT is(
    (SELECT count(*)::int FROM tmp_idp_test),
    1,
    'Inserito precontrattuale di test'
);

-- ============================================================
-- 2) Creazione contratto e snapshot
-- ============================================================
CREATE TEMP TABLE tmp_contratto AS
WITH ins AS (
    INSERT INTO vendite.contratti (
        billing_account_id,
        istanza_utility_id,
        utility_id,
        stato_doc_contratto_id
    )
    SELECT
        ba.billing_account_id,
        ba.istanza_utility_id,
        ba.utility_id,
        sd.stato_doc_contratto_id
    FROM tmp_ba ba,
         tmp_stato_doc sd
    RETURNING id
)
SELECT id FROM ins;

SELECT is(
    (SELECT count(*)::int FROM tmp_contratto),
    1,
    'Inserito contratto di test'
);

SELECT is(
    (SELECT count(*)::int
     FROM vendite.contratti_utilities cu
     WHERE cu.contratto_id = (SELECT id FROM tmp_contratto)),
    1,
    'Creato snapshot in contratti_utilities'
);

SELECT is(
    (SELECT cu.istanza_dati_precontrattuali_id
     FROM vendite.contratti_utilities cu
     WHERE cu.contratto_id = (SELECT id FROM tmp_contratto)),
    (SELECT id FROM tmp_idp_test),
    'Snapshot collegato al precontrattuale sorgente'
);

SELECT is(
    (SELECT cu.classe_utenza_id
     FROM vendite.contratti_utilities cu
     WHERE cu.contratto_id = (SELECT id FROM tmp_contratto)),
    (SELECT classe_utenza_id FROM tmp_idp_test),
    'Classe utenza snapshot coerente'
);

SELECT is(
    (SELECT cu.param_1_num::text
     FROM vendite.contratti_utilities cu
     WHERE cu.contratto_id = (SELECT id FROM tmp_contratto)),
    (SELECT param_1_num::text FROM tmp_idp_test),
    'param_1_num snapshot coerente'
);

SELECT is(
    (SELECT cu.param_2_txt
     FROM vendite.contratti_utilities cu
     WHERE cu.contratto_id = (SELECT id FROM tmp_contratto)),
    (SELECT param_2_txt FROM tmp_idp_test),
    'param_2_txt snapshot coerente'
);

SELECT is(
    (SELECT cu.meta::text
     FROM vendite.contratti_utilities cu
     WHERE cu.contratto_id = (SELECT id FROM tmp_contratto)),
    (SELECT meta::text FROM tmp_idp_test),
    'meta snapshot coerente'
);

-- ============================================================
-- 3) Blocco update dopo snapshot
-- ============================================================
SELECT throws_ok(
    $$
    UPDATE anagrafiche.istanze_dati_precontrattuali
       SET param_1_num = param_1_num + 1
     WHERE id = (SELECT id FROM tmp_idp_test);
    $$,
    'P0001',
    NULL,
    'Update precontrattuale bloccato dopo snapshot'
);
