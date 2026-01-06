-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test risorse_umane_auth_user:
--   - blocco collegamento auth_user per risorse non gestore
-- ------------------------------------------------------------

SELECT plan(8);

-- =========================================================
-- 1) Precondizione: esiste la qualifica DIPENDENTE
-- =========================================================
CREATE TEMP TABLE tmp_qualifica_test AS
SELECT id AS qualifica_id
FROM config.qualifiche
WHERE codice_interno = 'DIPENDENTE'
LIMIT 1;

SELECT ok(
    (SELECT count(*) FROM tmp_qualifica_test) = 1,
    'Esiste la qualifica DIPENDENTE in config.qualifiche'
);

-- =========================================================
-- 2) Recupero soggetto per partita_iva = 29878230910
-- =========================================================
CREATE TEMP TABLE tmp_soggetto_test AS
SELECT id
FROM anagrafiche.soggetti
WHERE partita_iva = '29878230910';

SELECT ok(
    (SELECT count(*) FROM tmp_soggetto_test) = 1,
    'Trovato soggetto con partita_iva = 29878230910'
);

-- =========================================================
-- 3) Ruolo RIS_UMANA + risorsa umana (non gestore)
-- =========================================================
CREATE TEMP TABLE tmp_soggetto_ruolo_test AS
SELECT script.fn_get_or_create_soggetto_ruolo(
    p_soggetto_id  := (SELECT id FROM tmp_soggetto_test),
    p_cd_int_ruolo := 'RIS_UMANA'
) AS soggetto_ruolo_id;

WITH ins AS (
    INSERT INTO anagrafiche.risorse_umane (
        soggetto_ruolo_id,
        soggetto_id,
        qualifica_id,
        valido_dal
    )
    SELECT
        sr.soggetto_ruolo_id,
        s.id,
        q.qualifica_id,
        CURRENT_DATE
    FROM tmp_soggetto_test s,
         tmp_soggetto_ruolo_test sr,
         tmp_qualifica_test q
    WHERE NOT EXISTS (
        SELECT 1
        FROM anagrafiche.risorse_umane ru
        WHERE ru.soggetto_ruolo_id = sr.soggetto_ruolo_id
    )
    RETURNING id
)
SELECT COALESCE(
    (SELECT id FROM ins),
    (
        SELECT ru.id
        FROM anagrafiche.risorse_umane ru
        JOIN tmp_soggetto_ruolo_test sr
          ON ru.soggetto_ruolo_id = sr.soggetto_ruolo_id
    )
)
INTO TEMP TABLE tmp_risorsa_umana_test;

SELECT ok(
    (SELECT count(*) FROM tmp_risorsa_umana_test) = 1,
    'Recuperata o inserita risorsa umana non gestore'
);

-- =========================================================
-- 4) Guard: auth_user ammesso solo per risorse del gestore
-- =========================================================
SELECT throws_ok(
    $$
    INSERT INTO anagrafiche.risorse_umane_auth_user (
        risorsa_umana_id,
        auth_user_id,
        attivo
    )
    VALUES (
        (SELECT id FROM tmp_risorsa_umana_test),
        1,
        TRUE
    );
    $$,
    NULL,
    NULL,
    'Guard: risorsa non gestore non puo'' essere collegata a auth_user'
);

-- =========================================================
-- 5) Recupero soggetto gestore per test positivo
-- =========================================================
CREATE TEMP TABLE tmp_soggetto_gestore AS
SELECT sr.soggetto_id
FROM anagrafiche.gestori g
JOIN anagrafiche.soggetti_ruoli sr
  ON sr.id = g.soggetto_ruolo_id
ORDER BY sr.soggetto_id
LIMIT 1;

SELECT ok(
    (SELECT count(*) FROM tmp_soggetto_gestore) = 1,
    'Trovato soggetto gestore per test positivo'
);

-- =========================================================
-- 6) Recupero auth_user disponibile
-- =========================================================
CREATE TEMP TABLE tmp_auth_user AS
SELECT au.id AS auth_user_id
FROM django.auth_user au
LEFT JOIN anagrafiche.risorse_umane_auth_user rau
  ON rau.auth_user_id = au.id
WHERE rau.id IS NULL
ORDER BY au.id
LIMIT 1;

SELECT ok(
    (SELECT count(*) FROM tmp_auth_user) = 1,
    'Trovato auth_user disponibile per collegamento'
);

-- =========================================================
-- 7) Collegamento positivo per risorsa del gestore
-- =========================================================
CREATE TEMP TABLE tmp_soggetto_ruolo_gestore AS
SELECT script.fn_get_or_create_soggetto_ruolo(
    p_soggetto_id  := (SELECT soggetto_id FROM tmp_soggetto_gestore),
    p_cd_int_ruolo := 'RIS_UMANA'
) AS soggetto_ruolo_id;

WITH ins AS (
    INSERT INTO anagrafiche.risorse_umane (
        soggetto_ruolo_id,
        soggetto_id,
        qualifica_id,
        valido_dal
    )
    SELECT
        sr.soggetto_ruolo_id,
        s.soggetto_id,
        q.qualifica_id,
        CURRENT_DATE
    FROM tmp_soggetto_gestore s,
         tmp_soggetto_ruolo_gestore sr,
         tmp_qualifica_test q
    WHERE NOT EXISTS (
        SELECT 1
        FROM anagrafiche.risorse_umane ru
        WHERE ru.soggetto_ruolo_id = sr.soggetto_ruolo_id
    )
    RETURNING id
)
SELECT COALESCE(
    (SELECT id FROM ins),
    (
        SELECT ru.id
        FROM anagrafiche.risorse_umane ru
        JOIN tmp_soggetto_ruolo_gestore sr
          ON ru.soggetto_ruolo_id = sr.soggetto_ruolo_id
    )
) AS id
INTO TEMP TABLE tmp_risorsa_umana_gestore;

SELECT ok(
    (SELECT count(*) FROM tmp_risorsa_umana_gestore) = 1,
    'Recuperata o inserita risorsa umana del gestore'
);

INSERT INTO anagrafiche.risorse_umane_auth_user (
    risorsa_umana_id,
    auth_user_id,
    attivo
)
SELECT
    ru.id,
    au.auth_user_id,
    TRUE
FROM tmp_risorsa_umana_gestore ru,
     tmp_auth_user au;

SELECT ok(
    (
        SELECT count(*)
        FROM anagrafiche.risorse_umane_auth_user rau
        WHERE rau.risorsa_umana_id = (SELECT id FROM tmp_risorsa_umana_gestore)
          AND rau.auth_user_id = (SELECT auth_user_id FROM tmp_auth_user)
    ) = 1,
    'Collegamento auth_user riuscito per risorsa del gestore'
);

SELECT * FROM finish();
