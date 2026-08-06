-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Toponomastica + stradario_generale (normalizzazione + guard)
-- ------------------------------------------------------------

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
-- ⚠️ Questo file non apre una transazione propria: la riga va prima di plan().
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(11);

-- =========================================================
-- 1) Crea due toponimi di test
-- =========================================================
CREATE TEMP TABLE tmp_def_param AS
SELECT script.fn_get_default_by_param(
    'config',
    'stati',
    'codice_iso3',
    'state_code_iso3',
    'test_toponomastica'
)::integer AS stato_id;

CREATE TEMP TABLE tmp_topo_norm_impl AS
SELECT EXISTS (
    SELECT 1
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'config'
      AND p.proname = 'trgfn_toponomastica_normalize'
      AND p.prosrc ILIKE '%fn_get_default_by_param%'
) AS has_default;

WITH def_stato AS (
    SELECT id
    FROM config.stati
    ORDER BY id
    LIMIT 1
), ins AS (
    INSERT INTO config.toponomastica (descrizione, stato_id, attivo)
    VALUES
        ('TOPO TEST 1 ' || to_char(clock_timestamp(), 'YYYYMMDDHH24MISS'), (SELECT id FROM def_stato), true),
        ('TOPO TEST 2 ' || to_char(clock_timestamp(), 'YYYYMMDDHH24MISS'), (SELECT id FROM def_stato), true)
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
-- 1b) Default stato_id su INSERT (se configurato)
-- =========================================================
CREATE TEMP TABLE tmp_topo_def_ins AS
SELECT NULL::integer AS stato_id
WHERE false;

WITH ins AS (
    INSERT INTO config.toponomastica (descrizione, stato_id, attivo)
    SELECT 'TOPO TEST DEF ' || to_char(clock_timestamp(), 'YYYYMMDDHH24MISS'), NULL, true
    WHERE (SELECT stato_id FROM tmp_def_param) IS NOT NULL
    RETURNING stato_id
)
INSERT INTO tmp_topo_def_ins (stato_id)
SELECT stato_id FROM ins;

SELECT CASE
    WHEN NOT (SELECT has_default FROM tmp_topo_norm_impl) THEN
        ok(true, 'Trigger normalize non presente: test insert default skipped')
    WHEN (SELECT stato_id FROM tmp_def_param) IS NULL THEN
        ok(true, 'Default stato_id non configurato: test insert default skipped')
    ELSE
        is(
            (SELECT stato_id FROM tmp_topo_def_ins),
            (SELECT stato_id FROM tmp_def_param),
            'stato_id default su insert (toponomastica)'
        )
END;

DELETE FROM config.toponomastica
WHERE descrizione LIKE 'TOPO TEST DEF %';

-- =========================================================
-- 1c) Errore se default assente
-- =========================================================
SELECT CASE
    WHEN NOT (SELECT has_default FROM tmp_topo_norm_impl) THEN
        ok(true, 'Trigger normalize non presente: test errore skipped')
    WHEN (SELECT stato_id FROM tmp_def_param) IS NULL THEN
        throws_ok(
            $$
            INSERT INTO config.toponomastica (descrizione, stato_id, attivo)
            VALUES ('TOPO TEST NO DEFAULT', NULL, true);
            $$,
            NULL,
            NULL,
            'Errore stato_id mancante'
        )
    ELSE
        ok(true, 'Default configurato: test errore skipped')
END;

-- =========================================================
-- 1d) Default stato_id su UPDATE (se configurato)
-- =========================================================
CREATE TEMP TABLE tmp_topo_def_upd (
    id bigint,
    stato_id integer
);

WITH ins AS (
    INSERT INTO config.toponomastica (descrizione, stato_id, attivo)
    SELECT 'TOPO TEST UPD ' || to_char(clock_timestamp(), 'YYYYMMDDHH24MISS'), (SELECT stato_id FROM tmp_def_param), true
    WHERE (SELECT stato_id FROM tmp_def_param) IS NOT NULL
    RETURNING id
)
INSERT INTO tmp_topo_def_upd (id)
SELECT id FROM ins;

UPDATE config.toponomastica
SET stato_id = NULL,
    descrizione = descrizione || ' UPD'
WHERE id IN (SELECT id FROM tmp_topo_def_upd);

UPDATE tmp_topo_def_upd
SET stato_id = (
    SELECT t.stato_id
    FROM config.toponomastica t
    WHERE t.id = tmp_topo_def_upd.id
);

CREATE TEMP TABLE tmp_topo_has_trg AS
SELECT EXISTS (
    SELECT 1
    FROM pg_trigger t
    JOIN pg_class c ON c.oid = t.tgrelid
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'config'
      AND c.relname = 'toponomastica'
      AND t.tgname = 'trg_toponomastica_normalize_ins_upd'
      AND NOT t.tgisinternal
) AS has_trg;

SELECT CASE
    WHEN NOT (SELECT has_default FROM tmp_topo_norm_impl) THEN
        ok(true, 'Trigger normalize non presente: test update default skipped')
    WHEN (SELECT stato_id FROM tmp_def_param) IS NULL THEN
        ok(true, 'Default stato_id non configurato: test update default skipped')
    WHEN NOT (SELECT has_trg FROM tmp_topo_has_trg) THEN
        ok(true, 'Trigger normalize non presente: test update default skipped')
    ELSE
        is(
            (SELECT stato_id FROM tmp_topo_def_upd),
            (SELECT stato_id FROM tmp_def_param),
            'stato_id default su update (toponomastica)'
        )
END;

DELETE FROM config.toponomastica
WHERE descrizione LIKE 'TOPO TEST UPD %';

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
-- 4) Manutenzione: bump toponomastica in uso
-- =========================================================
SELECT lives_ok(
    $$
    DO $proc$
    DECLARE
      v_topo_id integer;
    BEGIN
      SELECT id INTO v_topo_id FROM tmp_topo WHERE label = 't1';
      CALL maintenance.proc_bump_toponomastica(v_topo_id, 'TOPO TEST 22 FIX');
    END;
    $proc$;
    $$,
    'Manutenzione toponomastica con GUC attiva'
);

SELECT ok(
    EXISTS (
        SELECT 1
        FROM config.stradario_generale sg
        JOIN config.toponomastica t ON t.id = sg.toponomastica_id
        WHERE t.id = (SELECT id FROM tmp_topo WHERE label = 't1')
          AND sg.indirizzo_normalizzato ILIKE '%' || t.descrizione || '%'
    ),
    'Rinormalizzazione stradario_generale dopo manutenzione toponomastica'
);

-- =========================================================
-- 5) Disattivo toponomastica in uso -> errore
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
-- 6) Disattivo toponomastica non in uso -> ok
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
-- 7) Cambio toponomastica_id e rinormalizzazione
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
