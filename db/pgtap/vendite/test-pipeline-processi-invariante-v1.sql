-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: Fase 4.3 / 4.3-bis — armamento del task genera_scadenze_lotto
--       sullo step EMESSA e invariante sui `processi` esteso a TUTTE
--       le tappe (piano-db-satelliti-fattura §3.4 e C-7/D-C).
--
--       I test 1-3 presidiano l'armamento appena fatto; i test 4-7
--       sono l'invariante generale, scritto data-driven: si estende da
--       solo a tappe e task che oggi non esistono, invece di elencare
--       gli id di adesso. Complementare a
--       test-pipeline-definitiva-numerazione-stampa-v1.sql, che presidia
--       la sola tappa DEFINITIVA.
--
--       ⚠️ Nessun conteggio nudo: dove serve l'ordine si asserisce la
--       SEQUENZA dei nomi, che dice quale task e' comparso e se e' nel
--       posto giusto. Un `jsonb_array_length(...) = N` si romperebbe a
--       ogni aggiunta senza spiegare ne' quale ne' dove.
-- ------------------------------------------------------------
-- Indice test (1..7):
--   1)  step EMESSA MASSIVO (id 3): sequenza fondi -> fondi -> IVA -> scadenze
--   2)  step EMESSA GIORNALIERO (id 2): stessa sequenza (D-C: corsia riempita)
--   3)  ordinalita' su ENTRAMBE le corsie EMESSA: scadenze DOPO ricalcolo IVA
--   4)  invariante C-7: per ogni tappa, una sola variante distinta di processi
--   5)  nessuna pipeline attiva con processi vuoti (il difetto che D-C chiude)
--   6)  ogni task nominato nei processi esiste ed e' attivo nel registry
--   7)  ogni (pipeline, task) armato ha la sua task_policy attiva
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

SELECT plan(7);

-- ============================================================
-- 1-2) Armamento: la sequenza esatta delle due corsie EMESSA.
--      Le due corsie devono essere gemelle nei `processi`; il
--      `rollback` invece diverge apposta (D-C: la corsia immediata
--      non ha fermata, e una fattura numerata non si resetta).
-- ============================================================
SELECT is(
    (SELECT jsonb_path_query_array(processi, '$[*].task')
       FROM vendite.fatturazione_pipeline
      WHERE id = 3 AND attivo),
    '["genera_fondi_source_lotto","applica_fondi_lotto","ricalcola_iva_lotto","genera_scadenze_lotto"]'::jsonb,
    'step 3 (MASSIVO EMESSA): genera_scadenze_lotto armata in coda al ricalcolo IVA');

SELECT is(
    (SELECT jsonb_path_query_array(processi, '$[*].task')
       FROM vendite.fatturazione_pipeline
      WHERE id = 2 AND attivo),
    '["genera_fondi_source_lotto","applica_fondi_lotto","ricalcola_iva_lotto","genera_scadenze_lotto"]'::jsonb,
    'step 2 (GIORNALIERO EMESSA): corsia riempita come la massiva (D-C)');

-- ============================================================
-- 3) Ordinalita' esplicita su entrambe le corsie EMESSA.
--    La base di ripartizione delle rate e' `totale_a_pagare`, che
--    prima del ricalcolo IVA non esiste: invertire i due task
--    farebbe sollevare E_SCADENZE_BASE_NON_PRONTA su OGNI fattura.
--    Il BE ha lo stesso presidio a runtime
--    (`_TASK_ORDER_DEPENDENCIES` in pipeline_step_executor.py); qui
--    si presidia il seed, che e' cio' che quel guard legge.
--    Si contano le corsie che RISPETTANO l'ordine: cosi' una corsia
--    che perdesse del tutto uno dei due task farebbe fallire il test
--    invece di uscire dal confronto e passare per assenza.
-- ============================================================
SELECT is(
    (SELECT count(*)::int
       FROM vendite.fatturazione_pipeline p
      WHERE p.stato_doc_fiscale_id = 2
        AND p.attivo
        AND (SELECT MIN(ord) FILTER (WHERE elem ->> 'task' = 'ricalcola_iva_lotto')
                  < MIN(ord) FILTER (WHERE elem ->> 'task' = 'genera_scadenze_lotto')
               FROM jsonb_array_elements(p.processi) WITH ORDINALITY AS t(elem, ord))),
    (SELECT count(*)::int
       FROM vendite.fatturazione_pipeline
      WHERE stato_doc_fiscale_id = 2 AND attivo),
    'tappa EMESSA: su OGNI corsia genera_scadenze_lotto sta dopo ricalcola_iva_lotto');

