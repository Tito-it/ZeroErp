-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: attivazione (G2) del cockpit stampa fatture
--       (brief-db-processi-fatturazione-cockpit §6/§8/§9).
--       Verifica che il task stampa_documenti_lotto sia ARMATO nei
--       processi degli step DEFINITIVA (id 4 MASSIVO e 6 GIORNALIERO),
--       DOPO numera_fatture, e che le due corsie eseguano lo STESSO
--       processo (invariante D-1: mai processi duplicati/divergenti).
--       Complementare a test-stampa-coda-fondamenta-v1.sql (G1).
-- ------------------------------------------------------------
-- Indice test (1..4):
--   1)  step DEFINITIVA MASSIVO (id 4): tasks = [numera_fatture, stampa_documenti_lotto]
--   2)  step DEFINITIVA GIORNALIERO (id 6): tasks = [numera_fatture, stampa_documenti_lotto]
--   3)  step 4: stampa_documenti_lotto accodata DOPO numera_fatture (ordinalita')
--   4)  invariante D-1: una sola variante distinta di processi fra le due corsie
-- ------------------------------------------------------------

BEGIN;
SELECT plan(4);

-- ============================================================
-- 1-2) Ordine dei task su entrambe le corsie DEFINITIVA
--      (numera prima, stampa dopo: si accoda un documento gia' numerato)
-- ============================================================
SELECT is(
    (SELECT jsonb_path_query_array(processi, '$[*].task')
       FROM vendite.fatturazione_pipeline
      WHERE id = 4 AND attivo),
    '["numera_fatture","stampa_documenti_lotto"]'::jsonb,
    'step 4 (MASSIVO DEFINITIVA): numera_fatture seguito da stampa_documenti_lotto');

SELECT is(
    (SELECT jsonb_path_query_array(processi, '$[*].task')
       FROM vendite.fatturazione_pipeline
      WHERE id = 6 AND attivo),
    '["numera_fatture","stampa_documenti_lotto"]'::jsonb,
    'step 6 (GIORNALIERO DEFINITIVA): numera_fatture seguito da stampa_documenti_lotto');

-- ============================================================
-- 3) Ordinalita' esplicita: indice(numera) < indice(stampa) nello step 4.
--    Garanzia B-1: si stampa un documento che ha gia' il suo numero fiscale.
-- ============================================================
SELECT ok(
    (SELECT MIN(ord) FILTER (WHERE elem ->> 'task' = 'numera_fatture')
          < MIN(ord) FILTER (WHERE elem ->> 'task' = 'stampa_documenti_lotto')
       FROM vendite.fatturazione_pipeline p,
            jsonb_array_elements(p.processi) WITH ORDINALITY AS t(elem, ord)
      WHERE p.id = 4 AND p.attivo),
    'step 4: stampa_documenti_lotto accodata dopo numera_fatture');

-- ============================================================
-- 4) Invariante D-1: le due corsie DEFINITIVA (stato_doc_fiscale_id=8)
--    eseguono lo STESSO processo -> una sola variante distinta.
-- ============================================================
SELECT is(
    (SELECT count(DISTINCT processi)::int
       FROM vendite.fatturazione_pipeline
      WHERE stato_doc_fiscale_id = 8 AND attivo),
    1, 'invariante D-1: nessuna asimmetria fra le due corsie DEFINITIVA');

SELECT * FROM finish();
ROLLBACK;
