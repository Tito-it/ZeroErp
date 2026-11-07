-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
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
-- 1) Fixture: un lotto con due fatture lavorabili e nessuna oltre soglia
-- 2) Guard: p_lotto_id non valido
-- 3) Guard: p_batch_size non valido
-- 4) [skip, R-1] Le fatture oltre DRAFT/EMESSA si contano in skipped_rows e non si lavorano
-- 5) Una fattura difettosa non ferma le altre
-- 6) La fattura difettosa viene marcata C, col proprio task nel meta
-- 7) Corretta la causa, il RILANCIO dello stesso step ripara e ritira la bandiera
-- 8) Un critico di un ALTRO task fa saltare la fattura
-- 9) Le segnalazioni altrui NON si ritirano
-- 10) Idempotenza di lotto: il rerun cancella e riscrive lo stesso numero di rate
-- 11) Il ciclo a fette non perde nessuno (batch_size = 1)
-- rev 2026-10-24 (brief-modello-documento-vendita Q-2/Q-3/Q-4): il lotto, la sua
--   attivita' e la fattura oltre soglia si COSTRUISCONO. Prima si pescava «il primo
--   lotto che ha gia' una fattura oltre DRAFT/EMESSA» e «la prima attivita'»: su
--   un database ricostruito da zero non ci sono, e il file moriva nella fixture.
--   Ora commessa emittibile (dbops.fn_pgtap_crea_commessa), lotto DRAFT dalla sua
--   madre, attivita' dal PULL vero e una fattura DEFINITIVA (dbops.fn_pgtap_crea_fattura)
--   che entra nel lotto gia' FERMA (critical): il lotto e' coerente a ogni
--   istruzione, e il debito §22.4 (vincoli differiti esclusi) e' chiuso.
-- rev 2026-10-24 (brief-modello-documento-vendita R-1): esce dalla fixture la
--   fattura DEFINITIVA resa ferma dalla segnalazione 'C' di un altro task. Con
--   R-1 (Tid) quel mondo non esiste piu': una fattura in errore gia' congelata
--   non sta in un lotto non congelato (E_LOTTO_FATTURE_STATO_INCOERENTE), e nel
--   giro vero una definitiva in un lotto in bozza non si forma (dal DEFINITIVA
--   non si torna, e il ritorno del lotto in bozza cancella le fatture).
--   * Il 4 (la fattura oltre soglia saltata) diventa skip(): il ramo
--     `congela_fiscale` del wrapper e' una DIFESA DICHIARATA, NON PROVATA da
--     questo file. Resta nella funzione (Regola zero), il modello non lo
--     costruisce piu'.
--   * Attesa cambiata nel 1: il lotto ha ZERO fatture oltre soglia (era una).
--   * L'8 non dipendeva dalla definitiva (skipped_errore conta solo le
--     lavorabili): resta identico, come il resto del caso.
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   vendite.fatturazione_lotti e vendite.fatture hanno due guard DEFERRABLE
--   INITIALLY DEFERRED che pretendono la coerenza fra lo stato fiscale del
--   lotto e quello delle sue fatture (E_LOTTO_FATTURE_STATO_INCOERENTE), e qui
--   il COMMIT non arriva mai. ⭐ rev 2026-10-24: fino a ieri il file ne era
--   escluso perche' la fixture lasciava un lotto DRAFT con dentro una fattura
--   oltre soglia NON ferma, uno stato che l'applicazione non potrebbe
--   committare (brief-db-pgtap-runner-rls-baseline §22.4). Ora (R-1) il lotto
--   contiene solo fatture DRAFT come lui, e il guard si esercita.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
-- pgtap-contesto: escluso — il contesto lo apre dbops.fn_pgtap_crea_commessa (rev
--   2026-10-24), sull'operatore dell'azienda
--   che costruisce (fn_pgtap_crea_mondo_cliente, ramo «nessun contesto»).
CREATE TEMP TABLE tmp_comm_gsl AS
SELECT * FROM dbops.fn_pgtap_crea_commessa('genera scadenze lotto', 'PRONTA_FATTURAZIONE');

SELECT plan(11);

