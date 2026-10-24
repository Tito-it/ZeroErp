-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: dbops.fn_pgtap_crea_reso — il reso di fixture su una bolla
-- Riferimento: brief-db-pgtap-reso-costruito §3 (changeSet 20261025-05).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - senza bolla dal test, ne costruisce una consegnata e ci appoggia un reso
--     a credito confermato, per la meta' della riga;
--   - la testata porta solo i dati del reso: cliente, numero e stato li mettono
--     i trigger del dominio; la riga punta alla riga della bolla e alla riga
--     d'ordine del legame;
--   - la conferma passa dal verbo; DRAFT lascia il reso in bozza, e p_reso_id
--     gli aggiunge una riga;
--   - le regole del reso le giudicano i guard veri, non il builder;
--   - un errore del chiamante parla, prima di costruire.
--
-- Elenco test (plan 11):
--   1) la funzione esiste con la firma dichiarata
--   2) default: reso CONFERMATO, RESO_A_CREDITO, 5 di 10 (la meta' della riga)
--   3) default: la riga punta alla riga della bolla e alla riga d'ordine del legame
--   4) bolla del test: sorgente, cliente della bolla, numero dal dominio
--   5) DRAFT: il reso resta in bozza
--   6) p_reso_id: la seconda riga si aggiunge allo stesso reso, che si conferma
--   7) tipo per codice: RESO_PER_RICONSEGNA
--   8) la quantita' oltre il consegnato la rifiuta il guard vero
--   9) un reso su una bolla non consegnata lo rifiuta il guard vero
--  10) guard: uno stato abortito parla e nomina il verbo dell'annullo
--  11) guard: con p_reso_id la data non si passa
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: in testa. Gli helper aprono e RICHIUDONO da se' la
--   finestra dove serve (e' il loro contratto).
SET CONSTRAINTS ALL IMMEDIATE;

-- pgtap-contesto: escluso — il contesto lo apre il mondo del builder della
--   bolla, chiamato come lo chiamera' un file su un database ricostruito:
--   senza nessuna veste in sessione.

SELECT plan(11);

-- 1) La firma
SELECT has_function(
    'dbops', 'fn_pgtap_crea_reso',
    ARRAY['text', 'bigint', 'numeric', 'character varying', 'character varying',
          'bigint', 'bigint', 'bigint', 'date'],
    'dbops.fn_pgtap_crea_reso esiste con la firma dichiarata'
);

-- Fixture: il reso di default, dal nulla
CREATE TEMP TABLE t_def AS
SELECT * FROM dbops.fn_pgtap_crea_reso('presidio reso');

-- 2) Stato, tipo, quantita'
SELECT is(
    (SELECT s.codice_interno::text || ' ' || t.codice_interno::text || ' ' || d.quantita::text
       FROM t_def d
       JOIN config.stati_doc_reso s ON s.id = d.stato_doc_reso_id
       JOIN config.tipi_reso t ON t.id = d.tipo_reso_id),
    'CONFERMATO RESO_A_CREDITO 5.000000',
    'default: reso confermato a credito, per la meta'' della riga della bolla (5 di 10)'
);

-- 3) I legami della riga
SELECT is(
    (SELECT (dr.ddt_id = d.ddt_id)::text || ' '
         || (d.ordine_riga_id = (SELECT f.ordine_riga_id FROM vendite.ordini_righe_fulfillment f
                                   WHERE f.ddt_riga_id = d.ddt_riga_id ORDER BY f.id LIMIT 1))::text
       FROM t_def d
       JOIN vendite.ddt_righe dr ON dr.id = d.ddt_riga_id),
    'true true',
    'default: la riga punta alla riga della bolla e alla riga d''ordine del suo legame'
);

-- Fixture: una bolla del test, e un reso sopra
CREATE TEMP TABLE t_b AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('presidio reso bolla');

CREATE TEMP TABLE t_r AS
SELECT * FROM dbops.fn_pgtap_crea_reso('presidio reso bolla', (SELECT ddt_id FROM t_b), 2);

