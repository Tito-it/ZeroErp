-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: emittenti fiscali + mapping billing_account + default
--
-- Elenco test:
-- 1) Setup minimo PG/utility disponibile
-- 2) Creato soggetto PG 1 di supporto
-- 3) Creato soggetto PG 2 di supporto
-- 4) Esiste il ruolo EF in config.tipi_ruoli
-- 5) Creato/recuperato ruolo EF per soggetto 1
-- 6) Inserito emittente fiscale 1 con matrice utility
-- 7) Esiste esattamente un emittente di default nel mapping
-- 8) Esiste un billing_account senza mapping emittente
-- 9) Fallback funzione emittente (default)
-- 10) Creato/recuperato ruolo EF per soggetto 2
-- 11) Inserito emittente fiscale 2 con matrice utility
-- 12) Inserito mapping BA -> emittente (override)
-- 13) Override funzione emittente (mapping BA)
-- 14) Blocco disattivazione emittente con mapping
-- 15) Blocco cancellazione ultima utility attiva dell'emittente
-- ------------------------------------------------------------

BEGIN;

SELECT plan(15);

-- ============================================================
-- 0) Costanti
-- ============================================================
CREATE TEMP TABLE tmp_costanti_ef AS
WITH stamp AS (
    SELECT to_char(clock_timestamp(), 'YYYYMMDDHH24MISSMS') AS ts
),
semi AS (
    SELECT
        ts,
        right(ts, 10) AS seed_1,
        lpad((((right(ts, 10))::numeric + 1) % 10000000000)::text, 10, '0') AS seed_2
    FROM stamp
),
validi AS (
    SELECT
        ts,
        seed_1 ||
        (
            (
                10 - (
                    SELECT SUM(
                        CASE
                            WHEN gs.i % 2 = 0 THEN
                                CASE
                                    WHEN ((substr(seed_1, gs.i, 1))::int * 2) > 9
                                        THEN ((substr(seed_1, gs.i, 1))::int * 2) - 9
                                    ELSE ((substr(seed_1, gs.i, 1))::int * 2)
                                END
                            ELSE (substr(seed_1, gs.i, 1))::int
                        END
                    )
                    FROM generate_series(1, 10) AS gs(i)
                ) % 10
            ) % 10
        )::text AS cf_piva_1,
        seed_2 ||
        (
            (
                10 - (
                    SELECT SUM(
                        CASE
                            WHEN gs.i % 2 = 0 THEN
                                CASE
                                    WHEN ((substr(seed_2, gs.i, 1))::int * 2) > 9
                                        THEN ((substr(seed_2, gs.i, 1))::int * 2) - 9
                                    ELSE ((substr(seed_2, gs.i, 1))::int * 2)
                                END
                            ELSE (substr(seed_2, gs.i, 1))::int
                        END
                    )
                    FROM generate_series(1, 10) AS gs(i)
                ) % 10
            ) % 10
        )::text AS cf_piva_2
    FROM semi
)
SELECT
    'pgtap_emittenti_fiscali'::text AS test_scope,
    ('PGTAP-EF-' || v.ts)::text AS codice_ef1,
    ('PGTAP-EF2-' || v.ts)::text AS codice_ef2,
    v.cf_piva_1,
    v.cf_piva_2,
    ('ef1_' || v.ts || '@test.local')::text AS email_1,
    ('ef2_' || v.ts || '@test.local')::text AS email_2,
    ('A' || right(v.ts, 6))::text AS rea_1,
    ('B' || right(v.ts, 6))::text AS rea_2,
    ('SDI' || right(v.ts, 4))::text AS sdi_1,
    ('SDJ' || right(v.ts, 4))::text AS sdi_2
FROM validi v;

