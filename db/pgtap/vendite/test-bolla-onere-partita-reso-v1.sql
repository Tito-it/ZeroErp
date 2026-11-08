-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: la riga-onere della bolla non e' merce — non ha partita, non si
--       rende, non decide RESO/CONSEGNATO, non corregge la quantita' evasa,
--       e la vista di dettaglio la dichiara.
-- (changeSet 20261103-30 … -35 — brief-db-addebito-trasporto-ordine §8.1,
--  decisioni di Tid del 2026-11-03)
-- ------------------------------------------------------------
-- Il caso, costruito: una bolla SENZA ORDINE, causale VENDITA (fatturabile),
-- con l'onere scritto a mano al numero 1 (cosi' «la prima riga» e' l'onere,
-- ed e' il bersaglio sbagliato che il builder del reso non deve prendere) e
-- la merce al numero 2.
--
-- Elenco test (plan 12):
--  1) vw_ddt_righe_dettaglio: e_onere vero sull'onere, falso sulla merce
--  2) vw_ddt_righe_dettaglio: causale_onere_id = quella dell'articolo, NULL sulla merce
--  3) in bozza, la check della correzione dice RIGA_ONERE sull'onere (primo motivo)
--  4) il verbo vendite.fn_ddt_riga_correggi_qta_evasa solleva quel motivo
--     (E_DDT_RIGA_ONERE_NON_CORREGGIBILE)
--  5) sulla merce a mano il motivo resta RIGA_NON_EVASA (il nuovo non la cattura)
--  6) consegnata, fn_partite_merce(la bolla) porta la sola riga di merce
--  7) fn_partite_merce(NULL, NULL) non porta l'onere (ramo «tutte»)
--  8) vw_partite_merce non porta l'onere
--  9) un reso sulla riga-onere e' rifiutato (E_RESO_RIGA_ONERE)
-- 10) il builder del reso, senza riga chiesta, rende la prima riga di MERCE
-- 11) il reso totale della merce porta la bolla a RESO, anche con l'onere
--     (prima: il bool_and contava l'onere, mai reso, e la bolla restava CONSEGNATO)
-- 12) l'annullo del reso la riporta a CONSEGNATO
--
-- ⚠️ Dipende da 20261103-16 (script.fn_natura_e_merce) e -17 (l'ammissione
--   degli articoli-onere sulle righe di bolla): senza -17 la riga-onere non
--   entra e il file e' rosso nella fixture.
-- ⚠️ Non coperto qui: l'onere COPIATO dall'ordine (legame di evasione con la
--   quantita' intera, 20261103-36). La check giudica la natura della riga, non
--   il legame: il motivo RIGA_ONERE vale per costruzione anche per lui, e
--   precede RIGA_NON_EVASA, DDT_SENZA_ORIGINE e LEGAMI_MULTIPLI. La prova sulla
--   copia sta col pgTAP della copia.
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli
--   (scattano al COMMIT, che qui non arriva). Brief:
--   brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: il mondo si COSTRUISCE e apre il contesto sul suo
-- operatore (OPERATORE + RLS attiva). Brief: brief-db-pgtap-runner-rls-baseline §8.
CREATE TEMP TABLE _m AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('pgTAP bolla onere');
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _m)); END $ctx$;

-- L'annullo del reso confermato chiede conferma_reso (riga CONFERMATO ->
-- ANNULLATO della matrice): e' il passo del test 12, si concede qui.
DO $az$ BEGIN
    PERFORM dbops.fn_pgtap_concedi_azione(
        NULLIF(current_setting('app.current_user_id', true), '')::integer, 'conferma_reso');
END $az$;

SELECT plan(12);

-- L'esito di un'istruzione: NULL se passa, il codice di dominio (canale
-- CONSTRAINT) se solleva P0001, altrimenti lo SQLSTATE. Discrimina il codice,
-- non la frase: P0001 da solo lo darebbe anche un altro guard.
CREATE OR REPLACE FUNCTION pg_temp.esito(p_sql text) RETURNS text
LANGUAGE plpgsql AS $$
DECLARE v_s text; v_c text;
BEGIN
    EXECUTE p_sql;
    RETURN NULL;
