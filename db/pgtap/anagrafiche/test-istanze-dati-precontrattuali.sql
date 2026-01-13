-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: insert e vincoli FK su anagrafiche.istanze_dati_precontrattuali
--       usando utility_id = 2 (GAS), una istanza_utility esistente
--       e una classe_utenza esistente.
-- ------------------------------------------------------------

SELECT plan(8);

-- ============================================================
-- 0) Costanti e precondizioni
-- ============================================================
CREATE TEMP TABLE tmp_costanti_idp AS
SELECT
    2::integer AS utility_id,
    'pgtap_istanze_dati_precontrattuali'::text AS test_scope;

-- 0.1: Esiste la utility GAS con id=2
CREATE TEMP TABLE tmp_utility_gas AS
SELECT id AS utility_id
FROM config.utilities
WHERE id = (SELECT utility_id FROM tmp_costanti_idp)
  AND codice_interno = 'GAS';

SELECT is(
    (SELECT count(*)::int FROM tmp_utility_gas),
    1,
    'Esiste esattamente 1 utility GAS con id = 2'
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

-- 0.3: Seleziona una istanza_utility senza record già presente per utility_id=2
CREATE TEMP TABLE tmp_istanza_utility AS
SELECT iu.id AS istanza_utility_id
FROM anagrafiche.istanze_utilities iu
LEFT JOIN anagrafiche.istanze_dati_precontrattuali idp
  ON idp.istanza_utility_id = iu.id
 AND idp.utility_id = (SELECT utility_id FROM tmp_costanti_idp)
WHERE idp.id IS NULL
ORDER BY iu.id
LIMIT 1;

SELECT is(
    (SELECT count(*)::int FROM tmp_istanza_utility),
    1,
    'Esiste almeno una istanza_utility disponibile per utility_id=2'
);

-- Cleanup righe di test precedenti
DELETE FROM anagrafiche.istanze_dati_precontrattuali
WHERE meta ->> 'test_scope' = (SELECT test_scope FROM tmp_costanti_idp);

-- ============================================================
-- 1) Verifica vincoli FK (errori attesi)
-- ============================================================

-- 1.1: utility_id inesistente → FK violation
SELECT throws_ok(
    $$
    INSERT INTO anagrafiche.istanze_dati_precontrattuali (
        istanza_utility_id,
        utility_id,
        classe_utenza_id,
        param_1_num,
        param_2_txt,
        meta
    )
    SELECT
        iu.istanza_utility_id,
        -1,
        cu.classe_utenza_id,
        1.00,
        'TEST-FK-UTILITY',
        jsonb_build_object('test_scope', 'pgtap_istanze_dati_precontrattuali')
    FROM tmp_istanza_utility iu,
         tmp_classe_utenza cu;
    $$,
    '23503',
    NULL,
    'FK violation su utility_id inesistente'
);

-- 1.2: classe_utenza_id inesistente → FK violation
SELECT throws_ok(
    $$
    INSERT INTO anagrafiche.istanze_dati_precontrattuali (
        istanza_utility_id,
        utility_id,
        classe_utenza_id,
        param_1_num,
        param_2_txt,
        meta
    )
    SELECT
        iu.istanza_utility_id,
        k.utility_id,
        -1,
        1.00,
        'TEST-FK-CLASSE',
        jsonb_build_object('test_scope', 'pgtap_istanze_dati_precontrattuali')
    FROM tmp_istanza_utility iu,
         tmp_costanti_idp k;
    $$,
    '23503',
    NULL,
    'FK violation su classe_utenza_id inesistente'
);

-- 1.3: istanza_utility_id inesistente → FK violation
SELECT throws_ok(
    $$
    INSERT INTO anagrafiche.istanze_dati_precontrattuali (
        istanza_utility_id,
        utility_id,
        classe_utenza_id,
        param_1_num,
        param_2_txt,
        meta
    )
    SELECT
        -1,
        k.utility_id,
        cu.classe_utenza_id,
        1.00,
        'TEST-FK-ISTANZA',
        jsonb_build_object('test_scope', 'pgtap_istanze_dati_precontrattuali')
    FROM tmp_costanti_idp k,
         tmp_classe_utenza cu;
    $$,
    '23503',
    NULL,
    'FK violation su istanza_utility_id inesistente'
);

-- ============================================================
-- 2) Inserimento valido
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
        iu.istanza_utility_id,
        k.utility_id,
        cu.classe_utenza_id,
        12.50,
        'TEST-PGTAP',
        jsonb_build_object('test_scope', k.test_scope)
    FROM tmp_istanza_utility iu,
         tmp_costanti_idp k,
         tmp_classe_utenza cu
    RETURNING id
)
SELECT id
FROM ins;

SELECT is(
    (SELECT count(*)::int FROM tmp_idp_test),
    1,
    'Inserita 1 riga valida in istanze_dati_precontrattuali'
);

SELECT ok(
    EXISTS (
        SELECT 1
        FROM anagrafiche.istanze_dati_precontrattuali idp
        JOIN tmp_idp_test t
          ON t.id = idp.id
        WHERE idp.utility_id = (SELECT utility_id FROM tmp_costanti_idp)
          AND idp.classe_utenza_id = (SELECT classe_utenza_id FROM tmp_classe_utenza)
    ),
    'La riga inserita ha FK valide verso utility e classe utenza'
);

-- Cleanup riga di test
/*
DELETE FROM anagrafiche.istanze_dati_precontrattuali
WHERE id IN (SELECT id FROM tmp_idp_test);
*/
-- Fine test
SELECT * FROM finish();
