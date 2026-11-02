-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: dbops.fn_pgtap_crea_lotto — il builder del lotto di fatturazione
-- Riferimento: brief-modello-documento-vendita §4-septies, R-4 (Tid,
--   2026-10-24); changeSet 20261024-31 (e 20261024-30 per il lotto in
--   dbops.fn_pgtap_porta_a_stato).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - il lotto nasce dalla MADRE vendite.fn_create_fatturazione_lotto: codice,
--     lock_batch_id e stato DRAFT li decide lei; emittente e utility sono
--     quelli del cliente del mondo;
--   - il lotto e' dell'azienda (nessun cliente), salvo p_del_cliente;
--   - il terzo parametro riusa un cliente gia' costruito;
--   - lo stato chiesto si raggiunge per la matrice, sul lotto vuoto;
--   - p_gruppo_key_trattenuto scrive l'esito ERRORE che trattiene il gruppo;
--   - uno stato che non c'e' (o non vale per un lotto) parla prima di scrivere.
--
-- Elenco test (plan 9):
--   1) la funzione esiste con la firma dichiarata
--   2) dal nulla: lotto DRAFT dell'azienda del mondo, senza cliente
--   3) codice e lock_batch_id li ha dati la madre
--   4) il tipo documento ha un registro (la madre lo pretende)
--   5) terzo parametro: stesso cliente e stessa azienda, lotto nuovo senza cliente
--   6) p_del_cliente: il lotto e' legato al cliente
--   7) DEFINITIVA raggiunta per la matrice, sul lotto vuoto
--   8) il gruppo trattenuto: un esito ERRORE E_PULL_COMMESSA, quello tornato
--   9) guard: uno stato che non esiste parla
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: in testa. Gli helper aprono e RICHIUDONO da se' la
--   finestra dove serve (e' il loro contratto).
SET CONSTRAINTS ALL IMMEDIATE;

-- pgtap-contesto: escluso — il contesto lo apre la funzione esaminata, che qui
--   viene chiamata come la chiamera' un file su un database ricostruito: senza
--   nessuna veste in sessione. Aprirlo prima nasconderebbe meta' del contratto.

SELECT plan(9);

-- 1) La firma
SELECT has_function(
    'dbops', 'fn_pgtap_crea_lotto',
    ARRAY['text', 'character varying', 'bigint', 'bigint', 'date', 'text', 'boolean'],
    'dbops.fn_pgtap_crea_lotto(text, character varying, bigint, bigint, date, text, boolean) esiste con la firma dichiarata'
);

-- Fixture: il primo lotto, dal nulla
CREATE TEMP TABLE t_l1 AS
SELECT * FROM dbops.fn_pgtap_crea_lotto('presidio lotto 1');

-- 2) Il lotto c'e', in bozza, dell'azienda e senza cliente
SELECT is(
    (SELECT s.codice_interno::text
         || ' ' || (l.emittente_soggetto_ruolo_id = t.emittente_soggetto_ruolo_id)::text
         || ' ' || (l.utility_id = t.utility_id)::text
         || ' ' || (l.billing_account_id IS NULL)::text
       FROM t_l1 t
       JOIN vendite.fatturazione_lotti l ON l.id = t.lotto_id
       JOIN config.stati_doc_fiscale s ON s.id = l.stato_doc_fiscale_id),
    'DRAFT true true true',
    'dal nulla: lotto DRAFT con emittente e utility del mondo, senza cliente'
);

-- 3) Codice e lock_batch_id dalla madre
SELECT ok(
    (SELECT btrim(l.codice) <> '' AND l.lock_batch_id IS NOT NULL
            AND l.lock_batch_id = t.lock_batch_id
       FROM t_l1 t JOIN vendite.fatturazione_lotti l ON l.id = t.lotto_id),
    'codice e lock_batch_id li ha assegnati la madre (vendite.fn_create_fatturazione_lotto), non la fixture'
);

