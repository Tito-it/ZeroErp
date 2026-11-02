-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP per Zero ERP
-- Copyright (C) 2026 Tid (Michele Carlo Titini)
--
-- Rilasciato sotto GNU AGPLv3 o versione successiva.
-- Vedi LICENSE.md per il testo completo della licenza.
-- ------------------------------------------------------------
--
-- Test: il task di pipeline `consuma_plafond_lotto` — configurazione
--       (voce 1 di brief-db-richieste-aperte-dal-backend-2; `F3-b2` / `P5`
--        del piano di Fase 3)
--
-- ⛔ COSA DISCRIMINA, e non e' «il task compare nella lista».
--   Sono DUE cose, e la seconda il brief non l'aveva chiesta:
--
--     1) la POSIZIONE. Il task deve stare PRIMA di `numera_fatture`: li' la
--        fattura e' ancora sotto la soglia di congelamento e la riga si puo'
--        spezzare. Dopo, `trgfn_fattura_satellite_guard_congelamento` legge lo
--        stato VIVO e rifiuta — con un errore che parla d'altro, in un punto
--        dove nessuno lo cerca;
--
--     2) ⛔ la REGISTRAZIONE del task in `dbops.pipeline_task_registry` (+ la
--        sua implementazione). Verificato il 2026-08-31: le sole due righe di
--        JSON avrebbero fatto morire lo step a runtime con «Task non
--        registrato» — l'executor risolve l'handler via
--        `dbops.fn_get_pipeline_task_implementation`, non dalla lista.
--        E' un prerequisito che l'ordine di lavoro non nominava.
--
-- Elenco test (plan 6):
--  1) il task e' registrato a catalogo ed e' attivo
--  2) ⭐ l'handler si RISOLVE, e vale `consuma_plafond_lotto_default` — che e'
--     la chiave del `handler_registry` lato backend. Senza, lo step muore
--  3) e' presente in TUTTE le pipeline del passaggio che congela (oggi 4 e 6)
--  4) ⭐ ed e' PRIMO, prima di `numera_fatture`, su entrambe
--  5) ⚠️ il gemello negativo: NON compare in nessun altro step — ne prima
--     (si disferebbe) ne dopo (si consumerebbe due volte)
--  6) ⛔ il task NON dichiara una chiave `fn`: l'implementazione e' Python
--
-- Scopo:
--  - presidiare una configurazione che non e' codice e che nessun vincolo
--    protegge: `processi` e' una `jsonb`, e un task nel posto sbagliato o non
--    registrato non produce nessun errore finche' un lotto vero non ci passa —
--    cioe' su un documento fiscale, in produzione.
--
-- ⚠️ Questo file legge CONFIGURAZIONE (seed di 80_data e catalogo dei task),
--    che e' contratto e non popolazione: non conta righe di documenti.
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: scattano al COMMIT, e qui il COMMIT non arriva mai.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: il test gira come gira l'applicazione (OPERATORE + RLS).
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(6);

-- ============================================================
-- 1) Il task e' a catalogo
-- ============================================================
SELECT ok(
  EXISTS (SELECT 1 FROM dbops.pipeline_task_registry r
           WHERE r.task_code = 'consuma_plafond_lotto' AND r.attivo IS TRUE),
  '1) consuma_plafond_lotto e registrato in dbops.pipeline_task_registry ed e attivo');

-- ============================================================
-- 2) ⭐ E l'handler si RISOLVE — e' il passo che l'executor fa davvero
-- ============================================================
-- ⛔ E' la prova che le due righe di JSON da sole non bastavano. L'executor
--   chiama questa funzione per ogni task e poi cerca `handler_code` nel proprio
--   registro Python: senza le righe di catalogo la funzione SOLLEVA («Task non
--   registrato»), e lo step DEFINITIVA si ferma sul primo task — cioe' sul giro
--   che porta le fatture a definitiva.
-- ⚠️ Il valore atteso non e' decorativo: `consuma_plafond_lotto_default` e'
--   letteralmente la chiave di `handler_registry` in pipeline_step_executor.py.
--   Se qui uscisse un altro codice, il backend risponderebbe
--   E_TASK_IMPLEMENTATION_NOT_FOUND.
-- ⚠️ La chiamata e' GUARDATA da un EXISTS, e non e' pigrizia: la funzione
--   SOLLEVA su un task non registrato, e un raise dentro un'asserzione abortisce
--   la transazione — il file morirebbe qui e i casi 3-6 non girerebbero affatto.
--   Cosi' invece il caso diventa rosso e DICE cosa manca. Trovato con la prova
--   di mutazione, togliendo le righe di catalogo.
SELECT is(
  (SELECT CASE
            WHEN EXISTS (SELECT 1 FROM dbops.pipeline_task_registry r
                          WHERE r.task_code = 'consuma_plafond_lotto'
                            AND r.attivo IS TRUE)
            THEN (SELECT handler_code
                    FROM dbops.fn_get_pipeline_task_implementation(
                           (SELECT r.dominio_id FROM dbops.pipeline_task_registry r
                             WHERE r.task_code = 'consuma_plafond_lotto'),
                           'consuma_plafond_lotto', 'default'))
            ELSE 'TASK NON REGISTRATO A CATALOGO'
          END),
  'consuma_plafond_lotto_default',
  '2) l handler si risolve e vale consuma_plafond_lotto_default');

