-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: dbops.fn_pgtap_crea_ddt_da_ordine — la bolla consegnata nata da un ordine
-- Riferimento: brief-db-pgtap-bolla-e-reso-costruiti §4.1, giro 1
--   (changeSet 20261025-01; 20261025-02 lo stato abortito; 20261025-04 la
--   data dell'ordine, D-1; 20261025-32 l'ordine dal builder dell'ordine con le
--   righe e p_righe_ordine, brief-db-pgtap-reso-costruito E-1).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - la bolla nasce dall'ordine per la madre del dominio: sorgente
--     ORDINE_VENDITA, legame fra la riga d'ordine e la riga della bolla, ordine
--     proiettato a EVASO;
--   - arriva allo stato chiesto (default CONSEGNATO) per la matrice, quindi
--     con cio' che l'emissione pretende: causale, indirizzi, numero;
--   - DRAFT lascia la bolla in bozza, per il test che le scrive qualcosa;
--   - due spedizioni dalla stessa riga: p_qta_da_evadere, poi p_ordine_id;
--   - trigger di fatturazione, data, cliente del test e causale si scelgono;
--   - un errore del chiamante parla, e prima di costruire.
--
-- Elenco test (plan 17):
--   1) la funzione esiste con la firma dichiarata
--   2) default: CONSEGNATO, sorgente ORDINE_VENDITA, numero assegnato
--   3) default: la riga tornata e' legata alla riga d'ordine tornata, quantita' 10
--   4) default: ordine EVASO (proiezione della madre), causale VENDITA,
--      nessun indirizzo obbligatorio mancante
--   5) DRAFT: la bolla resta in bozza, senza numero
--   6) prima spedizione (4 di 10): ordine PARZIALMENTE_EVASO, data della bolla scelta
--   7) seconda spedizione (p_ordine_id, 6): stessa riga d'ordine, ordine EVASO
--   8) trigger di fatturazione e cliente del test (terzo parametro)
--   9) causale scelta per codice
--  10) guard: uno stato che non esiste parla
--  11) guard: con p_ordine_id la riga non si sceglie
--  12) guard: p_righe e p_qta_da_evadere insieme parlano
--  13) guard: uno stato abortito (ANNULLATO) parla e nomina il verbo
--      (rev 20261025-02: prima moriva in fondo, dopo aver costruito)
--  14) p_data_ordine: l'ordine nasce alla data chiesta, la bolla alla sua (D-1)
--  15) guard: con p_ordine_id la data dell'ordine non si sceglie (D-1)
--  16) p_righe_ordine: l'ordine nasce con le righe chieste (sconto) e la bolla le evade
--  17) ordine con una merce e un onere: p_qta_da_evadere vale per la merce, e la riga
--      tornata e' la merce (gli oneri non contano: brief-db-revisione-dbops D71)
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: in testa. Gli helper aprono e RICHIUDONO da se' la
--   finestra dove serve (e' il loro contratto).
SET CONSTRAINTS ALL IMMEDIATE;

-- pgtap-contesto: escluso — il contesto lo apre il mondo del builder
--   esaminato, chiamato come lo chiamera' un file su un database ricostruito:
--   senza nessuna veste in sessione.

SELECT plan(17);

-- 1) La firma
SELECT has_function(
    'dbops', 'fn_pgtap_crea_ddt_da_ordine',
    ARRAY['text', 'character varying', 'bigint', 'numeric', 'numeric', 'uuid',
          'character varying', 'bigint', 'numeric', 'jsonb', 'date', 'character varying', 'date', 'jsonb'],
    'dbops.fn_pgtap_crea_ddt_da_ordine esiste con la firma dichiarata'
);

-- Fixture: la bolla di default, dal nulla
CREATE TEMP TABLE t_b AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('presidio bolla');

-- 2) Stato, sorgente, numero
SELECT is(
    (SELECT s.codice_interno::text || ' ' || so.codice_interno::text
         || ' ' || (d.sorgente_id = b.ordine_id AND d.sorgente_uid IS NULL)::text || ' ' || (d.numero IS NOT NULL)::text
       FROM t_b b
       JOIN vendite.ddt d ON d.id = b.ddt_id
       JOIN config.stati_doc_ddt s ON s.id = d.stato_doc_ddt_id
       JOIN config.sorgenti so ON so.id = d.sorgente_tipo_id),
    'CONSEGNATO ORDINE_VENDITA true true',
    'default: bolla CONSEGNATA, nata dall''ordine tornato (sorgente ORDINE_VENDITA), col numero dell''emissione'
);

-- 3) Il legame fra le due righe
SELECT is(
    (SELECT (f.ordine_riga_id = b.ordine_riga_id)::text || ' ' || f.qta_evasa::text
            || ' ' || b.quantita::text
       FROM t_b b
       JOIN vendite.ordini_righe_fulfillment f ON f.ddt_riga_id = b.ddt_riga_id),
    'true 10.000000 10.000000',
    'default: la riga della bolla evade la riga d''ordine tornata, tutta (10)'
);