-- 4) La testata dal dominio
SELECT is(
    (SELECT (r.sorgente_uid = b.ddt_uid)::text || ' '
         || (r.destinatario_soggetto_ruolo_id = b.cliente_soggetto_ruolo_id)::text || ' '
         || (r.numero IS NOT NULL)::text
       FROM t_r x
       JOIN vendite.resi r ON r.id = x.reso_id, t_b b),
    'true true true',
    'bolla del test: il reso ne porta l''uid, il cliente e il numero li mettono i trigger'
);

-- 5) La bozza
CREATE TEMP TABLE t_bozza AS
SELECT * FROM dbops.fn_pgtap_crea_reso('presidio reso bolla', (SELECT ddt_id FROM t_b), 1,
                                       p_stato_codice_interno => 'DRAFT');

SELECT is(
    (SELECT s.codice_interno::text FROM t_bozza x
       JOIN config.stati_doc_reso s ON s.id = x.stato_doc_reso_id),
    'DRAFT',
    'DRAFT: il reso resta in bozza'
);

-- 6) La seconda riga sullo stesso reso, poi la conferma
CREATE TEMP TABLE t_riga2 AS
SELECT * FROM dbops.fn_pgtap_crea_reso('presidio reso bolla', NULL, 1,
                                       p_reso_id => (SELECT reso_id FROM t_bozza));

SELECT is(
    (SELECT (x.reso_id = z.reso_id)::text || ' ' || s.codice_interno::text || ' '
         || (SELECT count(*) FROM vendite.resi_righe rr WHERE rr.reso_id = x.reso_id)::text
       FROM t_riga2 x
       JOIN config.stati_doc_reso s ON s.id = x.stato_doc_reso_id, t_bozza z),
    'true CONFERMATO 2',
    'p_reso_id: la seconda riga si aggiunge allo stesso reso, che arriva confermato'
);

-- 7) Il tipo per codice
CREATE TEMP TABLE t_ric AS
SELECT * FROM dbops.fn_pgtap_crea_reso('presidio reso bolla', (SELECT ddt_id FROM t_b), 1,
                                       'RESO_PER_RICONSEGNA');

SELECT is(
    (SELECT t.codice_interno::text FROM t_ric x JOIN config.tipi_reso t ON t.id = x.tipo_reso_id),
    'RESO_PER_RICONSEGNA',
    'il tipo e'' quello chiesto per codice'
);

-- 8) Oltre il consegnato: non lo ferma il builder, lo ferma il guard della riga
SELECT throws_like(
    format($$SELECT dbops.fn_pgtap_crea_reso('presidio oltre', %s, 50)$$, (SELECT ddt_id FROM t_b)),
    '%superiore alla quantita consegnata residua%',
    'la quantita'' oltre il consegnato la rifiuta il guard vero (trgfn_resi_righe_guard_quantita)'
);

-- 9) Una bolla non consegnata: il guard della testata
CREATE TEMP TABLE t_emessa AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('presidio emessa', 'EMESSO');

SELECT throws_like(
    format($$SELECT dbops.fn_pgtap_crea_reso('presidio emessa', %s, 1)$$, (SELECT ddt_id FROM t_emessa)),
    '%non e'' in stato CONSEGNATO%',
    'un reso su una bolla non consegnata lo rifiuta il guard vero (trgfn_resi_guard_ddt_consegnato)'
);

-- 10) Guard: uno stato abortito
SELECT throws_like(
    $$SELECT dbops.fn_pgtap_crea_reso('presidio annullo', p_stato_codice_interno => 'ANNULLATO')$$,
    '%stato abortito%vendite.fn_annulla_reso%',
    'guard: uno stato abortito parla prima di costruire e nomina il verbo dell''annullo'
);

-- 11) Guard: la data di un reso che c'e' gia'
SELECT throws_like(
    format($$SELECT dbops.fn_pgtap_crea_reso('presidio data', p_reso_id => %s, p_data => DATE '2026-08-01')$$,
           (SELECT reso_id FROM t_bozza)),
    '%con p_reso_id la data%',
    'guard: con p_reso_id la data e'' quella del reso'
);

SELECT * FROM finish();
ROLLBACK;
