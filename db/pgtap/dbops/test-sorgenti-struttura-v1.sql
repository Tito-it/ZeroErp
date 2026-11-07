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
--   monta il guard sulle sue tabelle e le TOGLIE da qui nello stesso giro; il lotto Z
--   lo trova vuoto. Una tabella nuova con la provenienza e senza il guard fa rosso:
--   non entra nel debito, entra col guard. ⛔ L'elenco non si allunga.
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
--
-- Elenco test (plan 5):
--   1) l'unica esenzione dal guard e' il log dei reconcile, col suo motivo (D-9)
--   2) le tabelle ancora senza il guard unico sono esattamente il debito dichiarato
--   3) ogni montaggio del guard unico ha argomenti validi
--   4) nessuna tabella monta il guard unico insieme a una delle due sorelle vecchie
--   5) il perimetro non e' vuoto (un presidio che esamina zero tabelle e' verde e muto)
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(5);

SELECT results_eq(
    $$SELECT tabella::text COLLATE "default", length(guard_esente_perche) >= 40
        FROM dbops.fn_sorgenti_orfane_perimetro()
       WHERE guard_esente_perche IS NOT NULL
       ORDER BY 1$$,
    $$VALUES ('pratiche.reconcile_errori', true)$$,
    '1) dal guard e'' esente solo il log dei reconcile, con il motivo scritto');

-- Il debito, per lotto. Si toglie, non si aggiunge.
SELECT results_eq(
    $$SELECT (schema_tabella || '.' || nome_tabella)::text COLLATE "default"
        FROM dbops.fn_sorgenti_orfane_perimetro()
       WHERE grammatica <> 'UNICO'
         AND guard_esente_perche IS NULL
         AND schema_tabella !~ '^pg_temp'
       ORDER BY 1$$,
    $$VALUES
        -- lotto M (acquisti e magazzino)
        ('acquisti.ddt'), ('acquisti.ddt_righe'), ('acquisti.ordini'), ('acquisti.ordini_righe'),
        -- lotto D (documenti generati, coda di stampa)
        ('documenti.documenti_generati'),
        -- lotto M
        ('magazzino.eventi_assets'), ('magazzino.inventari'), ('magazzino.movimenti'),
        ('magazzino.movimenti_attesi'), ('magazzino.rettifiche'), ('magazzino.trasferimenti'),
        -- lotto P (pratiche)
        ('pratiche.pratiche_sorgenti'),
        -- lotto D
        ('vendite.fatture_stampa_coda')$$,
    '2) le tabelle ancora senza il guard unico sono esattamente il debito dichiarato (si toglie, non si aggiunge)');

SELECT is_empty(
    $$SELECT tabella::text FROM script.fn_sorgente_guard_montaggi() WHERE NOT argomenti_validi$$,
    '3) ogni montaggio del guard unico ha argomenti validi');

SELECT is_empty(
    $$SELECT m.tabella::text
        FROM script.fn_sorgente_guard_montaggi() m
       WHERE EXISTS (SELECT 1 FROM pg_trigger tg
                      WHERE tg.tgrelid = m.tabella AND NOT tg.tgisinternal
                        AND tg.tgfoid IN ('script.trgfn_guard_sorgente_polimorfa_tipizzata()'::regprocedure,
                                          'script.trgfn_guard_sorgente_polimorfa_testuale()'::regprocedure))$$,
    '4) nessuna tabella monta il guard unico insieme a una delle sorelle vecchie');

SELECT cmp_ok(
    (SELECT count(*)::int FROM dbops.fn_sorgenti_orfane_perimetro() WHERE schema_tabella !~ '^pg_temp'),
    '>', 0,
    '5) il perimetro della provenienza non e'' vuoto');

SELECT * FROM finish();
ROLLBACK;