-- ============================================================
-- 1) Setup minimo autosufficiente per creare soggetti PG candidabili a EF
-- ============================================================
CREATE TEMP TABLE tmp_setup_ef AS
SELECT
    tsd.id AS tipo_soggetto_dettaglio_id,
    COALESCE(
        (
            SELECT fgtsd.forma_giuridica_id
            FROM config.forme_giuridiche_tipi_soggetto_dettaglio fgtsd
            WHERE fgtsd.tipo_soggetto_dettaglio_id = tsd.id
              AND fgtsd.attivo = true
              AND (fgtsd.valido_dal IS NULL OR fgtsd.valido_dal <= CURRENT_DATE)
              AND (fgtsd.valido_al IS NULL OR fgtsd.valido_al >= CURRENT_DATE)
            ORDER BY fgtsd.forma_giuridica_id
            LIMIT 1
        ),
        (SELECT fg.id FROM config.forme_giuridiche fg ORDER BY fg.id LIMIT 1)
    ) AS forma_giuridica_id,
    (SELECT p.id FROM config.province p ORDER BY p.id LIMIT 1) AS provincia_id,
    (SELECT s.id FROM config.stradario s ORDER BY s.id LIMIT 1) AS stradario_id,
    COALESCE(
        (
            SELECT utr.utility_id
            FROM config.utilities_tipi_ruolo utr
            JOIN config.tipi_ruoli tr
              ON tr.id = utr.tipo_ruolo_id
             AND tr.codice_interno = 'EF'
            WHERE utr.attivo = true
              AND (utr.valido_dal IS NULL OR utr.valido_dal <= CURRENT_DATE)
              AND (utr.valido_al IS NULL OR utr.valido_al >= CURRENT_DATE)
            ORDER BY utr.utility_id
            LIMIT 1
        ),
        (SELECT u.id FROM config.utilities u ORDER BY u.id LIMIT 1)
    ) AS utility_id
FROM config.tipi_soggetto_dettaglio tsd
WHERE tsd.tipo_soggetto_id = 'PG'
  AND tsd.stato_iso2 = 'IT'
  AND tsd.formato_cf = 'NUM_11'
  AND tsd.formato_piva = 'NUM_11'
ORDER BY
    CASE WHEN tsd.dati_societari_policy = 'REQUIRED' THEN 0 ELSE 1 END,
    tsd.id
LIMIT 1;

SELECT ok(
    (SELECT tipo_soggetto_dettaglio_id IS NOT NULL
         AND forma_giuridica_id IS NOT NULL
         AND provincia_id IS NOT NULL
         AND stradario_id IS NOT NULL
         AND utility_id IS NOT NULL
     FROM tmp_setup_ef),
    'Setup minimo PG/utility disponibile'
);

-- ============================================================
-- 2) Crea soggetto PG 1 di supporto
-- ============================================================
CREATE TEMP TABLE tmp_soggetto_1 AS
WITH sogg AS (
    SELECT anagrafiche.fn_crea_soggetto_pg(
        p_ragione_sociale := 'PGTAP Emittente Soggetto 1',
        p_tipo_soggetto_dettaglio_id := (SELECT tipo_soggetto_dettaglio_id FROM tmp_setup_ef),
        p_email := (SELECT email_1 FROM tmp_costanti_ef),
        p_codice_fiscale := (SELECT cf_piva_1 FROM tmp_costanti_ef),
        p_partita_iva := (SELECT cf_piva_1 FROM tmp_costanti_ef),
        p_forma_giuridica_id := (SELECT forma_giuridica_id FROM tmp_setup_ef),
        p_id_prov_iscri_rea := (SELECT provincia_id FROM tmp_setup_ef),
        p_iscrizione_rea := (SELECT rea_1 FROM tmp_costanti_ef),
        p_capitale_sociale := 10000.00,
        p_destinatario_fe := 'C',
        p_codice_sdi := (SELECT sdi_1 FROM tmp_costanti_ef)
    ) AS soggetto_id
),
ind_det AS (
    SELECT anagrafiche.fn_get_or_create_indirizzo_dettaglio(
        p_stradario_id := (SELECT stradario_id FROM tmp_setup_ef),
        p_civico := 9001
    ) AS indirizzo_dettaglio_id
),
indirizzi AS (
    SELECT anagrafiche.fn_crea_indirizzo_soggetto(
        p_soggetto_id := s.soggetto_id,
        p_tipo_indirizzo_codice := ti.codice_interno,
        p_indirizzo_dettaglio_id := d.indirizzo_dettaglio_id
    )
    FROM sogg s
    CROSS JOIN ind_det d
    JOIN config.tipi_soggetto_dettaglio_tipi_indirizzo m
      ON m.tipo_soggetto_dettaglio_id = (SELECT tipo_soggetto_dettaglio_id FROM tmp_setup_ef)
    JOIN config.tipi_indirizzi ti
      ON ti.id = m.tipo_indirizzo_id
    WHERE m.obbligatorio = true
      AND m.attivo = true
      AND (m.valido_dal IS NULL OR m.valido_dal <= CURRENT_DATE)
      AND (m.valido_al IS NULL OR m.valido_al >= CURRENT_DATE)
)
SELECT soggetto_id FROM sogg;

