-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: dbops.fn_pgtap_crea_ordine_con_righe — l'ordine con le sue righe
-- Riferimento: brief-db-pgtap-reso-costruito §7.1, E-1 (changeSet 20261025-31).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - l'ordine nasce dal builder dell'ordine (che resta senza righe, D-1) e
--     arriva allo stato chiesto (default CONFERMATO) per la matrice, con le righe
--     scritte in bozza;
--   - una riga dai parametri, o piu' righe da p_righe (sconto, date di consegna);
--   - data alla nascita e trigger di fatturazione in bozza;
--   - p_ordine_id: righe e stato su una testata in bozza del test;
--   - un errore del chiamante parla, prima di costruire.
--
-- Elenco test (plan 10):
--   1) la funzione esiste con la firma dichiarata
--   2) default: CONFERMATO, una riga 10 x 25 con l'IVA
--   3) data alla nascita e trigger di fatturazione
--   4) DRAFT con due righe da p_righe: sconto e data di consegna sulla riga giusta
--   5) il builder dell'ordine resta senza righe (D-1)
--   6) p_ordine_id: la riga si aggiunge alla testata del test, che si conferma
--   7) guard: p_righe insieme alla riga dei parametri parla
--   8) guard: una chiave di riga sconosciuta parla
--   9) guard: con p_ordine_id il trigger non si passa
--  10) guard: una testata fuori bozza parla
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: in testa. Gli helper aprono e RICHIUDONO da se' la
--   finestra dove serve (e' il loro contratto).
SET CONSTRAINTS ALL IMMEDIATE;

-- pgtap-contesto: escluso — il contesto lo apre il mondo del builder
--   esaminato, chiamato come lo chiamera' un file su un database ricostruito:
--   senza nessuna veste in sessione.

SELECT plan(10);

-- 1) La firma
SELECT has_function(
    'dbops', 'fn_pgtap_crea_ordine_con_righe',
    ARRAY['text', 'character varying', 'bigint', 'numeric', 'numeric', 'uuid',
          'character varying', 'date', 'jsonb', 'bigint'],
    'dbops.fn_pgtap_crea_ordine_con_righe esiste con la firma dichiarata'
);

-- Fixture: l'ordine di default
CREATE TEMP TABLE t_def AS
SELECT * FROM dbops.fn_pgtap_crea_ordine_con_righe('presidio ordine righe');

-- 2) Stato e riga
SELECT is(
    (SELECT s.codice_interno::text || ' ' || r.quantita::text || ' ' || r.prezzo_unitario::text
         || ' ' || (r.iva_id IS NOT NULL)::text || ' '
         || (SELECT count(*) FROM vendite.ordini_righe x WHERE x.ordine_id = d.ordine_id)::text
       FROM t_def d
       JOIN config.stati_doc_ordini s ON s.id = d.stato_doc_ordine_id
       JOIN vendite.ordini_righe r ON r.id = d.ordine_riga_id),
    'CONFERMATO 10.000000 25.000000 true 1',
    'default: ordine confermato con una riga 10 x 25 e la sua IVA'
);

-- 3) Data e trigger
CREATE TEMP TABLE t_dt AS
SELECT * FROM dbops.fn_pgtap_crea_ordine_con_righe('presidio ordine data',
                  p_billing_account_id => (SELECT billing_account_id FROM t_def),
                  p_fatturazione_trigger => 'CONSEGNATO', p_data_ordine => DATE '2026-08-05');

SELECT is(
    (SELECT o.data::text || ' ' || o.fatturazione_trigger::text
         || ' ' || (t.billing_account_id = d.billing_account_id)::text
       FROM t_dt t JOIN vendite.ordini o ON o.id = t.ordine_id, t_def d),
    '2026-08-05 CONSEGNATO true',
    'la data nasce con la testata, il trigger si scrive in bozza, il cliente e'' quello del test'
);

