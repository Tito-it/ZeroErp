-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Toponomastica + stradario_generale (normalizzazione + guard)
-- ------------------------------------------------------------

SELECT plan(6);

-- =========================================================
-- 1) Crea due toponimi di test
-- =========================================================
WITH ins AS (
    INSERT INTO config.toponomastica (descrizione, stato_id, attivo)
    VALUES
        ('TOPO TEST 1 ' || to_char(clock_timestamp(), 'YYYYMMDDHH24MISS'), NULL, true),
        ('TOPO TEST 2 ' || to_char(clock_timestamp(), 'YYYYMMDDHH24MISS'), NULL, true)
    RETURNING id, descrizione
), labeled AS (
    SELECT
        id,
        descrizione,
        CASE
            WHEN descrizione LIKE 'TOPO TEST 1 %' THEN 't1'
            ELSE 't2'
        END AS label
    FROM ins
)
SELECT *
INTO TEMP TABLE tmp_topo
FROM labeled;

SELECT ok(
    (SELECT count(*) FROM tmp_topo) = 2,
    'Creati due toponimi di test'
);

-- =========================================================
-- 2) Crea stradario_generale collegati al topo 1
-- =========================================================
WITH ins AS (
    INSERT INTO config.stradario_generale (
        toponomastica_id,
        descrizione,
        descrizione_breve
    )
    SELECT id, 'STRADARIO TEST 1', 'S1'
    FROM tmp_topo WHERE label = 't1'
    UNION ALL
    SELECT id, 'STRADARIO TEST 2', 'S2'
    FROM tmp_topo WHERE label = 't1'
    UNION ALL
    SELECT id, 'STRADARIO TEST 3', 'S3'
    FROM tmp_topo WHERE label = 't1'
    RETURNING id, toponomastica_id, descrizione, indirizzo_normalizzato
)
SELECT *
INTO TEMP TABLE tmp_stradario_gen
FROM ins;

SELECT ok(
    EXISTS (
        SELECT 1
        FROM tmp_stradario_gen sg
        JOIN tmp_topo t ON t.id = sg.toponomastica_id
        WHERE sg.indirizzo_normalizzato ILIKE '%' || t.descrizione || '%'
    ),
    'indirizzo_normalizzato include il toponimo'
);

-- =========================================================
-- 3) Guard update toponomastica in uso
-- =========================================================
SELECT throws_ok(
    $$
    UPDATE config.toponomastica
    SET descrizione = descrizione || ' MOD'
    WHERE id = (SELECT id FROM tmp_topo WHERE label = 't1');
    $$,
    NULL,
    NULL,
    'Modifica toponimo in uso bloccata'
);

-- =========================================================
-- 4) Disattivo toponomastica in uso -> errore
-- =========================================================
SELECT throws_ok(
    $$
    UPDATE config.toponomastica
    SET attivo = false
    WHERE id = (SELECT id FROM tmp_topo WHERE label = 't1');
    $$,
    NULL,
    NULL,
    'Disattivazione toponimo in uso bloccata'
);

-- =========================================================
-- 5) Disattivo toponomastica non in uso -> ok
-- =========================================================
SELECT lives_ok(
    $$
    UPDATE config.toponomastica
    SET attivo = false
    WHERE id = (SELECT id FROM tmp_topo WHERE label = 't2');
    $$,
    'Disattivazione toponimo non in uso consentita'
);

-- =========================================================
-- 6) Cambio toponomastica_id e rinormalizzazione
-- =========================================================
UPDATE config.stradario_generale
SET toponomastica_id = (SELECT id FROM tmp_topo WHERE label = 't2')
WHERE id = (SELECT id FROM tmp_stradario_gen ORDER BY id LIMIT 1);

SELECT ok(
    EXISTS (
        SELECT 1
        FROM config.stradario_generale sg
        JOIN tmp_topo t2 ON t2.id = sg.toponomastica_id AND t2.label = 't2'
        WHERE sg.id = (SELECT id FROM tmp_stradario_gen ORDER BY id LIMIT 1)
          AND sg.indirizzo_normalizzato ILIKE '%' || t2.descrizione || '%'
    ),
    'Rinormalizzazione su cambio toponomastica_id'
);

-- =========================================================
-- Cleanup
-- =========================================================
DELETE FROM config.stradario_generale
WHERE id IN (SELECT id FROM tmp_stradario_gen);

DELETE FROM config.toponomastica
WHERE id IN (SELECT id FROM tmp_topo);

SELECT * FROM finish();