-- 4) Ordine evaso, causale, indirizzi
SELECT is(
    (SELECT so.codice_interno::text || ' ' || c.codice::text || ' '
         || cardinality(script.fn_indirizzi_obbligatori_mancanti('DDT_VENDITA',
                (SELECT array_agg(di.tipo_indirizzo_id) FROM vendite.ddt_indirizzi di
                  WHERE di.ddt_id = b.ddt_id)))::text
       FROM t_b b
       JOIN vendite.ordini o ON o.id = b.ordine_id
       JOIN config.stati_doc_ordini so ON so.id = o.stato_doc_ordine_id
       JOIN vendite.ddt d ON d.id = b.ddt_id
       JOIN config.causali_trasporto c ON c.id = d.causale_trasporto_id),
    'EVASO VENDITA 0',
    'default: ordine EVASO dalla proiezione della madre, causale VENDITA, nessun indirizzo obbligatorio mancante'
);

-- 5) La bolla in bozza
CREATE TEMP TABLE t_bozza AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('presidio bozza', 'DRAFT');

SELECT is(
    (SELECT s.codice_interno::text || ' ' || (d.numero IS NULL)::text
       FROM t_bozza b
       JOIN vendite.ddt d ON d.id = b.ddt_id
       JOIN config.stati_doc_ddt s ON s.id = d.stato_doc_ddt_id),
    'DRAFT true',
    'DRAFT: la bolla resta in bozza e il numero non c''e'' ancora'
);

-- 6) Prima spedizione: 4 di 10, alla data scelta
CREATE TEMP TABLE t_s1 AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('presidio sped', p_qta_da_evadere => 4,
                                                p_data => DATE '2026-08-20');

SELECT is(
    (SELECT s1.quantita::text || ' ' || so.codice_interno::text || ' ' || d.data::text
       FROM t_s1 s1
       JOIN vendite.ddt d ON d.id = s1.ddt_id
       JOIN vendite.ordini o ON o.id = s1.ordine_id
       JOIN config.stati_doc_ordini so ON so.id = o.stato_doc_ordine_id),
    '4.000000 PARZIALMENTE_EVASO 2026-08-20',
    'prima spedizione: 4 pezzi, ordine PARZIALMENTE_EVASO, bolla alla data chiesta'
);

-- 7) Seconda spedizione dallo stesso ordine: il resto
CREATE TEMP TABLE t_s2 AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('presidio sped',
                  p_ordine_id => (SELECT ordine_id FROM t_s1), p_qta_da_evadere => 6);

SELECT is(
    (SELECT s2.quantita::text || ' ' || (s2.ordine_riga_id = s1.ordine_riga_id)::text
         || ' ' || (s2.ddt_id <> s1.ddt_id)::text || ' ' || so.codice_interno::text
       FROM t_s1 s1, t_s2 s2
       JOIN vendite.ordini o ON o.id = s2.ordine_id
       JOIN config.stati_doc_ordini so ON so.id = o.stato_doc_ordine_id),
    '6.000000 true true EVASO',
    'seconda spedizione: 6 pezzi dalla stessa riga d''ordine, bolla nuova, ordine EVASO'
);

-- 8) Trigger di fatturazione e cliente del test
CREATE TEMP TABLE t_trig AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('presidio trigger',
                  p_billing_account_id => (SELECT billing_account_id FROM t_b),
                  p_fatturazione_trigger => 'SPEDITO');

SELECT is(
    (SELECT o.fatturazione_trigger::text || ' ' || (t.billing_account_id = b.billing_account_id)::text
         || ' ' || (t.cliente_soggetto_ruolo_id = b.cliente_soggetto_ruolo_id)::text
       FROM t_trig t
       JOIN vendite.ordini o ON o.id = t.ordine_id, t_b b),
    'SPEDITO true true',
    'trigger di fatturazione scritto in bozza, e il cliente e'' quello del terzo parametro'
);

-- 9) Causale per codice
CREATE TEMP TABLE t_camp AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('presidio causale', p_causale_codice => 'CAMPIONATURA');

SELECT is(
    (SELECT c.codice::text
       FROM t_camp t
       JOIN vendite.ddt d ON d.id = t.ddt_id
       JOIN config.causali_trasporto c ON c.id = d.causale_trasporto_id),
    'CAMPIONATURA',
    'la causale e'' quella chiesta per codice'
);

-- 10) Guard: uno stato che non esiste
SELECT throws_like(
    $$SELECT dbops.fn_pgtap_crea_ddt_da_ordine('presidio stato', 'NON_ESISTE')$$,
    '%nessuno stato attivo della bolla%',
    'guard: uno stato inesistente parla, prima di costruire'
);

-- 11) Guard: con un ordine gia' costruito la riga non si sceglie
SELECT throws_like(
    format($$SELECT dbops.fn_pgtap_crea_ddt_da_ordine('presidio ordine', p_ordine_id => %s, p_quantita => 3)$$,
           (SELECT ordine_id FROM t_s1)),
    '%con p_ordine_id cliente,%',
    'guard: con p_ordine_id quantita'' e articolo sono dell''ordine, e il builder lo dice'
);