-- 4) Due righe in bozza
CREATE TEMP TABLE t_due AS
SELECT * FROM dbops.fn_pgtap_crea_ordine_con_righe('presidio ordine due', 'DRAFT',
                  p_righe => jsonb_build_array(
                      jsonb_build_object('quantita', 10, 'prezzo', 20, 'sconto_percentuale', 5),
                      jsonb_build_object('quantita', 5, 'prezzo', 20,
                                         'data_consegna_confermata', '2026-12-20')));

SELECT is(
    (SELECT s.codice_interno::text || ' | '
         || string_agg(r.riga_nr || ':' || r.quantita || ':' || r.sconto_percentuale || ':'
                       || coalesce(r.data_consegna_confermata::text, '-'), ' ' ORDER BY r.riga_nr)
       FROM t_due d
       JOIN config.stati_doc_ordini s ON s.id = d.stato_doc_ordine_id
       JOIN vendite.ordini_righe r ON r.ordine_id = d.ordine_id
      GROUP BY s.codice_interno),
    'DRAFT | 1:10.000000:5.00:- 2:5.000000:0.00:2026-12-20',
    'DRAFT con due righe: lo sconto sulla prima, la data di consegna sulla seconda, il default di tabella altrove'
);

-- 5) D-1: il builder dell'ordine resta senza righe
CREATE TEMP TABLE t_nudo AS
SELECT * FROM dbops.fn_pgtap_crea_ordine('presidio ordine nudo');

SELECT is(
    (SELECT count(*)::int FROM vendite.ordini_righe r WHERE r.ordine_id = (SELECT ordine_id FROM t_nudo)),
    0,
    'dbops.fn_pgtap_crea_ordine continua a non scrivere righe (D-1 di brief-db-righe-e-componenti-debiti-residui)'
);

-- 6) La testata del test
CREATE TEMP TABLE t_test AS
SELECT * FROM dbops.fn_pgtap_crea_ordine_con_righe('presidio ordine test',
                  p_quantita => 3, p_ordine_id => (SELECT ordine_id FROM t_nudo));

SELECT is(
    (SELECT (t.ordine_id = n.ordine_id)::text || ' ' || s.codice_interno::text || ' ' || r.quantita::text
       FROM t_test t
       JOIN config.stati_doc_ordini s ON s.id = t.stato_doc_ordine_id
       JOIN vendite.ordini_righe r ON r.id = t.ordine_riga_id, t_nudo n),
    'true CONFERMATO 3.000000',
    'p_ordine_id: la riga va sulla testata del test, che arriva confermata'
);

-- 7) Guard: due modi di dire le righe
SELECT throws_like(
    $$SELECT dbops.fn_pgtap_crea_ordine_con_righe('presidio', p_quantita => 1,
                                                 p_righe => '[{"quantita": 1}]'::jsonb)$$,
    '%p_righe insieme a p_quantita%',
    'guard: p_righe insieme alla riga dei parametri parla'
);

-- 8) Guard: chiave sconosciuta
SELECT throws_like(
    $$SELECT dbops.fn_pgtap_crea_ordine_con_righe('presidio', p_righe => '[{"qta": 1}]'::jsonb)$$,
    '%chiavi di riga sconosciute%',
    'guard: una chiave di riga che il builder non conosce parla (errore di battitura)'
);

-- 9) Guard: il trigger e' della testata del test
SELECT throws_like(
    format($$SELECT dbops.fn_pgtap_crea_ordine_con_righe('presidio', p_ordine_id => %s, p_fatturazione_trigger => 'SPEDITO')$$,
           (SELECT ordine_id FROM t_nudo)),
    '%con p_ordine_id cliente, data e trigger%',
    'guard: con p_ordine_id il trigger di fatturazione non si passa'
);

-- 10) Guard: le righe si scrivono in bozza
SELECT throws_like(
    format($$SELECT dbops.fn_pgtap_crea_ordine_con_righe('presidio', p_ordine_id => %s)$$,
           (SELECT ordine_id FROM t_def)),
    '%fuori bozza%',
    'guard: una testata fuori bozza parla, invece di arrivare al lock delle righe'
);

SELECT * FROM finish();
ROLLBACK;