EXCEPTION WHEN OTHERS THEN
    GET STACKED DIAGNOSTICS v_s = RETURNED_SQLSTATE, v_c = CONSTRAINT_NAME;
    RETURN CASE WHEN v_s = 'P0001' THEN v_c ELSE v_s || ' ' || coalesce(v_c, '') END;
END $$;

-- ============================================================
-- FIXTURE
-- ============================================================
-- L'articolo-onere: quello del seed di una causale attiva (catalogo.articoli
-- e' unico per causale: uq_articoli_causale_onere); se il seed non c'e', se ne
-- costruisce uno su una causale libera. Non gestito a magazzino, natura
-- SERVIZIO_UNA_TANTUM (il guard del catalogo lo pretende).
CREATE TEMP TABLE _o AS
SELECT COALESCE(
  (SELECT a.id FROM catalogo.articoli a
     JOIN config.causali_onere c ON c.id = a.causale_onere_id
    WHERE a.attivo AND c.attivo AND NOT a.gestito_a_magazzino
    ORDER BY c.id, a.codice LIMIT 1),
  dbops.fn_pgtap_crea_articolo('PGT-ONERE-BOLLA', false,
    p_natura_vendita_id => (SELECT nv.id FROM config.nature_vendita nv
                             WHERE nv.codice_interno = 'SERVIZIO_UNA_TANTUM'),
    p_causale_onere_id  => (SELECT c.id FROM config.causali_onere c
                             WHERE c.attivo
                               AND NOT EXISTS (SELECT 1 FROM catalogo.articoli a
                                                WHERE a.causale_onere_id = c.id)
                             ORDER BY c.id LIMIT 1))) AS articolo_id;
ALTER TABLE _o ADD COLUMN causale_onere_id bigint;
UPDATE _o SET causale_onere_id = (SELECT a.causale_onere_id FROM catalogo.articoli a WHERE a.id = _o.articolo_id);

-- La bolla senza ordine IN BOZZA, con l'onere come riga 1 (prezzata: e' un
-- addebito), causale VENDITA (fatturabile: K-8 non la rifiuta).
CREATE TEMP TABLE _d AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_senza_ordine('bolla onere', 'DRAFT',
         p_billing_account_id => (SELECT billing_account_id FROM _m),
         p_quantita => 1, p_prezzo => 15,
         p_articolo_id => (SELECT articolo_id FROM _o));

-- La merce, riga 2, scritta come la scrive l'operatore.
CREATE TEMP TABLE _merce AS
SELECT dbops.fn_pgtap_crea_articolo(
         ('PGT-BOLLA-ONERE-M-' || substr(md5(clock_timestamp()::text), 1, 10))::varchar,
         false) AS articolo_id;
INSERT INTO vendite.ddt_righe (ddt_id, riga_nr, articolo_id, descrizione,
                               qta_operativa, quantita, prezzo_unitario, iva_id, meta)
SELECT d.ddt_id, 2, m.articolo_id, 'Fixture pgTAP: merce della bolla con onere',
       10, 10, 25,
       (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1),
       jsonb_build_object('test_scope', 'pgtap_bolla_onere')
  FROM _d d CROSS JOIN _merce m;

CREATE TEMP TABLE _righe AS
SELECT (SELECT ddt_riga_id FROM _d) AS onere_id,
       (SELECT r.id FROM vendite.ddt_righe r
         WHERE r.ddt_id = (SELECT ddt_id FROM _d) AND r.riga_nr = 2) AS merce_id;

-- ============================================================
-- IN BOZZA: la vista e la correzione della quantita'
-- ============================================================
SELECT is(
  (SELECT array_agg(v.e_onere ORDER BY v.riga_nr) FROM vendite.vw_ddt_righe_dettaglio v
    WHERE v.ddt_id = (SELECT ddt_id FROM _d)),
  ARRAY[true, false],
  '1) vw_ddt_righe_dettaglio: e_onere vero sulla riga-onere, falso sulla merce');

SELECT is(
  (SELECT array_agg(v.causale_onere_id ORDER BY v.riga_nr) FROM vendite.vw_ddt_righe_dettaglio v
    WHERE v.ddt_id = (SELECT ddt_id FROM _d)),
  ARRAY[(SELECT causale_onere_id FROM _o), NULL::bigint],
  '2) vw_ddt_righe_dettaglio: causale_onere_id dell''articolo sull''onere, NULL sulla merce');

