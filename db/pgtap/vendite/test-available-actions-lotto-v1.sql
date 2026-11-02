-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: capability del lotto di fatturazione e sorgente unica delle
--       precondizioni (risposta-db-azioni-lista-lotto.md §3)
-- ------------------------------------------------------------
-- Cosa presidia questo file
--   Che il pulsante e la funzione dicano la STESSA cosa. E' il difetto
--   che il 2026-07-31 ha prodotto in-app il vicolo cieco di «Annulla
--   lotto» — visibile da EMESSA in poi, dove fn_annulla_lotto_da_draft
--   rifiuta — e che allora fu tappato ricopiando la precondizione in
--   Vue. Da qui in avanti la precondizione e' UNA:
--
--     script.fn_check_lotto_annullabile          -> la solleva fn_annulla_lotto_da_draft
--                                                -> la espone  fn_available_actions_lotto
--     script.fn_check_lotto_riportabile_a_draft  -> idem per fn_riporta_lotto_a_draft
--
-- 🔴 I TEST CHE VALGONO DI PIU' SONO L'11 E IL 12.
--   Gli altri verificano che le capability abbiano la FORMA giusta. Gli
--   ultimi due verificano l'unica cosa che conta davvero: che dove il
--   check dice NO, la funzione di mutazione SOLLEVI — cioe' che i due
--   consumatori della stessa regola non possano divergere. Un file che
--   testasse solo il jsonb sarebbe verde anche il giorno in cui qualcuno
--   rimettesse una precondizione a mano dentro la fn di mutazione.
--
-- ⚠️ FIXTURE SCELTE, NON COSTRUITE, e detto invece che nascosto.
--   Un lotto con fatture e attivita' agganciate e' il prodotto di due
--   step di pipeline: non si fabbrica in un pgTAP senza riscrivere la
--   pipeline. Il file SCEGLIE lotti reali per stato e lavora dentro
--   BEGIN/ROLLBACK. Dove il DB non ha un lotto in quello stato il test
--   si SALTA invece di fallire: un rosso da assenza di dati non dice
--   niente a nessuno. I test 1-5 sono strutturali e girano sempre.
-- ------------------------------------------------------------
-- Indice test
-- 1) Seed: i tre verbi di stato del lotto hanno action_key/label_key in matrice
-- 2) Seed: DRAFT -> EMESSA (l avanzamento pipeline) NON e un azione manuale
-- 3) Le quattro funzioni nuove esistono
-- 4) Capability su lotto inesistente: NULL (contratto delle sorelle)
-- 5) Le fn_check rifiutano un lotto_id invalido
-- 6) Lotto DRAFT: la capability espone annulla e non numera
-- 7) Lotto DRAFT: enabled di annulla coincide col verdetto della fn_check
-- 8) Lotto EMESSA: la capability espone numera e riporta_a_draft
-- 9) Lotto EMESSA: enabled di riporta_a_draft coincide col verdetto della fn_check
-- 10) Lotto DEFINITIVA: solo ristampa, can_change_state falso
-- 11) Equivalenza check <-> mutazione (annulla)   <-- il test che vale
-- 12) Equivalenza check <-> mutazione (riporta)   <-- il test che vale
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

SELECT plan(12);

-- ============================================================
-- Strutturali (girano sempre)
-- ============================================================

-- I verbi nascono dalla matrice, non dal codice: se il `meta` non porta
-- action_key + label_key la funzione non li espone affatto e la barra
-- azioni resta vuota senza che nulla fallisca. E' un silenzio, quindi
-- va presidiato qui.
SELECT is(
  (SELECT count(*)::integer
     FROM config.stati_doc_fiscale_transizioni t
    WHERE t.ammesso IS TRUE
      AND t.solo_fattura IS FALSE
      AND (t.meta->>'action_key') IN ('annulla', 'numera', 'riporta_a_draft')
      AND (t.meta->>'label_key') IS NOT NULL
      AND COALESCE((t.meta->>'manuale')::boolean, false) IS TRUE),
  3,
  '1) Seed: i tre verbi di stato del lotto hanno action_key e label_key in matrice');

