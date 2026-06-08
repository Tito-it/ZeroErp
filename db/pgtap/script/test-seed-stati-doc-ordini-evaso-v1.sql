-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: seed stato EVASO ordini + transizione automatica CONFERMATO -> EVASO
--       + reason dedicato in script.fn_available_actions_ordine
-- ------------------------------------------------------------
-- Parallelo a test-seed-stati-doc-preventivi-evaso-v1.sql, applicato agli
-- ordini di vendita. EVASO = ordine gia' propagato a commessa (stato
-- terminale). La transizione CONFERMATO -> EVASO ha manuale=false: la invoca
-- il BE dopo il push commessa, non e' un bottone UI.
--
-- Indice test (1..7):
-- 1) Stato EVASO esiste (codice_interno='EVASO', codice='EVASO', attivo=TRUE)
-- 2) EVASO ha ordine=25 (subito dopo CONFERMATO=20, prima di ALLOCATO=30)
-- 3) Transizione CONFERMATO -> EVASO esiste, attiva, con manuale=false
-- 4) Nessuna transizione in uscita da EVASO (config: stato terminale)
-- 5) Guard: CONFERMATO -> EVASO ammessa (lives) — il guard approvazione
--    (->CONFERMATO only) e il guard matrice non bloccano
-- 6) fn_available_actions_ordine su EVASO: can_push_commessa=false,
--    reason='ORDINE_GIA_EVASO', stato_codice='EVASO'
-- 7) Guard: EVASO -> ANNULLATO bloccata (throws) — terminale a runtime
-- ------------------------------------------------------------
-- Nota emittente: l'ordine fixture passa emittente_fiscale_id esplicito e
--   billing_account_id=NULL (GUC vuota in pgTAP); bypassa trgfn_ordini_default_emittente
--   e il guard coerenza BA. La transizione di stato non dipende dal BA.

BEGIN;
SELECT plan(7);

-- Contesto non-API: GUC vuota (emittente passato esplicitamente).
SELECT set_config('app.current_user_id', '', true);

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
-- TEST 4) Nessuna transizione in uscita da EVASO (config: terminale)
-- ============================================================
SELECT ok(
  NOT EXISTS (
    SELECT 1
    FROM config.transizioni_stati_ordini t
    JOIN config.stati_doc_ordini sd ON sd.id = t.stato_da_id AND sd.codice_interno = 'EVASO'
  ),
  '4) config.transizioni_stati_ordini: nessuna transizione in uscita da EVASO (terminale)'
);

-- ============================================================
-- Fixture: ordine CONFERMATO con una riga (BA=NULL, emittente esplicito).
-- ============================================================
CREATE TEMP TABLE tmp_refs_ev AS
SELECT
  (SELECT ef.id FROM anagrafiche.emittenti_fiscali ef
    WHERE ef.attivo IS TRUE ORDER BY ef.id LIMIT 1) AS emittente_fiscale_id,
  (SELECT sr.id FROM anagrafiche.soggetti_ruoli sr ORDER BY sr.id LIMIT 1) AS soggetto_ruolo_id,
  (SELECT a.id FROM catalogo.articoli a WHERE a.attivo IS TRUE
    ORDER BY a.data_insert DESC NULLS LAST, a.id LIMIT 1) AS articolo_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1) AS valuta_id,
  (SELECT id FROM config.stati_doc_ordini WHERE codice_interno = 'CONFERMATO' LIMIT 1) AS stato_conf_id,
  (SELECT id FROM config.stati_doc_ordini WHERE codice_interno = 'EVASO'      LIMIT 1) AS stato_evaso_id,
  (SELECT id FROM config.stati_doc_ordini WHERE codice_interno = 'ANNULLATO'  LIMIT 1) AS stato_ann_id;

CREATE TEMP TABLE tmp_ord_ev AS
WITH ins AS (
  INSERT INTO vendite.ordini (
    soggetto_ruolo_id, billing_account_id, emittente_fiscale_id,
    stato_doc_ordine_id, valuta_id, data, storicizza, meta
  )
  SELECT r.soggetto_ruolo_id, NULL::bigint, r.emittente_fiscale_id,
         r.stato_conf_id, r.valuta_id, DATE '2026-06-15', false,
         '{"test_scope":"pgtap_ordine_evaso"}'::jsonb
  FROM tmp_refs_ev r
  RETURNING id
)
SELECT id FROM ins;

INSERT INTO vendite.ordini_righe (ordine_id, riga_nr, articolo_id, descrizione,
    qta_operativa, quantita, prezzo_unitario, attivo, storicizza, meta)
SELECT o.id, 1, r.articolo_id, 'riga evaso', 3.0, 3.0, 10.0, true, false, '{}'::jsonb
FROM tmp_ord_ev o, tmp_refs_ev r;

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
-- TEST 6) fn_available_actions_ordine su EVASO: push off + reason dedicato
-- ============================================================
SELECT ok(
  (SELECT (script.fn_available_actions_ordine(o.id)->>'can_push_commessa')::boolean IS FALSE
      AND (script.fn_available_actions_ordine(o.id)->>'can_push_commessa_reason') = 'ORDINE_GIA_EVASO'
      AND (script.fn_available_actions_ordine(o.id)->>'stato_codice') = 'EVASO'
     FROM tmp_ord_ev o),
  '6) EVASO: can_push_commessa=false, reason=ORDINE_GIA_EVASO, stato_codice=EVASO'
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
