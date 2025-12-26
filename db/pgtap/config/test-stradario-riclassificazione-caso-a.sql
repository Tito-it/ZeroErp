-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Caso A: cambio nome completo della via (stesso tracciato)
-- Verifica che l'update su config.stradario produca storico
-- ------------------------------------------------------------

SELECT plan(7);

-- =========================================================
-- 1) Stradario di riferimento
-- =========================================================
CREATE TEMP TABLE tmp_stradario_a AS
SELECT id, stradario_generale_id, storicizza
FROM config.stradario
ORDER BY id
LIMIT 1;

SELECT ok(
    (SELECT count(*) FROM tmp_stradario_a) = 1,
    'Esiste almeno un record in config.stradario'
);

-- =========================================================
-- 2) Toponomastica per creare nuova via
-- =========================================================
CREATE TEMP TABLE tmp_toponomastica_a AS
SELECT id
FROM config.toponomastica
ORDER BY id
LIMIT 1;

SELECT ok(
    (SELECT count(*) FROM tmp_toponomastica_a) = 1,
    'Esiste almeno un record in config.toponomastica'
);

-- =========================================================
-- 3) Nuova voce stradario_generale (nuovo nome via)
-- =========================================================
WITH ins AS (
    INSERT INTO config.stradario_generale (
        toponomastica_id,
        descrizione,
        descrizione_breve
    )
    SELECT
        t.id,
        'VIA TEST CASO A ' || to_char(now(), 'YYYYMMDDHH24MISS'),
        'TEST A ' || to_char(now(), 'HH24MISS')
    FROM tmp_toponomastica_a t
    RETURNING id
)
SELECT id
INTO TEMP TABLE tmp_stradario_generale_new
FROM ins;

SELECT ok(
    (SELECT count(*) FROM tmp_stradario_generale_new) = 1,
    'Inserita nuova via in config.stradario_generale'
);

-- =========================================================
-- 4) Abilito storicizza (se necessario)
-- =========================================================
UPDATE config.stradario
SET storicizza = TRUE
WHERE id = (SELECT id FROM tmp_stradario_a);

SELECT is(
    (SELECT storicizza FROM config.stradario WHERE id = (SELECT id FROM tmp_stradario_a)),
    TRUE,
    'Storicizza attivo su config.stradario'
);

-- =========================================================
-- 5) Cambio nome via (update stradario_generale_id)
-- =========================================================
CREATE TEMP TABLE tmp_ts_a AS
SELECT now() AS ts_pre;

UPDATE config.stradario
SET stradario_generale_id = (SELECT id FROM tmp_stradario_generale_new)
WHERE id = (SELECT id FROM tmp_stradario_a);

SELECT is(
    (SELECT stradario_generale_id FROM config.stradario WHERE id = (SELECT id FROM tmp_stradario_a)),
    (SELECT id FROM tmp_stradario_generale_new),
    'Aggiornato stradario_generale_id per il caso A'
);

-- =========================================================
-- 6) Verifica storico: snapshot con vecchio stradario_generale_id
-- =========================================================
SELECT ok(
    EXISTS (
        SELECT 1
        FROM storico.stradario s
        WHERE s.stradario_id = (SELECT id FROM tmp_stradario_a)
          AND s.snapshot ->> 'stradario_generale_id' = (SELECT stradario_generale_id::text FROM tmp_stradario_a)
    ),
    'Storico stradario contiene snapshot con stradario_generale_id precedente'
);

-- =========================================================
-- 7) Verifica fn_get_snapshot_as_of
-- =========================================================
SELECT is(
    (
        script.fn_get_snapshot_as_of(
            'config',
            'stradario',
            (SELECT id::text FROM tmp_stradario_a),
            'stradario_id',
            (SELECT ts_pre FROM tmp_ts_a)
        ) ->> 'stradario_generale_id'
    ),
    (SELECT stradario_generale_id::text FROM tmp_stradario_a),
    'fn_get_snapshot_as_of: ritorna stradario_generale_id precedente'
);

-- =========================================================
-- Cleanup: ripristino e rimuovo la via di test
-- =========================================================
UPDATE config.stradario
SET stradario_generale_id = (SELECT stradario_generale_id FROM tmp_stradario_a),
    storicizza = (SELECT storicizza FROM tmp_stradario_a)
WHERE id = (SELECT id FROM tmp_stradario_a);

DELETE FROM config.stradario_generale
WHERE id = (SELECT id FROM tmp_stradario_generale_new);

SELECT * FROM finish();
