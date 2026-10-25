-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: seed stato EVASO ordini + transizione automatica CONFERMATO -> EVASO
--       + reason dedicato in script.fn_available_actions_ordine
-- ------------------------------------------------------------
-- Parallelo a test-seed-stati-doc-preventivi-evaso-v1.sql, applicato agli
-- ordini di vendita. La transizione CONFERMATO -> EVASO ha manuale=false: non
-- e' un bottone UI.
-- ⚠️ rev 2026-10-11: il file fissava due regole che il modello ha cambiato a
--   luglio, ed era rosso da allora (test 4 e 6).
--   * EVASO = «spedizione completa» (proiezione dell'evasione,
--     vendite.fn_ordine_proietta_stato_evasione), non piu' «gia' propagato a
--     commessa»: dal 2026-07-09 ha uscite AUTOMATICHE verso CONFERMATO e
--     PARZIALMENTE_EVASO (una bolla annullata o una riga tolta lo riapre).
--     Resta terminale per l'operatore: nessuna uscita manuale.
--   * ORDINE_GIA_EVASO e' stato tolto il 2026-07-10 (20260710-02, fix «orfano
--     da push»): la spedizione non chiude il push in commessa, e il «gia'
--     fatturato» lo dice ORDINE_GIA_FATTURATO dalle righe di commessa.
--
-- Indice test (1..7):
-- 1) Stato EVASO esiste (codice_interno='EVASO', codice='EVASO', attivo=TRUE)
-- 2) EVASO ha ordine=25 (subito dopo CONFERMATO=20, prima di ALLOCATO=30)
-- 3) Transizione CONFERMATO -> EVASO esiste, attiva, con manuale=false
-- 4) Da EVASO nessuna uscita manuale; le sole uscite sono le automatiche
--    verso CONFERMATO e PARZIALMENTE_EVASO
-- 5) Guard: CONFERMATO -> EVASO ammessa (lives) — il guard approvazione
--    (->CONFERMATO only) e il guard matrice non bloccano
-- 6) fn_available_actions_ordine su EVASO: lo stato non spegne il push in
--    commessa (righe ancora da spingere -> acceso, senza motivo)
-- 7) Guard: EVASO -> ANNULLATO bloccata (throws) — terminale a runtime
-- ------------------------------------------------------------
-- rev 2026-10-25 (brief-db-pgtap-reso-costruito, giro D-4): l'ordine CONFERMATO con la
--   sua riga da dbops.fn_pgtap_crea_ordine_con_righe (cliente nuovo, trigger ereditato
--   dal BA, data 2026-06-15, 3 x 10); a mano resta solo la transizione CONFERMATO -> EVASO,
--   che e' il caso.

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

-- Contesto non-API: GUC vuota (emittente passato esplicitamente).
-- ⛔ 2026-09-04 — QUI IL TEST SPEGNEVA IL GUARD, e adesso non piu'.
--   La riga rimossa era `set_config('app.current_user_id', '', true)`: senza
--   utente in sessione `script.trgfn_guard_emittente_scope` usciva subito con
--   RETURN NEW, e le fixture entravano senza che nessuno guardasse l'emittente.
--   La fase 6 di `brief-db-processi-automatici-identita-e-perimetro` chiude quel
--   ramo — una sessione applicativa senza utente non scrive piu'.
--   ⇒ Il contesto operatore del preambolo RESTA valido per tutto il file, e le
--     fixture prendono l'emittente su cui quell'operatore puo' davvero scrivere
--     (`script.fn_pgtap_emittente_operatore()`).
--   ⭐ Non e' una riparazione di comodo: prima questo file collaudava il
--     comportamento di una porta aperta, adesso attraversa il guard come lo
--     attraversa l'applicazione.

-- ============================================================
-- TEST 1) Stato EVASO esiste e attivo
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1
    FROM config.stati_doc_ordini
    WHERE codice_interno = 'EVASO'
      AND codice = 'EVASO'
      AND attivo IS TRUE
  ),
  '1) config.stati_doc_ordini: EVASO esiste con codice_interno=EVASO, attivo=TRUE'
);

-- ============================================================
-- TEST 2) Ordine corretto (25, subito dopo CONFERMATO=20)
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1
    FROM config.stati_doc_ordini
    WHERE codice_interno = 'EVASO'
      AND ordine = 25
  ),
  '2) config.stati_doc_ordini: EVASO ha ordine=25 (dopo CONFERMATO=20, prima di ALLOCATO=30)'
);

