-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: la coppia apri/chiudi del giro di push commesse
--       vendite.fn_start_commessa_push_run · vendite.fn_close_commessa_push_run
--       (changeSet 20260822-68 e 20260822-69)
-- ------------------------------------------------------------
-- Indice test (1..13):
--  1) le due funzioni della coppia esistono
--  2) ⛔ fn_log_commessa_push_run NON esiste piu': la seconda porta e' chiusa
--  3) apertura: riga IN_ESECUZIONE, con run_at, dry_run e il filo del giro
--  4) chiusura con IN_ESECUZIONE -> errore di dominio (SQLSTATE)
--  5) chiusura con IN_ESECUZIONE -> e la frase dice quale stato ha rifiutato
--  6) chiusura con stato sconosciuto -> rifiuto
--  7) chiusura con stato vuoto -> rifiuto
--  8) durata negativa -> rifiuto (chiamata non valida)
--  9) p_id = 0 -> rifiuto (chiamata non valida)
-- 10) chiusura buona: stato normalizzato, durata e risultato scritti
-- 11) chi chiude senza ripetere gli handler NON cancella quelli dell'apertura
-- 12) doppia chiusura -> rifiuto, e la frase dice in che stato l'ha trovata
-- 13) ⭐ il vocabolario del CHECK e' quello che la chiusura conosce
--
-- Scopo:
--  - presidiare i due rifiuti della chiusura, che sono la ragione per cui
--    questo lotto esiste: un giro «chiuso in esecuzione» resterebbe aperto per
--    sempre, e una doppia chiusura sovrascriverebbe l'esito di un'altra corsa.
--  - ⭐ e presidiare il DISALLINEAMENTO che ha prodotto il lotto: il changeSet
--    20260822-62 allargo' chk_commesse_push_log_stato a quattro valori mentre
--    la funzione che ci scriveva ne ammetteva tre, e nessuno dei due poteva
--    accorgersene. Il test 13 e' l'unico posto in cui i due insiemi si
--    guardano in faccia: il giorno che qualcuno aggiunge un quinto stato, a
--    dirlo e' questo file e non la prima scrittura.
--
-- ⚠️ Il file precedente collaudava vendite.fn_log_commessa_push_run, che il
--   changeSet 69 ha tolto. Non e' stato adattato: e' stato riscritto, perche'
--   il soggetto e' un altro — prima era «una riga di log si scrive», ora e'
--   «un giro si apre e si chiude una volta sola».
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file sarebbe verde per sottrazione. IMMEDIATE li riporta a scattare a fine
--   di ogni istruzione. In testa e non in coda: in coda scatterebbero dopo il
--   cleanup, su righe ormai cancellate.
--   Brief: brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(13);

-- ============================================================
-- 1-2) Chi c'e' e chi non c'e' piu'
-- ============================================================
SELECT is(
  (
    SELECT count(*)::int
      FROM pg_proc p
      JOIN pg_namespace n ON n.oid = p.pronamespace
     WHERE n.nspname = 'vendite'
       AND p.proname IN ('fn_start_commessa_push_run', 'fn_close_commessa_push_run')
  ),
  2,
  '1. la coppia apri/chiudi esiste'
);

-- ⛔ Non e' un dettaglio: finche' la vecchia funzione esiste, esiste anche un
--   modo di scrivere un giro senza passare dall'apertura — cioe' senza
--   correlation_id e senza lasciare traccia se il giro si interrompe.
SELECT is(
  (
    SELECT count(*)::int
      FROM pg_proc p
      JOIN pg_namespace n ON n.oid = p.pronamespace
     WHERE n.nspname = 'vendite'
       AND p.proname = 'fn_log_commessa_push_run'
  ),
  0,
  '2. fn_log_commessa_push_run non esiste piu'': la seconda porta e'' chiusa'
);

-- ============================================================
-- 3) L'apertura
-- ============================================================
-- ⚠️ La funzione si chiama in un'istruzione SEPARATA dall'asserzione: la
--   snapshot di statement leggerebbe PRIMA delle scritture, e il rosso
--   accuserebbe la funzione invece del test.
CREATE TEMP TABLE tmp_giro_ptr AS
SELECT vendite.fn_start_commessa_push_run(
         p_dry_run        => true,
         p_source_types   => ARRAY['HandlerPreventivi', 'HandlerOrdini'],
         p_correlation_id => '0198f000-0000-7000-8000-0000000000fa'::uuid
       ) AS push_log_id;

SELECT ok(
  EXISTS (
    SELECT 1
      FROM vendite.commesse_push_log l
     WHERE l.id = (SELECT push_log_id FROM tmp_giro_ptr)
       AND l.stato          = 'IN_ESECUZIONE'
       AND l.dry_run        IS TRUE
       AND l.run_at         IS NOT NULL
       AND l.correlation_id = '0198f000-0000-7000-8000-0000000000fa'::uuid
       AND l.risultato      = '{}'::jsonb
       AND l.durata_ms      IS NULL
  ),
  '3. l''apertura crea la riga in testa: IN_ESECUZIONE, con l''ora e il filo del giro'
);

-- ============================================================
-- 4-5) IN_ESECUZIONE non chiude un giro
-- ============================================================
--   Il rifiuto piu' importante del file: un giro «chiuso in esecuzione» e' una
--   riga che nessuno riaprira' mai e che ogni conteggio leggera' come aperta.
SELECT throws_ok(
  $$ SELECT vendite.fn_close_commessa_push_run(
              (SELECT push_log_id FROM tmp_giro_ptr), 'IN_ESECUZIONE'); $$,
  'P0001',
  NULL,
  '4. chiudere con IN_ESECUZIONE solleva un errore di dominio'
);

