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
    $$SELECT tabella::text COLLATE "default"
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
        -- lotto C (le sorgente_* di attivita_fatturabili si ritirano), C, C
        ('vendite.attivita_fatturabili'), ('vendite.commesse_attivita'), ('vendite.commesse_sorgenti'),
        -- lotto T (testate), R (righe)
        ('vendite.contratti'), ('vendite.contratti_righe'), ('vendite.ddt'), ('vendite.ddt_righe'),
        -- lotto T (il registro dei canali si ritira)
        ('vendite.documenti_fatturazione_canali'),
        -- lotto T, R, D
        ('vendite.fatture'), ('vendite.fatture_righe'), ('vendite.fatture_stampa_coda'),
        -- lotto T, R, R, T
        ('vendite.ordini'), ('vendite.ordini_righe'), ('vendite.preventivi_righe'), ('vendite.resi')$$,
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
