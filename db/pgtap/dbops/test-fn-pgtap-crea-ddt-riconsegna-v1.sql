-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: dbops.fn_pgtap_crea_ddt_riconsegna — la bolla di ri-consegna di fixture
-- Riferimento: brief-db-pgtap-reso-costruito §3, D-3 (changeSet 20261025-06).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - la bolla nasce dalla madre vendite.fn_genera_ddt_riconsegna e arriva
--     allo stato chiesto (default CONSEGNATO), con cio' che l'emissione pretende;
--   - tutto il reso, o una quantita' di una sua riga, alla data chiesta;
--   - le regole della ri-consegna le giudica la madre;
--   - un errore del chiamante parla, prima di costruire.
--
-- Elenco test (plan 7):
--   1) la funzione esiste con la firma dichiarata
--   2) tutto il reso: CONSEGNATA, la quantita' del reso, legata alla riga del reso
--   3) causale e indirizzi: nessun obbligatorio mancante
--   4) una parte di una riga, alla data chiesta
--   5) un reso a credito non ha niente da ri-consegnare: lo dice la madre
--   6) guard: uno stato abortito parla
--   7) guard: la quantita' senza la riga del reso parla
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: in testa. Gli helper aprono e RICHIUDONO da se' la
--   finestra dove serve (e' il loro contratto).
SET CONSTRAINTS ALL IMMEDIATE;

-- pgtap-contesto: escluso — il contesto lo apre il mondo del builder della
--   bolla, chiamato come lo chiamera' un file su un database ricostruito:
--   senza nessuna veste in sessione.

SELECT plan(7);

-- 1) La firma
SELECT has_function(
    'dbops', 'fn_pgtap_crea_ddt_riconsegna',
    ARRAY['bigint', 'character varying', 'bigint', 'numeric', 'date', 'character varying'],
    'dbops.fn_pgtap_crea_ddt_riconsegna esiste con la firma dichiarata'
);

-- Fixture: un reso per ri-consegna di 3, e la sua ri-consegna intera
CREATE TEMP TABLE t_r AS
SELECT * FROM dbops.fn_pgtap_crea_reso('presidio ri-consegna', NULL, 3, 'RESO_PER_RICONSEGNA');

CREATE TEMP TABLE t_ric AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_riconsegna((SELECT reso_id FROM t_r));

-- 2) Stato, quantita', legame
SELECT is(
    (SELECT s.codice_interno::text || ' ' || x.quantita::text || ' '
         || EXISTS (SELECT 1 FROM vendite.resi_righe_riconsegne rc
                     WHERE rc.resi_riga_id = r.resi_riga_id AND rc.ddt_riga_id = x.ddt_riga_id)::text
       FROM t_ric x
       JOIN config.stati_doc_ddt s ON s.id = x.stato_doc_ddt_id, t_r r),
    'CONSEGNATO 3.000000 true',
    'tutto il reso: bolla consegnata, 3 pezzi, legata alla riga del reso'
);

-- 3) Cio' che l'emissione pretende
SELECT is(
    (SELECT (d.causale_trasporto_id IS NOT NULL)::text || ' '
         || cardinality(script.fn_indirizzi_obbligatori_mancanti('DDT_VENDITA',
                (SELECT array_agg(di.tipo_indirizzo_id) FROM vendite.ddt_indirizzi di
                  WHERE di.ddt_id = d.id)))::text
       FROM t_ric x JOIN vendite.ddt d ON d.id = x.ddt_id),
    'true 0',
    'la bolla ha la causale e nessun indirizzo obbligatorio mancante'
);

-- 4) Una parte di una riga, alla data chiesta
CREATE TEMP TABLE t_r2 AS
SELECT * FROM dbops.fn_pgtap_crea_reso('presidio ri-consegna 2', NULL, 4, 'RESO_PER_RICONSEGNA');

CREATE TEMP TABLE t_parte AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_riconsegna((SELECT reso_id FROM t_r2),
                  p_resi_riga_id => (SELECT resi_riga_id FROM t_r2), p_quantita => 1,
                  p_data => DATE '2026-09-01');

SELECT is(
    (SELECT x.quantita::text || ' ' || d.data::text
       FROM t_parte x JOIN vendite.ddt d ON d.id = x.ddt_id),
    '1.000000 2026-09-01',
    'una parte della riga del reso (1 di 4), alla data chiesta'
);

-- 5) Le regole sono della madre
CREATE TEMP TABLE t_credito AS
SELECT * FROM dbops.fn_pgtap_crea_reso('presidio ri-consegna credito', NULL, 1);

SELECT throws_like(
    format($$SELECT dbops.fn_pgtap_crea_ddt_riconsegna(%s)$$, (SELECT reso_id FROM t_credito)),
    '%Nessuna riga di ri-consegna pendente%',
    'un reso a credito non ha niente da ri-consegnare: lo dice la madre, non il builder'
);

-- 6) Guard: uno stato abortito
SELECT throws_like(
    format($$SELECT dbops.fn_pgtap_crea_ddt_riconsegna(%s, 'ANNULLATO')$$, (SELECT reso_id FROM t_r2)),
    '%stato abortito%vendite.fn_annulla_ddt%',
    'guard: uno stato abortito parla prima di costruire e nomina il verbo dell''annullo'
);

-- 7) Guard: la quantita' vale per una riga
SELECT throws_like(
    format($$SELECT dbops.fn_pgtap_crea_ddt_riconsegna(%s, p_quantita => 1)$$, (SELECT reso_id FROM t_r2)),
    '%p_resi_riga_id e p_quantita vanno insieme%',
    'guard: la quantita'' senza la riga del reso parla'
);

SELECT * FROM finish();
ROLLBACK;
