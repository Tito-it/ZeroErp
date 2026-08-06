-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: vendite.fn_genera_scadenze_lotto — il wrapper di lotto del piano rate
--       (piano-db-satelliti-fattura.md Fase 4.2, decisioni D-F e D-Q)
-- ------------------------------------------------------------
-- Perche' questo file esiste
--   Il wrapper non calcola niente: decide CHI si lavora, cosa succede a chi
--   fallisce e come si esce da un errore. Sono tre regole che non producono
--   numeri sbagliati ma comportamenti sbagliati, e l'unico modo di presidiarle
--   e' farle accadere.
--
--   Il test che vale di piu' e' il 7: **dopo aver corretto la causa, rilanciare
--   lo stesso step deve riparare**. E' la via d'uscita prevista da D-Q, ed e'
--   anche la regressione trovata collaudando la funzione — filtrando su
--   `stato_esecuzione = 'ERRORE'`, come diceva il piano, il passo si chiudeva
--   fuori da solo: quella colonna dice «c'e' un log critico» di QUALUNQUE task,
--   quindi lo step che marcava una fattura non la guardava mai piu' e la sua
--   bandiera restava alzata per sempre. Se qualcuno rimettesse quel filtro,
--   il test 7 deve tornare rosso.
-- ------------------------------------------------------------
-- Indice test
-- 1) Fixture: un lotto con fatture lavorabili e una oltre soglia
-- 2) Guard: p_lotto_id non valido
-- 3) Guard: p_batch_size non valido
-- 4) Le fatture oltre DRAFT/EMESSA si contano in skipped_rows e non si lavorano
-- 5) Una fattura difettosa non ferma le altre
-- 6) La fattura difettosa viene marcata C, col proprio task nel meta
-- 7) Corretta la causa, il RILANCIO dello stesso step ripara e ritira la bandiera
-- 8) Un critico di un ALTRO task fa saltare la fattura
-- 9) Le segnalazioni altrui NON si ritirano
-- 10) Idempotenza di lotto: il rerun cancella e riscrive lo stesso numero di rate
-- 11) Il ciclo a fette non perde nessuno (batch_size = 1)
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ QUESTO FILE NON USA `SET CONSTRAINTS ALL IMMEDIATE`, e la ragione e' un
--   DEBITO, non una scelta di stile.
--   vendite.fatturazione_lotti e vendite.fatture hanno due guard DEFERRABLE
--   INITIALLY DEFERRED che pretendono la coerenza fra lo stato fiscale del
--   lotto e quello delle sue fatture (E_LOTTO_FATTURE_STATO_INCOERENTE). Sono
--   differiti apposta: si aggiornano lotto e fatture in qualsiasi ordine dentro
--   la stessa transazione, e la coerenza si verifica al COMMIT.
--   ⚠️ Ma qui non e' questione di «troppo presto»: MISURATO mettendo il
--   controllo in coda, cioe' dove starebbe il COMMIT, il file esegue tutte le
--   sue asserzioni e POI fallisce lo stesso — «Lotto N: fattura/e con stato
--   fiscale diverso da quello del lotto». La fixture lascia davvero un lotto
--   incoerente: e' uno stato che l'applicazione non potrebbe committare.
--   La correzione vera e' allineare lo stato delle fatture a quello del lotto
--   prima di chiudere; allora la riga si rimette e il guard viene esercitato.
--   Brief: brief-db-pgtap-runner-rls-baseline §22.

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(11);

-- ============================================================
-- 0) Fixture
-- ============================================================
-- Si parte da un lotto che contiene gia' almeno una fattura oltre soglia, cosi'
-- il filtro D-F ha qualcosa da saltare senza doverla fabbricare forzando
-- transizioni di stato (che hanno un guard loro, e attraversarlo qui vorrebbe
-- dire testare due cose insieme).
CREATE TEMP TABLE tmp_refs_gsl AS
SELECT lf.lotto_id,
       (SELECT a.id FROM vendite.attivita_fatturabili a ORDER BY a.id LIMIT 1) AS attivita_id
  FROM vendite.fatturazione_lotti_fatture lf
  JOIN vendite.fatture f ON f.id = lf.fattura_id
  JOIN config.stati_doc_fiscale s ON s.id = f.stato_doc_fiscale_id
 WHERE s.codice_interno NOT IN ('DRAFT', 'EMESSA')
 ORDER BY lf.lotto_id
 LIMIT 1;

-- Due fatture DRAFT nello stesso lotto: la seconda nasce facendo divergere la
-- chiave della prima, che e' il modo reale in cui un lotto ne contiene due.
CREATE TEMP TABLE tmp_f1_gsl AS
SELECT vendite.fn_get_or_create_fattura_header(
         (SELECT lotto_id FROM tmp_refs_gsl),
         (SELECT attivita_id FROM tmp_refs_gsl)) AS id;