-- ============================================================
-- 3) Su ENTRAMBE le pipeline DEFINITIVA
-- ============================================================
-- ⚠️ Una sola sistemata darebbe un comportamento che dipende dal TIPO DI
--   LOTTO: plafond consumato sui giornalieri e non sui massivi, e nessuno se
--   ne accorgerebbe finche' i conti di un esportatore abituale non tornano.
-- ⭐ Le pipeline si scelgono per STATO e non per id: gli id 4 e 6 sono un dato
--   di seed, e un test che li scrive dentro smette di verificare il giorno che
--   se ne aggiunge una terza.
-- ⛔ E il criterio NON e' «ogni step che congela»: lo scoprii con questo stesso
--   test, che diventava rosso. Anche INVIATA congela, e li' il plafond e' gia'
--   stato consumato — riconsumarlo sarebbe il difetto. Il criterio giusto e'
--   il PRIMO stato che congela nell'ordine, cioe' il passaggio in cui il
--   congelamento AVVIENE: e' li' che le righe si possono ancora spezzare.
SELECT is(
  (SELECT count(*)::int
     FROM vendite.fatturazione_pipeline p
     JOIN config.stati_doc_fiscale s ON s.id = p.stato_doc_fiscale_id
    WHERE p.attivo IS TRUE
      AND s.id = (SELECT s2.id FROM config.stati_doc_fiscale s2
                   WHERE s2.congela_fiscale IS TRUE
                   ORDER BY s2.ordine, s2.id LIMIT 1)
      AND NOT EXISTS (
            SELECT 1 FROM jsonb_array_elements(p.processi) AS t
             WHERE t ->> 'task' = 'consuma_plafond_lotto')),
  0,
  '3) nessuna pipeline che congela e senza il task: c e su TUTTE');

-- ============================================================
-- 4) ⭐ ED E' PRIMO — la posizione e' la cosa che conta
-- ============================================================
-- ⛔ Dopo `numera_fatture` la fattura e' gia' oltre la soglia di congelamento, e
--   la spezzatura della riga verrebbe RIFIUTATA. Un test che si accontenta di
--   «il task c'e'» sarebbe verde su una pipeline che non puo' funzionare.
SELECT is(
  (SELECT count(*)::int
     FROM vendite.fatturazione_pipeline p
     JOIN config.stati_doc_fiscale s ON s.id = p.stato_doc_fiscale_id
    WHERE p.attivo IS TRUE
      AND s.id = (SELECT s2.id FROM config.stati_doc_fiscale s2
                   WHERE s2.congela_fiscale IS TRUE
                   ORDER BY s2.ordine, s2.id LIMIT 1)
      AND (SELECT min(ord) FROM jsonb_array_elements(p.processi)
                                WITH ORDINALITY AS t(el, ord)
                              WHERE t.el ->> 'task' = 'consuma_plafond_lotto')
          > (SELECT min(ord) FROM jsonb_array_elements(p.processi)
                                  WITH ORDINALITY AS t(el, ord)
                                WHERE t.el ->> 'task' = 'numera_fatture')),
  0,
  '4) il task viene PRIMA di numera_fatture su ogni pipeline che congela');

-- ============================================================
-- 5) ⚠️ IL GEMELLO NEGATIVO
-- ============================================================
-- Senza, un seed che avesse infilato il task ovunque passerebbe i casi 3 e 4.
-- Il consumo appartiene al passaggio in cui il documento CONGELA e a nessun
-- altro: prima (DRAFT, EMESSA) scriverebbe movimenti su un documento che puo'
-- ancora essere disfatto; dopo (INVIATA) li scriverebbe una seconda volta su
-- un plafond gia' consumato.
SELECT is(
  (SELECT count(*)::int
     FROM vendite.fatturazione_pipeline p
     JOIN config.stati_doc_fiscale s ON s.id = p.stato_doc_fiscale_id
    WHERE s.id <> (SELECT s2.id FROM config.stati_doc_fiscale s2
                    WHERE s2.congela_fiscale IS TRUE
                    ORDER BY s2.ordine, s2.id LIMIT 1)
      AND EXISTS (SELECT 1 FROM jsonb_array_elements(p.processi) AS t
                   WHERE t ->> 'task' = 'consuma_plafond_lotto')),
  0,
  '5) il task NON compare in nessun altro step: ne prima ne dopo');

-- ============================================================
-- 6) ⛔ NESSUNA chiave `fn`: l'implementazione e' Python
-- ============================================================
-- ⚠️ Il nome del task suona come una madre per lotto, e su questa stessa
--   pipeline e' gia' successo: `fn_generate_fatture_righe` fu scritta a DB
--   mentre l'implementazione viva era in Python, e — dice il codice —
--   «ha fatto scrivere DUE requisiti di aggregazione su codice non eseguito».
--   Un `fn` dichiarato per un task registrato a `None` viene respinto con
--   E_TASK_NOT_ALLOWED: il presidio c'e', ma e' meglio non farlo scattare.
SELECT is(
  (SELECT count(*)::int
     FROM vendite.fatturazione_pipeline p,
          LATERAL jsonb_array_elements(p.processi) AS t
    WHERE t ->> 'task' = 'consuma_plafond_lotto'
      AND t ? 'fn'),
  0,
  '6) il task non dichiara nessuna chiave fn: l implementazione e Python');

SELECT * FROM finish();

ROLLBACK;
