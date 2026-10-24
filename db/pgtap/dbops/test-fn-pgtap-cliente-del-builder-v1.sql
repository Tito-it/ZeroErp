-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: dbops.fn_pgtap_cliente_del_builder e dbops.fn_pgtap_azienda_di_chi_agisce
--   — il cliente dei builder col billing account del test, senza clienti in piu'
-- Riferimento: brief-modello-documento-vendita §4-octies (Tid, 2026-10-24);
--   changeSet 20261024-37, -38, -39, -40.
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - senza contesto l'azienda di chi agisce non c'e', e il building block lo dice;
--   - senza billing account il cliente e' quello del mondo (nuovo);
--   - col billing account del test: l'azienda di chi agisce e quel BA, e
--     NESSUN cliente nuovo, nemmeno passando dai cinque builder;
--   - un BA di un'altra azienda solleva, nominando il chiamante.
--
-- Elenco test (plan 7):
--   1) senza contesto: l'azienda di chi agisce solleva, nominando il chiamante
--   2) senza BA: il mondo, con un cliente nuovo e il contesto aperto
--   3) con contesto: l'azienda di chi agisce e' quella del mondo
--   4) col BA del test: stesso cliente, stessa azienda, nessun BA nuovo
--   5) i cinque builder col BA del test non costruiscono clienti in piu'
--   6) ...e ciascuno scrive sul cliente chiesto
--   7) un BA di un'altra azienda solleva, nominando il chiamante
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

-- pgtap-contesto: escluso — il contesto lo apre la funzione esaminata (ramo
--   «senza BA»), chiamata come su un database ricostruito.

SELECT plan(7);

-- 1) Senza contesto
SELECT throws_like(
    $$SELECT * FROM dbops.fn_pgtap_azienda_di_chi_agisce('presidio senza contesto')$$,
    'presidio senza contesto: nessun contesto aperto%',
    '1) senza contesto l''azienda di chi agisce non c''e'', e lo dice nominando il chiamante'
);

-- 2) Senza BA: il mondo
CREATE TEMP TABLE t_c1 AS
SELECT * FROM dbops.fn_pgtap_cliente_del_builder('presidio cliente 1', NULL, 'presidio');

SELECT ok(
    (SELECT c.billing_account_id IS NOT NULL
            AND NULLIF(current_setting('app.current_user_id', true), '')::integer = c.auth_user_id
       FROM t_c1 c),
    '2) senza billing account: il mondo, con un cliente nuovo e il contesto aperto sul suo operatore'
);

-- 3) L'azienda di chi agisce e' quella del mondo
SELECT is(
    (SELECT a.emittente_soggetto_ruolo_id FROM dbops.fn_pgtap_azienda_di_chi_agisce('presidio') a),
    (SELECT emittente_soggetto_ruolo_id FROM t_c1),
    '3) con il contesto aperto l''azienda di chi agisce e'' quella del mondo'
);

-- Quanti clienti ha l'azienda: il metro dei test 4-5.
CREATE TEMP TABLE t_ba_prima AS
SELECT count(*)::int AS n
  FROM anagrafiche.emittenti_fiscali_billing_account efba
 WHERE efba.emittente_soggetto_ruolo_id = (SELECT emittente_soggetto_ruolo_id FROM t_c1);

-- 4) Col BA del test: niente di nuovo
CREATE TEMP TABLE t_c2 AS
SELECT * FROM dbops.fn_pgtap_cliente_del_builder(
    'presidio cliente 2', (SELECT billing_account_id FROM t_c1), 'presidio');

SELECT is(
    (SELECT (c2.billing_account_id = c1.billing_account_id)::text
         || ' ' || (c2.emittente_soggetto_ruolo_id = c1.emittente_soggetto_ruolo_id)::text
         || ' ' || ((SELECT count(*) FROM anagrafiche.emittenti_fiscali_billing_account efba
                      WHERE efba.emittente_soggetto_ruolo_id = c1.emittente_soggetto_ruolo_id)
                    = (SELECT n FROM t_ba_prima))::text
       FROM t_c1 c1, t_c2 c2),
    'true true true',
    '4) col billing account del test: stesso cliente, stessa azienda, nessun cliente nuovo'
);

-- 5-6) I cinque builder col BA del test
CREATE TEMP TABLE t_doc AS
SELECT 'commessa' AS b, c.billing_account_id FROM dbops.fn_pgtap_crea_commessa('presidio b1', NULL, (SELECT billing_account_id FROM t_c1)) c
UNION ALL
SELECT 'contratto', k.billing_account_id FROM dbops.fn_pgtap_crea_contratto('presidio b2', 'DRAFT', (SELECT billing_account_id FROM t_c1)) k
UNION ALL
SELECT 'fattura', f.billing_account_id FROM dbops.fn_pgtap_crea_fattura('presidio b3', 'DRAFT', (SELECT billing_account_id FROM t_c1)) f
UNION ALL
SELECT 'ordine', o.billing_account_id FROM dbops.fn_pgtap_crea_ordine('presidio b4', 'DRAFT', (SELECT billing_account_id FROM t_c1)) o
UNION ALL
SELECT 'lotto', l.billing_account_id FROM dbops.fn_pgtap_crea_lotto('presidio b5', 'DRAFT', (SELECT billing_account_id FROM t_c1)) l;

SELECT is(
    (SELECT count(*)::int FROM anagrafiche.emittenti_fiscali_billing_account efba
      WHERE efba.emittente_soggetto_ruolo_id = (SELECT emittente_soggetto_ruolo_id FROM t_c1)),
    (SELECT n FROM t_ba_prima),
    '5) i cinque builder (commessa, contratto, fattura, ordine, lotto) col BA del test non costruiscono clienti in piu'''
);

SELECT is(
    (SELECT count(*)::int || ' ' || bool_and(d.billing_account_id = (SELECT billing_account_id FROM t_c1))::text
       FROM t_doc d),
    '5 true',
    '6) ...e ciascuno torna il cliente chiesto'
);

-- 7) Un BA di un'altra azienda
CREATE TEMP TABLE t_altrui AS
SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM t_altrui)); END $ctx$;
CREATE TEMP TABLE t_ba_altrui AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('presidio cliente altrui');
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM t_c1)); END $ctx$;

SELECT throws_like(
    format($$SELECT * FROM dbops.fn_pgtap_cliente_del_builder('presidio altrui', %s, 'presidio altrui')$$,
           (SELECT billing_account_id FROM t_ba_altrui)),
    'presidio altrui: %',
    '7) un billing account di un''altra azienda solleva, nominando il chiamante'
);

SELECT * FROM finish();
ROLLBACK;