UPDATE vendite.fatture
   SET termine_pagamento_id = (SELECT id FROM config.termini_pagamento WHERE codice_interno = 'TP_90G_1R'),
       totale_a_pagare = 100.00, data = DATE '2026-01-15'
 WHERE id = (SELECT id FROM tmp_f1_gsl);

CREATE TEMP TABLE tmp_f2_gsl AS
SELECT vendite.fn_get_or_create_fattura_header(
         (SELECT lotto_id FROM tmp_refs_gsl),
         (SELECT attivita_id FROM tmp_refs_gsl)) AS id;

-- La seconda resta SENZA totali: e' la fattura difettosa del giro.
UPDATE vendite.fatture
   SET termine_pagamento_id = (SELECT id FROM config.termini_pagamento WHERE codice_interno = 'TP_1RATA'),
       totale_a_pagare = NULL
 WHERE id = (SELECT id FROM tmp_f2_gsl);

SELECT ok(
  (SELECT lotto_id FROM tmp_refs_gsl) IS NOT NULL
  AND (SELECT id FROM tmp_f1_gsl) IS DISTINCT FROM (SELECT id FROM tmp_f2_gsl),
  '1) Fixture: un lotto con due fatture DRAFT distinte e almeno una oltre soglia');

-- ============================================================
-- 1) I guard sui parametri
-- ============================================================
SELECT throws_ok(
  $$ SELECT * FROM vendite.fn_genera_scadenze_lotto(0, 1000) $$,
  'P0001', NULL, '2) Guard: p_lotto_id non valido');

SELECT throws_ok(
  format($$ SELECT * FROM vendite.fn_genera_scadenze_lotto(%s, 0) $$, (SELECT lotto_id FROM tmp_refs_gsl)),
  'P0001', NULL, '3) Guard: p_batch_size non valido');

-- ============================================================
-- 2) Il giro
-- ============================================================
CREATE TEMP TABLE tmp_giro1_gsl AS
SELECT * FROM vendite.fn_genera_scadenze_lotto((SELECT lotto_id FROM tmp_refs_gsl), 1000);

-- D-F: chi e' oltre soglia non ha lavoro da fare. Non e' «lasciato indietro»,
-- e infatti si conta a parte da chi e' rotto.
SELECT ok(
  (SELECT skipped_rows FROM tmp_giro1_gsl) >= 1
  AND (SELECT count(*) FROM vendite.fatture_scadenze fs
        JOIN vendite.fatturazione_lotti_fatture lf ON lf.fattura_id = fs.fattura_id
        JOIN vendite.fatture f ON f.id = fs.fattura_id
        JOIN config.stati_doc_fiscale s ON s.id = f.stato_doc_fiscale_id
       WHERE lf.lotto_id = (SELECT lotto_id FROM tmp_refs_gsl)
         AND s.codice_interno NOT IN ('DRAFT','EMESSA')) = 0,
  '4) Le fatture oltre soglia si contano a parte e non ricevono rate');

-- D-Q: il fallimento di una non uccide il giro. La prima ha i totali e riceve
-- la sua rata, la seconda no e viene marcata.
SELECT ok(
  (SELECT failed_rows FROM tmp_giro1_gsl) >= 1
  AND (SELECT inserted_rows FROM tmp_giro1_gsl) >= 1
  AND (SELECT count(*) FROM vendite.fatture_scadenze WHERE fattura_id = (SELECT id FROM tmp_f1_gsl)) = 1,
  '5) Una fattura difettosa non ferma le altre: la sana riceve comunque le rate');

SELECT is(
  (SELECT count(*)::int FROM vendite.fatture_log
    WHERE fattura_id = (SELECT id FROM tmp_f2_gsl)
      AND status = 'C' AND disabilitato IS FALSE
      AND meta->>'task' = 'genera_scadenze_lotto'),
  1,
  '6) La fattura difettosa e marcata C, col proprio task nel meta');

-- ============================================================
-- 3) Il rilancio ripara — il test che presidia lo stallo
-- ============================================================
-- ⚠️ **La condizione va messa a mano, o il test non prova niente.** La catena
-- reale, misurata il 2026-08-01: il log critico porta subito
-- `vendite.fatture.critical = true`, ma `stato_esecuzione` resta **PENDING**
-- finche' il runner non risincronizza fra uno step e l'altro. Le due funzioni
-- di sync non servono qui — `fn_sync_fatture_log_critical_lotto` allinea il
-- flag `critical` e non lo stato di esecuzione, e `fn_sync_lotto_fatture_stato`
-- fa molto di piu': porta le fatture allo stato fiscale del LOTTO, quindi in
-- una fixture come questa sbatte (giustamente) contro il guard delle
-- transizioni. Si scrive quindi direttamente la condizione da cui il rilancio
-- deve saper uscire.
-- Senza questa riga il test passerebbe anche con il filtro sbagliato, perche'
-- lo scenario dello stallo non si formerebbe: era il difetto della prima
-- stesura di questo file.
UPDATE vendite.fatturazione_lotti_fatture
   SET stato_esecuzione = 'ERRORE'
 WHERE fattura_id = (SELECT id FROM tmp_f2_gsl);

