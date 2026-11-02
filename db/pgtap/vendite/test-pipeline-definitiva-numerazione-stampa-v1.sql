-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: attivazione (G2) del cockpit stampa fatture
--       (brief-db-processi-fatturazione-cockpit §6/§8/§9).
--       Verifica che il task stampa_documenti_lotto sia ARMATO nei
--       processi degli step DEFINITIVA (id 4 MASSIVO e 6 GIORNALIERO),
--       DOPO numera_fatture, e che le due corsie eseguano lo STESSO
--       processo (invariante D-1: mai processi duplicati/divergenti).
--       Complementare a test-stampa-coda-fondamenta-v1.sql (G1).
--
--       ⚠️ rev 2026-08-18 — I test 1-2 NON asserivano piu' l'invariante:
--       congelavano la LISTA INTERA dei processi. Il primo task legittimo
--       che si e' infilato nella tappa (popola_fatture_rettifiche, slice
--       note di credito N10) li ha fatti cadere pur essendo esattamente
--       dove il piano lo vuole. Un'asserzione che si rompe quando il
--       disegno viene rispettato non presidia il disegno: presidia il
--       minuto in cui e' stata scritta.
--       Ora asseriscono la PROIEZIONE del processo sui due task in gioco
--       — presenza, unicita' e ordine reciproco — e tollerano cio' che
--       sta in mezzo. ⚠️ La proiezione resta fail-closed: se uno dei due
--       task sparisce l'array cambia e il test cade (a differenza di un
--       test di solo ordine relativo, che tacerebbe).
-- ------------------------------------------------------------
-- Indice test (1..5):
--   1)  step DEFINITIVA MASSIVO (id 4): numera_fatture prima di stampa_documenti_lotto
--   2)  step DEFINITIVA GIORNALIERO (id 6): stessa coppia, stesso ordine
--   3)  step 4: stampa_documenti_lotto accodata DOPO numera_fatture (ordinalita')
--   4)  N10: popola_fatture_rettifiche FRA numerazione e stampa, su entrambe le corsie
--   5)  invariante D-1: una sola variante distinta di processi fra le due corsie
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

SELECT plan(5);

-- ============================================================
-- 1-2) La coppia numerazione -> stampa su entrambe le corsie DEFINITIVA.
--      Si asserisce la PROIEZIONE del processo sui due task: dice se
--      ciascuno c'e', se c'e' una volta sola e in che ordine, senza
--      pretendere di sapere cosa gli sta in mezzo.
-- ============================================================
SELECT is(
    (SELECT jsonb_agg(t.elem ->> 'task' ORDER BY t.ord)
       FROM vendite.fatturazione_pipeline p,
            jsonb_array_elements(p.processi) WITH ORDINALITY AS t(elem, ord)
      WHERE p.id = 4 AND p.attivo
        AND t.elem ->> 'task' IN ('numera_fatture', 'stampa_documenti_lotto')),
    '["numera_fatture","stampa_documenti_lotto"]'::jsonb,
    'step 4 (MASSIVO DEFINITIVA): numera_fatture seguito da stampa_documenti_lotto');

SELECT is(
    (SELECT jsonb_agg(t.elem ->> 'task' ORDER BY t.ord)
       FROM vendite.fatturazione_pipeline p,
            jsonb_array_elements(p.processi) WITH ORDINALITY AS t(elem, ord)
      WHERE p.id = 6 AND p.attivo
        AND t.elem ->> 'task' IN ('numera_fatture', 'stampa_documenti_lotto')),
    '["numera_fatture","stampa_documenti_lotto"]'::jsonb,
    'step 6 (GIORNALIERO DEFINITIVA): numera_fatture seguito da stampa_documenti_lotto');

-- ============================================================
-- 3) Ordinalita' esplicita: indice(numera) < indice(stampa) nello step 4.
--    Garanzia B-1: si stampa un documento che ha gia' il suo numero fiscale.
--    ⚠️ Deliberatamente ridondante col test 1 e da NON semplificare via: il
--    test 1 guarda la forma della proiezione, questo guarda gli indici. Su
--    un invariante fiscale due meccanismi diversi valgono piu' di uno solo.
-- ============================================================
SELECT ok(
    (SELECT MIN(ord) FILTER (WHERE elem ->> 'task' = 'numera_fatture')
          < MIN(ord) FILTER (WHERE elem ->> 'task' = 'stampa_documenti_lotto')
       FROM vendite.fatturazione_pipeline p,
            jsonb_array_elements(p.processi) WITH ORDINALITY AS t(elem, ord)
      WHERE p.id = 4 AND p.attivo),
    'step 4: stampa_documenti_lotto accodata dopo numera_fatture');

-- ============================================================
-- 4) N10 (note di credito): popola_fatture_rettifiche sta FRA la
--    numerazione e la stampa, su entrambe le corsie.
--    ⭐ Non e' una preferenza di ordine, sono due vincoli opposti che si
--    chiudono su quell'unica posizione (brief-db-note-credito-prerequisiti-be-fe P-2):
--    * DOPO numera_fatture, perche' fn_cleanup_fatture_by_ids non cancella
--      vendite.fatture_rettifiche e fk_fatture_ret_fattura non e' ON DELETE
--      CASCADE — con la proiezione scritta prima, il primo reset di lotto
--      sbatterebbe su una violazione di chiave esterna grezza. Dopo la
--      numerazione il reset non arriva piu': le tre porte sono tutte *_da_draft;
--    * PRIMA di stampa_documenti_lotto, perche' una TD04 porta
--      DatiFattureCollegate (numero e data del documento rettificato): il PDF
--      si costruisce quando il legame esiste, non prima.
--    Se il task manca su una corsia l'espressione e' NULL, la riga non entra
--    nel conteggio e il test cade: fail-closed.
-- ============================================================
SELECT is(
    (SELECT count(*)::int
       FROM vendite.fatturazione_pipeline p
      WHERE p.id IN (4, 6) AND p.attivo
        AND (SELECT MIN(ord) FILTER (WHERE elem ->> 'task' = 'numera_fatture')
                  < MIN(ord) FILTER (WHERE elem ->> 'task' = 'popola_fatture_rettifiche')
             AND MIN(ord) FILTER (WHERE elem ->> 'task' = 'popola_fatture_rettifiche')
                  < MIN(ord) FILTER (WHERE elem ->> 'task' = 'stampa_documenti_lotto')
               FROM jsonb_array_elements(p.processi) WITH ORDINALITY AS t(elem, ord))),
    2,
    'N10: popola_fatture_rettifiche fra numerazione e stampa su entrambe le corsie');

-- ============================================================
-- 5) Invariante D-1: le due corsie DEFINITIVA (stato_doc_fiscale_id=8)
--    eseguono lo STESSO processo -> una sola variante distinta.
-- ============================================================
SELECT is(
    (SELECT count(DISTINCT processi)::int
       FROM vendite.fatturazione_pipeline
      WHERE stato_doc_fiscale_id = 8 AND attivo),
    1, 'invariante D-1: nessuna asimmetria fra le due corsie DEFINITIVA');

SELECT * FROM finish();
ROLLBACK;
