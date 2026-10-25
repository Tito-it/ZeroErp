-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: dbops.fn_pgtap_fattura_attivita — le attivita' emesse con la fattura vera agganciata
-- Riferimento: brief-db-pgtap-reso-costruito §7.2, E-2 (changeSet 20261025-35).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - le attivita' del test si emettono dalla madre e ognuna si aggancia a una
--     riga di una fattura vera in bozza, con quantita' e prezzo dell'attivita';
--   - l'attivita' fatturabile si sceglie per attivita', non per segmento;
--   - col lotto: testata dalla madre, marchio e lucchetto;
--   - un errore del chiamante parla.
--
-- Elenco test (plan 8):
--   1) la funzione esiste con la firma dichiarata
--   2) una attivita': fattura in bozza, riga 10 x 25, agganciata
--   3) l'attivita' fatturabile e' quella dell'attivita' chiesta
--   4) due attivita' della stessa commessa: una fattura, due righe, nell'ordine dato
--   5) col lotto: la testata e' del lotto, l'attivita' fatturabile porta marchio e lucchetto
--   6) guard: nessuna attivita' parla
--   7) guard: un'attivita' gia' fatturata non ha piu' un'attivita' fatturabile libera
--   8) guard: attivita' di due conti diversi parlano
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: in testa. Gli helper aprono e RICHIUDONO da se' la
--   finestra dove serve (e' il loro contratto).
SET CONSTRAINTS ALL IMMEDIATE;

-- pgtap-contesto: escluso — il contesto lo apre il mondo dei builder della
--   fixture, chiamati come li chiamera' un file su un database ricostruito:
--   senza nessuna veste in sessione.

SELECT plan(8);

-- 1) La firma
SELECT has_function(
    'dbops', 'fn_pgtap_fattura_attivita',
    ARRAY['text', 'bigint[]', 'bigint'],
    'dbops.fn_pgtap_fattura_attivita esiste con la firma dichiarata'
);

-- Fixture: una bolla consegnata, la commessa del suo cliente con la sorgente
-- ROOT, due attivita' sul segmento della bolla (la seconda per la prova a due).
CREATE TEMP TABLE t_b AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('presidio fattura');

CREATE TEMP TABLE t_c AS
SELECT * FROM dbops.fn_pgtap_crea_commessa('presidio fattura', NULL,
                  (SELECT billing_account_id FROM t_b), p_con_sorgente_root => true);

CREATE TEMP TABLE t_a1 AS
SELECT * FROM dbops.fn_pgtap_crea_commessa_attivita((SELECT commessa_id FROM t_c), 25,
                  p_sorgente_codice  => 'DDT_VENDITA',
                  p_sorgente_uid     => (SELECT ddt_uid FROM t_b)::text,
                  p_sorgente_riga_id => (SELECT ddt_riga_id FROM t_b),
                  p_quantita         => 10);

CREATE TEMP TABLE t_f1 AS
SELECT * FROM dbops.fn_pgtap_fattura_attivita('presidio fattura', ARRAY[(SELECT attivita_id FROM t_a1)]);

-- 2) Fattura, riga, aggancio
SELECT is(
    (SELECT s.codice_interno::text || ' ' || fr.qta::text || ' ' || fr.prezzo_unitario::text
         || ' ' || (af.fattura_riga_id = f.fattura_riga_id)::text
       FROM t_f1 f
       JOIN vendite.fatture ft ON ft.id = f.fattura_id
       JOIN config.stati_doc_fiscale s ON s.id = ft.stato_doc_fiscale_id
       JOIN vendite.fatture_righe fr ON fr.id = f.fattura_riga_id
       JOIN vendite.attivita_fatturabili af ON af.id = f.attivita_fatturabile_id),
    'DRAFT 10.000000 25.000000 true',
    'una attivita'': fattura in bozza, riga 10 x 25, attivita'' fatturabile agganciata'
);

-- 3) L'attivita' fatturabile e' quella dell'attivita'
SELECT is(
    (SELECT af.commessa_attivita_id FROM t_f1 f
       JOIN vendite.attivita_fatturabili af ON af.id = f.attivita_fatturabile_id),
    (SELECT attivita_id FROM t_a1),
    'l''attivita'' fatturabile si sceglie per attivita'', non per segmento'
);

-- 4) Due attivita' della stessa commessa, una fattura
CREATE TEMP TABLE t_c2 AS
SELECT * FROM dbops.fn_pgtap_crea_commessa('presidio fattura due', NULL,
                  (SELECT billing_account_id FROM t_b), p_con_sorgente_root => true);

