-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: le FK di una tabella lette da pg_constraint (dbops.fn_foreign_keys_info)
--   e chi punta a una tabella (dbops.fn_find_file_usage).
-- Riferimento: brief-db-revisione-dbops, giro 4 (D53, Q9).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - una FK composita da' una riga per colonna, la colonna n della figlia
--     con la colonna n del padre, e la posizione: niente prodotto cartesiano;
--   - la tabella si nomina con lo schema: un'omonima in un altro schema non
--     entra nella risposta;
--   - su una figlia o un padre partizionati la FK dichiarata compare una volta,
--     non una per partizione;
--   - dbops.fn_find_file_usage sono le righe entranti di
--     dbops.fn_foreign_keys_info, con la colonna referenziata (anche una
--     UNIQUE che non e' la chiave primaria).
--
-- Elenco test (plan 9):
--   1-2) le firme
--   3)   FK composita entrante: due righe, coppie e posizioni giuste
--   4)   la stessa FK vista dalla figlia: due righe uscenti
--   5)   una FK verso una UNIQUE non primaria: la colonna referenziata e' quella
--   6)   l'omonima in un altro schema non entra
--   7)   figlia partizionata: la FK dichiarata compare una volta sul padre
--   8)   padre partizionato: la FK dichiarata compare una volta sulla figlia
--   9)   fn_find_file_usage = le entranti di fn_foreign_keys_info
--
-- ⚠️ Fixture su tabelle TEMP (pg_temp): l'omonima e' la TEMP «fatture», con lo
--   stesso nome di vendite.fatture. Nessun DDL su tabelle condivise, il
--   ROLLBACK porta via tutto.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

-- pgtap-contesto: escluso — il file legge il catalogo e crea solo tabelle TEMP
--   sue: nessuna tabella sotto RLS, nessuna veste da aprire.

SELECT plan(9);

-- Padre con chiave composita e una UNIQUE non primaria
CREATE TEMP TABLE t_padre (
    id    bigint PRIMARY KEY,
    a     int NOT NULL,
    b     int NOT NULL,
    cod   text NOT NULL UNIQUE,
    UNIQUE (a, b)
);
-- Figlia con la FK composita (colonne in ordine inverso rispetto al nome) e una FK sulla UNIQUE
CREATE TEMP TABLE t_figlia (
    id     bigint PRIMARY KEY,
    y      int,
    x      int,
    cod_p  text REFERENCES t_padre (cod),
    CONSTRAINT fk_t_figlia_comp FOREIGN KEY (x, y) REFERENCES t_padre (a, b)
);
-- L'omonima di vendite.fatture, in pg_temp, con una FK sua
CREATE TEMP TABLE fatture (
    id        bigint PRIMARY KEY,
    padre_id  bigint REFERENCES t_padre (id)
);
-- Figlia partizionata
CREATE TEMP TABLE t_figlia_part (
    id        bigint,
    anno      int,
    padre_id  bigint,
    PRIMARY KEY (id, anno),
    CONSTRAINT fk_t_figlia_part_padre FOREIGN KEY (padre_id) REFERENCES t_padre (id)
) PARTITION BY RANGE (anno);
CREATE TEMP TABLE t_figlia_part_1 PARTITION OF t_figlia_part FOR VALUES FROM (2025) TO (2026);
CREATE TEMP TABLE t_figlia_part_2 PARTITION OF t_figlia_part FOR VALUES FROM (2026) TO (2027);
-- Padre partizionato e una figlia che lo referenzia
CREATE TEMP TABLE t_padre_part (
    id    bigint,
    anno  int,
    PRIMARY KEY (id, anno)
) PARTITION BY RANGE (anno);
CREATE TEMP TABLE t_padre_part_1 PARTITION OF t_padre_part FOR VALUES FROM (2025) TO (2026);
CREATE TEMP TABLE t_padre_part_2 PARTITION OF t_padre_part FOR VALUES FROM (2026) TO (2027);
CREATE TEMP TABLE t_figlia_di_part (
    id      bigint PRIMARY KEY,
    p_id    bigint,
    p_anno  int,
    CONSTRAINT fk_t_figlia_di_part FOREIGN KEY (p_id, p_anno) REFERENCES t_padre_part (id, anno)
);