SELECT ok(
    (SELECT soggetto_id IS NOT NULL FROM tmp_soggetto_1),
    'Creato soggetto PG 1 di supporto'
);

-- ============================================================
-- 3) Crea soggetto PG 2 di supporto
-- ============================================================
CREATE TEMP TABLE tmp_soggetto_2 AS
WITH sogg AS (
    SELECT anagrafiche.fn_crea_soggetto_pg(
        p_ragione_sociale := 'PGTAP Emittente Soggetto 2',
        p_tipo_soggetto_dettaglio_id := (SELECT tipo_soggetto_dettaglio_id FROM tmp_setup_ef),
        p_email := (SELECT email_2 FROM tmp_costanti_ef),
        p_codice_fiscale := (SELECT cf_piva_2 FROM tmp_costanti_ef),
        p_partita_iva := (SELECT cf_piva_2 FROM tmp_costanti_ef),
        p_forma_giuridica_id := (SELECT forma_giuridica_id FROM tmp_setup_ef),
        p_id_prov_iscri_rea := (SELECT provincia_id FROM tmp_setup_ef),
        p_iscrizione_rea := (SELECT rea_2 FROM tmp_costanti_ef),
        p_capitale_sociale := 20000.00,
        p_destinatario_fe := 'C',
        p_codice_sdi := (SELECT sdi_2 FROM tmp_costanti_ef)
    ) AS soggetto_id
),
ind_det AS (
    SELECT anagrafiche.fn_get_or_create_indirizzo_dettaglio(
        p_stradario_id := (SELECT stradario_id FROM tmp_setup_ef),
        p_civico := 9002
    ) AS indirizzo_dettaglio_id
),
indirizzi AS (
    SELECT anagrafiche.fn_crea_indirizzo_soggetto(
        p_soggetto_id := s.soggetto_id,
        p_tipo_indirizzo_codice := ti.codice_interno,
        p_indirizzo_dettaglio_id := d.indirizzo_dettaglio_id
    )
    FROM sogg s
    CROSS JOIN ind_det d
    JOIN config.tipi_soggetto_dettaglio_tipi_indirizzo m
      ON m.tipo_soggetto_dettaglio_id = (SELECT tipo_soggetto_dettaglio_id FROM tmp_setup_ef)
    JOIN config.tipi_indirizzi ti
      ON ti.id = m.tipo_indirizzo_id
    WHERE m.obbligatorio = true
      AND m.attivo = true
      AND (m.valido_dal IS NULL OR m.valido_dal <= CURRENT_DATE)
      AND (m.valido_al IS NULL OR m.valido_al >= CURRENT_DATE)
)
SELECT soggetto_id FROM sogg;

SELECT ok(
    (SELECT soggetto_id IS NOT NULL FROM tmp_soggetto_2),
    'Creato soggetto PG 2 di supporto'
);

-- ============================================================
-- 4) Ruolo EF presente
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
-- Setup tecnico: abilita la utility di test per il ruolo EF
-- nella transazione corrente se la matrice non la prevede gia'
-- ============================================================
INSERT INTO config.utilities_tipi_ruolo (
    utility_id,
    tipo_ruolo_id,
    attivo,
    valido_dal,
    meta
)
SELECT
    s.utility_id,
    r.tipo_ruolo_id,
    true,
    CURRENT_DATE,
    jsonb_build_object('test_scope', k.test_scope)
FROM tmp_setup_ef s,
     tmp_ruolo_ef r,
     tmp_costanti_ef k
WHERE s.utility_id IS NOT NULL
  AND NOT EXISTS (
      SELECT 1
      FROM config.utilities_tipi_ruolo utr
      WHERE utr.utility_id = s.utility_id
        AND utr.tipo_ruolo_id = r.tipo_ruolo_id
  );