-- ⚠️ P0001 dice «e' un errore di dominio», non QUALE: il discriminante e' la
--   frase. Il pattern non attraversa il segnaposto — dove va il valore c'e' un %.
SELECT throws_like(
  $$ SELECT vendite.fn_close_commessa_push_run(
              (SELECT push_log_id FROM tmp_giro_ptr), 'IN_ESECUZIONE'); $$,
  '%non si chiude con lo stato%IN_ESECUZIONE%',
  '5. e la frase nomina lo stato che ha rifiutato'
);

-- ============================================================
-- 6-9) Le altre quattro forme di chiamata sbagliata
-- ============================================================
SELECT throws_like(
  $$ SELECT vendite.fn_close_commessa_push_run(
              (SELECT push_log_id FROM tmp_giro_ptr), 'KO'); $$,
  '%non si chiude con lo stato%KO%',
  '6. uno stato sconosciuto e'' rifiutato come IN_ESECUZIONE'
);

SELECT throws_like(
  $$ SELECT vendite.fn_close_commessa_push_run(
              (SELECT push_log_id FROM tmp_giro_ptr), '   '); $$,
  '%non si chiude con lo stato%(vuoto)%',
  '7. uno stato vuoto e'' rifiutato, e la frase lo dice invece di mostrare il nulla'
);

SELECT throws_like(
  $$ SELECT vendite.fn_close_commessa_push_run(
              (SELECT push_log_id FROM tmp_giro_ptr), 'COMPLETATO', NULL, -1); $$,
  '%Chiamata non valida%p_durata_ms%',
  '8. una durata negativa e'' una chiamata non valida, non un dato da correggere'
);

SELECT throws_like(
  $$ SELECT vendite.fn_close_commessa_push_run(0, 'COMPLETATO'); $$,
  '%Chiamata non valida%p_id%',
  '9. p_id = 0 e'' una chiamata non valida'
);

-- ============================================================
-- 10-11) La chiusura buona
-- ============================================================
-- ⚠️ In minuscolo di proposito: la normalizzazione e' parte del contratto, e
--   il chiamante Python passa quello che ha in mano.
-- ⛔ E senza ripetere p_source_types: il test 11 verifica che gli handler
--   dichiarati all'apertura NON vengano cancellati da chi chiude.
SELECT vendite.fn_close_commessa_push_run(
         p_id        => (SELECT push_log_id FROM tmp_giro_ptr),
         p_stato     => 'completato',
         p_risultato => jsonb_build_object('HandlerPreventivi', jsonb_build_object('created', 3)),
         p_durata_ms => 1500);

SELECT ok(
  EXISTS (
    SELECT 1
      FROM vendite.commesse_push_log l
     WHERE l.id = (SELECT push_log_id FROM tmp_giro_ptr)
       AND l.stato     = 'COMPLETATO'
       AND l.durata_ms = 1500
       AND l.risultato ? 'HandlerPreventivi'
  ),
  '10. la chiusura scrive l''esito normalizzato, la durata e il risultato'
);

SELECT is(
  (
    SELECT l.source_types
      FROM vendite.commesse_push_log l
     WHERE l.id = (SELECT push_log_id FROM tmp_giro_ptr)
  ),
  ARRAY['HandlerPreventivi', 'HandlerOrdini']::text[],
  '11. chiudere senza ripetere gli handler non cancella quelli dell''apertura'
);

-- ============================================================
-- 12) La doppia chiusura
-- ============================================================
--   ⛔ Non si sovrascrive un esito gia' registrato: verrebbe da un'altra corsa,
--   e a perdersi sarebbe la storia di entrambe.
SELECT throws_like(
  $$ SELECT vendite.fn_close_commessa_push_run(
              (SELECT push_log_id FROM tmp_giro_ptr), 'ERRORE'); $$,
  '%non e'' aperto%gia'' chiuso in stato COMPLETATO%',
  '12. la doppia chiusura e'' rifiutata, e la frase dice in che stato l''ha trovata'
);

-- ============================================================
-- 13) ⭐ Il presidio del disallineamento
-- ============================================================
--   Il CHECK di tabella e la funzione che ci scrive sono due elenchi, e il
--   giorno che divergono nessuno se ne accorge: e' successo col changeSet 62,
--   che allargo' il CHECK mentre il guard della funzione restava a tre valori.
--   ⚠️ Se questo test diventa rosso NON si aggiorna l'atteso: si guarda prima
--   se vendite.fn_close_commessa_push_run sa cosa farsene del valore nuovo.
SELECT set_eq(
  $$ SELECT unnest(regexp_matches(pg_get_constraintdef(c.oid), '''([A-Z_]+)''::text', 'g'))
       FROM pg_constraint c
      WHERE c.conrelid = 'vendite.commesse_push_log'::regclass
        AND c.conname  = 'chk_commesse_push_log_stato' $$,
  ARRAY['IN_ESECUZIONE', 'COMPLETATO', 'PARZIALE', 'ERRORE'],
  '13. il vocabolario del CHECK e'' IN_ESECUZIONE piu'' i tre esiti che la chiusura conosce'
);

SELECT * FROM finish();
ROLLBACK;
