-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: anagrafiche.fn_get_evento_stato_corrente_cliente(p_cliente_id).
-- Migration: 20260428-01-create-fn-get-evento-stato-corrente-cliente.
--
-- Strategia: costruisci un cliente, fai UPDATE delle date
-- (data_sospensione/data_riattivazione) per ogni scenario. Tutto in
-- BEGIN/ROLLBACK quindi nessun side-effect persistente. Eventuali trigger
-- BEFORE UPDATE su clienti non interferiscono con sosp/riatt.
-- (rev 2026-07-31: il trigger di normalize giorni_scadenza, che qui si
--  citava come non scattante, non esiste piu' — D-I, piano satelliti 3a.5.)
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

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file sarebbe verde per sottrazione. IMMEDIATE li riporta a scattare a fine
--   di ogni istruzione. In testa e non in coda: in coda scatterebbero dopo il
--   cleanup, su righe ormai cancellate.
--   Brief: brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(8);

-- =========================================================
-- Setup: costruisci un cliente.
--
-- rev 2026-09-23 (brief-db-fixture-che-costruiscono-giro-2, lotto 2).
--   Il cliente si PESCAVA («il primo di anagrafiche.clienti»): su un
--   database ricostruito (la CI) la tabella e' vuota, tmp_ctx_cliente
--   restava senza righe e la funzione moriva su p_cliente_id NULL con zero
--   asserzioni. Ora la catena soggetto -> CL -> istanza -> BA viene da
--   dbops.fn_pgtap_crea_cliente, nello stato PR come
--   anagrafiche/create-cliente. L'utility e' una che NON richiede il PDP
--   (config.utilities.richiede_pdp): il soggetto del test sono le date di
--   sospensione, e un cliente su un'utility a PDP ne pretenderebbe uno.
--   ⭐ rev 2026-10-10 (brief-db-codici-non-trovato-email-e-permessi R-9): la
--   riga di anagrafiche.clienti la scrive il builder, non piu' questo file
--   dopo fn_pgtap_crea_cliente_ba (regola del 2: le copie a mano erano gia'
--   diverse fra loro).
--   ⛔ Cio' che il builder scrive si legge in un'istruzione SEPARATA.
-- =========================================================
CREATE TEMP TABLE tmp_ctx_cliente AS
SELECT c.cliente_id
  FROM dbops.fn_pgtap_crea_cliente(
           'evento stato corrente',
           (SELECT u.id FROM config.utilities u
             WHERE NOT u.richiede_pdp
             ORDER BY u.id LIMIT 1),
           NULL,
           'PR') c;

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