SELECT is(
  (SELECT v.correggi_qta_evasa_blocco FROM vendite.vw_ddt_righe_dettaglio v
    WHERE v.id = (SELECT onere_id FROM _righe)),
  'RIGA_ONERE',
  '3) in bozza la correzione della quantita'' evasa sull''onere e'' spenta: primo motivo RIGA_ONERE');

SELECT is(
  pg_temp.esito(format('SELECT vendite.fn_ddt_riga_correggi_qta_evasa(%s, 2)',
                       (SELECT onere_id FROM _righe))),
  'E_DDT_RIGA_ONERE_NON_CORREGGIBILE',
  '4) il verbo della correzione solleva il primo motivo della check: E_DDT_RIGA_ONERE_NON_CORREGGIBILE');

SELECT is(
  (SELECT v.correggi_qta_evasa_blocco FROM vendite.vw_ddt_righe_dettaglio v
    WHERE v.id = (SELECT merce_id FROM _righe)),
  'RIGA_NON_EVASA',
  '5) sulla merce scritta a mano il motivo resta RIGA_NON_EVASA: il motivo nuovo prende solo l''onere');

-- ============================================================
-- CONSEGNATA: la partita
-- ============================================================
SELECT dbops.fn_pgtap_porta_a_stato('vendite.ddt'::regclass, (SELECT ddt_id FROM _d), 'CONSEGNATO');

SELECT is(
  (SELECT array_agg(p.ddt_riga_id ORDER BY p.ddt_riga_id)
     FROM vendite.fn_partite_merce(ARRAY[(SELECT ddt_id FROM _d)], NULL) p),
  ARRAY[(SELECT merce_id FROM _righe)],
  '6) fn_partite_merce sulla bolla: la sola riga di merce, l''onere non ha partita');

SELECT is(
  (SELECT count(*)::int FROM vendite.fn_partite_merce(NULL, NULL) p
    WHERE p.ddt_riga_id = (SELECT onere_id FROM _righe)),
  0,
  '7) fn_partite_merce(NULL, NULL), ramo «tutte»: l''onere non c''e''');

SELECT is(
  (SELECT count(*)::int FROM vendite.vw_partite_merce p
    WHERE p.ddt_riga_id = (SELECT onere_id FROM _righe)),
  0,
  '8) vw_partite_merce: l''onere non c''e''');

-- ============================================================
-- IL RESO
-- ============================================================
SELECT is(
  pg_temp.esito(format(
    $$SELECT * FROM dbops.fn_pgtap_crea_reso('reso onere', %s, 1,
                 p_stato_codice_interno => 'DRAFT', p_ddt_riga_id => %s)$$,
    (SELECT ddt_id FROM _d), (SELECT onere_id FROM _righe))),
  'E_RESO_RIGA_ONERE',
  '9) un reso sulla riga-onere e'' rifiutato: E_RESO_RIGA_ONERE');

-- Reso a credito di TUTTA la merce, confermato, senza dire la riga.
CREATE TEMP TABLE _r AS
SELECT * FROM dbops.fn_pgtap_crea_reso('reso merce', (SELECT ddt_id FROM _d), 10);

SELECT is(
  (SELECT ddt_riga_id FROM _r),
  (SELECT merce_id FROM _righe),
  '10) il builder del reso, senza riga chiesta, rende la prima riga di MERCE (non l''onere al numero 1)');

SELECT is(
  (SELECT s.codice_interno::text FROM vendite.ddt d
     JOIN config.stati_doc_ddt s ON s.id = d.stato_doc_ddt_id
    WHERE d.id = (SELECT ddt_id FROM _d)),
  'RESO',
  '11) reso totale della merce: la bolla va a RESO anche con l''onere');

SELECT vendite.fn_annulla_reso((SELECT reso_id FROM _r));

SELECT is(
  (SELECT s.codice_interno::text FROM vendite.ddt d
     JOIN config.stati_doc_ddt s ON s.id = d.stato_doc_ddt_id
    WHERE d.id = (SELECT ddt_id FROM _d)),
  'CONSEGNATO',
  '12) annullato il reso, la bolla torna a CONSEGNATO');

SELECT * FROM finish();
ROLLBACK;
