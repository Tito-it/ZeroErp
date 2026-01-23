-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: emittenti fiscali + mapping billing_account + default
--
-- Elenco test:
-- 1) Esiste un gestore con soggetto_id candidabile
-- 2) Esiste un secondo soggetto candidabile
-- 3) Esiste il ruolo EF in config.tipi_ruoli
-- 4) Creato/recuperato ruolo EF per soggetto 1
-- 5) Inserito emittente fiscale 1
-- 6) Esiste esattamente un emittente di default nel mapping
-- 7) Esiste un billing_account senza mapping emittente
-- 8) Fallback funzione emittente (default)
-- 9) Creato/recuperato ruolo EF per soggetto 2
-- 10) Inserito emittente fiscale 2
-- 11) Inserito mapping BA -> emittente (override)
-- 12) Override funzione emittente (mapping BA)
-- 13) Blocco disattivazione emittente con mapping
-- ------------------------------------------------------------

SELECT plan(13);

-- ============================================================
-- 0) Costanti
-- ============================================================
CREATE TEMP TABLE tmp_costanti_ef AS
SELECT
    'pgtap_emittenti_fiscali'::text AS test_scope,
    ('PGTAP-EF-' || to_char(clock_timestamp(), 'YYYYMMDDHH24MISSMS'))::text AS codice_ef1,
    ('PGTAP-EF2-' || to_char(clock_timestamp(), 'YYYYMMDDHH24MISSMS'))::text AS codice_ef2;

-- ============================================================
-- 1) Candidato: gestore senza emittente fiscale
-- ============================================================
CREATE TEMP TABLE tmp_soggetto_1 AS
SELECT s.id AS soggetto_id
FROM anagrafiche.gestori g
JOIN anagrafiche.soggetti_ruoli sr_g ON sr_g.id = g.soggetto_ruolo_id
JOIN anagrafiche.soggetti s ON s.id = sr_g.soggetto_id
WHERE NOT EXISTS (
    SELECT 1
    FROM anagrafiche.soggetti_ruoli sr_ef
    JOIN config.tipi_ruoli tr
      ON tr.id = sr_ef.tipo_ruolo_id
     AND tr.codice_interno = 'EF'
    JOIN anagrafiche.emittenti_fiscali ef
      ON ef.soggetto_ruolo_id = sr_ef.id
    WHERE sr_ef.soggetto_id = s.id
)
LIMIT 1;

SELECT ok(
    (SELECT count(*) FROM tmp_soggetto_1) = 1,
    'Esiste un gestore con soggetto_id candidabile'
);

-- ============================================================
-- 2) Secondo soggetto candidabile
-- ============================================================
CREATE TEMP TABLE tmp_soggetto_2 AS
SELECT s.id AS soggetto_id
FROM anagrafiche.soggetti s
WHERE s.id <> (SELECT soggetto_id FROM tmp_soggetto_1)
  AND NOT EXISTS (
    SELECT 1
    FROM anagrafiche.soggetti_ruoli sr_ef
    JOIN config.tipi_ruoli tr
      ON tr.id = sr_ef.tipo_ruolo_id
     AND tr.codice_interno = 'EF'
    JOIN anagrafiche.emittenti_fiscali ef
      ON ef.soggetto_ruolo_id = sr_ef.id
    WHERE sr_ef.soggetto_id = s.id
)
LIMIT 1;

SELECT ok(
    (SELECT count(*) FROM tmp_soggetto_2) = 1,
    'Esiste un secondo soggetto candidabile'
);

-- ============================================================
-- 3) Ruolo EF presente
-- ============================================================
CREATE TEMP TABLE tmp_ruolo_ef AS
SELECT id AS tipo_ruolo_id
FROM config.tipi_ruoli
WHERE codice_interno = 'EF';

SELECT ok(
    (SELECT count(*) FROM tmp_ruolo_ef) = 1,
    'Esiste il ruolo EF in config.tipi_ruoli'
);

-- ============================================================
-- 4) Ruolo EF per soggetto 1
-- ============================================================
CREATE TEMP TABLE tmp_ef_role_1 AS
SELECT
    script.fn_get_or_create_soggetto_ruolo(
        p_soggetto_id  := (SELECT soggetto_id FROM tmp_soggetto_1),
        p_cd_int_ruolo := 'EF'
    ) AS soggetto_ruolo_id;

SELECT ok(
    (SELECT soggetto_ruolo_id FROM tmp_ef_role_1) IS NOT NULL,
    'Creato/recuperato ruolo EF per soggetto 1'
);

-- ============================================================
-- 5) Inserimento emittente fiscale 1
-- ============================================================
CREATE TEMP TABLE tmp_emittente_1 AS
WITH ins AS (
    INSERT INTO anagrafiche.emittenti_fiscali (
        soggetto_ruolo_id,
        codice,
        descrizione,
        brand_meta
    )
    SELECT
        r.soggetto_ruolo_id,
        k.codice_ef1,
        'Emittente fiscale test 1',
        jsonb_build_object('test_scope', k.test_scope)
    FROM tmp_ef_role_1 r,
         tmp_costanti_ef k
    RETURNING id
)
SELECT id FROM ins;

SELECT is(
    (SELECT count(*)::int FROM tmp_emittente_1),
    1,
    'Inserito emittente fiscale 1'
);

-- ============================================================
-- 6) Verifica default mapping (1 solo)
-- ============================================================
SELECT is(
    (SELECT count(*)::int
       FROM anagrafiche.emittenti_fiscali_billing_account
      WHERE is_default = true),
    1,
    'Esiste esattamente un emittente di default nel mapping'
);

