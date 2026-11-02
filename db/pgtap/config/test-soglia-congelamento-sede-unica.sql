-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: la soglia di congelamento fiscale ha UNA sede sola
--       brief-db-be-iva-risolutore-e-regime-cliente, `D33` (coda di `I10`)
-- ------------------------------------------------------------
-- A cosa serve, in una frase
--   «Da che punto in poi un documento fiscale non si tocca piu'» e' UNA
--   domanda. Questo file impedisce che torni ad avere otto risposte.
--
-- ⭐ COM'ERA, e perche' e' cambiato
--   Fino al 2026-08-30 la regola viveva come `NOT IN ('DRAFT','EMESSA')`
--   scritta nel corpo di OTTO funzioni. `I10` aveva creato la colonna
--   `config.stati_doc_fiscale.congela_fiscale` proprio per toglierle, ma
--   l'aveva collegata a UN solo lettore: le altre sette continuavano a
--   portarsi la lista, e sette copie non danno errore se ci si dimentica di
--   aggiornarle.
--
-- ⚠️ E le due copie peggiori erano LE GUARDIE DI CONGELAMENTO. Una guardia
--   che usa una definizione di «congelato» diversa da quella di chi ricalcola
--   lascia il documento congelato per meta' sistema e scrivibile per l'altra —
--   senza un errore, senza una riga di log.
--
-- ⛔ COME SI REAGISCE A UN ROSSO SUL TEST 1
--   Non si aggiunge la funzione a un'eccezione. Si porta a leggere la colonna.
--   Se davvero risponde a un'altra domanda — e puo' succedere: «non ancora
--   numerato» NON e' per sempre lo stesso di «congelato» — allora quella
--   domanda vuole una colonna sua, non una lista di codici.
--
-- Indice test
-- 1) ⭐ Nessuna funzione porta piu' la lista di codici (e se lo fa, la NOMINA)
-- 2) Le funzioni che governano la soglia leggono davvero la colonna
-- 3) ⭐ Il guard SEGUE la colonna: spostarla ne cambia il comportamento
-- 4) ⛔ E la segue anche al contrario: rimessa, la scrittura torna possibile
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Brief: brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: RLS attiva, come gira l'applicazione.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(4);

-- ============================================================
-- 1) ⭐ La domanda che questo file esiste per porre
-- ============================================================
-- ⚠️ Si guardano solo le righe ESEGUIBILI: i commenti che CITANO la vecchia
--   forma sono documentazione, e diverse funzioni la citano di proposito per
--   spiegare cos'e' cambiato. Un test che contasse anche quelle sarebbe rosso
--   per sempre, e chi lo «aggiusta» finirebbe per cancellare le spiegazioni.
SELECT is(
  (SELECT count(*)
     FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname IN ('vendite', 'script')
      AND EXISTS (SELECT 1 FROM regexp_split_to_table(p.prosrc, E'\n') AS riga
                   WHERE riga ~ 'NOT IN \(''DRAFT'', ?''EMESSA''\)'
                     AND btrim(riga) !~ '^--')),
  0::bigint,
  '1) nessuna funzione porta piu la lista di codici nel corpo: '
  || COALESCE((SELECT string_agg(n.nspname || '.' || p.proname, ', ' ORDER BY p.proname)
                 FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
                WHERE n.nspname IN ('vendite', 'script')
                  AND EXISTS (SELECT 1 FROM regexp_split_to_table(p.prosrc, E'\n') AS riga
                               WHERE riga ~ 'NOT IN \(''DRAFT'', ?''EMESSA''\)'
                                 AND btrim(riga) !~ '^--')),
              'nessuna'));

