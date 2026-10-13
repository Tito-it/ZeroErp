-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: il presidio di PRONTEZZA del magazzino
--   (dbops.vw_articoli_a_magazzino_prontezza, brief modifiche certe sezione 7,
--   D-L2-k). Brief: brief-db-magazzino-lotto-2-motore, sezione 4.8, sezione 7.
--
-- ⚠️ Il test COSTRUISCE lo stato: spegne gestito_a_magazzino su tutti gli
--   articoli (in transazione) per il caso NESSUNO_MARCATO, e ne costruisce
--   uno marcato per il caso MARCATI. Non dipende dalla popolazione.
-- ⛔ rev 2026-10-13: dal 20261013-48 un articolo USATO non cambia
--   gestito_a_magazzino (A-10 di brief-db-articoli-ammessi-per-documento): lo
--   spegnimento passa dalla porta amministratore, il verbo
--   catalogo.fn_articolo_correggi_struttura, come un SUPER_ADMIN costruito.
--   Per tutti, usati o no: una porta sola, e il test non sceglie per conto suo
--   quali articoli sono usati.
--
-- Elenco test (plan 6):
--   1) la vista ha UNA riga
--   2) con zero articoli marcati -> NESSUNO_MARCATO, e fn_conta_presidio = 1 (lo zero suona)
--   3) un articolo marcato ma NON attivo non conta (asserito sulla definizione)
--   4) con uno marcato e attivo -> MARCATI, e fn_conta_presidio = 0 (il pieno tace)
--   5) la riga in dbops.presidi: ZERO, colonna_stato = stato, stato_atteso = MARCATI, SETTIMANALE, LIBERO
--   6) catalogo.articoli non ha RLS: il perimetro LIBERO e' quello giusto
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(6);

SELECT is((SELECT count(*) FROM dbops.vw_articoli_a_magazzino_prontezza), 1::bigint, '1) una riga sola');

CREATE TEMP TABLE _sa AS SELECT * FROM dbops.fn_pgtap_crea_operatore_umano('pgTAP-SA-prontezza', true);
DO $spegni$
DECLARE v_id catalogo.articoli.id%TYPE;
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _sa));
    FOR v_id IN SELECT a.id FROM catalogo.articoli a WHERE a.gestito_a_magazzino LOOP
        PERFORM catalogo.fn_articolo_correggi_struttura(v_id, '{"gestito_a_magazzino": false}'::jsonb);
    END LOOP;
    PERFORM script.fn_pgtap_set_contesto_operatore();
END $spegni$;
SELECT is(
    (SELECT (stato, dbops.fn_conta_presidio('dbops.vw_articoli_a_magazzino_prontezza'))::text FROM dbops.vw_articoli_a_magazzino_prontezza),
    '(NESSUNO_MARCATO,1)',
    '2) nessun articolo marcato: NESSUNO_MARCATO, e il presidio conta 1 (lo zero suona)');

-- Un articolo marcato ma NON attivo non conta: si asserisce sulla DEFINIZIONE
-- (un articolo non nasce spento — il figlio UoM pretende il padre attivo — e
-- spegnerne uno attraversa i guard di famiglia, che non sono il soggetto).
SELECT ok(
    (SELECT pg_get_viewdef('dbops.vw_articoli_a_magazzino_prontezza'::regclass, true) LIKE '%a.gestito_a_magazzino AND a.attivo%'),
    '3) il predicato pretende gestito_a_magazzino E attivo: un marcato spento non conta');

SELECT dbops.fn_pgtap_crea_articolo('PGT-L2Z-GESTITO', true, false, false);
SELECT is(
    (SELECT (stato, n_marcati, dbops.fn_conta_presidio('dbops.vw_articoli_a_magazzino_prontezza'))::text FROM dbops.vw_articoli_a_magazzino_prontezza),
    '(MARCATI,1,0)',
    '4) un articolo marcato e attivo: MARCATI, e il presidio conta 0 (il pieno tace)');

SELECT is(
    (SELECT (natura, colonna_stato, stato_atteso, cadenza, perimetro, attivo)::text FROM dbops.presidi WHERE vista = 'dbops.vw_articoli_a_magazzino_prontezza'),
    '(ZERO,stato,MARCATI,SETTIMANALE,LIBERO,t)',
    '5) la riga di catalogo: ZERO su colonna stato con atteso MARCATI, SETTIMANALE (D-L2-k), LIBERO');
SELECT is(
    (SELECT relrowsecurity FROM pg_class WHERE oid = 'catalogo.articoli'::regclass),
    false,
    '6) catalogo.articoli non ha RLS: il perimetro LIBERO e'' quello giusto');

SELECT * FROM finish();
ROLLBACK;