-- 🔴 L'avanzamento della pipeline NON e' un pulsante che nasce dalla
-- matrice: il suo gate (step successivo + criticita' + rilancio dello
-- stesso step, D-Q p.1) vive nel runner Python. Seedare `manuale` su
-- questa riga esporrebbe un verbo che il DB non sa valutare — cioe'
-- ricreerebbe esattamente il difetto che questo lavoro chiude.
SELECT ok(
  NOT EXISTS (
    SELECT 1 FROM config.stati_doc_fiscale_transizioni t
      JOIN config.stati_doc_fiscale sf ON sf.id = t.stato_from_id
      JOIN config.stati_doc_fiscale st ON st.id = t.stato_to_id
     WHERE sf.codice_interno = 'DRAFT' AND st.codice_interno = 'EMESSA'
       AND t.solo_fattura IS FALSE
       AND (t.meta->>'action_key') IS NOT NULL),
  '2) Seed: DRAFT -> EMESSA (avanzamento pipeline) non e esposta come azione');

SELECT is(
  (SELECT count(*)::integer FROM pg_proc p
     JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'script'
      AND p.proname IN ('fn_check_lotto_fatture_pre_fiscali',
                        'fn_check_lotto_annullabile',
                        'fn_check_lotto_riportabile_a_draft',
                        'fn_available_actions_lotto')),
  4,
  '3) Le quattro funzioni nuove esistono nello schema script');

-- Contratto delle sette sorelle: lotto inesistente -> NULL, non un jsonb
-- vuoto. Il FE distingue «non c'e'» da «non ha azioni».
SELECT ok(
  script.fn_available_actions_lotto(
    (SELECT COALESCE(max(id), 0) + 1000 FROM vendite.fatturazione_lotti)
  ) IS NULL,
  '4) Capability su lotto inesistente: NULL');

-- Un id assente o <= 0 e' un errore di programmazione, non una
-- condizione di dominio: la fn_check deve rifiutarlo, non rispondere [].
SELECT throws_ok(
  $$ SELECT script.fn_check_lotto_annullabile(0) $$,
  'P0001',
  NULL,
  '5) Le fn_check rifiutano un lotto_id invalido');

-- ============================================================
-- Fixture: un lotto per ciascuno dei tre stati che espongono azioni
-- ============================================================
-- rev 2026-10-27 (brief-modello-documento-vendita §15, 20261027-19): permesso => nascondi.
--   numera e riporta_a_draft hanno numera_fatture_lotti sulla loro riga della matrice, e
--   fn_available_actions_lotto li NASCONDE a chi non ce l'ha: senza, l'8 vedrebbe {} e il 9
--   un enabled NULL. Concessa all'operatore del test prima dei test di stato: le capability
--   si misurano su chi PUO' agire. Attese invariate.
SELECT dbops.fn_pgtap_concedi_azione(current_setting('app.current_user_id')::integer, 'numera_fatture_lotti');

CREATE TEMP TABLE tmp_lotto_aal AS
SELECT s.codice_interno AS stato,
       (SELECT fl.id
          FROM vendite.fatturazione_lotti fl
         WHERE fl.stato_doc_fiscale_id = s.id
         ORDER BY fl.id DESC
         LIMIT 1) AS lotto_id
  FROM config.stati_doc_fiscale s
 WHERE s.codice_interno IN ('DRAFT', 'EMESSA', 'DEFINITIVA');

-- Le due fixture dei test 11-12 non chiedono uno stato PRECISO ma una
-- CLASSE di stati: «non in bozza» e «oltre il pre-fiscale». Cercarle
-- cosi' invece che inchiodarle a DEFINITIVA e' la differenza fra due
-- test che girano e due test che si saltano su meta' dei database.
CREATE TEMP TABLE tmp_lotto_aal_x AS
SELECT (SELECT fl.id
          FROM vendite.fatturazione_lotti fl
          JOIN config.stati_doc_fiscale s ON s.id = fl.stato_doc_fiscale_id
         WHERE s.codice_interno <> 'DRAFT'
         ORDER BY fl.id DESC LIMIT 1) AS non_draft_id,
       (SELECT fl.id
          FROM vendite.fatturazione_lotti fl
          JOIN config.stati_doc_fiscale s ON s.id = fl.stato_doc_fiscale_id
         WHERE s.codice_interno NOT IN ('DRAFT', 'EMESSA')
         ORDER BY fl.id DESC LIMIT 1) AS oltre_pre_fiscale_id;

