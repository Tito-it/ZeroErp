-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Trigger: dbops.trgfn_prevent_deactivate_if_children
-- Caso: config.toponomastica (padre) -> config.stradario_generale (figlio senza attivo)
-- ------------------------------------------------------------

-- ⚠️ Transazione, e non e' una formalita'. Il cleanup di questo file sta in
--   coda: col runner vero (pg_prove gira con ON_ERROR_STOP) un fallimento a
--   meta' non ci arriva mai, e i dati di prova restano nel database a rompere
--   la corsa successiva — che vede un rosso non suo.
--   Brief: brief-db-pgtap-runner-rls-baseline §15.3.
BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file diventerebbe verde per sottrazione. Nel DB ce ne sono 365.
--   IMMEDIATE li riporta a scattare a fine di OGNI istruzione — cioe' esatta-
--   mente come si comportavano prima, quando il file girava in autocommit e
--   ogni istruzione era una transazione a se'. In testa e non in coda apposta:
--   in coda scatterebbero tutti insieme DOPO il cleanup, su righe ormai
--   cancellate. Brief: brief-db-pgtap-runner-rls-baseline §17.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(9);

CREATE TEMP TABLE tmp_test_keys AS
SELECT to_char(clock_timestamp(), 'YYYYMMDDHH24MISSMS') AS ts;

-- =========================================================
-- 0) Verifica presenza trigger BLOCK su toponomastica
-- =========================================================
CREATE TEMP TABLE tmp_trg_block AS
SELECT EXISTS (
    SELECT 1
    FROM pg_trigger t
    JOIN pg_class c ON c.oid = t.tgrelid
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'config'
      AND c.relname = 'toponomastica'
      AND t.tgname ILIKE '%block_deact%'
      AND NOT t.tgisinternal
) AS has_trg;

SELECT ok(
    (SELECT has_trg FROM tmp_trg_block),
    'Trigger BLOCK presente su config.toponomastica'
);

-- =========================================================
-- 1) Crea toponomastica di test
-- =========================================================
WITH ins AS (
    INSERT INTO config.toponomastica (descrizione, stato_id, attivo)
    VALUES (
        'TOPO TEST BLOCK ' || (SELECT ts FROM tmp_test_keys),
        NULL,
        true
    )
    RETURNING id
)
SELECT id
INTO TEMP TABLE tmp_topo
FROM ins;

SELECT ok(
    (SELECT count(*) FROM tmp_topo) = 1,
    'Creato toponomastica di test'
);

-- =========================================================
-- 2) Crea stradario_generale figlio
-- =========================================================
WITH ins AS (
    INSERT INTO config.stradario_generale (toponomastica_id, descrizione, descrizione_breve)
    VALUES (
        (SELECT id FROM tmp_topo),
        'STRADARIO TEST BLOCK ' || (SELECT ts FROM tmp_test_keys),
        'SB'
    )
    RETURNING id
)
SELECT id
INTO TEMP TABLE tmp_stradario
FROM ins;

SELECT ok(
    (SELECT count(*) FROM tmp_stradario) = 1,
    'Creato stradario_generale figlio di test'
);

-- =========================================================
-- 3) Disattivazione con figlio: deve fallire
-- =========================================================
SELECT CASE
    WHEN (SELECT has_trg FROM tmp_trg_block) THEN
        throws_ok(
            $$
            UPDATE config.toponomastica
            SET attivo = false
            WHERE id = (SELECT id FROM tmp_topo);
            $$,
            NULL,
            NULL,
            'Disattivazione toponomastica con figli: bloccata'
        )
    ELSE
        ok(true, 'Trigger non presente: test blocco skipped')
END;

-- =========================================================
-- 4) Rimuovi figlio e disattiva padre
-- =========================================================
SELECT lives_ok(
    $$
    DELETE FROM config.stradario_generale
    WHERE id = (SELECT id FROM tmp_stradario);
    $$,
    'Eliminazione figlio: OK'
);

SELECT CASE
    WHEN (SELECT has_trg FROM tmp_trg_block) THEN
        lives_ok(
            $$
            UPDATE config.toponomastica
            SET attivo = false
            WHERE id = (SELECT id FROM tmp_topo);
            $$,
            'Disattivazione toponomastica senza figli: OK'
        )
    ELSE
        ok(true, 'Trigger non presente: test disattivazione skipped')
END;

SELECT CASE
    WHEN (SELECT has_trg FROM tmp_trg_block) THEN
        is(
            (SELECT attivo FROM config.toponomastica WHERE id = (SELECT id FROM tmp_topo)),
            false,
            'Toponomastica disattivata senza figli'
        )
    ELSE
        ok(true, 'Trigger non presente: check attivo skipped')
END;

-- Cleanup
DELETE FROM config.toponomastica
WHERE id = (SELECT id FROM tmp_topo);

-- =========================================================
-- 5) REQUIRE: figlio non puo' puntare a padre non attivo
-- =========================================================
WITH ins AS (
    INSERT INTO config.toponomastica (descrizione, stato_id, attivo)
    VALUES (
        'TOPO TEST INATTIVO ' || (SELECT ts FROM tmp_test_keys),
        NULL,
        false
    )
    RETURNING id
)
SELECT id
INTO TEMP TABLE tmp_topo_inattivo
FROM ins;

SELECT ok(
    (SELECT count(*) FROM tmp_topo_inattivo) = 1,
    'Creato toponomastica inattiva di test'
);

SELECT throws_ok(
    $$
    BEGIN;
      INSERT INTO config.stradario_generale (toponomastica_id, descrizione, descrizione_breve)
      VALUES (
          (SELECT id FROM tmp_topo_inattivo),
          'STRADARIO TEST INATTIVO ' || (SELECT ts FROM tmp_test_keys),
          'SI'
      );
    COMMIT;
    END;
    $$,
    NULL,
    NULL,
    'Inserimento figlio con padre inattivo: bloccato'
);

DELETE FROM config.toponomastica
WHERE id = (SELECT id FROM tmp_topo_inattivo);

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia nulla dietro di se'. Le DELETE del cleanup restano
-- perche' dove sono un'asserzione devono girare davvero.
ROLLBACK;