-- Da qui in poi la fattura e' in ERRORE, esattamente come la troverebbe il
-- rilancio vero. Se il filtro tornasse a guardare `stato_esecuzione`, lo step
-- si chiuderebbe fuori da solo e il test sotto diventerebbe rosso.
UPDATE vendite.fatture SET totale_a_pagare = 50.00
 WHERE id = (SELECT id FROM tmp_f2_gsl);

CREATE TEMP TABLE tmp_giro2_gsl AS
SELECT * FROM vendite.fn_genera_scadenze_lotto((SELECT lotto_id FROM tmp_refs_gsl), 1000);

SELECT ok(
  (SELECT count(*) FROM vendite.fatture_scadenze WHERE fattura_id = (SELECT id FROM tmp_f2_gsl)) = 1
  AND (SELECT count(*) FROM vendite.fatture_log
        WHERE fattura_id = (SELECT id FROM tmp_f2_gsl)
          AND status = 'C' AND disabilitato IS FALSE
          AND meta->>'task' = 'genera_scadenze_lotto') = 0,
  '7) Corretta la causa, il rilancio dello stesso step ripara e ritira la propria bandiera');

-- ============================================================
-- 4) Le segnalazioni degli altri
-- ============================================================
INSERT INTO vendite.fatture_log (fattura_id, data_ora, messaggio, status, disabilitato, meta)
SELECT (SELECT id FROM tmp_f2_gsl), now(), 'guasto di un passo a monte', 'C', FALSE,
       jsonb_build_object('task', 'snapshot_indirizzi_lotto');

DELETE FROM vendite.fatture_scadenze WHERE fattura_id = (SELECT id FROM tmp_f2_gsl);

CREATE TEMP TABLE tmp_giro3_gsl AS
SELECT * FROM vendite.fn_genera_scadenze_lotto((SELECT lotto_id FROM tmp_refs_gsl), 1000);

SELECT ok(
  (SELECT skipped_errore_rows FROM tmp_giro3_gsl) >= 1
  AND (SELECT count(*) FROM vendite.fatture_scadenze WHERE fattura_id = (SELECT id FROM tmp_f2_gsl)) = 0,
  '8) Un critico di un ALTRO task fa saltare la fattura: non si generano rate su un documento gia dichiarato rotto');

SELECT is(
  (SELECT count(*)::int FROM vendite.fatture_log
    WHERE fattura_id = (SELECT id FROM tmp_f2_gsl)
      AND status = 'C' AND disabilitato IS FALSE
      AND meta->>'task' = 'snapshot_indirizzi_lotto'),
  1,
  '9) Le segnalazioni di un altro task restano: chi le ha alzate sa quando abbassarle');

-- ============================================================
-- 5) Idempotenza e ciclo a fette
-- ============================================================
-- Si toglie la segnalazione altrui, cosi' la fattura torna lavorabile.
UPDATE vendite.fatture_log SET disabilitato = TRUE
 WHERE fattura_id = (SELECT id FROM tmp_f2_gsl) AND meta->>'task' = 'snapshot_indirizzi_lotto';

CREATE TEMP TABLE tmp_giro4_gsl AS
SELECT * FROM vendite.fn_genera_scadenze_lotto((SELECT lotto_id FROM tmp_refs_gsl), 1000);

CREATE TEMP TABLE tmp_giro5_gsl AS
SELECT * FROM vendite.fn_genera_scadenze_lotto((SELECT lotto_id FROM tmp_refs_gsl), 1000);

SELECT is(
  (SELECT deleted_rows FROM tmp_giro5_gsl),
  (SELECT inserted_rows FROM tmp_giro4_gsl),
  '10) Idempotenza di lotto: il rerun cancella esattamente quello che il giro prima aveva scritto');

-- Con batch_size = 1 il ciclo a fette fa un giro per fattura: il risultato non
-- deve cambiare. E' il presidio dell'aritmetica delle fette, che e' l'unico
-- punto del wrapper in cui si puo' perdere per strada qualcuno.
CREATE TEMP TABLE tmp_giro6_gsl AS
SELECT * FROM vendite.fn_genera_scadenze_lotto((SELECT lotto_id FROM tmp_refs_gsl), 1);

SELECT ok(
  (SELECT fatture_count FROM tmp_giro6_gsl) = (SELECT fatture_count FROM tmp_giro5_gsl)
  AND (SELECT inserted_rows FROM tmp_giro6_gsl) = (SELECT inserted_rows FROM tmp_giro5_gsl),
  '11) batch_size = 1: il ciclo a fette lavora le stesse fatture e scrive le stesse rate');

SELECT * FROM finish();

ROLLBACK;