-- 4) Il tipo documento ha un registro
SELECT ok(
    EXISTS (SELECT 1 FROM vendite.tipi_doc_fiscale_registri m
             WHERE m.tipo_doc_fiscale_id = (SELECT tipo_doc_fiscale_id FROM t_l1)),
    'il tipo documento scelto ha un registro (vendite.tipi_doc_fiscale_registri)'
);

-- 5) Il terzo parametro: lo stesso cliente
CREATE TEMP TABLE t_l2 AS
SELECT * FROM dbops.fn_pgtap_crea_lotto(
    'presidio lotto 2', 'DRAFT', (SELECT billing_account_id FROM t_l1));

SELECT is(
    (SELECT (l2.billing_account_id = l1.billing_account_id)::text
         || ' ' || (l2.emittente_soggetto_ruolo_id = l1.emittente_soggetto_ruolo_id)::text
         || ' ' || (l2.lotto_id <> l1.lotto_id)::text
         || ' ' || (x.billing_account_id IS NULL)::text
       FROM t_l1 l1, t_l2 l2
       JOIN vendite.fatturazione_lotti x ON x.id = l2.lotto_id),
    'true true true true',
    'terzo parametro: stesso cliente e stessa azienda, lotto nuovo, ancora senza cliente'
);

-- 6) p_del_cliente
CREATE TEMP TABLE t_l3 AS
SELECT * FROM dbops.fn_pgtap_crea_lotto(
    'presidio lotto 3', 'DRAFT', (SELECT billing_account_id FROM t_l1),
    p_del_cliente => true);

SELECT is(
    (SELECT l.billing_account_id FROM vendite.fatturazione_lotti l
      WHERE l.id = (SELECT lotto_id FROM t_l3)),
    (SELECT billing_account_id FROM t_l1),
    'p_del_cliente => true: il lotto e'' legato al cliente'
);

-- 7) DEFINITIVA per la matrice
CREATE TEMP TABLE t_l4 AS
SELECT * FROM dbops.fn_pgtap_crea_lotto(
    'presidio lotto 4', 'DEFINITIVA', (SELECT billing_account_id FROM t_l1));

SELECT is(
    (SELECT s.codice_interno::text || ' ' || (t.stato_doc_fiscale_id = l.stato_doc_fiscale_id)::text
       FROM t_l4 t
       JOIN vendite.fatturazione_lotti l ON l.id = t.lotto_id
       JOIN config.stati_doc_fiscale s ON s.id = l.stato_doc_fiscale_id),
    'DEFINITIVA true',
    'DEFINITIVA raggiunta per la matrice (dbops.fn_pgtap_porta_a_stato), e lo stato tornato e'' quello vero'
);

-- 8) Il gruppo trattenuto
CREATE TEMP TABLE t_l5 AS
SELECT * FROM dbops.fn_pgtap_crea_lotto(
    'presidio lotto 5', 'DRAFT', (SELECT billing_account_id FROM t_l1),
    p_gruppo_key_trattenuto => 'PGTAP-GRUPPO-TRATTENUTO');

SELECT is(
    (SELECT count(*)::text || ' ' || bool_and(e.id = t.esito_id)::text
            || ' ' || bool_and(e.stato_esecuzione = 'ERRORE' AND e.errore_codice = 'E_PULL_COMMESSA')::text
       FROM t_l5 t
       JOIN vendite.fatturazione_lotti_esiti e ON e.lotto_id = t.lotto_id
      WHERE e.gruppo_key = 'PGTAP-GRUPPO-TRATTENUTO'),
    '1 true true',
    'il gruppo trattenuto: un esito ERRORE E_PULL_COMMESSA sul lotto, quello tornato'
);

-- 9) Uno stato che non c'e'
SELECT throws_like(
    $$SELECT * FROM dbops.fn_pgtap_crea_lotto('presidio lotto 6', 'NON_ESISTE')$$,
    'fn_pgtap_crea_lotto: nessuno stato fiscale attivo applicabile a un lotto%',
    'uno stato che non c''e'' solleva prima di costruire, nominando il builder'
);

SELECT * FROM finish();
ROLLBACK;