-- ============================================================
-- 7) Billing account senza mapping
-- ============================================================
CREATE TEMP TABLE tmp_ba_no_map AS
SELECT ba.id AS billing_account_id
FROM anagrafiche.billing_account ba
WHERE NOT EXISTS (
    SELECT 1
    FROM anagrafiche.emittenti_fiscali_billing_account m
    WHERE m.billing_account_id = ba.id
)
LIMIT 1;

SELECT ok(
    (SELECT count(*) FROM tmp_ba_no_map) = 1,
    'Esiste un billing_account senza mapping emittente'
);

-- ============================================================
-- 8) Fallback funzione emittente (default)
-- ============================================================
SELECT is(
    anagrafiche.fn_get_emittente_fiscale_id((SELECT billing_account_id FROM tmp_ba_no_map)),
    (SELECT soggetto_ruolo_id::bigint FROM tmp_ef_role_1),
    'Fallback funzione emittente (default)'
);

-- ============================================================
-- 9) Ruolo EF per soggetto 2
-- ============================================================
CREATE TEMP TABLE tmp_ef_role_2 AS
SELECT
    script.fn_get_or_create_soggetto_ruolo(
        p_soggetto_id  := (SELECT soggetto_id FROM tmp_soggetto_2),
        p_cd_int_ruolo := 'EF'
    ) AS soggetto_ruolo_id;

SELECT ok(
    (SELECT soggetto_ruolo_id FROM tmp_ef_role_2) IS NOT NULL,
    'Creato/recuperato ruolo EF per soggetto 2'
);

-- ============================================================
-- 10) Inserimento emittente fiscale 2
-- ============================================================
CREATE TEMP TABLE tmp_emittente_2 AS
WITH ins AS (
    INSERT INTO anagrafiche.emittenti_fiscali (
        soggetto_ruolo_id,
        codice,
        descrizione,
        brand_meta
    )
    SELECT
        r.soggetto_ruolo_id,
        k.codice_ef2,
        'Emittente fiscale test 2',
        jsonb_build_object('test_scope', k.test_scope)
    FROM tmp_ef_role_2 r,
         tmp_costanti_ef k
    RETURNING id
)
SELECT id FROM ins;

SELECT is(
    (SELECT count(*)::int FROM tmp_emittente_2),
    1,
    'Inserito emittente fiscale 2'
);

-- ============================================================
-- 11) Inserimento mapping BA -> emittente (override)
-- ============================================================
CREATE TEMP TABLE tmp_map_ba AS
WITH ins AS (
    INSERT INTO anagrafiche.emittenti_fiscali_billing_account (
        billing_account_id,
        emittente_soggetto_ruolo_id,
        is_default,
        meta
    )
    SELECT
        b.billing_account_id,
        r.soggetto_ruolo_id,
        false,
        jsonb_build_object('test_scope', k.test_scope)
    FROM tmp_ba_no_map b,
         tmp_ef_role_2 r,
         tmp_costanti_ef k
    RETURNING id
)
SELECT id FROM ins;

SELECT is(
    (SELECT count(*)::int FROM tmp_map_ba),
    1,
    'Inserito mapping BA -> emittente (override)'
);

-- ============================================================
-- 12) Verifica override funzione emittente
-- ============================================================
SELECT is(
    anagrafiche.fn_get_emittente_fiscale_id((SELECT billing_account_id FROM tmp_ba_no_map)),
    (SELECT soggetto_ruolo_id::bigint FROM tmp_ef_role_2),
    'Override funzione emittente (mapping BA)'
);

-- ============================================================
-- 13) Blocco disattivazione emittente con mapping
-- ============================================================
SELECT throws_ok(
    $$
    UPDATE anagrafiche.emittenti_fiscali
    SET attivo = false
    WHERE id = (SELECT id FROM tmp_emittente_2);
    $$,
    'P0001',
    NULL,
    'Blocco disattivazione emittente con mapping BA'
);

-- Cleanup
SELECT set_config('zeroerp.maintenance_ruoli_delete', 'on', false);


DELETE FROM anagrafiche.emittenti_fiscali_billing_account
WHERE meta ->> 'test_scope' = (SELECT test_scope FROM tmp_costanti_ef);
DELETE FROM anagrafiche.emittenti_fiscali
WHERE brand_meta ->> 'test_scope' = (SELECT test_scope FROM tmp_costanti_ef);

DELETE FROM anagrafiche.soggetti_ruoli sr
WHERE sr.id IN (
    (SELECT soggetto_ruolo_id FROM tmp_ef_role_1),
    (SELECT soggetto_ruolo_id FROM tmp_ef_role_2)
)
  AND NOT EXISTS (
    SELECT 1
    FROM anagrafiche.emittenti_fiscali ef
    WHERE ef.soggetto_ruolo_id = sr.id
  )
  AND NOT EXISTS (
    SELECT 1
    FROM anagrafiche.emittenti_fiscali_billing_account m
    WHERE m.emittente_soggetto_ruolo_id = sr.id
  );


DELETE FROM anagrafiche.emittenti_fiscali_billing_account m
USING anagrafiche.emittenti_fiscali ef
WHERE m.is_default = true
  AND m.emittente_soggetto_ruolo_id = ef.soggetto_ruolo_id
  AND ef.brand_meta ->> 'test_scope' = (SELECT test_scope FROM tmp_costanti_ef);