CREATE TEMP TABLE t_a2 AS
SELECT * FROM dbops.fn_pgtap_crea_commessa_attivita((SELECT commessa_id FROM t_c2), 30, p_quantita => 2);
CREATE TEMP TABLE t_a3 AS
SELECT * FROM dbops.fn_pgtap_crea_commessa_attivita((SELECT commessa_id FROM t_c2), 40, p_quantita => 1);

CREATE TEMP TABLE t_f2 AS
SELECT * FROM dbops.fn_pgtap_fattura_attivita('presidio fattura due',
                  ARRAY[(SELECT attivita_id FROM t_a3), (SELECT attivita_id FROM t_a2)]);

SELECT is(
    (SELECT count(DISTINCT f.fattura_id)::text || ' | '
         || string_agg(fr.riga_nr || ':' || fr.prezzo_unitario, ' ' ORDER BY fr.riga_nr)
       FROM t_f2 f JOIN vendite.fatture_righe fr ON fr.id = f.fattura_riga_id),
    '1 | 1:40.000000 2:30.000000',
    'due attivita'': una fattura, due righe, nell''ordine in cui il test le chiede'
);

-- 5) Col lotto
CREATE TEMP TABLE t_c3 AS
SELECT * FROM dbops.fn_pgtap_crea_commessa('presidio fattura lotto', NULL,
                  (SELECT billing_account_id FROM t_b), p_con_sorgente_root => true);
CREATE TEMP TABLE t_a4 AS
SELECT * FROM dbops.fn_pgtap_crea_commessa_attivita((SELECT commessa_id FROM t_c3), 12, p_quantita => 1);
CREATE TEMP TABLE t_l AS
SELECT * FROM dbops.fn_pgtap_crea_lotto('presidio fattura lotto', 'DRAFT', (SELECT billing_account_id FROM t_b));

CREATE TEMP TABLE t_f3 AS
SELECT * FROM dbops.fn_pgtap_fattura_attivita('presidio fattura lotto',
                  ARRAY[(SELECT attivita_id FROM t_a4)], (SELECT lotto_id FROM t_l));

SELECT is(
    (SELECT (af.lock_batch_id = l.lock_batch_id)::text || ' ' || af.lock_in_fatturazione::text
         || ' ' || (af.emit_batch_id = l.lock_batch_id)::text || ' '
         || EXISTS (SELECT 1 FROM vendite.fatturazione_lotti_fatture lf
                     WHERE lf.lotto_id = l.lotto_id AND lf.fattura_id = f.fattura_id)::text
       FROM t_f3 f
       JOIN vendite.attivita_fatturabili af ON af.id = f.attivita_fatturabile_id, t_l l),
    'true true true true',
    'col lotto: emessa col marchio del lotto, lucchetto, e la testata della madre e'' del lotto'
);

-- 6) Guard: niente da fatturare
SELECT throws_like(
    $$SELECT dbops.fn_pgtap_fattura_attivita('presidio', ARRAY[]::bigint[])$$,
    '%nessuna attivita''%',
    'guard: un elenco vuoto parla'
);

-- 7) Guard: gia' fatturata
SELECT throws_like(
    format($$SELECT dbops.fn_pgtap_fattura_attivita('presidio', ARRAY[%s]::bigint[])$$,
           (SELECT attivita_id FROM t_a1)),
    '%non ha un''attivita'' fatturabile libera%',
    'guard: un''attivita'' gia'' fatturata non si fattura due volte'
);

-- 8) Guard: due conti
CREATE TEMP TABLE t_altro AS
SELECT * FROM dbops.fn_pgtap_crea_commessa('presidio fattura altro', NULL, NULL, p_con_sorgente_root => true);
CREATE TEMP TABLE t_a5 AS
SELECT * FROM dbops.fn_pgtap_crea_commessa_attivita((SELECT commessa_id FROM t_altro), 5);

SELECT throws_like(
    format($$SELECT dbops.fn_pgtap_fattura_attivita('presidio', ARRAY[%s, %s]::bigint[])$$,
           (SELECT attivita_id FROM t_a2), (SELECT attivita_id FROM t_a5)),
    '%conti diversi%',
    'guard: attivita'' di due conti diversi non stanno in una fattura'
);

SELECT * FROM finish();
ROLLBACK;