-- ============================================================
-- 0) Fixture
-- ============================================================
-- ⭐ rev 2026-10-24 (R-1): il lotto non contiene piu' una fattura oltre soglia
-- (il modello non la mette in un lotto in bozza): il filtro D-F non ha niente
-- da saltare, e il 4 e' uno skip dichiarato.
-- ⚠️ Il pull PRETENDE una sorgente ROOT. Di solito c'e' gia': il builder della
--   commessa scrive un'attivita' da un consumo, e la madre lega il consumo (il
--   primo link e' ROOT). Se manca, la scrive il test (sorgente COMMESSA, chiave =
--   id della commessa).
INSERT INTO vendite.commesse_sorgenti (commessa_id, sorgente_tipo_id, sorgente_id, ruolo_link)
SELECT c.commessa_id, s.id, c.commessa_id, 'ROOT'
  FROM tmp_comm_gsl c
  JOIN config.sorgenti s ON s.codice_interno = 'COMMESSA' AND s.attivo IS TRUE
 WHERE NOT EXISTS (SELECT 1 FROM vendite.commesse_sorgenti x
                    WHERE x.commessa_id = c.commessa_id AND x.ruolo_link = 'ROOT');

CREATE TEMP TABLE tmp_lotto_gsl AS
SELECT vendite.fn_create_fatturazione_lotto(
         p_competenza_mese             => date_trunc('month', script.fn_data_operativa())::date,
         p_tipo_doc_fiscale_id         => ca.tipo_doc_fiscale_id,
         p_billing_account_id          => c.billing_account_id,
         p_meta                        => jsonb_build_object('test', 'pgtap_genera_scadenze_lotto'),
         p_emittente_soggetto_ruolo_id => c.emittente_soggetto_ruolo_id) AS lotto_id
  FROM tmp_comm_gsl c
  JOIN vendite.commesse_attivita ca ON ca.id = c.attivita_id;

-- L'attivita' fatturabile nasce dal PULL vero, col marchio del lotto.
CREATE TEMP TABLE tmp_pull_gsl AS
SELECT * FROM vendite.fn_emit_attivita_fatturabili_da_commessa(
         p_commessa_id   => (SELECT commessa_id FROM tmp_comm_gsl),
         p_emit_batch_id => (SELECT fl.lock_batch_id FROM vendite.fatturazione_lotti fl
                              WHERE fl.id = (SELECT lotto_id FROM tmp_lotto_gsl)));

-- ⛔ Nessuna fattura oltre soglia nel lotto (rev 2026-10-24, R-1): il lotto in
--   bozza contiene solo fatture lavorabili. Vedi la riga di revisione in testa.

CREATE TEMP TABLE tmp_refs_gsl AS
SELECT l.lotto_id, af.id AS attivita_id
  FROM tmp_lotto_gsl l, vendite.attivita_fatturabili af
 WHERE af.commessa_attivita_id = (SELECT attivita_id FROM tmp_comm_gsl);

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
  AND (SELECT count(*) FROM tmp_refs_gsl) = 1
  AND (SELECT inserted_rows FROM tmp_pull_gsl) = 1
  AND (SELECT count(*) FROM vendite.fatturazione_lotti_fatture lf
         JOIN vendite.fatture f ON f.id = lf.fattura_id
         JOIN config.stati_doc_fiscale s ON s.id = f.stato_doc_fiscale_id
        WHERE lf.lotto_id = (SELECT lotto_id FROM tmp_refs_gsl)
          AND s.codice_interno NOT IN ('DRAFT', 'EMESSA')) = 0
  -- ⚠️ attesa cambiata (R-1): zero fatture oltre soglia, era una. Le due DRAFT
  --   si contano davvero nel ponte, non per sottrazione.
  AND (SELECT count(*) FROM vendite.fatturazione_lotti_fatture lf
        WHERE lf.lotto_id = (SELECT lotto_id FROM tmp_refs_gsl)
          AND lf.fattura_id IN ((SELECT id FROM tmp_f1_gsl), (SELECT id FROM tmp_f2_gsl))) = 2
  AND (SELECT id FROM tmp_f1_gsl) IS DISTINCT FROM (SELECT id FROM tmp_f2_gsl),
  '1) Fixture: un lotto con due fatture DRAFT distinte e nessuna oltre soglia');

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
-- ⛔ rev 2026-10-24 (R-1): skip dichiarato. Il ramo resta nel wrapper come
--   difesa; questo file non lo prova piu', perche' il modello non mette una
--   fattura oltre soglia in un lotto in bozza.
SELECT skip('R-1 (Tid, 2026-10-24): una fattura definitiva non convive con una in errore nello stesso lotto; il ramo che la salta resta come difesa e il modello non lo costruisce piu''', 1);

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