-- ============================================================
-- 2) L'altro verso: la colonna deve essere LETTA
-- ============================================================
-- ⚠️ Senza questo, il test 1 diventerebbe verde anche cancellando la soglia da
--   una funzione invece che portandola sulla colonna — cioe' togliendo una
--   difesa invece di spostarla. E' la stessa forma del «test che conta i
--   cattivi»: sparisce il difetto dal conteggio, non dal sistema.
-- ⚠️ L'elenco e' ESPLICITO e non un `LIKE`: e' la seconda firma, e dice quali
--   funzioni ci si aspetta che governino questa soglia.
-- ⭐ rev 2026-08-30 (`D34`): erano OTTO, sono SETTE.
--   `trgfn_fatture_righe_guard_congelamento` non c'e' piu' — non e' stata
--   dimenticata, e' stata **riassorbita** dalla guardia generica, che ora prende
--   anche il codice errore come argomento. Le righe di fattura restano
--   protette: le protegge `trgfn_fattura_satellite_guard_congelamento`, che e'
--   in elenco. ⚠️ Che la fusione non abbia perso il codice errore specifico lo
--   verifica `db/pgtap/vendite/test-guard-congelamento-fusione-v1.sql`: questo
--   file guarda la SOGLIA, quello guarda la FUSIONE.
SELECT is(
  (SELECT count(*)
     FROM (VALUES ('vendite', 'fn_ricalcola_riepilogo_iva_fattura'),
                  ('vendite', 'trgfn_fattura_satellite_guard_congelamento'),
                  ('vendite', 'fn_genera_scadenze_fattura'),
                  ('vendite', 'fn_genera_scadenze_lotto'),
                  ('vendite', 'fn_snapshot_fattura_lotto'),
                  ('script',  'fn_check_fattura_eliminabile_da_lotto'),
                  ('script',  'fn_check_lotto_riportabile_a_draft')) AS att(sch, fn)
    WHERE NOT EXISTS (
            SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
             WHERE n.nspname = att.sch AND p.proname = att.fn
               AND p.prosrc ~ 'congela_fiscale')),
  0::bigint,
  '2) le sette funzioni della soglia leggono davvero congela_fiscale: '
  || COALESCE((SELECT string_agg(att.sch || '.' || att.fn, ', ' ORDER BY att.fn)
                 FROM (VALUES ('vendite', 'fn_ricalcola_riepilogo_iva_fattura'),
                              ('vendite', 'trgfn_fattura_satellite_guard_congelamento'),
                              ('vendite', 'fn_genera_scadenze_fattura'),
                              ('vendite', 'fn_genera_scadenze_lotto'),
                              ('vendite', 'fn_snapshot_fattura_lotto'),
                              ('script',  'fn_check_fattura_eliminabile_da_lotto'),
                              ('script',  'fn_check_lotto_riportabile_a_draft')) AS att(sch, fn)
                WHERE NOT EXISTS (
                        SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
                         WHERE n.nspname = att.sch AND p.proname = att.fn
                           AND p.prosrc ~ 'congela_fiscale')),
              'tutte'));

-- ============================================================
-- La materia per i due casi di comportamento
-- ============================================================
-- ⚠️ NON si sposta lo stato della fattura: `vendite.fatture` ha un guard di
--   transizione, e forzarlo proverebbe quello invece di questo. Si sposta la
--   COLONNA sullo stato che la fattura ha gia' — ed e' esattamente la
--   dimostrazione che serve: se il guard cambia idea, sta leggendo la colonna.
CREATE TEMP TABLE tmp_soglia AS
SELECT r.id AS riga_id, f.stato_doc_fiscale_id AS stato_id, s.codice_interno
  FROM vendite.fatture f
  JOIN vendite.fatture_righe r      ON r.fattura_id = f.id
  JOIN config.stati_doc_fiscale s   ON s.id = f.stato_doc_fiscale_id
 WHERE s.congela_fiscale IS FALSE
 ORDER BY f.id, r.id
 LIMIT 1;

-- ============================================================
-- 3) ⭐ Il guard SEGUE la colonna
-- ============================================================
-- ⛔ E' il caso che distingue «legge la colonna» da «per caso oggi la lista dice
--   la stessa cosa». Senza, i test 1 e 2 sarebbero verdi anche con un guard che
--   nomina `congela_fiscale` in un commento e decide su altro.
UPDATE config.stati_doc_fiscale SET congela_fiscale = true
 WHERE id = (SELECT stato_id FROM tmp_soglia);

SELECT throws_ok(
  format('UPDATE vendite.fatture_righe SET descrizione = descrizione WHERE id = %s',
         (SELECT riga_id FROM tmp_soglia)),
  'P0001',
  NULL,
  '3) spostata la colonna a true, il guard RIFIUTA: la soglia viene da li'
);

-- ============================================================
-- 4) ⛔ E la segue anche al contrario
-- ============================================================
-- ⚠️ Un guard che blocca sempre passerebbe il test 3. Questo e' il gemello che
--   lo smaschera: la soglia deve SEGUIRE il dato, non essere un muro fisso.
UPDATE config.stati_doc_fiscale SET congela_fiscale = false
 WHERE id = (SELECT stato_id FROM tmp_soglia);

SELECT lives_ok(
  format('UPDATE vendite.fatture_righe SET descrizione = descrizione WHERE id = %s',
         (SELECT riga_id FROM tmp_soglia)),
  '4) rimessa a false, la riga torna scrivibile: la soglia SEGUE il dato'
);

SELECT * FROM finish();

ROLLBACK;