-- ============================================================
-- 4) Invariante C-7, esteso a tutte le tappe (prima valeva solo per
--    la DEFINITIVA, test D-1 del file gemello).
--    Due corsie della stessa tappa devono eseguire lo STESSO
--    processo: se divergono, una delle due sta emettendo documenti
--    con meno lavorazione dell'altra e nessuno se ne accorge finche'
--    non la si accende. E' esattamente cio' che e' successo alla
--    corsia GIORNALIERO/EMESSA, rimasta vuota fino a D-C.
--    Data-driven: nessun id elencato, quindi copre anche le tappe
--    che verranno.
-- ============================================================
SELECT is(
    (SELECT count(*)::int
       FROM (SELECT stato_doc_fiscale_id
               FROM vendite.fatturazione_pipeline
              WHERE attivo
              GROUP BY stato_doc_fiscale_id
             HAVING count(DISTINCT processi) > 1) AS divergenti),
    0,
    'invariante C-7: nessuna tappa con corsie che eseguono processi diversi');

-- ============================================================
-- 5) Nessuna pipeline attiva con `processi` vuoti.
--    Una tappa vuota non e' una tappa che calcola meno: e' una tappa
--    che lascia passare il documento intatto. Sulla EMESSA
--    significava numerare, stampare e inviare allo SDI senza
--    riepilogo IVA ne' totali (D-C).
-- ============================================================
SELECT is(
    (SELECT count(*)::int
       FROM vendite.fatturazione_pipeline
      WHERE attivo AND jsonb_array_length(processi) = 0),
    0,
    'nessuna pipeline attiva con processi vuoti');

-- ============================================================
-- 6) Ogni task nominato nei processi esiste ed e' attivo nel
--    registry. Intercetta il refuso nel seed: un task inesistente
--    non fallisce all'apply del CSV, fallisce a giro avviato, sul
--    lotto di qualcuno.
-- ============================================================
SELECT is(
    (SELECT count(*)::int
       FROM vendite.fatturazione_pipeline p
       CROSS JOIN LATERAL jsonb_array_elements(p.processi) AS n(elem)
      WHERE p.attivo
        AND NOT EXISTS (SELECT 1
                          FROM dbops.pipeline_task_registry r
                         WHERE r.task_code = n.elem ->> 'task'
                           AND r.attivo)),
    0,
    'ogni task armato e'' registrato e attivo in dbops.pipeline_task_registry');

-- ============================================================
-- 7) Ogni (pipeline, task) armato ha la propria policy attiva.
--    Senza policy il task gira ma resta fuori da annullabilita' e
--    resume: si scopre quando un giro va storto e non si riesce a
--    ripartire, che e' il momento peggiore.
-- ============================================================
SELECT is(
    (SELECT count(*)::int
       FROM vendite.fatturazione_pipeline p
       CROSS JOIN LATERAL jsonb_array_elements(p.processi) AS n(elem)
      WHERE p.attivo
        AND NOT EXISTS (SELECT 1
                          FROM vendite.fatturazione_pipeline_task_policy tp
                         WHERE tp.pipeline_id = p.id
                           AND tp.task_code = n.elem ->> 'task'
                           AND tp.attivo)),
    0,
    'ogni (pipeline, task) armato ha la sua task_policy attiva');

SELECT * FROM finish();
ROLLBACK;