-- ============================================================
-- TEST 3) Transizione CONFERMATO -> EVASO con manuale=false
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1
    FROM config.transizioni_stati_ordini t
    JOIN config.stati_doc_ordini sd ON sd.id = t.stato_da_id AND sd.codice_interno = 'CONFERMATO'
    JOIN config.stati_doc_ordini sa ON sa.id = t.stato_a_id  AND sa.codice_interno = 'EVASO'
    WHERE t.attivo IS TRUE
      AND (t.meta->>'manuale')::boolean IS FALSE
  ),
  '3) config.transizioni_stati_ordini: CONFERMATO -> EVASO esiste, attiva, manuale=false'
);

-- ============================================================
-- TEST 4) Da EVASO: nessuna uscita manuale, solo le automatiche del rientro
-- ============================================================
SELECT is(
  (SELECT string_agg(sa.codice_interno || ':' || COALESCE(t.meta->>'manuale', 'NULL'), ',' ORDER BY sa.codice_interno)
     FROM config.transizioni_stati_ordini t
     JOIN config.stati_doc_ordini sd ON sd.id = t.stato_da_id AND sd.codice_interno = 'EVASO'
     JOIN config.stati_doc_ordini sa ON sa.id = t.stato_a_id
    WHERE t.attivo IS TRUE),
  'CONFERMATO:false,PARZIALMENTE_EVASO:false',
  '4) da EVASO nessuna uscita manuale: solo il rientro automatico verso CONFERMATO e PARZIALMENTE_EVASO'
);

-- ============================================================
-- Fixture: ordine CONFERMATO con una riga, per la strada vera.
-- ============================================================
CREATE TEMP TABLE tmp_refs_ev AS
SELECT
  (SELECT id FROM config.stati_doc_ordini WHERE codice_interno = 'EVASO'      LIMIT 1) AS stato_evaso_id,
  (SELECT id FROM config.stati_doc_ordini WHERE codice_interno = 'ANNULLATO'  LIMIT 1) AS stato_ann_id;

-- Il cliente lo fabbrica il builder (BA legato all'emittente dell'operatore);
-- il trigger di fatturazione e' quello ereditato dal BA (CONFERMATO, test 6).
CREATE TEMP TABLE tmp_ord_ev AS
SELECT o.ordine_id AS id
  FROM dbops.fn_pgtap_crea_ordine_con_righe('ordine evaso', 'CONFERMATO',
           p_quantita => 3, p_prezzo => 10, p_data_ordine => DATE '2026-06-15') o;

-- ============================================================
-- TEST 5) Guard: CONFERMATO -> EVASO ammessa (lives)
--   Verifica anche che il guard approvazione (scatta solo verso CONFERMATO)
--   non blocchi questa transizione in uscita da CONFERMATO.
-- ============================================================
SELECT lives_ok(
  format($q$UPDATE vendite.ordini SET stato_doc_ordine_id =
              (SELECT stato_evaso_id FROM tmp_refs_ev) WHERE id = %s$q$,
         (SELECT id FROM tmp_ord_ev)),
  '5) CONFERMATO -> EVASO -> ok (transizione automatica ammessa dal guard)'
);

-- ============================================================
-- TEST 6) fn_available_actions_ordine su EVASO: lo stato non spegne il push
-- ============================================================
-- ⭐ Dal 2026-07-10 (20260710-02) il push segue l'eleggibilita' reale
--   (fn_list_ordini_da_pushare), non lo stato: un ordine EVASO con righe mai
--   spinte e' un «orfano» da recuperare, e il bottone resta acceso. Questo
--   ordine ha una riga mai spinta e fatturazione_trigger CONFERMATO.
SELECT ok(
  (SELECT (script.fn_available_actions_ordine(o.id)->>'can_push_commessa')::boolean IS TRUE
      AND (script.fn_available_actions_ordine(o.id)->>'can_push_commessa_reason') IS NULL
      AND (script.fn_available_actions_ordine(o.id)->>'stato_codice') = 'EVASO'
     FROM tmp_ord_ev o),
  '6) EVASO con righe da spingere: push in commessa acceso, nessun motivo (ORDINE_GIA_EVASO non esiste piu'')'
);

-- ============================================================
-- TEST 7) Guard: EVASO -> ANNULLATO bloccata (terminale a runtime)
-- ============================================================
SELECT throws_ok(
  format($q$UPDATE vendite.ordini SET stato_doc_ordine_id =
              (SELECT stato_ann_id FROM tmp_refs_ev) WHERE id = %s$q$,
         (SELECT id FROM tmp_ord_ev)),
  'P0001', NULL,
  '7) EVASO -> ANNULLATO -> throws E_ORDINE_TRANSIZIONE_NON_AMMESSA (terminale)'
);

SELECT * FROM finish();
ROLLBACK;