-- ============================================================
-- 1-2) Le firme
-- ============================================================
SELECT has_function('dbops', 'fn_foreign_keys_info', ARRAY['regclass'],
    '1) dbops.fn_foreign_keys_info(regclass) esiste');
SELECT has_function('dbops', 'fn_find_file_usage', ARRAY['regclass'],
    '2) dbops.fn_find_file_usage(regclass) esiste');

-- ============================================================
-- 3-5) Le coppie di colonne
-- ============================================================
SELECT results_eq(
    $$SELECT posizione, source_column::text COLLATE "default", target_column::text COLLATE "default"
        FROM dbops.fn_foreign_keys_info('t_padre'::regclass)
       WHERE relazione = 'incoming' AND constraint_name = 'fk_t_figlia_comp'
       ORDER BY posizione$$,
    $$VALUES (1::bigint, 'x', 'a'), (2::bigint, 'y', 'b')$$,
    '3) FK composita entrante: due righe, x con a e y con b, nell''ordine della chiave (prima: quattro, ogni colonna con ogni colonna)'
);
SELECT results_eq(
    $$SELECT posizione, source_column::text COLLATE "default", target_table, target_column::text COLLATE "default"
        FROM dbops.fn_foreign_keys_info('t_figlia'::regclass)
       WHERE relazione = 'outgoing' AND constraint_name = 'fk_t_figlia_comp'
       ORDER BY posizione$$,
    $$VALUES (1::bigint, 'x', 't_padre'::regclass, 'a'), (2::bigint, 'y', 't_padre'::regclass, 'b')$$,
    '4) la stessa FK vista dalla figlia: due righe uscenti verso t_padre'
);
SELECT results_eq(
    $$SELECT source_column::text COLLATE "default", target_column::text COLLATE "default"
        FROM dbops.fn_foreign_keys_info('t_figlia'::regclass)
       WHERE relazione = 'outgoing' AND source_column = 'cod_p'$$,
    $$VALUES ('cod_p', 'cod')$$,
    '5) una FK verso una UNIQUE non primaria: la colonna referenziata e'' cod, non la chiave primaria'
);

-- ============================================================
-- 6) Lo schema conta
-- ============================================================
SELECT is_empty(
    $$SELECT 1 FROM dbops.fn_foreign_keys_info('vendite.fatture'::regclass)
       WHERE source_table = 'pg_temp.fatture'::regclass OR target_table = 't_padre'::regclass$$,
    '6) vendite.fatture non vede la FK dell''omonima in pg_temp (prima: il filtro era per solo nome)'
);

-- ============================================================
-- 7-8) Le partizioni
-- ============================================================
SELECT results_eq(
    $$SELECT source_table, count(*)
        FROM dbops.fn_foreign_keys_info('t_padre'::regclass)
       WHERE relazione = 'incoming' AND source_column = 'padre_id'
       GROUP BY source_table ORDER BY source_table::text$$,
    $$VALUES ('pg_temp.fatture'::regclass, 1::bigint), ('t_figlia_part'::regclass, 1::bigint)$$,
    '7) figlia partizionata: la FK compare una volta, sulla tabella partizionata, non una per partizione'
);
SELECT results_eq(
    $$SELECT constraint_name::text COLLATE "default", target_table, count(*)
        FROM dbops.fn_foreign_keys_info('t_figlia_di_part'::regclass)
       WHERE relazione = 'outgoing'
       GROUP BY 1, 2$$,
    $$VALUES ('fk_t_figlia_di_part', 't_padre_part'::regclass, 2::bigint)$$,
    '8) padre partizionato: la FK della figlia compare una volta (due colonne), verso la tabella partizionata'
);

-- ============================================================
-- 9) fn_find_file_usage e' la vista entrante di fn_foreign_keys_info
-- ============================================================
SELECT set_eq(
    $$SELECT table_with_fk, fk_name, posizione, fk_column, referenced_table, referenced_column
        FROM dbops.fn_find_file_usage('t_padre'::regclass)$$,
    $$SELECT source_table, constraint_name, posizione, source_column, target_table, target_column
        FROM dbops.fn_foreign_keys_info('t_padre'::regclass)
       WHERE relazione = 'incoming'$$,
    '9) dbops.fn_find_file_usage sono le righe entranti di dbops.fn_foreign_keys_info'
);

SELECT * FROM finish();
ROLLBACK;