-- 12) Guard: due modi di dire la quantita'
SELECT throws_like(
    $$SELECT dbops.fn_pgtap_crea_ddt_da_ordine('presidio righe', p_qta_da_evadere => 1,
                                              p_righe => '[]'::jsonb)$$,
    '%p_righe e p_qta_da_evadere insieme%',
    'guard: p_righe e p_qta_da_evadere insieme parlano'
);

-- 13) Guard: uno stato abortito. La bolla da ordine ha i legami, e l'UPDATE
--     della matrice non li dichiara: l'annullo e' del verbo, caso del test.
SELECT throws_like(
    $$SELECT dbops.fn_pgtap_crea_ddt_da_ordine('presidio annullo', 'ANNULLATO')$$,
    '%stato abortito%vendite.fn_annulla_ddt%',
    'guard: uno stato abortito parla prima di costruire e nomina il verbo dell''annullo'
);

-- 14) La data dell'ordine (rev 20261025-04, D-1): una bolla di una data passata
--     nasce da un ordine che non e' piu' giovane di lei.
CREATE TEMP TABLE t_date AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('presidio date', p_data => DATE '2026-08-20',
                                                p_data_ordine => DATE '2026-08-05');

SELECT is(
    (SELECT o.data::text || ' ' || d.data::text
       FROM t_date t
       JOIN vendite.ordini o ON o.id = t.ordine_id
       JOIN vendite.ddt d ON d.id = t.ddt_id),
    '2026-08-05 2026-08-20',
    'p_data_ordine: l''ordine nasce alla data chiesta, la bolla alla sua'
);

-- 15) Guard: la data dell'ordine e' dell'ordine del test
SELECT throws_like(
    format($$SELECT dbops.fn_pgtap_crea_ddt_da_ordine('presidio data', p_ordine_id => %s, p_data_ordine => DATE '2026-08-01')$$,
           (SELECT ordine_id FROM t_s1)),
    '%con p_ordine_id cliente, righe, data e trigger%',
    'guard: con p_ordine_id la data dell''ordine non si passa'
);

-- 16) Le righe dell'ordine (rev 20261025-32, E-1): sconto inoltrato al
--     builder dell'ordine, e la bolla le evade tutte.
CREATE TEMP TABLE t_righe AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('presidio righe ordine',
                  p_righe_ordine => jsonb_build_array(
                      jsonb_build_object('quantita', 4, 'prezzo', 30, 'sconto_percentuale', 5),
                      jsonb_build_object('quantita', 2, 'prezzo', 10)));

SELECT is(
    (SELECT (SELECT count(*) FROM vendite.ddt_righe dr WHERE dr.ddt_id = t.ddt_id)::text || ' '
         || orr.sconto_percentuale::text
       FROM t_righe t JOIN vendite.ordini_righe orr ON orr.id = t.ordine_riga_id),
    '2 5.00',
    'p_righe_ordine: l''ordine nasce con le due righe (la prima scontata) e la bolla le evade'
);

-- 17) Merce e onere nello stesso ordine. L'onere si costruisce come nei test
--   dell'onere in bolla: una causale e un articolo di natura non merce.
CREATE TEMP TABLE t_onere_art AS
WITH caus AS (
    INSERT INTO config.causali_onere (codice_interno, codice, descrizione)
    VALUES ('PGT_DDO_ONERE', 'PGT_DDO_ONERE', 'Fixture pgTAP: onere della bolla da ordine')
    RETURNING id)
SELECT dbops.fn_pgtap_crea_articolo('PGT-DDO-ONERE', false,
         p_natura_vendita_id => (SELECT nv.id FROM config.nature_vendita nv
                                  WHERE nv.codice_interno = 'SERVIZIO_UNA_TANTUM'),
         p_causale_onere_id  => (SELECT id FROM caus)) AS onere,
       dbops.fn_pgtap_crea_articolo('PGT-DDO-MERCE', false) AS merce;

-- Il builder dentro una funzione: prima della correzione solleva, e il test
--   legge la frase invece di fermare il file.
CREATE OR REPLACE FUNCTION pg_temp.bolla_merce_e_onere() RETURNS text
LANGUAGE plpgsql AS $fx$
DECLARE
    v_esito text;
BEGIN
    SELECT CASE WHEN b.articolo_id = a.merce THEN 'merce' ELSE 'altro' END
           || ' ' || b.quantita::text
      INTO v_esito
      FROM t_onere_art a
     CROSS JOIN LATERAL dbops.fn_pgtap_crea_ddt_da_ordine('presidio onere',
                  p_righe_ordine => jsonb_build_array(
                      jsonb_build_object('articolo_id', a.merce, 'quantita', 10, 'prezzo', 5),
                      jsonb_build_object('articolo_id', a.onere, 'quantita', 1, 'prezzo', 15)),
                  p_qta_da_evadere => 4) b;
    RETURN v_esito;
EXCEPTION WHEN others THEN
    RETURN SQLERRM;
END;
$fx$;

SELECT is(
    pg_temp.bolla_merce_e_onere(),
    'merce 4.000000',
    'merce e onere: p_qta_da_evadere vale per l''unica merce, e la riga tornata e'' la merce'
);

SELECT * FROM finish();
ROLLBACK;
