-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: dbops.fn_seed_elenco_colonne, la lettura degli elenchi di colonne del
--   montaggio del seed di primo impianto, e le sue due sedi di lettura.
--   Brief: brief-db-revisione-ui (giro 7, Q54: la regola del 2).
--   ChangeSet: 20_code/dbops/20261122-41 (il BB), 20_code/dbops/20261122-42 (la
--   grammatica), 20_code/script/20261122-43 (il trigger).
--
-- Elenco test (plan 8):
--   1) il BB e' IMMUTABLE e PARALLEL SAFE, come la grammatica che lo chiama
--   2) spazi (anche tab e a capo) e voci vuote tolti
--   3) l'ordine dell'elenco resta quello scritto
--   4) NULL, '' e un elenco di sole virgole danno l'array vuoto, mai NULL
--   5) la grammatica rifiuta un elenco del software NULL nella forma COLONNA
--   6) … e uno dell'installazione NULL
--   7) la grammatica legge i tre elenchi col BB: stessi array, spazi compresi
--   8) presidio sul testo: grammatica e trigger chiamano il BB, e nessuno dei due
--      ricopia la lettura (string_to_array)
--
-- ⚠️ 8 legge il testo delle due funzioni (plpgsql: prosrc e' il corpo). Dice che la
--   lettura sta in una sede sola, non che il trigger scarta le colonne giuste: quello
--   lo prova il percorso reale, ui/test-seed-primo-impianto-ui-software-v1 (casi
--   17-18, il ritiro della colonna dal preset personalizzato).
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(8);

SELECT is(
    (SELECT p.provolatile::text || p.proparallel::text
       FROM pg_proc p
      WHERE p.oid = to_regprocedure('dbops.fn_seed_elenco_colonne(text)')),
    'is',
    '1) dbops.fn_seed_elenco_colonne e'' IMMUTABLE e PARALLEL SAFE');

SELECT is(
    dbops.fn_seed_elenco_colonne(E' a , b ,,c ,\tdd\n, '),
    ARRAY['a', 'b', 'c', 'dd'],
    '2) spazi, tab, a capo e voci vuote tolti');

SELECT is(
    dbops.fn_seed_elenco_colonne('zeta,alfa,mu'),
    ARRAY['zeta', 'alfa', 'mu'],
    '3) l''ordine resta quello scritto');

SELECT is(
    format('%s|%s|%s',
           dbops.fn_seed_elenco_colonne(NULL),
           dbops.fn_seed_elenco_colonne(''),
           dbops.fn_seed_elenco_colonne(' , ,')),
    '{}|{}|{}',
    '4) NULL, vuoto e sole virgole danno l''array vuoto');

SELECT is(
    (SELECT format('%s|%s', a.valido::text, a.dettaglio)
       FROM dbops.fn_seed_primo_impianto_argomenti(ARRAY['COLONNA', NULL, 'b']) a),
    'false|forma COLONNA: i due elenchi devono essere tutti e due non vuoti',
    '5) la grammatica rifiuta un elenco del software NULL');

SELECT is(
    (SELECT format('%s|%s', a.valido::text, a.dettaglio)
       FROM dbops.fn_seed_primo_impianto_argomenti(ARRAY['COLONNA', 'a', NULL]) a),
    'false|forma COLONNA: i due elenchi devono essere tutti e due non vuoti',
    '6) la grammatica rifiuta un elenco dell''installazione NULL');

SELECT is(
    (SELECT format('%s|%s|%s', a.valido::text, a.colonne_software, a.colonne_installazione)
       FROM dbops.fn_seed_primo_impianto_argomenti(
                ARRAY['COLONNA', ' s1 ,s2,', E'i1,\ti2 , i3', ' i3 ']) a),
    format('true|%s|%s',
           dbops.fn_seed_elenco_colonne(' s1 ,s2,'),
           dbops.fn_seed_elenco_colonne(E'i1,\ti2 , i3')),
    '7) la grammatica legge gli elenchi col BB (il quarto argomento validato)');

SELECT is(
    (SELECT string_agg(format('%s:%s:%s', p.proname,
                              (p.prosrc ~ 'dbops\.fn_seed_elenco_colonne\(')::text,
                              (p.prosrc ~ 'string_to_array')::text),
                       ',' ORDER BY p.proname)
       FROM pg_proc p
      WHERE p.oid IN (to_regprocedure('dbops.fn_seed_primo_impianto_argomenti(text[])'),
                      to_regprocedure('script.trgfn_seed_primo_impianto()'))),
    'fn_seed_primo_impianto_argomenti:true:false,trgfn_seed_primo_impianto:true:false',
    '8) grammatica e trigger chiamano il BB e non ricopiano la lettura');

SELECT * FROM finish();
ROLLBACK;
