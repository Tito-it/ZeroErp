-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Il presidio di STRUTTURA della provenienza polimorfa: una tabella che dice «nasce
--   da» (sorgente_tipo_id con sorgente_id o sorgente_uid) monta il guard unico
--   script.trgfn_guard_sorgente, con argomenti validi, e uno solo dei guard.
--   Brief: brief-db-sorgente-documento-e-riga §7.2 lotto 0 («Presidi»: «una tabella con
--   sorgente_id/sorgente_uid senza il guard unico e' rossa»), giro 0.2. Il perimetro e'
--   dbops.fn_sorgenti_orfane_perimetro (20261106-20).
--
-- ⭐ IL DEBITO DELLA TRANSIZIONE E' UN ELENCO CHIUSO (test 2). Ogni lotto di famiglia
--   monta il guard sulle sue tabelle e le TOGLIE da qui nello stesso giro. Una tabella
--   nuova con la provenienza e senza il guard fa rosso: non entra nel debito, entra col
--   guard. ⛔ L'elenco non si allunga.
--   ⭐ L'ELENCO FINALE del cantiere (lotto Z, giro Z.4, 2026-11-08): le quattro tabelle
--   degli acquisti, passate al cantiere degli acquisti (analisi-simmetria-ordini-acquisto
--   §4.6-bis), che le toglie da qui nel giro che porta la loro provenienza al modello.
--   Sono le sole lette dal ramo TESTUALE di dbops.fn_sorgenti_orfane (la chiave in
--   sorgente_uid, con la regola del ponte): il ramo si ritira con loro. Le due esenzioni
--   del test 1 restano fuori dal guard per ragioni proprie, non per debito.
--   rev 2026-11-06: il lotto R (20261106-57) toglie le quattro righe di vendita
--   (preventivi, ordini, bolle, contratti); fatture_righe passa al lotto C.
--   rev 2026-11-06: il lotto T, giro T.1 (20261106-61), toglie il registro dei
--   canali: la tabella non esiste piu'. Il giro T.2 (20261106-69) monta il guard
--   unico su bolla e reso.
--   rev 2026-11-07: il giro T.3 (20261106-76) monta il guard unico su ordine, contratto
--   e fattura: le testate di vendita escono tutte dal debito.
--   rev 2026-11-07: il lotto C, giro C.1, toglie attivita_fatturabili (le sue sorgente_*
--   si ritirano: esce dal perimetro) e fatture_righe (guard unico montato). Il test 2
--   legge schema e nome dal perimetro, non regclass::text, che dipende dal search_path.
--   rev 2026-11-07: il lotto D, giro D.1 (20261108-17), monta il guard unico su
--   documenti_generati; la coda di stampa perde sorgente_uid (20261108-18) ed e'
--   esente dal guard col motivo (20261108-21): la sua chiave e' una FK vera.
--   rev 2026-11-08: il lotto P, giro P.1 (20261108-86), monta il guard unico su
--   pratiche_sorgenti, che esce dal debito; il guard testuale, rimasto senza
--   montaggi, si ritira (20261108-87): il test 4 guarda la sola sorella _tipizzata.
--   rev 2026-11-09: il lotto M, giro M.1 (20261109-07), monta il guard unico sul registro di
--     magazzino: escono magazzino.movimenti e magazzino.movimenti_attesi.
--   rev 2026-11-09: il lotto M, giro M.2 (20261109-16), monta il guard unico sulle testate di
--     magazzino e sull'evento, che escono dal debito; il guard tipizzato, rimasto senza
--     montaggi, si ritira (20261109-19): il test 4 verifica che non esista piu'.
--   rev 2026-11-08: il lotto Z, giro Z.4: l'elenco finale (sopra); il test 2 dice anche la
--     grammatica, TESTUALE, che quelle quattro tabelle tengono in vita; il test 1 legge
--     schema e nome dal perimetro, non regclass::text (rosso con lo schema nel search_path
--     di chi lancia, la trappola gia' tolta al test 2).
--   rev 2026-11-08: il giro finale bis (G-4, 20261110-32) ritira le colonne sorgente_* della
--     riga di fattura (la sua origine e' la catena delle attivita'): vendite.fatture_righe esce
--     dal perimetro da sola, come attivita_fatturabili al giro C.1. Nessun test cambia.
--
-- Elenco test (plan 5):
--   1) dal guard sono esenti il log dei reconcile (D-9) e la coda di stampa (D-3), col motivo
--   2) le tabelle ancora senza il guard unico sono esattamente il debito dichiarato
--   3) ogni montaggio del guard unico ha argomenti validi
--   4) le due sorelle vecchie del guard unico (_tipizzata, _testuale) non esistono piu'
--   5) il perimetro non e' vuoto (un presidio che esamina zero tabelle e' verde e muto)
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(5);

SELECT results_eq(
    $$SELECT (schema_tabella || '.' || nome_tabella)::text COLLATE "default", length(guard_esente_perche) >= 40
        FROM dbops.fn_sorgenti_orfane_perimetro()
       WHERE guard_esente_perche IS NOT NULL
       ORDER BY 1$$,
    $$VALUES ('pratiche.reconcile_errori', true), ('vendite.fatture_stampa_coda', true)$$,
    '1) dal guard sono esenti il log dei reconcile e la coda di stampa, con il motivo scritto');

-- Il debito, per lotto. Si toglie, non si aggiunge.
SELECT results_eq(
    $$SELECT (schema_tabella || '.' || nome_tabella)::text COLLATE "default", grammatica
        FROM dbops.fn_sorgenti_orfane_perimetro()
       WHERE grammatica <> 'UNICO'
         AND guard_esente_perche IS NULL
         AND schema_tabella !~ '^pg_temp'
       ORDER BY 1$$,
    $$VALUES
        -- acquisti: passati al cantiere degli acquisti (analisi-simmetria-ordini-acquisto §4.6-bis),
        -- che li toglie da qui nel giro che porta la provenienza al modello
        ('acquisti.ddt', 'TESTUALE'), ('acquisti.ddt_righe', 'TESTUALE'),
        ('acquisti.ordini', 'TESTUALE'), ('acquisti.ordini_righe', 'TESTUALE')$$,
    '2) le tabelle ancora senza il guard unico sono esattamente il debito dichiarato (si toglie, non si aggiunge)');

SELECT is_empty(
    $$SELECT tabella::text FROM script.fn_sorgente_guard_montaggi() WHERE NOT argomenti_validi$$,
    '3) ogni montaggio del guard unico ha argomenti validi');

-- Per nome da pg_proc, non ::regprocedure: il cast sul nome di una funzione ritirata e' un errore.
SELECT is_empty(
    $$SELECT n.nspname || '.' || p.proname
        FROM pg_catalog.pg_proc p JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
       WHERE n.nspname = 'script'
         AND p.proname IN ('trgfn_guard_sorgente_polimorfa_tipizzata', 'trgfn_guard_sorgente_polimorfa_testuale')$$,
    '4) le due sorelle vecchie del guard unico (_tipizzata, _testuale) non esistono piu'': nessuna tabella le puo'' montare');

SELECT cmp_ok(
    (SELECT count(*)::int FROM dbops.fn_sorgenti_orfane_perimetro() WHERE schema_tabella !~ '^pg_temp'),
    '>', 0,
    '5) il perimetro della provenienza non e'' vuoto');

SELECT * FROM finish();
ROLLBACK;