-- ============================================================
-- 6-7) Lotto in DRAFT
-- ============================================================
-- Da DRAFT l'unica uscita manuale e' l'annullamento. «Rendi definitive»
-- non deve comparire: il gate fiscale I-7 vuole EMESSA, e la matrice lo
-- dice gia' — se comparisse, vorrebbe dire che il filtro sullo stato di
-- partenza non sta funzionando.
SELECT CASE
  WHEN (SELECT lotto_id FROM tmp_lotto_aal WHERE stato = 'DRAFT') IS NULL
    THEN skip('nessun lotto in DRAFT su questo DB', 1)
  ELSE ok(
    EXISTS (
      SELECT 1 FROM jsonb_array_elements(
        script.fn_available_actions_lotto(
          (SELECT lotto_id FROM tmp_lotto_aal WHERE stato = 'DRAFT')
        ) -> 'available_actions') a
       WHERE a->>'key' = 'annulla')
    AND NOT EXISTS (
      SELECT 1 FROM jsonb_array_elements(
        script.fn_available_actions_lotto(
          (SELECT lotto_id FROM tmp_lotto_aal WHERE stato = 'DRAFT')
        ) -> 'available_actions') a
       WHERE a->>'key' IN ('numera', 'riporta_a_draft')),
    '6) Lotto DRAFT: la capability espone annulla e non numera')
END;

-- L'equivalenza fra i due consumatori della stessa regola, lato UI:
-- enabled DEVE essere il negato di «ci sono motivi». Se qualcuno domani
-- ricalcolasse enabled con una condizione propria, qui si vede.
SELECT CASE
  WHEN (SELECT lotto_id FROM tmp_lotto_aal WHERE stato = 'DRAFT') IS NULL
    THEN skip('nessun lotto in DRAFT su questo DB', 1)
  ELSE is(
    (SELECT (a->>'enabled')::boolean
       FROM jsonb_array_elements(
         script.fn_available_actions_lotto(
           (SELECT lotto_id FROM tmp_lotto_aal WHERE stato = 'DRAFT')
         ) -> 'available_actions') a
      WHERE a->>'key' = 'annulla'),
    (jsonb_array_length(
       script.fn_check_lotto_annullabile(
         (SELECT lotto_id FROM tmp_lotto_aal WHERE stato = 'DRAFT'))) = 0),
    '7) Lotto DRAFT: enabled di annulla coincide col verdetto della fn_check')
END;

-- ============================================================
-- 8-9) Lotto in EMESSA
-- ============================================================
-- Da EMESSA le uscite manuali sono due e opposte: avanti (numera) e
-- indietro (riporta_a_draft). L'annullamento NON c'e' — e' il vicolo
-- cieco del 2026-07-31, che ora non si puo' piu' ripresentare perche'
-- la riga DRAFT->ANNULLATA parte da DRAFT e da nessun altro stato.
SELECT CASE
  WHEN (SELECT lotto_id FROM tmp_lotto_aal WHERE stato = 'EMESSA') IS NULL
    THEN skip('nessun lotto in EMESSA su questo DB', 1)
  ELSE is(
    (SELECT array_agg(a->>'key' ORDER BY a->>'key')
       FROM jsonb_array_elements(
         script.fn_available_actions_lotto(
           (SELECT lotto_id FROM tmp_lotto_aal WHERE stato = 'EMESSA')
         ) -> 'available_actions') a),
    ARRAY['numera', 'riporta_a_draft'],
    '8) Lotto EMESSA: la capability espone numera e riporta_a_draft, e solo quelli')
END;

SELECT CASE
  WHEN (SELECT lotto_id FROM tmp_lotto_aal WHERE stato = 'EMESSA') IS NULL
    THEN skip('nessun lotto in EMESSA su questo DB', 1)
  ELSE is(
    (SELECT (a->>'enabled')::boolean
       FROM jsonb_array_elements(
         script.fn_available_actions_lotto(
           (SELECT lotto_id FROM tmp_lotto_aal WHERE stato = 'EMESSA')
         ) -> 'available_actions') a
      WHERE a->>'key' = 'riporta_a_draft'),
    (jsonb_array_length(
       script.fn_check_lotto_riportabile_a_draft(
         (SELECT lotto_id FROM tmp_lotto_aal WHERE stato = 'EMESSA'))) = 0),
    '9) Lotto EMESSA: enabled di riporta_a_draft coincide col verdetto della fn_check')