-- ============================================================
-- 5) Ruolo EF per soggetto 1
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
-- 6) Inserimento emittente fiscale 1 + matrice utility
-- ============================================================
CREATE TEMP TABLE tmp_emittente_1 AS
WITH ins_emittente AS (
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
    RETURNING id, soggetto_ruolo_id
),
ins_utility AS (
    INSERT INTO anagrafiche.emittenti_fiscali_utilities (
        emittente_soggetto_ruolo_id,
        utility_id,
        arrotondamento_importi_dec,
        metodo_arrotondamento_importi,
        meta
    )
    SELECT
        e.soggetto_ruolo_id,
        u.utility_id,
        2,
        'HALF_UP',
        jsonb_build_object('test_scope', k.test_scope)
    FROM ins_emittente e,
         tmp_setup_ef u,
         tmp_costanti_ef k
    RETURNING id
)
SELECT id FROM ins_emittente;

SELECT is(
    (SELECT count(*)::int FROM tmp_emittente_1),
    1,
    'Inserito emittente fiscale 1 con matrice utility'
);

-- ============================================================
-- 7) Verifica default mapping (1 solo)
-- ============================================================
SELECT is(
    (SELECT count(*)::int
       FROM anagrafiche.emittenti_fiscali_billing_account
      WHERE is_default = true),
    1,
    'Esiste esattamente un emittente di default nel mapping'
);

-- ============================================================
-- 8) Billing account senza mapping
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

CREATE TEMP TABLE tmp_emittente_default AS
SELECT m.emittente_soggetto_ruolo_id
FROM anagrafiche.emittenti_fiscali_billing_account m
WHERE m.is_default = true
  AND m.billing_account_id IS NULL
LIMIT 1;

-- ============================================================
-- 9) Fallback funzione emittente (default)
-- ============================================================
SELECT is(
    anagrafiche.fn_get_emittente_fiscale_id((SELECT billing_account_id FROM tmp_ba_no_map)),
    (SELECT emittente_soggetto_ruolo_id::bigint FROM tmp_emittente_default),
    'Fallback funzione emittente (default)'
);

-- ============================================================
-- 10) Ruolo EF per soggetto 2
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
-- 11) Inserimento emittente fiscale 2 + matrice utility
-- ============================================================
CREATE TEMP TABLE tmp_emittente_2 AS
WITH ins_emittente AS (
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
    RETURNING id, soggetto_ruolo_id
),
ins_utility AS (
    INSERT INTO anagrafiche.emittenti_fiscali_utilities (
        emittente_soggetto_ruolo_id,
        utility_id,
        arrotondamento_importi_dec,
        metodo_arrotondamento_importi,
        meta
    )
    SELECT
        e.soggetto_ruolo_id,
        u.utility_id,
        2,
        'HALF_UP',
        jsonb_build_object('test_scope', k.test_scope)
    FROM ins_emittente e,
         tmp_setup_ef u,
         tmp_costanti_ef k
    RETURNING id
)
SELECT id FROM ins_emittente;

SELECT is(
    (SELECT count(*)::int FROM tmp_emittente_2),
    1,
    'Inserito emittente fiscale 2 con matrice utility'
);

-- ============================================================
-- 12) Inserimento mapping BA -> emittente (override)
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
-- 13) Verifica override funzione emittente
-- ============================================================
SELECT is(
    anagrafiche.fn_get_emittente_fiscale_id((SELECT billing_account_id FROM tmp_ba_no_map)),
    (SELECT soggetto_ruolo_id::bigint FROM tmp_ef_role_2),
    'Override funzione emittente (mapping BA)'
);

-- ============================================================
-- 14) Blocco disattivazione emittente con mapping
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

-- ============================================================
-- 15) Blocco cancellazione ultima utility attiva dell'emittente
-- ============================================================
SELECT throws_ok(
    format(
        'DELETE FROM anagrafiche.emittenti_fiscali_utilities
          WHERE emittente_soggetto_ruolo_id = %s
            AND meta ->> ''test_scope'' = %L;
         SET CONSTRAINTS ALL IMMEDIATE;',
        (SELECT soggetto_ruolo_id FROM tmp_ef_role_2),
        (SELECT test_scope FROM tmp_costanti_ef)
    ),
    'P0001',
    NULL,
    'Blocco cancellazione ultima utility attiva dell''emittente'
);

SELECT * FROM finish();
ROLLBACK;
