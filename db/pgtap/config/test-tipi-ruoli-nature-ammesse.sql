-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test tabella config.tipi_ruoli_nature_ammesse
-- Verifica: struttura, seed data, vincoli UNIQUE, CHECK, FK
--
-- Indice test:
--   1) Tabella config.tipi_ruoli_nature_ammesse esiste
--   2) Seed data: 19 righe totali
--   3) GE ammette solo PG (1 riga)
--   4) EF ammette solo PG (1 riga)
--   5) RIS_UMANA ammette solo PF (1 riga)
--   6) CL ammette PF, PG, ENC (3 righe)
--   7) FO ammette PF, PG, ENC (3 righe)
--   8) VT ammette PF, PG (2 righe)
--   9) UNIQUE constraint: duplicato (tipo_ruolo_id, tipo_soggetto_id) bloccato
--  10) CHECK: valido_al < valido_dal bloccato
--  11) FK tipo_ruolo_id: valore invalido bloccato
--  12) FK tipo_soggetto_id: valore invalido bloccato
-- ------------------------------------------------------------

SELECT plan(12);

-- =========================================================
-- 1) La tabella esiste
-- =========================================================
SELECT has_table('config', 'tipi_ruoli_nature_ammesse', 'Tabella config.tipi_ruoli_nature_ammesse esiste');

-- =========================================================
-- 2) Seed data: 19 righe totali
-- =========================================================
SELECT is(
    (SELECT count(*)::int FROM config.tipi_ruoli_nature_ammesse),
    19,
    'Seed data: 19 righe totali in tipi_ruoli_nature_ammesse'
);

-- =========================================================
-- 3) GE ammette solo PG
-- =========================================================
SELECT is(
    (SELECT count(*)::int FROM config.tipi_ruoli_nature_ammesse
     WHERE tipo_ruolo_id = 3 AND attivo = true),
    1,
    'GE (id=3): ammette solo 1 natura (PG)'
);

-- =========================================================
-- 4) EF ammette solo PG
-- =========================================================
SELECT is(
    (SELECT count(*)::int FROM config.tipi_ruoli_nature_ammesse
     WHERE tipo_ruolo_id = 7 AND attivo = true),
    1,
    'EF (id=7): ammette solo 1 natura (PG)'
);

-- =========================================================
-- 5) RIS_UMANA ammette solo PF
-- =========================================================
SELECT is(
    (SELECT count(*)::int FROM config.tipi_ruoli_nature_ammesse
     WHERE tipo_ruolo_id = 14 AND attivo = true),
    1,
    'RIS_UMANA (id=14): ammette solo 1 natura (PF)'
);

-- =========================================================
-- 6) CL ammette PF, PG, ENC (3 righe)
-- =========================================================
SELECT is(
    (SELECT count(*)::int FROM config.tipi_ruoli_nature_ammesse
     WHERE tipo_ruolo_id = 1 AND attivo = true),
    3,
    'CL (id=1): ammette 3 nature (PF, PG, ENC)'
);

-- =========================================================
-- 7) FO ammette PF, PG, ENC (3 righe)
-- =========================================================
SELECT is(
    (SELECT count(*)::int FROM config.tipi_ruoli_nature_ammesse
     WHERE tipo_ruolo_id = 2 AND attivo = true),
    3,
    'FO (id=2): ammette 3 nature (PF, PG, ENC)'
);

-- =========================================================
-- 8) VT ammette PF, PG (2 righe)
-- =========================================================
SELECT is(
    (SELECT count(*)::int FROM config.tipi_ruoli_nature_ammesse
     WHERE tipo_ruolo_id = 9 AND attivo = true),
    2,
    'VT (id=9): ammette 2 nature (PF, PG)'
);

-- Riallineo la sequenza IDENTITY dopo il seed CSV
SELECT setval(
    pg_get_serial_sequence('config.tipi_ruoli_nature_ammesse', 'id'),
    COALESCE((SELECT MAX(id) FROM config.tipi_ruoli_nature_ammesse), 1)
);

-- =========================================================
-- 9) UNIQUE: duplicato (tipo_ruolo_id, tipo_soggetto_id) bloccato
-- =========================================================
SELECT throws_ok(
    $$
      INSERT INTO config.tipi_ruoli_nature_ammesse (tipo_ruolo_id, tipo_soggetto_id)
      VALUES (3, 'PG');
    $$,
    '23505'
);

-- =========================================================
-- 10) CHECK: valido_al < valido_dal bloccato
-- =========================================================
SELECT throws_ok(
    $$
      INSERT INTO config.tipi_ruoli_nature_ammesse
        (tipo_ruolo_id, tipo_soggetto_id, valido_dal, valido_al)
      VALUES (3, 'ENC', '2026-06-01', '2026-01-01');
    $$,
    '23514'
);

-- =========================================================
-- 11) FK: tipo_ruolo_id invalido bloccato
-- =========================================================
SELECT throws_ok(
    $$
      INSERT INTO config.tipi_ruoli_nature_ammesse (tipo_ruolo_id, tipo_soggetto_id)
      VALUES (9999, 'PG');
    $$,
    '23503'
);

-- =========================================================
-- 12) FK: tipo_soggetto_id invalido bloccato
-- =========================================================
SELECT throws_ok(
    $$
      INSERT INTO config.tipi_ruoli_nature_ammesse (tipo_ruolo_id, tipo_soggetto_id)
      VALUES (1, 'INVALIDO');
    $$,
    '23503'
);

-- Fine test
SELECT * FROM finish();