END;

-- ============================================================
-- 10) Lotto DEFINITIVA
-- ============================================================
-- Da DEFINITIVA non ci sono piu' uscite manuali di stato: resta la
-- ristampa, che non e' una transizione perche' stampare e' leggere
-- (I-4). can_change_state deve dire FALSO anche se un'azione c'e': e'
-- il motivo per cui si calcola sulle sole transizioni abilitate e non
-- sulla lunghezza dell'array.
SELECT CASE
  WHEN (SELECT lotto_id FROM tmp_lotto_aal WHERE stato = 'DEFINITIVA') IS NULL
    THEN skip('nessun lotto in DEFINITIVA su questo DB', 1)
  ELSE ok(
    (SELECT array_agg(a->>'key')
       FROM jsonb_array_elements(
         script.fn_available_actions_lotto(
           (SELECT lotto_id FROM tmp_lotto_aal WHERE stato = 'DEFINITIVA')
         ) -> 'available_actions') a) = ARRAY['ristampa']
    AND (script.fn_available_actions_lotto(
           (SELECT lotto_id FROM tmp_lotto_aal WHERE stato = 'DEFINITIVA')
         ) ->> 'can_change_state')::boolean IS FALSE,
    '10) Lotto DEFINITIVA: solo ristampa, can_change_state falso')
END;

-- ============================================================
-- 11-12) 🔴 Equivalenza check <-> funzione di mutazione
-- ============================================================
-- Il cuore del file. Si prende un lotto su cui il verbo NON e' lecito e
-- si verifica che le due strade diano lo stesso verdetto: la fn_check
-- elenca almeno un motivo E la fn di mutazione solleva. Se domani
-- qualcuno rimettesse una precondizione a mano dentro la mutazione (o
-- ne togliesse una), le due meta' si separerebbero e questo test
-- diventerebbe rosso — cosa che nessun test sul solo jsonb farebbe.
--
-- ⚠️ La chiamata alla mutazione e' dentro throws_ok proprio perche'
-- deve sollevare: una chiamata nuda abortirebbe la transazione e i
-- test successivi non verrebbero eseguiti affatto.
SELECT CASE
  WHEN (SELECT lotto_id FROM tmp_lotto_aal WHERE stato = 'DEFINITIVA') IS NULL
    THEN skip('nessun lotto oltre DRAFT su questo DB', 1)
  WHEN jsonb_array_length(
         script.fn_check_lotto_annullabile(
           (SELECT lotto_id FROM tmp_lotto_aal WHERE stato = 'DEFINITIVA'))) = 0
    THEN ok(false,
            '11) INCOERENZA: la fn_check dice annullabile un lotto che non e in DRAFT')
  ELSE throws_ok(
    format($$ SELECT * FROM vendite.fn_annulla_lotto_da_draft(%s) $$,
           (SELECT lotto_id FROM tmp_lotto_aal WHERE stato = 'DEFINITIVA')),
    'P0001',
    NULL,
    '11) Equivalenza (annulla): il check elenca motivi e la mutazione solleva')
END;

SELECT CASE
  WHEN (SELECT lotto_id FROM tmp_lotto_aal WHERE stato = 'DEFINITIVA') IS NULL
    THEN skip('nessun lotto oltre il pre-fiscale su questo DB', 1)
  WHEN jsonb_array_length(
         script.fn_check_lotto_riportabile_a_draft(
           (SELECT lotto_id FROM tmp_lotto_aal WHERE stato = 'DEFINITIVA'))) = 0
    THEN ok(false,
            '12) INCOERENZA: la fn_check dice riportabile un lotto oltre il pre-fiscale')
  ELSE throws_ok(
    format($$ SELECT * FROM vendite.fn_riporta_lotto_a_draft(%s) $$,
           (SELECT lotto_id FROM tmp_lotto_aal WHERE stato = 'DEFINITIVA')),
    'P0001',
    NULL,
    '12) Equivalenza (riporta): il check elenca motivi e la mutazione solleva')
END;

SELECT * FROM finish();

ROLLBACK;
