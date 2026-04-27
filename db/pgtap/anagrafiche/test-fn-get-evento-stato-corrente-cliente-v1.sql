-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: anagrafiche.fn_get_evento_stato_corrente_cliente(p_cliente_id).
-- Migration: 20260428-01-create-fn-get-evento-stato-corrente-cliente.
--
-- Strategia: prendi un cliente esistente, fai UPDATE delle date
-- (data_sospensione/data_riattivazione) per ogni scenario. Tutto in
-- BEGIN/ROLLBACK quindi nessun side-effect persistente. Il trigger di
-- normalize giorni_scadenza non scatta (clausola OF tipo_gg_scadenza_ft,
-- nr_giorni_scadenza). Eventuali altri trigger BEFORE UPDATE su clienti
-- non interferiscono con sosp/riatt.
--
-- Indice test (1..8):
--   1) sosp NULL, riatt NULL -> (NULL, NULL)
--   2) solo sospensione -> (data_sosp, 'SOSPENSIONE')
--   3) solo riattivazione (caso anomalo, opzione A) -> (data_riatt, 'RIATTIVAZIONE')
--   4) sosp > riatt -> (data_sosp, 'SOSPENSIONE')
--   5) sosp < riatt -> (data_riatt, 'RIATTIVAZIONE')
--   6) sosp = riatt -> (data_riatt, 'RIATTIVAZIONE') (pareggio = riatt)
--   7) p_cliente_id NULL -> E_PARAMETRO_INVALIDO
--   8) p_cliente_id non esistente -> E_VALORE_MANCANTE
-- ------------------------------------------------------------

BEGIN;
SELECT plan(8);

-- =========================================================
-- Setup: prendi un cliente esistente.
-- =========================================================
CREATE TEMP TABLE tmp_ctx_cliente AS
SELECT id AS cliente_id
  FROM anagrafiche.clienti
 ORDER BY id
 LIMIT 1;

-- ============================================================
-- 1) sosp NULL, riatt NULL -> (NULL, NULL)
-- ============================================================
UPDATE anagrafiche.clienti
   SET data_sospensione   = NULL,
       data_riattivazione = NULL
 WHERE id = (SELECT cliente_id FROM tmp_ctx_cliente);

SELECT is(
    (SELECT row(data_evento_stato, tipo_evento)::text
       FROM anagrafiche.fn_get_evento_stato_corrente_cliente(
                (SELECT cliente_id FROM tmp_ctx_cliente))),
    '(,)'::text,
    'sosp NULL + riatt NULL -> (NULL, NULL)'
);

-- ============================================================
-- 2) solo sospensione -> (data_sosp, 'SOSPENSIONE')
-- ============================================================
UPDATE anagrafiche.clienti
   SET data_sospensione   = DATE '2026-03-01',
       data_riattivazione = NULL
 WHERE id = (SELECT cliente_id FROM tmp_ctx_cliente);

SELECT is(
    (SELECT row(data_evento_stato, tipo_evento)::text
       FROM anagrafiche.fn_get_evento_stato_corrente_cliente(
                (SELECT cliente_id FROM tmp_ctx_cliente))),
    '(2026-03-01,SOSPENSIONE)'::text,
    'solo sospensione -> (data_sosp, SOSPENSIONE)'
);

-- ============================================================
-- 3) solo riattivazione (anomalo, opzione A) -> (data_riatt, 'RIATTIVAZIONE')
-- ============================================================
UPDATE anagrafiche.clienti
   SET data_sospensione   = NULL,
       data_riattivazione = DATE '2026-04-01'
 WHERE id = (SELECT cliente_id FROM tmp_ctx_cliente);

SELECT is(
    (SELECT row(data_evento_stato, tipo_evento)::text
       FROM anagrafiche.fn_get_evento_stato_corrente_cliente(
                (SELECT cliente_id FROM tmp_ctx_cliente))),
    '(2026-04-01,RIATTIVAZIONE)'::text,
    'solo riattivazione (anomalo) -> (data_riatt, RIATTIVAZIONE)'
);

-- ============================================================
-- 4) sosp > riatt -> (data_sosp, 'SOSPENSIONE')
--    Cronologia: prima riattivato, poi sospeso di nuovo -> SOSPESO
-- ============================================================
UPDATE anagrafiche.clienti
   SET data_sospensione   = DATE '2026-04-15',
       data_riattivazione = DATE '2026-04-01'
 WHERE id = (SELECT cliente_id FROM tmp_ctx_cliente);

SELECT is(
    (SELECT row(data_evento_stato, tipo_evento)::text
       FROM anagrafiche.fn_get_evento_stato_corrente_cliente(
                (SELECT cliente_id FROM tmp_ctx_cliente))),
    '(2026-04-15,SOSPENSIONE)'::text,
    'sosp > riatt -> (data_sosp, SOSPENSIONE)'
);

-- ============================================================
-- 5) sosp < riatt -> (data_riatt, 'RIATTIVAZIONE')
--    Cronologia: prima sospeso, poi riattivato -> RIATTIVATO
-- ============================================================
UPDATE anagrafiche.clienti
   SET data_sospensione   = DATE '2026-03-01',
       data_riattivazione = DATE '2026-04-01'
 WHERE id = (SELECT cliente_id FROM tmp_ctx_cliente);

SELECT is(
    (SELECT row(data_evento_stato, tipo_evento)::text
       FROM anagrafiche.fn_get_evento_stato_corrente_cliente(
                (SELECT cliente_id FROM tmp_ctx_cliente))),
    '(2026-04-01,RIATTIVAZIONE)'::text,
    'sosp < riatt -> (data_riatt, RIATTIVAZIONE)'
);

-- ============================================================
-- 6) sosp = riatt -> pareggio = (data_riatt, 'RIATTIVAZIONE')
-- ============================================================
UPDATE anagrafiche.clienti
   SET data_sospensione   = DATE '2026-04-10',
       data_riattivazione = DATE '2026-04-10'
 WHERE id = (SELECT cliente_id FROM tmp_ctx_cliente);

SELECT is(
    (SELECT row(data_evento_stato, tipo_evento)::text
       FROM anagrafiche.fn_get_evento_stato_corrente_cliente(
                (SELECT cliente_id FROM tmp_ctx_cliente))),
    '(2026-04-10,RIATTIVAZIONE)'::text,
    'sosp = riatt (pareggio) -> RIATTIVAZIONE (operazione successiva)'
);

-- ============================================================
-- 7) p_cliente_id NULL -> E_PARAMETRO_INVALIDO
-- ============================================================
SELECT throws_ok(
    $$SELECT * FROM anagrafiche.fn_get_evento_stato_corrente_cliente(NULL)$$,
    'P0001',
    NULL,
    'p_cliente_id NULL deve sollevare E_PARAMETRO_INVALIDO'
);

-- ============================================================
-- 8) p_cliente_id non esistente -> E_VALORE_MANCANTE
--    Uso un id che non puo' esistere in dev (BIGINT alto).
-- ============================================================
SELECT throws_ok(
    $$SELECT * FROM anagrafiche.fn_get_evento_stato_corrente_cliente(999999999)$$,
    'P0001',
    NULL,
    'p_cliente_id non esistente deve sollevare E_VALORE_MANCANTE'
);

SELECT * FROM finish();
ROLLBACK;
