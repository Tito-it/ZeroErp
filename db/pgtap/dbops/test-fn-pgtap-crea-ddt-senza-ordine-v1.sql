-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: dbops.fn_pgtap_crea_ddt_senza_ordine — la bolla senza ordine con la sua riga
-- Riferimento: brief-db-pgtap-reso-costruito §7.3, E-5 (changeSet 20261025-33/-34).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - la bolla nasce senza sorgente, con causale e indirizzi, e una riga che porta
--     da se' prezzo e aliquota; arriva allo stato chiesto (default CONSEGNATO);
--   - DRAFT lascia la bolla in bozza con la riga; data e causale si scelgono;
--   - la merce gestita a magazzino e lo stato abortito si rifiutano.
--
-- Elenco test (plan 8):
--   1) la funzione esiste con la firma dichiarata
--   2) default: CONSEGNATA, senza sorgente, numero dell'emissione
--   3) la riga: 10 x 25, con l'IVA, articolo costruito non gestito
--   4) causale e indirizzi: nessun obbligatorio mancante
--   5) DRAFT, data e causale scelte, cliente del test
--   6) dbops.fn_pgtap_crea_ddt: la data alla nascita (20261025-33)
--   7) guard: un articolo gestito a magazzino parla
--   8) guard: uno stato abortito parla e nomina il verbo
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: in testa. Gli helper aprono e RICHIUDONO da se' la
--   finestra dove serve (e' il loro contratto).
SET CONSTRAINTS ALL IMMEDIATE;

-- pgtap-contesto: escluso — il contesto lo apre il mondo del builder
--   esaminato, chiamato come lo chiamera' un file su un database ricostruito:
--   senza nessuna veste in sessione.

SELECT plan(8);

-- 1) La firma
SELECT has_function(
    'dbops', 'fn_pgtap_crea_ddt_senza_ordine',
    ARRAY['text', 'character varying', 'bigint', 'numeric', 'numeric', 'uuid',
          'character varying', 'date', 'bigint'],
    'dbops.fn_pgtap_crea_ddt_senza_ordine esiste con la firma dichiarata'
);

-- Fixture: la bolla di default
CREATE TEMP TABLE t_def AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_senza_ordine('presidio senza ordine');

-- 2) Stato, sorgente, numero
SELECT is(
    (SELECT s.codice_interno::text || ' ' || (d.sorgente_uid IS NULL)::text || ' ' || (d.numero IS NOT NULL)::text
       FROM t_def x
       JOIN vendite.ddt d ON d.id = x.ddt_id
       JOIN config.stati_doc_ddt s ON s.id = d.stato_doc_ddt_id),
    'CONSEGNATO true true',
    'default: bolla consegnata, senza ordine dietro, col numero dell''emissione'
);

-- 3) La riga
SELECT is(
    (SELECT r.quantita::text || ' ' || r.prezzo_unitario::text || ' ' || (r.iva_id IS NOT NULL)::text
         || ' ' || a.gestito_a_magazzino::text
       FROM t_def x
       JOIN vendite.ddt_righe r ON r.id = x.ddt_riga_id
       JOIN catalogo.articoli a ON a.id = r.articolo_id),
    '10.000000 25 true false',
    'la riga porta da se'' prezzo e aliquota, su un articolo merce non gestito'
);

-- 4) Causale e indirizzi
SELECT is(
    (SELECT c.codice::text || ' '
         || cardinality(script.fn_indirizzi_obbligatori_mancanti('DDT_VENDITA',
                (SELECT array_agg(di.tipo_indirizzo_id) FROM vendite.ddt_indirizzi di
                  WHERE di.ddt_id = d.id)))::text
       FROM t_def x
       JOIN vendite.ddt d ON d.id = x.ddt_id
       JOIN config.causali_trasporto c ON c.id = d.causale_trasporto_id),
    'VENDITA 0',
    'causale VENDITA e nessun indirizzo obbligatorio mancante'
);

-- 5) Bozza, data, causale, cliente del test
CREATE TEMP TABLE t_bozza AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_senza_ordine('presidio visione', 'DRAFT',
                  (SELECT billing_account_id FROM t_def),
                  p_causale_codice => 'CONTO_VISIONE', p_data => DATE '2026-09-01');

SELECT is(
    (SELECT s.codice_interno::text || ' ' || d.data::text || ' ' || c.codice::text
         || ' ' || (x.billing_account_id = y.billing_account_id)::text
       FROM t_bozza x
       JOIN vendite.ddt d ON d.id = x.ddt_id
       JOIN config.stati_doc_ddt s ON s.id = d.stato_doc_ddt_id
       JOIN config.causali_trasporto c ON c.id = d.causale_trasporto_id, t_def y),
    'DRAFT 2026-09-01 CONTO_VISIONE true',
    'DRAFT: bozza con la riga, alla data e con la causale chieste, sul cliente del test'
);

-- 6) La data alla nascita nel builder della testata (il builder in
--    un'istruzione, la lettura in un'altra: lo snapshot della stessa
--    istruzione non vedrebbe la bolla).
CREATE TEMP TABLE t_testata AS
SELECT dbops.fn_pgtap_crea_ddt((SELECT billing_account_id FROM t_def),
                               (SELECT cliente_soggetto_ruolo_id FROM t_def),
                               'VENDITA', NULL, NULL, DATE '2026-07-01') AS ddt_id;

SELECT is(
    (SELECT d.data FROM vendite.ddt d WHERE d.id = (SELECT ddt_id FROM t_testata)),
    DATE '2026-07-01',
    'dbops.fn_pgtap_crea_ddt: la data della bolla alla nascita (sesto parametro)'
);

-- 7) Guard: merce gestita
CREATE TEMP TABLE t_gestito AS
SELECT dbops.fn_pgtap_crea_articolo('PGT-PRES-GEST-' || substr(md5(clock_timestamp()::text), 1, 8), true) AS id;

SELECT throws_like(
    format($$SELECT dbops.fn_pgtap_crea_ddt_senza_ordine('presidio gestito', p_articolo_id => %L)$$,
           (SELECT id FROM t_gestito)),
    '%gestito a magazzino%',
    'guard: un articolo gestito a magazzino parla (la bolla muoverebbe merce)'
);

-- 8) Guard: stato abortito
SELECT throws_like(
    $$SELECT dbops.fn_pgtap_crea_ddt_senza_ordine('presidio annullo', 'ANNULLATO')$$,
    '%stato abortito%vendite.fn_annulla_ddt%',
    'guard: uno stato abortito parla prima di costruire e nomina il verbo dell''annullo'
);

SELECT * FROM finish();
ROLLBACK;
